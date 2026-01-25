"""
Checkpoint 5 验证测试 - 核心模块功能验证

验证任务1-4实现的核心模块功能正确性
"""
import pytest
import random
from src.stats_calculator import StatsCalculator
from src.models import Player, GameStats, Team, MatchResult
from src.season_manager import SeasonManager


class TestStatsCalculatorCore:
    """StatsCalculator核心功能测试"""
    
    def test_calculate_team_score_basic(self):
        """测试基本的球队总分计算"""
        player_stats = {
            'p1': GameStats(points=25, rebounds=5, assists=3),
            'p2': GameStats(points=20, rebounds=8, assists=2),
            'p3': GameStats(points=15, rebounds=3, assists=5),
        }
        team_ids = {'p1', 'p2', 'p3'}
        total = StatsCalculator.calculate_team_score(player_stats, team_ids)
        assert total == 60  # 25 + 20 + 15
    
    def test_calculate_team_score_subset(self):
        """测试只计算部分球员的总分"""
        player_stats = {
            'p1': GameStats(points=25),
            'p2': GameStats(points=20),
            'p3': GameStats(points=15),
        }
        team_ids = {'p1', 'p2'}  # 只计算p1和p2
        total = StatsCalculator.calculate_team_score(player_stats, team_ids)
        assert total == 45  # 25 + 20
    
    def test_score_consistency_invariant(self):
        """Property 1: 比分一致性不变量 - 球员得分之和等于球队总分"""
        # 创建测试球员
        home_players = [
            Player(id=f'h{i}', name=f'Home{i}', team_id='home', position='SG', 
                   age=25, overall=75+i, offense=75+i, defense=70, three_point=72,
                   rebounding=65, passing=70, stamina=75)
            for i in range(5)
        ]
        away_players = [
            Player(id=f'a{i}', name=f'Away{i}', team_id='away', position='SF',
                   age=26, overall=73+i, offense=73+i, defense=68, three_point=70,
                   rebounding=68, passing=68, stamina=73)
            for i in range(5)
        ]
        
        # 生成球队统计
        home_stats, home_score = StatsCalculator.generate_team_stats(home_players)
        away_stats, away_score = StatsCalculator.generate_team_stats(away_players)
        
        # 验证一致性
        calculated_home = sum(s.points for s in home_stats.values())
        calculated_away = sum(s.points for s in away_stats.values())
        
        assert calculated_home == home_score, f"Home score mismatch: {calculated_home} != {home_score}"
        assert calculated_away == away_score, f"Away score mismatch: {calculated_away} != {away_score}"
    
    def test_ability_based_stats_high_vs_low(self):
        """测试高能力值球员获得更高统计数据"""
        high_player = Player(
            id='high', name='Star', team_id='t1', position='SG', age=25,
            offense=90, defense=85, three_point=88, rebounding=70, 
            passing=80, stamina=85, overall=87
        )
        low_player = Player(
            id='low', name='Bench', team_id='t1', position='SG', age=25,
            offense=65, defense=60, three_point=62, rebounding=55,
            passing=58, stamina=65, overall=62
        )
        
        # 生成多次统计取平均
        high_points = []
        low_points = []
        for _ in range(50):
            high_stats = StatsCalculator.generate_ability_based_stats(high_player, is_starter=True)
            low_stats = StatsCalculator.generate_ability_based_stats(low_player, is_starter=True)
            high_points.append(high_stats.points)
            low_points.append(low_stats.points)
        
        high_avg = sum(high_points) / len(high_points)
        low_avg = sum(low_points) / len(low_points)
        
        # 高能力值球员平均得分应该更高
        assert high_avg > low_avg, f"High player avg ({high_avg:.1f}) should be > low player avg ({low_avg:.1f})"
    
    def test_validate_and_adjust_stats(self):
        """测试统计数据验证和调整"""
        home_ids = {'p1', 'p2'}
        away_ids = {'p3'}
        stats = {
            'p1': GameStats(points=30),
            'p2': GameStats(points=25),
            'p3': GameStats(points=40),
        }
        
        adjusted, home_score, away_score = StatsCalculator.validate_and_adjust_stats(
            stats, home_ids, away_ids
        )
        
        # 验证调整后的一致性
        calc_home = adjusted['p1'].points + adjusted['p2'].points
        calc_away = adjusted['p3'].points
        
        assert calc_home == home_score, f"Home score mismatch after adjustment"
        assert calc_away == away_score, f"Away score mismatch after adjustment"


class TestLLMInterfaceFallback:
    """LLMInterface Fallback机制测试"""
    
    def test_fallback_generates_valid_result(self):
        """Property 2: Fallback生成有效结果"""
        from src.llm_interface import LLMInterface
        
        # 创建无API key的LLM接口
        llm = LLMInterface(api_key=None)
        
        home_players = [
            Player(id=f'h{i}', name=f'Home{i}', team_id='home', position='PG',
                   age=25, overall=75, offense=75, defense=70, three_point=72,
                   rebounding=65, passing=70, stamina=75)
            for i in range(5)
        ]
        away_players = [
            Player(id=f'a{i}', name=f'Away{i}', team_id='away', position='SG',
                   age=26, overall=73, offense=73, defense=68, three_point=70,
                   rebounding=68, passing=68, stamina=73)
            for i in range(5)
        ]
        
        # 调用fallback
        result = llm._generate_fallback_match_result(
            'home', 'away', home_players, away_players, quick_mode=False
        )
        
        # 验证结果有效
        assert result is not None
        assert result.home_team_id == 'home'
        assert result.away_team_id == 'away'
        assert result.home_score != result.away_score  # 不能平局
        assert 70 <= result.home_score <= 150
        assert 70 <= result.away_score <= 150
        assert len(result.player_stats) > 0
    
    def test_fallback_quick_mode(self):
        """测试快速模式fallback不生成解说"""
        from src.llm_interface import LLMInterface
        
        llm = LLMInterface(api_key=None)
        
        home_players = [
            Player(id=f'h{i}', name=f'Home{i}', team_id='home', position='C',
                   age=25, overall=75, offense=75, defense=70, three_point=72,
                   rebounding=65, passing=70, stamina=75)
            for i in range(5)
        ]
        away_players = [
            Player(id=f'a{i}', name=f'Away{i}', team_id='away', position='PF',
                   age=26, overall=73, offense=73, defense=68, three_point=70,
                   rebounding=68, passing=68, stamina=73)
            for i in range(5)
        ]
        
        result = llm._generate_fallback_match_result(
            'home', 'away', home_players, away_players, quick_mode=True
        )
        
        # 快速模式不应该有解说文本
        assert result.narrative == ""
        assert result.commentary == ""
        assert result.highlights == []
        assert result.quarter_scores == []


class TestMatchEngineScoreConsistency:
    """MatchEngine比分一致性测试 - Requirements 3.2"""
    
    def test_match_engine_fallback_score_consistency(self):
        """Property 3: 比分一致性 - MatchEngine fallback结果的球员得分之和等于球队总分"""
        from src.match_engine import MatchEngine
        from src.llm_interface import LLMInterface
        
        llm = LLMInterface(api_key=None)
        engine = MatchEngine(llm)
        
        home_players = [
            Player(id=f'h{i}', name=f'Home{i}', team_id='home', position='SG',
                   age=25, overall=75+i, offense=75+i, defense=70, three_point=72,
                   rebounding=65, passing=70, stamina=75)
            for i in range(5)
        ]
        away_players = [
            Player(id=f'a{i}', name=f'Away{i}', team_id='away', position='SF',
                   age=26, overall=73+i, offense=73+i, defense=68, three_point=70,
                   rebounding=68, passing=68, stamina=73)
            for i in range(5)
        ]
        
        # 生成fallback结果
        result = engine._generate_fallback_match_result('home', 'away', home_players, away_players)
        
        # 验证比分一致性
        home_player_ids = {p.id for p in home_players}
        away_player_ids = {p.id for p in away_players}
        
        calculated_home = StatsCalculator.calculate_team_score(result.player_stats, home_player_ids)
        calculated_away = StatsCalculator.calculate_team_score(result.player_stats, away_player_ids)
        
        assert calculated_home == result.home_score, \
            f"Home score mismatch: calculated {calculated_home} != result {result.home_score}"
        assert calculated_away == result.away_score, \
            f"Away score mismatch: calculated {calculated_away} != result {result.away_score}"
    
    def test_llm_interface_fallback_score_consistency(self):
        """Property 3: 比分一致性 - LLMInterface fallback结果的球员得分之和等于球队总分"""
        from src.llm_interface import LLMInterface
        
        llm = LLMInterface(api_key=None)
        
        home_players = [
            Player(id=f'h{i}', name=f'Home{i}', team_id='home', position='PG',
                   age=25, overall=80+i, offense=80+i, defense=75, three_point=78,
                   rebounding=70, passing=75, stamina=80)
            for i in range(5)
        ]
        away_players = [
            Player(id=f'a{i}', name=f'Away{i}', team_id='away', position='SG',
                   age=26, overall=78+i, offense=78+i, defense=73, three_point=76,
                   rebounding=68, passing=73, stamina=78)
            for i in range(5)
        ]
        
        # 生成fallback结果
        result = llm._generate_fallback_match_result('home', 'away', home_players, away_players)
        
        # 验证比分一致性
        home_player_ids = {p.id for p in home_players}
        away_player_ids = {p.id for p in away_players}
        
        calculated_home = StatsCalculator.calculate_team_score(result.player_stats, home_player_ids)
        calculated_away = StatsCalculator.calculate_team_score(result.player_stats, away_player_ids)
        
        assert calculated_home == result.home_score, \
            f"Home score mismatch: calculated {calculated_home} != result {result.home_score}"
        assert calculated_away == result.away_score, \
            f"Away score mismatch: calculated {calculated_away} != result {result.away_score}"
    
    def test_ensure_score_consistency_method(self):
        """测试ensure_score_consistency方法正确计算比分"""
        player_stats = {
            'p1': GameStats(points=25, rebounds=5, assists=3),
            'p2': GameStats(points=20, rebounds=8, assists=2),
            'p3': GameStats(points=15, rebounds=3, assists=5),
            'a1': GameStats(points=22, rebounds=6, assists=4),
            'a2': GameStats(points=18, rebounds=7, assists=3),
        }
        home_ids = {'p1', 'p2', 'p3'}
        away_ids = {'a1', 'a2'}
        
        adjusted_stats, home_score, away_score = StatsCalculator.ensure_score_consistency(
            player_stats, home_ids, away_ids
        )
        
        # 验证返回的比分等于球员得分之和
        calculated_home = StatsCalculator.calculate_team_score(adjusted_stats, home_ids)
        calculated_away = StatsCalculator.calculate_team_score(adjusted_stats, away_ids)
        
        assert calculated_home == home_score, f"Home score mismatch: {calculated_home} != {home_score}"
        assert calculated_away == away_score, f"Away score mismatch: {calculated_away} != {away_score}"


class TestMatchEngineIsolation:
    """MatchEngine比赛隔离测试"""
    
    def test_player_match_only_simulates_player_team(self):
        """Property 3: 玩家比赛只模拟玩家球队"""
        from src.match_engine import MatchEngine
        from src.llm_interface import LLMInterface
        from src.models import ScheduledGame
        
        llm = LLMInterface(api_key=None)
        engine = MatchEngine(llm)
        
        # 创建球队
        teams = {
            'player_team': Team(id='player_team', name='玩家队', city='北京',
                               is_player_controlled=True, roster=['p1', 'p2', 'p3', 'p4', 'p5']),
            'ai_team': Team(id='ai_team', name='AI队', city='上海',
                           is_player_controlled=False, roster=['a1', 'a2', 'a3', 'a4', 'a5']),
        }
        
        # 创建球员
        players = {}
        for i in range(5):
            players[f'p{i+1}'] = Player(
                id=f'p{i+1}', name=f'Player{i+1}', team_id='player_team',
                position='SG', age=25, overall=75, offense=75, defense=70,
                three_point=72, rebounding=65, passing=70, stamina=75
            )
            players[f'a{i+1}'] = Player(
                id=f'a{i+1}', name=f'AI{i+1}', team_id='ai_team',
                position='SF', age=26, overall=73, offense=73, defense=68,
                three_point=70, rebounding=68, passing=68, stamina=73
            )
        
        # 创建比赛
        game = ScheduledGame(
            date='2024-10-15',
            home_team_id='player_team',
            away_team_id='ai_team'
        )
        
        # 模拟玩家球队比赛
        result, injuries = engine.simulate_player_team_match(
            game, teams, players, auto_update_stats=False, check_injuries=False
        )
        
        # 验证结果只包含这两支球队
        assert result.home_team_id == 'player_team'
        assert result.away_team_id == 'ai_team'
        
        # 验证球员统计只包含参赛球员
        for player_id in result.player_stats.keys():
            assert player_id in players, f"Unknown player {player_id} in stats"


class TestScheduleConstraints:
    """赛程约束测试"""
    
    @pytest.fixture
    def sample_teams(self):
        """创建20支测试球队"""
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
    
    def test_alternating_schedule_no_triple_consecutive(self, sample_teams):
        """Property 6: 没有球队连续比赛超过2天"""
        from datetime import datetime
        
        manager = SeasonManager(sample_teams)
        manager.generate_alternating_schedule()
        
        # 检查每支球队的连续比赛天数
        for team_id in manager.team_ids:
            team_games = [
                g for g in manager.schedule 
                if team_id in (g.home_team_id, g.away_team_id)
            ]
            team_games.sort(key=lambda g: g.date)
            
            consecutive = 1
            for i in range(1, len(team_games)):
                prev_date = datetime.strptime(team_games[i-1].date, "%Y-%m-%d")
                curr_date = datetime.strptime(team_games[i].date, "%Y-%m-%d")
                
                if (curr_date - prev_date).days == 1:
                    consecutive += 1
                    assert consecutive <= 2, \
                        f"Team {team_id} has {consecutive} consecutive game days"
                else:
                    consecutive = 1
    
    def test_schedule_team_game_count(self, sample_teams):
        """测试每队比赛场次在合理范围内"""
        manager = SeasonManager(sample_teams)
        manager.generate_alternating_schedule()
        
        for team_id in manager.team_ids:
            games_count = manager.get_team_games_count(team_id)
            # 每队至少38场，最多42场
            assert 38 <= games_count <= 42, \
                f"Team {team_id} has {games_count} games, expected 38-42"
    
    def test_no_team_plays_twice_same_day(self, sample_teams):
        """测试没有球队同一天打两场比赛"""
        manager = SeasonManager(sample_teams)
        manager.generate_alternating_schedule()
        
        # 按日期分组检查
        from collections import defaultdict
        date_teams = defaultdict(list)
        
        for game in manager.schedule:
            date_teams[game.date].append(game.home_team_id)
            date_teams[game.date].append(game.away_team_id)
        
        for date, teams in date_teams.items():
            # 检查是否有重复
            assert len(teams) == len(set(teams)), \
                f"Some team plays twice on {date}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
