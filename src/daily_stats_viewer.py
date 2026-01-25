"""
华夏篮球联赛教练模拟器 - 当日比赛数据查看器

提供当日所有比赛的数据统计查看功能
Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from src.models import (
    Team, Player, ScheduledGame, MatchResult, GameStats
)
from src.season_manager import SeasonManager


@dataclass
class DailyGameSummary:
    """当日比赛摘要"""
    date: str
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    home_score: int
    away_score: int
    is_played: bool
    player_stats: Dict[str, GameStats] = field(default_factory=dict)
    quarter_scores: List[tuple] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)


class DailyStatsViewer:
    """
    当日比赛数据查看器
    
    提供当日所有比赛的数据统计查看功能，包括：
    - 获取指定日期的所有比赛
    - 获取单场比赛的详细数据统计
    - 支持AI球队之间的比赛
    
    Requirements:
    - 5.1: 显示当日所有比赛列表
    - 5.2: 显示比赛最终比分
    - 5.3: 显示所有参赛球员的个人数据
    - 5.4: 支持AI球队比赛的数据查看
    - 5.5: 无比赛时显示提示信息
    """
    
    # 球队ID到球员ID前缀的映射（用于旧数据兼容）
    TEAM_TO_PLAYER_PREFIX = {
        "team_liaoning": "player_ln",
        "team_guangdong": "player_gd",
        "team_zhejiang": "player_zj",
        "team_shanghai": "player_sh",
        "team_beijing": "player_bj",
        "team_shandong": "player_sd",
        "team_xinjiang": "player_xj",
        "team_shenzhen": "player_sz",
        "team_guangzhou": "player_gz",
        "team_jilin": "player_jl",
        "team_fujian": "player_fj",
        "team_jiangsu": "player_js",
        "team_shanxi": "player_sx",
        "team_sichuan": "player_sc",
        "team_qingdao": "player_qd",
        "team_nanjing": "player_nj",
        "team_tianjin": "player_tj",
        "team_ningbo": "player_nb",
        "team_beikong": "player_bk",
        "team_guangsha": "player_gs",
    }
    
    def __init__(
        self,
        season_manager: SeasonManager,
        teams: Dict[str, Team],
        players: Dict[str, Player]
    ):
        """
        初始化当日比赛数据查看器
        
        Args:
            season_manager: 赛季管理器
            teams: 球队字典 {team_id: Team}
            players: 球员字典 {player_id: Player}
        """
        self.season_manager = season_manager
        self.teams = teams
        self.players = players
    
    def _get_team_id_from_player_id(self, player_id: str, home_team_id: str, away_team_id: str) -> Optional[str]:
        """
        根据球员ID前缀推断球队ID（用于旧数据兼容）
        
        Args:
            player_id: 球员ID
            home_team_id: 主队ID
            away_team_id: 客队ID
            
        Returns:
            推断出的球队ID，如果无法推断则返回None
        """
        # 外援无法通过ID前缀推断
        if player_id.startswith("foreign_"):
            return None
        
        # 获取球员ID前缀（如 player_gd）
        parts = player_id.split("_")
        if len(parts) >= 2:
            prefix = f"{parts[0]}_{parts[1]}"
            
            # 检查是否匹配主队
            home_prefix = self.TEAM_TO_PLAYER_PREFIX.get(home_team_id)
            if home_prefix and prefix == home_prefix:
                return home_team_id
            
            # 检查是否匹配客队
            away_prefix = self.TEAM_TO_PLAYER_PREFIX.get(away_team_id)
            if away_prefix and prefix == away_prefix:
                return away_team_id
        
        return None
    
    def get_daily_games(self, date: str) -> List[Dict]:
        """
        获取指定日期的所有比赛及其统计
        
        包括玩家球队比赛和AI球队之间的比赛 (Requirements 5.1, 5.4)
        
        Args:
            date: 日期字符串 (YYYY-MM-DD格式)
            
        Returns:
            比赛列表，每个比赛包含:
            - date: 比赛日期
            - home_team_id: 主队ID
            - home_team_name: 主队名称
            - away_team_id: 客队ID
            - away_team_name: 客队名称
            - home_score: 主队得分
            - away_score: 客队得分
            - is_played: 是否已完成
            - player_stats: 球员数据统计
            - quarter_scores: 节次比分
            - highlights: 精彩时刻
            - message: 提示信息（无比赛时）
        """
        # 获取该日期的所有比赛（包括已完成和未完成的）
        all_games = self._get_all_games_for_date(date)
        
        # 如果没有比赛，返回空列表和提示信息 (Requirements 5.5)
        if not all_games:
            return []
        
        result = []
        for game in all_games:
            game_data = self._build_game_data(game)
            result.append(game_data)
        
        return result
    
    def _get_all_games_for_date(self, date: str) -> List[ScheduledGame]:
        """
        获取指定日期的所有比赛（包括已完成和未完成的）
        
        Args:
            date: 日期字符串
            
        Returns:
            比赛列表
        """
        return [
            game for game in self.season_manager.schedule
            if game.date == date
        ]
    
    def _build_game_data(self, game: ScheduledGame) -> Dict:
        """
        构建单场比赛的数据字典
        
        Args:
            game: 比赛对象
            
        Returns:
            比赛数据字典
        """
        home_team = self.teams.get(game.home_team_id)
        away_team = self.teams.get(game.away_team_id)
        
        home_team_name = home_team.name if home_team else "未知球队"
        away_team_name = away_team.name if away_team else "未知球队"
        
        game_data = {
            "date": game.date,
            "home_team_id": game.home_team_id,
            "home_team_name": home_team_name,
            "away_team_id": game.away_team_id,
            "away_team_name": away_team_name,
            "is_played": game.is_played,
            "home_score": 0,
            "away_score": 0,
            "player_stats": {},
            "quarter_scores": [],
            "highlights": [],
        }
        
        # 如果比赛已完成，添加比赛结果数据 (Requirements 5.2, 5.3)
        if game.is_played and game.result:
            result = game.result
            game_data["home_score"] = result.home_score
            game_data["away_score"] = result.away_score
            game_data["quarter_scores"] = result.quarter_scores
            game_data["highlights"] = result.highlights
            
            # 添加球员数据统计，传入比赛时的球员列表
            game_data["player_stats"] = self._format_player_stats(
                result.player_stats,
                game.home_team_id,
                game.away_team_id,
                result.home_player_ids,
                result.away_player_ids
            )
        
        return game_data
    
    def _format_player_stats(
        self,
        player_stats: Dict[str, GameStats],
        home_team_id: str,
        away_team_id: str,
        home_player_ids: List[str] = None,
        away_player_ids: List[str] = None
    ) -> Dict:
        """
        格式化球员数据统计
        
        Args:
            player_stats: 原始球员数据 {player_id: GameStats}
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_player_ids: 比赛时主队球员ID列表（用于交易后正确显示）
            away_player_ids: 比赛时客队球员ID列表（用于交易后正确显示）
            
        Returns:
            格式化后的球员数据，按球队分组:
            {
                "home_team": [...],
                "away_team": [...]
            }
        """
        home_stats = []
        away_stats = []
        
        # 将列表转换为集合以便快速查找
        home_player_set = set(home_player_ids) if home_player_ids else set()
        away_player_set = set(away_player_ids) if away_player_ids else set()
        
        for player_id, stats in player_stats.items():
            player = self.players.get(player_id)
            if not player:
                continue
            
            stat_entry = {
                "player_id": player_id,
                "player_name": player.name,
                "position": player.position,
                "points": stats.points,
                "rebounds": stats.rebounds,
                "assists": stats.assists,
                "steals": stats.steals,
                "blocks": stats.blocks,
                "turnovers": stats.turnovers,
                "minutes": stats.minutes,
            }
            
            # 判断球员归属的优先级：
            # 1. 使用 MatchResult 中记录的比赛时球员列表（最可靠）
            # 2. 使用 GameStats 中记录的比赛时球队ID
            # 3. 根据球员ID前缀推断球队（旧数据兼容，适用于本土球员）
            # 4. 回退到 player.team_id（可能因交易而不准确，仅用于外援）
            if home_player_set and player_id in home_player_set:
                home_stats.append(stat_entry)
            elif away_player_set and player_id in away_player_set:
                away_stats.append(stat_entry)
            elif stats.team_id:
                # 使用 GameStats 中记录的球队ID
                if stats.team_id == home_team_id:
                    home_stats.append(stat_entry)
                elif stats.team_id == away_team_id:
                    away_stats.append(stat_entry)
            else:
                # 尝试根据球员ID前缀推断球队（旧数据兼容）
                inferred_team_id = self._get_team_id_from_player_id(player_id, home_team_id, away_team_id)
                if inferred_team_id == home_team_id:
                    home_stats.append(stat_entry)
                elif inferred_team_id == away_team_id:
                    away_stats.append(stat_entry)
                else:
                    # 最后回退到当前球员的球队ID（仅用于外援等无法推断的情况）
                    if player.team_id == home_team_id:
                        home_stats.append(stat_entry)
                    elif player.team_id == away_team_id:
                        away_stats.append(stat_entry)
        
        # 按得分降序排序
        home_stats.sort(key=lambda x: x["points"], reverse=True)
        away_stats.sort(key=lambda x: x["points"], reverse=True)
        
        return {
            "home_team": home_stats,
            "away_team": away_stats,
        }
    
    def get_game_box_score(self, game: ScheduledGame) -> Dict:
        """
        获取单场比赛的详细数据统计（Box Score）
        
        Args:
            game: 比赛对象
            
        Returns:
            详细数据统计字典:
            - date: 比赛日期
            - home_team: 主队信息
            - away_team: 客队信息
            - home_score: 主队得分
            - away_score: 客队得分
            - quarter_scores: 节次比分
            - highlights: 精彩时刻
            - home_players: 主队球员数据列表
            - away_players: 客队球员数据列表
            - narrative: 比赛描述
        """
        home_team = self.teams.get(game.home_team_id)
        away_team = self.teams.get(game.away_team_id)
        
        box_score = {
            "date": game.date,
            "home_team": {
                "id": game.home_team_id,
                "name": home_team.name if home_team else "未知球队",
                "city": home_team.city if home_team else "",
            },
            "away_team": {
                "id": game.away_team_id,
                "name": away_team.name if away_team else "未知球队",
                "city": away_team.city if away_team else "",
            },
            "is_played": game.is_played,
            "home_score": 0,
            "away_score": 0,
            "quarter_scores": [],
            "highlights": [],
            "home_players": [],
            "away_players": [],
            "narrative": "",
        }
        
        if not game.is_played or not game.result:
            return box_score
        
        result = game.result
        box_score["home_score"] = result.home_score
        box_score["away_score"] = result.away_score
        box_score["quarter_scores"] = result.quarter_scores
        box_score["highlights"] = result.highlights
        box_score["narrative"] = result.narrative or result.commentary
        
        # 将比赛时的球员列表转换为集合以便快速查找
        home_player_set = set(result.home_player_ids) if result.home_player_ids else set()
        away_player_set = set(result.away_player_ids) if result.away_player_ids else set()
        
        # 获取球员详细数据
        for player_id, stats in result.player_stats.items():
            player = self.players.get(player_id)
            if not player:
                continue
            
            player_data = {
                "player_id": player_id,
                "player_name": player.name,
                "position": player.position,
                "points": stats.points,
                "rebounds": stats.rebounds,
                "assists": stats.assists,
                "steals": stats.steals,
                "blocks": stats.blocks,
                "turnovers": stats.turnovers,
                "minutes": stats.minutes,
                # 额外信息
                "is_foreign": player.is_foreign,
                "overall": player.overall,
            }
            
            # 判断球员归属的优先级：
            # 1. 使用 MatchResult 中记录的比赛时球员列表（最可靠）
            # 2. 使用 GameStats 中记录的比赛时球队ID
            # 3. 根据球员ID前缀推断球队（旧数据兼容，适用于本土球员）
            # 4. 回退到 player.team_id（可能因交易而不准确，仅用于外援）
            if home_player_set and player_id in home_player_set:
                box_score["home_players"].append(player_data)
            elif away_player_set and player_id in away_player_set:
                box_score["away_players"].append(player_data)
            elif stats.team_id:
                # 使用 GameStats 中记录的球队ID
                if stats.team_id == game.home_team_id:
                    box_score["home_players"].append(player_data)
                elif stats.team_id == game.away_team_id:
                    box_score["away_players"].append(player_data)
            else:
                # 尝试根据球员ID前缀推断球队（旧数据兼容）
                inferred_team_id = self._get_team_id_from_player_id(player_id, game.home_team_id, game.away_team_id)
                if inferred_team_id == game.home_team_id:
                    box_score["home_players"].append(player_data)
                elif inferred_team_id == game.away_team_id:
                    box_score["away_players"].append(player_data)
                else:
                    # 最后回退到当前球员的球队ID（仅用于外援等无法推断的情况）
                    if player.team_id == game.home_team_id:
                        box_score["home_players"].append(player_data)
                    elif player.team_id == game.away_team_id:
                        box_score["away_players"].append(player_data)
        
        # 按得分降序排序
        box_score["home_players"].sort(key=lambda x: x["points"], reverse=True)
        box_score["away_players"].sort(key=lambda x: x["points"], reverse=True)
        
        return box_score
    
    def get_played_games_for_date(self, date: str) -> List[ScheduledGame]:
        """
        获取指定日期已完成的比赛
        
        Args:
            date: 日期字符串
            
        Returns:
            已完成的比赛列表
        """
        return [
            game for game in self.season_manager.schedule
            if game.date == date and game.is_played
        ]
    
    def has_games_on_date(self, date: str) -> bool:
        """
        检查指定日期是否有比赛
        
        Args:
            date: 日期字符串
            
        Returns:
            是否有比赛
        """
        return len(self._get_all_games_for_date(date)) > 0
    
    def get_no_games_message(self) -> str:
        """
        获取无比赛时的提示信息 (Requirements 5.5)
        
        Returns:
            提示信息字符串
        """
        return "今日无比赛"
    
    def get_daily_summary(self, date: str) -> Dict:
        """
        获取指定日期的比赛摘要
        
        Args:
            date: 日期字符串
            
        Returns:
            摘要字典:
            - date: 日期
            - total_games: 总比赛数
            - played_games: 已完成比赛数
            - games: 比赛列表
            - message: 提示信息（无比赛时）
        """
        games = self.get_daily_games(date)
        
        if not games:
            return {
                "date": date,
                "total_games": 0,
                "played_games": 0,
                "games": [],
                "message": self.get_no_games_message(),
            }
        
        played_count = sum(1 for g in games if g["is_played"])
        
        return {
            "date": date,
            "total_games": len(games),
            "played_games": played_count,
            "games": games,
            "message": None,
        }
