"""
华夏篮球联赛教练模拟器 - 个人数据榜单系统

负责计算和返回各项数据的排行榜
"""
from typing import Dict, List, Optional
from src.models import Player, Team


# 支持的统计类型及其对应的球员属性（常规赛）
STAT_TYPE_MAPPING = {
    "points": "avg_points",
    "rebounds": "avg_rebounds",
    "assists": "avg_assists",
    "steals": "avg_steals",
    "blocks": "avg_blocks",
}

# 季后赛统计类型映射
PLAYOFF_STAT_TYPE_MAPPING = {
    "points": "playoff_avg_points",
    "rebounds": "playoff_avg_rebounds",
    "assists": "playoff_avg_assists",
    "steals": "playoff_avg_steals",
    "blocks": "playoff_avg_blocks",
}

# 总数据统计类型映射（常规赛+季后赛累计）
TOTAL_STAT_TYPE_MAPPING = {
    "points": ("total_points", "playoff_total_points"),
    "rebounds": ("total_rebounds", "playoff_total_rebounds"),
    "assists": ("total_assists", "playoff_total_assists"),
    "steals": ("total_steals", "playoff_total_steals"),
    "blocks": ("total_blocks", "playoff_total_blocks"),
}

# 统计类型的中文名称
STAT_TYPE_NAMES = {
    "points": "得分",
    "rebounds": "篮板",
    "assists": "助攻",
    "steals": "抢断",
    "blocks": "盖帽",
}


class StatsLeaderboard:
    """个人数据榜单服务"""
    
    def __init__(self, players: Dict[str, Player], teams: Dict[str, Team], season_manager=None):
        """
        初始化榜单服务
        
        Args:
            players: 球员字典 {player_id: Player}
            teams: 球队字典 {team_id: Team}
            season_manager: 赛季管理器（用于获取球队战绩）
        """
        self.players = players
        self.teams = teams
        self.season_manager = season_manager
        # 缓存常规赛结束时的球队战绩排行榜
        self._cached_team_standings: Optional[List[Dict]] = None
    
    def get_leaderboard(
        self,
        stat_type: str,
        min_games: int = 5,
        top_n: int = 20,
        is_playoff: bool = False,
        domestic_only: bool = False
    ) -> List[Dict]:
        """
        获取指定数据类型的排行榜
        
        Args:
            stat_type: 统计类型 ("points", "rebounds", "assists", "steals", "blocks")
            min_games: 最小场次要求，默认5场（季后赛模式下忽略此参数）
            top_n: 返回前N名，默认20
            is_playoff: 是否为季后赛排行榜，默认False
            domestic_only: 是否只显示本土球员（排除外援），默认False
            
        Returns:
            排行榜列表，每个条目包含:
            - rank: 排名
            - player_id: 球员ID
            - player_name: 球员姓名
            - team_id: 球队ID
            - team_name: 球队名称
            - games_played: 出场次数
            - stat_value: 统计数值
            - stat_type: 统计类型
        """
        if stat_type not in STAT_TYPE_MAPPING:
            raise ValueError(f"不支持的统计类型: {stat_type}。支持的类型: {list(STAT_TYPE_MAPPING.keys())}")
        
        # 根据是否季后赛选择对应的属性映射
        if is_playoff:
            stat_attr = PLAYOFF_STAT_TYPE_MAPPING[stat_type]
            games_attr = "playoff_games_played"
            # 季后赛不使用最小场次限制，只要有出场即可
            effective_min_games = 1
        else:
            stat_attr = STAT_TYPE_MAPPING[stat_type]
            games_attr = "games_played"
            effective_min_games = min_games
        
        # 筛选满足条件的球员
        eligible_players = []
        for player in self.players.values():
            # 检查场次要求
            if getattr(player, games_attr) < effective_min_games:
                continue
            # 检查是否只显示本土球员
            if domestic_only and player.is_foreign:
                continue
            eligible_players.append(player)
        
        # 按统计数值降序排序
        sorted_players = sorted(
            eligible_players,
            key=lambda p: getattr(p, stat_attr),
            reverse=True
        )
        
        # 取前N名
        top_players = sorted_players[:top_n]
        
        # 构建排行榜结果
        leaderboard = []
        for rank, player in enumerate(top_players, start=1):
            team = self.teams.get(player.team_id)
            team_name = team.name if team else "未知球队"
            
            leaderboard.append({
                "rank": rank,
                "player_id": player.id,
                "player_name": player.name,
                "team_id": player.team_id,
                "team_name": team_name,
                "games_played": getattr(player, games_attr),
                "stat_value": round(getattr(player, stat_attr), 1),
                "stat_type": stat_type,
                "is_foreign": player.is_foreign,
            })
        
        return leaderboard
    
    def get_all_leaderboards(
        self,
        min_games: int = 5,
        top_n: int = 20,
        is_playoff: bool = False,
        domestic_only: bool = False
    ) -> Dict[str, List[Dict]]:
        """
        获取所有类型的排行榜
        
        Args:
            min_games: 最小场次要求，默认5场（季后赛模式下忽略）
            top_n: 返回前N名，默认20
            is_playoff: 是否为季后赛排行榜，默认False
            domestic_only: 是否只显示本土球员，默认False
            
        Returns:
            包含所有5种数据类型的字典:
            {
                "points": [...],
                "rebounds": [...],
                "assists": [...],
                "steals": [...],
                "blocks": [...]
            }
        """
        all_leaderboards = {}
        
        for stat_type in STAT_TYPE_MAPPING.keys():
            all_leaderboards[stat_type] = self.get_leaderboard(
                stat_type=stat_type,
                min_games=min_games,
                top_n=top_n,
                is_playoff=is_playoff,
                domestic_only=domestic_only
            )
        
        return all_leaderboards
    
    def get_total_leaderboard(
        self,
        stat_type: str,
        min_games: int = 5,
        top_n: int = 20,
        domestic_only: bool = False
    ) -> List[Dict]:
        """
        获取总数据排行榜（常规赛+季后赛）
        
        Args:
            stat_type: 统计类型 ("points", "rebounds", "assists", "steals", "blocks")
            min_games: 最小场次要求，默认5场（常规赛+季后赛总场次）
            top_n: 返回前N名，默认20
            domestic_only: 是否只显示本土球员，默认False
            
        Returns:
            排行榜列表，每个条目包含:
            - rank: 排名
            - player_id: 球员ID
            - player_name: 球员姓名
            - team_id: 球队ID
            - team_name: 球队名称
            - games_played: 总出场次数（常规赛+季后赛）
            - regular_games: 常规赛场次
            - playoff_games: 季后赛场次
            - stat_value: 场均统计数值
            - stat_type: 统计类型
        """
        if stat_type not in TOTAL_STAT_TYPE_MAPPING:
            raise ValueError(f"不支持的统计类型: {stat_type}。支持的类型: {list(TOTAL_STAT_TYPE_MAPPING.keys())}")
        
        regular_attr, playoff_attr = TOTAL_STAT_TYPE_MAPPING[stat_type]
        
        # 计算每个球员的总数据
        player_totals = []
        for player in self.players.values():
            # 检查是否只显示本土球员
            if domestic_only and player.is_foreign:
                continue
                
            total_games = player.games_played + player.playoff_games_played
            if total_games < min_games:
                continue
            
            # 计算总累计数据
            regular_total = getattr(player, regular_attr)
            playoff_total = getattr(player, playoff_attr)
            combined_total = regular_total + playoff_total
            
            # 计算场均
            avg_value = combined_total / total_games if total_games > 0 else 0
            
            player_totals.append({
                "player": player,
                "total_games": total_games,
                "regular_games": player.games_played,
                "playoff_games": player.playoff_games_played,
                "avg_value": avg_value
            })
        
        # 按场均数值降序排序
        sorted_players = sorted(player_totals, key=lambda x: x["avg_value"], reverse=True)
        
        # 取前N名
        top_players = sorted_players[:top_n]
        
        # 构建排行榜结果
        leaderboard = []
        for rank, item in enumerate(top_players, start=1):
            player = item["player"]
            team = self.teams.get(player.team_id)
            team_name = team.name if team else "未知球队"
            
            leaderboard.append({
                "rank": rank,
                "player_id": player.id,
                "player_name": player.name,
                "team_id": player.team_id,
                "team_name": team_name,
                "games_played": item["total_games"],
                "regular_games": item["regular_games"],
                "playoff_games": item["playoff_games"],
                "stat_value": round(item["avg_value"], 1),
                "stat_type": stat_type,
                "is_foreign": player.is_foreign,
            })
        
        return leaderboard
    
    def get_all_total_leaderboards(
        self,
        min_games: int = 5,
        top_n: int = 20,
        domestic_only: bool = False
    ) -> Dict[str, List[Dict]]:
        """
        获取所有类型的总数据排行榜（常规赛+季后赛）
        
        Args:
            min_games: 最小场次要求，默认5场
            top_n: 返回前N名，默认20
            domestic_only: 是否只显示本土球员，默认False
            
        Returns:
            包含所有5种数据类型的字典
        """
        all_leaderboards = {}
        
        for stat_type in TOTAL_STAT_TYPE_MAPPING.keys():
            all_leaderboards[stat_type] = self.get_total_leaderboard(
                stat_type=stat_type,
                min_games=min_games,
                top_n=top_n,
                domestic_only=domestic_only
            )
        
        return all_leaderboards
    
    def get_stat_type_name(self, stat_type: str) -> str:
        """
        获取统计类型的中文名称
        
        Args:
            stat_type: 统计类型
            
        Returns:
            中文名称
        """
        return STAT_TYPE_NAMES.get(stat_type, stat_type)
    
    @staticmethod
    def get_supported_stat_types() -> List[str]:
        """
        获取支持的统计类型列表
        
        Returns:
            统计类型列表
        """
        return list(STAT_TYPE_MAPPING.keys())
    
    def get_team_standings_leaderboard(self) -> List[Dict]:
        """
        获取球队战绩排行榜
        
        如果已缓存（常规赛结束后），返回缓存的排行榜
        否则从season_manager获取当前排行榜
        
        Returns:
            球队战绩排行榜列表，每个条目包含:
            - rank: 排名
            - team_id: 球队ID
            - team_name: 球队名称
            - wins: 胜场
            - losses: 负场
            - win_pct: 胜率
            - games_behind: 落后场次
        """
        # 如果有缓存，返回缓存的排行榜
        if self._cached_team_standings is not None:
            return self._cached_team_standings
        
        # 否则从season_manager获取当前排行榜
        if self.season_manager is None:
            return []
        
        standings = self.season_manager.get_standings()
        
        leaderboard = []
        for rank, standing in enumerate(standings, start=1):
            team = self.teams.get(standing.team_id)
            team_name = team.name if team else "未知球队"
            
            leaderboard.append({
                "rank": rank,
                "team_id": standing.team_id,
                "team_name": team_name,
                "wins": standing.wins,
                "losses": standing.losses,
                "win_pct": round(standing.win_pct, 3),
                "games_behind": standing.games_behind
            })
        
        return leaderboard
    
    def cache_team_standings(self) -> None:
        """
        缓存当前球队战绩排行榜
        
        在常规赛结束进入季后赛时调用，确保季后赛期间排行榜保持不变
        """
        self._cached_team_standings = self.get_team_standings_leaderboard()
    
    def clear_team_standings_cache(self) -> None:
        """
        清除球队战绩排行榜缓存
        
        在新赛季开始时调用
        """
        self._cached_team_standings = None
    
    def is_team_standings_cached(self) -> bool:
        """
        检查球队战绩排行榜是否已缓存
        
        Returns:
            是否已缓存
        """
        return self._cached_team_standings is not None
