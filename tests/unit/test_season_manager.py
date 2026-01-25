"""
SeasonManager 单元测试
"""
import pytest
from src.models import Team, Standing
from src.season_manager import SeasonManager, REGULAR_SEASON_GAMES


@pytest.fixture
def sample_teams():
    """创建测试用球队列表"""
    teams = []
    for i in range(20):
        team = Team(
            id=f"team_{i:02d}",
            name=f"球队{i+1}",
            city=f"城市{i+1}",
            status="stable",
            is_player_controlled=(i == 0),
            roster=[]
        )
        teams.append(team)
    return teams


@pytest.fixture
def season_manager(sample_teams):
    """创建SeasonManager实例"""
    return SeasonManager(sample_teams)


class TestSeasonManagerInit:
    """测试SeasonManager初始化"""
    
    def test_init_with_teams(self, sample_teams):
        """测试使用球队列表初始化"""
        manager = SeasonManager(sample_teams)
        assert len(manager.teams) == 20
        assert len(manager.standings) == 20
    
    def test_init_standings(self, season_manager):
        """测试排行榜初始化"""
        for team_id, standing in season_manager.standings.items():
            assert standing.wins == 0
            assert standing.losses == 0
            assert standing.win_pct == 0.0
            assert standing.games_behind == 0.0


class TestGenerateSchedule:
    """测试赛程生成"""
    
    def test_generate_schedule_creates_games(self, season_manager):
        """测试生成赛程"""
        schedule = season_manager.generate_schedule()
        assert len(schedule) > 0
    
    def test_each_team_has_42_games(self, season_manager):
        """测试每队有足够的比赛场次（38-42场）"""
        season_manager.generate_schedule()
        
        for team_id in season_manager.team_ids:
            games_count = season_manager.get_team_games_count(team_id)
            # 每队至少38场（19主场+19客场），最多42场
            assert games_count >= 38, \
                f"Team {team_id} has {games_count} games, expected at least 38"
            assert games_count <= REGULAR_SEASON_GAMES, \
                f"Team {team_id} has {games_count} games, expected at most {REGULAR_SEASON_GAMES}"
    
    def test_schedule_has_dates(self, season_manager):
        """测试赛程有日期"""
        season_manager.generate_schedule()
        
        for game in season_manager.schedule:
            assert game.date is not None
            assert len(game.date) == 10  # YYYY-MM-DD format
    
    def test_games_not_played_initially(self, season_manager):
        """测试比赛初始状态为未进行"""
        season_manager.generate_schedule()
        
        for game in season_manager.schedule:
            assert game.is_played is False


class TestGetGamesForDate:
    """测试获取指定日期比赛"""
    
    def test_get_games_for_existing_date(self, season_manager):
        """测试获取存在比赛的日期"""
        season_manager.generate_schedule()
        
        # 获取第一个比赛日
        first_date = season_manager.schedule[0].date
        games = season_manager.get_games_for_date(first_date)
        
        assert len(games) > 0
        for game in games:
            assert game.date == first_date
    
    def test_get_games_for_nonexistent_date(self, season_manager):
        """测试获取不存在比赛的日期"""
        season_manager.generate_schedule()
        
        games = season_manager.get_games_for_date("1900-01-01")
        assert len(games) == 0


class TestUpdateStandings:
    """测试排行榜更新"""
    
    def test_update_standings_home_win(self, season_manager):
        """测试主队获胜更新排行榜"""
        team1 = season_manager.team_ids[0]
        team2 = season_manager.team_ids[1]
        
        season_manager.update_standings(team1, team2, 100, 90)
        
        assert season_manager.standings[team1].wins == 1
        assert season_manager.standings[team1].losses == 0
        assert season_manager.standings[team2].wins == 0
        assert season_manager.standings[team2].losses == 1
    
    def test_update_standings_away_win(self, season_manager):
        """测试客队获胜更新排行榜"""
        team1 = season_manager.team_ids[0]
        team2 = season_manager.team_ids[1]
        
        season_manager.update_standings(team1, team2, 90, 100)
        
        assert season_manager.standings[team1].wins == 0
        assert season_manager.standings[team1].losses == 1
        assert season_manager.standings[team2].wins == 1
        assert season_manager.standings[team2].losses == 0
    
    def test_update_standings_win_pct(self, season_manager):
        """测试胜率计算"""
        team1 = season_manager.team_ids[0]
        team2 = season_manager.team_ids[1]
        
        # 第一场：team1胜
        season_manager.update_standings(team1, team2, 100, 90)
        # 第二场：team2胜
        season_manager.update_standings(team2, team1, 100, 90)
        
        assert season_manager.standings[team1].win_pct == 0.5
        assert season_manager.standings[team2].win_pct == 0.5
    
    def test_update_standings_games_behind(self, season_manager):
        """测试落后场次计算"""
        team1 = season_manager.team_ids[0]
        team2 = season_manager.team_ids[1]
        team3 = season_manager.team_ids[2]
        
        # team1: 2胜0负
        season_manager.update_standings(team1, team2, 100, 90)
        season_manager.update_standings(team1, team3, 100, 90)
        
        standings = season_manager.get_standings()
        leader = standings[0]
        
        assert leader.team_id == team1
        assert leader.games_behind == 0.0
        
        # team2和team3各落后1.5场
        # 落后场次 = (领先者胜场 - 本队胜场 + 本队负场 - 领先者负场) / 2
        # team2: (2 - 0 + 1 - 0) / 2 = 1.5
        team2_standing = season_manager.standings[team2]
        team3_standing = season_manager.standings[team3]
        assert team2_standing.games_behind == 1.5
        assert team3_standing.games_behind == 1.5


class TestGetStandings:
    """测试获取排行榜"""
    
    def test_get_standings_sorted_by_win_pct(self, season_manager):
        """测试排行榜按胜率排序"""
        team1 = season_manager.team_ids[0]
        team2 = season_manager.team_ids[1]
        team3 = season_manager.team_ids[2]
        
        # team1: 2胜0负 (100%)
        season_manager.update_standings(team1, team2, 100, 90)
        season_manager.update_standings(team1, team3, 100, 90)
        
        # team2: 1胜1负 (50%)
        season_manager.update_standings(team2, team3, 100, 90)
        
        standings = season_manager.get_standings()
        
        # 验证排序
        assert standings[0].team_id == team1
        assert standings[0].win_pct == 1.0
        assert standings[1].team_id == team2
        assert standings[1].win_pct == 0.5
    
    def test_get_team_rank(self, season_manager):
        """测试获取球队排名"""
        team1 = season_manager.team_ids[0]
        team2 = season_manager.team_ids[1]
        
        season_manager.update_standings(team1, team2, 100, 90)
        
        assert season_manager.get_team_rank(team1) == 1
        # team2排名应该在后面
        assert season_manager.get_team_rank(team2) > 1


class TestSeasonProgress:
    """测试赛季进度"""
    
    def test_is_regular_season_over_false(self, season_manager):
        """测试常规赛未结束"""
        season_manager.generate_schedule()
        assert season_manager.is_regular_season_over() is False
    
    def test_is_match_day(self, season_manager):
        """测试比赛日判断"""
        season_manager.generate_schedule()
        
        first_date = season_manager.schedule[0].date
        assert season_manager.is_match_day(first_date) is True
        assert season_manager.is_match_day("1900-01-01") is False
    
    def test_get_season_progress(self, season_manager):
        """测试获取赛季进度"""
        season_manager.generate_schedule()
        
        played, total = season_manager.get_season_progress()
        assert played == 0
        assert total > 0


class TestPlayoffAIAdjustment:
    """测试季后赛AI能力值调整"""
    
    def test_adjust_ai_players_only_affects_ai_teams(self, season_manager):
        """测试只调整AI球队球员"""
        from src.models import Player
        from src.player_data_manager import calculate_overall
        
        # 创建测试球员
        players = {}
        teams = {}
        
        # 玩家控制的球队
        player_team = Team(
            id="player_team",
            name="玩家球队",
            city="城市A",
            status="stable",
            is_player_controlled=True,
            roster=["player_1"]
        )
        teams["player_team"] = player_team
        
        # AI控制的球队
        ai_team = Team(
            id="ai_team",
            name="AI球队",
            city="城市B",
            status="stable",
            is_player_controlled=False,
            roster=["player_2"]
        )
        teams["ai_team"] = ai_team
        
        # 玩家球队的球员
        player_1 = Player(
            id="player_1",
            name="球员1",
            team_id="player_team",
            position="PG",
            age=25,
            offense=80,
            defense=75,
            three_point=78,
            rebounding=50,
            passing=82,
            stamina=80
        )
        player_1.overall = calculate_overall(player_1)
        players["player_1"] = player_1
        
        # AI球队的球员
        player_2 = Player(
            id="player_2",
            name="球员2",
            team_id="ai_team",
            position="SG",
            age=26,
            offense=75,
            defense=70,
            three_point=80,
            rebounding=45,
            passing=70,
            stamina=75
        )
        player_2.overall = calculate_overall(player_2)
        players["player_2"] = player_2
        
        # 记录原始值
        original_player_1_offense = player_1.offense
        original_player_1_defense = player_1.defense
        
        # 执行调整
        adjustments = season_manager.adjust_ai_players_for_playoffs(
            players, teams, calculate_overall
        )
        
        # 玩家球队的球员不应该被调整
        assert player_1.offense == original_player_1_offense
        assert player_1.defense == original_player_1_defense
        assert "player_1" not in adjustments
    
    def test_adjust_ai_players_within_range(self, season_manager):
        """测试调整范围在-2到+2之间"""
        from src.models import Player
        from src.player_data_manager import calculate_overall
        import random
        
        # 设置随机种子以确保可重复性
        random.seed(42)
        
        players = {}
        teams = {}
        
        # 创建多个AI球队和球员
        for i in range(5):
            team = Team(
                id=f"ai_team_{i}",
                name=f"AI球队{i}",
                city=f"城市{i}",
                status="stable",
                is_player_controlled=False,
                roster=[f"player_{i}"]
            )
            teams[f"ai_team_{i}"] = team
            
            player = Player(
                id=f"player_{i}",
                name=f"球员{i}",
                team_id=f"ai_team_{i}",
                position="SF",
                age=25,
                offense=70,
                defense=70,
                three_point=70,
                rebounding=70,
                passing=70,
                stamina=70
            )
            player.overall = calculate_overall(player)
            players[f"player_{i}"] = player
        
        # 执行调整
        adjustments = season_manager.adjust_ai_players_for_playoffs(
            players, teams, calculate_overall
        )
        
        # 验证所有调整值在-2到+2范围内
        for player_id, adjustment in adjustments.items():
            assert -2 <= adjustment <= 2, f"Adjustment {adjustment} out of range for {player_id}"
    
    def test_adjust_ai_players_attributes_capped(self, season_manager):
        """测试属性值不超过0-99范围"""
        from src.models import Player
        from src.player_data_manager import calculate_overall
        import random
        
        # 设置随机种子
        random.seed(123)
        
        players = {}
        teams = {}
        
        # AI球队
        team = Team(
            id="ai_team",
            name="AI球队",
            city="城市",
            status="stable",
            is_player_controlled=False,
            roster=["player_high", "player_low"]
        )
        teams["ai_team"] = team
        
        # 高属性球员（接近99）
        player_high = Player(
            id="player_high",
            name="高属性球员",
            team_id="ai_team",
            position="C",
            age=28,
            offense=98,
            defense=99,
            three_point=97,
            rebounding=99,
            passing=98,
            stamina=99
        )
        player_high.overall = calculate_overall(player_high)
        players["player_high"] = player_high
        
        # 低属性球员（接近0）
        player_low = Player(
            id="player_low",
            name="低属性球员",
            team_id="ai_team",
            position="PG",
            age=20,
            offense=1,
            defense=0,
            three_point=2,
            rebounding=1,
            passing=0,
            stamina=1
        )
        player_low.overall = calculate_overall(player_low)
        players["player_low"] = player_low
        
        # 执行调整
        season_manager.adjust_ai_players_for_playoffs(
            players, teams, calculate_overall
        )
        
        # 验证属性值在0-99范围内
        for player in players.values():
            assert 0 <= player.offense <= 99
            assert 0 <= player.defense <= 99
            assert 0 <= player.three_point <= 99
            assert 0 <= player.rebounding <= 99
            assert 0 <= player.passing <= 99
            assert 0 <= player.stamina <= 99
            assert 0 <= player.overall <= 99
