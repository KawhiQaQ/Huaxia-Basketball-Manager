"""
DailyStatsViewer 单元测试
"""
import pytest
from src.models import Team, Player, ScheduledGame, MatchResult, GameStats
from src.season_manager import SeasonManager
from src.daily_stats_viewer import DailyStatsViewer


@pytest.fixture
def sample_teams():
    """创建测试用球队列表"""
    teams = {}
    for i in range(4):
        team = Team(
            id=f"team_{i:02d}",
            name=f"球队{i+1}",
            city=f"城市{i+1}",
            status="stable",
            is_player_controlled=(i == 0),  # 只有第一支球队是玩家控制
            roster=[f"player_{i}_1", f"player_{i}_2"]
        )
        teams[team.id] = team
    return teams


@pytest.fixture
def sample_players(sample_teams):
    """创建测试用球员"""
    players = {}
    for team_id, team in sample_teams.items():
        for j, player_id in enumerate(team.roster):
            player = Player(
                id=player_id,
                name=f"球员{team_id}_{j+1}",
                team_id=team_id,
                position="PG" if j == 0 else "SG",
                age=25 + j,
                offense=70 + j * 5,
                defense=65 + j * 3,
                three_point=68 + j * 4,
                rebounding=60 + j * 2,
                passing=72 + j * 3,
                stamina=75 + j * 2
            )
            players[player_id] = player
    return players


@pytest.fixture
def season_manager(sample_teams):
    """创建SeasonManager实例"""
    return SeasonManager(list(sample_teams.values()))


@pytest.fixture
def daily_stats_viewer(season_manager, sample_teams, sample_players):
    """创建DailyStatsViewer实例"""
    return DailyStatsViewer(season_manager, sample_teams, sample_players)


class TestDailyStatsViewerInit:
    """测试DailyStatsViewer初始化"""
    
    def test_init_with_valid_data(self, season_manager, sample_teams, sample_players):
        """测试使用有效数据初始化"""
        viewer = DailyStatsViewer(season_manager, sample_teams, sample_players)
        assert viewer.season_manager is season_manager
        assert viewer.teams == sample_teams
        assert viewer.players == sample_players


class TestGetDailyGames:
    """测试获取当日比赛"""
    
    def test_get_daily_games_no_games(self, daily_stats_viewer):
        """测试无比赛日期返回空列表"""
        games = daily_stats_viewer.get_daily_games("1900-01-01")
        assert games == []
    
    def test_get_daily_games_with_schedule(self, daily_stats_viewer, season_manager):
        """测试有比赛的日期"""
        season_manager.generate_schedule()
        
        # 获取第一个比赛日
        if season_manager.schedule:
            first_date = season_manager.schedule[0].date
            games = daily_stats_viewer.get_daily_games(first_date)
            
            assert len(games) > 0
            for game in games:
                assert game["date"] == first_date
                assert "home_team_id" in game
                assert "away_team_id" in game
                assert "home_team_name" in game
                assert "away_team_name" in game
                assert "is_played" in game
    
    def test_get_daily_games_includes_ai_vs_ai(self, daily_stats_viewer, season_manager, sample_teams):
        """测试包含AI vs AI比赛 (Requirements 5.4)"""
        season_manager.generate_schedule()
        
        # 找到一个AI vs AI的比赛日期
        ai_team_ids = [
            team_id for team_id, team in sample_teams.items()
            if not team.is_player_controlled
        ]
        
        ai_vs_ai_date = None
        for game in season_manager.schedule:
            if (game.home_team_id in ai_team_ids and 
                game.away_team_id in ai_team_ids):
                ai_vs_ai_date = game.date
                break
        
        if ai_vs_ai_date:
            games = daily_stats_viewer.get_daily_games(ai_vs_ai_date)
            
            # 验证AI vs AI比赛被包含
            ai_games = [
                g for g in games
                if (g["home_team_id"] in ai_team_ids and 
                    g["away_team_id"] in ai_team_ids)
            ]
            assert len(ai_games) > 0


class TestGetGameBoxScore:
    """测试获取比赛详细数据"""
    
    def test_get_box_score_unplayed_game(self, daily_stats_viewer, sample_teams):
        """测试未完成比赛的box score"""
        team_ids = list(sample_teams.keys())
        game = ScheduledGame(
            date="2024-10-15",
            home_team_id=team_ids[0],
            away_team_id=team_ids[1],
            is_played=False
        )
        
        box_score = daily_stats_viewer.get_game_box_score(game)
        
        assert box_score["is_played"] is False
        assert box_score["home_score"] == 0
        assert box_score["away_score"] == 0
        assert box_score["home_players"] == []
        assert box_score["away_players"] == []
    
    def test_get_box_score_played_game(self, daily_stats_viewer, sample_teams, sample_players):
        """测试已完成比赛的box score"""
        team_ids = list(sample_teams.keys())
        home_team_id = team_ids[0]
        away_team_id = team_ids[1]
        
        # 创建比赛结果
        player_stats = {}
        for player_id, player in sample_players.items():
            if player.team_id in [home_team_id, away_team_id]:
                player_stats[player_id] = GameStats(
                    points=20,
                    rebounds=5,
                    assists=3,
                    steals=1,
                    blocks=1,
                    turnovers=2,
                    minutes=30
                )
        
        result = MatchResult(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=105,
            away_score=98,
            narrative="精彩的比赛",
            player_stats=player_stats,
            quarter_scores=[(25, 22), (28, 26), (24, 25), (28, 25)],
            highlights=["精彩扣篮", "关键三分"]
        )
        
        game = ScheduledGame(
            date="2024-10-15",
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            is_played=True,
            result=result
        )
        
        box_score = daily_stats_viewer.get_game_box_score(game)
        
        assert box_score["is_played"] is True
        assert box_score["home_score"] == 105
        assert box_score["away_score"] == 98
        assert len(box_score["quarter_scores"]) == 4
        assert len(box_score["highlights"]) == 2
        assert len(box_score["home_players"]) > 0
        assert len(box_score["away_players"]) > 0


class TestDailySummary:
    """测试当日比赛摘要"""
    
    def test_get_daily_summary_no_games(self, daily_stats_viewer):
        """测试无比赛时的摘要"""
        summary = daily_stats_viewer.get_daily_summary("1900-01-01")
        
        assert summary["total_games"] == 0
        assert summary["played_games"] == 0
        assert summary["games"] == []
        assert summary["message"] == "今日无比赛"
    
    def test_get_daily_summary_with_games(self, daily_stats_viewer, season_manager):
        """测试有比赛时的摘要"""
        season_manager.generate_schedule()
        
        if season_manager.schedule:
            first_date = season_manager.schedule[0].date
            summary = daily_stats_viewer.get_daily_summary(first_date)
            
            assert summary["total_games"] > 0
            assert summary["message"] is None


class TestNoGamesMessage:
    """测试无比赛提示信息"""
    
    def test_get_no_games_message(self, daily_stats_viewer):
        """测试获取无比赛提示信息 (Requirements 5.5)"""
        message = daily_stats_viewer.get_no_games_message()
        assert message == "今日无比赛"


class TestHasGamesOnDate:
    """测试日期是否有比赛"""
    
    def test_has_games_on_date_false(self, daily_stats_viewer):
        """测试无比赛日期"""
        assert daily_stats_viewer.has_games_on_date("1900-01-01") is False
    
    def test_has_games_on_date_true(self, daily_stats_viewer, season_manager):
        """测试有比赛日期"""
        season_manager.generate_schedule()
        
        if season_manager.schedule:
            first_date = season_manager.schedule[0].date
            assert daily_stats_viewer.has_games_on_date(first_date) is True
