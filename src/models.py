"""
华夏篮球联赛教练模拟器 - 数据模型定义

使用dataclass定义球员、球队、比赛统计等核心数据结构
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class Position(str, Enum):
    """球员位置枚举"""
    PG = "PG"  # 控球后卫
    SG = "SG"  # 得分后卫
    SF = "SF"  # 小前锋
    PF = "PF"  # 大前锋
    C = "C"    # 中锋


class TeamStatus(str, Enum):
    """球队状态枚举"""
    CONTENDING = "contending"    # 争冠
    REBUILDING = "rebuilding"    # 重建
    STABLE = "stable"            # 稳定


class SeasonPhase(str, Enum):
    """赛季阶段枚举"""
    REGULAR = "regular"          # 常规赛
    PLAYOFF = "playoff"          # 季后赛


@dataclass
class GameStats:
    """单场比赛球员数据"""
    points: int = 0
    rebounds: int = 0
    assists: int = 0
    steals: int = 0
    blocks: int = 0
    turnovers: int = 0
    minutes: int = 0
    team_id: str = ""  # 比赛时球员所属球队ID（用于交易后正确显示历史数据）


@dataclass
class Player:
    """球员数据模型"""
    # 基本信息
    id: str
    name: str
    team_id: str
    position: str  # PG/SG/SF/PF/C
    age: int
    is_foreign: bool = False
    
    # 细项属性 (0-99)
    offense: int = 70
    defense: int = 70
    three_point: int = 70
    rebounding: int = 70
    passing: int = 70
    stamina: int = 70
    
    # 总评 (自动计算)
    overall: int = 70
    
    # 技术标签和交易指数
    skill_tags: List[str] = field(default_factory=list)
    trade_index: int = 50  # 0-100，越低越不可能被交易
    
    # 伤病状态
    is_injured: bool = False
    injury_days: int = 0
    
    # 被裁状态（外援被替换后标记为被裁，不再出战比赛）
    is_waived: bool = False
    
    # 训练进度系统
    # 单项训练点数（每个属性累积20点后该属性+1）
    training_points: Dict[str, int] = field(default_factory=lambda: {
        "offense": 0, "defense": 0, "three_point": 0,
        "rebounding": 0, "passing": 0, "stamina": 0
    })
    # 单项提升计数（累积5次单项+1后总评+1）
    attribute_upgrades: int = 0
    
    # 赛季统计 (场均)
    games_played: int = 0
    avg_points: float = 0.0
    avg_rebounds: float = 0.0
    avg_assists: float = 0.0
    avg_steals: float = 0.0
    avg_blocks: float = 0.0
    avg_turnovers: float = 0.0
    avg_minutes: float = 0.0
    
    # 累计统计（用于计算场均）
    total_points: int = 0
    total_rebounds: int = 0
    total_assists: int = 0
    total_steals: int = 0
    total_blocks: int = 0
    total_turnovers: int = 0
    total_minutes: int = 0
    
    # 季后赛统计 (场均)
    playoff_games_played: int = 0
    playoff_avg_points: float = 0.0
    playoff_avg_rebounds: float = 0.0
    playoff_avg_assists: float = 0.0
    playoff_avg_steals: float = 0.0
    playoff_avg_blocks: float = 0.0
    playoff_avg_turnovers: float = 0.0
    playoff_avg_minutes: float = 0.0
    
    # 季后赛累计统计
    playoff_total_points: int = 0
    playoff_total_rebounds: int = 0
    playoff_total_assists: int = 0
    playoff_total_steals: int = 0
    playoff_total_blocks: int = 0
    playoff_total_turnovers: int = 0
    playoff_total_minutes: int = 0


@dataclass
class Team:
    """球队数据模型"""
    id: str
    name: str
    city: str
    status: str = "stable"  # contending/rebuilding/stable
    is_player_controlled: bool = False
    roster: List[str] = field(default_factory=list)  # 球员ID列表
    budget: int = 200  # 球队经费（万元），初始200万


@dataclass
class Standing:
    """排名数据"""
    team_id: str
    wins: int = 0
    losses: int = 0
    win_pct: float = 0.0
    games_behind: float = 0.0
    
    def update_win_pct(self) -> None:
        """更新胜率"""
        total_games = self.wins + self.losses
        if total_games > 0:
            self.win_pct = self.wins / total_games
        else:
            self.win_pct = 0.0


@dataclass
class MatchResult:
    """比赛结果"""
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    narrative: str = ""  # 比赛过程描述
    player_stats: dict = field(default_factory=dict)  # 球员单场数据 {player_id: GameStats}
    
    # 新增字段 - 比赛过程展示
    quarter_scores: List[tuple] = field(default_factory=list)  # [(主队Q1, 客队Q1), (主队Q2, 客队Q2), ...]
    highlights: List[str] = field(default_factory=list)  # 精彩时刻列表
    commentary: str = ""  # 完整解说文本
    
    # 新增字段 - 记录比赛时的球员列表（用于交易后正确显示历史数据）
    home_player_ids: List[str] = field(default_factory=list)
    away_player_ids: List[str] = field(default_factory=list)
    
    @property
    def winner_id(self) -> str:
        """获取胜者ID"""
        return self.home_team_id if self.home_score > self.away_score else self.away_team_id
    
    @property
    def loser_id(self) -> str:
        """获取败者ID"""
        return self.away_team_id if self.home_score > self.away_score else self.home_team_id


@dataclass
class PlayoffSeries:
    """季后赛系列赛"""
    team1_id: str
    team2_id: str
    team1_wins: int = 0
    team2_wins: int = 0
    round_name: str = "quarter"  # play_in/quarter/semi/final
    games: List['MatchResult'] = field(default_factory=list)  # 存储每场比赛结果
    
    @property
    def wins_needed(self) -> int:
        """获取晋级所需胜场"""
        return 2 if self.round_name == "play_in" else 4
    
    @property
    def is_complete(self) -> bool:
        """系列赛是否结束"""
        return self.team1_wins >= self.wins_needed or self.team2_wins >= self.wins_needed
    
    @property
    def winner_id(self) -> Optional[str]:
        """获取系列赛胜者"""
        if self.team1_wins >= self.wins_needed:
            return self.team1_id
        elif self.team2_wins >= self.wins_needed:
            return self.team2_id
        return None
    
    def add_game_result(self, result: 'MatchResult') -> None:
        """添加比赛结果到系列赛"""
        self.games.append(result)


@dataclass
class ScheduledGame:
    """赛程中的比赛"""
    date: str  # 格式: YYYY-MM-DD
    home_team_id: str
    away_team_id: str
    is_played: bool = False
    result: Optional[MatchResult] = None


@dataclass
class TradeProposal:
    """交易提案"""
    offering_team_id: str
    receiving_team_id: str
    players_offered: List[str] = field(default_factory=list)  # 提供的球员ID
    players_requested: List[str] = field(default_factory=list)  # 请求的球员ID


@dataclass
class TrainingProgram:
    """训练项目"""
    name: str
    target_attribute: str
    boost_min: int = 1
    boost_max: int = 2


@dataclass
class GameState:
    """游戏状态 - 用于存档"""
    current_date: str
    player_team_id: str
    season_phase: str = "regular"  # regular/playoff
    teams: dict = field(default_factory=dict)  # {team_id: Team}
    players: dict = field(default_factory=dict)  # {player_id: Player}
    standings: List[Standing] = field(default_factory=list)
    schedule: List[ScheduledGame] = field(default_factory=list)
    playoff_bracket: dict = field(default_factory=dict)
    free_agents: List[str] = field(default_factory=list)  # 自由球员ID列表
    # 季后赛状态字段 (Requirements 6.1, 6.2, 6.3)
    is_playoff_phase: bool = False  # 是否在季后赛阶段
    player_eliminated: bool = False  # 玩家球队是否已被淘汰
    # 外援市场已用名字状态
    foreign_used_names: dict = field(default_factory=dict)  # {"used_first_names": [], "used_last_names": []}
    # 训练次数状态
    training_state: dict = field(default_factory=lambda: {
        "team_training_count": 0,
        "individual_training_count": {},
        "training_date": None
    })
