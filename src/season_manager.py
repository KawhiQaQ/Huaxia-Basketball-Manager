"""
华夏篮球联赛教练模拟器 - 赛季管理器

负责赛程安排、排行榜管理和赛季进度控制
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from src.models import Team, Standing, ScheduledGame, PlayoffSeries, Player


# 华夏篮球联赛常规赛配置
REGULAR_SEASON_GAMES = 42  # 每队常规赛场次
SEASON_START_DATE = "2024-10-15"  # 赛季开始日期


class SeasonManager:
    """赛季管理器"""
    
    def __init__(self, teams: List[Team]):
        """
        初始化赛季管理器
        
        Args:
            teams: 球队列表
        """
        self.teams = {team.id: team for team in teams}
        self.team_ids = list(self.teams.keys())
        self.standings: Dict[str, Standing] = {}
        self.schedule: List[ScheduledGame] = []
        self.playoff_bracket: Dict[str, PlayoffSeries] = {}
        self.current_date = SEASON_START_DATE
        
        # 初始化排行榜
        self._init_standings()
    
    def _init_standings(self) -> None:
        """初始化所有球队的排行榜数据"""
        for team_id in self.team_ids:
            self.standings[team_id] = Standing(team_id=team_id)
    
    def generate_schedule(self, start_date: str = SEASON_START_DATE) -> List[ScheduledGame]:
        """
        生成42场常规赛赛程（分组赛制）
        
        华夏篮球联赛有20支球队，分为4组，每组5队：
        - 同组对手：4队 × 3场 = 12场
        - 异组对手：15队 × 2场 = 30场
        - 总计：42场
        
        确保每队每天最多只有一场比赛（Requirements 4.1, 4.2）
        
        Args:
            start_date: 赛季开始日期 (YYYY-MM-DD格式)
            
        Returns:
            赛程列表
        """
        self.schedule = []
        num_teams = len(self.team_ids)
        
        if num_teams < 2:
            return self.schedule
        
        # 将20支球队分为4组，每组5队
        groups = self._create_groups()
        
        # 生成所有比赛配对
        all_matchups = self._generate_group_matchups(groups)
        
        # 打乱比赛顺序
        random.shuffle(all_matchups)
        
        # 分配比赛日期 - 使用冲突检测确保每队每天最多一场比赛
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        # 跟踪每个日期已安排比赛的球队
        date_team_games: Dict[str, set] = {}
        
        for home_id, away_id in all_matchups:
            # 找到一个两队都没有比赛的日期
            game_date = self._find_available_date(
                current_date, home_id, away_id, date_team_games
            )
            
            date_str = game_date.strftime("%Y-%m-%d")
            
            # 记录该日期这两队已有比赛
            if date_str not in date_team_games:
                date_team_games[date_str] = set()
            date_team_games[date_str].add(home_id)
            date_team_games[date_str].add(away_id)
            
            # 创建比赛
            game = ScheduledGame(
                date=date_str,
                home_team_id=home_id,
                away_team_id=away_id
            )
            self.schedule.append(game)
        
        # 按日期排序
        self.schedule.sort(key=lambda g: g.date)
        
        return self.schedule
    
    def _create_groups(self) -> List[List[str]]:
        """
        将球队分为4组，每组5队
        
        Returns:
            4个组的列表，每组包含5个球队ID
        """
        team_list = list(self.team_ids)
        random.shuffle(team_list)
        
        groups = []
        group_size = 5
        for i in range(0, len(team_list), group_size):
            groups.append(team_list[i:i + group_size])
        
        return groups
    
    def _generate_group_matchups(self, groups: List[List[str]]) -> List[Tuple[str, str]]:
        """
        根据分组生成所有比赛配对
        
        同组对手：4队 × 3场 = 12场（2主1客或1主2客）
        异组对手：15队 × 2场 = 30场（1主1客）
        
        Args:
            groups: 4个组的列表
            
        Returns:
            所有比赛配对列表 (home_id, away_id)
        """
        all_matchups = []
        
        # 为每个球队记录其所在组
        team_to_group = {}
        for group_idx, group in enumerate(groups):
            for team_id in group:
                team_to_group[team_id] = group_idx
        
        # 生成同组比赛（每对打3场）
        for group in groups:
            for i, team1 in enumerate(group):
                for team2 in group[i+1:]:
                    # 每对同组球队打3场：随机分配主客场（2主1客或1主2客）
                    if random.random() < 0.5:
                        # team1 2主1客
                        all_matchups.append((team1, team2))  # team1主场
                        all_matchups.append((team1, team2))  # team1主场
                        all_matchups.append((team2, team1))  # team2主场
                    else:
                        # team1 1主2客
                        all_matchups.append((team1, team2))  # team1主场
                        all_matchups.append((team2, team1))  # team2主场
                        all_matchups.append((team2, team1))  # team2主场
        
        # 生成异组比赛（每对打2场，主客各1场）
        all_teams = list(self.team_ids)
        for i, team1 in enumerate(all_teams):
            for team2 in all_teams[i+1:]:
                # 只处理不同组的球队
                if team_to_group[team1] != team_to_group[team2]:
                    all_matchups.append((team1, team2))  # team1主场
                    all_matchups.append((team2, team1))  # team2主场
        
        return all_matchups
    
    def generate_alternating_schedule(self, start_date: str = SEASON_START_DATE) -> List[ScheduledGame]:
        """
        生成交替赛程（分组赛制）- 确保球队隔天比赛
        
        华夏篮球联赛有20支球队，分为4组，每组5队：
        - 同组对手：4队 × 3场 = 12场
        - 异组对手：15队 × 2场 = 30场
        - 总计：42场
        
        实现Requirements 8.1-8.5:
        - 每队大约隔天比赛一次
        - 没有球队连续比赛超过2天
        - 偶尔安排2天休息以增加变化
        - 第一天10队5场，第二天另外10队5场
        - 通过变化避免同样10队总在同一天比赛
        
        Args:
            start_date: 赛季开始日期 (YYYY-MM-DD格式)
            
        Returns:
            赛程列表
        """
        self.schedule = []
        num_teams = len(self.team_ids)
        
        if num_teams < 2:
            return self.schedule
        
        # 将20支球队分为4组，每组5队
        groups = self._create_groups()
        
        # 生成所有比赛配对
        all_matchups = self._generate_group_matchups(groups)
        
        # 打乱比赛顺序
        random.shuffle(all_matchups)
        
        # 使用交替分配方法
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.schedule = self._distribute_games_alternating(all_matchups, current_date)
        
        # 按日期排序
        self.schedule.sort(key=lambda g: g.date)
        
        return self.schedule
    
    def _distribute_games_alternating(
        self,
        all_matchups: List[Tuple[str, str]],
        start_date: datetime
    ) -> List[ScheduledGame]:
        """
        交替分配比赛日期 - 严格控制背靠背，增加休息变化
        
        目标：
        - 0背靠背（连续两天比赛）
        - 大部分隔1天比赛
        - 少量隔2-3天比赛增加真实感
        
        Args:
            all_matchups: 所有比赛配对列表
            start_date: 开始日期
            
        Returns:
            赛程列表
        """
        schedule = []
        
        # 跟踪每个球队的比赛日期
        team_game_dates: Dict[str, List[datetime]] = {team_id: [] for team_id in self.team_ids}
        
        # 跟踪每个日期已安排比赛的球队
        date_team_games: Dict[str, set] = {}
        
        # 打乱比赛顺序
        remaining_games = list(all_matchups)
        random.shuffle(remaining_games)
        
        # 按天安排比赛
        current_date = start_date
        games_per_day = 5  # 每天5场比赛（10队参赛）
        
        day_counter = 0
        max_days = 500
        stuck_counter = 0
        
        while remaining_games and day_counter < max_days:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in date_team_games:
                date_team_games[date_str] = set()
            
            games_scheduled_today = 0
            still_remaining = []
            
            # 逐步放宽约束
            relax_level = stuck_counter // 30
            
            for home_id, away_id in remaining_games:
                if games_scheduled_today >= games_per_day:
                    still_remaining.append((home_id, away_id))
                    continue
                
                # 检查当天是否已有比赛
                teams_on_date = date_team_games.get(date_str, set())
                if home_id in teams_on_date or away_id in teams_on_date:
                    still_remaining.append((home_id, away_id))
                    continue
                
                # 严格禁止背靠背
                home_would_b2b = self._would_create_back_to_back(home_id, current_date, team_game_dates)
                away_would_b2b = self._would_create_back_to_back(away_id, current_date, team_game_dates)
                
                if home_would_b2b or away_would_b2b:
                    still_remaining.append((home_id, away_id))
                    continue
                
                # 安排比赛
                self._record_game(home_id, away_id, current_date, team_game_dates, date_team_games)
                schedule.append(ScheduledGame(
                    date=date_str,
                    home_team_id=home_id,
                    away_team_id=away_id
                ))
                games_scheduled_today += 1
            
            # 检查是否有进展
            if len(still_remaining) == len(remaining_games):
                stuck_counter += 1
            else:
                stuck_counter = 0
            
            remaining_games = still_remaining
            current_date += timedelta(days=1)
            day_counter += 1
        
        # 强制安排剩余比赛（仍然禁止背靠背）
        for home_id, away_id in remaining_games:
            game_date = self._find_non_b2b_date(
                current_date, home_id, away_id, team_game_dates, date_team_games
            )
            date_str = game_date.strftime("%Y-%m-%d")
            if date_str not in date_team_games:
                date_team_games[date_str] = set()
            date_team_games[date_str].add(home_id)
            date_team_games[date_str].add(away_id)
            team_game_dates[home_id].append(game_date)
            team_game_dates[away_id].append(game_date)
            schedule.append(ScheduledGame(
                date=date_str,
                home_team_id=home_id,
                away_team_id=away_id
            ))
        
        # 添加休息日变化（隔2-3天）
        schedule = self._add_rest_day_variation(schedule)
        
        return schedule
    
    def _find_non_b2b_date(
        self,
        start_date: datetime,
        team1_id: str,
        team2_id: str,
        team_game_dates: Dict[str, List[datetime]],
        date_team_games: Dict[str, set]
    ) -> datetime:
        """
        找到一个不会产生背靠背的可用日期
        """
        current_date = start_date
        max_days = 365
        
        for _ in range(max_days):
            date_str = current_date.strftime("%Y-%m-%d")
            teams_on_date = date_team_games.get(date_str, set())
            
            if team1_id not in teams_on_date and team2_id not in teams_on_date:
                # 检查背靠背
                if not self._would_create_back_to_back(team1_id, current_date, team_game_dates) and \
                   not self._would_create_back_to_back(team2_id, current_date, team_game_dates):
                    return current_date
            
            current_date += timedelta(days=1)
        
        return current_date
    
    def _add_rest_day_variation(self, schedule: List[ScheduledGame]) -> List[ScheduledGame]:
        """
        添加休息日变化 - 将部分比赛推迟1-2天，创造隔2-3天的休息
        
        目标：约20-30%的比赛间隔为2-3天
        """
        if not schedule:
            return schedule
        
        # 重建team_game_dates
        team_game_dates: Dict[str, List[datetime]] = {team_id: [] for team_id in self.team_ids}
        for game in schedule:
            game_date = datetime.strptime(game.date, "%Y-%m-%d")
            team_game_dates[game.home_team_id].append(game_date)
            team_game_dates[game.away_team_id].append(game_date)
        
        # 对每个球队的比赛日期排序
        for team_id in team_game_dates:
            team_game_dates[team_id].sort()
        
        # 重建date_team_games
        date_team_games: Dict[str, set] = {}
        for game in schedule:
            if game.date not in date_team_games:
                date_team_games[game.date] = set()
            date_team_games[game.date].add(game.home_team_id)
            date_team_games[game.date].add(game.away_team_id)
        
        # 随机选择约15%的比赛进行日期调整
        adjusted_schedule = list(schedule)
        num_adjustments = len(schedule) // 7  # 约15%
        games_to_adjust = random.sample(range(len(schedule)), min(num_adjustments, len(schedule)))
        
        for idx in games_to_adjust:
            game = adjusted_schedule[idx]
            original_date = datetime.strptime(game.date, "%Y-%m-%d")
            
            # 尝试推迟1-2天
            for delay in [1, 2]:
                new_date = original_date + timedelta(days=delay)
                new_date_str = new_date.strftime("%Y-%m-%d")
                
                # 检查新日期是否可行
                teams_on_new_date = date_team_games.get(new_date_str, set())
                if game.home_team_id in teams_on_new_date or game.away_team_id in teams_on_new_date:
                    continue
                
                # 检查是否会产生背靠背
                # 临时移除原日期
                temp_home_dates = [d for d in team_game_dates[game.home_team_id] if d != original_date]
                temp_away_dates = [d for d in team_game_dates[game.away_team_id] if d != original_date]
                temp_home_dates.append(new_date)
                temp_away_dates.append(new_date)
                temp_home_dates.sort()
                temp_away_dates.sort()
                
                # 检查背靠背
                home_has_b2b = self._has_back_to_back(temp_home_dates)
                away_has_b2b = self._has_back_to_back(temp_away_dates)
                
                if not home_has_b2b and not away_has_b2b:
                    # 更新date_team_games
                    if game.date in date_team_games:
                        date_team_games[game.date].discard(game.home_team_id)
                        date_team_games[game.date].discard(game.away_team_id)
                    
                    if new_date_str not in date_team_games:
                        date_team_games[new_date_str] = set()
                    date_team_games[new_date_str].add(game.home_team_id)
                    date_team_games[new_date_str].add(game.away_team_id)
                    
                    # 更新team_game_dates
                    team_game_dates[game.home_team_id] = temp_home_dates
                    team_game_dates[game.away_team_id] = temp_away_dates
                    
                    # 更新比赛日期
                    game.date = new_date_str
                    break
        
        return adjusted_schedule
    
    def _has_back_to_back(self, dates: List[datetime]) -> bool:
        """检查日期列表中是否有背靠背"""
        if len(dates) < 2:
            return False
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                return True
        return False
    
    def _would_create_back_to_back(
        self,
        team_id: str,
        new_date: datetime,
        team_game_dates: Dict[str, List[datetime]]
    ) -> bool:
        """
        检查在指定日期安排比赛是否会产生背靠背
        
        Args:
            team_id: 球队ID
            new_date: 新比赛日期
            team_game_dates: 每个球队的比赛日期列表
            
        Returns:
            是否会产生背靠背
        """
        if team_id not in team_game_dates:
            return False
        
        existing_dates = team_game_dates[team_id]
        if not existing_dates:
            return False
        
        yesterday = new_date - timedelta(days=1)
        tomorrow = new_date + timedelta(days=1)
        
        for game_date in existing_dates:
            if game_date == yesterday or game_date == tomorrow:
                return True
        
        return False
    
    def _can_schedule_game(
        self,
        team1_id: str,
        team2_id: str,
        game_date: datetime,
        team_game_dates: Dict[str, List[datetime]],
        date_team_games: Dict[str, set]
    ) -> bool:
        """
        检查是否可以在指定日期安排比赛
        
        Args:
            team1_id: 球队1 ID
            team2_id: 球队2 ID
            game_date: 比赛日期
            team_game_dates: 每个球队的比赛日期列表
            date_team_games: 每个日期已安排比赛的球队集合
            
        Returns:
            是否可以安排
        """
        date_str = game_date.strftime("%Y-%m-%d")
        teams_on_date = date_team_games.get(date_str, set())
        
        # 检查当天是否已有比赛
        if team1_id in teams_on_date or team2_id in teams_on_date:
            return False
        
        # 检查是否会超过连续比赛限制
        if self._would_exceed_consecutive_days(team1_id, game_date, team_game_dates, max_consecutive=2):
            return False
        if self._would_exceed_consecutive_days(team2_id, game_date, team_game_dates, max_consecutive=2):
            return False
        
        return True
    
    def _record_game(
        self,
        team1_id: str,
        team2_id: str,
        game_date: datetime,
        team_game_dates: Dict[str, List[datetime]],
        date_team_games: Dict[str, set]
    ) -> None:
        """
        记录比赛安排
        
        Args:
            team1_id: 球队1 ID
            team2_id: 球队2 ID
            game_date: 比赛日期
            team_game_dates: 每个球队的比赛日期列表
            date_team_games: 每个日期已安排比赛的球队集合
        """
        date_str = game_date.strftime("%Y-%m-%d")
        
        if date_str not in date_team_games:
            date_team_games[date_str] = set()
        
        date_team_games[date_str].add(team1_id)
        date_team_games[date_str].add(team2_id)
        team_game_dates[team1_id].append(game_date)
        team_game_dates[team2_id].append(game_date)
    
    def _find_alternating_date(
        self,
        start_date: datetime,
        team1_id: str,
        team2_id: str,
        team_game_dates: Dict[str, List[datetime]],
        date_team_games: Dict[str, set],
        preferred_group: Optional[set] = None
    ) -> datetime:
        """
        找到符合交替规则的可用日期
        
        确保:
        - 两队在该日期都没有比赛
        - 默认至少隔一天比赛（休息日）
        - 没有球队连续比赛超过2天
        
        Args:
            start_date: 开始搜索的日期
            team1_id: 球队1 ID
            team2_id: 球队2 ID
            team_game_dates: 每个球队的比赛日期列表
            date_team_games: 每个日期已安排比赛的球队集合
            preferred_group: 优先安排的球队组（用于保持组别交替）
            
        Returns:
            可用的比赛日期
        """
        current_date = start_date
        max_days_to_search = 365
        
        for _ in range(max_days_to_search):
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 检查该日期是否有冲突
            teams_on_date = date_team_games.get(date_str, set())
            
            if team1_id not in teams_on_date and team2_id not in teams_on_date:
                # 检查两队是否都至少休息了一天（默认隔天比赛）
                team1_rested = self._has_rest_day(team1_id, current_date, team_game_dates)
                team2_rested = self._has_rest_day(team2_id, current_date, team_game_dates)
                
                # 检查是否会导致连续3天比赛
                team1_no_exceed = not self._would_exceed_consecutive_days(
                    team1_id, current_date, team_game_dates, max_consecutive=2
                )
                team2_no_exceed = not self._would_exceed_consecutive_days(
                    team2_id, current_date, team_game_dates, max_consecutive=2
                )
                
                # 优先选择两队都休息过的日期
                if team1_rested and team2_rested and team1_no_exceed and team2_no_exceed:
                    return current_date
            
            current_date += timedelta(days=1)
        
        # 如果找不到理想日期，放宽条件（允许背靠背但不超过2天连续）
        current_date = start_date
        for _ in range(max_days_to_search):
            date_str = current_date.strftime("%Y-%m-%d")
            teams_on_date = date_team_games.get(date_str, set())
            
            if team1_id not in teams_on_date and team2_id not in teams_on_date:
                if not self._would_exceed_consecutive_days(
                    team1_id, current_date, team_game_dates, max_consecutive=2
                ) and not self._would_exceed_consecutive_days(
                    team2_id, current_date, team_game_dates, max_consecutive=2
                ):
                    return current_date
            
            current_date += timedelta(days=1)
        
        return current_date
    
    def _has_rest_day(
        self,
        team_id: str,
        new_date: datetime,
        team_game_dates: Dict[str, List[datetime]]
    ) -> bool:
        """
        检查球队在新比赛日期前是否至少休息了一天
        
        Args:
            team_id: 球队ID
            new_date: 新比赛日期
            team_game_dates: 每个球队的比赛日期列表
            
        Returns:
            是否至少休息了一天
        """
        if team_id not in team_game_dates:
            return True
        
        existing_dates = team_game_dates[team_id]
        if not existing_dates:
            return True
        
        # 检查前一天是否有比赛
        yesterday = new_date - timedelta(days=1)
        for game_date in existing_dates:
            if game_date == yesterday:
                return False  # 前一天有比赛，没有休息
        
        return True
    
    def _would_exceed_consecutive_days(
        self,
        team_id: str,
        new_date: datetime,
        team_game_dates: Dict[str, List[datetime]],
        max_consecutive: int = 2
    ) -> bool:
        """
        检查添加新比赛日期是否会导致超过最大连续比赛天数
        
        Args:
            team_id: 球队ID
            new_date: 新比赛日期
            team_game_dates: 每个球队的比赛日期列表
            max_consecutive: 最大允许连续天数
            
        Returns:
            是否会超过限制
        """
        if team_id not in team_game_dates:
            return False
        
        existing_dates = team_game_dates[team_id]
        if not existing_dates:
            return False
        
        # 将新日期加入临时列表进行检查
        all_dates = sorted(existing_dates + [new_date])
        
        # 检查连续天数
        consecutive = 1
        for i in range(1, len(all_dates)):
            if (all_dates[i] - all_dates[i-1]).days == 1:
                consecutive += 1
                if consecutive > max_consecutive:
                    return True
            else:
                consecutive = 1
        
        return False
    
    def _add_schedule_variation(self, schedule: List[ScheduledGame]) -> List[ScheduledGame]:
        """
        添加赛程变化
        
        偶尔安排背靠背或休息两天，避免过于规律
        
        Args:
            schedule: 原始赛程
            
        Returns:
            调整后的赛程
        """
        if not schedule:
            return schedule
        
        # 重新构建team_game_dates用于验证
        team_game_dates: Dict[str, List[datetime]] = {team_id: [] for team_id in self.team_ids}
        
        for game in schedule:
            game_date = datetime.strptime(game.date, "%Y-%m-%d")
            team_game_dates[game.home_team_id].append(game_date)
            team_game_dates[game.away_team_id].append(game_date)
        
        # 对每个球队的比赛日期排序
        for team_id in team_game_dates:
            team_game_dates[team_id].sort()
        
        # 随机选择一些比赛进行日期调整（约10%的比赛）
        num_adjustments = max(1, len(schedule) // 10)
        games_to_adjust = random.sample(range(len(schedule)), min(num_adjustments, len(schedule)))
        
        adjusted_schedule = list(schedule)
        date_team_games: Dict[str, set] = {}
        
        # 重建date_team_games
        for game in adjusted_schedule:
            if game.date not in date_team_games:
                date_team_games[game.date] = set()
            date_team_games[game.date].add(game.home_team_id)
            date_team_games[game.date].add(game.away_team_id)
        
        for idx in games_to_adjust:
            game = adjusted_schedule[idx]
            original_date = datetime.strptime(game.date, "%Y-%m-%d")
            
            # 随机决定调整方向：提前1天或推迟1天
            adjustment = random.choice([-1, 1])
            new_date = original_date + timedelta(days=adjustment)
            new_date_str = new_date.strftime("%Y-%m-%d")
            
            # 检查新日期是否可行
            teams_on_new_date = date_team_games.get(new_date_str, set())
            
            if (game.home_team_id not in teams_on_new_date and 
                game.away_team_id not in teams_on_new_date):
                
                # 临时更新team_game_dates进行验证
                temp_home_dates = [d for d in team_game_dates[game.home_team_id] if d != original_date]
                temp_away_dates = [d for d in team_game_dates[game.away_team_id] if d != original_date]
                temp_home_dates.append(new_date)
                temp_away_dates.append(new_date)
                temp_home_dates.sort()
                temp_away_dates.sort()
                
                # 检查是否会导致连续3天比赛
                home_ok = self._check_consecutive_days(temp_home_dates, max_consecutive=2)
                away_ok = self._check_consecutive_days(temp_away_dates, max_consecutive=2)
                
                if home_ok and away_ok:
                    # 更新date_team_games
                    if game.date in date_team_games:
                        date_team_games[game.date].discard(game.home_team_id)
                        date_team_games[game.date].discard(game.away_team_id)
                    
                    if new_date_str not in date_team_games:
                        date_team_games[new_date_str] = set()
                    date_team_games[new_date_str].add(game.home_team_id)
                    date_team_games[new_date_str].add(game.away_team_id)
                    
                    # 更新team_game_dates
                    team_game_dates[game.home_team_id] = temp_home_dates
                    team_game_dates[game.away_team_id] = temp_away_dates
                    
                    # 更新比赛日期
                    game.date = new_date_str
        
        return adjusted_schedule
    
    def _check_consecutive_days(self, dates: List[datetime], max_consecutive: int = 2) -> bool:
        """
        检查日期列表中是否有超过最大连续天数的情况
        
        Args:
            dates: 排序后的日期列表
            max_consecutive: 最大允许连续天数
            
        Returns:
            True表示没有超过限制，False表示超过了
        """
        if len(dates) <= 1:
            return True
        
        consecutive = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                consecutive += 1
                if consecutive > max_consecutive:
                    return False
            else:
                consecutive = 1
        
        return True
    
    def _find_available_date(
        self,
        start_date: datetime,
        team1_id: str,
        team2_id: str,
        date_team_games: Dict[str, set]
    ) -> datetime:
        """
        找到一个两队都没有比赛的可用日期
        
        Args:
            start_date: 开始搜索的日期
            team1_id: 球队1 ID
            team2_id: 球队2 ID
            date_team_games: 每个日期已安排比赛的球队集合
            
        Returns:
            可用的比赛日期
        """
        current_date = start_date
        max_days_to_search = 365  # 最多搜索一年
        
        for _ in range(max_days_to_search):
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 检查该日期是否有冲突
            if date_str not in date_team_games:
                # 该日期还没有任何比赛，可以使用
                return current_date
            
            teams_on_date = date_team_games[date_str]
            if team1_id not in teams_on_date and team2_id not in teams_on_date:
                # 两队在该日期都没有比赛，可以使用
                return current_date
            
            # 有冲突，尝试下一天
            current_date += timedelta(days=1)
        
        # 如果找不到可用日期（理论上不应该发生），返回当前日期
        return current_date
    
    def _validate_schedule(self) -> Tuple[bool, List[Dict]]:
        """
        验证生成的赛程无冲突（每队每天最多一场比赛）
        
        Returns:
            (is_valid, conflicts) 元组
            - is_valid: 赛程是否有效（无冲突）
            - conflicts: 冲突列表，每个冲突包含 {date, team_id, games}
        """
        conflicts = []
        
        # 按日期和球队统计比赛
        date_team_games: Dict[str, Dict[str, List[ScheduledGame]]] = {}
        
        for game in self.schedule:
            date = game.date
            if date not in date_team_games:
                date_team_games[date] = {}
            
            # 记录主队比赛
            if game.home_team_id not in date_team_games[date]:
                date_team_games[date][game.home_team_id] = []
            date_team_games[date][game.home_team_id].append(game)
            
            # 记录客队比赛
            if game.away_team_id not in date_team_games[date]:
                date_team_games[date][game.away_team_id] = []
            date_team_games[date][game.away_team_id].append(game)
        
        # 检查每个日期每支球队是否只有一场比赛
        for date, teams in date_team_games.items():
            for team_id, games in teams.items():
                if len(games) > 1:
                    conflicts.append({
                        "date": date,
                        "team_id": team_id,
                        "games": games,
                        "game_count": len(games)
                    })
        
        is_valid = len(conflicts) == 0
        return is_valid, conflicts

    def get_games_for_date(self, date: str) -> List[ScheduledGame]:
        """
        获取指定日期的比赛
        
        Args:
            date: 日期字符串 (YYYY-MM-DD格式)
            
        Returns:
            当日比赛列表
        """
        return [game for game in self.schedule if game.date == date and not game.is_played]
    
    def get_team_games_count(self, team_id: str) -> int:
        """
        获取指定球队的总比赛场次
        
        Args:
            team_id: 球队ID
            
        Returns:
            比赛场次
        """
        count = 0
        for game in self.schedule:
            if game.home_team_id == team_id or game.away_team_id == team_id:
                count += 1
        return count
    
    def get_team_remaining_games(self, team_id: str) -> List[ScheduledGame]:
        """
        获取指定球队的剩余比赛
        
        Args:
            team_id: 球队ID
            
        Returns:
            剩余比赛列表
        """
        return [
            game for game in self.schedule
            if (game.home_team_id == team_id or game.away_team_id == team_id)
            and not game.is_played
        ]
    
    def mark_game_played(self, game: ScheduledGame) -> None:
        """
        标记比赛已完成
        
        Args:
            game: 比赛对象
        """
        game.is_played = True

    def update_standings(self, home_team_id: str, away_team_id: str, 
                         home_score: int, away_score: int) -> None:
        """
        根据比赛结果更新排行榜
        
        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_score: 主队得分
            away_score: 客队得分
        """
        # 确保两队都在排行榜中
        if home_team_id not in self.standings:
            self.standings[home_team_id] = Standing(team_id=home_team_id)
        if away_team_id not in self.standings:
            self.standings[away_team_id] = Standing(team_id=away_team_id)
        
        home_standing = self.standings[home_team_id]
        away_standing = self.standings[away_team_id]
        
        # 更新胜负场次
        if home_score > away_score:
            home_standing.wins += 1
            away_standing.losses += 1
        else:
            away_standing.wins += 1
            home_standing.losses += 1
        
        # 更新胜率
        home_standing.update_win_pct()
        away_standing.update_win_pct()
        
        # 更新落后场次
        self._update_games_behind()
    
    def _update_games_behind(self) -> None:
        """更新所有球队的落后场次"""
        if not self.standings:
            return
        
        # 找到领先者的胜率
        sorted_standings = self.get_standings()
        if not sorted_standings:
            return
        
        leader = sorted_standings[0]
        leader_wins = leader.wins
        leader_losses = leader.losses
        
        for standing in self.standings.values():
            # 落后场次 = (领先者胜场 - 本队胜场 + 本队负场 - 领先者负场) / 2
            standing.games_behind = (
                (leader_wins - standing.wins) + (standing.losses - leader_losses)
            ) / 2
    
    def get_standings(self) -> List[Standing]:
        """
        获取排行榜（按胜率降序排列）
        
        Returns:
            排序后的排名列表
        """
        standings_list = list(self.standings.values())
        
        # 按胜率降序排序，胜率相同则按胜场数降序
        standings_list.sort(key=lambda s: (s.win_pct, s.wins), reverse=True)
        
        return standings_list
    
    def get_team_standing(self, team_id: str) -> Optional[Standing]:
        """
        获取指定球队的排名数据
        
        Args:
            team_id: 球队ID
            
        Returns:
            排名数据，不存在则返回None
        """
        return self.standings.get(team_id)
    
    def get_team_rank(self, team_id: str) -> int:
        """
        获取指定球队的排名位置
        
        Args:
            team_id: 球队ID
            
        Returns:
            排名位置（1-20），不存在则返回-1
        """
        standings = self.get_standings()
        for i, standing in enumerate(standings):
            if standing.team_id == team_id:
                return i + 1
        return -1
    
    def is_regular_season_over(self) -> bool:
        """
        检查常规赛是否结束
        
        Returns:
            是否结束
        """
        # 检查是否所有比赛都已完成
        for game in self.schedule:
            if not game.is_played:
                return False
        return len(self.schedule) > 0
    
    def get_playoff_teams(self) -> List[str]:
        """
        获取进入季后赛的球队（前12名）
        
        Returns:
            球队ID列表，按排名排序
        """
        standings = self.get_standings()
        return [s.team_id for s in standings[:12]]
    
    def get_schedule_dates(self) -> List[str]:
        """
        获取所有比赛日期
        
        Returns:
            日期列表（去重且排序）
        """
        dates = set()
        for game in self.schedule:
            dates.add(game.date)
        return sorted(list(dates))
    
    def is_match_day(self, date: str) -> bool:
        """
        检查指定日期是否为比赛日
        
        Args:
            date: 日期字符串
            
        Returns:
            是否为比赛日
        """
        return len(self.get_games_for_date(date)) > 0
    
    def get_next_game_date(self, current_date: str) -> Optional[str]:
        """
        获取下一个比赛日
        
        Args:
            current_date: 当前日期
            
        Returns:
            下一个比赛日，没有则返回None
        """
        for game in self.schedule:
            if game.date > current_date and not game.is_played:
                return game.date
        return None
    
    def get_season_progress(self) -> Tuple[int, int]:
        """
        获取赛季进度
        
        Returns:
            (已完成比赛数, 总比赛数) 元组
        """
        played = sum(1 for game in self.schedule if game.is_played)
        total = len(self.schedule)
        return played, total
    
    def init_playoffs(self) -> Dict[str, PlayoffSeries]:
        """
        初始化季后赛对阵
        
        华夏篮球联赛季后赛规则：
        - 前12名进入季后赛
        - 1-4名直接进入8强（四分之一决赛）
        - 5-12名进入附加赛（play-in），争夺4个8强名额
        - 附加赛采用best-of-3赛制
        - 四分之一决赛、半决赛、总决赛采用best-of-7赛制
        
        附加赛对阵：
        - 5 vs 12, 6 vs 11, 7 vs 10, 8 vs 9
        
        Returns:
            季后赛对阵字典
        """
        self.playoff_bracket = {}
        
        # 获取排名前12的球队
        standings = self.get_standings()
        if len(standings) < 12:
            return self.playoff_bracket
        
        playoff_teams = [s.team_id for s in standings[:12]]
        
        # 1-4名直接进入8强，存储为待定对阵
        # 他们将在附加赛结束后与附加赛胜者配对
        self.playoff_bracket["quarter_seed_1"] = playoff_teams[0]  # 第1名
        self.playoff_bracket["quarter_seed_2"] = playoff_teams[1]  # 第2名
        self.playoff_bracket["quarter_seed_3"] = playoff_teams[2]  # 第3名
        self.playoff_bracket["quarter_seed_4"] = playoff_teams[3]  # 第4名
        
        # 5-12名进入附加赛 (best-of-3)
        # 对阵: 5 vs 12, 6 vs 11, 7 vs 10, 8 vs 9
        play_in_matchups = [
            (playoff_teams[4], playoff_teams[11]),   # 5 vs 12
            (playoff_teams[5], playoff_teams[10]),   # 6 vs 11
            (playoff_teams[6], playoff_teams[9]),    # 7 vs 10
            (playoff_teams[7], playoff_teams[8]),    # 8 vs 9
        ]
        
        for i, (team1, team2) in enumerate(play_in_matchups):
            series_id = f"play_in_{i+1}"
            self.playoff_bracket[series_id] = PlayoffSeries(
                team1_id=team1,
                team2_id=team2,
                team1_wins=0,
                team2_wins=0,
                round_name="play_in"
            )
        
        return self.playoff_bracket
    
    def adjust_ai_players_for_playoffs(
        self,
        players: Dict[str, Player],
        teams: Dict[str, Team],
        calculate_overall_func
    ) -> Dict[str, int]:
        """
        在常规赛结束进入季后赛时，随机调整AI球队球员的能力值
        
        Requirements: 3.5
        - 调整范围: -2 到 +2
        - 只调整AI控制球队的球员
        - 调整后重新计算总评
        
        Args:
            players: 球员字典 {player_id: Player}
            teams: 球队字典 {team_id: Team}
            calculate_overall_func: 计算总评的函数
            
        Returns:
            调整记录字典 {player_id: adjustment_value}
        """
        adjustments = {}
        
        # 获取所有AI控制的球队ID
        ai_team_ids = {
            team_id for team_id, team in teams.items()
            if not team.is_player_controlled
        }
        
        # 遍历所有球员，调整AI球队球员的能力值
        for player_id, player in players.items():
            # 只调整AI球队的球员
            if player.team_id not in ai_team_ids:
                continue
            
            # 随机调整总评 (-2 到 +2)，不改变各项属性
            adjustment = random.randint(-2, 2)
            
            if adjustment == 0:
                continue
            
            player.overall = max(0, min(99, player.overall + adjustment))
            
            # 记录调整
            adjustments[player_id] = adjustment
        
        return adjustments
    
    def update_playoff_series(self, series_id: str, winner_id: str, game_result: Optional['MatchResult'] = None) -> Tuple[bool, Optional[str]]:
        """
        更新季后赛系列赛比分
        
        Args:
            series_id: 系列赛ID
            winner_id: 本场比赛胜者ID
            game_result: 比赛结果对象（可选，用于存储球员统计）
            
        Returns:
            (系列赛是否结束, 系列赛胜者ID或None)
        """
        if series_id not in self.playoff_bracket:
            print(f"[DEBUG] update_playoff_series: series_id {series_id} not in playoff_bracket")
            return False, None
        
        series = self.playoff_bracket[series_id]
        
        # 如果不是PlayoffSeries对象（可能是种子球队ID），返回
        if not isinstance(series, PlayoffSeries):
            print(f"[DEBUG] update_playoff_series: series {series_id} is not PlayoffSeries")
            return False, None
        
        # 存储比赛结果
        if game_result:
            series.add_game_result(game_result)
        
        # 调试日志：更新前的比分
        print(f"[DEBUG] update_playoff_series: {series_id} before update: {series.team1_wins}-{series.team2_wins}")
        print(f"[DEBUG] update_playoff_series: winner_id={winner_id}, team1_id={series.team1_id}, team2_id={series.team2_id}")
        
        # 更新胜场
        if winner_id == series.team1_id:
            series.team1_wins += 1
            print(f"[DEBUG] update_playoff_series: team1 wins, new score: {series.team1_wins}-{series.team2_wins}")
        elif winner_id == series.team2_id:
            series.team2_wins += 1
            print(f"[DEBUG] update_playoff_series: team2 wins, new score: {series.team1_wins}-{series.team2_wins}")
        else:
            print(f"[DEBUG] update_playoff_series: winner_id {winner_id} does not match team1 or team2!")
            return False, None
        
        # 检查系列赛是否结束
        if series.is_complete:
            series_winner = series.winner_id
            # 触发下一轮对阵生成
            self._advance_playoff_winner(series_id, series_winner)
            return True, series_winner
        
        return False, None
    
    def _advance_playoff_winner(self, series_id: str, winner_id: str) -> None:
        """
        处理系列赛胜者晋级
        
        Args:
            series_id: 完成的系列赛ID
            winner_id: 胜者ID
        """
        # 附加赛胜者晋级到四分之一决赛
        if series_id.startswith("play_in_"):
            self._setup_quarterfinals_if_ready()
        
        # 四分之一决赛胜者晋级到半决赛
        elif series_id.startswith("quarter_"):
            self._setup_semifinals_if_ready()
        
        # 半决赛胜者晋级到总决赛
        elif series_id.startswith("semi_"):
            self._setup_finals_if_ready()
    
    def _setup_quarterfinals_if_ready(self) -> None:
        """
        当所有附加赛结束后，设置四分之一决赛对阵
        
        对阵规则：
        - 1号种子 vs play_in_4胜者 (8/9胜者)
        - 2号种子 vs play_in_3胜者 (7/10胜者)
        - 3号种子 vs play_in_2胜者 (6/11胜者)
        - 4号种子 vs play_in_1胜者 (5/12胜者)
        """
        # 检查所有附加赛是否完成
        play_in_winners = []
        for i in range(1, 5):
            series_id = f"play_in_{i}"
            if series_id not in self.playoff_bracket:
                return
            series = self.playoff_bracket[series_id]
            if not isinstance(series, PlayoffSeries) or not series.is_complete:
                return
            play_in_winners.append(series.winner_id)
        
        # 所有附加赛完成，设置四分之一决赛
        # play_in_1胜者(5/12) vs 4号种子
        # play_in_2胜者(6/11) vs 3号种子
        # play_in_3胜者(7/10) vs 2号种子
        # play_in_4胜者(8/9) vs 1号种子
        quarter_matchups = [
            (self.playoff_bracket["quarter_seed_1"], play_in_winners[3]),  # 1 vs play_in_4胜者
            (self.playoff_bracket["quarter_seed_2"], play_in_winners[2]),  # 2 vs play_in_3胜者
            (self.playoff_bracket["quarter_seed_3"], play_in_winners[1]),  # 3 vs play_in_2胜者
            (self.playoff_bracket["quarter_seed_4"], play_in_winners[0]),  # 4 vs play_in_1胜者
        ]
        
        for i, (team1, team2) in enumerate(quarter_matchups):
            series_id = f"quarter_{i+1}"
            self.playoff_bracket[series_id] = PlayoffSeries(
                team1_id=team1,
                team2_id=team2,
                team1_wins=0,
                team2_wins=0,
                round_name="quarter"
            )
    
    def _setup_semifinals_if_ready(self) -> None:
        """
        当所有四分之一决赛结束后，设置半决赛对阵
        
        对阵规则：
        - quarter_1胜者 vs quarter_4胜者
        - quarter_2胜者 vs quarter_3胜者
        """
        # 检查所有四分之一决赛是否完成
        quarter_winners = []
        for i in range(1, 5):
            series_id = f"quarter_{i}"
            if series_id not in self.playoff_bracket:
                return
            series = self.playoff_bracket[series_id]
            if not isinstance(series, PlayoffSeries) or not series.is_complete:
                return
            quarter_winners.append(series.winner_id)
        
        # 设置半决赛
        semi_matchups = [
            (quarter_winners[0], quarter_winners[3]),  # quarter_1胜者 vs quarter_4胜者
            (quarter_winners[1], quarter_winners[2]),  # quarter_2胜者 vs quarter_3胜者
        ]
        
        for i, (team1, team2) in enumerate(semi_matchups):
            series_id = f"semi_{i+1}"
            self.playoff_bracket[series_id] = PlayoffSeries(
                team1_id=team1,
                team2_id=team2,
                team1_wins=0,
                team2_wins=0,
                round_name="semi"
            )
    
    def _setup_finals_if_ready(self) -> None:
        """
        当所有半决赛结束后，设置总决赛对阵
        """
        # 检查所有半决赛是否完成
        semi_winners = []
        for i in range(1, 3):
            series_id = f"semi_{i}"
            if series_id not in self.playoff_bracket:
                return
            series = self.playoff_bracket[series_id]
            if not isinstance(series, PlayoffSeries) or not series.is_complete:
                return
            semi_winners.append(series.winner_id)
        
        # 设置总决赛
        self.playoff_bracket["final"] = PlayoffSeries(
            team1_id=semi_winners[0],
            team2_id=semi_winners[1],
            team1_wins=0,
            team2_wins=0,
            round_name="final"
        )
    
    def get_playoff_bracket(self) -> Dict[str, PlayoffSeries]:
        """
        获取季后赛对阵表
        
        Returns:
            季后赛对阵字典
        """
        return self.playoff_bracket
    
    def get_current_playoff_series(self) -> List[PlayoffSeries]:
        """
        获取当前进行中的系列赛
        
        Returns:
            进行中的系列赛列表
        """
        active_series = []
        for key, value in self.playoff_bracket.items():
            if isinstance(value, PlayoffSeries) and not value.is_complete:
                active_series.append(value)
        return active_series
    
    def get_playoff_round_name(self) -> str:
        """
        获取当前季后赛轮次名称
        
        Returns:
            轮次名称: play_in/quarter/semi/final/champion
        """
        # 检查是否有总决赛
        if "final" in self.playoff_bracket:
            final = self.playoff_bracket["final"]
            if isinstance(final, PlayoffSeries):
                if final.is_complete:
                    return "champion"
                return "final"
        
        # 检查半决赛
        for i in range(1, 3):
            series_id = f"semi_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries) and not series.is_complete:
                    return "semi"
        
        # 检查四分之一决赛
        for i in range(1, 5):
            series_id = f"quarter_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries) and not series.is_complete:
                    return "quarter"
        
        # 检查附加赛
        for i in range(1, 5):
            series_id = f"play_in_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries) and not series.is_complete:
                    return "play_in"
        
        return "unknown"
    
    def get_champion(self) -> Optional[str]:
        """
        获取冠军球队ID
        
        Returns:
            冠军球队ID，如果总决赛未结束则返回None
        """
        if "final" not in self.playoff_bracket:
            return None
        
        final = self.playoff_bracket["final"]
        if isinstance(final, PlayoffSeries) and final.is_complete:
            return final.winner_id
        
        return None
    
    def is_playoffs_over(self) -> bool:
        """
        检查季后赛是否结束
        
        Returns:
            是否结束
        """
        return self.get_champion() is not None
    
    def get_playoff_bracket_for_display(self, teams: Dict[str, Team]) -> Dict:
        """
        获取用于前端显示的季后赛对阵图数据
        
        Args:
            teams: 球队字典 {team_id: Team}
            
        Returns:
            包含所有系列赛信息的字典，包括球队名称
        """
        # 调试日志：打印当前playoff_bracket中所有系列赛的比分
        print(f"[DEBUG] get_playoff_bracket_for_display called")
        for series_id, series in self.playoff_bracket.items():
            if isinstance(series, PlayoffSeries):
                print(f"[DEBUG] Series {series_id}: {series.team1_wins}-{series.team2_wins}")
        
        result = {
            "is_playoff_phase": len(self.playoff_bracket) > 0,
            "current_round": self.get_playoff_round_name(),
            "play_in": [],
            "quarter_seeds": [],
            "quarter": [],
            "semi": [],
            "final": None,
            "champion_id": self.get_champion(),
            "champion_name": None
        }
        
        # 获取冠军名称
        if result["champion_id"] and result["champion_id"] in teams:
            result["champion_name"] = teams[result["champion_id"]].name
        
        # 获取1-4号种子
        for i in range(1, 5):
            seed_key = f"quarter_seed_{i}"
            if seed_key in self.playoff_bracket:
                team_id = self.playoff_bracket[seed_key]
                team_name = teams[team_id].name if team_id in teams else ""
                result["quarter_seeds"].append({
                    "seed": i,
                    "team_id": team_id,
                    "team_name": team_name
                })
        
        # 获取附加赛系列赛
        for i in range(1, 5):
            series_id = f"play_in_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries):
                    result["play_in"].append(self._series_to_display(series_id, series, teams))
        
        # 获取四分之一决赛系列赛
        for i in range(1, 5):
            series_id = f"quarter_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries):
                    result["quarter"].append(self._series_to_display(series_id, series, teams))
        
        # 获取半决赛系列赛
        for i in range(1, 3):
            series_id = f"semi_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries):
                    result["semi"].append(self._series_to_display(series_id, series, teams))
        
        # 获取总决赛
        if "final" in self.playoff_bracket:
            series = self.playoff_bracket["final"]
            if isinstance(series, PlayoffSeries):
                result["final"] = self._series_to_display("final", series, teams)
        
        return result
    
    def _series_to_display(self, series_id: str, series: PlayoffSeries, teams: Dict[str, Team]) -> Dict:
        """
        将系列赛转换为显示格式
        
        Args:
            series_id: 系列赛ID
            series: 系列赛对象
            teams: 球队字典
            
        Returns:
            显示格式的系列赛字典
        """
        team1_name = teams[series.team1_id].name if series.team1_id in teams else ""
        team2_name = teams[series.team2_id].name if series.team2_id in teams else ""
        winner_name = None
        if series.winner_id and series.winner_id in teams:
            winner_name = teams[series.winner_id].name
        
        return {
            "series_id": series_id,
            "team1_id": series.team1_id,
            "team1_name": team1_name,
            "team2_id": series.team2_id,
            "team2_name": team2_name,
            "team1_wins": series.team1_wins,
            "team2_wins": series.team2_wins,
            "round_name": series.round_name,
            "wins_needed": series.wins_needed,
            "is_complete": series.is_complete,
            "winner_id": series.winner_id,
            "winner_name": winner_name
        }
    
    def get_player_team_series(self, player_team_id: str) -> Optional[Tuple[str, PlayoffSeries]]:
        """
        获取玩家球队当前参与的系列赛
        
        优先返回未完成的系列赛，如果所有系列赛都已完成则返回最高轮次的已完成系列赛
        
        Args:
            player_team_id: 玩家球队ID
            
        Returns:
            (series_id, PlayoffSeries) 元组，如果不存在则返回None
        """
        # 按轮次顺序查找：final -> semi -> quarter -> play_in
        # 优先返回最高轮次的未完成系列赛
        
        all_player_series = []
        
        # 检查总决赛
        if "final" in self.playoff_bracket:
            series = self.playoff_bracket["final"]
            if isinstance(series, PlayoffSeries):
                if series.team1_id == player_team_id or series.team2_id == player_team_id:
                    all_player_series.append(("final", series, 4))  # 轮次权重4
        
        # 检查半决赛
        for i in range(1, 3):
            series_id = f"semi_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries):
                    if series.team1_id == player_team_id or series.team2_id == player_team_id:
                        all_player_series.append((series_id, series, 3))  # 轮次权重3
        
        # 检查四分之一决赛
        for i in range(1, 5):
            series_id = f"quarter_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries):
                    if series.team1_id == player_team_id or series.team2_id == player_team_id:
                        all_player_series.append((series_id, series, 2))  # 轮次权重2
        
        # 检查附加赛
        for i in range(1, 5):
            series_id = f"play_in_{i}"
            if series_id in self.playoff_bracket:
                series = self.playoff_bracket[series_id]
                if isinstance(series, PlayoffSeries):
                    if series.team1_id == player_team_id or series.team2_id == player_team_id:
                        all_player_series.append((series_id, series, 1))  # 轮次权重1
        
        if not all_player_series:
            return None
        
        # 优先返回未完成的系列赛（按轮次从高到低）
        incomplete_series = [(sid, s, w) for sid, s, w in all_player_series if not s.is_complete]
        if incomplete_series:
            # 按轮次权重降序排序，返回最高轮次的未完成系列赛
            incomplete_series.sort(key=lambda x: x[2], reverse=True)
            return (incomplete_series[0][0], incomplete_series[0][1])
        
        # 如果所有系列赛都已完成，返回最高轮次的已完成系列赛
        all_player_series.sort(key=lambda x: x[2], reverse=True)
        return (all_player_series[0][0], all_player_series[0][1])
    
    def is_team_eliminated(self, team_id: str) -> bool:
        """
        检查球队是否已在季后赛中被淘汰
        
        Args:
            team_id: 球队ID
            
        Returns:
            是否已淘汰
        """
        # 如果季后赛未开始，没有球队被淘汰
        if not self.playoff_bracket:
            return False
        
        # 检查球队是否在任何已完成的系列赛中失败
        all_series_keys = [
            *[f"play_in_{i}" for i in range(1, 5)],
            *[f"quarter_{i}" for i in range(1, 5)],
            *[f"semi_{i}" for i in range(1, 3)],
            "final"
        ]
        
        for series_key in all_series_keys:
            if series_key in self.playoff_bracket:
                series = self.playoff_bracket[series_key]
                if isinstance(series, PlayoffSeries):
                    # 如果球队在这个系列赛中
                    if series.team1_id == team_id or series.team2_id == team_id:
                        # 如果系列赛已完成且球队不是胜者
                        if series.is_complete and series.winner_id != team_id:
                            return True
                        # 如果系列赛未完成，球队还在比赛中
                        if not series.is_complete:
                            return False
        
        # 检查球队是否在季后赛名单中
        playoff_teams = self.get_playoff_teams()
        if team_id not in playoff_teams:
            return False  # 不在季后赛中，不算淘汰
        
        return False
    
    def is_team_in_playoffs(self, team_id: str) -> bool:
        """
        检查球队是否在季后赛中
        
        Args:
            team_id: 球队ID
            
        Returns:
            是否在季后赛中
        """
        playoff_teams = self.get_playoff_teams()
        return team_id in playoff_teams
