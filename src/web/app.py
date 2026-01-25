"""
华夏篮球联赛教练模拟器 - Flask Web后端

提供RESTful API接口供前端调用
Requirements: 6.11, 6.12
"""
import os
from typing import Dict, Optional
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from src.models import Team, Player, GameState, TradeProposal
from src.player_data_manager import PlayerDataManager
from src.season_manager import SeasonManager
from src.match_engine import MatchEngine
from src.training_system import TrainingSystem, TRAINING_PROGRAMS, TrainingLimitError
from src.trade_system import TradeSystem
from src.foreign_market import ForeignMarket, SCOUT_COST, TARGETED_SCOUT_COST, MAX_SALARY, POSITIONS
from src.storage_manager import StorageManager
from src.game_controller import GameController
from src.stats_leaderboard import StatsLeaderboard
from src.daily_stats_viewer import DailyStatsViewer
from src.injury_system import InjurySystem
from src.llm_interface import LLMInterface


# Flask应用初始化
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

# 配置CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 全局游戏状态管理
class GameStateManager:
    """全局游戏状态管理器"""
    
    def __init__(self):
        self.data_manager: Optional[PlayerDataManager] = None
        self.season_manager: Optional[SeasonManager] = None
        self.match_engine: Optional[MatchEngine] = None
        self.training_system: Optional[TrainingSystem] = None
        self.trade_system: Optional[TradeSystem] = None
        self.foreign_market: Optional[ForeignMarket] = None  # 外援市场系统
        self.storage_manager: Optional[StorageManager] = None
        self.game_controller: Optional[GameController] = None
        self.stats_leaderboard: Optional[StatsLeaderboard] = None
        self.daily_stats_viewer: Optional[DailyStatsViewer] = None
        
        self.teams: Dict[str, Team] = {}
        self.players: Dict[str, Player] = {}
        self.player_team_id: Optional[str] = None
        self.is_game_started: bool = False
    
    def initialize_managers(self):
        """初始化所有管理器"""
        self.data_manager = PlayerDataManager()
        self.storage_manager = StorageManager()
    
    def start_new_game(self, player_team_id: str) -> bool:
        """
        开始新游戏
        
        Args:
            player_team_id: 玩家选择的球队ID
            
        Returns:
            是否成功
            
        Requirements: 4.1, 4.2
        - 4.1: 游戏开始日期设置为首场比赛前一天
        - 4.2: 所有球员初始 games_played = 0
        """
        try:
            from datetime import datetime, timedelta
            
            # 加载数据
            self.teams, self.players = self.data_manager.load_all_data()
            
            if player_team_id not in self.teams:
                return False
            
            self.player_team_id = player_team_id
            
            # 设置玩家控制的球队
            for team_id, team in self.teams.items():
                team.is_player_controlled = (team_id == player_team_id)
            
            # 重置所有球员的赛季统计数据 (Requirements 4.2)
            # 确保新游戏开始时所有球员 games_played = 0
            for player in self.players.values():
                player.games_played = 0
                player.avg_points = 0.0
                player.avg_rebounds = 0.0
                player.avg_assists = 0.0
                player.avg_steals = 0.0
                player.avg_blocks = 0.0
                player.avg_turnovers = 0.0
                player.avg_minutes = 0.0
                player.total_points = 0
                player.total_rebounds = 0
                player.total_assists = 0
                player.total_steals = 0
                player.total_blocks = 0
                player.total_turnovers = 0
                player.total_minutes = 0
            
            # 初始化赛季管理器
            self.season_manager = SeasonManager(list(self.teams.values()))
            self.season_manager.generate_alternating_schedule()
            
            # 设置游戏开始日期为首场比赛前一天 (Requirements 4.1)
            if self.season_manager.schedule:
                # 获取首场比赛日期
                first_game_date_str = self.season_manager.schedule[0].date
                first_game_date = datetime.strptime(first_game_date_str, "%Y-%m-%d")
                # 设置开始日期为首场比赛前一天
                start_date = (first_game_date - timedelta(days=1)).strftime("%Y-%m-%d")
                self.season_manager.current_date = start_date
            
            # 初始化比赛引擎
            llm_interface = LLMInterface()
            self.match_engine = MatchEngine(llm_interface, self.data_manager)
            
            # 初始化训练系统
            self.training_system = TrainingSystem(self.data_manager)
            
            # 初始化交易系统（传入llm_interface用于智能交易评估）
            self.trade_system = TradeSystem(self.data_manager, llm_interface)
            
            # 初始化外援市场系统
            self.foreign_market = ForeignMarket(self.data_manager, llm_interface)
            
            # 初始化游戏控制器
            injury_system = InjurySystem()
            self.game_controller = GameController(
                season_manager=self.season_manager,
                match_engine=self.match_engine,
                training_system=self.training_system,
                injury_system=injury_system,
                teams=self.teams,
                players=self.players,
                player_team_id=player_team_id
            )
            
            # 初始化榜单和数据查看器
            self.stats_leaderboard = StatsLeaderboard(self.players, self.teams, self.season_manager)
            self.daily_stats_viewer = DailyStatsViewer(
                self.season_manager, self.teams, self.players
            )
            
            self.is_game_started = True
            return True
            
        except Exception as e:
            print(f"Error starting new game: {e}")
            return False

    def load_game(self, slot: int) -> tuple:
        """
        加载存档
        
        Args:
            slot: 存档槽位
            
        Returns:
            (是否成功, 消息)
        """
        try:
            state = self.storage_manager.load_game(slot)
            
            # 恢复游戏状态
            self.teams = state.teams
            self.players = state.players
            self.player_team_id = state.player_team_id
            
            # 更新数据管理器
            self.data_manager.teams = self.teams
            self.data_manager.players = self.players
            
            # 重新初始化赛季管理器
            self.season_manager = SeasonManager(list(self.teams.values()))
            self.season_manager.standings = {s.team_id: s for s in state.standings}
            self.season_manager.schedule = state.schedule
            self.season_manager.playoff_bracket = state.playoff_bracket
            self.season_manager.current_date = state.current_date
            
            # 初始化比赛引擎
            llm_interface = LLMInterface()
            self.match_engine = MatchEngine(llm_interface, self.data_manager)
            
            # 初始化训练系统
            self.training_system = TrainingSystem(self.data_manager)
            # 恢复训练状态
            if hasattr(state, 'training_state') and state.training_state:
                self.training_system.restore_training_state(state.training_state)
            
            # 初始化交易系统（传入llm_interface用于智能交易评估）
            self.trade_system = TradeSystem(self.data_manager, llm_interface)
            self.trade_system.set_free_agents(state.free_agents)
            
            # 初始化外援市场系统
            self.foreign_market = ForeignMarket(self.data_manager, llm_interface)
            # 恢复已用名字状态
            if state.foreign_used_names:
                self.foreign_market.restore_used_names_state(state.foreign_used_names)
            
            # 初始化游戏控制器
            injury_system = InjurySystem()
            self.game_controller = GameController(
                season_manager=self.season_manager,
                match_engine=self.match_engine,
                training_system=self.training_system,
                injury_system=injury_system,
                teams=self.teams,
                players=self.players,
                player_team_id=self.player_team_id
            )
            self.game_controller._current_date = state.current_date
            
            # 恢复季后赛状态 (Requirements 6.2)
            self.game_controller.is_playoff_phase = state.is_playoff_phase
            self.game_controller.player_eliminated = state.player_eliminated
            
            # 初始化榜单和数据查看器
            self.stats_leaderboard = StatsLeaderboard(self.players, self.teams, self.season_manager)
            self.daily_stats_viewer = DailyStatsViewer(
                self.season_manager, self.teams, self.players
            )
            
            # 如果是季后赛阶段，缓存球队战绩排行榜
            if state.is_playoff_phase:
                self.stats_leaderboard.cache_team_standings()
            
            self.is_game_started = True
            return True, "加载成功"
            
        except Exception as e:
            return False, str(e)
    
    def save_game(self, slot: int) -> tuple:
        """
        保存游戏
        
        Args:
            slot: 存档槽位
            
        Returns:
            (是否成功, 消息)
        """
        if not self.is_game_started:
            return False, "游戏未开始"
        
        try:
            # 获取外援市场已用名字状态
            foreign_used_names = {}
            if self.foreign_market:
                foreign_used_names = self.foreign_market.get_used_names_state()
            
            # 获取训练状态
            training_state = {}
            if self.training_system:
                training_state = self.training_system.get_training_state_for_save()
            
            state = GameState(
                current_date=self.game_controller.current_date,
                player_team_id=self.player_team_id,
                season_phase="playoff" if self.game_controller.is_playoff_phase else "regular",
                teams=self.teams,
                players=self.players,
                standings=self.season_manager.get_standings(),
                schedule=self.season_manager.schedule,
                playoff_bracket=self.season_manager.playoff_bracket,
                free_agents=self.trade_system.free_agents if self.trade_system else [],
                # 季后赛状态字段 (Requirements 6.1, 6.2, 6.3)
                is_playoff_phase=self.game_controller.is_playoff_phase,
                player_eliminated=self.game_controller.player_eliminated,
                # 外援市场已用名字状态
                foreign_used_names=foreign_used_names,
                # 训练状态
                training_state=training_state
            )
            
            self.storage_manager.save_game(state, slot)
            return True, "保存成功"
            
        except Exception as e:
            return False, str(e)


# 全局游戏状态实例
game_state = GameStateManager()
game_state.initialize_managers()


# ============== 错误响应辅助函数 ==============

def error_response(code: str, message: str, status_code: int = 400):
    """生成统一格式的错误响应"""
    return jsonify({
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }), status_code


def success_response(data=None, message: str = "操作成功"):
    """生成统一格式的成功响应"""
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response)


def check_game_started():
    """检查游戏是否已开始"""
    if not game_state.is_game_started:
        return error_response("GAME_NOT_STARTED", "游戏未开始，请先创建新游戏或加载存档")
    return None


# ============== 游戏状态管理API (Requirements 6.10, 6.12) ==============

@app.route('/api/game/new', methods=['POST'])
def new_game():
    """
    创建新游戏
    
    Request Body:
        team_id: 玩家选择的球队ID
    """
    data = request.get_json() or {}
    team_id = data.get('team_id')
    
    if not team_id:
        return error_response("INVALID_TEAM_ID", "请选择一支球队")
    
    success = game_state.start_new_game(team_id)
    
    if success:
        return success_response(
            data={"team_id": team_id},
            message="新游戏创建成功"
        )
    else:
        return error_response("INVALID_TEAM_ID", f"无效的球队ID: {team_id}")


@app.route('/api/game/load', methods=['POST'])
def load_game():
    """
    加载存档
    
    Request Body:
        slot: 存档槽位 (1-10)
    """
    data = request.get_json() or {}
    slot = data.get('slot')
    
    if not slot or not isinstance(slot, int) or slot < 1 or slot > 10:
        return error_response("INVALID_SLOT", "无效的存档槽位，有效范围为1-10")
    
    success, message = game_state.load_game(slot)
    
    if success:
        return success_response(message=message)
    else:
        return error_response("LOAD_FAILED", message)


@app.route('/api/game/save', methods=['POST'])
def save_game():
    """
    保存游戏
    
    Request Body:
        slot: 存档槽位 (1-10)
    """
    error = check_game_started()
    if error:
        return error
    
    data = request.get_json() or {}
    slot = data.get('slot')
    
    if not slot or not isinstance(slot, int) or slot < 1 or slot > 10:
        return error_response("INVALID_SLOT", "无效的存档槽位，有效范围为1-10")
    
    success, message = game_state.save_game(slot)
    
    if success:
        return success_response(message=message)
    else:
        return error_response("SAVE_FAILED", message)


@app.route('/api/game/export-players', methods=['GET'])
def export_players():
    """
    导出球员名单为players.json格式
    
    - 被裁球员(is_waived=True)不导出
    - 保留当前球员的team_id（包括新签约的外援）
    - 能力值保留当前训练后的数值
    - 统计数据和训练进度重置为0
    """
    error = check_game_started()
    if error:
        return error
    
    # 构建players.json格式的数据
    players_data = {}
    for player_id, player in game_state.players.items():
        # 跳过被裁球员
        if getattr(player, 'is_waived', False):
            continue
            
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
            "trade_index": getattr(player, 'trade_index', 50),
            "is_injured": False,
            "injury_days": 0,
            "games_played": 0,
            "avg_points": 0.0,
            "avg_rebounds": 0.0,
            "avg_assists": 0.0,
            "avg_steals": 0.0,
            "avg_blocks": 0.0,
            "avg_turnovers": 0.0,
            "avg_minutes": 0.0,
            "total_points": 0,
            "total_rebounds": 0,
            "total_assists": 0,
            "total_steals": 0,
            "total_blocks": 0,
            "total_turnovers": 0,
            "total_minutes": 0
        }
    
    export_data = {"players": players_data}
    
    return success_response(data=export_data)


@app.route('/api/game/state', methods=['GET'])
def get_game_state():
    """获取当前游戏状态"""
    error = check_game_started()
    if error:
        return error
    
    controller = game_state.game_controller
    season_manager = game_state.season_manager
    season_status = controller.get_season_status()
    
    # 获取玩家球队信息
    player_team = game_state.teams.get(game_state.player_team_id)
    team_standing = season_manager.get_team_standing(game_state.player_team_id)
    team_rank = season_manager.get_team_rank(game_state.player_team_id)
    
    # 季后赛状态字段 (Requirements 1.1, 1.2)
    is_playoff_phase = controller.is_playoff_phase
    is_regular_season_over = season_manager.is_regular_season_over()
    can_enter_playoffs = is_regular_season_over and not is_playoff_phase
    
    # 调试日志
    print(f"[DEBUG] Playoff entry check: is_regular_season_over={is_regular_season_over}, is_playoff_phase={is_playoff_phase}, can_enter_playoffs={can_enter_playoffs}")
    
    # 玩家球队季后赛状态 (Requirements 1.1, 1.2)
    player_team_playoff_status = {
        "is_in_playoffs": False,
        "is_eliminated": False,
        "is_champion": False,
        "current_series_id": None,
        "series_score": None,
        "series_complete": False,  # 当前系列赛是否已完成
        "game_played_this_round": False  # 玩家是否已在本轮打过一场
    }
    
    if game_state.player_team_id:
        # 检查是否在季后赛中
        player_team_playoff_status["is_in_playoffs"] = season_manager.is_team_in_playoffs(game_state.player_team_id)
        
        # 检查是否被淘汰
        player_team_playoff_status["is_eliminated"] = controller.player_eliminated
        
        # 检查是否是冠军
        champion = season_manager.get_champion()
        player_team_playoff_status["is_champion"] = (champion == game_state.player_team_id)
        
        # 检查玩家是否已在本轮打过一场
        player_team_playoff_status["game_played_this_round"] = controller.player_playoff_game_played_this_round
        
        # 获取当前系列赛
        if is_playoff_phase and not controller.player_eliminated:
            player_series = season_manager.get_player_team_series(game_state.player_team_id)
            if player_series:
                series_id, series = player_series
                player_team_playoff_status["current_series_id"] = series_id
                player_team_playoff_status["series_score"] = f"{series.team1_wins}-{series.team2_wins}"
                player_team_playoff_status["series_complete"] = series.is_complete
    
    # 获取季后赛控制台动作
    playoff_dashboard_action = controller.get_playoff_dashboard_action() if is_playoff_phase else None
    
    state_data = {
        "current_date": controller.current_date,
        "day_type": controller.get_day_type().value,
        "is_match_day": controller.is_match_day(),
        "can_train": controller.can_train(),  # 新增：是否可以训练
        "player_team": {
            "id": game_state.player_team_id,
            "name": player_team.name if player_team else "",
            "city": player_team.city if player_team else "",
            "rank": team_rank,
            "wins": team_standing.wins if team_standing else 0,
            "losses": team_standing.losses if team_standing else 0,
            "win_pct": round(team_standing.win_pct, 3) if team_standing else 0,
            "budget": player_team.budget if player_team else 0  # 球队经费（万元）
        },
        "season_status": season_status,
        "available_actions": controller.get_available_actions(),
        # 新增字段 (Requirements 5.4, 7.1, 7.2, 7.3)
        "player_match_completed_today": controller.player_match_completed_today,
        "has_player_match_today": controller.has_player_match_today(),
        "dashboard_action": controller.get_dashboard_action(),
        "status_message": controller.get_status_message(),
        # 季后赛状态字段 (Requirements 1.1, 1.2)
        "is_playoff_phase": is_playoff_phase,
        "can_enter_playoffs": can_enter_playoffs,
        "player_team_playoff_status": player_team_playoff_status,
        "playoff_dashboard_action": playoff_dashboard_action,  # 新增：季后赛控制台动作
        # 外援市场相关
        "scout_cost": SCOUT_COST  # 球探搜索费用（万元）
    }
    
    # 如果是比赛日，添加今日比赛信息
    if controller.is_match_day():
        today_game = controller.get_player_team_today_game()
        if today_game:
            opponent_id = (today_game.away_team_id 
                         if today_game.home_team_id == game_state.player_team_id 
                         else today_game.home_team_id)
            opponent = game_state.teams.get(opponent_id)
            state_data["today_game"] = {
                "home_team_id": today_game.home_team_id,
                "away_team_id": today_game.away_team_id,
                "opponent_name": opponent.name if opponent else "",
                "is_home": today_game.home_team_id == game_state.player_team_id,
                "is_played": today_game.is_played
            }
    
    return success_response(data=state_data)


@app.route('/api/saves', methods=['GET'])
def list_saves():
    """获取所有存档列表"""
    saves = game_state.storage_manager.list_saves()
    
    save_list = []
    for slot, save_time, team_name, phase_name in saves:
        save_list.append({
            "slot": slot,
            "save_time": save_time,
            "team_name": team_name,
            "phase_name": phase_name
        })
    
    return success_response(data=save_list)


@app.route('/api/saves/<int:slot>', methods=['DELETE'])
def delete_save(slot: int):
    """
    删除指定槽位的存档
    
    Args:
        slot: 存档槽位 (1-10)
    """
    if slot < 1 or slot > 10:
        return error_response("INVALID_SLOT", "无效的存档槽位，有效范围为1-10")
    
    if not game_state.storage_manager.save_exists(slot):
        return error_response("SAVE_NOT_FOUND", f"存档槽位 {slot} 不存在")
    
    success = game_state.storage_manager.delete_save(slot)
    
    if success:
        return success_response(message=f"存档 {slot} 已删除")
    else:
        return error_response("DELETE_FAILED", "删除存档失败")


# ============== 球队和球员API (Requirements 6.2, 6.4) ==============

@app.route('/api/teams', methods=['GET'])
def get_teams():
    """获取所有球队"""
    # 即使游戏未开始也可以获取球队列表（用于选择球队）
    if not game_state.teams:
        # 临时加载球队数据
        temp_manager = PlayerDataManager()
        teams, _ = temp_manager.load_all_data()
    else:
        teams = game_state.teams
    
    teams_list = []
    for team_id, team in teams.items():
        teams_list.append({
            "id": team.id,
            "name": team.name,
            "city": team.city,
            "status": team.status,
            "roster_size": len(team.roster)
        })
    
    # 按城市名排序
    teams_list.sort(key=lambda t: t["city"])
    
    return success_response(data=teams_list)


@app.route('/api/team/<team_id>/roster', methods=['GET'])
def get_roster(team_id: str):
    """获取球队阵容
    
    Query Params:
        mode: 数据模式 (regular/playoff/total)，默认regular
    """
    error = check_game_started()
    if error:
        return error
    
    team = game_state.teams.get(team_id)
    if not team:
        return error_response("INVALID_TEAM_ID", f"无效的球队ID: {team_id}")
    
    # 获取数据模式参数
    mode = request.args.get('mode', 'regular')
    
    roster = game_state.data_manager.get_team_roster(team_id)
    
    players_list = []
    for player in roster:
        if mode == 'playoff':
            # 季后赛数据
            games_played = player.playoff_games_played
            avg_points = round(player.playoff_avg_points, 1)
            avg_rebounds = round(player.playoff_avg_rebounds, 1)
            avg_assists = round(player.playoff_avg_assists, 1)
            avg_steals = round(player.playoff_avg_steals, 1)
            avg_blocks = round(player.playoff_avg_blocks, 1)
        elif mode == 'total':
            # 总数据（常规赛+季后赛）
            total_games = player.games_played + player.playoff_games_played
            if total_games > 0:
                total_points = player.total_points + player.playoff_total_points
                total_rebounds = player.total_rebounds + player.playoff_total_rebounds
                total_assists = player.total_assists + player.playoff_total_assists
                total_steals = player.total_steals + player.playoff_total_steals
                total_blocks = player.total_blocks + player.playoff_total_blocks
                avg_points = round(total_points / total_games, 1)
                avg_rebounds = round(total_rebounds / total_games, 1)
                avg_assists = round(total_assists / total_games, 1)
                avg_steals = round(total_steals / total_games, 1)
                avg_blocks = round(total_blocks / total_games, 1)
            else:
                avg_points = 0.0
                avg_rebounds = 0.0
                avg_assists = 0.0
                avg_steals = 0.0
                avg_blocks = 0.0
            games_played = total_games
        else:
            # 常规赛数据（默认）
            games_played = player.games_played
            avg_points = round(player.avg_points, 1)
            avg_rebounds = round(player.avg_rebounds, 1)
            avg_assists = round(player.avg_assists, 1)
            avg_steals = round(player.avg_steals, 1)
            avg_blocks = round(player.avg_blocks, 1)
        
        players_list.append({
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "overall": player.overall,
            "is_foreign": player.is_foreign,
            "is_injured": player.is_injured,
            "injury_days": player.injury_days,
            "is_waived": player.is_waived,
            "games_played": games_played,
            "avg_points": avg_points,
            "avg_rebounds": avg_rebounds,
            "avg_assists": avg_assists,
            "avg_steals": avg_steals,
            "avg_blocks": avg_blocks
        })
    
    # 按总评降序排序
    players_list.sort(key=lambda p: p["overall"], reverse=True)
    
    return success_response(data={
        "team": {
            "id": team.id,
            "name": team.name,
            "city": team.city
        },
        "roster": players_list,
        "mode": mode
    })


@app.route('/api/player/<player_id>', methods=['GET'])
def get_player(player_id: str):
    """获取球员详情（含场均数据）
    
    Query Params:
        mode: 数据模式 (regular/playoff/total)，默认regular
    """
    error = check_game_started()
    if error:
        return error
    
    # 获取数据模式参数
    mode = request.args.get('mode', 'regular')
    
    profile = game_state.data_manager.get_player_full_profile(player_id, mode=mode)
    
    if not profile:
        return error_response("INVALID_PLAYER_ID", f"无效的球员ID: {player_id}")
    
    # 添加是否是玩家球队球员的标识
    profile['is_player_team'] = (profile.get('team_id') == game_state.player_team_id)
    
    return success_response(data=profile)


# ============== 排行榜API (Requirements 6.8) ==============

@app.route('/api/leaderboard/<stat_type>', methods=['GET'])
def get_leaderboard(stat_type: str):
    """
    获取数据榜单
    
    Args:
        stat_type: 统计类型 (points/rebounds/assists/steals/blocks)
        
    Query Params:
        min_games: 最小场次要求，默认5（季后赛模式下忽略）
        top_n: 返回前N名，默认20
        is_playoff: 是否为季后赛排行榜，默认false
        domestic_only: 是否只显示本土球员，默认false
    """
    error = check_game_started()
    if error:
        return error
    
    min_games = request.args.get('min_games', 5, type=int)
    top_n = request.args.get('top_n', 20, type=int)
    is_playoff = request.args.get('is_playoff', 'false').lower() == 'true'
    domestic_only = request.args.get('domestic_only', 'false').lower() == 'true'
    
    try:
        leaderboard = game_state.stats_leaderboard.get_leaderboard(
            stat_type=stat_type,
            min_games=min_games,
            top_n=top_n,
            is_playoff=is_playoff,
            domestic_only=domestic_only
        )
        
        stat_name = game_state.stats_leaderboard.get_stat_type_name(stat_type)
        
        return success_response(data={
            "stat_type": stat_type,
            "stat_name": stat_name,
            "min_games": min_games,
            "is_playoff": is_playoff,
            "domestic_only": domestic_only,
            "leaderboard": leaderboard
        })
        
    except ValueError as e:
        return error_response("INVALID_STAT_TYPE", str(e))


@app.route('/api/leaderboards', methods=['GET'])
def get_all_leaderboards():
    """
    获取所有榜单
    
    Query Params:
        min_games: 最小场次要求，默认5（季后赛模式下忽略）
        top_n: 返回前N名，默认20
        is_playoff: 是否为季后赛排行榜，默认false
        domestic_only: 是否只显示本土球员，默认false
    """
    error = check_game_started()
    if error:
        return error
    
    min_games = request.args.get('min_games', 5, type=int)
    top_n = request.args.get('top_n', 20, type=int)
    is_playoff = request.args.get('is_playoff', 'false').lower() == 'true'
    domestic_only = request.args.get('domestic_only', 'false').lower() == 'true'
    
    all_leaderboards = game_state.stats_leaderboard.get_all_leaderboards(
        min_games=min_games,
        top_n=top_n,
        is_playoff=is_playoff,
        domestic_only=domestic_only
    )
    
    return success_response(data={
        "min_games": min_games,
        "is_playoff": is_playoff,
        "domestic_only": domestic_only,
        "leaderboards": all_leaderboards
    })


@app.route('/api/leaderboard/total/<stat_type>', methods=['GET'])
def get_total_leaderboard(stat_type: str):
    """
    获取总数据榜单（常规赛+季后赛）
    
    Args:
        stat_type: 统计类型 (points/rebounds/assists/steals/blocks)
        
    Query Params:
        min_games: 最小场次要求，默认5
        top_n: 返回前N名，默认20
        domestic_only: 是否只显示本土球员，默认false
    """
    error = check_game_started()
    if error:
        return error
    
    min_games = request.args.get('min_games', 5, type=int)
    top_n = request.args.get('top_n', 20, type=int)
    domestic_only = request.args.get('domestic_only', 'false').lower() == 'true'
    
    try:
        leaderboard = game_state.stats_leaderboard.get_total_leaderboard(
            stat_type=stat_type,
            min_games=min_games,
            top_n=top_n,
            domestic_only=domestic_only
        )
        
        stat_name = game_state.stats_leaderboard.get_stat_type_name(stat_type)
        
        return success_response(data={
            "stat_type": stat_type,
            "stat_name": stat_name,
            "min_games": min_games,
            "domestic_only": domestic_only,
            "leaderboard": leaderboard
        })
        
    except ValueError as e:
        return error_response("INVALID_STAT_TYPE", str(e))


@app.route('/api/leaderboards/total', methods=['GET'])
def get_all_total_leaderboards():
    """
    获取所有总数据榜单（常规赛+季后赛）
    
    Query Params:
        min_games: 最小场次要求，默认5
        top_n: 返回前N名，默认20
    """
    error = check_game_started()
    if error:
        return error
    
    min_games = request.args.get('min_games', 5, type=int)
    top_n = request.args.get('top_n', 20, type=int)
    
    all_leaderboards = game_state.stats_leaderboard.get_all_total_leaderboards(
        min_games=min_games,
        top_n=top_n
    )
    
    return success_response(data={
        "min_games": min_games,
        "leaderboards": all_leaderboards
    })


@app.route('/api/leaderboard/team-standings', methods=['GET'])
def get_team_standings_leaderboard():
    """
    获取球队战绩排行榜
    
    返回20支球队的战绩排名
    季后赛阶段返回常规赛结束时的排名（保持不变）
    """
    error = check_game_started()
    if error:
        return error
    
    leaderboard = game_state.stats_leaderboard.get_team_standings_leaderboard()
    is_cached = game_state.stats_leaderboard.is_team_standings_cached()
    
    return success_response(data={
        "leaderboard": leaderboard,
        "is_playoff_cached": is_cached
    })


# ============== 比赛和赛程API (Requirements 6.3, 6.7, 6.9) ==============

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """
    获取赛程
    
    Query Params:
        team_id: 筛选指定球队的比赛（可选）
        played: 筛选已完成/未完成的比赛（可选，true/false）
        limit: 返回数量限制（可选）
    """
    error = check_game_started()
    if error:
        return error
    
    team_id = request.args.get('team_id')
    played_filter = request.args.get('played')
    limit = request.args.get('limit', type=int)
    
    schedule = game_state.season_manager.schedule
    
    # 筛选
    filtered_schedule = []
    for game in schedule:
        # 球队筛选
        if team_id:
            if game.home_team_id != team_id and game.away_team_id != team_id:
                continue
        
        # 完成状态筛选
        if played_filter is not None:
            is_played = played_filter.lower() == 'true'
            if game.is_played != is_played:
                continue
        
        home_team = game_state.teams.get(game.home_team_id)
        away_team = game_state.teams.get(game.away_team_id)
        
        game_data = {
            "date": game.date,
            "home_team_id": game.home_team_id,
            "home_team_name": home_team.name if home_team else "",
            "away_team_id": game.away_team_id,
            "away_team_name": away_team.name if away_team else "",
            "is_played": game.is_played
        }
        
        if game.is_played and game.result:
            game_data["home_score"] = game.result.home_score
            game_data["away_score"] = game.result.away_score
        
        filtered_schedule.append(game_data)
    
    # 限制数量
    if limit:
        filtered_schedule = filtered_schedule[:limit]
    
    return success_response(data={
        "total": len(filtered_schedule),
        "schedule": filtered_schedule
    })


@app.route('/api/standings', methods=['GET'])
def get_standings():
    """获取排行榜"""
    error = check_game_started()
    if error:
        return error
    
    standings = game_state.season_manager.get_standings()
    
    standings_list = []
    for i, standing in enumerate(standings, start=1):
        team = game_state.teams.get(standing.team_id)
        standings_list.append({
            "rank": i,
            "team_id": standing.team_id,
            "team_name": team.name if team else "",
            "wins": standing.wins,
            "losses": standing.losses,
            "win_pct": round(standing.win_pct, 3),
            "games_behind": standing.games_behind
        })
    
    return success_response(data=standings_list)


@app.route('/api/daily-games/<date>', methods=['GET'])
def get_daily_games(date: str):
    """
    获取当日比赛
    
    返回指定日期的所有比赛及其完整球员统计数据
    
    Args:
        date: 日期字符串 (YYYY-MM-DD格式)
        
    Returns:
        {
            "date": str,
            "total_games": int,
            "played_games": int,
            "games": [
                {
                    "date": str,
                    "home_team_id": str,
                    "home_team_name": str,
                    "away_team_id": str,
                    "away_team_name": str,
                    "home_score": int,
                    "away_score": int,
                    "is_played": bool,
                    "player_stats": {
                        "home_team": [...],
                        "away_team": [...]
                    },
                    "quarter_scores": [...],
                    "highlights": [...]
                },
                ...
            ],
            "message": str (无比赛时)
        }
        
    Requirements: 3.1, 3.2, 3.3
    """
    error = check_game_started()
    if error:
        return error
    
    # 验证日期格式
    try:
        from datetime import datetime
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return error_response("INVALID_DATE", f"无效的日期格式: {date}，请使用YYYY-MM-DD格式")
    
    daily_summary = game_state.daily_stats_viewer.get_daily_summary(date)
    
    # 确保每场比赛都有完整的球员统计数据 (Requirements 3.1, 3.2)
    if daily_summary.get("games"):
        for game in daily_summary["games"]:
            # 确保player_stats字段存在且格式正确
            if "player_stats" not in game:
                game["player_stats"] = {"home_team": [], "away_team": []}
            elif not isinstance(game["player_stats"], dict):
                game["player_stats"] = {"home_team": [], "away_team": []}
            else:
                # 确保home_team和away_team字段存在
                if "home_team" not in game["player_stats"]:
                    game["player_stats"]["home_team"] = []
                if "away_team" not in game["player_stats"]:
                    game["player_stats"]["away_team"] = []
            
            # 确保每个球员统计都包含所有必要字段 (Requirements 3.2)
            for team_key in ["home_team", "away_team"]:
                for player_stat in game["player_stats"].get(team_key, []):
                    # 确保所有统计字段存在
                    player_stat.setdefault("points", 0)
                    player_stat.setdefault("rebounds", 0)
                    player_stat.setdefault("assists", 0)
                    player_stat.setdefault("steals", 0)
                    player_stat.setdefault("blocks", 0)
                    player_stat.setdefault("turnovers", 0)
                    player_stat.setdefault("minutes", 0)
    
    return success_response(data=daily_summary)


@app.route('/api/advance-day-only', methods=['POST'])
def advance_day_only():
    """
    仅推进日期API (Requirements 1.1, 1.2, 1.5)
    
    流程:
    1. 检查玩家球队是否有未完成的比赛（如果有则阻止推进）
    2. 检查当前日期是否有未模拟的AI比赛
    3. 如果有AI比赛未模拟，先模拟
    4. 推进日期到下一天
    5. 返回新状态
    
    注意：此方法不会模拟下一天的任何比赛
    
    Returns:
        {
            "success": true,
            "data": {
                "previous_date": str,
                "new_date": str,
                "ai_matches_simulated": [...],
                "new_day_type": str,
                "has_player_match": bool,
                "dashboard_action": str
            }
        }
        
    Error Response (如果玩家有未完成比赛):
        {
            "success": false,
            "error": {
                "code": "PLAYER_MATCH_PENDING",
                "message": "玩家球队今天有未完成的比赛，请先完成比赛再推进日期"
            }
        }
    """
    error = check_game_started()
    if error:
        return error
    
    controller = game_state.game_controller
    
    try:
        # 调用 advance_day_only() 方法
        result = controller.advance_day_only()
        
        # 格式化AI比赛结果
        ai_matches = []
        for match_result in result.get("ai_matches_simulated", []):
            home_team = game_state.teams.get(match_result.home_team_id)
            away_team = game_state.teams.get(match_result.away_team_id)
            ai_matches.append({
                "home_team_id": match_result.home_team_id,
                "home_team_name": home_team.name if home_team else "",
                "away_team_id": match_result.away_team_id,
                "away_team_name": away_team.name if away_team else "",
                "home_score": match_result.home_score,
                "away_score": match_result.away_score
            })
        
        # 格式化伤病信息
        injury_list = []
        for player, days in result.get("new_injuries", []):
            injury_list.append({
                "player_id": player.id,
                "player_name": player.name,
                "recovery_days": days
            })
        
        # 格式化恢复球员信息
        recovered_list = []
        for player in result.get("recovered_players", []):
            recovered_list.append({
                "player_id": player.id,
                "player_name": player.name
            })
        
        return success_response(
            data={
                "previous_date": result["previous_date"],
                "new_date": result["new_date"],
                "ai_matches_simulated": ai_matches,
                "new_injuries": injury_list,
                "recovered_players": recovered_list,
                "new_day_type": result["new_day_type"],
                "has_player_match": result["has_player_match"],
                "dashboard_action": result["dashboard_action"],
                "status_message": result.get("status_message", "")
            },
            message="日期推进成功"
        )
        
    except ValueError as e:
        # 玩家球队有未完成的比赛
        error_msg = str(e)
        if "未完成的比赛" in error_msg:
            return error_response("PLAYER_MATCH_PENDING", error_msg)
        return error_response("ADVANCE_DAY_ERROR", f"日期推进失败: {error_msg}")
        
    except Exception as e:
        return error_response("ADVANCE_DAY_ERROR", f"日期推进失败: {str(e)}")


@app.route('/api/advance-day', methods=['POST'])
def advance_day():
    """
    推进日期 (Requirements 1.1, 1.2)
    
    改为调用 advance_day_only() 方法，保持API兼容性
    
    Request Body:
        days: 推进天数，默认1（为兼容性保留，实际只推进1天）
        auto_simulate: 是否自动模拟比赛，默认true（为兼容性保留）
        use_llm: 是否使用LLM，默认true（为兼容性保留）
    
    Returns:
        与原API兼容的响应格式
        
    Error Response (如果玩家有未完成比赛):
        {
            "success": false,
            "error": {
                "code": "PLAYER_MATCH_PENDING",
                "message": "玩家球队今天有未完成的比赛，请先完成比赛再推进日期"
            }
        }
    """
    error = check_game_started()
    if error:
        return error
    
    data = request.get_json() or {}
    days = data.get('days', 1)
    
    if days < 1:
        return error_response("INVALID_DAYS", "推进天数必须为正整数")
    
    controller = game_state.game_controller
    
    try:
        # 改为调用 advance_day_only() 方法 (Requirements 1.1, 1.2)
        # 如果需要推进多天，循环调用
        all_day_results = []
        previous_date = controller.current_date
        
        for _ in range(days):
            result = controller.advance_day_only()
            
            # 格式化当天结果
            matches = []
            for match_result in result.get("ai_matches_simulated", []):
                home_team = game_state.teams.get(match_result.home_team_id)
                away_team = game_state.teams.get(match_result.away_team_id)
                matches.append({
                    "home_team_name": home_team.name if home_team else "",
                    "away_team_name": away_team.name if away_team else "",
                    "home_score": match_result.home_score,
                    "away_score": match_result.away_score
                })
            
            all_day_results.append({
                "date": result["new_date"],
                "day_type": result["new_day_type"],
                "matches_played": matches
            })
        
        return success_response(data={
            "previous_date": previous_date,
            "new_date": controller.current_date,
            "days_advanced": days,
            "day_results": all_day_results
        })
        
    except ValueError as e:
        # 玩家球队有未完成的比赛
        error_msg = str(e)
        if "未完成的比赛" in error_msg:
            return error_response("PLAYER_MATCH_PENDING", error_msg)
        return error_response("ADVANCE_FAILED", error_msg)
        
    except Exception as e:
        return error_response("ADVANCE_FAILED", str(e))


# ============== 训练和交易API (Requirements 6.5, 6.6) ==============

@app.route('/api/training/programs', methods=['GET'])
def get_training_programs():
    """获取训练项目"""
    programs = []
    for program in TRAINING_PROGRAMS:
        programs.append({
            "name": program.name,
            "target_attribute": program.target_attribute,
            "boost_min": program.boost_min,
            "boost_max": program.boost_max
        })
    
    return success_response(data=programs)


@app.route('/api/training/status', methods=['GET'])
def get_training_status():
    """
    获取训练状态
    
    返回今日训练次数使用情况
    """
    error = check_game_started()
    if error:
        return error
    
    # 检查是否在季后赛阶段
    is_playoff_phase = game_state.game_controller.is_playoff_phase
    
    # 确保训练系统日期同步
    current_date = game_state.game_controller.current_date
    game_state.training_system._check_and_reset_if_new_day(current_date)
    
    status = game_state.training_system.get_training_status()
    
    # 添加季后赛状态
    status["is_playoff_phase"] = is_playoff_phase
    if is_playoff_phase:
        status["playoff_restriction_message"] = "季后赛阶段无法进行训练"
    
    # 获取玩家球队阵容的单独训练剩余次数
    roster = game_state.data_manager.get_team_roster(game_state.player_team_id)
    individual_remaining = {}
    for player in roster:
        individual_remaining[player.id] = {
            "player_name": player.name,
            "remaining": game_state.training_system.get_individual_training_remaining(player.id)
        }
    
    status["individual_training_remaining"] = individual_remaining
    
    return success_response(data=status)


@app.route('/api/training/execute', methods=['POST'])
def execute_training():
    """
    执行训练
    
    Request Body:
        program_name: 训练项目名称
        player_id: 球员ID（可选，不提供则训练全队）
    
    训练限制:
        - 每天最多2次全队训练
        - 每个球员每天最多2次单独训练
        - 每次训练随机提升0~2点训练点数
        - 训练点数达到20时，该属性+1
        - 累积5次属性+1后，总评+1
        - 季后赛阶段无法训练
    """
    error = check_game_started()
    if error:
        return error
    
    # 检查是否在季后赛阶段
    if game_state.game_controller.is_playoff_phase:
        return error_response("PLAYOFF_RESTRICTION", "季后赛阶段无法进行训练")
    
    # 检查是否可以训练（只有玩家球队有比赛时才不能训练）
    if not game_state.game_controller.can_train():
        return error_response("TRAINING_NOT_ALLOWED", "今天有比赛，无法进行训练")
    
    data = request.get_json() or {}
    program_name = data.get('program_name')
    player_id = data.get('player_id')
    
    if not program_name:
        return error_response("INVALID_PROGRAM", "请选择训练项目")
    
    # 获取训练项目
    program = game_state.training_system.get_program_by_name(program_name)
    if not program:
        return error_response("INVALID_PROGRAM", f"无效的训练项目: {program_name}")
    
    # 获取玩家球队
    player_team = game_state.teams.get(game_state.player_team_id)
    if not player_team:
        return error_response("GAME_NOT_STARTED", "游戏状态异常")
    
    # 获取当前日期用于训练次数跟踪
    current_date = game_state.game_controller.current_date
    
    try:
        if player_id:
            # 训练单个球员
            result = game_state.training_system.train_single_player(
                team=player_team,
                player_id=player_id,
                program=program,
                current_date=current_date
            )
            
            player = game_state.players.get(player_id)
            remaining = game_state.training_system.get_individual_training_remaining(player_id)
            
            # 构建消息
            msg_parts = [f"训练点数+{result['training_points_gained']}"]
            if result.get('attribute_upgraded'):
                msg_parts.append(f"{program.target_attribute}+1")
            if result.get('overall_upgraded'):
                msg_parts.append("总评+1")
            msg_parts.append(f"剩余{remaining}次单独训练")
            
            return success_response(
                data={
                    "player_id": player_id,
                    "player_name": player.name if player else "",
                    "attribute": program.target_attribute,
                    "target_attribute": program.target_attribute,
                    "training_points_gained": result['training_points_gained'],
                    "attribute_upgraded": result['attribute_upgraded'],
                    "overall_upgraded": result['overall_upgraded'],
                    "current_training_points": result['current_training_points'],
                    "current_attribute_upgrades": result['current_attribute_upgrades'],
                    "individual_training_remaining": remaining
                },
                message="，".join(msg_parts)
            )
        else:
            # 训练全队
            results = game_state.training_system.apply_team_training(
                team=player_team,
                program=program,
                current_date=current_date
            )
            
            training_results = []
            total_upgrades = 0
            total_overall_upgrades = 0
            for pid, result in results.items():
                player = game_state.players.get(pid)
                training_results.append({
                    "player_id": pid,
                    "player_name": player.name if player else "",
                    "training_points_gained": result['training_points_gained'],
                    "attribute_upgraded": result['attribute_upgraded'],
                    "overall_upgraded": result['overall_upgraded'],
                    "current_training_points": result['current_training_points'],
                    "current_attribute_upgrades": result['current_attribute_upgrades'],
                    "skipped": result.get('skipped', False)
                })
                if result.get('attribute_upgraded'):
                    total_upgrades += 1
                if result.get('overall_upgraded'):
                    total_overall_upgrades += 1
            
            remaining = game_state.training_system.get_team_training_remaining()
            
            # 构建消息
            msg_parts = ["全队训练完成"]
            if total_upgrades > 0:
                msg_parts.append(f"{total_upgrades}人属性提升")
            if total_overall_upgrades > 0:
                msg_parts.append(f"{total_overall_upgrades}人总评提升")
            msg_parts.append(f"剩余{remaining}次全队训练")
            
            return success_response(
                data={
                    "attribute": program.target_attribute,
                    "target_attribute": program.target_attribute,
                    "results": training_results,
                    "team_training_remaining": remaining,
                    "total_attribute_upgrades": total_upgrades,
                    "total_overall_upgrades": total_overall_upgrades
                },
                message="，".join(msg_parts)
            )
            
    except TrainingLimitError as e:
        return error_response("TRAINING_LIMIT_REACHED", str(e))
    except Exception as e:
        return error_response("TRAINING_FAILED", str(e))


@app.route('/api/training/progress/<player_id>', methods=['GET'])
def get_player_training_progress(player_id: str):
    """
    获取球员训练进度
    
    Args:
        player_id: 球员ID
        
    Returns:
        球员的训练进度信息，包括各属性训练点数和属性提升计数
    """
    error = check_game_started()
    if error:
        return error
    
    player = game_state.players.get(player_id)
    if not player:
        return error_response("INVALID_PLAYER_ID", f"无效的球员ID: {player_id}")
    
    # 确保训练进度字段存在
    training_points = player.training_points if hasattr(player, 'training_points') and player.training_points else {
        "offense": 0, "defense": 0, "three_point": 0,
        "rebounding": 0, "passing": 0, "stamina": 0
    }
    attribute_upgrades = player.attribute_upgrades if hasattr(player, 'attribute_upgrades') else 0
    
    return success_response(data={
        "player_id": player.id,
        "player_name": player.name,
        "training_points": training_points,
        "attribute_upgrades": attribute_upgrades,
        "points_per_upgrade": 20,
        "upgrades_per_overall": 5,
        "current_attributes": {
            "offense": player.offense,
            "defense": player.defense,
            "three_point": player.three_point,
            "rebounding": player.rebounding,
            "passing": player.passing,
            "stamina": player.stamina
        },
        "overall": player.overall
    })


@app.route('/api/training/team-progress', methods=['GET'])
def get_team_training_progress():
    """
    获取玩家球队所有球员的训练进度
    
    Returns:
        球队所有球员的训练进度列表
    """
    error = check_game_started()
    if error:
        return error
    
    team_id = game_state.player_team_id
    roster = game_state.data_manager.get_team_roster(team_id)
    
    players_progress = []
    for player in roster:
        # 确保训练进度字段存在
        training_points = player.training_points if hasattr(player, 'training_points') and player.training_points else {
            "offense": 0, "defense": 0, "three_point": 0,
            "rebounding": 0, "passing": 0, "stamina": 0
        }
        attribute_upgrades = player.attribute_upgrades if hasattr(player, 'attribute_upgrades') else 0
        
        # 计算总训练点数
        total_training_points = sum(training_points.values())
        
        players_progress.append({
            "player_id": player.id,
            "player_name": player.name,
            "position": player.position,
            "overall": player.overall,
            "is_injured": player.is_injured,
            "training_points": training_points,
            "total_training_points": total_training_points,
            "attribute_upgrades": attribute_upgrades,
            "current_attributes": {
                "offense": player.offense,
                "defense": player.defense,
                "three_point": player.three_point,
                "rebounding": player.rebounding,
                "passing": player.passing,
                "stamina": player.stamina
            }
        })
    
    # 按总评降序排序
    players_progress.sort(key=lambda p: p["overall"], reverse=True)
    
    return success_response(data={
        "players": players_progress,
        "points_per_upgrade": 20,
        "upgrades_per_overall": 5
    })


@app.route('/api/trade/propose', methods=['POST'])
def propose_trade():
    """
    发起交易
    
    Request Body:
        receiving_team_id: 接收交易的球队ID
        players_offered: 提供的球员ID列表
        players_requested: 请求的球员ID列表
        
    注意: 季后赛阶段无法进行交易
    """
    error = check_game_started()
    if error:
        return error
    
    # 检查是否在季后赛阶段
    if game_state.game_controller.is_playoff_phase:
        return error_response("PLAYOFF_RESTRICTION", "季后赛阶段无法进行交易")
    
    data = request.get_json() or {}
    receiving_team_id = data.get('receiving_team_id')
    players_offered = data.get('players_offered', [])
    players_requested = data.get('players_requested', [])
    
    if not receiving_team_id:
        return error_response("INVALID_TEAM_ID", "请选择交易对象球队")
    
    if not players_offered or not players_requested:
        return error_response("INVALID_TRADE", "请选择交易球员")
    
    # 创建交易提案
    proposal = TradeProposal(
        offering_team_id=game_state.player_team_id,
        receiving_team_id=receiving_team_id,
        players_offered=players_offered,
        players_requested=players_requested
    )
    
    success, message = game_state.trade_system.propose_trade(proposal)
    
    if success:
        return success_response(message=message)
    else:
        return error_response("TRADE_REJECTED", message)


@app.route('/api/trade/available-players/<team_id>', methods=['GET'])
def get_tradeable_players(team_id):
    """
    获取指定球队可交易的球员列表
    
    外援不可被交易，会被排除在列表之外
    
    Args:
        team_id: 球队ID
        
    Returns:
        可交易球员列表
    """
    error = check_game_started()
    if error:
        return error
    
    team = game_state.teams.get(team_id)
    if not team:
        return error_response("TEAM_NOT_FOUND", "找不到指定球队")
    
    # 获取可交易球员（排除外援）
    available_players = game_state.trade_system.get_available_players(team_id)
    
    players_list = []
    for player in available_players:
        players_list.append({
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "overall": player.overall,
            "trade_index": player.trade_index,
            "is_foreign": player.is_foreign
        })
    
    # 按总评降序排序
    players_list.sort(key=lambda p: p["overall"], reverse=True)
    
    return success_response(data={
        "team_id": team_id,
        "team_name": team.name,
        "players": players_list,
        "note": "外援不可被交易"
    })


@app.route('/api/free-agents', methods=['GET'])
def get_free_agents():
    """获取自由球员"""
    error = check_game_started()
    if error:
        return error
    
    free_agents = game_state.trade_system.get_free_agents()
    
    agents_list = []
    for player in free_agents:
        agents_list.append({
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "overall": player.overall,
            "is_foreign": player.is_foreign
        })
    
    # 按总评降序排序
    agents_list.sort(key=lambda p: p["overall"], reverse=True)
    
    return success_response(data=agents_list)


@app.route('/api/free-agents/sign', methods=['POST'])
def sign_free_agent():
    """
    签约自由球员
    
    Request Body:
        player_id: 自由球员ID
    """
    error = check_game_started()
    if error:
        return error
    
    data = request.get_json() or {}
    player_id = data.get('player_id')
    
    if not player_id:
        return error_response("INVALID_PLAYER_ID", "请选择要签约的球员")
    
    success, message = game_state.trade_system.sign_free_agent(
        team_id=game_state.player_team_id,
        player_id=player_id
    )
    
    if success:
        return success_response(message=message)
    else:
        return error_response("SIGN_FAILED", message)


# ============== 玩家比赛模拟API ==============

@app.route('/api/match/simulate-player', methods=['POST'])
def simulate_player_match():
    """
    模拟玩家球队比赛（快速模拟）
    
    使用与AI球队相同的快速模拟方法，返回比分和球员统计数据
    
    Returns:
        比赛结果，包括:
        - home_team_id/name: 主队信息
        - away_team_id/name: 客队信息
        - home_score/away_score: 比分
        - player_stats: 球员统计数据
        - new_injuries: 新伤病列表
        - budget_reward: 经费奖励（万元）
        - current_budget: 当前经费（万元）
    """
    error = check_game_started()
    if error:
        return error
    
    controller = game_state.game_controller
    
    # 检查今天是否有玩家球队比赛
    if not controller.has_player_match_today():
        return error_response("NO_MATCH_TODAY", "今天没有玩家球队的比赛")
    
    # 检查比赛是否已完成
    if controller.is_player_match_completed():
        return error_response("MATCH_ALREADY_COMPLETED", "今天的比赛已经完成")
    
    try:
        # 模拟玩家球队比赛（使用快速模拟）
        result, injuries, budget_reward = controller.simulate_player_match()
        
        if result is None:
            return error_response("SIMULATION_FAILED", "比赛模拟失败")
        
        # 获取球队信息
        home_team = game_state.teams.get(result.home_team_id)
        away_team = game_state.teams.get(result.away_team_id)
        player_team = game_state.teams.get(game_state.player_team_id)
        
        # 格式化球员统计数据
        formatted_player_stats = _format_player_stats_for_response(
            result.player_stats,
            result.home_team_id,
            result.away_team_id
        )
        
        # 格式化伤病信息
        injury_list = []
        for player, days in injuries:
            injury_list.append({
                "player_id": player.id,
                "player_name": player.name,
                "recovery_days": days
            })
        
        return success_response(
            data={
                "home_team_id": result.home_team_id,
                "home_team_name": home_team.name if home_team else "",
                "away_team_id": result.away_team_id,
                "away_team_name": away_team.name if away_team else "",
                "home_score": result.home_score,
                "away_score": result.away_score,
                "player_stats": formatted_player_stats,
                "new_injuries": injury_list,
                "player_match_completed_today": True,
                "budget_reward": budget_reward,
                "current_budget": player_team.budget if player_team else 0
            },
            message="比赛模拟完成"
        )
        
    except ValueError as e:
        return error_response("SIMULATION_ERROR", str(e))
    except Exception as e:
        return error_response("SIMULATION_FAILED", f"比赛模拟失败: {str(e)}")


@app.route('/api/advance-day-after-match', methods=['POST'])
def advance_day_after_match():
    """
    比赛后推进日期
    
    快速模拟当天剩余AI球队比赛，然后推进日期
    
    Request Body:
        use_llm: 是否使用LLM进行AI比赛模拟（可选，默认True）
        
    Returns:
        推进结果，包括:
        - previous_date: 之前的日期
        - new_date: 新日期
        - ai_matches_simulated: AI比赛模拟结果列表
        - new_injuries: 新伤病列表
        - recovered_players: 恢复健康的球员列表
        
    Requirements: 5.5
    """
    error = check_game_started()
    if error:
        return error
    
    data = request.get_json() or {}
    use_llm = data.get('use_llm', True)
    
    controller = game_state.game_controller
    
    # 检查是否可以推进日期
    if not controller.can_advance_day():
        return error_response(
            "CANNOT_ADVANCE", 
            "玩家球队今天的比赛尚未完成，无法推进日期"
        )
    
    try:
        # 推进日期并模拟AI比赛
        result = controller.advance_day_with_ai_simulation(use_llm=use_llm)
        
        # 格式化AI比赛结果
        ai_matches = []
        for match_result in result.get("ai_matches_simulated", []):
            home_team = game_state.teams.get(match_result.home_team_id)
            away_team = game_state.teams.get(match_result.away_team_id)
            ai_matches.append({
                "home_team_id": match_result.home_team_id,
                "home_team_name": home_team.name if home_team else "",
                "away_team_id": match_result.away_team_id,
                "away_team_name": away_team.name if away_team else "",
                "home_score": match_result.home_score,
                "away_score": match_result.away_score
            })
        
        # 格式化伤病信息
        injury_list = []
        for player, days in result.get("new_injuries", []):
            injury_list.append({
                "player_id": player.id,
                "player_name": player.name,
                "recovery_days": days
            })
        
        # 格式化恢复球员信息
        recovered_list = []
        for player in result.get("recovered_players", []):
            recovered_list.append({
                "player_id": player.id,
                "player_name": player.name
            })
        
        return success_response(
            data={
                "previous_date": result["previous_date"],
                "new_date": result["new_date"],
                "ai_matches_simulated": ai_matches,
                "new_injuries": injury_list,
                "recovered_players": recovered_list
            },
            message="日期推进成功"
        )
        
    except ValueError as e:
        return error_response("ADVANCE_ERROR", str(e))
    except Exception as e:
        return error_response("ADVANCE_FAILED", f"日期推进失败: {str(e)}")


@app.route('/api/game/dashboard-action', methods=['GET'])
def get_dashboard_action():
    """
    获取控制台主按钮状态
    
    返回应显示的按钮类型:
    - 'go_to_match': 玩家球队今天有比赛且未完成，显示"前往比赛"按钮
    - 'advance_day': 玩家球队今天没有比赛或比赛已完成，显示"推进日期"按钮
    
    Returns:
        {
            "action": "go_to_match" | "advance_day",
            "has_player_match_today": bool,
            "player_match_completed_today": bool,
            "is_match_day": bool,
            "today_game": {...} (如果有玩家比赛)
        }
        
    Requirements: 5.2, 5.3, 5.5
    """
    error = check_game_started()
    if error:
        return error
    
    controller = game_state.game_controller
    
    # 获取dashboard动作
    action = controller.get_dashboard_action()
    has_player_match = controller.has_player_match_today()
    match_completed = controller.is_player_match_completed()
    is_match_day = controller.is_match_day()
    
    response_data = {
        "action": action,
        "has_player_match_today": has_player_match,
        "player_match_completed_today": match_completed,
        "is_match_day": is_match_day
    }
    
    # 如果有玩家比赛，添加比赛信息
    if has_player_match:
        today_game = controller.get_player_team_today_game()
        if today_game:
            opponent_id = (today_game.away_team_id 
                         if today_game.home_team_id == game_state.player_team_id 
                         else today_game.home_team_id)
            opponent = game_state.teams.get(opponent_id)
            response_data["today_game"] = {
                "home_team_id": today_game.home_team_id,
                "away_team_id": today_game.away_team_id,
                "opponent_name": opponent.name if opponent else "",
                "is_home": today_game.home_team_id == game_state.player_team_id,
                "is_played": today_game.is_played
            }
    
    return success_response(data=response_data)


def _format_player_stats_for_response(
    player_stats: dict,
    home_team_id: str,
    away_team_id: str
) -> dict:
    """
    格式化球员统计数据用于API响应
    
    Args:
        player_stats: 原始球员统计数据 {player_id: GameStats}
        home_team_id: 主队ID
        away_team_id: 客队ID
        
    Returns:
        格式化后的球员数据，按球队分组
    """
    home_stats = []
    away_stats = []
    
    # 调试日志
    print(f"[DEBUG] _format_player_stats_for_response called")
    print(f"[DEBUG] home_team_id: {home_team_id}, away_team_id: {away_team_id}")
    print(f"[DEBUG] player_stats count: {len(player_stats)}")
    
    for player_id, stats in player_stats.items():
        player = game_state.players.get(player_id)
        if not player:
            print(f"[DEBUG] Player not found: {player_id}")
            continue
        
        print(f"[DEBUG] Player {player.name} (team_id: {player.team_id}): {stats.points} pts")
        
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
        
        if player.team_id == home_team_id:
            home_stats.append(stat_entry)
        elif player.team_id == away_team_id:
            away_stats.append(stat_entry)
        else:
            print(f"[DEBUG] Player {player.name} team_id {player.team_id} doesn't match home or away")
    
    # 按得分降序排序
    home_stats.sort(key=lambda x: x["points"], reverse=True)
    away_stats.sort(key=lambda x: x["points"], reverse=True)
    
    print(f"[DEBUG] home_stats count: {len(home_stats)}, away_stats count: {len(away_stats)}")
    
    return {
        "home_team": home_stats,
        "away_team": away_stats,
    }


# ============== 季后赛API (Requirements 5.1, 5.2, 5.3, 5.4, 5.5) ==============

@app.route('/api/playoff/bracket', methods=['GET'])
def get_playoff_bracket():
    """
    获取季后赛对阵图 (Requirements 5.1, 5.5)
    
    返回完整的季后赛对阵图数据，包括所有轮次的系列赛信息。
    
    Returns:
        {
            "success": true,
            "data": {
                "is_playoff_phase": bool,
                "current_round": str,  # "play_in" | "quarter" | "semi" | "final" | "champion"
                "bracket": {
                    "play_in": [...],
                    "quarter_seeds": [...],
                    "quarter": [...],
                    "semi": [...],
                    "final": {...}
                },
                "champion_id": str | null,
                "champion_name": str | null
            }
        }
    """
    error = check_game_started()
    if error:
        return error
    
    # 调用 season_manager.get_playoff_bracket_for_display()
    bracket_data = game_state.season_manager.get_playoff_bracket_for_display(game_state.teams)
    
    return success_response(data=bracket_data)


@app.route('/api/playoff/init', methods=['POST'])
def init_playoffs():
    """
    初始化季后赛 (Requirements 5.2)
    
    在常规赛结束后调用，初始化季后赛对阵并调整AI球员能力值。
    
    Returns:
        {
            "success": true,
            "data": {
                "playoff_teams": [...],
                "ai_adjustments": {...}
            },
            "message": "季后赛初始化成功"
        }
    """
    error = check_game_started()
    if error:
        return error
    
    try:
        # 在进入季后赛前缓存球队战绩排行榜
        game_state.stats_leaderboard.cache_team_standings()
        
        # 调用 game_controller.enter_playoffs()
        result = game_state.game_controller.enter_playoffs()
        
        if result["success"]:
            return success_response(
                data={
                    "playoff_teams": result["playoff_teams"],
                    "ai_adjustments": result["ai_adjustments"]
                },
                message=result["message"]
            )
        else:
            return error_response("PLAYOFF_INIT_FAILED", result["message"])
            
    except ValueError as e:
        return error_response("PLAYOFF_INIT_FAILED", str(e))
    except Exception as e:
        return error_response("PLAYOFF_INIT_ERROR", f"季后赛初始化失败: {str(e)}")


@app.route('/api/playoff/simulate-game', methods=['POST'])
def simulate_playoff_game():
    """
    模拟季后赛比赛 (Requirements 5.3)
    
    模拟指定系列赛的一场比赛。
    
    Request Body:
        series_id: 系列赛ID (如 "play_in_1", "quarter_1", "semi_1", "final")
        use_llm: 是否使用LLM进行模拟（可选，默认True）
        match_context: 比赛背景信息（可选）
    
    Returns:
        {
            "success": true,
            "data": {
                "match_result": {...},
                "series_update": {...},
                "next_round_created": bool
            }
        }
    """
    error = check_game_started()
    if error:
        return error
    
    data = request.get_json() or {}
    series_id = data.get('series_id')
    use_llm = data.get('use_llm', True)
    match_context = data.get('match_context')
    
    if not series_id:
        return error_response("INVALID_SERIES_ID", "请提供系列赛ID")
    
    try:
        # 调用 game_controller.simulate_playoff_game()
        result, series_update = game_state.game_controller.simulate_playoff_game(
            series_id=series_id,
            use_llm=use_llm,
            match_context=match_context
        )
        
        if result is None:
            return error_response("SIMULATION_FAILED", "比赛模拟失败")
        
        # 获取球队信息
        home_team = game_state.teams.get(result.home_team_id)
        away_team = game_state.teams.get(result.away_team_id)
        
        # 格式化球员统计数据
        formatted_player_stats = _format_player_stats_for_response(
            result.player_stats,
            result.home_team_id,
            result.away_team_id
        )
        
        return success_response(
            data={
                "match_result": {
                    "home_team_id": result.home_team_id,
                    "home_team_name": home_team.name if home_team else "",
                    "away_team_id": result.away_team_id,
                    "away_team_name": away_team.name if away_team else "",
                    "home_score": result.home_score,
                    "away_score": result.away_score,
                    "player_stats": formatted_player_stats
                },
                "series_update": series_update,
                "next_round_created": series_update.get("next_round_created", False)
            },
            message="比赛模拟完成"
        )
        
    except ValueError as e:
        return error_response("SIMULATION_ERROR", str(e))
    except Exception as e:
        return error_response("SIMULATION_FAILED", f"比赛模拟失败: {str(e)}")


@app.route('/api/playoff/status', methods=['GET'])
def get_playoff_status():
    """
    获取季后赛状态摘要 (Requirements 5.4)
    
    返回季后赛状态和玩家球队状态。
    
    Returns:
        {
            "success": true,
            "data": {
                "is_playoff_phase": bool,
                "is_regular_season_over": bool,
                "can_enter_playoffs": bool,
                "current_round": str | null,
                "player_team_status": {
                    "is_in_playoffs": bool,
                    "is_eliminated": bool,
                    "is_champion": bool,
                    "current_series_id": str | null,
                    "series_score": str | null
                }
            }
        }
    """
    error = check_game_started()
    if error:
        return error
    
    controller = game_state.game_controller
    season_manager = game_state.season_manager
    player_team_id = game_state.player_team_id
    
    # 基本状态
    is_playoff_phase = controller.is_playoff_phase
    is_regular_season_over = season_manager.is_regular_season_over()
    can_enter_playoffs = is_regular_season_over and not is_playoff_phase
    
    # 当前轮次
    current_round = None
    if is_playoff_phase:
        current_round = season_manager.get_playoff_round_name()
    
    # 玩家球队状态
    player_team_status = {
        "is_in_playoffs": False,
        "is_eliminated": False,
        "is_champion": False,
        "current_series_id": None,
        "series_score": None
    }
    
    if player_team_id:
        # 检查是否在季后赛中
        player_team_status["is_in_playoffs"] = season_manager.is_team_in_playoffs(player_team_id)
        
        # 检查是否被淘汰
        player_team_status["is_eliminated"] = controller.player_eliminated
        
        # 检查是否是冠军
        champion = season_manager.get_champion()
        player_team_status["is_champion"] = (champion == player_team_id)
        
        # 获取当前系列赛
        if is_playoff_phase and not controller.player_eliminated:
            player_series = season_manager.get_player_team_series(player_team_id)
            if player_series:
                series_id, series = player_series
                player_team_status["current_series_id"] = series_id
                player_team_status["series_score"] = f"{series.team1_wins}-{series.team2_wins}"
    
    return success_response(data={
        "is_playoff_phase": is_playoff_phase,
        "is_regular_season_over": is_regular_season_over,
        "can_enter_playoffs": can_enter_playoffs,
        "current_round": current_round,
        "player_team_status": player_team_status
    })


@app.route('/api/playoff/round-games/<round_name>', methods=['GET'])
def get_playoff_round_games(round_name: str):
    """
    获取季后赛指定轮次的所有比赛及球员统计数据
    
    类似于常规赛的每日比赛查看，但以轮次为单位。
    
    Args:
        round_name: 轮次名称 (play_in/quarter/semi/final)
        
    Returns:
        {
            "success": true,
            "data": {
                "round_name": str,
                "round_display_name": str,
                "total_series": int,
                "series_list": [
                    {
                        "series_id": str,
                        "team1_id": str,
                        "team1_name": str,
                        "team2_id": str,
                        "team2_name": str,
                        "team1_wins": int,
                        "team2_wins": int,
                        "is_complete": bool,
                        "winner_id": str | null,
                        "winner_name": str | null,
                        "games": [
                            {
                                "game_number": int,
                                "home_team_id": str,
                                "home_team_name": str,
                                "away_team_id": str,
                                "away_team_name": str,
                                "home_score": int,
                                "away_score": int,
                                "player_stats": {
                                    "home_team": [...],
                                    "away_team": [...]
                                }
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        }
    """
    error = check_game_started()
    if error:
        return error
    
    # 验证轮次名称
    valid_rounds = ['play_in', 'quarter', 'semi', 'final']
    if round_name not in valid_rounds:
        return error_response("INVALID_ROUND", f"无效的轮次名称: {round_name}，有效值为: {', '.join(valid_rounds)}")
    
    # 轮次显示名称映射
    round_display_names = {
        'play_in': '附加赛 (12进8)',
        'quarter': '四分之一决赛',
        'semi': '半决赛',
        'final': '总决赛'
    }
    
    season_manager = game_state.season_manager
    bracket = season_manager.get_playoff_bracket()
    
    series_list = []
    
    # 根据轮次获取对应的系列赛
    if round_name == 'play_in':
        series_ids = [f'play_in_{i}' for i in range(1, 5)]
    elif round_name == 'quarter':
        series_ids = [f'quarter_{i}' for i in range(1, 5)]
    elif round_name == 'semi':
        series_ids = [f'semi_{i}' for i in range(1, 3)]
    else:  # final
        series_ids = ['final']
    
    for series_id in series_ids:
        if series_id not in bracket:
            continue
        
        series = bracket[series_id]
        if not hasattr(series, 'team1_id'):
            continue
        
        # 获取球队信息
        team1 = game_state.teams.get(series.team1_id)
        team2 = game_state.teams.get(series.team2_id)
        
        team1_name = team1.name if team1 else "未知球队"
        team2_name = team2.name if team2 else "未知球队"
        
        winner_name = None
        if series.winner_id:
            winner_team = game_state.teams.get(series.winner_id)
            winner_name = winner_team.name if winner_team else None
        
        # 获取系列赛中的所有比赛
        games_data = []
        if hasattr(series, 'games') and series.games:
            for i, game_result in enumerate(series.games):
                home_team = game_state.teams.get(game_result.home_team_id)
                away_team = game_state.teams.get(game_result.away_team_id)
                
                # 格式化球员统计
                formatted_stats = _format_player_stats_for_response(
                    game_result.player_stats,
                    game_result.home_team_id,
                    game_result.away_team_id
                )
                
                games_data.append({
                    "game_number": i + 1,
                    "home_team_id": game_result.home_team_id,
                    "home_team_name": home_team.name if home_team else "",
                    "away_team_id": game_result.away_team_id,
                    "away_team_name": away_team.name if away_team else "",
                    "home_score": game_result.home_score,
                    "away_score": game_result.away_score,
                    "player_stats": formatted_stats,
                    "quarter_scores": game_result.quarter_scores,
                    "highlights": game_result.highlights
                })
        
        series_list.append({
            "series_id": series_id,
            "team1_id": series.team1_id,
            "team1_name": team1_name,
            "team2_id": series.team2_id,
            "team2_name": team2_name,
            "team1_wins": series.team1_wins,
            "team2_wins": series.team2_wins,
            "is_complete": series.is_complete,
            "winner_id": series.winner_id,
            "winner_name": winner_name,
            "games": games_data
        })
    
    return success_response(data={
        "round_name": round_name,
        "round_display_name": round_display_names.get(round_name, round_name),
        "total_series": len(series_list),
        "series_list": series_list
    })


@app.route('/api/playoff/advance', methods=['POST'])
def advance_playoffs():
    """
    推进季后赛 - 模拟所有AI系列赛的一场比赛
    
    此API会模拟所有不涉及玩家球队的系列赛各一场比赛。
    如果玩家已淘汰，也会模拟玩家原来所在系列赛的比赛。
    
    Returns:
        {
            "success": true,
            "data": {
                "simulated_games": [...],  # 模拟的比赛列表
                "series_updates": [...],   # 系列赛更新
                "round_advanced": bool,    # 是否进入下一轮
                "current_round": str,      # 当前轮次
                "playoffs_complete": bool  # 季后赛是否结束
            }
        }
    """
    error = check_game_started()
    if error:
        return error
    
    controller = game_state.game_controller
    season_manager = game_state.season_manager
    player_team_id = game_state.player_team_id
    
    if not controller.is_playoff_phase:
        return error_response("NOT_IN_PLAYOFFS", "尚未进入季后赛阶段")
    
    try:
        simulated_games = []
        series_updates = []
        
        # 获取所有进行中的系列赛
        # 使用 list() 创建副本，避免在遍历过程中修改字典导致 "dictionary changed size during iteration" 错误
        bracket = season_manager.get_playoff_bracket()
        series_items = list(bracket.items())
        
        for series_id, series in series_items:
            # 跳过非系列赛对象（如种子列表）
            if not hasattr(series, 'is_complete'):
                continue
            
            # 跳过已完成的系列赛
            if series.is_complete:
                continue
            
            # 检查是否涉及玩家球队
            involves_player = (series.team1_id == player_team_id or 
                             series.team2_id == player_team_id)
            
            # 如果涉及玩家球队且玩家未淘汰，跳过（让玩家自己打）
            if involves_player and not controller.player_eliminated:
                continue
            
            # 模拟这场比赛
            try:
                result, series_update = controller.simulate_playoff_game(
                    series_id=series_id,
                    use_llm=True
                )
                
                if result:
                    home_team = game_state.teams.get(result.home_team_id)
                    away_team = game_state.teams.get(result.away_team_id)
                    
                    # 格式化球员统计数据（与常规赛一致）
                    formatted_player_stats = _format_player_stats_for_response(
                        result.player_stats,
                        result.home_team_id,
                        result.away_team_id
                    )
                    
                    simulated_games.append({
                        "series_id": series_id,
                        "home_team_id": result.home_team_id,
                        "home_team_name": home_team.name if home_team else "",
                        "away_team_id": result.away_team_id,
                        "away_team_name": away_team.name if away_team else "",
                        "home_score": result.home_score,
                        "away_score": result.away_score,
                        "player_stats": formatted_player_stats
                    })
                    
                    series_updates.append(series_update)
                    
            except Exception as e:
                print(f"Error simulating series {series_id}: {e}")
                continue
        
        # 重置玩家的"本轮已打"标志，允许玩家打下一场
        # 无论是否有AI比赛被模拟，都应该重置标志
        # 这样当所有AI系列赛都已结束时（如总决赛），玩家仍可继续比赛
        controller.player_playoff_game_played_this_round = False
        
        # 季后赛推进时，所有伤病球员恢复2天
        all_players = list(game_state.players.values())
        controller.injury_system.recover_players(all_players, days_passed=2)
        
        # 检查季后赛是否结束
        playoffs_complete = season_manager.is_playoffs_over()
        current_round = season_manager.get_playoff_round_name()
        
        # 检查是否有新的轮次
        round_advanced = any(u.get("next_round_created", False) for u in series_updates)
        
        return success_response(
            data={
                "simulated_games": simulated_games,
                "series_updates": series_updates,
                "round_advanced": round_advanced,
                "current_round": current_round,
                "playoffs_complete": playoffs_complete
            },
            message=f"模拟了 {len(simulated_games)} 场季后赛比赛"
        )
        
    except Exception as e:
        return error_response("ADVANCE_FAILED", f"推进季后赛失败: {str(e)}")


# ============== 外援市场API ==============

@app.route('/api/foreign-market/info', methods=['GET'])
def get_foreign_market_info():
    """
    获取外援市场信息
    
    Returns:
        - budget: 当前经费（万元）
        - scout_cost: 普通球探搜索费用（万元）
        - targeted_scout_cost: 定向搜索费用（万元）
        - max_salary: 工资上限（万元）
        - positions: 可选位置列表
        - can_scout: 是否可以进行普通球探搜索
        - can_targeted_scout: 是否可以进行定向搜索
        - scouted_players: 当前搜索到的所有外援列表（隐藏部分能力值）
        - scouted_player: 当前搜索到的第一个外援（向后兼容）
        - foreign_count: 当前外援数量
        - max_foreign: 最大外援数量
        - foreign_players: 当前外援列表（用于替换选择）
        - needs_replacement: 签约时是否需要替换现有外援
        - sponsor_status: 赞助系统状态
        - is_playoff_phase: 是否在季后赛阶段（季后赛阶段外援市场禁用）
    """
    error = check_game_started()
    if error:
        return error
    
    player_team = game_state.teams.get(game_state.player_team_id)
    if not player_team:
        return error_response("TEAM_NOT_FOUND", "找不到玩家球队")
    
    foreign_market = game_state.foreign_market
    current_date = game_state.game_controller.current_date
    is_playoff_phase = game_state.game_controller.is_playoff_phase
    
    # 季后赛阶段返回禁用状态
    if is_playoff_phase:
        from src.foreign_market import MAX_FOREIGN_PLAYERS, SCOUT_RESULT_EXPIRY_DAYS
        
        # 获取当前未被裁的外援数量和列表
        foreign_players = foreign_market.get_active_foreign_players(player_team)
        foreign_count = len(foreign_players)
        foreign_players_data = [{
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "age": p.age,
            "overall": p.overall
        } for p in foreign_players]
        
        return success_response(data={
            "budget": player_team.budget,
            "scout_cost": SCOUT_COST,
            "targeted_scout_cost": TARGETED_SCOUT_COST,
            "max_salary": MAX_SALARY,
            "positions": POSITIONS,
            "can_scout": False,
            "scout_reason": "季后赛阶段无法使用外援市场",
            "can_targeted_scout": False,
            "targeted_scout_reason": "季后赛阶段无法使用外援市场",
            "scouted_players": [],
            "scouted_player": None,
            "foreign_count": foreign_count,
            "max_foreign": MAX_FOREIGN_PLAYERS,
            "foreign_players": foreign_players_data,
            "needs_replacement": False,
            "sponsor_status": {
                "can_sponsor": False,
                "reason": "季后赛阶段无法拉赞助"
            },
            "scout_result_expiry_days": SCOUT_RESULT_EXPIRY_DAYS,
            "is_playoff_phase": True
        })
    
    # 先检查并清理过期的外援
    expired_names = foreign_market.check_and_expire_scouted_players(current_date)
    
    # 检查是否可以搜索
    can_scout, scout_reason = foreign_market.can_scout(player_team, targeted=False)
    can_targeted_scout, targeted_scout_reason = foreign_market.can_scout(player_team, targeted=True)
    
    # 获取当前未被裁的外援数量和列表
    foreign_players = foreign_market.get_active_foreign_players(player_team)
    foreign_count = len(foreign_players)
    
    # 检查签约时是否需要替换
    can_sign, sign_reason, needs_replacement = foreign_market.can_sign_foreign_player(player_team)
    
    # 获取所有搜索到的外援（隐藏部分能力值）
    scouted_players_data = foreign_market.get_all_scouted_players_display_info(current_date)
    
    # 向后兼容：获取第一个外援
    scouted_player_data = scouted_players_data[0] if scouted_players_data else None
    
    # 获取赞助系统状态
    sponsor_status = foreign_market.get_sponsor_status(current_date)
    
    # 格式化外援列表（只显示未被裁的）
    foreign_players_data = [{
        "id": p.id,
        "name": p.name,
        "position": p.position,
        "age": p.age,
        "overall": p.overall
    } for p in foreign_players]
    
    from src.foreign_market import MAX_FOREIGN_PLAYERS, SCOUT_RESULT_EXPIRY_DAYS
    
    response_data = {
        "budget": player_team.budget,
        "scout_cost": SCOUT_COST,
        "targeted_scout_cost": TARGETED_SCOUT_COST,
        "max_salary": MAX_SALARY,
        "positions": POSITIONS,
        "can_scout": can_scout,
        "scout_reason": scout_reason,
        "can_targeted_scout": can_targeted_scout,
        "targeted_scout_reason": targeted_scout_reason,
        "scouted_players": scouted_players_data,
        "scouted_player": scouted_player_data,
        "foreign_count": foreign_count,
        "max_foreign": MAX_FOREIGN_PLAYERS,
        "foreign_players": foreign_players_data,
        "needs_replacement": needs_replacement,
        "sponsor_status": sponsor_status,
        "scout_result_expiry_days": SCOUT_RESULT_EXPIRY_DAYS,
        "is_playoff_phase": False
    }
    
    # 如果有过期的外援，添加到响应中
    if expired_names:
        response_data["expired_players"] = expired_names
    
    return success_response(data=response_data)


@app.route('/api/foreign-market/scout', methods=['POST'])
def scout_foreign_player():
    """
    进行球探搜索，生成一名外援
    
    Request Body:
        use_llm: 是否使用LLM生成（可选，默认True）
        targeted: 是否为定向搜索（可选，默认False）
        target_position: 定向搜索的目标位置（targeted=True时必填）
        
    Returns:
        - success: 是否成功
        - scouted_player: 搜索到的外援信息（隐藏部分能力值）
        - scouted_players: 所有搜索到的外援列表
        - current_budget: 搜索后的经费
        
    注意: 季后赛阶段无法使用外援市场
    """
    error = check_game_started()
    if error:
        return error
    
    # 检查是否在季后赛阶段
    if game_state.game_controller.is_playoff_phase:
        return error_response("PLAYOFF_RESTRICTION", "季后赛阶段无法使用外援市场")
    
    player_team = game_state.teams.get(game_state.player_team_id)
    if not player_team:
        return error_response("TEAM_NOT_FOUND", "找不到玩家球队")
    
    data = request.get_json() or {}
    use_llm = data.get('use_llm', True)
    targeted = data.get('targeted', False)
    target_position = data.get('target_position', None)
    
    # 定向搜索必须指定位置
    if targeted and not target_position:
        return error_response("INVALID_PARAMS", "定向搜索必须指定目标位置")
    
    foreign_market = game_state.foreign_market
    current_date = game_state.game_controller.current_date
    
    # 进行球探搜索（传入当前日期）
    success, message, result = foreign_market.scout_foreign_player(
        player_team, use_llm, targeted, target_position, current_date
    )
    
    if not success:
        return error_response("SCOUT_FAILED", message)
    
    # 获取新搜索到的外援的显示信息
    scouted_player_data = foreign_market.get_scouted_player_display_info(result.player.id, current_date)
    
    # 获取所有搜索到的外援列表
    scouted_players_data = foreign_market.get_all_scouted_players_display_info(current_date)
    
    return success_response(
        data={
            "scouted_player": scouted_player_data,
            "scouted_players": scouted_players_data,
            "current_budget": player_team.budget
        },
        message=message
    )


@app.route('/api/foreign-market/sign', methods=['POST'])
def sign_scouted_player():
    """
    签约搜索到的外援
    
    Request Body:
        replace_player_id: 要替换的外援ID（当外援已满时必须提供）
        scouted_player_id: 要签约的搜索结果外援ID（可选，默认签约第一个）
    
    Returns:
        - success: 是否成功
        - message: 结果消息
        - current_budget: 签约后的经费
        - player_full_info: 签约后显示的完整球员信息（包含所有能力值）
        - needs_replacement: 是否需要替换外援
        - foreign_players: 当前外援列表（需要替换时返回）
        - scouted_players: 剩余的搜索结果列表
        
    注意: 季后赛阶段无法使用外援市场
    """
    error = check_game_started()
    if error:
        return error
    
    # 检查是否在季后赛阶段
    if game_state.game_controller.is_playoff_phase:
        return error_response("PLAYOFF_RESTRICTION", "季后赛阶段无法使用外援市场")
    
    player_team = game_state.teams.get(game_state.player_team_id)
    if not player_team:
        return error_response("TEAM_NOT_FOUND", "找不到玩家球队")
    
    foreign_market = game_state.foreign_market
    current_date = game_state.game_controller.current_date
    
    # 获取请求参数
    data = request.get_json() or {}
    replace_player_id = data.get('replace_player_id', None)
    scouted_player_id = data.get('scouted_player_id', None)
    
    # 获取签约前的完整信息（用于签约后展示）
    full_info = foreign_market.get_full_player_info(scouted_player_id)
    
    # 签约外援
    success, message, foreign_list = foreign_market.sign_scouted_player(
        player_team, replace_player_id, scouted_player_id
    )
    
    if success:
        # 获取剩余的搜索结果列表
        scouted_players_data = foreign_market.get_all_scouted_players_display_info(current_date)
        
        return success_response(
            message=message,
            data={
                "current_budget": player_team.budget,
                "player_full_info": full_info,
                "scouted_players": scouted_players_data
            }
        )
    else:
        # 如果返回了外援列表，说明需要替换
        if foreign_list is not None:
            return jsonify({
                "success": False,
                "error": {
                    "code": "NEEDS_REPLACEMENT",
                    "message": message
                },
                "data": {
                    "needs_replacement": True,
                    "foreign_players": foreign_list
                }
            })
        return error_response("SIGN_FAILED", message)


@app.route('/api/foreign-market/dismiss', methods=['POST'])
def dismiss_scouted_player():
    """
    放弃搜索到的外援
    
    Request Body:
        player_id: 要放弃的外援ID（可选，默认放弃第一个）
    
    Returns:
        - success: 是否成功
        - message: 结果消息
        - scouted_players: 剩余的搜索结果列表
    """
    error = check_game_started()
    if error:
        return error
    
    foreign_market = game_state.foreign_market
    current_date = game_state.game_controller.current_date
    
    # 获取请求参数
    data = request.get_json() or {}
    player_id = data.get('player_id', None)
    
    success, message = foreign_market.dismiss_scouted_player(player_id)
    
    if not success:
        return error_response("DISMISS_FAILED", message)
    
    # 获取剩余的搜索结果列表
    scouted_players_data = foreign_market.get_all_scouted_players_display_info(current_date)
    
    return success_response(
        message=message,
        data={
            "scouted_players": scouted_players_data
        }
    )


@app.route('/api/foreign-market/sponsor', methods=['POST'])
def get_sponsor():
    """
    拉赞助获取经费
    
    每5天可以拉一次赞助，获得10-100万元不等的赞助经费。
    其中50万及以上概率低，80万以上概率极低。
    
    Returns:
        - success: 是否成功
        - message: 结果消息
        - amount: 获得的赞助金额（万元）
        - current_budget: 赞助后的经费
        - sponsor_status: 更新后的赞助状态
        
    注意: 季后赛阶段无法拉赞助
    """
    error = check_game_started()
    if error:
        return error
    
    # 检查是否在季后赛阶段
    if game_state.game_controller.is_playoff_phase:
        return error_response("PLAYOFF_RESTRICTION", "季后赛阶段无法拉赞助")
    
    player_team = game_state.teams.get(game_state.player_team_id)
    if not player_team:
        return error_response("TEAM_NOT_FOUND", "找不到玩家球队")
    
    foreign_market = game_state.foreign_market
    current_date = game_state.game_controller.current_date
    
    # 拉赞助
    success, message, amount = foreign_market.get_sponsor(player_team, current_date)
    
    if success:
        # 获取更新后的赞助状态
        sponsor_status = foreign_market.get_sponsor_status(current_date)
        
        return success_response(
            message=message,
            data={
                "amount": amount,
                "current_budget": player_team.budget,
                "sponsor_status": sponsor_status
            }
        )
    else:
        return error_response("SPONSOR_FAILED", message)


@app.route('/api/foreign-market/sponsor-status', methods=['GET'])
def get_sponsor_status():
    """
    获取赞助系统状态
    
    Returns:
        - can_sponsor: 是否可以拉赞助
        - reason: 原因
        - cooldown_remaining: 剩余冷却天数
        - cooldown_days: 冷却周期（天）
        - min_amount: 最小赞助金额
        - max_amount: 最大赞助金额
        - last_sponsor_date: 上次拉赞助日期
    """
    error = check_game_started()
    if error:
        return error
    
    foreign_market = game_state.foreign_market
    current_date = game_state.game_controller.current_date
    
    sponsor_status = foreign_market.get_sponsor_status(current_date)
    
    return success_response(data=sponsor_status)


# ============== 主页路由 ==============

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


# ============== 应用启动 ==============

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
