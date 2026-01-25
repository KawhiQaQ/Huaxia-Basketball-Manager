"""
华夏篮球联赛教练模拟器 - 伤病系统

负责随机伤病事件的触发和管理
Requirements: 13.1, 13.2, 13.4
"""
import random
from typing import List, Tuple, Optional
from src.models import Player, Team


class InjurySystem:
    """伤病系统 - 负责伤病检测、应用和恢复"""
    
    # 每场比赛每人受伤概率 (2%)
    INJURY_PROBABILITY = 0.1
    
    # 恢复天数范围 (3-21天)
    INJURY_DURATION_MIN = 3
    INJURY_DURATION_MAX = 21
    
    def __init__(
        self,
        injury_probability: float = INJURY_PROBABILITY,
        duration_min: int = INJURY_DURATION_MIN,
        duration_max: int = INJURY_DURATION_MAX
    ):
        """
        初始化伤病系统
        
        Args:
            injury_probability: 受伤概率 (0-1)
            duration_min: 最短恢复天数
            duration_max: 最长恢复天数
        """
        self.injury_probability = injury_probability
        self.duration_min = duration_min
        self.duration_max = duration_max
    
    def check_for_injuries(
        self,
        players: List[Player]
    ) -> List[Tuple[Player, int]]:
        """
        检查球员是否受伤（随机伤病检测）
        
        对每个未受伤的球员进行伤病检测，根据概率随机触发伤病
        
        Args:
            players: 要检查的球员列表
            
        Returns:
            受伤球员和恢复天数的列表 [(player, days), ...]
        """
        injuries = []
        
        for player in players:
            # 已受伤的球员不再检测
            if player.is_injured:
                continue
            
            # 随机检测是否受伤
            if random.random() < self.injury_probability:
                # 随机生成恢复天数
                recovery_days = random.randint(
                    self.duration_min,
                    self.duration_max
                )
                injuries.append((player, recovery_days))
        
        return injuries
    
    def apply_injury(self, player: Player, days: int) -> None:
        """
        应用伤病到球员
        
        将球员标记为受伤状态，并设置恢复天数
        
        Args:
            player: 球员对象
            days: 恢复天数（必须为正数）
        """
        if days <= 0:
            return
        
        player.is_injured = True
        player.injury_days = days
    
    def recover_players(
        self,
        players: List[Player],
        days_passed: int = 1
    ) -> List[Player]:
        """
        处理球员恢复
        
        减少受伤球员的恢复天数，当恢复天数归零时恢复健康状态
        
        Args:
            players: 球员列表
            days_passed: 经过的天数（默认1天）
            
        Returns:
            本次恢复健康的球员列表
        """
        recovered = []
        
        for player in players:
            if not player.is_injured:
                continue
            
            # 减少恢复天数
            player.injury_days -= days_passed
            
            # 检查是否恢复
            if player.injury_days <= 0:
                player.is_injured = False
                player.injury_days = 0
                recovered.append(player)
        
        return recovered
    
    def get_injured_players(self, team: Team, players: dict) -> List[Player]:
        """
        获取球队中受伤的球员
        
        Args:
            team: 球队对象
            players: 球员字典 {player_id: Player}
            
        Returns:
            受伤球员列表
        """
        injured = []
        
        for player_id in team.roster:
            player = players.get(player_id)
            if player and player.is_injured:
                injured.append(player)
        
        return injured
    
    def get_healthy_players(self, team: Team, players: dict) -> List[Player]:
        """
        获取球队中健康的球员
        
        Args:
            team: 球队对象
            players: 球员字典 {player_id: Player}
            
        Returns:
            健康球员列表
        """
        healthy = []
        
        for player_id in team.roster:
            player = players.get(player_id)
            if player and not player.is_injured:
                healthy.append(player)
        
        return healthy
    
    def get_all_injured_players(self, players: dict) -> List[Player]:
        """
        获取所有受伤的球员
        
        Args:
            players: 球员字典 {player_id: Player}
            
        Returns:
            所有受伤球员列表
        """
        return [p for p in players.values() if p.is_injured]
    
    def check_team_injuries(
        self,
        team: Team,
        players: dict
    ) -> List[Tuple[Player, int]]:
        """
        检查球队球员的伤病情况
        
        对球队中所有健康球员进行伤病检测
        
        Args:
            team: 球队对象
            players: 球员字典 {player_id: Player}
            
        Returns:
            受伤球员和恢复天数的列表
        """
        team_players = []
        for player_id in team.roster:
            player = players.get(player_id)
            if player:
                team_players.append(player)
        
        return self.check_for_injuries(team_players)
    
    def apply_injuries_batch(
        self,
        injuries: List[Tuple[Player, int]]
    ) -> int:
        """
        批量应用伤病
        
        Args:
            injuries: 伤病列表 [(player, days), ...]
            
        Returns:
            应用的伤病数量
        """
        count = 0
        for player, days in injuries:
            self.apply_injury(player, days)
            count += 1
        return count
    
    def get_injury_report(
        self,
        team: Team,
        players: dict
    ) -> str:
        """
        生成球队伤病报告
        
        Args:
            team: 球队对象
            players: 球员字典
            
        Returns:
            格式化的伤病报告字符串
        """
        injured = self.get_injured_players(team, players)
        
        if not injured:
            return f"{team.name}: 无伤病球员"
        
        report = f"{team.name} 伤病报告:\n"
        for player in injured:
            report += f"  - {player.name}: 预计还需 {player.injury_days} 天恢复\n"
        
        return report
