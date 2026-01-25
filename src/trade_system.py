"""
华夏篮球联赛教练模拟器 - 交易系统

负责球员交易、自由市场和AI球队间交易功能
"""
import random
from typing import Dict, List, Optional, Tuple, Union

from src.models import Player, Team, TradeProposal
from src.player_data_manager import PlayerDataManager
from src.llm_interface import LLMInterface


class TradeSystem:
    """交易系统类"""
    
    # 自由球员池（初始为空，可通过add_free_agent添加）
    free_agents: List[str] = []
    
    # 交易历史记录
    trade_history: List[str] = []
    
    def __init__(
        self,
        data_manager: PlayerDataManager,
        llm_interface: Optional[LLMInterface] = None
    ):
        """
        初始化交易系统
        
        Args:
            data_manager: 球员数据管理器
            llm_interface: LLM接口（可选，用于智能交易评估）
        """
        self.data_manager = data_manager
        self.llm_interface = llm_interface
        self.free_agents: List[str] = []
        self.trade_history: List[str] = []
    
    def get_available_players(self, team_id: str) -> List[Player]:
        """
        获取指定球队可交易的球员列表
        
        Args:
            team_id: 球队ID
            
        Returns:
            可交易球员列表（排除外援，外援不可被交易）
        """
        roster = self.data_manager.get_team_roster(team_id)
        # 排除外援，外援不可被交易
        return [p for p in roster if not p.is_foreign]
    
    def propose_trade(self, proposal: TradeProposal) -> Tuple[bool, str]:
        """
        发起交易提案
        
        Args:
            proposal: 交易提案对象
            
        Returns:
            (是否成功, 消息) 元组
        """
        # 验证交易提案
        valid, message = self._validate_proposal(proposal)
        if not valid:
            return False, message
        
        # 获取相关球队和球员信息
        offering_team = self.data_manager.get_team(proposal.offering_team_id)
        receiving_team = self.data_manager.get_team(proposal.receiving_team_id)
        
        if not offering_team or not receiving_team:
            return False, "无效的球队ID"
        
        players_offered = [
            self.data_manager.get_player(pid) 
            for pid in proposal.players_offered
        ]
        players_requested = [
            self.data_manager.get_player(pid) 
            for pid in proposal.players_requested
        ]
        
        # 过滤掉None值
        players_offered = [p for p in players_offered if p is not None]
        players_requested = [p for p in players_requested if p is not None]
        
        if not players_offered or not players_requested:
            return False, "交易中包含无效的球员"
        
        # 评估交易
        accepted, reason, fairness_score, suggestions = self.evaluate_trade_with_llm(
            proposal, offering_team, receiving_team,
            players_offered, players_requested
        )
        
        if accepted:
            # 执行交易
            self.execute_trade(proposal)
            
            # 记录交易历史
            offered_names = ", ".join(p.name for p in players_offered)
            requested_names = ", ".join(p.name for p in players_requested)
            history_entry = (
                f"{offering_team.name} 用 {offered_names} "
                f"换取 {receiving_team.name} 的 {requested_names}"
            )
            self.trade_history.append(history_entry)
            
            return True, f"交易成功！{reason}"
        else:
            return False, f"交易被拒绝：{reason} {suggestions}"

    
    def evaluate_trade_with_llm(
        self,
        proposal: TradeProposal,
        offering_team: Team,
        receiving_team: Team,
        players_offered: List[Player],
        players_requested: List[Player]
    ) -> Tuple[bool, str, int, str]:
        """
        使用LLM评估交易提案
        
        所有交易都会调用LLM进行评估，LLM模拟球队经理人角色来决定是否接受交易。
        trade_index作为球员交易价值的参考信息传递给LLM，而不是用于本地预检。
        
        Args:
            proposal: 交易提案
            offering_team: 发起交易的球队
            receiving_team: 接收交易的球队
            players_offered: 提供的球员列表
            players_requested: 请求的球员列表
            
        Returns:
            (是否接受, 理由, 公平性评分, 建议) 元组
        """
        print("\n" + "="*50)
        print("🔄 交易评估开始")
        print(f"   发起方: {offering_team.name}")
        print(f"   接收方: {receiving_team.name}")
        print(f"   提供球员: {[f'{p.name}(交易价值:{p.trade_index})' for p in players_offered]}")
        print(f"   请求球员: {[f'{p.name}(交易价值:{p.trade_index})' for p in players_requested]}")
        print(f"   接收方状态: {receiving_team.status}")
        print("="*50)
        
        # 直接调用LLM进行评估，让LLM模拟球队经理人角色
        if self.llm_interface:
            print("🤖 调用 LLM 模拟球队经理人评估交易...")
            
            # 获取双方球队完整阵容，用于分析位置构成
            receiving_roster = self.data_manager.get_team_roster(receiving_team.id)
            offering_roster = self.data_manager.get_team_roster(offering_team.id)
            
            result = self.llm_interface.evaluate_trade(
                proposal, offering_team, receiving_team,
                players_offered, players_requested,
                self.trade_history,
                receiving_roster=receiving_roster,
                offering_roster=offering_roster
            )
            print(f"📋 LLM 评估结果: 接受={result[0]}, 公平性={result[2]}/10")
            print(f"   理由: {result[1]}")
            return result
        else:
            # 无LLM时使用本地评估
            print("⚠️  未配置 LLM，使用本地算法评估...")
            result = self._evaluate_trade_locally(
                players_offered, players_requested,
                offering_team, receiving_team
            )
            print(f"📋 本地评估结果: 接受={result[0]}, 公平性={result[2]}/10")
            print(f"   理由: {result[1]}")
            return result
    
    def _validate_proposal(self, proposal: TradeProposal) -> Tuple[bool, str]:
        """
        验证交易提案的有效性
        
        Args:
            proposal: 交易提案
            
        Returns:
            (是否有效, 消息) 元组
        """
        # 检查球队是否存在
        if not self.data_manager.get_team(proposal.offering_team_id):
            return False, "发起交易的球队不存在"
        if not self.data_manager.get_team(proposal.receiving_team_id):
            return False, "接收交易的球队不存在"
        
        # 检查是否是同一支球队
        if proposal.offering_team_id == proposal.receiving_team_id:
            return False, "不能与自己进行交易"
        
        # 检查球员是否存在且属于正确的球队
        for player_id in proposal.players_offered:
            player = self.data_manager.get_player(player_id)
            if not player:
                return False, f"球员 {player_id} 不存在"
            if player.team_id != proposal.offering_team_id:
                return False, f"球员 {player.name} 不属于发起交易的球队"
            # 检查外援不可交易
            if player.is_foreign:
                return False, f"外援 {player.name} 不可被交易"
        
        for player_id in proposal.players_requested:
            player = self.data_manager.get_player(player_id)
            if not player:
                return False, f"球员 {player_id} 不存在"
            if player.team_id != proposal.receiving_team_id:
                return False, f"球员 {player.name} 不属于接收交易的球队"
            # 检查外援不可交易
            if player.is_foreign:
                return False, f"外援 {player.name} 不可被交易"
        
        # 检查交易后外援数量是否超限
        foreign_limit_result = self._check_foreign_player_limit(proposal)
        if foreign_limit_result is not True:
            return False, foreign_limit_result
        
        return True, "验证通过"
    
    def _check_foreign_player_limit(self, proposal: TradeProposal) -> Union[bool, str]:
        """
        检查交易后外援数量是否符合规定
        
        逻辑：
        - 被裁球员(is_waived=True)不计入外援数量
        - 如果交易会导致外援数量增加且超过限制，则拒绝
        - 如果交易不增加外援数量（或减少），则允许
        
        Args:
            proposal: 交易提案
            
        Returns:
            True 如果符合限制，否则返回错误消息字符串
        """
        MAX_FOREIGN_PLAYERS = 4
        
        # 计算发起方的外援数量（排除被裁球员）
        offering_roster = self.data_manager.get_team_roster(proposal.offering_team_id)
        original_offering_foreign = sum(1 for p in offering_roster if p.is_foreign and not p.is_waived)
        
        # 计算送出的外援数量
        offering_foreign_out = 0
        for pid in proposal.players_offered:
            player = self.data_manager.get_player(pid)
            if player and player.is_foreign and not player.is_waived:
                offering_foreign_out += 1
        
        # 计算获得的外援数量
        offering_foreign_in = 0
        foreign_requested = []
        for pid in proposal.players_requested:
            player = self.data_manager.get_player(pid)
            if player and player.is_foreign and not player.is_waived:
                offering_foreign_in += 1
                foreign_requested.append(player.name)
        
        # 计算交易后的外援数量
        offering_foreign_after = original_offering_foreign - offering_foreign_out + offering_foreign_in
        
        # 只有当交易会增加外援数量且超过限制时才拒绝
        if offering_foreign_in > offering_foreign_out and offering_foreign_after > MAX_FOREIGN_PLAYERS:
            offering_team = self.data_manager.get_team(proposal.offering_team_id)
            team_name = offering_team.name if offering_team else "发起方"
            return f"{team_name}交易后外援数量将达到{offering_foreign_after}人，超过限制（每队最多{MAX_FOREIGN_PLAYERS}名外援）。当前外援{original_offering_foreign}人，交易获得外援：{', '.join(foreign_requested)}"
        
        # 计算接收方的外援数量（排除被裁球员）
        receiving_roster = self.data_manager.get_team_roster(proposal.receiving_team_id)
        original_receiving_foreign = sum(1 for p in receiving_roster if p.is_foreign and not p.is_waived)
        
        # 计算送出的外援数量
        receiving_foreign_out = 0
        for pid in proposal.players_requested:
            player = self.data_manager.get_player(pid)
            if player and player.is_foreign and not player.is_waived:
                receiving_foreign_out += 1
        
        # 计算获得的外援数量
        receiving_foreign_in = 0
        foreign_offered = []
        for pid in proposal.players_offered:
            player = self.data_manager.get_player(pid)
            if player and player.is_foreign and not player.is_waived:
                receiving_foreign_in += 1
                foreign_offered.append(player.name)
        
        # 计算交易后的外援数量
        receiving_foreign_after = original_receiving_foreign - receiving_foreign_out + receiving_foreign_in
        
        # 只有当交易会增加外援数量且超过限制时才拒绝
        if receiving_foreign_in > receiving_foreign_out and receiving_foreign_after > MAX_FOREIGN_PLAYERS:
            receiving_team = self.data_manager.get_team(proposal.receiving_team_id)
            team_name = receiving_team.name if receiving_team else "接收方"
            return f"{team_name}交易后外援数量将达到{receiving_foreign_after}人，超过限制（每队最多{MAX_FOREIGN_PLAYERS}名外援）。当前外援{original_receiving_foreign}人，交易获得外援：{', '.join(foreign_offered)}"
        
        return True

    
    def _evaluate_trade_locally(
        self,
        players_offered: List[Player],
        players_requested: List[Player],
        offering_team: Team,
        receiving_team: Team
    ) -> Tuple[bool, str, int, str]:
        """
        本地交易评估逻辑（无LLM时使用）
        
        模拟球队经理人角色，综合考虑球员价值、交易指数、球队状态等因素。
        trade_index 作为重要参考因素，但不是硬性拒绝条件。
        
        Args:
            players_offered: 提供的球员列表
            players_requested: 请求的球员列表
            offering_team: 发起交易的球队
            receiving_team: 接收交易的球队
            
        Returns:
            (是否接受, 理由, 公平性评分, 建议) 元组
        """
        # 计算双方球员总价值
        offered_value = sum(p.overall for p in players_offered)
        requested_value = sum(p.overall for p in players_requested)
        
        # 考虑年龄因素（年轻球员有额外价值）
        offered_age_bonus = sum(max(0, 28 - p.age) for p in players_offered)
        requested_age_bonus = sum(max(0, 28 - p.age) for p in players_requested)
        
        # 考虑交易指数因素（交易指数低的球员需要更高回报）
        # 交易指数越低，需要的溢价越高
        requested_trade_penalty = sum(max(0, 50 - p.trade_index) * 0.5 for p in players_requested)
        offered_trade_penalty = sum(max(0, 50 - p.trade_index) * 0.5 for p in players_offered)
        
        # 调整后的价值
        adjusted_offered = offered_value + offered_age_bonus * 0.5 - offered_trade_penalty
        adjusted_requested = requested_value + requested_age_bonus * 0.5 + requested_trade_penalty
        
        # 计算价值差异
        value_diff = adjusted_offered - adjusted_requested
        total_value = adjusted_offered + adjusted_requested
        diff_ratio = abs(value_diff) / total_value if total_value > 0 else 0
        
        # 计算公平性评分
        fairness_score = int(10 - (diff_ratio * 20))
        fairness_score = max(1, min(10, fairness_score))
        
        # 检查是否涉及核心球员
        has_core_player = any(p.trade_index < 20 for p in players_requested)
        has_important_player = any(p.trade_index < 40 for p in players_requested)
        
        # 根据球队状态调整接受概率
        base_accept_prob = 0.5
        
        if receiving_team.status == "contending":
            # 争冠球队更保守，保护核心
            if has_core_player:
                base_accept_prob = 0.2
            elif has_important_player:
                base_accept_prob = 0.35
        elif receiving_team.status == "rebuilding":
            # 重建球队更愿意交易老将
            offered_avg_age = sum(p.age for p in players_offered) / len(players_offered)
            if offered_avg_age < 26:
                base_accept_prob = 0.6  # 更愿意接受年轻球员
        
        # 根据价值差异调整
        if value_diff > 0:
            # 发起方提供更多价值，更容易接受
            accept_prob = min(0.9, base_accept_prob + diff_ratio)
        else:
            # 发起方提供较少价值，更难接受
            accept_prob = max(0.1, base_accept_prob - diff_ratio * 2)
        
        # 决定是否接受
        accepted = random.random() < accept_prob
        
        # 生成理由
        if accepted:
            if value_diff > 0:
                reason = f"这笔交易对我们有利，获得的球员价值更高。"
            elif has_core_player:
                reason = f"虽然要送出核心球员，但对方开出的条件足够诱人。"
            else:
                reason = f"交易价值基本对等，符合球队发展需要。"
            suggestions = ""
        else:
            if has_core_player and value_diff < 10:
                reason = f"涉及核心球员，需要更高的交易价值才能考虑。"
                suggestions = "建议增加更多有价值的筹码。"
            elif diff_ratio > 0.15:
                reason = f"交易价值差异过大（{diff_ratio*100:.1f}%），不够公平。"
                suggestions = "建议调整交易筹码，使双方价值更加对等。"
            else:
                reason = f"球队目前不考虑这笔交易，不符合发展战略。"
                suggestions = "可以稍后再试，或者调整交易方案。"
        
        return accepted, reason, fairness_score, suggestions
    
    def execute_trade(self, proposal: TradeProposal) -> None:
        """
        执行交易，更新双方球队阵容
        
        Args:
            proposal: 已接受的交易提案
        """
        # 转移发起方提供的球员到接收方
        for player_id in proposal.players_offered:
            self.data_manager.transfer_player(
                player_id,
                proposal.offering_team_id,
                proposal.receiving_team_id
            )
        
        # 转移接收方提供的球员到发起方
        for player_id in proposal.players_requested:
            self.data_manager.transfer_player(
                player_id,
                proposal.receiving_team_id,
                proposal.offering_team_id
            )

    
    def get_free_agents(self) -> List[Player]:
        """
        获取自由球员列表
        
        Returns:
            自由球员对象列表
        """
        free_agent_players = []
        for player_id in self.free_agents:
            player = self.data_manager.get_player(player_id)
            if player:
                free_agent_players.append(player)
        return free_agent_players
    
    def add_free_agent(self, player_id: str) -> bool:
        """
        将球员添加到自由球员池
        
        Args:
            player_id: 球员ID
            
        Returns:
            是否添加成功
        """
        player = self.data_manager.get_player(player_id)
        if not player:
            return False
        
        # 从原球队移除
        if player.team_id:
            team = self.data_manager.get_team(player.team_id)
            if team and player_id in team.roster:
                team.roster.remove(player_id)
        
        # 更新球员状态
        player.team_id = ""
        
        # 添加到自由球员池
        if player_id not in self.free_agents:
            self.free_agents.append(player_id)
        
        return True
    
    def sign_free_agent(self, team_id: str, player_id: str) -> Tuple[bool, str]:
        """
        签约自由球员
        
        Args:
            team_id: 签约球队ID
            player_id: 自由球员ID
            
        Returns:
            (是否成功, 消息) 元组
        """
        # 检查球队是否存在
        team = self.data_manager.get_team(team_id)
        if not team:
            return False, "球队不存在"
        
        # 检查球员是否在自由球员池中
        if player_id not in self.free_agents:
            return False, "该球员不在自由球员市场中"
        
        player = self.data_manager.get_player(player_id)
        if not player:
            return False, "球员不存在"
        
        # 检查外援限制
        if player.is_foreign:
            roster = self.data_manager.get_team_roster(team_id)
            foreign_count = sum(1 for p in roster if p.is_foreign)
            if foreign_count >= 4:
                return False, "球队外援名额已满（最多4名外援）"
        
        # 执行签约
        # 从自由球员池移除
        self.free_agents.remove(player_id)
        
        # 添加到球队阵容
        if player_id not in team.roster:
            team.roster.append(player_id)
        
        # 更新球员所属球队
        player.team_id = team_id
        
        return True, f"成功签约 {player.name}！"
    
    def simulate_ai_trades(self) -> List[TradeProposal]:
        """
        模拟AI球队之间的随机交易
        
        Returns:
            完成的交易提案列表
        """
        completed_trades = []
        
        # 获取所有AI控制的球队
        all_teams = self.data_manager.get_all_teams()
        ai_teams = [t for t in all_teams if not t.is_player_controlled]
        
        if len(ai_teams) < 2:
            return completed_trades
        
        # 低频交易：每次调用只有10%概率发生交易
        if random.random() > 0.1:
            return completed_trades
        
        # 随机选择两支AI球队
        team1, team2 = random.sample(ai_teams, 2)
        
        # 获取可交易球员（交易指数较高的）
        team1_players = [
            p for p in self.data_manager.get_team_roster(team1.id)
            if p.trade_index >= 40 and not p.is_injured
        ]
        team2_players = [
            p for p in self.data_manager.get_team_roster(team2.id)
            if p.trade_index >= 40 and not p.is_injured
        ]
        
        if not team1_players or not team2_players:
            return completed_trades
        
        # 随机选择交易球员
        player1 = random.choice(team1_players)
        
        # 寻找价值相近的球员
        target_value = player1.overall
        suitable_players = [
            p for p in team2_players
            if abs(p.overall - target_value) <= 10
        ]
        
        if not suitable_players:
            return completed_trades
        
        player2 = random.choice(suitable_players)
        
        # 创建交易提案
        proposal = TradeProposal(
            offering_team_id=team1.id,
            receiving_team_id=team2.id,
            players_offered=[player1.id],
            players_requested=[player2.id]
        )
        
        # 尝试执行交易（使用简化的评估）
        success, _ = self._try_ai_trade(proposal)
        
        if success:
            completed_trades.append(proposal)
            # 记录交易历史
            history_entry = (
                f"[AI交易] {team1.name} 用 {player1.name} "
                f"换取 {team2.name} 的 {player2.name}"
            )
            self.trade_history.append(history_entry)
        
        return completed_trades
    
    def _try_ai_trade(self, proposal: TradeProposal) -> Tuple[bool, str]:
        """
        尝试执行AI交易（简化评估）
        
        Args:
            proposal: 交易提案
            
        Returns:
            (是否成功, 消息) 元组
        """
        # 验证交易
        valid, message = self._validate_proposal(proposal)
        if not valid:
            return False, message
        
        # 获取球员
        players_offered = [
            self.data_manager.get_player(pid)
            for pid in proposal.players_offered
        ]
        players_requested = [
            self.data_manager.get_player(pid)
            for pid in proposal.players_requested
        ]
        
        players_offered = [p for p in players_offered if p]
        players_requested = [p for p in players_requested if p]
        
        if not players_offered or not players_requested:
            return False, "无效球员"
        
        # 简单的价值比较
        offered_value = sum(p.overall for p in players_offered)
        requested_value = sum(p.overall for p in players_requested)
        
        diff_ratio = abs(offered_value - requested_value) / max(offered_value, requested_value)
        
        # AI交易更容易达成（价值差异15%以内）
        if diff_ratio <= 0.15:
            self.execute_trade(proposal)
            return True, "AI交易成功"
        
        return False, "价值差异过大"
    
    def get_trade_history(self) -> List[str]:
        """
        获取交易历史记录
        
        Returns:
            交易历史列表
        """
        return self.trade_history.copy()
    
    def set_free_agents(self, player_ids: List[str]) -> None:
        """
        设置自由球员池
        
        Args:
            player_ids: 自由球员ID列表
        """
        self.free_agents = player_ids.copy()