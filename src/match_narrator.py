"""
华夏篮球联赛教练模拟器 - 比赛解说系统

负责生成比赛解说内容和格式化数据统计表
"""
from typing import Dict, List, Optional
from src.models import Team, Player, MatchResult, GameStats


class MatchNarrator:
    """比赛解说系统"""
    
    def __init__(self, llm_interface=None):
        """
        初始化比赛解说系统
        
        Args:
            llm_interface: LLM接口实例（可选，用于生成解说）
        """
        self.llm = llm_interface
    
    def generate_commentary(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        result: MatchResult
    ) -> Dict:
        """
        生成比赛解说内容
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            result: 比赛结果
            
        Returns:
            Dict with: narrative, quarter_scores, highlights, box_score
        """
        # 生成节次比分（如果没有的话）
        quarter_scores = result.quarter_scores if result.quarter_scores else self._generate_quarter_scores(
            result.home_score, result.away_score
        )
        
        # 生成精彩时刻（如果没有的话）
        highlights = result.highlights if result.highlights else self._generate_highlights(
            home_team, away_team, home_players, away_players, result
        )
        
        # 生成解说文本
        commentary = result.commentary if result.commentary else self._generate_basic_commentary(
            home_team, away_team, result, quarter_scores, highlights
        )
        
        # 格式化数据统计表
        box_score = self.format_box_score(result, home_team, away_team, 
                                          {p.id: p for p in home_players + away_players})
        
        return {
            "narrative": result.narrative,
            "quarter_scores": quarter_scores,
            "highlights": highlights,
            "commentary": commentary,
            "box_score": box_score
        }
    
    def _generate_quarter_scores(self, home_total: int, away_total: int) -> List[tuple]:
        """
        根据总比分生成节次比分
        
        Args:
            home_total: 主队总得分
            away_total: 客队总得分
            
        Returns:
            节次比分列表 [(主队Q1, 客队Q1), ...]
        """
        import random
        
        # 分配比例（模拟真实比赛的得分分布）
        ratios = [0.22, 0.26, 0.26, 0.26]  # 第一节略低，后三节相对均匀
        
        home_quarters = []
        away_quarters = []
        
        home_remaining = home_total
        away_remaining = away_total
        
        for i in range(4):
            if i < 3:
                # 前三节按比例分配，加入随机波动
                home_q = int(home_total * ratios[i] * random.uniform(0.85, 1.15))
                away_q = int(away_total * ratios[i] * random.uniform(0.85, 1.15))
                
                # 确保不超过剩余分数
                home_q = min(home_q, home_remaining - (3 - i) * 15)  # 保证后面每节至少15分
                away_q = min(away_q, away_remaining - (3 - i) * 15)
                home_q = max(home_q, 15)  # 每节至少15分
                away_q = max(away_q, 15)
            else:
                # 最后一节用剩余分数
                home_q = home_remaining
                away_q = away_remaining
            
            home_quarters.append(home_q)
            away_quarters.append(away_q)
            home_remaining -= home_q
            away_remaining -= away_q
        
        return list(zip(home_quarters, away_quarters))
    
    def _generate_highlights(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        result: MatchResult
    ) -> List[str]:
        """
        生成精彩时刻列表
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            result: 比赛结果
            
        Returns:
            精彩时刻描述列表
        """
        highlights = []
        all_players = {p.id: p for p in home_players + away_players}
        
        # 找出表现最好的球员
        top_scorers = []
        for player_id, stats in result.player_stats.items():
            if player_id in all_players:
                player = all_players[player_id]
                team_name = home_team.name if player.team_id == home_team.id else away_team.name
                top_scorers.append((player, stats, team_name))
        
        # 按得分排序
        top_scorers.sort(key=lambda x: x[1].points, reverse=True)
        
        # 生成得分王精彩时刻
        if top_scorers:
            top_player, top_stats, team_name = top_scorers[0]
            highlights.append(
                f"{team_name}的{top_player.name}砍下全场最高{top_stats.points}分，"
                f"带领球队{'取得胜利' if (top_player.team_id == result.winner_id) else '虽败犹荣'}。"
            )
        
        # 找出篮板王
        top_rebounders = sorted(top_scorers, key=lambda x: x[1].rebounds, reverse=True)
        if top_rebounders and top_rebounders[0][1].rebounds >= 10:
            player, stats, team_name = top_rebounders[0]
            highlights.append(f"{player.name}抢下{stats.rebounds}个篮板，统治内线。")
        
        # 找出助攻王
        top_assisters = sorted(top_scorers, key=lambda x: x[1].assists, reverse=True)
        if top_assisters and top_assisters[0][1].assists >= 8:
            player, stats, team_name = top_assisters[0]
            highlights.append(f"{player.name}送出{stats.assists}次助攻，串联全队进攻。")
        
        # 检查是否有双双或三双
        for player, stats, team_name in top_scorers:
            double_count = sum([
                1 if stats.points >= 10 else 0,
                1 if stats.rebounds >= 10 else 0,
                1 if stats.assists >= 10 else 0,
                1 if stats.steals >= 10 else 0,
                1 if stats.blocks >= 10 else 0
            ])
            if double_count >= 3:
                highlights.append(f"{player.name}打出三双表现！")
                break
            elif double_count >= 2:
                highlights.append(f"{player.name}收获两双数据。")
        
        # 添加比赛结果描述
        score_diff = abs(result.home_score - result.away_score)
        winner_name = home_team.name if result.home_score > result.away_score else away_team.name
        loser_name = away_team.name if result.home_score > result.away_score else home_team.name
        
        if score_diff >= 20:
            highlights.append(f"{winner_name}大胜{loser_name}{score_diff}分，展现强大实力。")
        elif score_diff <= 5:
            highlights.append(f"比赛悬念保持到最后，{winner_name}险胜{loser_name}。")
        
        return highlights[:5]  # 最多返回5个精彩时刻
    
    def _generate_basic_commentary(
        self,
        home_team: Team,
        away_team: Team,
        result: MatchResult,
        quarter_scores: List[tuple],
        highlights: List[str]
    ) -> str:
        """
        生成基础解说文本
        
        Args:
            home_team: 主队
            away_team: 客队
            result: 比赛结果
            quarter_scores: 节次比分
            highlights: 精彩时刻
            
        Returns:
            解说文本
        """
        commentary_parts = []
        
        # 开场
        commentary_parts.append(
            f"欢迎收看华夏篮球联赛常规赛，{home_team.name}主场迎战{away_team.name}。"
        )
        
        # 各节描述
        quarter_names = ["第一节", "第二节", "第三节", "第四节"]
        home_running = 0
        away_running = 0
        
        for i, (home_q, away_q) in enumerate(quarter_scores):
            home_running += home_q
            away_running += away_q
            
            if home_q > away_q:
                lead_team = home_team.name
                lead_points = home_q - away_q
            else:
                lead_team = away_team.name
                lead_points = away_q - home_q
            
            commentary_parts.append(
                f"{quarter_names[i]}结束，{lead_team}本节赢了{lead_points}分，"
                f"比分{home_running}:{away_running}。"
            )
        
        # 精彩时刻
        if highlights:
            commentary_parts.append("\n【精彩时刻】")
            for highlight in highlights:
                commentary_parts.append(f"• {highlight}")
        
        # 结尾
        winner_name = home_team.name if result.home_score > result.away_score else away_team.name
        commentary_parts.append(
            f"\n比赛结束！{winner_name}以{result.home_score}:{result.away_score}赢得比赛。"
        )
        
        return "\n".join(commentary_parts)
    
    def format_box_score(
        self,
        result: MatchResult,
        home_team: Team,
        away_team: Team,
        players: Dict[str, Player]
    ) -> str:
        """
        格式化比赛数据统计表
        
        Args:
            result: 比赛结果
            home_team: 主队
            away_team: 客队
            players: 球员字典 {player_id: Player}
            
        Returns:
            格式化的数据统计表字符串
        """
        lines = []
        
        # 比分标题
        lines.append("=" * 70)
        lines.append(f"{'比赛数据统计':^66}")
        lines.append("=" * 70)
        lines.append(f"{home_team.name} {result.home_score} : {result.away_score} {away_team.name}")
        lines.append("-" * 70)
        
        # 节次比分
        if result.quarter_scores:
            quarter_line = "节次比分: "
            for i, (home_q, away_q) in enumerate(result.quarter_scores):
                quarter_line += f"Q{i+1}({home_q}-{away_q}) "
            lines.append(quarter_line)
            lines.append("-" * 70)
        
        # 表头
        header = f"{'球员':<12} {'球队':<10} {'得分':>6} {'篮板':>6} {'助攻':>6} {'抢断':>6} {'盖帽':>6} {'失误':>6} {'时间':>6}"
        lines.append(header)
        lines.append("-" * 70)
        
        # 分队显示球员数据
        home_stats = []
        away_stats = []
        
        for player_id, stats in result.player_stats.items():
            if player_id in players:
                player = players[player_id]
                team_name = home_team.name if player.team_id == home_team.id else away_team.name
                
                stat_line = (
                    f"{player.name:<12} {team_name:<10} "
                    f"{stats.points:>6} {stats.rebounds:>6} {stats.assists:>6} "
                    f"{stats.steals:>6} {stats.blocks:>6} {stats.turnovers:>6} {stats.minutes:>6}"
                )
                
                if player.team_id == home_team.id:
                    home_stats.append((stats.points, stat_line))
                else:
                    away_stats.append((stats.points, stat_line))
        
        # 按得分排序
        home_stats.sort(reverse=True)
        away_stats.sort(reverse=True)
        
        # 主队数据
        lines.append(f"【{home_team.name}】")
        for _, line in home_stats:
            lines.append(line)
        
        lines.append("")
        
        # 客队数据
        lines.append(f"【{away_team.name}】")
        for _, line in away_stats:
            lines.append(line)
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def display_match_progress(
        self,
        home_team: Team,
        away_team: Team,
        result: MatchResult,
        players: Dict[str, Player],
        progressive: bool = True
    ) -> None:
        """
        显示比赛过程（用于终端输出）
        
        Args:
            home_team: 主队
            away_team: 客队
            result: 比赛结果
            players: 球员字典
            progressive: 是否逐步显示
        """
        import time
        
        print("\n" + "=" * 50)
        print(f"🏀 {home_team.name} VS {away_team.name}")
        print("=" * 50)
        
        # 显示节次比分
        if result.quarter_scores:
            quarter_names = ["第一节", "第二节", "第三节", "第四节"]
            home_running = 0
            away_running = 0
            
            for i, (home_q, away_q) in enumerate(result.quarter_scores):
                home_running += home_q
                away_running += away_q
                
                if progressive:
                    time.sleep(0.5)
                
                print(f"\n{quarter_names[i]}结束")
                print(f"  {home_team.name}: {home_q}分 (总分: {home_running})")
                print(f"  {away_team.name}: {away_q}分 (总分: {away_running})")
        
        # 显示精彩时刻
        if result.highlights:
            print("\n📌 精彩时刻:")
            for highlight in result.highlights:
                if progressive:
                    time.sleep(0.3)
                print(f"  • {highlight}")
        
        # 显示最终比分
        print("\n" + "-" * 50)
        winner = home_team.name if result.home_score > result.away_score else away_team.name
        print(f"🏆 最终比分: {home_team.name} {result.home_score} : {result.away_score} {away_team.name}")
        print(f"   胜者: {winner}")
        
        # 显示解说
        if result.commentary:
            print("\n📝 比赛解说:")
            print(result.commentary)
        elif result.narrative:
            print("\n📝 比赛概述:")
            print(result.narrative)
