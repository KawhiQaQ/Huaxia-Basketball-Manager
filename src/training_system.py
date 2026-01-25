"""
华夏篮球联赛教练模拟器 - 训练系统

负责处理日常训练和球员能力值提升
Requirements: 3.1, 3.2, 3.4
"""
import random
from typing import List, Dict, Tuple, Optional
from src.models import Player, Team, TrainingProgram
from src.player_data_manager import PlayerDataManager


# 预定义训练项目 - 每次训练随机提高0~2点训练点数
TRAINING_PROGRAMS = [
    TrainingProgram("投篮训练", "three_point", 1, 2),
    TrainingProgram("进攻训练", "offense", 1, 2),
    TrainingProgram("防守训练", "defense", 1, 2),
    TrainingProgram("篮板训练", "rebounding", 1, 2),
    TrainingProgram("传球训练", "passing", 1, 2),
    TrainingProgram("体能训练", "stamina", 1, 2),
]

# 属性上限
ATTRIBUTE_MAX = 99

# 训练次数限制
MAX_TEAM_TRAINING_PER_DAY = 2  # 每天最多2次全队训练
MAX_INDIVIDUAL_TRAINING_PER_PLAYER = 2  # 每个球员每天最多2次单独训练

# 训练进度系统常量
TRAINING_POINTS_PER_UPGRADE = 20  # 单项训练点数达到20后，该单项+1
ATTRIBUTE_UPGRADES_PER_OVERALL = 5  # 累积5次单项+1后，总评+1


class TrainingAccessError(Exception):
    """训练访问控制错误"""
    pass


class TrainingLimitError(Exception):
    """训练次数限制错误"""
    pass


class TrainingSystem:
    """训练系统"""
    
    def __init__(self, data_manager: PlayerDataManager):
        """
        初始化训练系统
        
        Args:
            data_manager: 球员数据管理器
        """
        self.data_manager = data_manager
        
        # 训练次数跟踪（每天重置）
        self._team_training_count: int = 0  # 今日全队训练次数
        self._individual_training_count: Dict[str, int] = {}  # 今日各球员单独训练次数 {player_id: count}
        self._current_training_date: Optional[str] = None  # 当前训练日期
    
    def reset_daily_training_counts(self, date: str = None) -> None:
        """
        重置每日训练次数（新的一天开始时调用）
        
        Args:
            date: 当前日期，用于跟踪
        """
        self._team_training_count = 0
        self._individual_training_count = {}
        self._current_training_date = date
    
    def _check_and_reset_if_new_day(self, date: str = None) -> None:
        """
        检查是否是新的一天，如果是则重置训练次数
        
        Args:
            date: 当前日期
        """
        if date and date != self._current_training_date:
            self.reset_daily_training_counts(date)
    
    def get_team_training_remaining(self) -> int:
        """
        获取今日剩余全队训练次数
        
        Returns:
            剩余全队训练次数
        """
        return max(0, MAX_TEAM_TRAINING_PER_DAY - self._team_training_count)
    
    def get_individual_training_remaining(self, player_id: str) -> int:
        """
        获取指定球员今日剩余单独训练次数
        
        Args:
            player_id: 球员ID
            
        Returns:
            剩余单独训练次数
        """
        used = self._individual_training_count.get(player_id, 0)
        return max(0, MAX_INDIVIDUAL_TRAINING_PER_PLAYER - used)
    
    def get_training_status(self) -> Dict:
        """
        获取当前训练状态
        
        Returns:
            训练状态字典，包含全队训练和各球员单独训练的剩余次数
        """
        return {
            "team_training_remaining": self.get_team_training_remaining(),
            "team_training_used": self._team_training_count,
            "max_team_training": MAX_TEAM_TRAINING_PER_DAY,
            "individual_training_used": self._individual_training_count.copy(),
            "max_individual_training": MAX_INDIVIDUAL_TRAINING_PER_PLAYER,
            "current_date": self._current_training_date
        }
    
    def get_training_state_for_save(self) -> Dict:
        """
        获取训练状态用于存档
        
        Returns:
            训练状态字典
        """
        return {
            "team_training_count": self._team_training_count,
            "individual_training_count": self._individual_training_count.copy(),
            "training_date": self._current_training_date
        }
    
    def restore_training_state(self, state: Dict) -> None:
        """
        从存档恢复训练状态
        
        Args:
            state: 训练状态字典
        """
        if state:
            self._team_training_count = state.get("team_training_count", 0)
            self._individual_training_count = state.get("individual_training_count", {})
            self._current_training_date = state.get("training_date", None)
    
    @staticmethod
    def get_available_programs() -> List[TrainingProgram]:
        """
        获取所有可用的训练项目
        
        Returns:
            训练项目列表
        """
        return TRAINING_PROGRAMS.copy()
    
    def execute_training(self, player: Player, program: TrainingProgram) -> Dict:
        """
        执行单个球员的训练
        
        训练会提升目标属性的训练点数0-2点（根据训练项目的boost_min和boost_max），
        当训练点数达到20时，该属性+1，训练点数重置。
        当累积5次属性+1后，总评+1，属性提升计数重置。
        
        Args:
            player: 要训练的球员
            program: 训练项目
            
        Returns:
            训练结果字典，包含:
            - training_points_gained: 获得的训练点数
            - attribute_upgraded: 是否触发属性+1
            - overall_upgraded: 是否触发总评+1
            - current_training_points: 当前训练点数
            - current_attribute_upgrades: 当前属性提升计数
            
        Requirements: 3.2
        """
        attr_name = program.target_attribute
        
        # 确保训练点数字典存在
        if not hasattr(player, 'training_points') or player.training_points is None:
            player.training_points = {
                "offense": 0, "defense": 0, "three_point": 0,
                "rebounding": 0, "passing": 0, "stamina": 0
            }
        if not hasattr(player, 'attribute_upgrades') or player.attribute_upgrades is None:
            player.attribute_upgrades = 0
        
        # 计算训练点数提升（0-2点，根据训练项目配置）
        points_gained = random.randint(program.boost_min, program.boost_max)
        
        # 更新训练点数
        current_points = player.training_points.get(attr_name, 0)
        new_points = current_points + points_gained
        
        result = {
            "training_points_gained": points_gained,
            "attribute_upgraded": False,
            "overall_upgraded": False,
            "current_training_points": new_points,
            "current_attribute_upgrades": player.attribute_upgrades
        }
        
        # 检查是否达到属性提升阈值
        if new_points >= TRAINING_POINTS_PER_UPGRADE:
            # 获取当前属性值
            current_attr_value = getattr(player, attr_name, 0)
            
            # 属性+1，但不超过上限
            if current_attr_value < ATTRIBUTE_MAX:
                setattr(player, attr_name, current_attr_value + 1)
                result["attribute_upgraded"] = True
                
                # 重置训练点数（保留溢出部分）
                new_points = new_points - TRAINING_POINTS_PER_UPGRADE
                
                # 增加属性提升计数
                player.attribute_upgrades += 1
                result["current_attribute_upgrades"] = player.attribute_upgrades
                
                # 检查是否达到总评提升阈值
                if player.attribute_upgrades >= ATTRIBUTE_UPGRADES_PER_OVERALL:
                    # 总评+1，但不超过上限
                    if player.overall < ATTRIBUTE_MAX:
                        player.overall += 1
                        result["overall_upgraded"] = True
                    
                    # 重置属性提升计数
                    player.attribute_upgrades = 0
                    result["current_attribute_upgrades"] = 0
            else:
                # 属性已达上限，训练点数不再累积
                new_points = TRAINING_POINTS_PER_UPGRADE
        
        # 更新训练点数
        player.training_points[attr_name] = new_points
        result["current_training_points"] = new_points
        
        return result
    
    def _validate_team_access(self, team: Team) -> None:
        """
        验证球队是否有训练权限
        
        只有玩家控制的球队可以训练，AI球队不能训练
        
        Args:
            team: 要验证的球队
            
        Raises:
            TrainingAccessError: 如果球队没有训练权限
            
        Requirements: 3.4
        """
        if not team.is_player_controlled:
            raise TrainingAccessError(
                f"球队 '{team.name}' 是AI控制的球队，无法进行训练操作"
            )
    
    def _validate_team_training_limit(self) -> None:
        """
        验证全队训练次数是否已达上限
        
        Raises:
            TrainingLimitError: 如果全队训练次数已达上限
        """
        if self._team_training_count >= MAX_TEAM_TRAINING_PER_DAY:
            raise TrainingLimitError(
                f"今日全队训练次数已达上限（{MAX_TEAM_TRAINING_PER_DAY}次）"
            )
    
    def _validate_individual_training_limit(self, player_id: str, player_name: str = "") -> None:
        """
        验证球员单独训练次数是否已达上限
        
        Args:
            player_id: 球员ID
            player_name: 球员名称（用于错误消息）
            
        Raises:
            TrainingLimitError: 如果球员单独训练次数已达上限
        """
        used = self._individual_training_count.get(player_id, 0)
        if used >= MAX_INDIVIDUAL_TRAINING_PER_PLAYER:
            name_str = f"'{player_name}'" if player_name else f"ID:{player_id}"
            raise TrainingLimitError(
                f"球员{name_str}今日单独训练次数已达上限（{MAX_INDIVIDUAL_TRAINING_PER_PLAYER}次）"
            )
    
    def apply_team_training(self, team: Team, program: TrainingProgram, 
                            current_date: str = None) -> Dict[str, Dict]:
        """
        对整个球队执行训练
        
        只有玩家控制的球队可以训练，AI球队训练操作会被拒绝。
        每天最多进行2次全队训练。
        
        Args:
            team: 要训练的球队
            program: 训练项目
            current_date: 当前日期（用于重置每日训练次数）
            
        Returns:
            字典，键为球员ID，值为训练结果字典
            
        Raises:
            TrainingAccessError: 如果是AI控制的球队
            TrainingLimitError: 如果全队训练次数已达上限
            
        Requirements: 3.1, 3.4
        """
        # 检查是否是新的一天
        self._check_and_reset_if_new_day(current_date)
        
        # 验证训练权限
        self._validate_team_access(team)
        
        # 验证全队训练次数限制
        self._validate_team_training_limit()
        
        results = {}
        roster = self.data_manager.get_team_roster(team.id)
        
        for player in roster:
            # 跳过受伤球员
            if player.is_injured:
                results[player.id] = {
                    "training_points_gained": 0,
                    "attribute_upgraded": False,
                    "overall_upgraded": False,
                    "current_training_points": player.training_points.get(program.target_attribute, 0) if hasattr(player, 'training_points') and player.training_points else 0,
                    "current_attribute_upgrades": player.attribute_upgrades if hasattr(player, 'attribute_upgrades') else 0,
                    "skipped": True
                }
                continue
            
            result = self.execute_training(player, program)
            result["skipped"] = False
            results[player.id] = result
        
        # 增加全队训练计数
        self._team_training_count += 1
        
        return results
    
    def train_single_player(self, team: Team, player_id: str, 
                            program: TrainingProgram,
                            current_date: str = None) -> Dict:
        """
        训练单个球员
        
        只有玩家控制的球队可以训练，AI球队训练操作会被拒绝。
        每个球员每天最多进行2次单独训练。
        
        Args:
            team: 球员所属球队
            player_id: 球员ID
            program: 训练项目
            current_date: 当前日期（用于重置每日训练次数）
            
        Returns:
            训练结果字典
            
        Raises:
            TrainingAccessError: 如果是AI控制的球队
            TrainingLimitError: 如果球员单独训练次数已达上限
            ValueError: 如果球员不存在或不属于该球队
            
        Requirements: 3.1, 3.4
        """
        # 检查是否是新的一天
        self._check_and_reset_if_new_day(current_date)
        
        # 验证训练权限
        self._validate_team_access(team)
        
        # 获取球员
        player = self.data_manager.get_player(player_id)
        if player is None:
            raise ValueError(f"球员 '{player_id}' 不存在")
        
        if player.team_id != team.id:
            raise ValueError(f"球员 '{player.name}' 不属于球队 '{team.name}'")
        
        # 验证球员单独训练次数限制
        self._validate_individual_training_limit(player_id, player.name)
        
        # 检查伤病状态
        if player.is_injured:
            return {
                "training_points_gained": 0,
                "attribute_upgraded": False,
                "overall_upgraded": False,
                "current_training_points": player.training_points.get(program.target_attribute, 0) if hasattr(player, 'training_points') and player.training_points else 0,
                "current_attribute_upgrades": player.attribute_upgrades if hasattr(player, 'attribute_upgrades') else 0,
                "skipped": True
            }
        
        result = self.execute_training(player, program)
        result["skipped"] = False
        
        # 增加球员单独训练计数
        self._individual_training_count[player_id] = self._individual_training_count.get(player_id, 0) + 1
        
        return result
    
    def can_train(self, team: Team) -> bool:
        """
        检查球队是否可以进行训练
        
        Args:
            team: 要检查的球队
            
        Returns:
            True如果可以训练，False如果不能
            
        Requirements: 3.4
        """
        return team.is_player_controlled
    
    def get_program_by_name(self, name: str) -> Optional[TrainingProgram]:
        """
        根据名称获取训练项目
        
        Args:
            name: 训练项目名称
            
        Returns:
            训练项目，不存在则返回None
        """
        for program in TRAINING_PROGRAMS:
            if program.name == name:
                return program
        return None
    
    def get_program_by_attribute(self, attribute: str) -> Optional[TrainingProgram]:
        """
        根据目标属性获取训练项目
        
        Args:
            attribute: 目标属性名称
            
        Returns:
            训练项目，不存在则返回None
        """
        for program in TRAINING_PROGRAMS:
            if program.target_attribute == attribute:
                return program
        return None
