"""
华夏篮球联赛教练模拟器 - 大语言模型接口

负责与国内LLM API（如DeepSeek）的通信，用于比赛模拟和交易评估
"""
import json
import re
import random
import asyncio
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from config import LLMConfig
from src.models import Player, Team, MatchResult, GameStats, TradeProposal
from src.stats_calculator import StatsCalculator


class LLMInterface:
    """大语言模型接口类"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        初始化LLM接口
        
        Args:
            api_key: API密钥，默认从配置读取
            base_url: API端点，默认从配置读取
            model: 模型名称，默认从配置读取
        """
        self.api_key = api_key or LLMConfig.API_KEY
        self.base_url = base_url or LLMConfig.BASE_URL
        self.model = model or LLMConfig.MODEL
        self.timeout = LLMConfig.TIMEOUT
        self.max_retries = LLMConfig.MAX_RETRIES
        self.temperature = LLMConfig.TEMPERATURE
        self.max_tokens = LLMConfig.MAX_TOKENS
        self._llm_available = None  # 缓存LLM可用性状态
        
        # 上一场比赛数据缓存 - 用于防止模型生成过于相似的结果
        # 格式: {team_id: {"team_score": int, "player_scores": {player_id: int}}}
        self._last_match_data: Dict[str, Dict] = {}
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试LLM连接是否正常
        
        Returns:
            (是否成功, 消息) 元组
        """
        if not HAS_HTTPX:
            return False, "httpx库未安装，请运行: pip install httpx"
        
        if not self.api_key:
            return False, "API密钥未配置，请设置LLM_API_KEY环境变量或在config.py中配置"
        
        try:
            # 发送一个简单的测试请求
            response = self.chat("你好", "你是一个测试助手，请简短回复。")
            if response:
                self._llm_available = True
                return True, "LLM连接正常"
            else:
                self._llm_available = False
                return False, "LLM返回空响应"
        except Exception as e:
            self._llm_available = False
            return False, f"LLM连接失败: {str(e)}"
    
    def is_available(self) -> bool:
        """
        检查LLM是否可用（使用缓存结果）
        
        Returns:
            是否可用
        """
        if self._llm_available is None:
            success, _ = self.test_connection()
            return success
        return self._llm_available
    
    def record_match_result(
        self,
        team_id: str,
        team_score: int,
        player_stats: Dict[str, GameStats],
        team_player_ids: set
    ) -> None:
        """
        记录球队的上一场比赛数据
        
        用于在下一场比赛的提示词中加入历史数据，防止模型生成过于相似的结果
        
        Args:
            team_id: 球队ID
            team_score: 球队总得分
            player_stats: 球员统计数据字典 {player_id: GameStats}
            team_player_ids: 该球队的球员ID集合
        """
        player_scores = {}
        for player_id in team_player_ids:
            if player_id in player_stats:
                player_scores[player_id] = player_stats[player_id].points
        
        self._last_match_data[team_id] = {
            "team_score": team_score,
            "player_scores": player_scores
        }
    
    def get_last_match_data(self, team_id: str) -> Optional[Dict]:
        """
        获取球队的上一场比赛数据
        
        Args:
            team_id: 球队ID
            
        Returns:
            上一场比赛数据字典，如果没有则返回None
            格式: {"team_score": int, "player_scores": {player_id: int}}
        """
        return self._last_match_data.get(team_id)
    
    def clear_last_match_data(self, team_id: Optional[str] = None) -> None:
        """
        清除上一场比赛数据
        
        Args:
            team_id: 球队ID，如果为None则清除所有数据
        """
        if team_id is None:
            self._last_match_data.clear()
        elif team_id in self._last_match_data:
            del self._last_match_data[team_id]
    
    def _format_last_match_info(
        self,
        team_id: str,
        team_name: str,
        players: List[Player]
    ) -> str:
        """
        格式化上一场比赛信息，用于加入提示词
        
        Args:
            team_id: 球队ID
            team_name: 球队名称
            players: 球员列表
            
        Returns:
            格式化的上一场比赛信息字符串，如果没有数据则返回空字符串
        """
        last_data = self.get_last_match_data(team_id)
        if not last_data:
            return ""
        
        player_id_to_name = {p.id: p.name for p in players}
        
        info = f"\n【{team_name}上一场比赛数据参考】\n"
        info += f"球队总得分: {last_data['team_score']}分\n"
        info += "球员得分:\n"
        
        # 按得分排序显示
        sorted_scores = sorted(
            last_data['player_scores'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for player_id, points in sorted_scores:
            player_name = player_id_to_name.get(player_id, player_id)
            info += f"  - {player_name}: {points}分\n"
        
        info += "★ 请确保本场比赛球队总得分与上一场相差至少10分，球员得分按照规则指引有明显差异！★\n"
        
        return info
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        发送聊天请求到LLM API
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            
        Returns:
            LLM响应文本
            
        Raises:
            Exception: API调用失败时抛出异常
        """
        if not HAS_HTTPX:
            raise ImportError("httpx库未安装，请运行: pip install httpx")
        
        if not self.api_key:
            raise ValueError("API密钥未配置，请设置LLM_API_KEY环境变量或在config.py中配置")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                    
            except httpx.TimeoutException as e:
                last_error = e
                continue
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 401:
                    raise ValueError("API密钥无效，请检查配置")
                elif e.response.status_code == 402:
                    raise ValueError("API账户余额不足，请充值后再试")
                elif e.response.status_code == 429:
                    raise ValueError("API请求频率超限，请稍后再试")
                continue
            except Exception as e:
                last_error = e
                continue
        
        raise Exception(f"API调用失败，已重试{self.max_retries}次: {last_error}")


    def get_ability_guidance_text(self) -> str:
        """
        获取能力值引导文本
        
        返回详细的能力值与统计数据对应关系说明，强调随机性和多样性
        """
        return '''
【能力值与统计数据对应关系 - 重要：保持高随机性和多样性】

★★★ 核心原则：每场比赛的数据分布必须不同！★★★

每个球员本场比赛有三种状态（随机决定）：
- 爆发状态（15%概率）：数据比平时高30-50%
- 低迷状态（15%概率）：数据比平时低40-60%
- 正常状态（70%概率）：正常发挥，但仍有较大波动

【比赛角色机制 - 必须实现】
每场比赛随机选择1-2个球员作为"进攻核心"：
- 进攻核心获得20-30%的得分加成
- 核心可以是任何球员，不一定是能力值最高的
- 这样每场比赛的得分王可能不同

1. 得分期望（正常状态下）:
   - 90+总评: 期望15-25分，爆发可达35+
   - 85-89总评: 期望10-22分
   - 80-84总评: 期望8-12分
   - 75-79总评: 期望2-8分
   - <75总评: 期望0-6分
   
   【关键】低能力值球员爆发时可以得到25+分！
   【关键】高能力值球员低迷时可能只有8-12分！

2. 篮板期望:
   - 高篮板能力(85+): 期望5-12个，爆发可达18+
   - 中等(75-84): 期望3-8个
   - 低(<75): 期望1-6个

3. 助攻期望:
   - 高传球能力(85+): 期望6-12个
   - 中等(75-84): 期望2-6个
   - 低(<75): 期望0-5个

4. 抢断/盖帽: 0-5个，与防守能力相关但波动大

5. 若对位球员防守能力强，则该球员得分50%概率被限制下滑20%~40%

【必须遵守的规则 - 违反将导致数据不真实】
1. ★ 尽量不要让同一个球员连续多场都是得分最高！每场比赛的得分王30%概率不同
2. ★ 但能力值最高的还是高概率(60%)获得队内得分王
3. ★ 50%的概率让同一个球员连续两场得分在队内排名不一致，比如第一场得分队内排名第3，那么第二场不应该再排名第3
4. ★ 每场比赛至少有2-3个"意外"：低能力值球员得分超过高能力值球员
5. ★ 数据分布要有层次感：不要所有人得分都在10-20之间
6. ★ 偶尔让替补球员成为得分王（约15%概率）
7. ★ 比赛结果要有悬念，弱队有25-30%概率爆冷获胜
8. ★ 同一球员连续两场比赛的得分差异应该至少有5-10分

【数据分布示例 - 好的例子】
第一场: 28, 22, 18, 12, 10, 8, 6, 4 (核心球员A爆发)
第二场: 24, 20, 19, 15, 11, 9, 7, 5 (均衡分布)
第三场: 32, 16, 14, 13, 12, 8, 6, 3 (核心球员B爆发)
第四场: 18, 17, 16, 15, 14, 10, 8, 6 (团队篮球)

【数据分布示例 - 坏的例子（避免！）】
第一场: 32, 24, 15, 14, 11, 9, 8, 6
第二场: 32, 24, 15, 14, 12, 9, 8, 6  ← 太相似了！
第三场: 31, 23, 16, 14, 11, 9, 8, 6  ← 还是太相似！

【球队总得分变化规则 - 重要】
★ 同一支球队连续两场比赛的总得分应该有明显差异！
★ 80%的概率：连续两场比赛的球队总得分相差至少10分以上
★ 20%的概率：连续两场比赛的球队总得分相差5-10分
★ 避免连续多场比赛总得分都在相近区间（如都在100-105分之间）

【球队总得分示例 - 好的例子】
某球队连续5场总得分: 98, 112, 95, 108, 103 （波动明显，差异大）

【球队总得分示例 - 坏的例子（避免！）】
某球队连续5场总得分: 102, 104, 101, 103, 105 ← 太相似了！每场都在100-105之间
'''

    def get_foreign_player_minutes_guidance(self, players: List[Player], team_name: str) -> str:
        """
        获取外援上场时间约束提示词
        
        根据华夏篮球联赛外援规则（四节七人次，前三节最多同时两名外援，第四节最多一名外援），
        生成外援上场时间分配建议。
        
        Args:
            players: 球队球员列表
            team_name: 球队名称
            
        Returns:
            外援上场时间约束提示词
        """
        # 筛选出未受伤、未被裁的外援
        foreign_players = [p for p in players if p.is_foreign and not p.is_injured and not p.is_waived]
        
        if not foreign_players:
            return ""
        
        # 按总评排序
        foreign_players.sort(key=lambda p: p.overall, reverse=True)
        foreign_count = len(foreign_players)
        
        guidance = f"\n【{team_name}外援上场时间约束 - 必须遵守】\n"
        guidance += "根据华夏篮球联赛外援规则（四节七人次，前三节最多同时两名外援，第四节最多一名外援）:\n"
        guidance += f"该队有{foreign_count}名外援:\n"
        
        for i, p in enumerate(foreign_players):
            guidance += f"  - {p.name}(ID:{p.id}) 总评:{p.overall}\n"
        
        if foreign_count >= 4:
            # 4名外援的时间分配
            guidance += "\n外援上场时间分配要求:\n"
            guidance += f"  - 核心外援({foreign_players[0].name}): 35-40分钟\n"
            guidance += f"  - 主力外援({foreign_players[1].name}): 25-30分钟\n"
            guidance += f"  - 次主力外援({foreign_players[2].name}): 15-20分钟\n"
            guidance += f"  - 次主力外援({foreign_players[3].name}): 15-20分钟\n"
        elif foreign_count == 3:
            # 3名外援的时间分配
            guidance += "\n外援上场时间分配要求:\n"
            guidance += f"  - 核心外援({foreign_players[0].name}): 35-40分钟\n"
            guidance += f"  - 主力外援({foreign_players[1].name}): 25-30分钟\n"
            guidance += f"  - 主力外援({foreign_players[2].name}): 25-30分钟\n"
        elif foreign_count == 2:
            # 2名外援的时间分配
            guidance += "\n外援上场时间分配要求:\n"
            guidance += f"  - 核心外援({foreign_players[0].name}): 35-40分钟\n"
            guidance += f"  - 主力外援({foreign_players[1].name}): 30-40分钟\n"
        elif foreign_count == 1:
            # 1名外援的时间分配
            guidance += "\n外援上场时间分配要求:\n"
            guidance += f"  - 外援({foreign_players[0].name}): 35-40分钟\n"
        
        guidance += "\n★ 请按照上述时间范围分配外援上场时间！外援时间应该在区间内波动！\n"
        
        return guidance

    def build_match_prompt(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        match_context: Optional[str] = None
    ) -> str:
        """
        构建比赛模拟提示词
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            match_context: 比赛背景信息（可选）
            
        Returns:
            构建好的提示词
        """
        def format_player_info(player: Player) -> str:
            """格式化单个球员信息"""
            injury_status = "（伤病中）" if player.is_injured else ""
            foreign_tag = "（外援）" if player.is_foreign else ""
            tags = "、".join(player.skill_tags) if player.skill_tags else "无"
            
            return (
                f"  - ID:{player.id} {player.name}{foreign_tag}{injury_status}\n"
                f"    位置: {player.position} | 年龄: {player.age}\n"
                f"    总评: {player.overall} | 进攻: {player.offense} | 防守: {player.defense}\n"
                f"    三分: {player.three_point} | 篮板: {player.rebounding} | 传球: {player.passing}\n"
                f"    体力: {player.stamina} | 技术标签: {tags}"
            )
        
        def format_team_roster(team: Team, players: List[Player]) -> str:
            """格式化球队阵容"""
            # 按总评排序，取前11人（主力+轮换），排除受伤和被裁球员
            active_players = [p for p in players if not p.is_injured and not p.is_waived]
            sorted_players = sorted(active_players, key=lambda p: p.overall, reverse=True)[:11]
            
            team_overall = sum(p.overall for p in sorted_players) / len(sorted_players) if sorted_players else 0
            
            roster_str = f"【{team.name}】（{team.city}）\n"
            roster_str += f"球队状态: {team.status} | 平均总评: {team_overall:.1f}\n"
            roster_str += "阵容:\n"
            
            for player in sorted_players:
                roster_str += format_player_info(player) + "\n"
            
            return roster_str
        
        # 构建提示词
        prompt = "你是一个专业的篮球比赛解说员和数据分析师。请根据以下两支球队的阵容信息，模拟一场常规赛比赛。\n\n"
        
        prompt += "=" * 50 + "\n"
        prompt += "【比赛信息】\n"
        prompt += f"主队: {home_team.name}\n"
        prompt += f"客队: {away_team.name}\n"
        
        if match_context:
            prompt += f"比赛背景: {match_context}\n"
        
        prompt += "=" * 50 + "\n\n"
        
        # 主队阵容
        prompt += format_team_roster(home_team, home_players) + "\n"
        
        # 客队阵容
        prompt += format_team_roster(away_team, away_players) + "\n"
        
        # 添加上一场比赛数据参考（防止模型生成过于相似的结果）
        home_last_match_info = self._format_last_match_info(home_team.id, home_team.name, home_players)
        away_last_match_info = self._format_last_match_info(away_team.id, away_team.name, away_players)
        
        if home_last_match_info or away_last_match_info:
            prompt += "=" * 50 + "\n"
            prompt += "【上一场比赛数据参考 - 请确保本场数据有明显差异】\n"
            if home_last_match_info:
                prompt += home_last_match_info
            if away_last_match_info:
                prompt += away_last_match_info
            prompt += "\n"
        
        # 添加能力值引导文本
        prompt += "=" * 50 + "\n"
        prompt += self.get_ability_guidance_text() + "\n"
        
        # 添加外援上场时间约束
        home_foreign_guidance = self.get_foreign_player_minutes_guidance(home_players, home_team.name)
        away_foreign_guidance = self.get_foreign_player_minutes_guidance(away_players, away_team.name)
        if home_foreign_guidance or away_foreign_guidance:
            prompt += "=" * 50 + "\n"
            if home_foreign_guidance:
                prompt += home_foreign_guidance
            if away_foreign_guidance:
                prompt += away_foreign_guidance
        
        prompt += "=" * 50 + "\n"
        prompt += "【输出要求】\n"
        prompt += "请按以下JSON格式输出比赛结果（只输出JSON，不要其他内容）:\n"
        prompt += """```json
{
  "home_score": <主队得分>,
  "away_score": <客队得分>,
  "narrative": "<比赛过程描述，包含关键时刻和精彩表现，100-200字>",
  "quarter_scores": [[<主队Q1得分>, <客队Q1得分>], [<主队Q2得分>, <客队Q2得分>], [<主队Q3得分>, <客队Q3得分>], [<主队Q4得分>, <客队Q4得分>]],
  "highlights": ["<精彩时刻1>", "<精彩时刻2>", "<精彩时刻3>"],
  "commentary": "<完整的比赛解说文本，描述比赛进程、关键转折点、球员表现等，200-400字>",
  "player_stats": {
    "<球员ID，如player_bj_001>": {
      "points": <得分>,
      "rebounds": <篮板>,
      "assists": <助攻>,
      "steals": <抢断>,
      "blocks": <盖帽>,
      "turnovers": <失误>,
      "minutes": <上场时间>
    }
  }
}
```

注意事项:
1. 比分应该符合篮球比赛实际情况（通常在85-120分之间）
2. 【重要】球员数据必须与其能力值相匹配，参考上面的能力值引导生成统计数据
3. 总评高的球队获胜概率更大，但弱队也有机会爆冷
4. 每位上场球员的上场时间总和应接近240分钟（5人×48分钟）
5. 【重要】player_stats的key必须使用球员ID（如player_bj_001），不要使用球员名字
6. 【非常重要】每支球队必须各输出9-11名球员的数据，两队合计18-22人。不是总共9-11人，而是每队各9-11人！
7. quarter_scores必须是4个节次的得分，每节得分之和等于总得分
"""
        
        return prompt
    
    def get_match_system_prompt(self) -> str:
        """获取比赛模拟的系统提示词"""
        return (
            "你是一个专业的篮球比赛模拟器。你需要根据球员能力值和球队状态，"
            "生成合理的比赛结果。请确保:\n"
            "1. 输出严格遵循JSON格式\n"
            "2. 比分和数据符合篮球比赛实际\n"
            "3. 强队获胜概率更高，但要保留一定随机性\n"
            "4. 【重要】球员数据与其能力值的关系:(期望不是一定)\n"
            "   - 90+总评球员期望得分15-25分\n"
            "   - 85-89总评球员期望得分10-22分\n"
            "   - 80-84总评球员期望得分8-15分\n"
            "   - 75-79总评球员期望得分2-8分\n"
            "   - 70-74总评球员期望得分0-6分\n"
            "   - 还有40%概率会落到其它总评区间的期望得分中"
            "5. 各项能力值影响对应统计数据（进攻→得分，篮板→篮板数，传球→助攻等）\n"
            "6. 保持随机性，各项数据不要连续两场太相似\n"
            "7. 【非常重要】每支球队必须各输出9-11名球员的数据，两队合计18-22人"
        )

    def build_quick_match_prompt(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player]
    ) -> str:
        """
        构建快速模拟提示词 - 仅输出球员统计数据
        
        用于非玩家球队比赛的快速模拟，不生成解说文本
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            
        Returns:
            构建好的提示词
        """
        def format_player_brief(player: Player) -> str:
            """格式化球员简要信息"""
            injury_status = "（伤病中）" if player.is_injured else ""
            return (
                f"  - ID:{player.id} {player.name}{injury_status} "
                f"位置:{player.position} 总评:{player.overall} "
                f"进攻:{player.offense} 三分:{player.three_point} "
                f"篮板:{player.rebounding} 传球:{player.passing} 防守:{player.defense}"
            )
        
        def format_team_brief(team: Team, players: List[Player]) -> str:
            """格式化球队简要信息"""
            active_players = [p for p in players if not p.is_injured and not p.is_waived]
            sorted_players = sorted(active_players, key=lambda p: p.overall, reverse=True)[:11]
            team_overall = sum(p.overall for p in sorted_players) / len(sorted_players) if sorted_players else 0
            
            roster_str = f"【{team.name}】平均总评:{team_overall:.1f}\n"
            for player in sorted_players:
                roster_str += format_player_brief(player) + "\n"
            return roster_str
        
        prompt = "请根据以下两支球队的阵容，快速模拟一场篮球比赛，只需输出球员统计数据。\n\n"
        
        prompt += f"主队: {home_team.name}\n"
        prompt += format_team_brief(home_team, home_players) + "\n"
        
        prompt += f"客队: {away_team.name}\n"
        prompt += format_team_brief(away_team, away_players) + "\n"
        
        # 添加上一场比赛数据参考（防止模型生成过于相似的结果）
        home_last_match_info = self._format_last_match_info(home_team.id, home_team.name, home_players)
        away_last_match_info = self._format_last_match_info(away_team.id, away_team.name, away_players)
        
        if home_last_match_info or away_last_match_info:
            prompt += "【上一场比赛数据参考 - 请确保本场数据有明显差异】\n"
            if home_last_match_info:
                prompt += home_last_match_info
            if away_last_match_info:
                prompt += away_last_match_info
            prompt += "\n"
        
        # 添加能力值引导文本
        prompt += self.get_ability_guidance_text() + "\n"
        
        # 添加外援上场时间约束
        home_foreign_guidance = self.get_foreign_player_minutes_guidance(home_players, home_team.name)
        away_foreign_guidance = self.get_foreign_player_minutes_guidance(away_players, away_team.name)
        if home_foreign_guidance or away_foreign_guidance:
            if home_foreign_guidance:
                prompt += home_foreign_guidance
            if away_foreign_guidance:
                prompt += away_foreign_guidance
            prompt += "\n"
        
        prompt += "【输出要求】\n"
        prompt += "请只输出JSON格式的球员统计数据（不要其他内容）:\n"
        prompt += """```json
{
  "player_stats": {
    "<球员ID>": {
      "points": <得分>,
      "rebounds": <篮板>,
      "assists": <助攻>,
      "steals": <抢断>,
      "blocks": <盖帽>,
      "turnovers": <失误>,
      "minutes": <上场时间>
    }
  }
}
```

注意事项:
1. 【重要】球员数据必须与其能力值相匹配，参考上面的能力值引导生成统计数据
2. 高总评球员(90+)应该有更高的得分期望(20-35分)
3. 进攻能力高的球员得分更高，篮板能力高的球员篮板更多
4. 传球能力高的球员助攻更多，防守能力高的球员抢断盖帽更多
5. 每位上场球员的上场时间总和应接近240分钟
6. 【非常重要】每支球队必须各输出9-11名球员的数据，两队合计18-22人。不是总共9-11人，而是每队各9-11人！
7. 不需要输出比赛解说、精彩时刻等文本内容
8. 保持随机性，但整体趋势符合能力值分布
"""
        return prompt
    
    def get_quick_match_system_prompt(self) -> str:
        """获取快速模拟的系统提示词"""
        return (
            "你是一个专业的篮球数据分析师。你需要根据球员能力值，"
            "快速生成合理的比赛统计数据。请确保:\n"
            "1. 输出严格遵循JSON格式，只包含player_stats\n"
            "2. 【重要】高能力值球员(85+总评)应该有更高的数据产出:\n"
            "   - 90+总评球员期望得分15-25分\n"
            "   - 85-89总评球员期望得分10-22分\n"
            "   - 80-84总评球员期望得分8-12分\n"
            "   - 75-79总评球员期望得分2-8分\n"
            "   - 70-74总评球员期望得分0-6分\n"
            "3. 各项数据与对应能力值正相关（进攻→得分，篮板→篮板数，传球→助攻，防守→抢断盖帽）\n"
            "4. 保持一定随机性\n"
            "5. 【非常重要】每支球队必须各输出9-11名球员的数据，两队合计18-22人"
        )
    
    def parse_quick_match_response(
        self,
        response: str,
        home_team_id: str,
        away_team_id: str,
        home_players: List[Player],
        away_players: List[Player]
    ) -> MatchResult:
        """
        解析快速模拟响应
        
        只解析球员统计数据，使用StatsCalculator计算球队总分
        
        Args:
            response: LLM响应文本
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_players: 主队球员列表
            away_players: 客队球员列表
            
        Returns:
            MatchResult对象（不含解说文本）
        """
        try:
            json_data = self._extract_json(response)
            
            if json_data is None:
                print(f"⚠️ [LLM解析] 无法从响应中提取JSON数据")
                print(f"   响应内容前200字符: {response[:200]}...")
                raise ValueError("无法从响应中提取JSON数据")
            
            # 解析球员统计
            player_stats = {}
            raw_stats = json_data.get("player_stats", {})
            
            if not raw_stats:
                print(f"⚠️ [LLM解析] JSON中没有player_stats字段")
                print(f"   JSON字段: {list(json_data.keys())}")
            
            all_players = {p.id: p for p in home_players + away_players}
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            
            matched_count = 0
            for player_id, stats in raw_stats.items():
                if player_id in all_players:
                    matched_count += 1
                    # 确定球员所属球队
                    player_team_id = all_players[player_id].team_id
                    player_stats[player_id] = GameStats(
                        points=max(0, min(60, int(stats.get("points", 0)))),
                        rebounds=max(0, min(30, int(stats.get("rebounds", 0)))),
                        assists=max(0, min(25, int(stats.get("assists", 0)))),
                        steals=max(0, min(10, int(stats.get("steals", 0)))),
                        blocks=max(0, min(10, int(stats.get("blocks", 0)))),
                        turnovers=max(0, min(15, int(stats.get("turnovers", 0)))),
                        minutes=max(0, min(48, int(stats.get("minutes", 0)))),
                        team_id=player_team_id  # 记录比赛时球员所属球队
                    )
            
            print(f"   [LLM解析] 解析到 {len(raw_stats)} 个球员数据，匹配 {matched_count} 个")
            
            # 应用得分随机调整（两队各自选择模式）
            player_stats = StatsCalculator.apply_score_adjustment(
                player_stats, home_player_ids, away_player_ids
            )
            print(f"   [LLM解析] 已应用得分随机调整")
            
            # 使用StatsCalculator计算球队总分
            home_score = StatsCalculator.calculate_team_score(player_stats, home_player_ids)
            away_score = StatsCalculator.calculate_team_score(player_stats, away_player_ids)
            
            # 验证并调整统计数据确保分数在合理范围内
            player_stats, home_score, away_score = StatsCalculator.validate_and_adjust_stats(
                player_stats, home_player_ids, away_player_ids
            )
            
            # 确保不是平局
            if home_score == away_score:
                # 随机给一方加1分
                if random.random() < 0.5:
                    home_score += 1
                    # 给主队得分最高的球员加1分
                    home_top_scorer = max(
                        [(pid, s) for pid, s in player_stats.items() if pid in home_player_ids],
                        key=lambda x: x[1].points,
                        default=(None, None)
                    )
                    if home_top_scorer[0]:
                        player_stats[home_top_scorer[0]].points += 1
                else:
                    away_score += 1
                    away_top_scorer = max(
                        [(pid, s) for pid, s in player_stats.items() if pid in away_player_ids],
                        key=lambda x: x[1].points,
                        default=(None, None)
                    )
                    if away_top_scorer[0]:
                        player_stats[away_top_scorer[0]].points += 1
            
            # 快速模拟不生成解说文本
            return MatchResult(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_score=home_score,
                away_score=away_score,
                narrative="",
                player_stats=player_stats,
                quarter_scores=[],
                highlights=[],
                commentary="",
                home_player_ids=list(home_player_ids),  # 记录比赛时的球员列表
                away_player_ids=list(away_player_ids)   # 记录比赛时的球员列表
            )
            
        except Exception as e:
            # 解析失败，使用fallback
            return self._generate_fallback_match_result(
                home_team_id, away_team_id, home_players, away_players,
                quick_mode=True
            )
    
    def simulate_match_quick(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player]
    ) -> MatchResult:
        """
        快速比赛模拟 - 用于非玩家球队比赛
        
        仅生成球员统计数据，不生成解说、精彩时刻等文本内容
        用于每日比赛页面展示和场均数据更新，显著提高模拟速度
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            
        Returns:
            MatchResult对象（不含解说文本）
        """
        if not self.api_key:
            print(f"⚠️ [LLM] API密钥未配置，使用本地算法模拟: {home_team.name} vs {away_team.name}")
            result = self._generate_fallback_match_result(
                home_team.id, away_team.id, home_players, away_players,
                quick_mode=True
            )
            # 记录比赛数据供下一场参考
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            return result
        
        try:
            print(f"🤖 [LLM] 快速模拟比赛: {home_team.name} vs {away_team.name}")
            prompt = self.build_quick_match_prompt(
                home_team, away_team, home_players, away_players
            )
            system_prompt = self.get_quick_match_system_prompt()
            
            response = self.chat(prompt, system_prompt)
            print(f"✅ [LLM] 收到响应，正在解析...")
            
            result = self.parse_quick_match_response(
                response, home_team.id, away_team.id, home_players, away_players
            )
            print(f"✅ [LLM] 解析成功: {result.home_score}:{result.away_score}, 球员数据: {len(result.player_stats)}人")
            
            # 记录比赛数据供下一场参考
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            
            return result
            
        except Exception as e:
            # LLM调用失败，使用fallback
            print(f"⚠️ [LLM] 快速模拟失败，使用本地算法: {home_team.name} vs {away_team.name}")
            print(f"   错误信息: {str(e)}")
            result = self._generate_fallback_match_result(
                home_team.id, away_team.id, home_players, away_players,
                quick_mode=True
            )
            # 记录比赛数据供下一场参考
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            return result

    def _simulate_single_match_for_batch(
        self,
        match_data: Dict
    ) -> Tuple[int, MatchResult]:
        """
        为批量模拟执行单场比赛模拟（内部方法）
        
        Args:
            match_data: 包含比赛信息的字典
                - index: 比赛索引
                - home_team: 主队
                - away_team: 客队
                - home_players: 主队球员列表
                - away_players: 客队球员列表
                
        Returns:
            (索引, MatchResult) 元组
        """
        index = match_data["index"]
        home_team = match_data["home_team"]
        away_team = match_data["away_team"]
        home_players = match_data["home_players"]
        away_players = match_data["away_players"]
        
        try:
            # 构建提示词
            prompt = self.build_quick_match_prompt(
                home_team, away_team, home_players, away_players
            )
            system_prompt = self.get_quick_match_system_prompt()
            
            # 发送请求
            response = self.chat(prompt, system_prompt)
            
            # 解析响应
            result = self.parse_quick_match_response(
                response, home_team.id, away_team.id, home_players, away_players
            )
            
            # 记录比赛数据
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            
            return (index, result)
            
        except Exception as e:
            # 失败时使用 fallback
            print(f"⚠️ [LLM并发] 比赛 {index+1} 模拟失败: {home_team.name} vs {away_team.name}, 错误: {str(e)}")
            result = self._generate_fallback_match_result(
                home_team.id, away_team.id, home_players, away_players,
                quick_mode=True
            )
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            return (index, result)

    def batch_simulate_matches_concurrent(
        self,
        matches: List[Dict]
    ) -> List[MatchResult]:
        """
        并发批量模拟多场比赛
        
        使用线程池并发发送多个 LLM API 请求，显著提高批量模拟速度。
        
        Args:
            matches: 比赛信息列表，每个元素为字典:
                {
                    "home_team": Team,
                    "away_team": Team,
                    "home_players": List[Player],
                    "away_players": List[Player]
                }
                
        Returns:
            MatchResult 列表，顺序与输入 matches 一致
        """
        if not matches:
            return []
        
        # 检查是否启用并发
        if not LLMConfig.ENABLE_CONCURRENT_SIMULATION:
            print(f"ℹ️ [LLM] 并发模拟已禁用，使用串行模式")
            return self._batch_simulate_sequential(matches)
        
        # 检查 API 密钥
        if not self.api_key:
            print(f"⚠️ [LLM] API密钥未配置，使用本地算法批量模拟 {len(matches)} 场比赛")
            return self._batch_simulate_fallback(matches)
        
        max_workers = min(LLMConfig.MAX_CONCURRENT_REQUESTS, len(matches))
        print(f"🚀 [LLM并发] 开始并发模拟 {len(matches)} 场比赛，最大并发数: {max_workers}")
        
        # 准备任务数据
        match_data_list = []
        for i, match in enumerate(matches):
            match_data_list.append({
                "index": i,
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_players": match["home_players"],
                "away_players": match["away_players"]
            })
        
        # 使用线程池并发执行
        results = [None] * len(matches)
        completed = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(self._simulate_single_match_for_batch, data): data["index"]
                for data in match_data_list
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_index):
                try:
                    index, result = future.result()
                    results[index] = result
                    completed += 1
                    home_team = matches[index]["home_team"]
                    away_team = matches[index]["away_team"]
                    print(f"✅ [LLM并发] ({completed}/{len(matches)}) {home_team.name} vs {away_team.name}: {result.home_score}:{result.away_score}")
                except Exception as e:
                    index = future_to_index[future]
                    print(f"❌ [LLM并发] 比赛 {index+1} 执行异常: {str(e)}")
                    # 使用 fallback 结果
                    match = matches[index]
                    results[index] = self._generate_fallback_match_result(
                        match["home_team"].id,
                        match["away_team"].id,
                        match["home_players"],
                        match["away_players"],
                        quick_mode=True
                    )
                    completed += 1
        
        print(f"🏁 [LLM并发] 批量模拟完成，共 {len(matches)} 场比赛")
        return results

    def _batch_simulate_sequential(
        self,
        matches: List[Dict]
    ) -> List[MatchResult]:
        """
        串行批量模拟（并发禁用时使用）
        
        Args:
            matches: 比赛信息列表
            
        Returns:
            MatchResult 列表
        """
        results = []
        for i, match in enumerate(matches):
            print(f"🤖 [LLM] 串行模拟 ({i+1}/{len(matches)}): {match['home_team'].name} vs {match['away_team'].name}")
            result = self.simulate_match_quick(
                match["home_team"],
                match["away_team"],
                match["home_players"],
                match["away_players"]
            )
            results.append(result)
        return results

    def _batch_simulate_fallback(
        self,
        matches: List[Dict]
    ) -> List[MatchResult]:
        """
        批量模拟 fallback（API 不可用时使用本地算法）
        
        Args:
            matches: 比赛信息列表
            
        Returns:
            MatchResult 列表
        """
        results = []
        for match in matches:
            result = self._generate_fallback_match_result(
                match["home_team"].id,
                match["away_team"].id,
                match["home_players"],
                match["away_players"],
                quick_mode=True
            )
            # 记录比赛数据
            home_player_ids = {p.id for p in match["home_players"]}
            away_player_ids = {p.id for p in match["away_players"]}
            self.record_match_result(match["home_team"].id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(match["away_team"].id, result.away_score, result.player_stats, away_player_ids)
            results.append(result)
        return results

    def build_trade_prompt(
        self,
        proposal: TradeProposal,
        offering_team: Team,
        receiving_team: Team,
        players_offered: List[Player],
        players_requested: List[Player],
        trade_history: Optional[List[str]] = None,
        receiving_roster: Optional[List[Player]] = None,
        offering_roster: Optional[List[Player]] = None
    ) -> str:
        """
        构建交易评估提示词
        
        让LLM模拟接收方球队的总经理角色，根据球队状态、球员价值、交易指数、
        位置构成等综合因素来决定是否接受交易。
        
        Args:
            proposal: 交易提案
            offering_team: 发起交易的球队
            receiving_team: 接收交易的球队
            players_offered: 提供的球员列表
            players_requested: 请求的球员列表
            trade_history: 历史交易记录（可选）
            receiving_roster: 接收方球队完整阵容（用于位置分析）
            offering_roster: 发起方球队完整阵容（用于位置分析）
            
        Returns:
            构建好的提示词
        """
        def format_player_value(player: Player) -> str:
            """格式化球员价值信息"""
            foreign_tag = "（外援）" if player.is_foreign else ""
            tags = "、".join(player.skill_tags) if player.skill_tags else "无"
            
            # 计算球员价值评估
            age_factor = "年轻有潜力" if player.age < 25 else ("巅峰期" if player.age < 30 else "经验丰富")
            
            # 交易指数解读
            if player.trade_index < 20:
                trade_status = "绝对核心（较难交易）"
            elif player.trade_index < 40:
                trade_status = "重要球员（需要高价值回报）"
            elif player.trade_index < 60:
                trade_status = "轮换球员（可以考虑交易）"
            elif player.trade_index < 80:
                trade_status = "边缘球员（愿意交易）"
            else:
                trade_status = "可随时交易"
            
            return (
                f"  【{player.name}】{foreign_tag}\n"
                f"    位置: {player.position} | 年龄: {player.age}（{age_factor}）\n"
                f"    总评: {player.overall} | 进攻: {player.offense} | 防守: {player.defense}\n"
                f"    三分: {player.three_point} | 篮板: {player.rebounding} | 传球: {player.passing}\n"
                f"    技术标签: {tags}\n"
                f"    交易价值指数: {player.trade_index}/100 - {trade_status}"
            )
        
        def get_team_status_desc(status: str) -> str:
            """获取球队状态描述"""
            status_map = {
                "contending": "争冠球队 - 追求即战力，愿意用未来换现在，对核心球员保护意识强",
                "rebuilding": "重建球队 - 追求年轻球员和选秀权，愿意交易老将换取未来资产",
                "stable": "稳定球队 - 寻求平衡发展，不会做出极端交易，注重阵容深度"
            }
            return status_map.get(status, "状态未知")
        
        def analyze_position_composition(roster: List[Player]) -> Dict[str, int]:
            """分析球队位置构成"""
            position_count = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
            for player in roster:
                pos = player.position.upper()
                if pos in position_count:
                    position_count[pos] += 1
            return position_count
        
        def format_position_composition(position_count: Dict[str, int]) -> str:
            """格式化位置构成信息"""
            position_names = {
                "PG": "控球后卫(PG)",
                "SG": "得分后卫(SG)", 
                "SF": "小前锋(SF)",
                "PF": "大前锋(PF)",
                "C": "中锋(C)"
            }
            parts = []
            for pos, name in position_names.items():
                count = position_count.get(pos, 0)
                parts.append(f"{name}: {count}人")
            return " | ".join(parts)
        
        def analyze_trade_position_impact(
            roster: List[Player],
            players_out: List[Player],
            players_in: List[Player]
        ) -> str:
            """分析交易对位置构成的影响"""
            # 当前位置构成
            current = analyze_position_composition(roster)
            
            # 计算交易后的位置构成
            after = current.copy()
            for p in players_out:
                pos = p.position.upper()
                if pos in after:
                    after[pos] = max(0, after[pos] - 1)
            for p in players_in:
                pos = p.position.upper()
                if pos in after:
                    after[pos] += 1
            
            # 分析变化
            changes = []
            position_names = {"PG": "控卫", "SG": "分卫", "SF": "小前", "PF": "大前", "C": "中锋"}
            for pos in ["PG", "SG", "SF", "PF", "C"]:
                diff = after[pos] - current[pos]
                if diff != 0:
                    change_str = f"+{diff}" if diff > 0 else str(diff)
                    changes.append(f"{position_names[pos]}{change_str}")
            
            if not changes:
                return "位置构成无变化"
            return "位置变化: " + ", ".join(changes)
        
        # 构建提示词 - 让LLM扮演接收方球队总经理
        prompt = f"""你现在是{receiving_team.name}的总经理。你需要根据球队当前状态和发展战略，评估是否接受这笔交易提案。

请站在{receiving_team.name}的角度，综合考虑以下因素做出决策：
- 球队当前状态（争冠/重建/稳定）
- 球员的交易价值指数（越低越是核心，越难放走）
- 球员能力值和年龄
- 交易是否符合球队发展方向
- 【重要】球队当前的位置构成和交易后的位置变化

"""
        
        prompt += "=" * 50 + "\n"
        prompt += "【交易提案详情】\n"
        prompt += f"发起方: {offering_team.name}（{offering_team.city}）\n"
        prompt += f"接收方（你的球队）: {receiving_team.name}（{receiving_team.city}）\n"
        prompt += "=" * 50 + "\n\n"
        
        # 接收方（你的球队）信息
        prompt += f"【你的球队 - {receiving_team.name}】\n"
        prompt += f"球队状态: {get_team_status_desc(receiving_team.status)}\n"
        
        # 添加接收方球队位置构成分析
        if receiving_roster:
            receiving_positions = analyze_position_composition(receiving_roster)
            prompt += f"当前阵容位置构成: {format_position_composition(receiving_positions)}\n"
            # 分析交易对位置的影响
            position_impact = analyze_trade_position_impact(
                receiving_roster, players_requested, players_offered
            )
            prompt += f"交易后{position_impact}\n"
        
        prompt += "\n对方想要的球员（你需要送出的）:\n"
        # 显示送出球员的位置汇总
        requested_positions = [p.position for p in players_requested]
        prompt += f"  📍 送出球员位置: {', '.join(requested_positions)}\n"
        for player in players_requested:
            prompt += format_player_value(player) + "\n"
        
        # 计算请求球员总价值
        requested_total = sum(p.overall for p in players_requested)
        requested_avg_age = sum(p.age for p in players_requested) / len(players_requested) if players_requested else 0
        requested_avg_trade_index = sum(p.trade_index for p in players_requested) / len(players_requested) if players_requested else 50
        prompt += f"送出球员总评合计: {requested_total} | 平均年龄: {requested_avg_age:.1f} | 平均交易价值指数: {requested_avg_trade_index:.1f}\n\n"
        
        # 发起方信息
        prompt += f"【对方球队 - {offering_team.name}】\n"
        prompt += f"球队状态: {get_team_status_desc(offering_team.status)}\n"
        prompt += "对方提供的球员（你将获得的）:\n"
        # 显示获得球员的位置汇总
        offered_positions = [p.position for p in players_offered]
        prompt += f"  📍 获得球员位置: {', '.join(offered_positions)}\n"
        for player in players_offered:
            prompt += format_player_value(player) + "\n"
        
        # 计算提供球员总价值
        offered_total = sum(p.overall for p in players_offered)
        offered_avg_age = sum(p.age for p in players_offered) / len(players_offered) if players_offered else 0
        offered_avg_trade_index = sum(p.trade_index for p in players_offered) / len(players_offered) if players_offered else 50
        prompt += f"获得球员总评合计: {offered_total} | 平均年龄: {offered_avg_age:.1f} | 平均交易价值指数: {offered_avg_trade_index:.1f}\n\n"
        
        # 历史交易记录
        if trade_history:
            prompt += "【近期交易历史参考】\n"
            for record in trade_history[-5:]:  # 只显示最近5条
                prompt += f"  - {record}\n"
            prompt += "\n"
        
        prompt += "=" * 50 + "\n"
        prompt += "【决策指南】\n"
        prompt += """
作为总经理，你需要考虑：

1. 交易价值指数的重要性：
   - 指数<20: 这是球队绝对核心，除非能力值持平或更高，否则不应交易
   - 指数20-40: 重要球员，需要获得有利的回报才考虑
   - 指数40-60: 可以考虑交易，但需要公平回报
   - 指数>60: 愿意交易，只要回报合理即可

2. 球队状态的影响：
   - 争冠球队：保护核心，追求即战力，不轻易交易主力
   - 重建球队：愿意用老将换年轻球员，但核心新星也要保护
   - 稳定球队：追求平衡，不做亏本交易

3. 【重要】位置构成的考量：
   - 检查交易后各位置是否有足够的球员轮换
   - 如果某位置只剩1人或0人，这是严重的阵容缺陷
   - 每个位置有2名球员就是人员充足
   - 如果获得的球员位置正好是球队薄弱环节，可以适当放宽条件
   - 如果送出的球员位置本就人手紧张，应该更加谨慎

4. 综合评估：
   - 即使交易价值指数低的球员，如果回报足够丰厚，也可以考虑
   - 即使交易价值指数高的球员，如果回报太差，也应该拒绝
   - 年龄、潜力、位置需求都是重要考量因素
   - 位置匹配度可以影响交易的接受意愿

"""
        prompt += "=" * 50 + "\n"
        prompt += "【输出要求】\n"
        prompt += "请按以下JSON格式输出你的决策（只输出JSON，不要其他内容）:\n"
        prompt += """```json
{
  "accepted": <true或false>,
  "reason": "<作为总经理的决策理由，说明为什么接受或拒绝这笔交易，要体现你对球队状态和球员价值的考量，50-150字>",
  "fairness_score": <这笔交易对你球队的公平性评分，1-10分，10分表示你占很大便宜，5分表示公平，1分表示你吃大亏>,
  "suggestions": "<如果拒绝，给出你愿意接受的交易修改建议；如果接受，可以为空>"
}
```
"""
        
        return prompt
    
    def get_trade_system_prompt(self) -> str:
        """获取交易评估的系统提示词"""
        return (
            "你是一个篮球球队的总经理。你需要站在自己球队的角度，"
            "根据球队状态、球员价值、交易指数和位置构成，决定是否接受交易提案。\n\n"
            "关键决策原则:\n"
            "1. 交易价值指数是球员对球队重要性的体现，指数越低越是核心\n"
            "2. 核心球员（指数<20）除非获得同等或更高能力值球员，否则不应轻易交易\n"
            "3. 球员能力值是最直观的回报因素，球员能力值的参考权重大于指数\n"
            "4. 争冠球队更看重即战力（能力值），重建球队偏向于年轻球员\n"
            "5. 即使是核心球员，如果对方开出的条件足够诱人，也可以考虑\n"
            "6. 【重要】位置构成是关键考量因素：\n"
            "   - 交易后某位置人数不足会严重影响球队运转\n"
            "   - 能力值是最重要的回报\n"
            "   - 如果获得的球员能补强薄弱位置，可以适当放宽条件\n"
            "   - 如果送出球员后某位置只剩1人或0人，应该拒绝交易\n"
            "7. 你的目标是让球队变得更好，而不是死守某个球员\n"
            "8. 交易难度和严格程度不能过高，公平性大于等于4都应该考虑接受\n"
            "9. 适当吃亏保持玩家良好的游玩体验"
            "10. 输出必须严格遵循JSON格式"
        )


    def parse_match_response(
        self,
        response: str,
        home_team_id: str,
        away_team_id: str,
        home_players: List[Player],
        away_players: List[Player]
    ) -> MatchResult:
        """
        解析比赛模拟响应
        
        使用StatsCalculator计算球队总分，确保比分与球员数据一致
        
        Args:
            response: LLM响应文本
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_players: 主队球员列表
            away_players: 客队球员列表
            
        Returns:
            MatchResult对象
        """
        try:
            # 尝试从响应中提取JSON
            json_data = self._extract_json(response)
            
            if json_data is None:
                print(f"⚠️ [LLM解析] 无法从响应中提取JSON数据")
                print(f"   响应内容前200字符: {response[:200]}...")
                raise ValueError("无法从响应中提取JSON数据")
            
            # 解析文本字段
            narrative = json_data.get("narrative", "比赛精彩激烈。")
            
            # 解析新增字段 - quarter_scores
            quarter_scores = []
            raw_quarters = json_data.get("quarter_scores", [])
            if raw_quarters and isinstance(raw_quarters, list):
                for q in raw_quarters:
                    if isinstance(q, (list, tuple)) and len(q) >= 2:
                        quarter_scores.append((int(q[0]), int(q[1])))
            
            # 解析新增字段 - highlights
            highlights = []
            raw_highlights = json_data.get("highlights", [])
            if raw_highlights and isinstance(raw_highlights, list):
                highlights = [str(h) for h in raw_highlights if h]
            
            # 解析新增字段 - commentary
            commentary = json_data.get("commentary", "")
            
            # 解析球员统计
            player_stats = {}
            raw_stats = json_data.get("player_stats", {})
            
            # 构建球员ID和名字的映射
            all_players = {p.id: p for p in home_players + away_players}
            player_name_to_id = {p.name: p.id for p in home_players + away_players}
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            
            matched_count = 0
            for player_key, stats in raw_stats.items():
                # 首先尝试直接匹配球员ID
                if player_key in all_players:
                    matched_count += 1
                    # 记录比赛时球员所属球队
                    player_team_id = all_players[player_key].team_id
                    player_stats[player_key] = GameStats(
                        points=max(0, min(60, int(stats.get("points", 0)))),
                        rebounds=max(0, min(30, int(stats.get("rebounds", 0)))),
                        assists=max(0, min(25, int(stats.get("assists", 0)))),
                        steals=max(0, min(10, int(stats.get("steals", 0)))),
                        blocks=max(0, min(10, int(stats.get("blocks", 0)))),
                        turnovers=max(0, min(15, int(stats.get("turnovers", 0)))),
                        minutes=max(0, min(48, int(stats.get("minutes", 0)))),
                        team_id=player_team_id
                    )
                # 如果ID不匹配，尝试使用球员名字匹配
                elif player_key in player_name_to_id:
                    actual_id = player_name_to_id[player_key]
                    matched_count += 1
                    # 记录比赛时球员所属球队
                    player_team_id = all_players[actual_id].team_id
                    player_stats[actual_id] = GameStats(
                        points=max(0, min(60, int(stats.get("points", 0)))),
                        rebounds=max(0, min(30, int(stats.get("rebounds", 0)))),
                        assists=max(0, min(25, int(stats.get("assists", 0)))),
                        steals=max(0, min(10, int(stats.get("steals", 0)))),
                        blocks=max(0, min(10, int(stats.get("blocks", 0)))),
                        turnovers=max(0, min(15, int(stats.get("turnovers", 0)))),
                        minutes=max(0, min(48, int(stats.get("minutes", 0)))),
                        team_id=player_team_id
                    )
                    print(f"   [LLM解析] 使用球员名字匹配: {player_key} -> {actual_id}")
            
            print(f"   [LLM解析] 解析到 {len(raw_stats)} 个球员数据，匹配 {matched_count} 个")
            
            # 如果没有匹配到任何球员，使用fallback
            if matched_count == 0 and len(raw_stats) > 0:
                print(f"⚠️ [LLM解析] 球员ID全部不匹配，使用fallback")
                print(f"   LLM返回的球员key: {list(raw_stats.keys())[:5]}...")
                print(f"   实际球员ID: {list(all_players.keys())[:5]}...")
                raise ValueError("球员ID不匹配")
            
            # 应用得分随机调整（两队各自选择模式）
            player_stats = StatsCalculator.apply_score_adjustment(
                player_stats, home_player_ids, away_player_ids
            )
            print(f"   [LLM解析] 已应用得分随机调整")
            
            # 使用StatsCalculator计算球队总分（确保比分与球员数据一致）
            home_score = StatsCalculator.calculate_team_score(player_stats, home_player_ids)
            away_score = StatsCalculator.calculate_team_score(player_stats, away_player_ids)
            
            # 验证并调整统计数据确保分数在合理范围内
            player_stats, home_score, away_score = StatsCalculator.validate_and_adjust_stats(
                player_stats, home_player_ids, away_player_ids
            )
            
            # 确保不是平局
            if home_score == away_score:
                home_score += 1
                # 给主队得分最高的球员加1分
                home_top_scorer = max(
                    [(pid, s) for pid, s in player_stats.items() if pid in home_player_ids],
                    key=lambda x: x[1].points,
                    default=(None, None)
                )
                if home_top_scorer[0]:
                    player_stats[home_top_scorer[0]].points += 1
            
            # 验证节次比分总和是否匹配总比分
            if quarter_scores:
                home_quarter_total = sum(q[0] for q in quarter_scores)
                away_quarter_total = sum(q[1] for q in quarter_scores)
                # 如果不匹配，重新生成节次比分
                if home_quarter_total != home_score or away_quarter_total != away_score:
                    quarter_scores = self._generate_quarter_scores_fallback(home_score, away_score)
            
            return MatchResult(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_score=home_score,
                away_score=away_score,
                narrative=narrative,
                player_stats=player_stats,
                quarter_scores=quarter_scores,
                highlights=highlights,
                commentary=commentary,
                home_player_ids=list(home_player_ids),  # 记录比赛时的球员列表
                away_player_ids=list(away_player_ids)   # 记录比赛时的球员列表
            )
            
        except Exception as e:
            # 解析失败，使用fallback
            print(f"⚠️ [LLM解析] 解析失败，使用fallback: {str(e)}")
            return self._generate_fallback_match_result(
                home_team_id, away_team_id, home_players, away_players
            )
    
    def parse_trade_response(self, response: str) -> Tuple[bool, str, int, str]:
        """
        解析交易评估响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            (是否接受, 理由, 公平性评分, 建议) 元组
        """
        try:
            json_data = self._extract_json(response)
            
            if json_data is None:
                raise ValueError("无法从响应中提取JSON数据")
            
            accepted = bool(json_data.get("accepted", False))
            reason = json_data.get("reason", "交易评估完成。")
            fairness_score = max(1, min(10, int(json_data.get("fairness_score", 5))))
            suggestions = json_data.get("suggestions", "")
            
            return accepted, reason, fairness_score, suggestions
            
        except Exception as e:
            # 解析失败，使用fallback（默认拒绝）
            return False, "交易评估系统暂时无法处理此请求。", 5, "请稍后重试。"
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取JSON数据
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            解析后的字典，失败返回None
        """
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试从markdown代码块中提取
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # 尝试找到JSON对象
        brace_pattern = r'\{[\s\S]*\}'
        matches = re.findall(brace_pattern, text)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _generate_fallback_match_result(
        self,
        home_team_id: str,
        away_team_id: str,
        home_players: List[Player],
        away_players: List[Player],
        quick_mode: bool = False
    ) -> MatchResult:
        """
        生成fallback比赛结果（当LLM调用失败时使用）
        
        使用StatsCalculator基于球员能力值生成统计数据
        确保比分一致性：球队总分 = 球员得分之和
        
        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            home_players: 主队球员列表
            away_players: 客队球员列表
            quick_mode: 是否为快速模式（不生成解说文本）
            
        Returns:
            基于球员能力值随机生成的MatchResult，保证比分一致性
        """
        # 使用StatsCalculator生成球队统计数据
        home_player_stats, _ = StatsCalculator.generate_team_stats(home_players)
        away_player_stats, _ = StatsCalculator.generate_team_stats(away_players)
        
        # 获取球员ID集合
        home_player_ids = set(home_player_stats.keys())
        away_player_ids = set(away_player_stats.keys())
        
        # 合并球员统计
        player_stats = {**home_player_stats, **away_player_stats}
        
        # 应用得分随机调整（两队各自选择模式）
        player_stats = StatsCalculator.apply_score_adjustment(
            player_stats, home_player_ids, away_player_ids
        )
        
        # 使用validate_and_adjust_stats确保分数在合理范围内并保持一致性
        player_stats, home_score, away_score = StatsCalculator.validate_and_adjust_stats(
            player_stats, home_player_ids, away_player_ids
        )
        
        # 确保不是平局
        if home_score == away_score:
            # 根据球队平均总评决定谁加分
            home_avg = sum(p.overall for p in home_players) / len(home_players) if home_players else 70
            away_avg = sum(p.overall for p in away_players) / len(away_players) if away_players else 70
            
            if home_avg >= away_avg:
                home_score += 1
                # 给主队得分最高的球员加1分
                home_top = max(
                    [(pid, s) for pid, s in player_stats.items() if pid in home_player_ids],
                    key=lambda x: x[1].points,
                    default=(None, None)
                )
                if home_top[0]:
                    player_stats[home_top[0]].points += 1
            else:
                away_score += 1
                away_top = max(
                    [(pid, s) for pid, s in player_stats.items() if pid in away_player_ids],
                    key=lambda x: x[1].points,
                    default=(None, None)
                )
                if away_top[0]:
                    player_stats[away_top[0]].points += 1
        
        # 快速模式不生成解说文本
        if quick_mode:
            return MatchResult(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_score=home_score,
                away_score=away_score,
                narrative="",
                player_stats=player_stats,
                quarter_scores=[],
                highlights=[],
                commentary="",
                home_player_ids=list(home_player_ids),  # 记录比赛时的球员列表
                away_player_ids=list(away_player_ids)   # 记录比赛时的球员列表
            )
        
        # 完整模式生成解说文本
        quarter_scores = self._generate_quarter_scores_fallback(home_score, away_score)
        highlights = self._generate_highlights_fallback(
            home_players, away_players, player_stats, home_score, away_score
        )
        
        winner_team = "主队" if home_score > away_score else "客队"
        narrative = f"比赛结束，最终比分{home_score}:{away_score}。{winner_team}凭借出色的团队配合赢得比赛。"
        
        commentary = self._generate_commentary_fallback(
            home_score, away_score, quarter_scores, highlights
        )
        
        return MatchResult(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            narrative=narrative,
            player_stats=player_stats,
            quarter_scores=quarter_scores,
            highlights=highlights,
            commentary=commentary,
            home_player_ids=list(home_player_ids),  # 记录比赛时的球员列表
            away_player_ids=list(away_player_ids)   # 记录比赛时的球员列表
        )
    
    def _generate_quarter_scores_fallback(self, home_total: int, away_total: int) -> List[tuple]:
        """生成节次比分（fallback）"""
        ratios = [0.22, 0.26, 0.26, 0.26]
        
        home_quarters = []
        away_quarters = []
        home_remaining = home_total
        away_remaining = away_total
        
        for i in range(4):
            if i < 3:
                home_q = int(home_total * ratios[i] * random.uniform(0.85, 1.15))
                away_q = int(away_total * ratios[i] * random.uniform(0.85, 1.15))
                home_q = min(home_q, home_remaining - (3 - i) * 15)
                away_q = min(away_q, away_remaining - (3 - i) * 15)
                home_q = max(home_q, 15)
                away_q = max(away_q, 15)
            else:
                home_q = home_remaining
                away_q = away_remaining
            
            home_quarters.append(home_q)
            away_quarters.append(away_q)
            home_remaining -= home_q
            away_remaining -= away_q
        
        return list(zip(home_quarters, away_quarters))
    
    def _generate_highlights_fallback(
        self,
        home_players: List[Player],
        away_players: List[Player],
        player_stats: dict,
        home_score: int,
        away_score: int
    ) -> List[str]:
        """生成精彩时刻（fallback）"""
        highlights = []
        
        # 找出得分最高的球员
        top_scorer = None
        top_points = 0
        for player_id, stats in player_stats.items():
            if stats.points > top_points:
                top_points = stats.points
                for p in home_players + away_players:
                    if p.id == player_id:
                        top_scorer = p
                        break
        
        if top_scorer:
            highlights.append(f"{top_scorer.name}砍下全场最高{top_points}分。")
        
        # 比分差距描述
        score_diff = abs(home_score - away_score)
        if score_diff >= 20:
            highlights.append("一场实力悬殊的比赛，胜者展现了强大的统治力。")
        elif score_diff <= 5:
            highlights.append("比赛悬念保持到最后一刻，双方战至最后。")
        else:
            highlights.append("双方你来我往，比赛精彩纷呈。")
        
        highlights.append("两队球员都展现了出色的竞技状态。")
        
        return highlights
    
    def _generate_commentary_fallback(
        self,
        home_score: int,
        away_score: int,
        quarter_scores: List[tuple],
        highlights: List[str]
    ) -> str:
        """生成解说文本（fallback）"""
        lines = ["比赛开始，双方球员进入状态。"]
        
        quarter_names = ["第一节", "第二节", "第三节", "第四节"]
        home_running = 0
        away_running = 0
        
        for i, (home_q, away_q) in enumerate(quarter_scores):
            home_running += home_q
            away_running += away_q
            if home_q > away_q:
                lines.append(f"{quarter_names[i]}主队占据优势，本节赢了{home_q - away_q}分。")
            else:
                lines.append(f"{quarter_names[i]}客队表现更好，本节赢了{away_q - home_q}分。")
        
        for highlight in highlights:
            lines.append(highlight)
        
        winner = "主队" if home_score > away_score else "客队"
        lines.append(f"比赛结束，{winner}以{max(home_score, away_score)}:{min(home_score, away_score)}赢得胜利。")
        
        return "\n".join(lines)
    
    def simulate_match_full(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        match_context: Optional[str] = None,
        use_llm: bool = True
    ) -> MatchResult:
        """
        完整比赛模拟 - 用于玩家球队比赛
        
        生成完整比赛数据，包括:
        - narrative: 比赛过程描述
        - commentary: 完整解说文本
        - highlights: 精彩时刻列表
        - quarter_scores: 四节比分
        - player_stats: 球员统计数据
        
        使用StatsCalculator计算球队总分，确保比分与球员数据一致
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            match_context: 比赛背景信息
            use_llm: 是否使用LLM（False则使用fallback）
            
        Returns:
            MatchResult对象（包含完整解说文本）
        """
        if not use_llm or not self.api_key:
            print(f"⚠️ [LLM] 完整模拟跳过LLM: use_llm={use_llm}, api_key={'已配置' if self.api_key else '未配置'}")
            result = self._generate_fallback_match_result(
                home_team.id, away_team.id, home_players, away_players,
                quick_mode=False
            )
            # 记录比赛数据供下一场参考
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            return result
        
        try:
            print(f"🤖 [LLM] 完整模拟比赛: {home_team.name} vs {away_team.name}")
            prompt = self.build_match_prompt(
                home_team, away_team, home_players, away_players, match_context
            )
            system_prompt = self.get_match_system_prompt()
            
            response = self.chat(prompt, system_prompt)
            print(f"✅ [LLM] 收到响应，正在解析...")
            
            result = self.parse_match_response(
                response, home_team.id, away_team.id, home_players, away_players
            )
            print(f"✅ [LLM] 解析成功: {result.home_score}:{result.away_score}, 球员数据: {len(result.player_stats)}人")
            
            # 记录比赛数据供下一场参考
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            
            return result
            
        except Exception as e:
            # LLM调用失败，使用fallback
            print(f"⚠️ [LLM] 完整模拟失败，使用本地算法: {home_team.name} vs {away_team.name}")
            print(f"   错误信息: {str(e)}")
            result = self._generate_fallback_match_result(
                home_team.id, away_team.id, home_players, away_players,
                quick_mode=False
            )
            # 记录比赛数据供下一场参考
            home_player_ids = {p.id for p in home_players}
            away_player_ids = {p.id for p in away_players}
            self.record_match_result(home_team.id, result.home_score, result.player_stats, home_player_ids)
            self.record_match_result(away_team.id, result.away_score, result.player_stats, away_player_ids)
            return result
    
    def simulate_match(
        self,
        home_team: Team,
        away_team: Team,
        home_players: List[Player],
        away_players: List[Player],
        match_context: Optional[str] = None,
        use_llm: bool = True
    ) -> MatchResult:
        """
        模拟比赛（向后兼容接口，调用simulate_match_full）
        
        Args:
            home_team: 主队
            away_team: 客队
            home_players: 主队球员列表
            away_players: 客队球员列表
            match_context: 比赛背景信息
            use_llm: 是否使用LLM（False则使用fallback）
            
        Returns:
            MatchResult对象
        """
        return self.simulate_match_full(
            home_team, away_team, home_players, away_players,
            match_context, use_llm
        )
    
    def evaluate_trade(
        self,
        proposal: TradeProposal,
        offering_team: Team,
        receiving_team: Team,
        players_offered: List[Player],
        players_requested: List[Player],
        trade_history: Optional[List[str]] = None,
        use_llm: bool = True,
        receiving_roster: Optional[List[Player]] = None,
        offering_roster: Optional[List[Player]] = None
    ) -> Tuple[bool, str, int, str]:
        """
        评估交易（高级接口）
        
        Args:
            proposal: 交易提案
            offering_team: 发起交易的球队
            receiving_team: 接收交易的球队
            players_offered: 提供的球员列表
            players_requested: 请求的球员列表
            trade_history: 历史交易记录
            use_llm: 是否使用LLM
            receiving_roster: 接收方球队完整阵容（用于位置分析）
            offering_roster: 发起方球队完整阵容（用于位置分析）
            
        Returns:
            (是否接受, 理由, 公平性评分, 建议) 元组
        """
        if not use_llm or not self.api_key:
            print("ℹ️  使用本地算法评估交易")
            return self._evaluate_trade_fallback(
                players_offered, players_requested, offering_team, receiving_team
            )
        
        print("🤖 使用LLM评估交易...")
        try:
            prompt = self.build_trade_prompt(
                proposal, offering_team, receiving_team,
                players_offered, players_requested, trade_history,
                receiving_roster=receiving_roster,
                offering_roster=offering_roster
            )
            system_prompt = self.get_trade_system_prompt()
            
            response = self.chat(prompt, system_prompt)
            
            result = self.parse_trade_response(response)
            print("✅ LLM评估成功")
            return result
            
        except Exception as e:
            # LLM调用失败，使用fallback
            print(f"\n⚠️  警告：LLM交易评估失败，使用本地算法")
            print(f"   错误信息: {str(e)}")
            print(f"   提示：请检查API配置和网络连接\n")
            return self._evaluate_trade_fallback(
                players_offered, players_requested, offering_team, receiving_team
            )
    
    def _evaluate_trade_fallback(
        self,
        players_offered: List[Player],
        players_requested: List[Player],
        offering_team: Team,
        receiving_team: Team
    ) -> Tuple[bool, str, int, str]:
        """
        交易评估fallback逻辑
        
        基于简单规则评估交易是否合理
        """
        # 计算双方球员总价值
        offered_value = sum(p.overall for p in players_offered)
        requested_value = sum(p.overall for p in players_requested)
        
        # 计算价值差异
        value_diff = abs(offered_value - requested_value)
        total_value = offered_value + requested_value
        diff_ratio = value_diff / total_value if total_value > 0 else 0
        
        # 检查核心球员
        has_core_player = any(p.trade_index < 30 for p in players_requested)
        
        # 计算公平性评分
        fairness_score = int(10 - (diff_ratio * 20))
        fairness_score = max(1, min(10, fairness_score))
        
        # 决定是否接受
        if has_core_player:
            # 核心球员需要更高的溢价
            accepted = diff_ratio < 0.05 and offered_value > requested_value * 1.1
            reason = "涉及核心球员，需要更高的交易价值。" if not accepted else "交易价值合理，核心球员获得了足够的回报。"
        elif diff_ratio > 0.15:
            accepted = False
            reason = f"交易价值差异过大（{diff_ratio*100:.1f}%），不够公平。"
        else:
            # 加入一定随机性
            accepted = random.random() < (0.7 - diff_ratio)
            reason = "交易价值基本对等。" if accepted else "球队目前不考虑这笔交易。"
        
        suggestions = "" if accepted else "建议调整交易筹码，使双方价值更加对等。"
        
        return accepted, reason, fairness_score, suggestions
