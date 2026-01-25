"""
Integration test for China Basketball League Coach Simulator - Final Checkpoint
Tests the complete game flow without LLM calls
"""
import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime

from src.models import Player, Team, GameStats, Standing, PlayoffSeries, GameState
from src.player_data_manager import PlayerDataManager, calculate_overall
from src.training_system import TrainingSystem
from src.season_manager import SeasonManager
from src.injury_system import InjurySystem
from src.storage_manager import StorageManager


class TestCompleteGameFlow:
    """Test complete game flow integration"""
    
    @pytest.fixture
    def data_manager(self):
        """Load real player data"""
        return PlayerDataManager()
    
    @pytest.fixture
    def teams_and_players(self, data_manager):
        """Get teams and players from data manager"""
        teams, players = data_manager.load_all_data()
        return teams, players, data_manager
    
    def test_all_20_teams_loaded(self, teams_and_players):
        """Verify all 20 teams are loaded"""
        teams, _, _ = teams_and_players
        assert len(teams) == 20, f"Expected 20 teams, got {len(teams)}"
    
    def test_team_selection_marks_player_controlled(self, teams_and_players):
        """Test that selecting a team marks it as player-controlled"""
        teams, players, _ = teams_and_players
        
        # Select first team
        team_ids = list(teams.keys())
        selected_team_id = team_ids[0]
        
        # Mark as player controlled
        teams[selected_team_id].is_player_controlled = True
        
        # Verify exactly one team is player controlled
        player_controlled = [t for t in teams.values() if t.is_player_controlled]
        ai_controlled = [t for t in teams.values() if not t.is_player_controlled]
        
        assert len(player_controlled) == 1
        assert len(ai_controlled) == 19
    
    def test_season_schedule_generation(self, teams_and_players):
        """Test season schedule generates games for all teams"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        schedule = season_manager.generate_schedule()
        
        # Count games per team - schedule returns ScheduledGame objects
        team_games = {team_id: 0 for team_id in teams.keys()}
        for game in schedule:
            team_games[game.home_team_id] += 1
            team_games[game.away_team_id] += 1
        
        # Each team should have at least 38 games (minimum: 19 home + 19 away)
        # and at most 42 games (target)
        for team_id, count in team_games.items():
            assert count >= 38, f"Team {team_id} has only {count} games, expected at least 38"
            assert count <= 42, f"Team {team_id} has {count} games, expected at most 42"
    
    def test_training_system_attribute_boost(self, teams_and_players):
        """Test training system boosts training points correctly"""
        teams, players, data_manager = teams_and_players
        training_system = TrainingSystem(data_manager)
        
        # Get a player
        player = list(players.values())[0]
        original_offense = player.offense
        
        # Execute training
        programs = training_system.get_available_programs()
        offense_program = next(p for p in programs if p.target_attribute == 'offense')
        
        result = training_system.execute_training(player, offense_program)
        
        # Verify training points gained is within range (0-2)
        assert 0 <= result['training_points_gained'] <= 2, f"Training points {result['training_points_gained']} not in range 0-2"
        
        # Verify training points are tracked
        assert result['current_training_points'] >= result['training_points_gained']
        
        # If attribute upgraded, verify it increased by 1
        if result['attribute_upgraded']:
            assert player.offense == original_offense + 1
    
    def test_training_only_for_player_team(self, teams_and_players):
        """Test training only applies to player-controlled team"""
        teams, players, data_manager = teams_and_players
        training_system = TrainingSystem(data_manager)
        
        # Mark first team as player controlled
        team_ids = list(teams.keys())
        player_team = teams[team_ids[0]]
        player_team.is_player_controlled = True
        
        ai_team = teams[team_ids[1]]
        ai_team.is_player_controlled = False
        
        # Training should work for player team
        assert training_system.can_train(player_team) == True
        
        # Training should not work for AI team
        assert training_system.can_train(ai_team) == False
    
    def test_standings_update_after_game(self, teams_and_players):
        """Test standings update correctly after a game"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        team_ids = list(teams.keys())
        home_id = team_ids[0]
        away_id = team_ids[1]
        
        # Simulate a game result
        season_manager.update_standings(home_id, away_id, 110, 100)
        
        standings = season_manager.get_standings()
        
        # Find the teams in standings
        home_standing = next(s for s in standings if s.team_id == home_id)
        away_standing = next(s for s in standings if s.team_id == away_id)
        
        assert home_standing.wins == 1
        assert home_standing.losses == 0
        assert away_standing.wins == 0
        assert away_standing.losses == 1
    
    def test_injury_system_marks_player_injured(self, teams_and_players):
        """Test injury system correctly marks players as injured"""
        _, players, _ = teams_and_players
        injury_system = InjurySystem()
        
        player = list(players.values())[0]
        
        # Apply injury
        injury_system.apply_injury(player, 5)
        
        assert player.is_injured == True
        assert player.injury_days == 5
    
    def test_injury_recovery(self, teams_and_players):
        """Test injured players recover after time passes"""
        _, players, _ = teams_and_players
        injury_system = InjurySystem()
        
        player = list(players.values())[0]
        
        # Apply injury
        injury_system.apply_injury(player, 3)
        assert player.is_injured == True
        
        # Recover over time
        recovered = injury_system.recover_players([player], 3)
        
        assert player.is_injured == False
        assert player.injury_days == 0
    
    def test_playoff_qualification(self, teams_and_players):
        """Test playoff qualification logic"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        # Simulate some games to create standings
        team_ids = list(teams.keys())
        for i, team_id in enumerate(team_ids):
            # Give teams different win counts
            for _ in range(20 - i):
                opponent = team_ids[(i + 1) % len(team_ids)]
                season_manager.update_standings(team_id, opponent, 100, 90)
        
        # Initialize playoffs
        playoff_series = season_manager.init_playoffs()
        
        # Should have playoff series created
        assert len(playoff_series) > 0


class TestStorageRoundTrip:
    """Test save/load round trip consistency"""
    
    @pytest.fixture
    def temp_save_dir(self):
        """Create temporary save directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_save_load_roundtrip(self, temp_save_dir):
        """Test saving and loading preserves game state"""
        # Load initial data
        data_manager = PlayerDataManager()
        teams, players = data_manager.load_all_data()
        
        # Create game state
        team_ids = list(teams.keys())
        teams[team_ids[0]].is_player_controlled = True
        
        season_manager = SeasonManager(list(teams.values()))
        schedule = season_manager.generate_schedule()
        
        # Create storage manager with temp directory
        storage_manager = StorageManager(save_dir=temp_save_dir)
        
        # Create game state object
        game_state = GameState(
            current_date='2024-10-15',
            player_team_id=team_ids[0],
            season_phase='regular',
            teams=teams,
            players=players,
            standings=season_manager.get_standings(),
            schedule=schedule,
            playoff_bracket={},
            free_agents=[]
        )
        
        # Save
        storage_manager.save_game(game_state, slot=1)
        
        # Load
        loaded_state = storage_manager.load_game(slot=1)
        
        # Verify key data preserved
        assert loaded_state.current_date == game_state.current_date
        assert loaded_state.player_team_id == game_state.player_team_id
        assert loaded_state.season_phase == game_state.season_phase
        assert len(loaded_state.teams) == len(game_state.teams)
        assert len(loaded_state.players) == len(game_state.players)


class TestPlayerDataIntegrity:
    """Test player data integrity"""
    
    def test_all_players_have_required_attributes(self):
        """Test all players have required attributes"""
        data_manager = PlayerDataManager()
        _, players = data_manager.load_all_data()
        
        required_attrs = [
            'name', 'position', 'age', 'offense', 'defense',
            'three_point', 'rebounding', 'passing', 'stamina',
            'overall', 'skill_tags', 'trade_index', 'is_foreign'
        ]
        
        for player_id, player in players.items():
            for attr in required_attrs:
                assert hasattr(player, attr), f"Player {player_id} missing {attr}"
    
    def test_overall_calculation_consistency(self):
        """Test overall rating calculation is consistent"""
        data_manager = PlayerDataManager()
        _, players = data_manager.load_all_data()
        
        for player_id, player in players.items():
            # Recalculate overall using the module-level function
            calculated = calculate_overall(player)
            
            # Should be within valid range
            assert 0 <= calculated <= 99, f"Player {player_id} overall {calculated} out of range"


class TestPlayoffSystemIntegration:
    """Test complete playoff system integration"""
    
    @pytest.fixture
    def data_manager(self):
        """Load real player data"""
        return PlayerDataManager()
    
    @pytest.fixture
    def teams_and_players(self, data_manager):
        """Get teams and players from data manager"""
        teams, players = data_manager.load_all_data()
        return teams, players, data_manager
    
    @pytest.fixture
    def temp_save_dir(self):
        """Create temporary save directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_playoff_bracket_structure(self, teams_and_players):
        """Test playoff bracket has correct structure after initialization"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        # Simulate games to create standings
        team_ids = list(teams.keys())
        for i, team_id in enumerate(team_ids):
            for _ in range(20 - i):
                opponent = team_ids[(i + 1) % len(team_ids)]
                season_manager.update_standings(team_id, opponent, 100, 90)
        
        # Initialize playoffs
        season_manager.init_playoffs()
        bracket = season_manager.get_playoff_bracket()
        
        # Verify play-in series exist (5v12, 6v11, 7v10, 8v9)
        assert "play_in_1" in bracket
        assert "play_in_2" in bracket
        assert "play_in_3" in bracket
        assert "play_in_4" in bracket
        
        # Verify top 4 seeds are stored
        assert "quarter_seed_1" in bracket
        assert "quarter_seed_2" in bracket
        assert "quarter_seed_3" in bracket
        assert "quarter_seed_4" in bracket
        
        # Verify play-in series are PlayoffSeries objects
        for i in range(1, 5):
            series = bracket[f"play_in_{i}"]
            assert isinstance(series, PlayoffSeries)
            assert series.round_name == "play_in"
            assert series.team1_wins == 0
            assert series.team2_wins == 0
    
    def test_playoff_series_wins_needed(self, teams_and_players):
        """Test wins_needed is correct for different rounds"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        # Simulate games
        team_ids = list(teams.keys())
        for i, team_id in enumerate(team_ids):
            for _ in range(20 - i):
                opponent = team_ids[(i + 1) % len(team_ids)]
                season_manager.update_standings(team_id, opponent, 100, 90)
        
        # Initialize playoffs
        season_manager.init_playoffs()
        bracket = season_manager.get_playoff_bracket()
        
        # Play-in should need 2 wins
        play_in_series = bracket["play_in_1"]
        assert play_in_series.wins_needed == 2
        
        # Create a quarter-final series to test
        quarter_series = PlayoffSeries(
            team1_id="team1",
            team2_id="team2",
            round_name="quarter"
        )
        assert quarter_series.wins_needed == 4
        
        # Semi-final should need 4 wins
        semi_series = PlayoffSeries(
            team1_id="team1",
            team2_id="team2",
            round_name="semi"
        )
        assert semi_series.wins_needed == 4
        
        # Final should need 4 wins
        final_series = PlayoffSeries(
            team1_id="team1",
            team2_id="team2",
            round_name="final"
        )
        assert final_series.wins_needed == 4
    
    def test_playoff_series_completion(self, teams_and_players):
        """Test series completion detection"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        # Simulate games
        team_ids = list(teams.keys())
        for i, team_id in enumerate(team_ids):
            for _ in range(20 - i):
                opponent = team_ids[(i + 1) % len(team_ids)]
                season_manager.update_standings(team_id, opponent, 100, 90)
        
        # Initialize playoffs
        season_manager.init_playoffs()
        bracket = season_manager.get_playoff_bracket()
        
        # Get first play-in series
        series = bracket["play_in_1"]
        team1_id = series.team1_id
        
        # Series should not be complete initially
        assert not series.is_complete
        assert series.winner_id is None
        
        # Simulate team1 winning 2 games (play-in needs 2 wins)
        season_manager.update_playoff_series("play_in_1", team1_id)
        season_manager.update_playoff_series("play_in_1", team1_id)
        
        # Series should now be complete
        updated_bracket = season_manager.get_playoff_bracket()
        updated_series = updated_bracket["play_in_1"]
        assert updated_series.is_complete
        assert updated_series.winner_id == team1_id
    
    def test_playoff_state_save_load_roundtrip(self, teams_and_players, temp_save_dir):
        """Test playoff state is correctly saved and loaded"""
        teams, players, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        # Simulate games
        team_ids = list(teams.keys())
        for i, team_id in enumerate(team_ids):
            for _ in range(20 - i):
                opponent = team_ids[(i + 1) % len(team_ids)]
                season_manager.update_standings(team_id, opponent, 100, 90)
        
        # Initialize playoffs
        season_manager.init_playoffs()
        bracket = season_manager.get_playoff_bracket()
        
        # Simulate some playoff games
        series = bracket["play_in_1"]
        team1_id = series.team1_id
        season_manager.update_playoff_series("play_in_1", team1_id)
        
        # Create game state with playoff data
        game_state = GameState(
            current_date='2025-03-15',
            player_team_id=team_ids[0],
            season_phase='playoff',
            teams=teams,
            players=players,
            standings=season_manager.get_standings(),
            schedule=season_manager.schedule,
            playoff_bracket=season_manager.get_playoff_bracket(),
            free_agents=[],
            is_playoff_phase=True,
            player_eliminated=False
        )
        
        # Save
        storage_manager = StorageManager(save_dir=temp_save_dir)
        storage_manager.save_game(game_state, slot=1)
        
        # Load
        loaded_state = storage_manager.load_game(slot=1)
        
        # Verify playoff state preserved
        assert loaded_state.season_phase == 'playoff'
        assert loaded_state.is_playoff_phase == True
        assert loaded_state.player_eliminated == False
        
        # Verify playoff bracket preserved
        assert "play_in_1" in loaded_state.playoff_bracket
        loaded_series = loaded_state.playoff_bracket["play_in_1"]
        assert isinstance(loaded_series, PlayoffSeries)
        assert loaded_series.team1_wins == 1  # We simulated one win
        assert loaded_series.round_name == "play_in"
    
    def test_playoff_state_with_eliminated_player(self, teams_and_players, temp_save_dir):
        """Test saving and loading when player is eliminated"""
        teams, players, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        team_ids = list(teams.keys())
        
        # Create game state with player eliminated
        game_state = GameState(
            current_date='2025-03-20',
            player_team_id=team_ids[0],
            season_phase='playoff',
            teams=teams,
            players=players,
            standings=season_manager.get_standings(),
            schedule=season_manager.schedule,
            playoff_bracket={},
            free_agents=[],
            is_playoff_phase=True,
            player_eliminated=True  # Player is eliminated
        )
        
        # Save
        storage_manager = StorageManager(save_dir=temp_save_dir)
        storage_manager.save_game(game_state, slot=2)
        
        # Load
        loaded_state = storage_manager.load_game(slot=2)
        
        # Verify eliminated state preserved
        assert loaded_state.is_playoff_phase == True
        assert loaded_state.player_eliminated == True
    
    def test_team_elimination_detection(self, teams_and_players):
        """Test is_team_eliminated correctly identifies eliminated teams"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        # Simulate games
        team_ids = list(teams.keys())
        for i, team_id in enumerate(team_ids):
            for _ in range(20 - i):
                opponent = team_ids[(i + 1) % len(team_ids)]
                season_manager.update_standings(team_id, opponent, 100, 90)
        
        # Initialize playoffs
        season_manager.init_playoffs()
        bracket = season_manager.get_playoff_bracket()
        
        # Get play-in series and simulate team2 losing
        series = bracket["play_in_1"]
        team1_id = series.team1_id
        team2_id = series.team2_id
        
        # Team2 should not be eliminated yet
        assert not season_manager.is_team_eliminated(team2_id)
        
        # Simulate team1 winning the series (2 wins for play-in)
        season_manager.update_playoff_series("play_in_1", team1_id)
        season_manager.update_playoff_series("play_in_1", team1_id)
        
        # Team2 should now be eliminated
        assert season_manager.is_team_eliminated(team2_id)
        
        # Team1 should not be eliminated
        assert not season_manager.is_team_eliminated(team1_id)
    
    def test_get_playoff_bracket_for_display(self, teams_and_players):
        """Test get_playoff_bracket_for_display returns complete data"""
        teams, _, _ = teams_and_players
        season_manager = SeasonManager(list(teams.values()))
        season_manager.generate_schedule()
        
        # Simulate games
        team_ids = list(teams.keys())
        for i, team_id in enumerate(team_ids):
            for _ in range(20 - i):
                opponent = team_ids[(i + 1) % len(team_ids)]
                season_manager.update_standings(team_id, opponent, 100, 90)
        
        # Initialize playoffs
        season_manager.init_playoffs()
        
        # Get display data
        display_data = season_manager.get_playoff_bracket_for_display(teams)
        
        # Verify structure
        assert "play_in" in display_data
        assert "quarter_seeds" in display_data
        assert "quarter" in display_data
        assert "semi" in display_data
        assert "final" in display_data
        
        # Verify play-in series have team names
        for series in display_data["play_in"]:
            assert "team1_id" in series
            assert "team1_name" in series
            assert "team2_id" in series
            assert "team2_name" in series
            assert "team1_wins" in series
            assert "team2_wins" in series
            assert "is_complete" in series


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
