"""
华夏篮球联赛教练模拟器 - 球员数据管理器

负责球员和球队数据的加载、保存和管理
"""
import json
import os
from typing import Dict, List, Tuple, Optional
from src.models import Player, Team


# 数据文件路径
PLAYERS_FILE = "player_data/players.json"
TEAMS_FILE = "player_data/teams.json"


# 总评计算权重（按位置）
OVERALL_WEIGHTS = {
    "PG": {"offense": 0.25, "defense": 0.15, "three_point": 0.20,
           "rebounding": 0.05, "passing": 0.25, "stamina": 0.10},
    "SG": {"offense": 0.30, "defense": 0.15, "three_point": 0.25,
           "rebounding": 0.05, "passing": 0.15, "stamina": 0.10},
    "SF": {"offense": 0.25, "defense": 0.20, "three_point": 0.20,
           "rebounding": 0.15, "passing": 0.10, "stamina": 0.10},
    "PF": {"offense": 0.20, "defense": 0.25, "three_point": 0.10,
           "rebounding": 0.25, "passing": 0.10, "stamina": 0.10},
    "C":  {"offense": 0.15, "defense": 0.30, "three_point": 0.05,
           "rebounding": 0.30, "passing": 0.10, "stamina": 0.10},
}


def calculate_overall(player: Player) -> int:
    """
    根据位置加权计算球员总评
    
    Args:
        player: 球员对象
        
    Returns:
        计算后的总评值 (0-99)
    """
    position = player.position
    if position not in OVERALL_WEIGHTS:
        # 默认使用SF权重
        position = "SF"
    
    weights = OVERALL_WEIGHTS[position]
    
    overall = (
        player.offense * weights["offense"] +
        player.defense * weights["defense"] +
        player.three_point * weights["three_point"] +
        player.rebounding * weights["rebounding"] +
        player.passing * weights["passing"] +
        player.stamina * weights["stamina"]
    )
    
    # 确保结果在0-99范围内
    return max(0, min(99, int(overall)))


class PlayerDataManager:
    """球员数据管理器"""
    
    def __init__(self, players_file: str = PLAYERS_FILE, teams_file: str = TEAMS_FILE):
        """
        初始化数据管理器
        
        Args:
            players_file: 球员数据文件路径
            teams_file: 球队数据文件路径
        """
        self.players_file = players_file
        self.teams_file = teams_file
        self.players: Dict[str, Player] = {}
        self.teams: Dict[str, Team] = {}
    
    def load_all_data(self) -> Tuple[Dict[str, Team], Dict[str, Player]]:
        """
        加载所有球员和球队数据
        
        Returns:
            (teams字典, players字典) 元组
        """
        self._load_teams()
        self._load_players()
        self._rebuild_team_rosters()
        return self.teams, self.players
    
    def _rebuild_team_rosters(self) -> None:
        """根据球员的team_id重新构建球队roster列表"""
        # 清空所有球队的roster
        for team in self.teams.values():
            team.roster = []
        
        # 根据球员的team_id重新分配到对应球队
        for player_id, player in self.players.items():
            if player.team_id and player.team_id in self.teams:
                if player_id not in self.teams[player.team_id].roster:
                    self.teams[player.team_id].roster.append(player_id)
    
    def _load_teams(self) -> None:
        """从文件加载球队数据"""
        if not os.path.exists(self.teams_file):
            self.teams = {}
            return
        
        with open(self.teams_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        teams_data = data.get("teams", {})
        self.teams = {}
        
        for team_id, team_dict in teams_data.items():
            self.teams[team_id] = Team(
                id=team_dict.get("id", team_id),
                name=team_dict.get("name", ""),
                city=team_dict.get("city", ""),
                status=team_dict.get("status", "stable"),
                is_player_controlled=team_dict.get("is_player_controlled", False),
                roster=team_dict.get("roster", [])
            )
    
    def _load_players(self) -> None:
        """从文件加载球员数据"""
        if not os.path.exists(self.players_file):
            self.players = {}
            return
        
        with open(self.players_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        players_data = data.get("players", {})
        self.players = {}
        
        for player_id, player_dict in players_data.items():
            player = Player(
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
                # 训练进度系统字段
                training_points=player_dict.get("training_points", {
                    "offense": 0, "defense": 0, "three_point": 0,
                    "rebounding": 0, "passing": 0, "stamina": 0
                }),
                attribute_upgrades=player_dict.get("attribute_upgrades", 0),
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
                total_minutes=player_dict.get("total_minutes", 0)
            )
            self.players[player_id] = player
    
    def save_all_data(self, teams: Optional[Dict[str, Team]] = None, 
                      players: Optional[Dict[str, Player]] = None) -> None:
        """
        保存所有球员和球队数据
        
        Args:
            teams: 球队字典，如果为None则使用内部数据
            players: 球员字典，如果为None则使用内部数据
        """
        if teams is not None:
            self.teams = teams
        if players is not None:
            self.players = players
        
        self._save_teams()
        self._save_players()
    
    def _save_teams(self) -> None:
        """保存球队数据到文件"""
        teams_data = {}
        for team_id, team in self.teams.items():
            teams_data[team_id] = {
                "id": team.id,
                "name": team.name,
                "city": team.city,
                "status": team.status,
                "is_player_controlled": team.is_player_controlled,
                "roster": team.roster
            }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.teams_file), exist_ok=True)
        
        with open(self.teams_file, 'w', encoding='utf-8') as f:
            json.dump({"teams": teams_data}, f, ensure_ascii=False, indent=2)
    
    def _save_players(self) -> None:
        """保存球员数据到文件"""
        players_data = {}
        for player_id, player in self.players.items():
            players_data[player_id] = {
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
                # 训练进度系统字段
                "training_points": player.training_points if hasattr(player, 'training_points') and player.training_points else {
                    "offense": 0, "defense": 0, "three_point": 0,
                    "rebounding": 0, "passing": 0, "stamina": 0
                },
                "attribute_upgrades": player.attribute_upgrades if hasattr(player, 'attribute_upgrades') else 0,
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
                "total_minutes": player.total_minutes
            }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.players_file), exist_ok=True)
        
        with open(self.players_file, 'w', encoding='utf-8') as f:
            json.dump({"players": players_data}, f, ensure_ascii=False, indent=2)
    
    def get_team_roster(self, team_id: str) -> List[Player]:
        """
        获取指定球队的球员列表
        
        Args:
            team_id: 球队ID
            
        Returns:
            球员对象列表
        """
        if team_id not in self.teams:
            return []
        
        team = self.teams[team_id]
        roster = []
        
        for player_id in team.roster:
            if player_id in self.players:
                roster.append(self.players[player_id])
        
        return roster
    
    def update_player_overall(self, player_id: str) -> int:
        """
        更新球员总评
        
        Args:
            player_id: 球员ID
            
        Returns:
            更新后的总评值
        """
        if player_id not in self.players:
            return 0
        
        player = self.players[player_id]
        player.overall = calculate_overall(player)
        return player.overall
    
    def update_player_stats(self, player_id: str, game_stats: dict) -> bool:
        """
        更新球员比赛统计数据
        
        根据单场比赛数据更新球员的累计统计和场均数据。
        此方法用于完整模拟和快速模拟两种模式，确保统计更新逻辑一致。
        
        Args:
            player_id: 球员ID
            game_stats: 单场比赛数据字典，包含以下字段:
                - points: 得分
                - rebounds: 篮板
                - assists: 助攻
                - steals: 抢断
                - blocks: 盖帽
                - turnovers: 失误
                - minutes: 上场时间
        
        Returns:
            bool: 更新是否成功（球员存在返回True，否则返回False）
        
        Requirements:
            - 11.1: 更新 games_played 计数
            - 11.2: 更新累计数据 (total_points, total_rebounds, etc.)
            - 11.3: 重新计算场均数据 (avg = total / games_played)
            - 11.4: 快速模拟和完整模拟使用相同的更新逻辑
        """
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        
        # Requirement 11.1: 更新 games_played 计数
        player.games_played += 1
        
        # Requirement 11.2: 更新累计数据
        player.total_points += game_stats.get("points", 0)
        player.total_rebounds += game_stats.get("rebounds", 0)
        player.total_assists += game_stats.get("assists", 0)
        player.total_steals += game_stats.get("steals", 0)
        player.total_blocks += game_stats.get("blocks", 0)
        player.total_turnovers += game_stats.get("turnovers", 0)
        player.total_minutes += game_stats.get("minutes", 0)
        
        # Requirement 11.3: 重新计算场均数据 (avg = total / games_played)
        # games_played 已经在上面增加了，所以这里一定 > 0
        player.avg_points = player.total_points / player.games_played
        player.avg_rebounds = player.total_rebounds / player.games_played
        player.avg_assists = player.total_assists / player.games_played
        player.avg_steals = player.total_steals / player.games_played
        player.avg_blocks = player.total_blocks / player.games_played
        player.avg_turnovers = player.total_turnovers / player.games_played
        player.avg_minutes = player.total_minutes / player.games_played
        
        return True
    
    def update_player_playoff_stats(self, player_id: str, game_stats: dict) -> bool:
        """
        更新球员季后赛统计数据
        
        根据单场季后赛比赛数据更新球员的季后赛累计统计和场均数据。
        
        Args:
            player_id: 球员ID
            game_stats: 单场比赛数据字典，包含以下字段:
                - points: 得分
                - rebounds: 篮板
                - assists: 助攻
                - steals: 抢断
                - blocks: 盖帽
                - turnovers: 失误
                - minutes: 上场时间
        
        Returns:
            bool: 更新是否成功（球员存在返回True，否则返回False）
        """
        if player_id not in self.players:
            return False
        
        player = self.players[player_id]
        
        # 更新季后赛出场次数
        player.playoff_games_played += 1
        
        # 更新季后赛累计数据
        player.playoff_total_points += game_stats.get("points", 0)
        player.playoff_total_rebounds += game_stats.get("rebounds", 0)
        player.playoff_total_assists += game_stats.get("assists", 0)
        player.playoff_total_steals += game_stats.get("steals", 0)
        player.playoff_total_blocks += game_stats.get("blocks", 0)
        player.playoff_total_turnovers += game_stats.get("turnovers", 0)
        player.playoff_total_minutes += game_stats.get("minutes", 0)
        
        # 重新计算季后赛场均数据
        player.playoff_avg_points = player.playoff_total_points / player.playoff_games_played
        player.playoff_avg_rebounds = player.playoff_total_rebounds / player.playoff_games_played
        player.playoff_avg_assists = player.playoff_total_assists / player.playoff_games_played
        player.playoff_avg_steals = player.playoff_total_steals / player.playoff_games_played
        player.playoff_avg_blocks = player.playoff_total_blocks / player.playoff_games_played
        player.playoff_avg_turnovers = player.playoff_total_turnovers / player.playoff_games_played
        player.playoff_avg_minutes = player.playoff_total_minutes / player.playoff_games_played
        
        return True
    
    def transfer_player(self, player_id: str, from_team_id: str, to_team_id: str) -> bool:
        """
        转移球员到另一支球队
        
        Args:
            player_id: 球员ID
            from_team_id: 原球队ID
            to_team_id: 目标球队ID
            
        Returns:
            是否转移成功
        """
        if player_id not in self.players:
            return False
        if from_team_id not in self.teams or to_team_id not in self.teams:
            return False
        
        player = self.players[player_id]
        from_team = self.teams[from_team_id]
        to_team = self.teams[to_team_id]
        
        # 从原球队移除
        if player_id in from_team.roster:
            from_team.roster.remove(player_id)
        
        # 添加到新球队
        if player_id not in to_team.roster:
            to_team.roster.append(player_id)
        
        # 更新球员所属球队
        player.team_id = to_team_id
        
        return True
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """
        获取指定球员
        
        Args:
            player_id: 球员ID
            
        Returns:
            球员对象，不存在则返回None
        """
        return self.players.get(player_id)
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """
        获取指定球队
        
        Args:
            team_id: 球队ID
            
        Returns:
            球队对象，不存在则返回None
        """
        return self.teams.get(team_id)
    
    def get_all_teams(self) -> List[Team]:
        """获取所有球队列表"""
        return list(self.teams.values())
    
    def get_all_players(self) -> List[Player]:
        """获取所有球员列表"""
        return list(self.players.values())
    
    def get_player_full_profile(self, player_id: str, mode: str = 'regular') -> Optional[Dict]:
        """
        获取球员完整档案，包括基本属性和赛季场均数据
        
        Args:
            player_id: 球员ID
            mode: 数据模式 (regular/playoff/total)
            
        Returns:
            包含球员完整信息的字典，不存在则返回None
            
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        player = self.players.get(player_id)
        if player is None:
            return None
        
        # 获取球队名称
        team_name = ""
        if player.team_id and player.team_id in self.teams:
            team_name = self.teams[player.team_id].name
        
        # 根据模式获取统计数据
        if mode == 'playoff':
            games_played = player.playoff_games_played
            has_stats = games_played > 0
            if has_stats:
                season_stats = {
                    "games_played": games_played,
                    "avg_points": round(player.playoff_avg_points, 1),
                    "avg_rebounds": round(player.playoff_avg_rebounds, 1),
                    "avg_assists": round(player.playoff_avg_assists, 1),
                    "avg_steals": round(player.playoff_avg_steals, 1),
                    "avg_blocks": round(player.playoff_avg_blocks, 1),
                    "avg_turnovers": round(player.playoff_avg_turnovers, 1),
                    "avg_minutes": round(player.playoff_avg_minutes, 1)
                }
            else:
                season_stats = {
                    "games_played": 0,
                    "avg_points": "暂无数据",
                    "avg_rebounds": "暂无数据",
                    "avg_assists": "暂无数据",
                    "avg_steals": "暂无数据",
                    "avg_blocks": "暂无数据",
                    "avg_turnovers": "暂无数据",
                    "avg_minutes": "暂无数据"
                }
        elif mode == 'total':
            total_games = player.games_played + player.playoff_games_played
            has_stats = total_games > 0
            if has_stats:
                total_points = player.total_points + player.playoff_total_points
                total_rebounds = player.total_rebounds + player.playoff_total_rebounds
                total_assists = player.total_assists + player.playoff_total_assists
                total_steals = player.total_steals + player.playoff_total_steals
                total_blocks = player.total_blocks + player.playoff_total_blocks
                total_turnovers = player.total_turnovers + player.playoff_total_turnovers
                total_minutes = player.total_minutes + player.playoff_total_minutes
                season_stats = {
                    "games_played": total_games,
                    "avg_points": round(total_points / total_games, 1),
                    "avg_rebounds": round(total_rebounds / total_games, 1),
                    "avg_assists": round(total_assists / total_games, 1),
                    "avg_steals": round(total_steals / total_games, 1),
                    "avg_blocks": round(total_blocks / total_games, 1),
                    "avg_turnovers": round(total_turnovers / total_games, 1),
                    "avg_minutes": round(total_minutes / total_games, 1)
                }
            else:
                season_stats = {
                    "games_played": 0,
                    "avg_points": "暂无数据",
                    "avg_rebounds": "暂无数据",
                    "avg_assists": "暂无数据",
                    "avg_steals": "暂无数据",
                    "avg_blocks": "暂无数据",
                    "avg_turnovers": "暂无数据",
                    "avg_minutes": "暂无数据"
                }
            games_played = total_games
        else:
            # 常规赛数据（默认）
            games_played = player.games_played
            has_stats = games_played > 0
            if has_stats:
                season_stats = {
                    "games_played": games_played,
                    "avg_points": round(player.avg_points, 1),
                    "avg_rebounds": round(player.avg_rebounds, 1),
                    "avg_assists": round(player.avg_assists, 1),
                    "avg_steals": round(player.avg_steals, 1),
                    "avg_blocks": round(player.avg_blocks, 1),
                    "avg_turnovers": round(player.avg_turnovers, 1),
                    "avg_minutes": round(player.avg_minutes, 1)
                }
            else:
                season_stats = {
                    "games_played": 0,
                    "avg_points": "暂无数据",
                    "avg_rebounds": "暂无数据",
                    "avg_assists": "暂无数据",
                    "avg_steals": "暂无数据",
                    "avg_blocks": "暂无数据",
                    "avg_turnovers": "暂无数据",
                    "avg_minutes": "暂无数据"
                }
        
        # 基本信息
        profile = {
            "id": player.id,
            "name": player.name,
            "team_id": player.team_id,
            "team_name": team_name,
            "position": player.position,
            "age": player.age,
            "is_foreign": player.is_foreign,
            "overall": player.overall,
            "skill_tags": player.skill_tags,
            "is_injured": player.is_injured,
            "injury_days": player.injury_days,
            
            # 基本属性 (Requirements 2.1)
            "attributes": {
                "offense": player.offense,
                "defense": player.defense,
                "three_point": player.three_point,
                "rebounding": player.rebounding,
                "passing": player.passing,
                "stamina": player.stamina
            },
            
            # 训练进度
            "training_progress": {
                "training_points": player.training_points if hasattr(player, 'training_points') and player.training_points else {
                    "offense": 0, "defense": 0, "three_point": 0,
                    "rebounding": 0, "passing": 0, "stamina": 0
                },
                "attribute_upgrades": player.attribute_upgrades if hasattr(player, 'attribute_upgrades') else 0,
                "points_per_upgrade": 20,  # 单项训练点数达到20后该属性+1
                "upgrades_per_overall": 5  # 累积5次单项+1后总评+1
            },
            
            # 基本信息（用于模态框显示）
            "basic_info": {
                "name": player.name,
                "position": player.position
            },
            
            # 比赛场次 (Requirements 2.3)
            "games_played": games_played,
            
            # 赛季场均数据 (Requirements 2.2, 2.4)
            "season_stats": season_stats,
            "has_stats": has_stats,
            "mode": mode
        }
        
        return profile
