"""
API集成测试 - 华夏篮球联赛教练模拟器Web后端

测试主要API端点和错误处理
Requirements: 6.11
"""
import pytest
import json
from flask import Flask

# 导入Flask应用
from src.web.app import app, game_state


@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # 重置游戏状态
        game_state.is_game_started = False
        game_state.teams = {}
        game_state.players = {}
        game_state.player_team_id = None
        game_state.initialize_managers()
        yield client


@pytest.fixture
def started_game_client(client):
    """创建已开始游戏的测试客户端"""
    # 获取球队列表
    response = client.get('/api/teams')
    data = json.loads(response.data)
    teams = data['data']
    
    # 选择第一支球队开始游戏
    team_id = teams[0]['id']
    client.post('/api/game/new', 
                data=json.dumps({'team_id': team_id}),
                content_type='application/json')
    
    return client


class TestGameStateAPI:
    """游戏状态管理API测试"""
    
    def test_get_teams_without_game(self, client):
        """测试未开始游戏时获取球队列表"""
        response = client.get('/api/teams')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'data' in data
        assert len(data['data']) == 20  # 20支球队
    
    def test_new_game_success(self, client):
        """测试创建新游戏成功"""
        # 先获取球队列表
        response = client.get('/api/teams')
        teams = json.loads(response.data)['data']
        team_id = teams[0]['id']
        
        # 创建新游戏
        response = client.post('/api/game/new',
                              data=json.dumps({'team_id': team_id}),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['team_id'] == team_id
    
    def test_new_game_invalid_team(self, client):
        """测试创建新游戏时使用无效球队ID"""
        response = client.post('/api/game/new',
                              data=json.dumps({'team_id': 'invalid_team_id'}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'INVALID_TEAM_ID'
    
    def test_new_game_no_team(self, client):
        """测试创建新游戏时未提供球队ID"""
        response = client.post('/api/game/new',
                              data=json.dumps({}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'INVALID_TEAM_ID'
    
    def test_get_game_state_not_started(self, client):
        """测试未开始游戏时获取游戏状态"""
        response = client.get('/api/game/state')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_get_game_state_started(self, started_game_client):
        """测试已开始游戏时获取游戏状态"""
        response = started_game_client.get('/api/game/state')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'current_date' in data['data']
        assert 'player_team' in data['data']
        assert 'available_actions' in data['data']


class TestTeamAndPlayerAPI:
    """球队和球员API测试"""
    
    def test_get_roster_not_started(self, client):
        """测试未开始游戏时获取阵容"""
        response = client.get('/api/team/some_team/roster')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_get_roster_success(self, started_game_client):
        """测试获取球队阵容成功"""
        # 获取玩家球队ID
        state_response = started_game_client.get('/api/game/state')
        team_id = json.loads(state_response.data)['data']['player_team']['id']
        
        response = started_game_client.get(f'/api/team/{team_id}/roster')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'roster' in data['data']
        assert len(data['data']['roster']) > 0
    
    def test_get_roster_invalid_team(self, started_game_client):
        """测试获取无效球队阵容"""
        response = started_game_client.get('/api/team/invalid_team/roster')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_TEAM_ID'
    
    def test_get_player_not_started(self, client):
        """测试未开始游戏时获取球员详情"""
        response = client.get('/api/player/some_player')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_get_player_success(self, started_game_client):
        """测试获取球员详情成功"""
        # 先获取阵容中的球员ID
        state_response = started_game_client.get('/api/game/state')
        team_id = json.loads(state_response.data)['data']['player_team']['id']
        
        roster_response = started_game_client.get(f'/api/team/{team_id}/roster')
        roster = json.loads(roster_response.data)['data']['roster']
        player_id = roster[0]['id']
        
        response = started_game_client.get(f'/api/player/{player_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        # 验证球员详情包含必要字段
        player_data = data['data']
        assert 'id' in player_data
        assert 'name' in player_data
        assert 'attributes' in player_data
        assert 'season_stats' in player_data
    
    def test_get_player_invalid(self, started_game_client):
        """测试获取无效球员详情"""
        response = started_game_client.get('/api/player/invalid_player_id')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_PLAYER_ID'


class TestLeaderboardAPI:
    """排行榜API测试"""
    
    def test_get_leaderboard_not_started(self, client):
        """测试未开始游戏时获取排行榜"""
        response = client.get('/api/leaderboard/points')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_get_leaderboard_success(self, started_game_client):
        """测试获取排行榜成功"""
        response = started_game_client.get('/api/leaderboard/points')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['stat_type'] == 'points'
        assert 'leaderboard' in data['data']
    
    def test_get_leaderboard_invalid_stat(self, started_game_client):
        """测试获取无效统计类型的排行榜"""
        response = started_game_client.get('/api/leaderboard/invalid_stat')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_STAT_TYPE'
    
    def test_get_all_leaderboards(self, started_game_client):
        """测试获取所有排行榜"""
        response = started_game_client.get('/api/leaderboards')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'leaderboards' in data['data']
        # 应该包含5种统计类型
        assert 'points' in data['data']['leaderboards']
        assert 'rebounds' in data['data']['leaderboards']
        assert 'assists' in data['data']['leaderboards']
        assert 'steals' in data['data']['leaderboards']
        assert 'blocks' in data['data']['leaderboards']


class TestScheduleAPI:
    """赛程API测试"""
    
    def test_get_schedule_not_started(self, client):
        """测试未开始游戏时获取赛程"""
        response = client.get('/api/schedule')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_get_schedule_success(self, started_game_client):
        """测试获取赛程成功"""
        response = started_game_client.get('/api/schedule')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'schedule' in data['data']
        assert data['data']['total'] > 0
    
    def test_get_standings_success(self, started_game_client):
        """测试获取排名成功"""
        response = started_game_client.get('/api/standings')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) == 20  # 20支球队
    
    def test_get_daily_games_invalid_date(self, started_game_client):
        """测试获取无效日期的比赛"""
        response = started_game_client.get('/api/daily-games/invalid-date')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_DATE'
    
    def test_get_daily_games_success(self, started_game_client):
        """测试获取当日比赛成功"""
        # 获取当前日期
        state_response = started_game_client.get('/api/game/state')
        current_date = json.loads(state_response.data)['data']['current_date']
        
        response = started_game_client.get(f'/api/daily-games/{current_date}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True


class TestTrainingAPI:
    """训练API测试"""
    
    def test_get_training_programs(self, client):
        """测试获取训练项目（无需游戏开始）"""
        response = client.get('/api/training/programs')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['data']) > 0
    
    def test_execute_training_not_started(self, client):
        """测试未开始游戏时执行训练"""
        response = client.post('/api/training/execute',
                              data=json.dumps({'program_name': '进攻训练'}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'GAME_NOT_STARTED'


class TestSaveLoadAPI:
    """存档API测试"""
    
    def test_save_game_not_started(self, client):
        """测试未开始游戏时保存"""
        response = client.post('/api/game/save',
                              data=json.dumps({'slot': 1}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_save_game_invalid_slot(self, started_game_client):
        """测试使用无效槽位保存"""
        response = started_game_client.post('/api/game/save',
                                           data=json.dumps({'slot': 99}),
                                           content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_SLOT'
    
    def test_load_game_invalid_slot(self, client):
        """测试使用无效槽位加载"""
        response = client.post('/api/game/load',
                              data=json.dumps({'slot': 0}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error']['code'] == 'INVALID_SLOT'
    
    def test_list_saves(self, client):
        """测试获取存档列表"""
        response = client.get('/api/saves')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'data' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestPlayoffAPI:
    """季后赛API测试 (Requirements 5.1, 5.2, 5.3, 5.4, 5.5)"""
    
    def test_get_playoff_bracket_not_started(self, client):
        """测试未开始游戏时获取季后赛对阵图"""
        response = client.get('/api/playoff/bracket')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_get_playoff_bracket_before_playoffs(self, started_game_client):
        """测试常规赛期间获取季后赛对阵图 (Requirements 5.1)"""
        response = started_game_client.get('/api/playoff/bracket')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        # 常规赛期间，季后赛未开始
        assert data['data']['is_playoff_phase'] == False
        assert data['data']['champion_id'] is None
    
    def test_get_playoff_status_not_started(self, client):
        """测试未开始游戏时获取季后赛状态"""
        response = client.get('/api/playoff/status')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_get_playoff_status_before_playoffs(self, started_game_client):
        """测试常规赛期间获取季后赛状态 (Requirements 5.4)"""
        response = started_game_client.get('/api/playoff/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['is_playoff_phase'] == False
        assert data['data']['is_regular_season_over'] == False
        assert data['data']['can_enter_playoffs'] == False
        assert 'player_team_status' in data['data']
    
    def test_init_playoffs_not_started(self, client):
        """测试未开始游戏时初始化季后赛"""
        response = client.post('/api/playoff/init',
                              data=json.dumps({}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_init_playoffs_before_regular_season_ends(self, started_game_client):
        """测试常规赛未结束时初始化季后赛 (Requirements 5.2)"""
        response = started_game_client.post('/api/playoff/init',
                                           data=json.dumps({}),
                                           content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        # 应该返回错误，因为常规赛未结束
        assert 'error' in data
    
    def test_simulate_playoff_game_not_started(self, client):
        """测试未开始游戏时模拟季后赛比赛"""
        response = client.post('/api/playoff/simulate-game',
                              data=json.dumps({'series_id': 'play_in_1'}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_simulate_playoff_game_no_series_id(self, started_game_client):
        """测试模拟季后赛比赛时未提供系列赛ID (Requirements 5.3)"""
        response = started_game_client.post('/api/playoff/simulate-game',
                                           data=json.dumps({}),
                                           content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'INVALID_SERIES_ID'
    
    def test_game_state_includes_playoff_fields(self, started_game_client):
        """测试游戏状态包含季后赛字段 (Requirements 1.1, 1.2)"""
        response = started_game_client.get('/api/game/state')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        # 验证季后赛相关字段存在
        state_data = data['data']
        assert 'is_playoff_phase' in state_data
        assert 'can_enter_playoffs' in state_data
        assert 'player_team_playoff_status' in state_data
        
        # 验证玩家球队季后赛状态字段
        playoff_status = state_data['player_team_playoff_status']
        assert 'is_in_playoffs' in playoff_status
        assert 'is_eliminated' in playoff_status
        assert 'is_champion' in playoff_status
        assert 'current_series_id' in playoff_status
        assert 'series_score' in playoff_status
    
    def test_playoff_bracket_response_format(self, started_game_client):
        """测试季后赛对阵图响应格式 (Requirements 5.5)"""
        response = started_game_client.get('/api/playoff/bracket')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        bracket_data = data['data']
        # 验证必要字段存在
        assert 'is_playoff_phase' in bracket_data
        assert 'current_round' in bracket_data
        assert 'play_in' in bracket_data
        assert 'quarter_seeds' in bracket_data
        assert 'quarter' in bracket_data
        assert 'semi' in bracket_data
        assert 'final' in bracket_data
        assert 'champion_id' in bracket_data
        assert 'champion_name' in bracket_data
    
    def test_playoff_status_response_format(self, started_game_client):
        """测试季后赛状态响应格式 (Requirements 5.4)"""
        response = started_game_client.get('/api/playoff/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        status_data = data['data']
        # 验证必要字段存在
        assert 'is_playoff_phase' in status_data
        assert 'is_regular_season_over' in status_data
        assert 'can_enter_playoffs' in status_data
        assert 'current_round' in status_data
        assert 'player_team_status' in status_data
        
        # 验证玩家球队状态字段
        player_status = status_data['player_team_status']
        assert 'is_in_playoffs' in player_status
        assert 'is_eliminated' in player_status
        assert 'is_champion' in player_status
        assert 'current_series_id' in player_status
        assert 'series_score' in player_status

    def test_playoff_round_games_not_started(self, client):
        """测试未开始游戏时获取季后赛轮次比赛"""
        response = client.get('/api/playoff/round-games/quarter')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'GAME_NOT_STARTED'
    
    def test_playoff_round_games_invalid_round(self, started_game_client):
        """测试获取无效轮次的季后赛比赛"""
        response = started_game_client.get('/api/playoff/round-games/invalid_round')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert data['error']['code'] == 'INVALID_ROUND'
    
    def test_playoff_round_games_response_format(self, started_game_client):
        """测试季后赛轮次比赛响应格式"""
        response = started_game_client.get('/api/playoff/round-games/quarter')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        
        round_data = data['data']
        # 验证必要字段存在
        assert 'round_name' in round_data
        assert 'round_display_name' in round_data
        assert 'total_series' in round_data
        assert 'series_list' in round_data
        assert round_data['round_name'] == 'quarter'
