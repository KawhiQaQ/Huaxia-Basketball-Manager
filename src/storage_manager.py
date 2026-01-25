"""
华夏篮球联赛教练模拟器 - 存档管理器

负责游戏状态的保存和加载
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import asdict

from src.models import (
    GameState, Player, Team, Standing, ScheduledGame, 
    PlayoffSeries, MatchResult, GameStats
)


# 存档目录
SAVE_DIR = "saves/"


class SaveLoadError(Exception):
    """存档/读档错误"""
    pass


class CorruptedSaveError(SaveLoadError):
    """存档数据损坏错误"""
    pass


class StorageManager:
    """存档管理器"""
    
    def __init__(self, save_dir: str = SAVE_DIR):
        """
        初始化存档管理器
        
        Args:
            save_dir: 存档目录路径
        """
        self.save_dir = save_dir
        self._ensure_save_dir()
    
    def _ensure_save_dir(self) -> None:
        """确保存档目录存在"""
        os.makedirs(self.save_dir, exist_ok=True)
    
    def _get_save_path(self, slot: int) -> str:
        """
        获取存档文件路径
        
        Args:
            slot: 存档槽位号
            
        Returns:
            存档文件完整路径
        """
        return os.path.join(self.save_dir, f"save_{slot}.json")
    
    def save_game(self, state: GameState, slot: int) -> None:
        """
        保存游戏状态到指定槽位
        
        Args:
            state: 游戏状态对象
            slot: 存档槽位号 (1-10)
            
        Raises:
            SaveLoadError: 保存失败时抛出
        """
        if slot < 1 or slot > 10:
            raise SaveLoadError(f"无效的存档槽位: {slot}，有效范围为1-10")
        
        try:
            save_data = self._serialize_game_state(state)
            save_data["_meta"] = {
                "save_time": datetime.now().isoformat(),
                "version": "1.0",
                "slot": slot
            }
            
            save_path = self._get_save_path(slot)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            raise SaveLoadError(f"保存游戏失败: {str(e)}")
    
    def load_game(self, slot: int) -> GameState:
        """
        从指定槽位加载游戏状态
        
        Args:
            slot: 存档槽位号 (1-10)
            
        Returns:
            游戏状态对象
            
        Raises:
            SaveLoadError: 存档不存在时抛出
            CorruptedSaveError: 存档数据损坏时抛出
        """
        if slot < 1 or slot > 10:
            raise SaveLoadError(f"无效的存档槽位: {slot}，有效范围为1-10")
        
        save_path = self._get_save_path(slot)
        
        if not os.path.exists(save_path):
            raise SaveLoadError(f"存档槽位 {slot} 不存在")
        
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CorruptedSaveError(f"存档数据损坏，无法解析JSON: {str(e)}")
        except Exception as e:
            raise SaveLoadError(f"读取存档失败: {str(e)}")
        
        # 验证存档数据完整性
        self._validate_save_data(save_data)
        
        # 反序列化游戏状态
        return self._deserialize_game_state(save_data)

    
    def list_saves(self) -> List[Tuple[int, str, str, str]]:
        """
        列出所有存档
        
        Returns:
            存档列表，每项为 (槽位号, 保存时间, 球队名称, 赛季阶段)
        """
        saves = []
        
        for slot in range(1, 11):
            save_path = self._get_save_path(slot)
            if os.path.exists(save_path):
                try:
                    with open(save_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    meta = data.get("_meta", {})
                    save_time = meta.get("save_time", "未知时间")
                    
                    # 获取玩家球队名称
                    player_team_id = data.get("player_team_id", "")
                    teams = data.get("teams", {})
                    team_name = "未知球队"
                    if player_team_id and player_team_id in teams:
                        team_name = teams[player_team_id].get("name", "未知球队")
                    
                    season_phase = data.get("season_phase", "regular")
                    phase_name = "常规赛" if season_phase == "regular" else "季后赛"
                    
                    saves.append((slot, save_time, team_name, phase_name))
                    
                except (json.JSONDecodeError, KeyError):
                    # 存档损坏，仍然显示但标记为损坏
                    saves.append((slot, "存档损坏", "无法读取", ""))
        
        return saves
    
    def delete_save(self, slot: int) -> bool:
        """
        删除指定槽位的存档
        
        Args:
            slot: 存档槽位号
            
        Returns:
            是否删除成功
        """
        if slot < 1 or slot > 10:
            return False
        
        save_path = self._get_save_path(slot)
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
                return True
            except OSError:
                return False
        return False
    
    def save_exists(self, slot: int) -> bool:
        """
        检查指定槽位是否有存档
        
        Args:
            slot: 存档槽位号
            
        Returns:
            是否存在存档
        """
        if slot < 1 or slot > 10:
            return False
        return os.path.exists(self._get_save_path(slot))
    
    def _serialize_game_state(self, state: GameState) -> Dict[str, Any]:
        """
        将游戏状态序列化为字典
        
        Args:
            state: 游戏状态对象
            
        Returns:
            可JSON序列化的字典
        """
        return {
            "current_date": state.current_date,
            "player_team_id": state.player_team_id,
            "season_phase": state.season_phase,
            "teams": self._serialize_teams(state.teams),
            "players": self._serialize_players(state.players),
            "standings": self._serialize_standings(state.standings),
            "schedule": self._serialize_schedule(state.schedule),
            "playoff_bracket": self._serialize_playoff_bracket(state.playoff_bracket),
            "free_agents": state.free_agents,
            # 季后赛状态字段 (Requirements 6.1, 6.2, 6.3)
            "is_playoff_phase": state.is_playoff_phase,
            "player_eliminated": state.player_eliminated,
            # 外援市场已用名字状态
            "foreign_used_names": state.foreign_used_names,
            # 训练次数状态
            "training_state": state.training_state
        }
    
    def _serialize_teams(self, teams: Dict[str, Team]) -> Dict[str, Dict]:
        """序列化球队数据"""
        result = {}
        for team_id, team in teams.items():
            result[team_id] = {
                "id": team.id,
                "name": team.name,
                "city": team.city,
                "status": team.status,
                "is_player_controlled": team.is_player_controlled,
                "roster": team.roster,
                "budget": team.budget  # 保存球队经费
            }
        return result
    
    def _serialize_players(self, players: Dict[str, Player]) -> Dict[str, Dict]:
        """序列化球员数据"""
        result = {}
        for player_id, player in players.items():
            result[player_id] = {
                "id": player.id,
                "name": player.name,
                "team_id": player.team_id,
                "position": player.position,
                "age": player.age,
                "is_foreign": player.is_foreign,
                "offense": player.offense,
                "defense": player.defense,
                "three_point": player.three_point,
                "rebounding": player.rebounding,
                "passing": player.passing,
                "stamina": player.stamina,
                "overall": player.overall,
                "skill_tags": player.skill_tags,
                "trade_index": player.trade_index,
                "is_injured": player.is_injured,
                "injury_days": player.injury_days,
                "is_waived": player.is_waived,
                # 训练进度系统字段
                "training_points": player.training_points if hasattr(player, 'training_points') and player.training_points else {
                    "offense": 0, "defense": 0, "three_point": 0,
                    "rebounding": 0, "passing": 0, "stamina": 0
                },
                "attribute_upgrades": player.attribute_upgrades if hasattr(player, 'attribute_upgrades') else 0,
                # 常规赛统计
                "games_played": player.games_played,
                "avg_points": player.avg_points,
                "avg_rebounds": player.avg_rebounds,
                "avg_assists": player.avg_assists,
                "avg_steals": player.avg_steals,
                "avg_blocks": player.avg_blocks,
                "avg_turnovers": player.avg_turnovers,
                "avg_minutes": player.avg_minutes,
                "total_points": player.total_points,
                "total_rebounds": player.total_rebounds,
                "total_assists": player.total_assists,
                "total_steals": player.total_steals,
                "total_blocks": player.total_blocks,
                "total_turnovers": player.total_turnovers,
                "total_minutes": player.total_minutes,
                # 季后赛统计
                "playoff_games_played": player.playoff_games_played,
                "playoff_avg_points": player.playoff_avg_points,
                "playoff_avg_rebounds": player.playoff_avg_rebounds,
                "playoff_avg_assists": player.playoff_avg_assists,
                "playoff_avg_steals": player.playoff_avg_steals,
                "playoff_avg_blocks": player.playoff_avg_blocks,
                "playoff_avg_turnovers": player.playoff_avg_turnovers,
                "playoff_avg_minutes": player.playoff_avg_minutes,
                "playoff_total_points": player.playoff_total_points,
                "playoff_total_rebounds": player.playoff_total_rebounds,
                "playoff_total_assists": player.playoff_total_assists,
                "playoff_total_steals": player.playoff_total_steals,
                "playoff_total_blocks": player.playoff_total_blocks,
                "playoff_total_turnovers": player.playoff_total_turnovers,
                "playoff_total_minutes": player.playoff_total_minutes
            }
        return result

    
    def _serialize_standings(self, standings: List[Standing]) -> List[Dict]:
        """序列化排行榜数据"""
        result = []
        for standing in standings:
            result.append({
                "team_id": standing.team_id,
                "wins": standing.wins,
                "losses": standing.losses,
                "win_pct": standing.win_pct,
                "games_behind": standing.games_behind
            })
        return result
    
    def _serialize_schedule(self, schedule: List[ScheduledGame]) -> List[Dict]:
        """序列化赛程数据"""
        result = []
        for game in schedule:
            game_dict = {
                "date": game.date,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "is_played": game.is_played,
                "result": None
            }
            if game.result:
                game_dict["result"] = {
                    "home_team_id": game.result.home_team_id,
                    "away_team_id": game.result.away_team_id,
                    "home_score": game.result.home_score,
                    "away_score": game.result.away_score,
                    "narrative": game.result.narrative,
                    "player_stats": self._serialize_player_stats(game.result.player_stats),
                    "home_player_ids": game.result.home_player_ids,  # 保存比赛时的球员列表
                    "away_player_ids": game.result.away_player_ids   # 保存比赛时的球员列表
                }
            result.append(game_dict)
        return result
    
    def _serialize_player_stats(self, player_stats: Dict) -> Dict:
        """序列化球员比赛统计"""
        result = {}
        for player_id, stats in player_stats.items():
            if isinstance(stats, GameStats):
                result[player_id] = {
                    "points": stats.points,
                    "rebounds": stats.rebounds,
                    "assists": stats.assists,
                    "steals": stats.steals,
                    "blocks": stats.blocks,
                    "turnovers": stats.turnovers,
                    "minutes": stats.minutes,
                    "team_id": stats.team_id  # 保存比赛时球员所属球队
                }
            elif isinstance(stats, dict):
                result[player_id] = stats
        return result
    
    def _serialize_playoff_bracket(self, bracket: Dict) -> Dict:
        """序列化季后赛对阵数据"""
        result = {}
        for key, value in bracket.items():
            if isinstance(value, PlayoffSeries):
                result[key] = {
                    "_type": "PlayoffSeries",
                    "team1_id": value.team1_id,
                    "team2_id": value.team2_id,
                    "team1_wins": value.team1_wins,
                    "team2_wins": value.team2_wins,
                    "round_name": value.round_name,
                    "games": self._serialize_match_results(value.games)
                }
            else:
                # 种子球队ID (字符串)
                result[key] = value
        return result
    
    def _serialize_match_results(self, games: List[MatchResult]) -> List[Dict]:
        """序列化比赛结果列表"""
        result = []
        for game in games:
            if game:
                result.append({
                    "home_team_id": game.home_team_id,
                    "away_team_id": game.away_team_id,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "narrative": game.narrative,
                    "player_stats": self._serialize_player_stats(game.player_stats),
                    "quarter_scores": game.quarter_scores,
                    "highlights": game.highlights,
                    "commentary": game.commentary,
                    "home_player_ids": game.home_player_ids,  # 保存比赛时的球员列表
                    "away_player_ids": game.away_player_ids   # 保存比赛时的球员列表
                })
        return result
    
    def _deserialize_game_state(self, data: Dict) -> GameState:
        """
        将字典反序列化为游戏状态
        
        Args:
            data: 存档数据字典
            
        Returns:
            游戏状态对象
        """
        return GameState(
            current_date=data.get("current_date", "2024-10-15"),
            player_team_id=data.get("player_team_id", ""),
            season_phase=data.get("season_phase", "regular"),
            teams=self._deserialize_teams(data.get("teams", {})),
            players=self._deserialize_players(data.get("players", {})),
            standings=self._deserialize_standings(data.get("standings", [])),
            schedule=self._deserialize_schedule(data.get("schedule", [])),
            playoff_bracket=self._deserialize_playoff_bracket(data.get("playoff_bracket", {})),
            free_agents=data.get("free_agents", []),
            # 季后赛状态字段 (Requirements 6.1, 6.2, 6.3)
            is_playoff_phase=data.get("is_playoff_phase", False),
            player_eliminated=data.get("player_eliminated", False),
            # 外援市场已用名字状态
            foreign_used_names=data.get("foreign_used_names", {}),
            # 训练次数状态
            training_state=data.get("training_state", {
                "team_training_count": 0,
                "individual_training_count": {},
                "training_date": None
            })
        )
    
    def _deserialize_teams(self, teams_data: Dict) -> Dict[str, Team]:
        """反序列化球队数据"""
        result = {}
        for team_id, team_dict in teams_data.items():
            result[team_id] = Team(
                id=team_dict.get("id", team_id),
                name=team_dict.get("name", ""),
                city=team_dict.get("city", ""),
                status=team_dict.get("status", "stable"),
                is_player_controlled=team_dict.get("is_player_controlled", False),
                roster=team_dict.get("roster", []),
                budget=team_dict.get("budget", 200)  # 加载球队经费，默认200万
            )
        return result
    
    def _deserialize_players(self, players_data: Dict) -> Dict[str, Player]:
        """反序列化球员数据"""
        result = {}
        for player_id, player_dict in players_data.items():
            result[player_id] = Player(
                id=player_dict.get("id", player_id),
                name=player_dict.get("name", ""),
                team_id=player_dict.get("team_id", ""),
                position=player_dict.get("position", "SF"),
                age=player_dict.get("age", 25),
                is_foreign=player_dict.get("is_foreign", False),
                offense=player_dict.get("offense", 70),
                defense=player_dict.get("defense", 70),
                three_point=player_dict.get("three_point", 70),
                rebounding=player_dict.get("rebounding", 70),
                passing=player_dict.get("passing", 70),
                stamina=player_dict.get("stamina", 70),
                overall=player_dict.get("overall", 70),
                skill_tags=player_dict.get("skill_tags", []),
                trade_index=player_dict.get("trade_index", 50),
                is_injured=player_dict.get("is_injured", False),
                injury_days=player_dict.get("injury_days", 0),
                is_waived=player_dict.get("is_waived", False),
                # 训练进度系统字段
                training_points=player_dict.get("training_points", {
                    "offense": 0, "defense": 0, "three_point": 0,
                    "rebounding": 0, "passing": 0, "stamina": 0
                }),
                attribute_upgrades=player_dict.get("attribute_upgrades", 0),
                # 常规赛统计
                games_played=player_dict.get("games_played", 0),
                avg_points=player_dict.get("avg_points", 0.0),
                avg_rebounds=player_dict.get("avg_rebounds", 0.0),
                avg_assists=player_dict.get("avg_assists", 0.0),
                avg_steals=player_dict.get("avg_steals", 0.0),
                avg_blocks=player_dict.get("avg_blocks", 0.0),
                avg_turnovers=player_dict.get("avg_turnovers", 0.0),
                avg_minutes=player_dict.get("avg_minutes", 0.0),
                total_points=player_dict.get("total_points", 0),
                total_rebounds=player_dict.get("total_rebounds", 0),
                total_assists=player_dict.get("total_assists", 0),
                total_steals=player_dict.get("total_steals", 0),
                total_blocks=player_dict.get("total_blocks", 0),
                total_turnovers=player_dict.get("total_turnovers", 0),
                total_minutes=player_dict.get("total_minutes", 0),
                # 季后赛统计
                playoff_games_played=player_dict.get("playoff_games_played", 0),
                playoff_avg_points=player_dict.get("playoff_avg_points", 0.0),
                playoff_avg_rebounds=player_dict.get("playoff_avg_rebounds", 0.0),
                playoff_avg_assists=player_dict.get("playoff_avg_assists", 0.0),
                playoff_avg_steals=player_dict.get("playoff_avg_steals", 0.0),
                playoff_avg_blocks=player_dict.get("playoff_avg_blocks", 0.0),
                playoff_avg_turnovers=player_dict.get("playoff_avg_turnovers", 0.0),
                playoff_avg_minutes=player_dict.get("playoff_avg_minutes", 0.0),
                playoff_total_points=player_dict.get("playoff_total_points", 0),
                playoff_total_rebounds=player_dict.get("playoff_total_rebounds", 0),
                playoff_total_assists=player_dict.get("playoff_total_assists", 0),
                playoff_total_steals=player_dict.get("playoff_total_steals", 0),
                playoff_total_blocks=player_dict.get("playoff_total_blocks", 0),
                playoff_total_turnovers=player_dict.get("playoff_total_turnovers", 0),
                playoff_total_minutes=player_dict.get("playoff_total_minutes", 0)
            )
        return result

    
    def _deserialize_standings(self, standings_data: List) -> List[Standing]:
        """反序列化排行榜数据"""
        result = []
        for standing_dict in standings_data:
            result.append(Standing(
                team_id=standing_dict.get("team_id", ""),
                wins=standing_dict.get("wins", 0),
                losses=standing_dict.get("losses", 0),
                win_pct=standing_dict.get("win_pct", 0.0),
                games_behind=standing_dict.get("games_behind", 0.0)
            ))
        return result
    
    def _deserialize_schedule(self, schedule_data: List) -> List[ScheduledGame]:
        """反序列化赛程数据"""
        result = []
        for game_dict in schedule_data:
            game = ScheduledGame(
                date=game_dict.get("date", ""),
                home_team_id=game_dict.get("home_team_id", ""),
                away_team_id=game_dict.get("away_team_id", ""),
                is_played=game_dict.get("is_played", False),
                result=None
            )
            
            result_data = game_dict.get("result")
            if result_data:
                player_stats = self._deserialize_player_stats(
                    result_data.get("player_stats", {})
                )
                game.result = MatchResult(
                    home_team_id=result_data.get("home_team_id", ""),
                    away_team_id=result_data.get("away_team_id", ""),
                    home_score=result_data.get("home_score", 0),
                    away_score=result_data.get("away_score", 0),
                    narrative=result_data.get("narrative", ""),
                    player_stats=player_stats,
                    home_player_ids=result_data.get("home_player_ids", []),  # 加载比赛时的球员列表
                    away_player_ids=result_data.get("away_player_ids", [])   # 加载比赛时的球员列表
                )
            
            result.append(game)
        return result
    
    def _deserialize_player_stats(self, stats_data: Dict) -> Dict:
        """反序列化球员比赛统计"""
        result = {}
        for player_id, stats_dict in stats_data.items():
            result[player_id] = GameStats(
                points=stats_dict.get("points", 0),
                rebounds=stats_dict.get("rebounds", 0),
                assists=stats_dict.get("assists", 0),
                steals=stats_dict.get("steals", 0),
                blocks=stats_dict.get("blocks", 0),
                turnovers=stats_dict.get("turnovers", 0),
                minutes=stats_dict.get("minutes", 0),
                team_id=stats_dict.get("team_id", "")  # 加载比赛时球员所属球队
            )
        return result
    
    def _deserialize_playoff_bracket(self, bracket_data: Dict) -> Dict:
        """反序列化季后赛对阵数据"""
        result = {}
        for key, value in bracket_data.items():
            if isinstance(value, dict) and value.get("_type") == "PlayoffSeries":
                series = PlayoffSeries(
                    team1_id=value.get("team1_id", ""),
                    team2_id=value.get("team2_id", ""),
                    team1_wins=value.get("team1_wins", 0),
                    team2_wins=value.get("team2_wins", 0),
                    round_name=value.get("round_name", "quarter"),
                    games=self._deserialize_match_results(value.get("games", []))
                )
                result[key] = series
            else:
                # 种子球队ID (字符串)
                result[key] = value
        return result
    
    def _deserialize_match_results(self, games_data: List[Dict]) -> List[MatchResult]:
        """反序列化比赛结果列表"""
        result = []
        for game_dict in games_data:
            if game_dict:
                player_stats = self._deserialize_player_stats(
                    game_dict.get("player_stats", {})
                )
                match_result = MatchResult(
                    home_team_id=game_dict.get("home_team_id", ""),
                    away_team_id=game_dict.get("away_team_id", ""),
                    home_score=game_dict.get("home_score", 0),
                    away_score=game_dict.get("away_score", 0),
                    narrative=game_dict.get("narrative", ""),
                    player_stats=player_stats,
                    quarter_scores=game_dict.get("quarter_scores", []),
                    highlights=game_dict.get("highlights", []),
                    commentary=game_dict.get("commentary", ""),
                    home_player_ids=game_dict.get("home_player_ids", []),  # 加载比赛时的球员列表
                    away_player_ids=game_dict.get("away_player_ids", [])   # 加载比赛时的球员列表
                )
                result.append(match_result)
        return result
    
    def _validate_save_data(self, data: Dict) -> None:
        """
        验证存档数据完整性
        
        Args:
            data: 存档数据字典
            
        Raises:
            CorruptedSaveError: 数据不完整或损坏时抛出
        """
        required_fields = [
            "current_date",
            "player_team_id", 
            "season_phase",
            "teams",
            "players",
            "standings",
            "schedule"
        ]
        
        for field in required_fields:
            if field not in data:
                raise CorruptedSaveError(f"存档数据缺少必要字段: {field}")
        
        # 验证日期格式
        current_date = data.get("current_date", "")
        if not self._is_valid_date(current_date):
            raise CorruptedSaveError(f"存档日期格式无效: {current_date}")
        
        # 验证赛季阶段
        season_phase = data.get("season_phase", "")
        if season_phase not in ["regular", "playoff"]:
            raise CorruptedSaveError(f"存档赛季阶段无效: {season_phase}")
        
        # 验证玩家球队存在
        player_team_id = data.get("player_team_id", "")
        teams = data.get("teams", {})
        if player_team_id and player_team_id not in teams:
            raise CorruptedSaveError(f"玩家球队不存在于球队列表中: {player_team_id}")
        
        # 验证球队数据结构
        for team_id, team_data in teams.items():
            if not isinstance(team_data, dict):
                raise CorruptedSaveError(f"球队数据格式错误: {team_id}")
            if "name" not in team_data:
                raise CorruptedSaveError(f"球队缺少名称: {team_id}")
        
        # 验证球员数据结构
        players = data.get("players", {})
        for player_id, player_data in players.items():
            if not isinstance(player_data, dict):
                raise CorruptedSaveError(f"球员数据格式错误: {player_id}")
            if "name" not in player_data:
                raise CorruptedSaveError(f"球员缺少名称: {player_id}")
    
    def _is_valid_date(self, date_str: str) -> bool:
        """
        验证日期字符串格式
        
        Args:
            date_str: 日期字符串
            
        Returns:
            是否为有效日期格式
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    
    def check_save_integrity(self, slot: int) -> Tuple[bool, str]:
        """
        检查存档完整性
        
        Args:
            slot: 存档槽位号
            
        Returns:
            (是否完整, 错误信息或成功信息)
        """
        if slot < 1 or slot > 10:
            return False, f"无效的存档槽位: {slot}"
        
        save_path = self._get_save_path(slot)
        
        if not os.path.exists(save_path):
            return False, f"存档槽位 {slot} 不存在"
        
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"存档数据损坏，JSON解析失败: {str(e)}"
        except Exception as e:
            return False, f"读取存档失败: {str(e)}"
        
        try:
            self._validate_save_data(data)
            return True, "存档完整"
        except CorruptedSaveError as e:
            return False, str(e)
    
    def try_load_game(self, slot: int) -> Tuple[Optional[GameState], str]:
        """
        尝试加载游戏，返回结果和错误信息
        
        这是一个更友好的加载方法，不会抛出异常，而是返回错误信息。
        适合在UI层使用。
        
        Args:
            slot: 存档槽位号
            
        Returns:
            (游戏状态或None, 错误信息或成功信息)
        """
        try:
            state = self.load_game(slot)
            return state, "加载成功"
        except CorruptedSaveError as e:
            return None, f"存档损坏: {str(e)}\n建议删除此存档并开始新游戏。"
        except SaveLoadError as e:
            return None, str(e)
        except Exception as e:
            return None, f"未知错误: {str(e)}"
    
    def repair_save_if_possible(self, slot: int) -> Tuple[bool, str]:
        """
        尝试修复损坏的存档
        
        目前支持的修复：
        - 补充缺失的可选字段
        - 修复无效的赛季阶段值
        
        Args:
            slot: 存档槽位号
            
        Returns:
            (是否修复成功, 结果信息)
        """
        if slot < 1 or slot > 10:
            return False, f"无效的存档槽位: {slot}"
        
        save_path = self._get_save_path(slot)
        
        if not os.path.exists(save_path):
            return False, f"存档槽位 {slot} 不存在"
        
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return False, "存档JSON格式损坏，无法修复"
        except Exception as e:
            return False, f"读取存档失败: {str(e)}"
        
        repaired = False
        repairs = []
        
        # 尝试修复缺失的可选字段
        if "playoff_bracket" not in data:
            data["playoff_bracket"] = {}
            repaired = True
            repairs.append("添加缺失的playoff_bracket字段")
        
        if "free_agents" not in data:
            data["free_agents"] = []
            repaired = True
            repairs.append("添加缺失的free_agents字段")
        
        # 修复无效的赛季阶段
        if data.get("season_phase") not in ["regular", "playoff"]:
            data["season_phase"] = "regular"
            repaired = True
            repairs.append("修复无效的赛季阶段为regular")
        
        # 确保standings是列表
        if not isinstance(data.get("standings"), list):
            data["standings"] = []
            repaired = True
            repairs.append("修复standings为空列表")
        
        # 确保schedule是列表
        if not isinstance(data.get("schedule"), list):
            data["schedule"] = []
            repaired = True
            repairs.append("修复schedule为空列表")
        
        if repaired:
            try:
                # 保存修复后的数据
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True, f"修复成功: {', '.join(repairs)}"
            except Exception as e:
                return False, f"保存修复后的数据失败: {str(e)}"
        
        # 检查是否还有其他问题
        try:
            self._validate_save_data(data)
            return True, "存档无需修复"
        except CorruptedSaveError as e:
            return False, f"存档存在无法自动修复的问题: {str(e)}"
    
    def get_save_info(self, slot: int) -> Optional[Dict[str, Any]]:
        """
        获取存档的详细信息
        
        Args:
            slot: 存档槽位号
            
        Returns:
            存档信息字典，不存在或损坏则返回None
        """
        if slot < 1 or slot > 10:
            return None
        
        save_path = self._get_save_path(slot)
        
        if not os.path.exists(save_path):
            return None
        
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            meta = data.get("_meta", {})
            teams = data.get("teams", {})
            players = data.get("players", {})
            standings = data.get("standings", [])
            
            player_team_id = data.get("player_team_id", "")
            team_name = "未知球队"
            if player_team_id and player_team_id in teams:
                team_name = teams[player_team_id].get("name", "未知球队")
            
            # 计算进度
            schedule = data.get("schedule", [])
            games_played = sum(1 for g in schedule if g.get("is_played", False))
            total_games = len(schedule)
            
            return {
                "slot": slot,
                "save_time": meta.get("save_time", "未知"),
                "version": meta.get("version", "未知"),
                "current_date": data.get("current_date", "未知"),
                "player_team_id": player_team_id,
                "player_team_name": team_name,
                "season_phase": data.get("season_phase", "regular"),
                "num_teams": len(teams),
                "num_players": len(players),
                "games_played": games_played,
                "total_games": total_games,
                "progress_pct": (games_played / total_games * 100) if total_games > 0 else 0
            }
        except Exception:
            return None
