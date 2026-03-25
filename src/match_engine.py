"""
华夏篮球联赛教练模拟器 - 比赛引擎

负责调用LLM进行比赛模拟，生成比赛叙述和球员统计数据
"""
import random
from typing import List, Optional, Dict, Tuple
from dataclasses import asdict

from src.models import (
    Player, Team, MatchResult, GameStats, ScheduledGame
)
from src.llm_interface import LLMInterface
from src.player_data_manager import PlayerDataManager
from src.injury_system import InjurySystem
from config import SimulationConfig


class MatchEngine:
    """比赛引擎 - 负责比赛模拟和统计更新
    
    支持分层模拟策略:
    - 玩家球队比赛（Full Simulation）: 完整模拟，生成解说、精彩时刻、节次比分和球员统计
    - 非玩家球队比赛（Quick Simulation）: 快速模拟，仅生成球员统计数据
    """
    
    def __init__(
        self,
        llm_interface: LLMInterface,
        data_manager: Optional[PlayerDataManager] = None,
        injury_system: Optional[InjurySystem] = None
    ):
        """
        初始化比赛引擎
        
        Args:
            llm_interface: LLM接口实例
            data_manager: 球员数据管理器（可选，用于自动更新统计）
            injury_system: 伤病系统（可选，用于伤病检测）
        """
        self.llm = llm_interface
        self.data_manager = data_manager
        self.injury_system = injury_system or InjurySystem()
    
    def simulate_match(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        match_context: Optional[str] = None,
        use_llm: bool = True,
        auto_update_stats: bool = True,
        check_injuries: bool = True,
        is_playoff: bool = False
    ) -> Tuple[MatchResult, List[Tuple[Player, int]]]:
        """
        模拟一场比赛
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            match_context: 比赛背景信息（可选）
            use_llm: 是否使用LLM进行模拟（False则使用fallback算法）
            auto_update_stats: 是否自动更新球员统计数据
            check_injuries: 是否检查伤病（适用于所有球队，包括AI球队）
            is_playoff: 是否为季后赛比赛
            
        Returns:
            (MatchResult对象, 新伤病列表) 元组
            MatchResult包含比分、叙述和球员统计
            新伤病列表为 [(Player, recovery_days), ...]
        """
        # 过滤掉受伤球员和被裁球员（Requirements 13.3）
        active_home_players = [p for p in home_players if not p.is_injured and not p.is_waived]
        active_away_players = [p for p in away_players if not p.is_injured and not p.is_waived]
        
        # 检查全局配置和LLM接口是否可用
        if not SimulationConfig.USE_LLM or self.llm is None:
            use_llm = False
        
        # 调用LLM接口进行比赛模拟
        if self.llm is not None:
            result = self.llm.simulate_match(
                home_team=home_team,
                away_team=away_team,
                home_players=active_home_players,
                away_players=active_away_players,
                match_context=match_context,
                use_llm=use_llm
            )
        else:
            # LLM不可用时使用本地fallback算法
            result = self._generate_fallback_match_result(
                home_team.id, away_team.id, 
                active_home_players, active_away_players
            )
        
        # 自动更新球员统计数据
        if auto_update_stats and self.data_manager:
            self._update_all_player_stats(result, is_playoff=is_playoff)
        
        # 检查伤病（适用于所有球队，包括AI球队 - Requirements 13.5）
        new_injuries = []
        if check_injuries:
            # 对参赛的健康球员进行伤病检测
            all_active_players = active_home_players + active_away_players
            new_injuries = self.injury_system.check_for_injuries(all_active_players)
            
            # 应用伤病
            for player, days in new_injuries:
                self.injury_system.apply_injury(player, days)
        
        return result, new_injuries
    
    def simulate_scheduled_game(
        self,
        game: ScheduledGame,
        teams: Dict[str, Team],
        players: Dict[str, Player],
        match_context: Optional[str] = None,
        use_llm: bool = True,
        auto_update_stats: bool = True,
        check_injuries: bool = True,
        is_playoff: bool = False
    ) -> Tuple[MatchResult, List[Tuple[Player, int]]]:
        """
        模拟一场已安排的比赛
        
        Args:
            game: 赛程中的比赛
            teams: 球队字典 {team_id: Team}
            players: 球员字典 {player_id: Player}
            match_context: 比赛背景信息
            use_llm: 是否使用LLM
            auto_update_stats: 是否自动更新统计
            check_injuries: 是否检查伤病
            is_playoff: 是否为季后赛比赛
            
        Returns:
            (MatchResult对象, 新伤病列表) 元组
        """
        home_team = teams.get(game.home_team_id)
        away_team = teams.get(game.away_team_id)
        
        if not home_team or not away_team:
            raise ValueError(f"找不到球队: {game.home_team_id} 或 {game.away_team_id}")
        
        # 获取球队阵容
        home_players = self._get_team_players(home_team, players)
        away_players = self._get_team_players(away_team, players)
        
        return self.simulate_match(
            home_team=home_team,
            away_team=away_team,
            home_players=home_players,
            away_players=away_players,
            match_context=match_context,
            use_llm=use_llm,
            auto_update_stats=auto_update_stats,
            check_injuries=check_injuries,
            is_playoff=is_playoff
        )
    
    def simulate_player_team_match(
        self,
        game: ScheduledGame,
        teams: Dict[str, Team],
        players: Dict[str, Player],
        match_context: Optional[str] = None,
        auto_update_stats: bool = True,
        check_injuries: bool = True,
        is_playoff: bool = False
    ) -> Tuple[MatchResult, List[Tuple[Player, int]]]:
        """
        模拟玩家球队比赛 - 使用快速模拟（与AI球队相同）
        
        生成球员统计数据，不生成解说文本
        
        Args:
            game: 赛程中的比赛（必须包含玩家球队）
            teams: 球队字典 {team_id: Team}
            players: 球员字典 {player_id: Player}
            match_context: 比赛背景信息（可选，已弃用）
            auto_update_stats: 是否自动更新球员统计数据
            check_injuries: 是否检查伤病
            is_playoff: 是否为季后赛比赛
            
        Returns:
            (MatchResult对象, 新伤病列表) 元组
        """
        # 直接调用 AI 球队模拟方法（快速模拟）
        return self.simulate_ai_team_match(
            game=game,
            teams=teams,
            players=players,
            auto_update_stats=auto_update_stats,
            check_injuries=check_injuries,
            is_playoff=is_playoff
        )
    
    def simulate_ai_team_match(
        self,
        game: ScheduledGame,
        teams: Dict[str, Team],
        players: Dict[str, Player],
        auto_update_stats: bool = True,
        check_injuries: bool = True,
        is_playoff: bool = False
    ) -> Tuple[MatchResult, List[Tuple[Player, int]]]:
        """
        模拟非玩家球队比赛 - 快速模式（根据全局配置决定是否使用LLM）
        
        根据SimulationConfig.USE_LLM配置决定使用LLM还是本地算法：
        - USE_LLM=True: 使用LLM快速模拟
        - USE_LLM=False: 使用本地算法（调试模式，更快）
        
        仅生成:
        - 球员统计数据 (player_stats)
        
        不生成解说等文本内容，用于每日比赛页面展示和场均数据更新
        
        Args:
            game: 赛程中的比赛（不包含玩家球队）
            teams: 球队字典 {team_id: Team}
            players: 球员字典 {player_id: Player}
            auto_update_stats: 是否自动更新球员统计数据
            check_injuries: 是否检查伤病
            is_playoff: 是否为季后赛比赛
            
        Returns:
            (MatchResult对象, 新伤病列表) 元组
            MatchResult仅包含球员统计数据，不含解说文本
            
        Requirements: 4.4, 4.5, 4.6 - AI比赛根据配置使用LLM或本地算法
        """
        home_team = teams.get(game.home_team_id)
        away_team = teams.get(game.away_team_id)
        
        if not home_team or not away_team:
            raise ValueError(f"找不到球队: {game.home_team_id} 或 {game.away_team_id}")
        
        # 获取球队阵容
        home_players = self._get_team_players(home_team, players)
        away_players = self._get_team_players(away_team, players)
        
        # 过滤掉受伤球员和被裁球员
        active_home_players = [p for p in home_players if not p.is_injured and not p.is_waived]
        active_away_players = [p for p in away_players if not p.is_injured and not p.is_waived]
        
        # 根据全局配置决定使用LLM还是本地算法
        if SimulationConfig.USE_LLM and self.llm is not None:
            # 使用LLM快速模拟
            result = self.llm.simulate_match_quick(
                home_team=home_team,
                away_team=away_team,
                home_players=active_home_players,
                away_players=active_away_players
            )
        else:
            # 使用本地算法模拟（调试模式）
            from src.stats_calculator import StatsCalculator
            
            # 生成球队统计数据
            home_player_stats, home_score = StatsCalculator.generate_team_stats(active_home_players)
            away_player_stats, away_score = StatsCalculator.generate_team_stats(active_away_players)
            
            # 获取球员ID集合
            home_player_ids = set(home_player_stats.keys())
            away_player_ids = set(away_player_stats.keys())
            
            # 合并球员统计
            player_stats = {**home_player_stats, **away_player_stats}
            
            # 应用得分随机调整（两队各自选择模式）
            player_stats = StatsCalculator.apply_score_adjustment(
                player_stats, home_player_ids, away_player_ids
            )
            
            # 重新计算球队总分（基于调整后的球员得分）
            home_score = StatsCalculator.calculate_team_score(player_stats, home_player_ids)
            away_score = StatsCalculator.calculate_team_score(player_stats, away_player_ids)
            
            # 确保不是平局
            if home_score == away_score:
                if random.random() < 0.5:
                    home_score += 1
                    # 给主队得分最高的球员加1分
                    home_top = max(
                        [(pid, s) for pid, s in player_stats.items() if pid in home_player_ids],
                        key=lambda x: x[1].points,
                        default=(None, None)
                    )
                    if home_top[0]:
                        player_stats[home_top[0]].points += 1
                else:
                    away_score += 1
                    # 给客队得分最高的球员加1分
                    away_top = max(
                        [(pid, s) for pid, s in player_stats.items() if pid in away_player_ids],
                        key=lambda x: x[1].points,
                        default=(None, None)
                    )
                    if away_top[0]:
                        player_stats[away_top[0]].points += 1
            
            result = MatchResult(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=home_score,
                away_score=away_score,
                narrative="",
                player_stats=player_stats,
                quarter_scores=[],
                highlights=[],
                commentary="",
                home_player_ids=list(home_player_ids),  # 记录比赛时的球员列表
                away_player_ids=list(away_player_ids)   # 记录比赛时的球员列表
            )
        
        # 自动更新球员统计数据
        if auto_update_stats and self.data_manager:
            self._update_all_player_stats(result, is_playoff=is_playoff)
        
        # 检查伤病（适用于所有球队，包括AI球队）
        new_injuries = []
        if check_injuries:
            all_active_players = active_home_players + active_away_players
            new_injuries = self.injury_system.check_for_injuries(all_active_players)
            
            for player, days in new_injuries:
                self.injury_system.apply_injury(player, days)
        
        return result, new_injuries
    
    def batch_simulate_ai_matches(
        self,
        games: List[ScheduledGame],
        teams: Dict[str, Team],
        players: Dict[str, Player],
        auto_update_stats: bool = True,
        check_injuries: bool = True,
        is_playoff: bool = False
    ) -> List[Tuple[MatchResult, List[Tuple[Player, int]]]]:
        """
        批量模拟非玩家球队比赛（支持并发）
        
        用于日期推进时快速处理多场比赛。
        当启用并发模拟时，会同时发送多个 LLM API 请求，显著提高模拟速度。
        
        Args:
            games: 赛程中的比赛列表（不包含玩家球队的比赛）
            teams: 球队字典 {team_id: Team}
            players: 球员字典 {player_id: Player}
            auto_update_stats: 是否自动更新球员统计数据
            check_injuries: 是否检查伤病
            is_playoff: 是否为季后赛比赛
            
        Returns:
            [(MatchResult, 新伤病列表), ...] 列表
            每个MatchResult仅包含球员统计数据
            
        Requirements: 1.2, 5.3, 6.1
        """
        from config import LLMConfig, SimulationConfig
        
        results = []
        
        if not games:
            return results
        
        # 检查是否使用 LLM 并发模拟
        use_concurrent = (
            SimulationConfig.USE_LLM and 
            self.llm is not None and 
            LLMConfig.ENABLE_CONCURRENT_SIMULATION and
            len(games) > 1
        )
        
        if use_concurrent:
            # 准备比赛数据
            matches_data = []
            game_player_data = []  # 存储每场比赛的球员数据，用于后续伤病检测
            
            for game in games:
                home_team = teams.get(game.home_team_id)
                away_team = teams.get(game.away_team_id)
                
                if not home_team or not away_team:
                    print(f"警告: 找不到球队 {game.home_team_id} 或 {game.away_team_id}")
                    continue
                
                # 获取球队阵容
                home_players = self._get_team_players(home_team, players)
                away_players = self._get_team_players(away_team, players)
                
                # 过滤掉受伤球员和被裁球员
                active_home_players = [p for p in home_players if not p.is_injured and not p.is_waived]
                active_away_players = [p for p in away_players if not p.is_injured and not p.is_waived]
                
                matches_data.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_players": active_home_players,
                    "away_players": active_away_players
                })
                game_player_data.append((active_home_players, active_away_players))
            
            # 并发模拟所有比赛
            if matches_data:
                match_results = self.llm.batch_simulate_matches_concurrent(matches_data)
                
                # 处理结果
                for i, result in enumerate(match_results):
                    active_home_players, active_away_players = game_player_data[i]
                    
                    # 自动更新球员统计数据
                    if auto_update_stats and self.data_manager:
                        self._update_all_player_stats(result, is_playoff=is_playoff)
                    
                    # 检查伤病
                    new_injuries = []
                    if check_injuries:
                        all_active_players = active_home_players + active_away_players
                        new_injuries = self.injury_system.check_for_injuries(all_active_players)
                        
                        for player, days in new_injuries:
                            self.injury_system.apply_injury(player, days)
                    
                    results.append((result, new_injuries))
        else:
            # 串行模拟（原有逻辑）
            for game in games:
                try:
                    result, injuries = self.simulate_ai_team_match(
                        game=game,
                        teams=teams,
                        players=players,
                        auto_update_stats=auto_update_stats,
                        check_injuries=check_injuries,
                        is_playoff=is_playoff
                    )
                    results.append((result, injuries))
                except Exception as e:
                    # 如果单场比赛模拟失败，记录错误但继续处理其他比赛
                    print(f"警告: 模拟比赛 {game.home_team_id} vs {game.away_team_id} 失败: {e}")
                    # 创建一个空的fallback结果
                    fallback_result = self._create_empty_fallback_result(
                        game.home_team_id, game.away_team_id
                    )
                    results.append((fallback_result, []))
        
        return results

    def batch_simulate_playoff_ai_matches(
        self,
        series_matches: List[Tuple[str, str, str]],
        teams: Dict[str, Team],
        players: Dict[str, Player],
        auto_update_stats: bool = True,
        check_injuries: bool = True
    ) -> List[Tuple[str, MatchResult, List[Tuple[Player, int]]]]:
        """
        批量并发模拟季后赛AI比赛

        与 batch_simulate_ai_matches 类似，但接受季后赛系列赛数据而非 ScheduledGame。

        Args:
            series_matches: [(series_id, home_team_id, away_team_id), ...] 列表
            teams: 球队字典
            players: 球员字典
            auto_update_stats: 是否自动更新球员统计数据
            check_injuries: 是否检查伤病

        Returns:
            [(series_id, MatchResult, 新伤病列表), ...] 列表
        """
        from config import LLMConfig, SimulationConfig

        results = []

        if not series_matches:
            return results

        use_concurrent = (
            SimulationConfig.USE_LLM and
            self.llm is not None and
            LLMConfig.ENABLE_CONCURRENT_SIMULATION and
            len(series_matches) > 1
        )

        if use_concurrent:
            matches_data = []
            game_meta = []  # (series_id, active_home_players, active_away_players)

            for series_id, home_team_id, away_team_id in series_matches:
                home_team = teams.get(home_team_id)
                away_team = teams.get(away_team_id)

                if not home_team or not away_team:
                    print(f"警告: 找不到球队 {home_team_id} 或 {away_team_id}")
                    continue

                home_players_list = self._get_team_players(home_team, players)
                away_players_list = self._get_team_players(away_team, players)
                active_home = [p for p in home_players_list if not p.is_injured and not p.is_waived]
                active_away = [p for p in away_players_list if not p.is_injured and not p.is_waived]

                matches_data.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_players": active_home,
                    "away_players": active_away
                })
                game_meta.append((series_id, active_home, active_away))

            if matches_data:
                match_results = self.llm.batch_simulate_matches_concurrent(matches_data)

                for i, result in enumerate(match_results):
                    sid, active_home, active_away = game_meta[i]

                    if auto_update_stats and self.data_manager:
                        self._update_all_player_stats(result, is_playoff=True)

                    new_injuries = []
                    if check_injuries:
                        all_active = active_home + active_away
                        new_injuries = self.injury_system.check_for_injuries(all_active)
                        for player, days in new_injuries:
                            self.injury_system.apply_injury(player, days)

                    results.append((sid, result, new_injuries))
        else:
            # 串行回退
            for series_id, home_team_id, away_team_id in series_matches:
                try:
                    home_team = teams.get(home_team_id)
                    away_team = teams.get(away_team_id)
                    if not home_team or not away_team:
                        continue

                    home_players_list = self._get_team_players(home_team, players)
                    away_players_list = self._get_team_players(away_team, players)
                    active_home = [p for p in home_players_list if not p.is_injured and not p.is_waived]
                    active_away = [p for p in away_players_list if not p.is_injured and not p.is_waived]

                    if SimulationConfig.USE_LLM and self.llm is not None:
                        result = self.llm.simulate_match_quick(
                            home_team=home_team,
                            away_team=away_team,
                            home_players=active_home,
                            away_players=active_away
                        )
                    else:
                        result = self._generate_fallback_match_result(
                            home_team_id, away_team_id, active_home, active_away
                        )

                    if auto_update_stats and self.data_manager:
                        self._update_all_player_stats(result, is_playoff=True)

                    new_injuries = []
                    if check_injuries:
                        all_active = active_home + active_away
                        new_injuries = self.injury_system.check_for_injuries(all_active)
                        for player, days in new_injuries:
                            self.injury_system.apply_injury(player, days)

                    results.append((series_id, result, new_injuries))
                except Exception as e:
                    print(f"警告: 模拟季后赛 {series_id} ({home_team_id} vs {away_team_id}) 失败: {e}")
                    fallback = self._create_empty_fallback_result(home_team_id, away_team_id)
                    results.append((series_id, fallback, []))

        return results

    
    def _create_empty_fallback_result(
        self,
        home_team_id: str,
        away_team_id: str
    ) -> MatchResult:
        """
        创建空的fallback比赛结果（当模拟完全失败时使用）
        
        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            
        Returns:
            基本的MatchResult对象
        """
        # 生成随机但合理的比分
        home_score = random.randint(90, 110)
        away_score = random.randint(90, 110)
        
        # 确保不是平局
        if home_score == away_score:
            home_score += 1
        
        return MatchResult(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            narrative="",
            player_stats={},
            quarter_scores=[],
            highlights=[],
            commentary=""
        )
    
    def _get_team_players(
        self,
        team: Team,
        players: Dict[str, Player]
    ) -> List[Player]:
        """
        获取球队的球员列表
        
        Args:
            team: 球队对象
            players: 球员字典
            
        Returns:
            球员列表
        """
        team_players = []
        for player_id in team.roster:
            if player_id in players:
                team_players.append(players[player_id])
        return team_players
    
    def _generate_fallback_match_result(
        self,
        home_team_id: str,
        away_team_id: str,
        home_players: List[Player],
        away_players: List[Player]
    ) -> MatchResult:
        """
        生成fallback比赛结果（当LLM不可用时使用）
        
        使用StatsCalculator确保比分一致性：球队总分 = 球员得分之和
        
        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_players: 主队球员列表
            away_players: 客队球员列表
            
        Returns:
            基于球员能力值随机生成的MatchResult，保证比分一致性
        """
        from src.stats_calculator import StatsCalculator
        
        # 使用StatsCalculator生成球队统计数据，确保比分一致性
        home_player_stats, home_score = StatsCalculator.generate_team_stats(home_players)
        away_player_stats, away_score = StatsCalculator.generate_team_stats(away_players)
        
        # 获取球员ID集合
        home_player_ids = set(home_player_stats.keys())
        away_player_ids = set(away_player_stats.keys())
        
        # 合并球员统计
        player_stats = {**home_player_stats, **away_player_stats}
        
        # 应用得分随机调整（两队各自选择模式）
        player_stats = StatsCalculator.apply_score_adjustment(
            player_stats, home_player_ids, away_player_ids
        )
        
        # 确保分数在合理范围内
        player_stats, home_score, away_score = StatsCalculator.validate_and_adjust_stats(
            player_stats, home_player_ids, away_player_ids
        )
        
        # 确保不是平局
        if home_score == away_score:
            # 根据球队平均总评决定谁加分
            home_avg = sum(p.overall for p in home_players) / len(home_players) if home_players else 70
            away_avg = sum(p.overall for p in away_players) / len(away_players) if away_players else 70
            
            if home_avg >= away_avg:
                home_score += 1
                # 给主队得分最高的球员加1分
                home_top = max(
                    [(pid, s) for pid, s in player_stats.items() if pid in home_player_ids],
                    key=lambda x: x[1].points,
                    default=(None, None)
                )
                if home_top[0]:
                    player_stats[home_top[0]].points += 1
            else:
                away_score += 1
                away_top = max(
                    [(pid, s) for pid, s in player_stats.items() if pid in away_player_ids],
                    key=lambda x: x[1].points,
                    default=(None, None)
                )
                if away_top[0]:
                    player_stats[away_top[0]].points += 1
        
        # 生成比赛叙述
        narrative = f"比赛结束，最终比分{home_score}:{away_score}。双方球员都展现了出色的竞技状态。"
        
        return MatchResult(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            narrative=narrative,
            player_stats=player_stats,
            home_player_ids=list(home_player_ids),  # 记录比赛时的球员列表
            away_player_ids=list(away_player_ids)   # 记录比赛时的球员列表
        )
    
    def _update_all_player_stats(self, result: MatchResult, is_playoff: bool = False) -> None:
        """
        更新比赛中所有球员的统计数据
        
        Args:
            result: 比赛结果
            is_playoff: 是否为季后赛比赛
        """
        if not self.data_manager:
            return
        
        for player_id, game_stats in result.player_stats.items():
            self.update_player_stats(player_id, game_stats, is_playoff=is_playoff)
    
    def update_player_stats(
        self,
        player_id: str,
        game_stats: GameStats,
        is_playoff: bool = False
    ) -> None:
        """
        更新单个球员的统计数据
        
        根据单场比赛数据更新球员的累计统计和场均数据
        
        Args:
            player_id: 球员ID
            game_stats: 单场比赛统计数据
            is_playoff: 是否为季后赛比赛
        """
        if not self.data_manager:
            return
        
        player = self.data_manager.get_player(player_id)
        if not player:
            return
        
        # 将GameStats转换为字典格式
        stats_dict = {
            "points": game_stats.points,
            "rebounds": game_stats.rebounds,
            "assists": game_stats.assists,
            "steals": game_stats.steals,
            "blocks": game_stats.blocks,
            "turnovers": game_stats.turnovers,
            "minutes": game_stats.minutes
        }
        
        # 根据是否季后赛使用不同的更新方法
        if is_playoff:
            self.data_manager.update_player_playoff_stats(player_id, stats_dict)
        else:
            self.data_manager.update_player_stats(player_id, stats_dict)
    
    def batch_update_player_stats(
        self,
        player_stats: Dict[str, GameStats],
        is_playoff: bool = False
    ) -> None:
        """
        批量更新多个球员的统计数据
        
        Args:
            player_stats: 球员统计字典 {player_id: GameStats}
            is_playoff: 是否为季后赛比赛
        """
        for player_id, game_stats in player_stats.items():
            self.update_player_stats(player_id, game_stats, is_playoff=is_playoff)
    
    def get_match_summary(self, result: MatchResult) -> str:
        """
        生成比赛摘要文本
        
        Args:
            result: 比赛结果
            
        Returns:
            格式化的比赛摘要字符串
        """
        summary = f"比赛结束\n"
        summary += f"{'=' * 40}\n"
        summary += f"最终比分: {result.home_score} - {result.away_score}\n"
        summary += f"{'=' * 40}\n"
        
        if result.narrative:
            summary += f"\n比赛回顾:\n{result.narrative}\n"
        
        if result.player_stats:
            summary += f"\n{'=' * 40}\n"
            summary += "球员数据:\n"
            
            # 按得分排序显示球员数据
            sorted_stats = sorted(
                result.player_stats.items(),
                key=lambda x: x[1].points,
                reverse=True
            )
            
            for player_id, stats in sorted_stats[:10]:  # 只显示前10名
                summary += (
                    f"  {player_id}: "
                    f"{stats.points}分 {stats.rebounds}篮板 {stats.assists}助攻 "
                    f"{stats.steals}抢断 {stats.blocks}盖帽 "
                    f"({stats.minutes}分钟)\n"
                )
        
        return summary
    
    def validate_match_result(self, result: MatchResult) -> bool:
        """
        验证比赛结果的有效性
        
        Args:
            result: 比赛结果
            
        Returns:
            是否有效
        """
        # 验证比分
        if result.home_score < 0 or result.away_score < 0:
            return False
        if result.home_score > 200 or result.away_score > 200:
            return False
        if result.home_score == result.away_score:
            return False  # 篮球比赛不能平局
        
        # 验证球员统计
        for player_id, stats in result.player_stats.items():
            if stats.points < 0 or stats.rebounds < 0 or stats.assists < 0:
                return False
            if stats.minutes < 0 or stats.minutes > 48:
                return False
            if stats.steals < 0 or stats.blocks < 0 or stats.turnovers < 0:
                return False
        
        return True
    
    def get_player_season_stats(self, player_id: str) -> Optional[Dict]:
        """
        获取球员的赛季统计数据
        
        Args:
            player_id: 球员ID
            
        Returns:
            包含场均数据和累计数据的字典，球员不存在则返回None
        """
        if not self.data_manager:
            return None
        
        player = self.data_manager.get_player(player_id)
        if not player:
            return None
        
        return {
            "games_played": player.games_played,
            "averages": {
                "points": round(player.avg_points, 1),
                "rebounds": round(player.avg_rebounds, 1),
                "assists": round(player.avg_assists, 1),
                "steals": round(player.avg_steals, 1),
                "blocks": round(player.avg_blocks, 1),
                "turnovers": round(player.avg_turnovers, 1),
                "minutes": round(player.avg_minutes, 1)
            },
            "totals": {
                "points": player.total_points,
                "rebounds": player.total_rebounds,
                "assists": player.total_assists,
                "steals": player.total_steals,
                "blocks": player.total_blocks,
                "turnovers": player.total_turnovers,
                "minutes": player.total_minutes
            }
        }
    
    def reset_player_season_stats(self, player_id: str) -> bool:
        """
        重置球员的赛季统计数据（用于新赛季开始）
        
        Args:
            player_id: 球员ID
            
        Returns:
            是否重置成功
        """
        if not self.data_manager:
            return False
        
        player = self.data_manager.get_player(player_id)
        if not player:
            return False
        
        # 重置累计数据
        player.total_points = 0
        player.total_rebounds = 0
        player.total_assists = 0
        player.total_steals = 0
        player.total_blocks = 0
        player.total_turnovers = 0
        player.total_minutes = 0
        player.games_played = 0
        
        # 重置场均数据
        player.avg_points = 0.0
        player.avg_rebounds = 0.0
        player.avg_assists = 0.0
        player.avg_steals = 0.0
        player.avg_blocks = 0.0
        player.avg_turnovers = 0.0
        player.avg_minutes = 0.0
        
        return True
    
    def reset_all_season_stats(self) -> int:
        """
        重置所有球员的赛季统计数据
        
        Returns:
            重置的球员数量
        """
        if not self.data_manager:
            return 0
        
        count = 0
        for player in self.data_manager.get_all_players():
            if self.reset_player_season_stats(player.id):
                count += 1
        
        return count

    def process_daily_recovery(
        self,
        players: Dict[str, Player],
        days_passed: int = 1
    ) -> List[Player]:
        """
        处理日期推进时的球员恢复
        
        在日期推进时调用，减少受伤球员的恢复天数
        
        Args:
            players: 球员字典 {player_id: Player}
            days_passed: 经过的天数（默认1天）
            
        Returns:
            本次恢复健康的球员列表
        """
        all_players = list(players.values())
        return self.injury_system.recover_players(all_players, days_passed)
    
    def get_team_injury_report(
        self,
        team: Team,
        players: Dict[str, Player]
    ) -> str:
        """
        获取球队伤病报告
        
        Args:
            team: 球队对象
            players: 球员字典
            
        Returns:
            格式化的伤病报告字符串
        """
        return self.injury_system.get_injury_report(team, players)
    
    def get_available_players(
        self,
        team: Team,
        players: Dict[str, Player]
    ) -> List[Player]:
        """
        获取球队可用（健康）的球员
        
        Args:
            team: 球队对象
            players: 球员字典
            
        Returns:
            健康球员列表
        """
        return self.injury_system.get_healthy_players(team, players)
    
    def get_injured_players(
        self,
        team: Team,
        players: Dict[str, Player]
    ) -> List[Player]:
        """
        获取球队受伤的球员
        
        Args:
            team: 球队对象
            players: 球员字典
            
        Returns:
            受伤球员列表
        """
        return self.injury_system.get_injured_players(team, players)
