"""
华夏篮球联赛教练模拟器 - 球员数据统计计算器

负责计算球队总分、验证统计数据一致性、基于能力值生成统计数据
"""
import random
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import asdict

from src.models import Player, GameStats


class StatsCalculator:
    """球员数据统计计算器"""
    
    # 合理的比赛分数范围
    MIN_TEAM_SCORE = 82
    MAX_TEAM_SCORE = 150
    
    # 高能力值球员阈值
    HIGH_ABILITY_THRESHOLD = 85
    
    # 基于球队总分的调整区间配置
    # 格式: (分数下限, 分数上限, 最小调整, 最大调整)
    TEAM_SCORE_ADJUSTMENT_RANGES = [
        (0, 90, 5, 10),       # 总分 <= 90: +5 ~ +10
        (91, 100, -2, 8),     # 总分 91-100: -2 ~ +8
        (101, 110, -5, 7),    # 总分 101-110: -5 ~ +7
        (111, 120, -6, 6),    # 总分 111-120: -6 ~ +6
        (121, 125, -3, 3),    # 总分 111-120: -6 ~ +6
        (126, 139, -9, -3),   # 总分 >= 121: -8 ~ -3
        (140, 999, -15, -10),   # 总分 >= 121: -8 ~ -3
    ]
    
    @staticmethod
    def get_adjustment_range_for_score(team_score: int) -> Tuple[int, int]:
        """
        根据球队总分获取对应的调整区间
        
        Args:
            team_score: LLM模拟的球队总分
            
        Returns:
            (最小调整值, 最大调整值) 元组
        """
        for min_score, max_score, min_adj, max_adj in StatsCalculator.TEAM_SCORE_ADJUSTMENT_RANGES:
            if min_score <= team_score <= max_score:
                return (min_adj, max_adj)
        # 默认返回中间区间
        return (-5, 7)
    
    @staticmethod
    def apply_team_score_adjustment(
        player_stats: Dict[str, GameStats],
        team_player_ids: Set[str],
        original_team_score: int
    ) -> Tuple[Dict[str, GameStats], int]:
        """
        根据球队总分区间调整球队总分，再分配到球员
        
        1. 根据原始总分确定调整区间
        2. 在区间内随机选择调整值，得到新的球队总分
        3. 根据新总分重新分配球员得分，并增加方差
        
        Args:
            player_stats: 球员统计字典 {player_id: GameStats}
            team_player_ids: 该球队的球员ID集合
            original_team_score: LLM模拟的原始球队总分
            
        Returns:
            (调整后的球员统计字典, 调整后的球队总分) 元组
        """
        # 获取调整区间
        min_adj, max_adj = StatsCalculator.get_adjustment_range_for_score(original_team_score)
        
        # 随机选择调整值
        adjustment = random.randint(min_adj, max_adj)
        new_team_score = max(StatsCalculator.MIN_TEAM_SCORE, original_team_score + adjustment)
        
        adjusted_stats = dict(player_stats)  # 浅拷贝
        
        # 获取该球队的球员及其原始得分
        team_players = []
        for player_id in team_player_ids:
            if player_id not in player_stats:
                continue
            stats = player_stats[player_id]
            if isinstance(stats, GameStats):
                team_players.append((player_id, stats.points, stats))
            elif isinstance(stats, dict):
                team_players.append((player_id, stats.get('points', 0), stats))
        
        if not team_players:
            return adjusted_stats, new_team_score
        
        # 计算原始总分（用于比例分配）
        current_total = sum(pts for _, pts, _ in team_players)
        
        if current_total == 0:
            # 如果原始总分为0，平均分配
            points_per_player = new_team_score // len(team_players)
            remainder = new_team_score % len(team_players)
            for i, (player_id, _, stats) in enumerate(team_players):
                extra = 1 if i < remainder else 0
                new_points = points_per_player + extra
                adjusted_stats[player_id] = StatsCalculator._create_adjusted_game_stats(
                    stats, new_points
                )
            return adjusted_stats, new_team_score
        
        # 按比例分配新总分，并增加随机方差
        ratio = new_team_score / current_total
        running_total = 0
        
        # 先计算基础分配（带方差）
        base_allocations = []
        for player_id, original_pts, stats in team_players:
            # 基础分配
            base_new_pts = original_pts * ratio
            # 增加随机方差：±15% 的波动，使模拟更真实
            variance_factor = random.uniform(0.85, 1.15)
            varied_pts = base_new_pts * variance_factor
            # 额外的小幅随机调整 ±2分
            micro_adjustment = random.randint(-2, 2)
            final_pts = max(0, int(varied_pts + micro_adjustment))
            base_allocations.append((player_id, final_pts, stats))
        
        # 计算当前分配的总分
        allocated_total = sum(pts for _, pts, _ in base_allocations)
        
        # 调整最后一个球员的得分以确保总分精确
        if base_allocations:
            # 找到得分最高的球员来吸收差值（更合理）
            diff = new_team_score - allocated_total
            if diff != 0:
                # 按得分排序，让高分球员吸收差值
                sorted_allocations = sorted(base_allocations, key=lambda x: x[1], reverse=True)
                player_id, pts, stats = sorted_allocations[0]
                adjusted_pts = max(0, pts + diff)
                # 更新分配
                base_allocations = [
                    (pid, adjusted_pts if pid == player_id else p, s)
                    for pid, p, s in base_allocations
                ]
        
        # 应用分配结果
        for player_id, new_points, stats in base_allocations:
            adjusted_stats[player_id] = StatsCalculator._create_adjusted_game_stats(
                stats, new_points
            )
        
        return adjusted_stats, new_team_score
    
    @staticmethod
    def _create_adjusted_game_stats(stats, new_points: int) -> GameStats:
        """
        创建调整后的GameStats对象
        
        Args:
            stats: 原始统计数据 (GameStats 或 dict)
            new_points: 新的得分
            
        Returns:
            新的GameStats对象
        """
        if isinstance(stats, GameStats):
            return GameStats(
                points=new_points,
                rebounds=stats.rebounds,
                assists=stats.assists,
                steals=stats.steals,
                blocks=stats.blocks,
                turnovers=stats.turnovers,
                minutes=stats.minutes,
                team_id=stats.team_id
            )
        elif isinstance(stats, dict):
            return GameStats(
                points=new_points,
                rebounds=stats.get('rebounds', 0),
                assists=stats.get('assists', 0),
                steals=stats.get('steals', 0),
                blocks=stats.get('blocks', 0),
                turnovers=stats.get('turnovers', 0),
                minutes=stats.get('minutes', 0),
                team_id=stats.get('team_id', '')
            )
        return GameStats(points=new_points)
    
    @staticmethod
    def apply_score_adjustment(
        player_stats: Dict[str, GameStats],
        home_player_ids: Optional[Set[str]] = None,
        away_player_ids: Optional[Set[str]] = None
    ) -> Dict[str, GameStats]:
        """
        对球员得分进行随机调整（基于球队总分区间）
        
        新逻辑：
        1. 先计算各队LLM模拟的总分
        2. 根据总分区间确定调整范围
        3. 调整球队总分
        4. 根据新总分重新分配球员得分（带方差）
        5. 如果调整后同分，给原本更高分的队伍+1
        
        Args:
            player_stats: 球员统计字典 {player_id: GameStats}
            home_player_ids: 主队球员ID集合（可选）
            away_player_ids: 客队球员ID集合（可选）
            
        Returns:
            调整后的球员统计字典
        """
        # 如果提供了两队球员ID，分别调整
        if home_player_ids is not None and away_player_ids is not None:
            # 计算原始总分
            original_home_score = StatsCalculator.calculate_team_score(player_stats, home_player_ids)
            original_away_score = StatsCalculator.calculate_team_score(player_stats, away_player_ids)
            
            # 调整主队
            adjusted_stats, new_home_score = StatsCalculator.apply_team_score_adjustment(
                player_stats, home_player_ids, original_home_score
            )
            # 调整客队
            adjusted_stats, new_away_score = StatsCalculator.apply_team_score_adjustment(
                adjusted_stats, away_player_ids, original_away_score
            )
            
            # 处理同分情况：给原本LLM模拟更高分的队伍+1
            if new_home_score == new_away_score:
                if original_home_score > original_away_score:
                    # 主队原本更高，给主队+1
                    adjusted_stats = StatsCalculator._add_one_point_to_team(
                        adjusted_stats, home_player_ids
                    )
                elif original_away_score > original_home_score:
                    # 客队原本更高，给客队+1
                    adjusted_stats = StatsCalculator._add_one_point_to_team(
                        adjusted_stats, away_player_ids
                    )
                else:
                    # 原本也同分，随机给一队+1
                    if random.random() < 0.5:
                        adjusted_stats = StatsCalculator._add_one_point_to_team(
                            adjusted_stats, home_player_ids
                        )
                    else:
                        adjusted_stats = StatsCalculator._add_one_point_to_team(
                            adjusted_stats, away_player_ids
                        )
            
            return adjusted_stats
        
        # 否则对所有球员使用同一模式（向后兼容）
        all_player_ids = set(player_stats.keys())
        original_score = StatsCalculator.calculate_team_score(player_stats, all_player_ids)
        adjusted_stats, _ = StatsCalculator.apply_team_score_adjustment(
            player_stats, all_player_ids, original_score
        )
        return adjusted_stats
    
    @staticmethod
    def _add_one_point_to_team(
        player_stats: Dict[str, GameStats],
        team_player_ids: Set[str]
    ) -> Dict[str, GameStats]:
        """
        给球队随机一名球员+1分
        
        Args:
            player_stats: 球员统计字典
            team_player_ids: 球队球员ID集合
            
        Returns:
            调整后的球员统计字典
        """
        team_players = [pid for pid in team_player_ids if pid in player_stats]
        if not team_players:
            return player_stats
        
        # 随机选择一名球员加1分
        lucky_player = random.choice(team_players)
        stats = player_stats[lucky_player]
        
        if isinstance(stats, GameStats):
            player_stats[lucky_player] = GameStats(
                points=stats.points + 1,
                rebounds=stats.rebounds,
                assists=stats.assists,
                steals=stats.steals,
                blocks=stats.blocks,
                turnovers=stats.turnovers,
                minutes=stats.minutes,
                team_id=stats.team_id
            )
        
        return player_stats
    
    @staticmethod
    def calculate_team_score(
        player_stats: Dict[str, GameStats],
        team_player_ids: Optional[Set[str]] = None
    ) -> int:
        """
        根据球员得分计算球队总分
        
        确保数据一致性：球队总分 = 所有球员得分之和
        
        Args:
            player_stats: 球员统计字典 {player_id: GameStats}
            team_player_ids: 球队球员ID集合（可选，用于筛选特定球队）
            
        Returns:
            球队总分
        """
        total = 0
        for player_id, stats in player_stats.items():
            if team_player_ids is None or player_id in team_player_ids:
                if isinstance(stats, GameStats):
                    total += stats.points
                elif isinstance(stats, dict):
                    total += stats.get('points', 0)
        return total
    
    @staticmethod
    def validate_and_adjust_stats(
        player_stats: Dict[str, GameStats],
        home_player_ids: Set[str],
        away_player_ids: Set[str],
        expected_home_score: Optional[int] = None,
        expected_away_score: Optional[int] = None
    ) -> Tuple[Dict[str, GameStats], int, int]:
        """
        验证并调整球员统计数据
        
        确保：
        1. 总分在合理范围内 (70-150)
        2. 如果提供了期望分数，调整球员数据使总分匹配
        3. 球员数据保持合理性
        
        Args:
            player_stats: 球员统计字典
            home_player_ids: 主队球员ID集合
            away_player_ids: 客队球员ID集合
            expected_home_score: 期望的主队总分（可选）
            expected_away_score: 期望的客队总分（可选）
            
        Returns:
            (调整后的球员统计, 主队总分, 客队总分) 元组
        """
        # 计算当前总分
        home_total = StatsCalculator.calculate_team_score(player_stats, home_player_ids)
        away_total = StatsCalculator.calculate_team_score(player_stats, away_player_ids)
        
        adjusted_stats = {}
        
        # 复制并可能调整统计数据
        for player_id, stats in player_stats.items():
            if isinstance(stats, GameStats):
                adjusted_stats[player_id] = GameStats(
                    points=stats.points,
                    rebounds=stats.rebounds,
                    assists=stats.assists,
                    steals=stats.steals,
                    blocks=stats.blocks,
                    turnovers=stats.turnovers,
                    minutes=stats.minutes,
                    team_id=stats.team_id  # 保留比赛时球队ID
                )
            elif isinstance(stats, dict):
                adjusted_stats[player_id] = GameStats(
                    points=stats.get('points', 0),
                    rebounds=stats.get('rebounds', 0),
                    assists=stats.get('assists', 0),
                    steals=stats.get('steals', 0),
                    blocks=stats.get('blocks', 0),
                    turnovers=stats.get('turnovers', 0),
                    minutes=stats.get('minutes', 0),
                    team_id=stats.get('team_id', '')  # 保留比赛时球队ID
                )
        
        # 如果需要调整主队分数
        if expected_home_score is not None and home_total != expected_home_score:
            adjusted_stats = StatsCalculator._adjust_team_points(
                adjusted_stats, home_player_ids, home_total, expected_home_score
            )
            home_total = expected_home_score
        
        # 如果需要调整客队分数
        if expected_away_score is not None and away_total != expected_away_score:
            adjusted_stats = StatsCalculator._adjust_team_points(
                adjusted_stats, away_player_ids, away_total, expected_away_score
            )
            away_total = expected_away_score
        
        # 验证分数在合理范围内
        if not (StatsCalculator.MIN_TEAM_SCORE <= home_total <= StatsCalculator.MAX_TEAM_SCORE):
            # 需要规范化
            target_home = max(StatsCalculator.MIN_TEAM_SCORE, 
                            min(StatsCalculator.MAX_TEAM_SCORE, home_total))
            adjusted_stats = StatsCalculator._adjust_team_points(
                adjusted_stats, home_player_ids, home_total, target_home
            )
            home_total = target_home
        
        if not (StatsCalculator.MIN_TEAM_SCORE <= away_total <= StatsCalculator.MAX_TEAM_SCORE):
            target_away = max(StatsCalculator.MIN_TEAM_SCORE,
                            min(StatsCalculator.MAX_TEAM_SCORE, away_total))
            adjusted_stats = StatsCalculator._adjust_team_points(
                adjusted_stats, away_player_ids, away_total, target_away
            )
            away_total = target_away
        
        return adjusted_stats, home_total, away_total
    
    @staticmethod
    def _adjust_team_points(
        player_stats: Dict[str, GameStats],
        team_player_ids: Set[str],
        current_total: int,
        target_total: int
    ) -> Dict[str, GameStats]:
        """
        调整球队球员得分使总分达到目标值
        
        按比例调整每个球员的得分
        
        Args:
            player_stats: 球员统计字典
            team_player_ids: 球队球员ID集合
            current_total: 当前总分
            target_total: 目标总分
            
        Returns:
            调整后的球员统计字典
        """
        if current_total == 0:
            # 如果当前总分为0，平均分配
            team_players = [pid for pid in team_player_ids if pid in player_stats]
            if team_players:
                points_per_player = target_total // len(team_players)
                remainder = target_total % len(team_players)
                for i, pid in enumerate(team_players):
                    extra = 1 if i < remainder else 0
                    player_stats[pid].points = points_per_player + extra
            return player_stats
        
        # 按比例调整
        ratio = target_total / current_total
        running_total = 0
        team_players = [pid for pid in team_player_ids if pid in player_stats]
        
        for i, pid in enumerate(team_players):
            if i == len(team_players) - 1:
                # 最后一个球员获得剩余分数，确保总分精确
                player_stats[pid].points = target_total - running_total
            else:
                new_points = int(player_stats[pid].points * ratio)
                new_points = max(0, min(60, new_points))  # 限制单人得分范围
                player_stats[pid].points = new_points
                running_total += new_points
        
        return player_stats
    
    @staticmethod
    def generate_ability_based_stats(
        player: Player,
        is_starter: bool,
        team_pace: float = 1.0,
        game_role_boost: float = 0.0
    ) -> GameStats:
        """
        基于球员能力值生成统计数据，带有显著随机性
        
        引入多重随机机制：
        1. "状态"机制：15%爆发、15%低迷、70%正常
        2. "比赛角色"机制：每场比赛随机选择1-2个球员作为进攻核心
        3. "手感"机制：独立于状态的投篮手感波动
        4. 更大的随机方差，让结果更不可预测
        
        Args:
            player: 球员对象
            is_starter: 是否首发
            team_pace: 球队节奏因子（默认1.0）
            game_role_boost: 比赛角色加成（0.0-0.5，进攻核心获得加成）
            
        Returns:
            生成的单场比赛统计数据
        """
        # 决定球员本场状态
        state_roll = random.random()
        if state_roll < 0.15:
            # 爆发状态：数据提升 50-100%
            state_multiplier = random.uniform(1.5, 2.0)
            state = "hot"
        elif state_roll < 0.30:
            # 低迷状态：数据下降 40-60%
            state_multiplier = random.uniform(0.4, 0.6)
            state = "cold"
        else:
            # 正常状态：较大幅度波动 70%-130%
            state_multiplier = random.uniform(0.7, 1.3)
            state = "normal"
        
        # 独立的"手感"因子 - 影响得分的额外随机性
        shooting_feel = random.uniform(0.6, 1.5)
        
        # 根据总评和是否首发决定上场时间
        if is_starter:
            base_minutes = 28 + (player.overall - 70) * 0.12
            base_minutes = max(24, min(36, base_minutes))
        else:
            base_minutes = 14 + (player.overall - 70) * 0.08
            base_minutes = max(8, min(24, base_minutes))
        
        # 上场时间有较大随机波动
        minutes = int(base_minutes + random.gauss(0, 5))
        minutes = max(5, min(42, minutes))
        
        # 时间因子
        time_factor = minutes / 30.0
        
        # === 得分计算 ===
        # 基础得分：降低能力值的影响权重，增加随机性
        base_points = 8 + (player.overall - 70) * 0.25 + (player.offense - 70) * 0.1
        # 大方差，让结果更不可预测
        points_std = 8 + random.uniform(0, 4)
        
        # 应用比赛角色加成
        role_multiplier = 1.0 + game_role_boost
        
        points = random.gauss(base_points, points_std) * time_factor * state_multiplier * shooting_feel * team_pace * role_multiplier
        
        # 偶尔出现极端值（5%概率大爆发，5%概率极低迷）
        extreme_roll = random.random()
        if extreme_roll < 0.05:
            points *= random.uniform(1.5, 2.0)  # 大爆发
        elif extreme_roll > 0.95:
            points *= random.uniform(0.3, 0.5)  # 极低迷
        
        points = int(max(0, min(55, points)))
        
        # === 篮板计算 ===
        base_rebounds = 2.5 + (player.rebounding - 70) * 0.1
        rebound_std = 3.0
        
        rebounds = random.gauss(base_rebounds, rebound_std) * time_factor * state_multiplier
        # 篮板也有极端情况
        if random.random() < 0.08:
            rebounds *= random.uniform(1.5, 2.5)
        rebounds = int(max(0, min(22, rebounds)))
        
        # === 助攻计算 ===
        base_assists = 2 + (player.passing - 70) * 0.08
        assist_std = 2.5
        
        assists = random.gauss(base_assists, assist_std) * time_factor * state_multiplier
        # 组织后卫偶尔大爆发
        if random.random() < 0.08:
            assists *= random.uniform(1.5, 2.0)
        assists = int(max(0, min(18, assists)))
        
        # === 抢断计算 ===
        base_steals = 0.8 + (player.defense - 70) * 0.025
        steal_std = 1.2
        
        steals = random.gauss(base_steals, steal_std) * time_factor * state_multiplier
        steals = int(max(0, min(7, steals)))
        
        # === 盖帽计算 ===
        base_blocks = 0.5 + (player.defense - 70) * 0.02 + (player.rebounding - 70) * 0.01
        block_std = 1.0
        
        blocks = random.gauss(base_blocks, block_std) * time_factor * state_multiplier
        blocks = int(max(0, min(6, blocks)))
        
        # === 失误计算（与状态相反：爆发时失误少，低迷时失误多）===
        base_turnovers = 2.0 - (player.passing - 70) * 0.015
        turnover_std = 1.5
        
        # 状态影响失误：爆发时失误少，低迷时失误多
        if state == "hot":
            turnover_multiplier = 0.6
        elif state == "cold":
            turnover_multiplier = 1.5
        else:
            turnover_multiplier = random.uniform(0.8, 1.2)
        
        turnovers = random.gauss(base_turnovers, turnover_std) * time_factor * turnover_multiplier
        turnovers = int(max(0, min(8, turnovers)))
        
        return GameStats(
            points=points,
            rebounds=rebounds,
            assists=assists,
            steals=steals,
            blocks=blocks,
            turnovers=turnovers,
            minutes=minutes
        )
    
    @staticmethod
    def generate_team_stats(
        players: List[Player],
        target_score: Optional[int] = None,
        team_pace: float = 1.0
    ) -> Tuple[Dict[str, GameStats], int]:
        """
        为整个球队生成统计数据
        
        引入"比赛角色"机制：
        - 每场比赛随机选择1-2个球员作为"进攻核心"，获得得分加成
        - 这样不同比赛会有不同的得分分布，更加真实
        
        Args:
            players: 球员列表（按能力值排序，前5人为首发）
            target_score: 目标总分（可选，如果提供则调整使总分匹配）
            team_pace: 球队节奏因子
            
        Returns:
            (球员统计字典, 球队总分) 元组
        """
        # 过滤受伤球员和被裁球员，并按能力值排序
        active_players = [p for p in players if not p.is_injured and not p.is_waived]
        sorted_players = sorted(active_players, key=lambda p: p.overall, reverse=True)
        
        # 取前8人（5首发 + 3轮换）
        rotation = sorted_players[:8]
        
        # === 比赛角色分配 ===
        # 随机选择1-2个球员作为本场比赛的"进攻核心"
        num_cores = random.choice([1, 1, 2])  # 67%概率1个核心，33%概率2个核心
        
        # 核心球员可以是任何轮换球员，不一定是能力值最高的
        # 但能力值高的球员有更高概率被选中
        core_weights = []
        for i, player in enumerate(rotation):
            # 首发球员权重更高，但替补也有机会
            base_weight = 3 if i < 5 else 1
            # 能力值影响权重，但不是决定性的
            ability_weight = 1 + (player.overall - 70) * 0.02
            core_weights.append(base_weight * ability_weight)
        
        # 归一化权重
        total_weight = sum(core_weights)
        core_weights = [w / total_weight for w in core_weights]
        
        # 选择核心球员
        core_indices = set()
        for _ in range(num_cores):
            # 加权随机选择
            r = random.random()
            cumulative = 0
            for i, w in enumerate(core_weights):
                cumulative += w
                if r <= cumulative and i not in core_indices:
                    core_indices.add(i)
                    break
            else:
                # 如果没选中，随机选一个
                available = [i for i in range(len(rotation)) if i not in core_indices]
                if available:
                    core_indices.add(random.choice(available))
        
        player_stats = {}
        for i, player in enumerate(rotation):
            is_starter = i < 5
            # 核心球员获得得分加成
            game_role_boost = random.uniform(0.3, 0.5) if i in core_indices else 0.0
            
            stats = StatsCalculator.generate_ability_based_stats(
                player, is_starter, team_pace, game_role_boost
            )
            # 记录比赛时球员所属球队（用于交易后正确显示历史数据）
            stats.team_id = player.team_id
            player_stats[player.id] = stats
        
        # 计算总分
        total_score = StatsCalculator.calculate_team_score(player_stats)
        
        # 如果需要调整到目标分数
        if target_score is not None and total_score != target_score:
            player_ids = set(player_stats.keys())
            player_stats = StatsCalculator._adjust_team_points(
                player_stats, player_ids, total_score, target_score
            )
            total_score = target_score
        
        return player_stats, total_score
    
    @staticmethod
    def validate_score_consistency(
        home_score: int,
        away_score: int,
        player_stats: Dict[str, GameStats],
        home_player_ids: Set[str],
        away_player_ids: Set[str]
    ) -> bool:
        """
        验证比分与球员数据的一致性
        
        Args:
            home_score: 主队总分
            away_score: 客队总分
            player_stats: 球员统计字典
            home_player_ids: 主队球员ID集合
            away_player_ids: 客队球员ID集合
            
        Returns:
            是否一致
        """
        calculated_home = StatsCalculator.calculate_team_score(player_stats, home_player_ids)
        calculated_away = StatsCalculator.calculate_team_score(player_stats, away_player_ids)
        
        return calculated_home == home_score and calculated_away == away_score
    
    @staticmethod
    def ensure_score_consistency(
        player_stats: Dict[str, GameStats],
        home_player_ids: Set[str],
        away_player_ids: Set[str]
    ) -> Tuple[Dict[str, GameStats], int, int]:
        """
        确保比分一致性：球队总分 = 球员得分之和
        
        此方法计算球队总分并返回一致的结果，用于创建MatchResult时确保比分一致性。
        
        Args:
            player_stats: 球员统计字典
            home_player_ids: 主队球员ID集合
            away_player_ids: 客队球员ID集合
            
        Returns:
            (球员统计字典, 主队总分, 客队总分) 元组
            返回的总分保证等于对应球队球员得分之和
        """
        # 计算球队总分（直接从球员得分计算，确保一致性）
        home_score = StatsCalculator.calculate_team_score(player_stats, home_player_ids)
        away_score = StatsCalculator.calculate_team_score(player_stats, away_player_ids)
        
        # 验证并调整统计数据确保分数在合理范围内
        adjusted_stats, adjusted_home, adjusted_away = StatsCalculator.validate_and_adjust_stats(
            player_stats, home_player_ids, away_player_ids
        )
        
        return adjusted_stats, adjusted_home, adjusted_away
    
    @staticmethod
    def get_expected_points_range(player: Player, is_starter: bool) -> Tuple[int, int]:
        """
        获取球员的期望得分范围
        
        用于验证生成的统计数据是否合理
        
        Args:
            player: 球员对象
            is_starter: 是否首发
            
        Returns:
            (最小期望得分, 最大期望得分) 元组
        """
        if player.overall >= StatsCalculator.HIGH_ABILITY_THRESHOLD:
            if is_starter:
                # 85+总评首发球员期望得分范围：20-50
                # 允许30+场均得分
                return (20, 50)
            else:
                return (10, 30)
        else:
            if is_starter:
                return (5, 28)
            else:
                return (0, 18)
