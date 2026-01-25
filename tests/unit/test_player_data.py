"""
单元测试 - 球员数据管理器

验证数据层的基本功能
"""
import pytest
import os
import json
import tempfile
from src.models import Player, Team
from src.player_data_manager import PlayerDataManager, calculate_overall


class TestCalculateOverall:
    """测试总评计算函数"""
    
    def test_calculate_overall_pg(self):
        """测试控球后卫总评计算"""
        player = Player(
            id="test_pg",
            name="测试控卫",
            team_id="test_team",
            position="PG",
            age=25,
            offense=80,
            defense=70,
            three_point=75,
            rebounding=40,
            passing=85,
            stamina=80
        )
        overall = calculate_overall(player)
        # PG权重: offense=0.25, defense=0.15, three_point=0.20, rebounding=0.05, passing=0.25, stamina=0.10
        expected = int(80*0.25 + 70*0.15 + 75*0.20 + 40*0.05 + 85*0.25 + 80*0.10)
        assert overall == expected
        assert 0 <= overall <= 99
    
    def test_calculate_overall_center(self):
        """测试中锋总评计算"""
        player = Player(
            id="test_c",
            name="测试中锋",
            team_id="test_team",
            position="C",
            age=28,
            offense=70,
            defense=85,
            three_point=30,
            rebounding=90,
            passing=50,
            stamina=75
        )
        overall = calculate_overall(player)
        # C权重: offense=0.15, defense=0.30, three_point=0.05, rebounding=0.30, passing=0.10, stamina=0.10
        expected = int(70*0.15 + 85*0.30 + 30*0.05 + 90*0.30 + 50*0.10 + 75*0.10)
        assert overall == expected
        assert 0 <= overall <= 99
    
    def test_calculate_overall_bounds(self):
        """测试总评边界值"""
        # 最低属性
        player_low = Player(
            id="test_low",
            name="测试低",
            team_id="test_team",
            position="SF",
            age=20,
            offense=0,
            defense=0,
            three_point=0,
            rebounding=0,
            passing=0,
            stamina=0
        )
        assert calculate_overall(player_low) == 0
        
        # 最高属性
        player_high = Player(
            id="test_high",
            name="测试高",
            team_id="test_team",
            position="SF",
            age=25,
            offense=99,
            defense=99,
            three_point=99,
            rebounding=99,
            passing=99,
            stamina=99
        )
        assert calculate_overall(player_high) == 99


class TestPlayerDataManager:
    """测试球员数据管理器"""
    
    def test_load_all_data(self):
        """测试加载所有数据"""
        mgr = PlayerDataManager()
        teams, players = mgr.load_all_data()
        
        # 验证加载了20支球队
        assert len(teams) == 20
        
        # 验证加载了球员数据
        assert len(players) > 0
        
        # 验证球队数据结构
        for team_id, team in teams.items():
            assert isinstance(team, Team)
            assert team.id == team_id
            assert team.name != ""
            assert team.city != ""
            assert isinstance(team.roster, list)
    
    def test_get_team_roster(self):
        """测试获取球队阵容"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        roster = mgr.get_team_roster("team_liaoning")
        assert len(roster) > 0
        
        for player in roster:
            assert isinstance(player, Player)
            assert player.team_id == "team_liaoning"
    
    def test_get_team_roster_invalid(self):
        """测试获取不存在球队的阵容"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        roster = mgr.get_team_roster("invalid_team")
        assert roster == []
    
    def test_update_player_overall(self):
        """测试更新球员总评"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        # 获取一个球员
        player_id = list(mgr.players.keys())[0]
        player = mgr.players[player_id]
        
        # 修改属性
        original_offense = player.offense
        player.offense = min(99, player.offense + 5)
        
        # 更新总评
        new_overall = mgr.update_player_overall(player_id)
        
        # 验证总评已更新
        assert player.overall == new_overall
        assert 0 <= new_overall <= 99
        
        # 恢复原值
        player.offense = original_offense
    
    def test_update_player_stats(self):
        """测试更新球员统计数据 - 验证 Requirements 11.1, 11.2, 11.3"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        player_id = list(mgr.players.keys())[0]
        player = mgr.players[player_id]
        
        # 重置球员统计数据以便测试
        player.games_played = 0
        player.total_points = 0
        player.total_rebounds = 0
        player.total_assists = 0
        player.total_steals = 0
        player.total_blocks = 0
        player.total_turnovers = 0
        player.total_minutes = 0
        player.avg_points = 0.0
        player.avg_rebounds = 0.0
        player.avg_assists = 0.0
        player.avg_steals = 0.0
        player.avg_blocks = 0.0
        player.avg_turnovers = 0.0
        player.avg_minutes = 0.0
        
        # 第一场比赛数据
        game_stats_1 = {
            "points": 20,
            "rebounds": 5,
            "assists": 8,
            "steals": 2,
            "blocks": 1,
            "turnovers": 3,
            "minutes": 35
        }
        
        result = mgr.update_player_stats(player_id, game_stats_1)
        
        # 验证返回值
        assert result == True
        
        # Requirement 11.1: 验证 games_played 更新
        assert player.games_played == 1
        
        # Requirement 11.2: 验证累计数据更新
        assert player.total_points == 20
        assert player.total_rebounds == 5
        assert player.total_assists == 8
        assert player.total_steals == 2
        assert player.total_blocks == 1
        assert player.total_turnovers == 3
        assert player.total_minutes == 35
        
        # Requirement 11.3: 验证场均数据计算 (avg = total / games_played)
        assert player.avg_points == 20.0
        assert player.avg_rebounds == 5.0
        assert player.avg_assists == 8.0
        assert player.avg_steals == 2.0
        assert player.avg_blocks == 1.0
        assert player.avg_turnovers == 3.0
        assert player.avg_minutes == 35.0
        
        # 第二场比赛数据
        game_stats_2 = {
            "points": 30,
            "rebounds": 7,
            "assists": 6,
            "steals": 1,
            "blocks": 2,
            "turnovers": 2,
            "minutes": 38
        }
        
        mgr.update_player_stats(player_id, game_stats_2)
        
        # 验证两场比赛后的数据
        assert player.games_played == 2
        
        # 累计数据
        assert player.total_points == 50  # 20 + 30
        assert player.total_rebounds == 12  # 5 + 7
        assert player.total_assists == 14  # 8 + 6
        assert player.total_steals == 3  # 2 + 1
        assert player.total_blocks == 3  # 1 + 2
        assert player.total_turnovers == 5  # 3 + 2
        assert player.total_minutes == 73  # 35 + 38
        
        # 场均数据 (avg = total / games_played)
        assert player.avg_points == 25.0  # 50 / 2
        assert player.avg_rebounds == 6.0  # 12 / 2
        assert player.avg_assists == 7.0  # 14 / 2
        assert player.avg_steals == 1.5  # 3 / 2
        assert player.avg_blocks == 1.5  # 3 / 2
        assert player.avg_turnovers == 2.5  # 5 / 2
        assert player.avg_minutes == 36.5  # 73 / 2
    
    def test_update_player_stats_invalid_player(self):
        """测试更新不存在球员的统计数据"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        result = mgr.update_player_stats("invalid_player_id", {"points": 20})
        assert result == False
    
    def test_update_player_stats_missing_fields(self):
        """测试更新统计数据时缺少某些字段"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        player_id = list(mgr.players.keys())[0]
        player = mgr.players[player_id]
        
        # 重置统计数据
        player.games_played = 0
        player.total_points = 0
        player.total_rebounds = 0
        player.avg_points = 0.0
        player.avg_rebounds = 0.0
        
        # 只提供部分字段
        game_stats = {
            "points": 15,
            "rebounds": 8
            # 缺少 assists, steals, blocks, turnovers, minutes
        }
        
        mgr.update_player_stats(player_id, game_stats)
        
        # 验证提供的字段被更新
        assert player.total_points == 15
        assert player.total_rebounds == 8
        assert player.games_played == 1
        
        # 验证缺少的字段使用默认值0
        assert player.avg_points == 15.0
        assert player.avg_rebounds == 8.0
    
    def test_transfer_player(self):
        """测试球员转会"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        # 获取辽宁队的一个球员
        liaoning_roster = mgr.get_team_roster("team_liaoning")
        if len(liaoning_roster) > 0:
            player = liaoning_roster[-1]  # 取最后一个球员
            player_id = player.id
            
            # 转会到广东队
            result = mgr.transfer_player(player_id, "team_liaoning", "team_guangdong")
            assert result == True
            
            # 验证球员已转会
            assert player.team_id == "team_guangdong"
            assert player_id not in mgr.teams["team_liaoning"].roster
            assert player_id in mgr.teams["team_guangdong"].roster
            
            # 转回辽宁队（恢复原状）
            mgr.transfer_player(player_id, "team_guangdong", "team_liaoning")


class TestPlayerModel:
    """测试球员数据模型"""
    
    def test_player_required_attributes(self):
        """测试球员必需属性"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        for player_id, player in mgr.players.items():
            # 验证所有必需属性存在
            assert hasattr(player, 'id')
            assert hasattr(player, 'name')
            assert hasattr(player, 'team_id')
            assert hasattr(player, 'position')
            assert hasattr(player, 'age')
            assert hasattr(player, 'is_foreign')
            assert hasattr(player, 'offense')
            assert hasattr(player, 'defense')
            assert hasattr(player, 'three_point')
            assert hasattr(player, 'rebounding')
            assert hasattr(player, 'passing')
            assert hasattr(player, 'stamina')
            assert hasattr(player, 'overall')
            assert hasattr(player, 'skill_tags')
            assert hasattr(player, 'trade_index')
            
            # 验证属性值范围
            assert 0 <= player.offense <= 99
            assert 0 <= player.defense <= 99
            assert 0 <= player.three_point <= 99
            assert 0 <= player.rebounding <= 99
            assert 0 <= player.passing <= 99
            assert 0 <= player.stamina <= 99
            assert 0 <= player.overall <= 99
            assert 0 <= player.trade_index <= 100
            assert player.position in ["PG", "SG", "SF", "PF", "C"]


class TestTeamModel:
    """测试球队数据模型"""
    
    def test_team_count(self):
        """测试球队数量"""
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        assert len(mgr.teams) == 20
    
    def test_team_roster_integrity(self):
        """测试球队阵容完整性 - 验证已存在的球员数据一致性
        
        注意：当前使用样例数据，只验证已存在的球员。
        完整球员数据将在全流程跑通后补充。
        """
        mgr = PlayerDataManager()
        mgr.load_all_data()
        
        for team_id, team in mgr.teams.items():
            # 每支球队应该有阵容定义
            assert len(team.roster) > 0
            
            # 验证阵容中已存在的球员数据一致性
            existing_players = [pid for pid in team.roster if pid in mgr.players]
            for player_id in existing_players:
                assert mgr.players[player_id].team_id == team_id
        
        # 验证至少有一些球员数据存在（样例数据）
        assert len(mgr.players) > 0, "应该至少有一些样例球员数据"
