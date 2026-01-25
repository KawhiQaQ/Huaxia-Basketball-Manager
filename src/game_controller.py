"""
华夏篮球联赛教练模拟器 - 游戏控制器

负责日期推进、比赛日/训练日判断和游戏流程控制
Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from src.models import (
    Player, Team, MatchResult, GameState, ScheduledGame, PlayoffSeries
)
from src.season_manager import SeasonManager
from src.match_engine import MatchEngine
from src.training_system import TrainingSystem, TrainingProgram
from src.injury_system import InjurySystem


class DayType(str, Enum):
    """日期类型枚举"""
    MATCH_DAY = "match_day"      # 比赛日
    TRAINING_DAY = "training_day"  # 训练日


class DateRegressionError(Exception):
    """日期回退错误 - 日期只能前进不能后退"""
    pass


class GameController:
    """
    游戏控制器 - 负责日期推进和游戏流程控制
    
    Requirements:
    - 10.1: 跟踪当前游戏日期
    - 10.2: 判断比赛日/训练日
    - 10.3: 比赛日触发比赛模拟
    - 10.4: 非比赛日允许训练
    - 10.5: 日期只能前进不能后退
    - 5.1, 5.4, 7.1, 7.2, 7.3: 玩家球队比赛流程控制
    """
    
    def __init__(
        self,
        season_manager: SeasonManager,
        match_engine: MatchEngine,
        training_system: TrainingSystem,
        injury_system: Optional[InjurySystem] = None,
        teams: Optional[Dict[str, Team]] = None,
        players: Optional[Dict[str, Player]] = None,
        player_team_id: Optional[str] = None
    ):
        """
        初始化游戏控制器
        
        Args:
            season_manager: 赛季管理器
            match_engine: 比赛引擎
            training_system: 训练系统
            injury_system: 伤病系统（可选）
            teams: 球队字典（可选）
            players: 球员字典（可选）
            player_team_id: 玩家控制的球队ID（可选）
        """
        self.season_manager = season_manager
        self.match_engine = match_engine
        self.training_system = training_system
        self.injury_system = injury_system or InjurySystem()
        self.teams = teams or {}
        self.players = players or {}
        self.player_team_id = player_team_id
        
        # 当前日期从赛季管理器获取
        self._current_date = season_manager.current_date
        
        # 玩家今日比赛是否完成 (Requirements 5.4, 7.1, 7.2)
        self.player_match_completed_today: bool = False
        
        # 季后赛状态属性 (Requirements 4.3, 4.4)
        self.is_playoff_phase: bool = False
        self.player_eliminated: bool = False
        
        # 季后赛轮次比赛跟踪：玩家是否已在当前轮次打过一场比赛
        # 用于实现"玩家打一场 -> AI打一场"的交替流程
        self.player_playoff_game_played_this_round: bool = False
    
    @property
    def current_date(self) -> str:
        """获取当前游戏日期 (Requirements 10.1)"""
        return self._current_date
    
    @current_date.setter
    def current_date(self, value: str) -> None:
        """
        设置当前日期（带日期单向性检查）
        
        Args:
            value: 新日期字符串 (YYYY-MM-DD格式)
            
        Raises:
            DateRegressionError: 如果新日期早于或等于当前日期
            
        Requirements: 10.5
        """
        self._validate_date_progression(value)
        self._current_date = value
        self.season_manager.current_date = value
    
    def _validate_date_progression(self, new_date: str) -> None:
        """
        验证日期只能前进不能后退 (Requirements 10.5)
        
        Args:
            new_date: 新日期字符串
            
        Raises:
            DateRegressionError: 如果新日期不晚于当前日期
        """
        current = datetime.strptime(self._current_date, "%Y-%m-%d")
        new = datetime.strptime(new_date, "%Y-%m-%d")
        
        if new <= current:
            raise DateRegressionError(
                f"日期只能前进不能后退: 当前日期 {self._current_date}, "
                f"尝试设置为 {new_date}"
            )
    
    def get_day_type(self, date: Optional[str] = None) -> DayType:
        """
        判断指定日期是比赛日还是训练日 (Requirements 10.2)
        
        Args:
            date: 日期字符串，默认为当前日期
            
        Returns:
            DayType枚举值
        """
        check_date = date or self._current_date
        
        if self.season_manager.is_match_day(check_date):
            return DayType.MATCH_DAY
        else:
            return DayType.TRAINING_DAY
    
    def is_match_day(self, date: Optional[str] = None) -> bool:
        """
        检查指定日期是否为比赛日
        
        Args:
            date: 日期字符串，默认为当前日期
            
        Returns:
            是否为比赛日
        """
        return self.get_day_type(date) == DayType.MATCH_DAY
    
    def is_training_day(self, date: Optional[str] = None) -> bool:
        """
        检查指定日期是否为训练日
        
        Args:
            date: 日期字符串，默认为当前日期
            
        Returns:
            是否为训练日
        """
        return self.get_day_type(date) == DayType.TRAINING_DAY

    def has_player_match_today(self) -> bool:
        """
        检查玩家球队今天是否有比赛 (Requirements 5.1, 7.1)
        
        Returns:
            玩家球队今天是否有比赛
        """
        if not self.player_team_id:
            return False
        
        games = self.season_manager.get_games_for_date(self._current_date)
        for game in games:
            if (game.home_team_id == self.player_team_id or 
                game.away_team_id == self.player_team_id):
                return True
        return False
    
    def is_player_match_completed(self) -> bool:
        """
        检查玩家球队今天的比赛是否已完成 (Requirements 5.4, 7.2)
        
        Returns:
            玩家球队今天的比赛是否已完成
        """
        # 如果今天没有玩家比赛，返回True（无需完成）
        if not self.has_player_match_today():
            return True
        
        # 检查状态跟踪标志
        if self.player_match_completed_today:
            return True
        
        # 检查赛程中的比赛是否已完成
        game = self.get_player_team_today_game()
        if game and game.is_played:
            return True
        
        return False
    
    def get_dashboard_action(self) -> str:
        """
        获取控制台主按钮动作 (Requirements 5.1, 5.4, 7.1, 7.2)
        
        根据当前游戏状态返回应该显示的按钮类型:
        - 'go_to_match': 玩家球队今天有比赛且未完成，显示"前往比赛"按钮
        - 'advance_day': 玩家球队今天没有比赛或比赛已完成，显示"推进日期"按钮
        
        Returns:
            'go_to_match' 或 'advance_day'
        """
        # 如果玩家球队今天有比赛且未完成，显示"前往比赛"
        if self.has_player_match_today() and not self.is_player_match_completed():
            return 'go_to_match'
        
        # 否则显示"推进日期"
        return 'advance_day'

    def advance_date(
        self,
        days: int = 1,
        auto_simulate_matches: bool = True,
        use_llm: bool = True
    ) -> Dict:
        """
        推进游戏日期 (Requirements 10.1, 10.2, 10.3, 10.4)
        
        日期推进时会：
        1. 检查日期类型（比赛日/训练日）
        2. 比赛日自动模拟所有比赛
        3. 处理球员伤病恢复
        4. 更新排行榜
        5. 重置玩家比赛完成状态
        
        Args:
            days: 推进的天数（默认1天，必须为正数）
            auto_simulate_matches: 是否自动模拟比赛日的比赛
            use_llm: 比赛模拟是否使用LLM
            
        Returns:
            包含推进结果的字典:
            {
                "previous_date": str,
                "new_date": str,
                "days_advanced": int,
                "day_results": [
                    {
                        "date": str,
                        "day_type": str,
                        "matches_played": List[MatchResult],
                        "recovered_players": List[Player],
                        "new_injuries": List[Tuple[Player, int]]
                    },
                    ...
                ]
            }
            
        Raises:
            ValueError: 如果days不是正整数
        """
        if days < 1:
            raise ValueError(f"推进天数必须为正整数，收到: {days}")
        
        previous_date = self._current_date
        day_results = []
        
        for _ in range(days):
            # 计算下一天日期
            current = datetime.strptime(self._current_date, "%Y-%m-%d")
            next_date = (current + timedelta(days=1)).strftime("%Y-%m-%d")
            
            # 更新日期（会触发日期单向性检查）
            self._current_date = next_date
            self.season_manager.current_date = next_date
            
            # 重置玩家比赛完成状态 (Requirements 5.4, 7.1)
            self.player_match_completed_today = False
            
            # 处理当天事件
            day_result = self._process_day(
                next_date,
                auto_simulate_matches,
                use_llm
            )
            day_results.append(day_result)
        
        return {
            "previous_date": previous_date,
            "new_date": self._current_date,
            "days_advanced": days,
            "day_results": day_results
        }
    
    def _process_day(
        self,
        date: str,
        auto_simulate_matches: bool,
        use_llm: bool
    ) -> Dict:
        """
        处理单天的游戏事件
        
        Args:
            date: 日期字符串
            auto_simulate_matches: 是否自动模拟比赛
            use_llm: 是否使用LLM
            
        Returns:
            当天结果字典
        """
        day_type = self.get_day_type(date)
        matches_played = []
        new_injuries = []
        
        # 处理球员伤病恢复
        recovered_players = self._process_injury_recovery()
        
        # 比赛日处理 (Requirements 10.3)
        if day_type == DayType.MATCH_DAY and auto_simulate_matches:
            matches_played, new_injuries = self._simulate_day_matches(date, use_llm)
        
        return {
            "date": date,
            "day_type": day_type.value,
            "matches_played": matches_played,
            "recovered_players": recovered_players,
            "new_injuries": new_injuries
        }
    
    def _process_injury_recovery(self) -> List[Player]:
        """
        处理球员伤病恢复
        
        Returns:
            本次恢复健康的球员列表
        """
        all_players = list(self.players.values())
        return self.injury_system.recover_players(all_players, days_passed=1)
    
    def _simulate_day_matches(
        self,
        date: str,
        use_llm: bool
    ) -> Tuple[List[MatchResult], List[Tuple[Player, int]]]:
        """
        模拟指定日期的所有比赛 (Requirements 10.3)
        
        只有玩家球队参与的比赛才使用LLM模拟，
        其他AI球队之间的比赛使用本地算法快速模拟。
        
        Args:
            date: 日期字符串
            use_llm: 是否使用LLM（仅对玩家球队比赛生效）
            
        Returns:
            (比赛结果列表, 新伤病列表) 元组
        """
        games = self.season_manager.get_games_for_date(date)
        results = []
        all_injuries = []
        
        for game in games:
            # 判断是否为玩家球队参与的比赛
            is_player_game = (
                self.player_team_id and 
                (game.home_team_id == self.player_team_id or 
                 game.away_team_id == self.player_team_id)
            )
            
            # 只有玩家球队参与的比赛才使用LLM
            game_use_llm = use_llm and is_player_game
            
            result, injuries = self.match_engine.simulate_scheduled_game(
                game=game,
                teams=self.teams,
                players=self.players,
                use_llm=game_use_llm,
                auto_update_stats=True,
                check_injuries=True
            )
            
            # 标记比赛已完成
            game.is_played = True
            game.result = result
            
            # 更新排行榜
            self.season_manager.update_standings(
                home_team_id=result.home_team_id,
                away_team_id=result.away_team_id,
                home_score=result.home_score,
                away_score=result.away_score
            )
            
            results.append(result)
            all_injuries.extend(injuries)
        
        return results, all_injuries
    
    def can_train(self, date: Optional[str] = None) -> bool:
        """
        检查指定日期是否可以进行训练 (Requirements 10.4)
        
        只有当玩家球队没有比赛时才能训练。
        整个比赛日都不能训练（无论比赛是否完成）。
        
        Args:
            date: 日期字符串，默认为当前日期
            
        Returns:
            是否可以训练
        """
        check_date = date or self._current_date
        
        if not self.player_team_id:
            return True
        
        # 检查玩家球队在该日期是否有比赛（包括已完成的）
        for game in self.season_manager.schedule:
            if game.date == check_date:
                if (game.home_team_id == self.player_team_id or 
                    game.away_team_id == self.player_team_id):
                    return False
        
        return True
    
    def get_available_actions(self, date: Optional[str] = None) -> List[str]:
        """
        获取指定日期可用的操作列表
        
        Args:
            date: 日期字符串，默认为当前日期
            
        Returns:
            可用操作名称列表
        """
        check_date = date or self._current_date
        day_type = self.get_day_type(check_date)
        
        actions = ["查看阵容", "查看排行榜", "查看赛程", "存档"]
        
        if day_type == DayType.MATCH_DAY:
            actions.extend(["观看比赛", "模拟比赛"])
        else:
            actions.extend(["训练球员", "交易球员", "签约自由球员"])
        
        actions.append("推进日期")
        
        return actions
    
    def get_today_games(self) -> List[ScheduledGame]:
        """
        获取今天的比赛列表
        
        Returns:
            今天的比赛列表
        """
        return self.season_manager.get_games_for_date(self._current_date)
    
    def get_player_team_today_game(self) -> Optional[ScheduledGame]:
        """
        获取玩家球队今天的比赛
        
        Returns:
            玩家球队今天的比赛，没有则返回None
        """
        if not self.player_team_id:
            return None
        
        games = self.get_today_games()
        for game in games:
            if (game.home_team_id == self.player_team_id or 
                game.away_team_id == self.player_team_id):
                return game
        return None
    
    def get_next_game_date(self) -> Optional[str]:
        """
        获取下一个比赛日
        
        Returns:
            下一个比赛日日期，没有则返回None
        """
        return self.season_manager.get_next_game_date(self._current_date)
    
    def skip_to_next_game(
        self,
        auto_simulate_matches: bool = True,
        use_llm: bool = True
    ) -> Optional[Dict]:
        """
        跳过到下一个比赛日
        
        会自动处理中间所有日期的事件
        
        Args:
            auto_simulate_matches: 是否自动模拟比赛
            use_llm: 是否使用LLM
            
        Returns:
            推进结果字典，如果没有下一场比赛则返回None
        """
        next_game_date = self.get_next_game_date()
        if not next_game_date:
            return None
        
        # 计算需要推进的天数
        current = datetime.strptime(self._current_date, "%Y-%m-%d")
        target = datetime.strptime(next_game_date, "%Y-%m-%d")
        days_to_advance = (target - current).days
        
        if days_to_advance <= 0:
            return None
        
        return self.advance_date(
            days=days_to_advance,
            auto_simulate_matches=auto_simulate_matches,
            use_llm=use_llm
        )

    def get_season_status(self) -> Dict:
        """
        获取赛季状态摘要
        
        Returns:
            赛季状态字典
        """
        played, total = self.season_manager.get_season_progress()
        
        return {
            "current_date": self._current_date,
            "day_type": self.get_day_type().value,
            "games_played": played,
            "total_games": total,
            "progress_pct": (played / total * 100) if total > 0 else 0,
            "is_regular_season_over": self.season_manager.is_regular_season_over(),
            "is_playoffs_over": self.season_manager.is_playoffs_over(),
            "playoff_round": self.season_manager.get_playoff_round_name() if self.season_manager.is_regular_season_over() else None,
            "champion": self.season_manager.get_champion()
        }
    
    def enter_playoffs(self) -> Dict:
        """
        进入季后赛阶段 (Requirements 1.3, 1.4)
        
        流程:
        1. 验证常规赛已结束
        2. 调用 season_manager.init_playoffs()
        3. 调用 season_manager.adjust_ai_players_for_playoffs()
        4. 设置 is_playoff_phase = True
        
        Returns:
            初始化结果字典:
            {
                "success": bool,
                "playoff_teams": List[Dict],  # 季后赛球队列表
                "ai_adjustments": Dict[str, int],  # AI球员能力调整
                "message": str
            }
            
        Raises:
            ValueError: 如果常规赛尚未结束
        """
        # 验证常规赛已结束
        if not self.season_manager.is_regular_season_over():
            played, total = self.season_manager.get_season_progress()
            remaining = total - played
            raise ValueError(f"常规赛尚未结束，还剩 {remaining} 场比赛")
        
        # 检查是否已经在季后赛阶段
        if self.is_playoff_phase:
            return {
                "success": False,
                "playoff_teams": [],
                "ai_adjustments": {},
                "message": "已经在季后赛阶段"
            }
        
        # 初始化季后赛对阵
        self.season_manager.init_playoffs()
        
        # 调整AI球员能力值
        from src.player_data_manager import calculate_overall
        ai_adjustments = self.season_manager.adjust_ai_players_for_playoffs(
            players=self.players,
            teams=self.teams,
            calculate_overall_func=calculate_overall
        )
        
        # 设置季后赛阶段标志
        self.is_playoff_phase = True
        
        # 重置玩家淘汰状态
        self.player_eliminated = False
        
        # 重置玩家本轮比赛标志
        self.player_playoff_game_played_this_round = False
        
        # 清理外援市场（进入季后赛后，所有未签约外援视为放弃）
        if self.foreign_market:
            self.foreign_market.clear_all_scouted_players()
        
        # 获取季后赛球队信息
        playoff_teams = []
        standings = self.season_manager.get_standings()
        for i, standing in enumerate(standings[:12]):
            team = self.teams.get(standing.team_id)
            team_name = team.name if team else ""
            playoff_teams.append({
                "rank": i + 1,
                "team_id": standing.team_id,
                "team_name": team_name,
                "wins": standing.wins,
                "losses": standing.losses
            })
        
        return {
            "success": True,
            "playoff_teams": playoff_teams,
            "ai_adjustments": ai_adjustments,
            "message": "季后赛初始化成功"
        }
    
    def simulate_playoff_game(
        self,
        series_id: str,
        use_llm: bool = True,
        match_context: Optional[str] = None
    ) -> Tuple[Optional[MatchResult], Dict]:
        """
        模拟一场季后赛比赛 (Requirements 4.2, 4.3)
        
        流程:
        1. 根据series_id获取系列赛
        2. 模拟比赛并更新系列赛比分
        3. 检查系列赛是否结束并触发晋级
        4. 检查玩家球队是否被淘汰
        
        Args:
            series_id: 系列赛ID (如 "play_in_1", "quarter_1", "semi_1", "final")
            use_llm: 是否使用LLM进行模拟
            match_context: 比赛背景信息（可选）
            
        Returns:
            (MatchResult对象, 系列赛更新信息) 元组
            系列赛更新信息包含:
            {
                "series_id": str,
                "team1_wins": int,
                "team2_wins": int,
                "is_complete": bool,
                "winner_id": str | None,
                "winner_name": str | None,
                "next_round_created": bool,
                "player_eliminated": bool,
                "is_champion": bool
            }
            
        Raises:
            ValueError: 如果series_id无效或系列赛已结束
        """
        # 验证季后赛阶段
        if not self.is_playoff_phase:
            raise ValueError("尚未进入季后赛阶段")
        
        # 获取系列赛
        bracket = self.season_manager.get_playoff_bracket()
        if series_id not in bracket:
            raise ValueError(f"无效的系列赛ID: {series_id}")
        
        series = bracket[series_id]
        if not isinstance(series, PlayoffSeries):
            raise ValueError(f"无效的系列赛: {series_id}")
        
        # 检查系列赛是否已结束
        if series.is_complete:
            raise ValueError(f"系列赛 {series_id} 已结束")
        
        # 获取两队信息
        team1 = self.teams.get(series.team1_id)
        team2 = self.teams.get(series.team2_id)
        
        if not team1 or not team2:
            raise ValueError(f"无法找到球队信息")
        
        # 获取两队球员
        team1_players = [p for p in self.players.values() if p.team_id == series.team1_id]
        team2_players = [p for p in self.players.values() if p.team_id == series.team2_id]
        
        # 判断是否为玩家球队参与的比赛
        is_player_game = (
            self.player_team_id and 
            (series.team1_id == self.player_team_id or series.team2_id == self.player_team_id)
        )
        
        # 季后赛所有比赛统一使用相同的模拟方式（与常规赛一致）
        # 当use_llm=True时，所有比赛都使用LLM模拟，生成球员统计数据
        game_use_llm = use_llm
        
        # 模拟比赛 (team1为主队)
        result, injuries = self.match_engine.simulate_match(
            home_team=team1,
            away_team=team2,
            home_players=team1_players,
            away_players=team2_players,
            match_context=match_context,
            use_llm=game_use_llm,
            auto_update_stats=True,
            check_injuries=True,
            is_playoff=True  # 季后赛比赛，更新季后赛统计
        )
        
        # 确定本场比赛胜者
        if result.home_score > result.away_score:
            game_winner_id = series.team1_id
        else:
            game_winner_id = series.team2_id
        
        # 更新系列赛比分，同时存储比赛结果
        series_complete, series_winner = self.season_manager.update_playoff_series(
            series_id=series_id,
            winner_id=game_winner_id,
            game_result=result  # 传递比赛结果以存储球员统计
        )
        
        # 检查是否创建了下一轮对阵
        next_round_created = False
        if series_complete:
            # 检查是否有新的系列赛被创建
            new_bracket = self.season_manager.get_playoff_bracket()
            if series_id.startswith("play_in_"):
                # 检查四分之一决赛是否创建
                next_round_created = any(
                    f"quarter_{i}" in new_bracket 
                    for i in range(1, 5)
                )
            elif series_id.startswith("quarter_"):
                # 检查半决赛是否创建
                next_round_created = any(
                    f"semi_{i}" in new_bracket 
                    for i in range(1, 3)
                )
            elif series_id.startswith("semi_"):
                # 检查总决赛是否创建
                next_round_created = "final" in new_bracket
        
        # 检查玩家球队是否被淘汰
        player_eliminated = False
        is_champion = False
        if self.player_team_id:
            if self.season_manager.is_team_eliminated(self.player_team_id):
                self.player_eliminated = True
                player_eliminated = True
            
            # 检查玩家是否获得冠军
            champion = self.season_manager.get_champion()
            if champion == self.player_team_id:
                is_champion = True
        
        # 如果是玩家球队的比赛，标记玩家已在本轮打过一场
        if is_player_game:
            self.player_playoff_game_played_this_round = True
        
        # 获取胜者名称
        winner_name = None
        if series_winner and series_winner in self.teams:
            winner_name = self.teams[series_winner].name
        
        series_update = {
            "series_id": series_id,
            "team1_wins": series.team1_wins,
            "team2_wins": series.team2_wins,
            "is_complete": series_complete,
            "winner_id": series_winner,
            "winner_name": winner_name,
            "next_round_created": next_round_created,
            "player_eliminated": player_eliminated,
            "is_champion": is_champion
        }
        
        return result, series_update
    
    def get_playoff_dashboard_action(self) -> str:
        """
        获取季后赛阶段的控制台主按钮动作 (Requirements 4.1, 4.4, 4.5)
        
        根据当前季后赛状态返回应该显示的按钮类型:
        - 'go_to_match': 玩家球队有未完成的系列赛需要比赛，且本轮还没打过
        - 'advance_series': 玩家已打过一场，需要推进AI系列赛
        - 'view_playoffs': 玩家已淘汰，观看剩余比赛
        - 'champion': 玩家获得冠军
        - 'season_over': 季后赛结束（其他球队获得冠军）
        
        Returns:
            动作字符串
        """
        # 检查是否在季后赛阶段
        if not self.is_playoff_phase:
            return 'not_in_playoffs'
        
        # 检查玩家是否获得冠军
        champion = self.season_manager.get_champion()
        if champion:
            if champion == self.player_team_id:
                return 'champion'
            else:
                return 'season_over'
        
        # 检查玩家是否已淘汰
        if self.player_eliminated:
            return 'view_playoffs'
        
        # 检查玩家球队的系列赛状态
        if self.player_team_id:
            player_series = self.season_manager.get_player_team_series(self.player_team_id)
            if player_series:
                series_id, series = player_series
                if not series.is_complete:
                    # 玩家系列赛未完成
                    # 检查玩家是否已在本轮打过一场比赛
                    if self.player_playoff_game_played_this_round:
                        # 玩家已打过一场，需要先推进AI系列赛
                        return 'advance_series'
                    else:
                        # 玩家还没打，可以比赛
                        return 'go_to_match'
                else:
                    # 玩家当前系列赛已完成，检查是否有下一轮系列赛
                    next_series = self._get_player_next_series(series_id)
                    if next_series:
                        # 下一轮系列赛已创建
                        if self.player_playoff_game_played_this_round:
                            # 玩家已打过一场，需要先推进AI系列赛
                            return 'advance_series'
                        else:
                            # 玩家可以继续比赛
                            return 'go_to_match'
                    else:
                        # 下一轮尚未创建，需要推进AI系列赛
                        return 'advance_series'
        
        # 默认：等待下一场比赛
        return 'advance_series'
    
    def _get_player_next_series(self, current_series_id: str) -> Optional[Tuple[str, PlayoffSeries]]:
        """
        获取玩家球队的下一轮系列赛
        
        Args:
            current_series_id: 当前系列赛ID
            
        Returns:
            (series_id, PlayoffSeries) 元组，如果下一轮尚未创建则返回None
        """
        if not self.player_team_id:
            return None
        
        bracket = self.season_manager.get_playoff_bracket()
        
        # 根据当前轮次确定下一轮的前缀
        if current_series_id.startswith("play_in_"):
            next_round_prefix = "quarter_"
        elif current_series_id.startswith("quarter_"):
            next_round_prefix = "semi_"
        elif current_series_id.startswith("semi_"):
            next_round_prefix = "final"
        else:
            # 已经是总决赛，没有下一轮
            return None
        
        # 查找玩家球队在下一轮的系列赛
        for series_id, series in bracket.items():
            if not isinstance(series, PlayoffSeries):
                continue
            
            if next_round_prefix == "final":
                if series_id == "final":
                    if series.team1_id == self.player_team_id or series.team2_id == self.player_team_id:
                        return (series_id, series)
            else:
                if series_id.startswith(next_round_prefix):
                    if series.team1_id == self.player_team_id or series.team2_id == self.player_team_id:
                        return (series_id, series)
        
        return None
    
    def get_player_team_current_series(self) -> Optional[Tuple[str, PlayoffSeries]]:
        """
        获取玩家球队当前的系列赛
        
        Returns:
            (series_id, PlayoffSeries) 元组，如果玩家不在季后赛或已淘汰则返回None
        """
        if not self.player_team_id:
            return None
        
        if not self.is_playoff_phase:
            return None
        
        if self.player_eliminated:
            return None
        
        return self.season_manager.get_player_team_series(self.player_team_id)
    
    def set_date_directly(self, new_date: str) -> None:
        """
        直接设置日期（带日期单向性检查）
        
        这是一个受限的方法，主要用于加载存档时恢复日期状态。
        正常游戏流程应使用 advance_date() 方法。
        
        Args:
            new_date: 新日期字符串
            
        Raises:
            DateRegressionError: 如果新日期早于或等于当前日期
            
        Requirements: 10.5
        """
        self._validate_date_progression(new_date)
        self._current_date = new_date
        self.season_manager.current_date = new_date
    
    def initialize_from_game_state(self, state: GameState) -> None:
        """
        从游戏状态初始化控制器
        
        用于加载存档后恢复游戏状态
        
        Args:
            state: 游戏状态对象
        """
        # 直接设置日期（不检查单向性，因为是加载存档）
        self._current_date = state.current_date
        self.season_manager.current_date = state.current_date
        
        self.teams = state.teams
        self.players = state.players
        self.player_team_id = state.player_team_id
        
        # 重置玩家比赛完成状态（加载存档后需要重新检查）
        self.player_match_completed_today = False
        
        # 检查当天玩家比赛是否已完成
        if self.has_player_match_today():
            game = self.get_player_team_today_game()
            if game and game.is_played:
                self.player_match_completed_today = True
        
        # 恢复季后赛状态 (Requirements 6.2)
        # 优先使用存档中保存的状态，如果没有则从playoff_bracket推断（向后兼容）
        if hasattr(state, 'is_playoff_phase'):
            self.is_playoff_phase = state.is_playoff_phase
        else:
            # 向后兼容：检查是否有季后赛对阵数据来判断是否在季后赛阶段
            playoff_bracket = self.season_manager.get_playoff_bracket()
            self.is_playoff_phase = len(playoff_bracket) > 0
        
        # 恢复玩家淘汰状态
        if hasattr(state, 'player_eliminated'):
            self.player_eliminated = state.player_eliminated
        else:
            # 向后兼容：检查玩家球队是否已淘汰
            if self.player_team_id and self.is_playoff_phase:
                self.player_eliminated = self.season_manager.is_team_eliminated(self.player_team_id)
            else:
                self.player_eliminated = False
    
    def get_game_state(self) -> Dict:
        """
        获取当前游戏状态（用于存档）
        
        Returns:
            游戏状态字典
        """
        return {
            "current_date": self._current_date,
            "player_team_id": self.player_team_id,
            "season_phase": "playoff" if self.is_playoff_phase else "regular",
            "teams": self.teams,
            "players": self.players,
            "standings": self.season_manager.get_standings(),
            "schedule": self.season_manager.schedule,
            "playoff_bracket": self.season_manager.get_playoff_bracket(),
            "player_match_completed_today": self.player_match_completed_today,
            "is_playoff_phase": self.is_playoff_phase,
            "player_eliminated": self.player_eliminated
        }
    
    def compare_dates(self, date1: str, date2: str) -> int:
        """
        比较两个日期
        
        Args:
            date1: 第一个日期
            date2: 第二个日期
            
        Returns:
            -1 如果 date1 < date2
            0 如果 date1 == date2
            1 如果 date1 > date2
        """
        d1 = datetime.strptime(date1, "%Y-%m-%d")
        d2 = datetime.strptime(date2, "%Y-%m-%d")
        
        if d1 < d2:
            return -1
        elif d1 > d2:
            return 1
        else:
            return 0
    
    def is_date_in_future(self, date: str) -> bool:
        """
        检查日期是否在当前日期之后
        
        Args:
            date: 要检查的日期
            
        Returns:
            是否在未来
        """
        return self.compare_dates(date, self._current_date) > 0
    
    def is_date_in_past(self, date: str) -> bool:
        """
        检查日期是否在当前日期之前
        
        Args:
            date: 要检查的日期
            
        Returns:
            是否在过去
        """
        return self.compare_dates(date, self._current_date) < 0
    
    def get_days_until(self, target_date: str) -> int:
        """
        计算到目标日期的天数
        
        Args:
            target_date: 目标日期
            
        Returns:
            天数（负数表示已过去）
        """
        current = datetime.strptime(self._current_date, "%Y-%m-%d")
        target = datetime.strptime(target_date, "%Y-%m-%d")
        return (target - current).days

    def simulate_player_match(
        self,
        match_context: Optional[str] = None
    ) -> Tuple[Optional[MatchResult], List[Tuple[Player, int]], int]:
        """
        模拟玩家球队比赛 (Requirements 5.3, 5.5, 6.1, 6.2)
        
        调用MatchEngine完整模拟玩家球队的比赛，生成完整的比赛解说和统计数据。
        只模拟玩家球队的比赛，不模拟其他AI球队的比赛。
        比赛结束后会根据胜负给予经费奖励。
        
        Args:
            match_context: 比赛背景信息（可选）
            
        Returns:
            (MatchResult对象, 新伤病列表, 经费奖励) 元组
            如果今天没有玩家球队比赛或比赛已完成，返回 (None, [], 0)
            
        Raises:
            ValueError: 如果玩家球队ID未设置
        """
        if not self.player_team_id:
            raise ValueError("玩家球队ID未设置")
        
        # 检查今天是否有玩家球队比赛
        if not self.has_player_match_today():
            return None, [], 0
        
        # 检查比赛是否已完成
        if self.is_player_match_completed():
            return None, [], 0
        
        # 获取玩家球队今天的比赛
        game = self.get_player_team_today_game()
        if not game:
            return None, [], 0
        
        # 使用MatchEngine完整模拟玩家球队比赛
        result, injuries = self.match_engine.simulate_player_team_match(
            game=game,
            teams=self.teams,
            players=self.players,
            match_context=match_context,
            auto_update_stats=True,
            check_injuries=True
        )
        
        # 标记比赛已完成
        game.is_played = True
        game.result = result
        
        # 更新排行榜
        self.season_manager.update_standings(
            home_team_id=result.home_team_id,
            away_team_id=result.away_team_id,
            home_score=result.home_score,
            away_score=result.away_score
        )
        
        # 计算并添加经费奖励（季后赛阶段不增加经费）
        budget_reward = 0
        player_team = self.teams.get(self.player_team_id)
        if player_team and not self.is_playoff_phase:
            # 判断玩家球队是否获胜
            is_win = result.winner_id == self.player_team_id
            from src.foreign_market import ForeignMarket
            budget_reward = ForeignMarket.add_match_reward(player_team, is_win)
        
        # 标记玩家今日比赛已完成 (Requirements 5.4, 7.2)
        self.player_match_completed_today = True
        
        return result, injuries, budget_reward
    
    def advance_day_with_ai_simulation(
        self,
        use_llm: bool = True
    ) -> Dict:
        """
        推进日期并快速模拟AI球队比赛 (Requirements 5.5, 7.4, 7.5)
        
        在玩家比赛完成后调用，推进日期并快速模拟当天剩余的AI球队比赛。
        确保玩家比赛完成后才能推进日期。
        
        Args:
            use_llm: 是否使用LLM进行AI比赛模拟（快速模式）
            
        Returns:
            包含推进结果的字典:
            {
                "previous_date": str,
                "new_date": str,
                "ai_matches_simulated": List[MatchResult],
                "new_injuries": List[Tuple[Player, int]],
                "recovered_players": List[Player],
                "error": str (可选，如果有错误)
            }
            
        Raises:
            ValueError: 如果玩家球队今天有比赛但未完成
        """
        # 检查玩家比赛是否完成 (Requirements 7.2)
        if self.has_player_match_today() and not self.is_player_match_completed():
            raise ValueError("玩家球队今天的比赛尚未完成，无法推进日期")
        
        previous_date = self._current_date
        ai_matches_results = []
        all_injuries = []
        
        # 模拟当天剩余的AI球队比赛 (Requirements 7.4)
        today_games = self.season_manager.get_games_for_date(self._current_date)
        ai_games = []
        
        for game in today_games:
            # 跳过已完成的比赛（包括玩家球队的比赛）
            if game.is_played:
                continue
            
            # 跳过玩家球队参与的比赛（应该已经完成了）
            if self.player_team_id and (
                game.home_team_id == self.player_team_id or 
                game.away_team_id == self.player_team_id
            ):
                continue
            
            ai_games.append(game)
        
        # 批量模拟AI球队比赛
        if ai_games:
            batch_results = self.match_engine.batch_simulate_ai_matches(
                games=ai_games,
                teams=self.teams,
                players=self.players,
                auto_update_stats=True,
                check_injuries=True
            )
            
            for i, (result, injuries) in enumerate(batch_results):
                game = ai_games[i]
                
                # 标记比赛已完成
                game.is_played = True
                game.result = result
                
                # 更新排行榜
                self.season_manager.update_standings(
                    home_team_id=result.home_team_id,
                    away_team_id=result.away_team_id,
                    home_score=result.home_score,
                    away_score=result.away_score
                )
                
                ai_matches_results.append(result)
                all_injuries.extend(injuries)
        
        # 推进日期
        current = datetime.strptime(self._current_date, "%Y-%m-%d")
        next_date = (current + timedelta(days=1)).strftime("%Y-%m-%d")
        
        self._current_date = next_date
        self.season_manager.current_date = next_date
        
        # 重置玩家比赛完成状态
        self.player_match_completed_today = False
        
        # 处理球员伤病恢复 (Requirements 7.5)
        recovered_players = self._process_injury_recovery()
        
        return {
            "previous_date": previous_date,
            "new_date": self._current_date,
            "ai_matches_simulated": ai_matches_results,
            "new_injuries": all_injuries,
            "recovered_players": recovered_players
        }
    
    def can_advance_day(self) -> bool:
        """
        检查是否可以推进日期 (Requirements 7.2)
        
        如果玩家球队今天有比赛且未完成，则不能推进日期。
        
        Returns:
            是否可以推进日期
        """
        # 如果玩家球队今天有比赛且未完成，不能推进日期
        if self.has_player_match_today() and not self.is_player_match_completed():
            return False
        return True

    def get_status_message(self) -> str:
        """
        获取当前游戏状态消息 (Requirements 7.1, 7.2, 7.3)
        
        根据游戏状态返回正确的状态消息:
        - "今日有比赛" 当玩家球队今天有未完成的比赛
        - "今日比赛已完成" 当玩家球队今天的比赛已完成
        - "训练日" 当今天没有玩家球队的比赛
        
        Returns:
            状态消息字符串
        """
        # 检查玩家球队今天是否有比赛
        if self.has_player_match_today():
            # 检查比赛是否已完成
            if self.is_player_match_completed():
                return "今日比赛已完成"
            else:
                return "今日有比赛"
        else:
            # 今天没有玩家球队的比赛，是训练日
            return "训练日"

    def advance_day_only(self) -> Dict:
        """
        仅推进日期，不模拟下一天的比赛 (Requirements 1.1, 1.2, 4.1, 4.2, 4.3)
        
        流程:
        1. 检查玩家球队是否有未完成的比赛（如果有则阻止推进）
        2. 检查当前日期是否有未模拟的AI比赛
        3. 如果有，先模拟这些AI比赛
        4. 然后推进日期到下一天
        5. 重置玩家比赛完成状态
        
        注意：此方法不会模拟下一天的任何比赛
        
        Returns:
            {
                "previous_date": str,
                "new_date": str,
                "ai_matches_simulated": List[MatchResult],
                "new_day_type": str,
                "has_player_match": bool,
                "dashboard_action": str
            }
            
        Raises:
            ValueError: 如果玩家球队有未完成的比赛
        """
        previous_date = self._current_date
        ai_matches_results = []
        all_injuries = []
        
        # 步骤0: 检查玩家球队是否有未完成的比赛（阻止跳过，确保42场比赛完整）
        if self.has_player_match_today() and not self.is_player_match_completed():
            raise ValueError("玩家球队今天有未完成的比赛，请先完成比赛再推进日期")
        
        # 步骤1: 检查并模拟当前日期未完成的AI比赛 (Requirements 4.1, 4.3)
        today_games = self.season_manager.get_games_for_date(self._current_date)
        ai_games_to_simulate = []
        
        for game in today_games:
            # 跳过已完成的比赛
            if game.is_played:
                continue
            
            # 跳过玩家球队参与的比赛（此时应该已经完成了）
            if self.player_team_id and (
                game.home_team_id == self.player_team_id or 
                game.away_team_id == self.player_team_id
            ):
                continue
            
            ai_games_to_simulate.append(game)
        
        # 批量模拟AI球队比赛（使用LLM快速模式）
        if ai_games_to_simulate:
            batch_results = self.match_engine.batch_simulate_ai_matches(
                games=ai_games_to_simulate,
                teams=self.teams,
                players=self.players,
                auto_update_stats=True,
                check_injuries=True
            )
            
            for i, (result, injuries) in enumerate(batch_results):
                game = ai_games_to_simulate[i]
                
                # 标记比赛已完成
                game.is_played = True
                game.result = result
                
                # 更新排行榜
                self.season_manager.update_standings(
                    home_team_id=result.home_team_id,
                    away_team_id=result.away_team_id,
                    home_score=result.home_score,
                    away_score=result.away_score
                )
                
                ai_matches_results.append(result)
                all_injuries.extend(injuries)
        
        # 步骤2: 推进日期到下一天 (Requirements 1.1, 1.2)
        current = datetime.strptime(self._current_date, "%Y-%m-%d")
        next_date = (current + timedelta(days=1)).strftime("%Y-%m-%d")
        
        self._current_date = next_date
        self.season_manager.current_date = next_date
        
        # 步骤3: 重置玩家比赛完成状态
        self.player_match_completed_today = False
        
        # 步骤4: 处理球员伤病恢复
        recovered_players = self._process_injury_recovery()
        
        # 获取新日期的状态信息
        new_day_type = self.get_day_type().value
        has_player_match = self.has_player_match_today()
        dashboard_action = self.get_dashboard_action()
        status_message = self.get_status_message()
        
        return {
            "previous_date": previous_date,
            "new_date": self._current_date,
            "ai_matches_simulated": ai_matches_results,
            "new_injuries": all_injuries,
            "recovered_players": recovered_players,
            "new_day_type": new_day_type,
            "has_player_match": has_player_match,
            "dashboard_action": dashboard_action,
            "status_message": status_message
        }
