"""
华夏篮球联赛教练模拟器 - 外援市场系统

负责外援球探搜索、生成外援球员等功能
替代原有的自由球员市场
"""
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from src.models import Player, Team
from src.player_data_manager import PlayerDataManager, calculate_overall
from src.llm_interface import LLMInterface


# 外援市场配置
SCOUT_COST = 20  # 普通球探搜索费用（万元）
TARGETED_SCOUT_COST = 50  # 定向搜索费用（万元）
INITIAL_BUDGET = 1000  # 初始经费（万元）
WIN_REWARD_MIN = 5  # 赢球奖励最小值（万元）
WIN_REWARD_MAX = 15  # 赢球奖励最大值（万元）
LOSE_REWARD_MIN = 2  # 输球奖励最小值（万元）
LOSE_REWARD_MAX = 5  # 输球奖励最大值（万元）

# 外援工资上限（万元）
MAX_SALARY = 300

# 外援数量上限
MAX_FOREIGN_PLAYERS = 4

# 搜索结果有效期配置
SCOUT_RESULT_EXPIRY_DAYS = 20  # 搜索结果有效期（天）

# 赞助系统配置
SPONSOR_COOLDOWN_DAYS = 5  # 赞助冷却天数
SPONSOR_MIN_AMOUNT = 10  # 赞助最小金额（万元）
SPONSOR_MAX_AMOUNT = 100  # 赞助最大金额（万元）

# 赞助金额概率分布（加权随机）
# 格式: (金额范围, 权重) - 权重越高越容易获得
SPONSOR_AMOUNT_WEIGHTS = [
    ((10, 29), 40),   # 10-29万: 40% 概率
    ((30, 49), 30),   # 30-49万: 30% 概率
    ((50, 69), 15),   # 50-69万: 15% 概率
    ((70, 79), 10),   # 70-79万: 10% 概率
    ((80, 100), 5),   # 80-100万: 5% 概率（极低）
]

# 外援能力值范围
FOREIGN_OVERALL_MIN = 86
FOREIGN_OVERALL_MAX = 96

# 定向搜索能力值下限
TARGETED_OVERALL_MIN = 88

# 外援能力值概率分布（加权随机）- 普通搜索
# 格式: (能力值范围, 权重) - 权重越高越容易抽到
FOREIGN_OVERALL_WEIGHTS = [
    ((86, 88), 55),   # 86-88: 40% 概率
    ((89, 90), 20),   # 89-90: 25% 概率
    ((90, 91), 15),   # 90-91: 20% 概率
    ((92, 93), 7),   # 92-93: 10% 概率
    ((94, 95), 2.5),    # 94-95: 4% 概率
    ((96, 96), 0.5),    # 96-97: 1% 概率（极低）
]

# 定向搜索能力值概率分布（保证≥88）
TARGETED_OVERALL_WEIGHTS = [
    ((88, 90), 70),   # 88-90: 65% 概率
    ((91, 91), 15),   # 90-91: 20% 概率
    ((92, 92), 9),   # 92-93: 10% 概率
    ((93, 93), 4),    # 94-95: 4% 概率
    ((94, 94), 1),    # 96-97: 1% 概率
    ((95, 95), 0.5),    # 96-97: 1% 概率
    ((96, 96), 0.5),    # 96-97: 1% 概率
]

# 工资与能力值关系配置
# 70%概率工资与能力值正相关，30%概率随机
SALARY_CORRELATION_PROBABILITY = 0.70

# 位置列表
POSITIONS = ["PG", "SG", "SF", "PF", "C"]

# 过往经历模板（按能力值区间）
CAREER_BACKGROUNDS = {
    "elite": [  # 95-96
        "曾在NBA效力6个赛季，巅峰期场均贡献18分5篮板，两次入选全明星替补阵容。因伤病困扰选择来到华夏篮球联赛寻求新的挑战，希望在这里重新证明自己的价值。",
        "2015年NBA首轮第18顺位被选中，先后效力于三支NBA球队，生涯场均12.5分。上赛季因球队重建被裁，决定来到华夏篮球联赛展现自己的实力。",
        "欧洲篮球联赛两届MVP得主，曾代表国家队征战世界杯并打入八强。在欧洲联赛场均22分被誉为'欧洲乔丹'，本赛季首次来到亚洲联赛。",
        "NBA总冠军成员，在夺冠赛季担任球队重要轮换，季后赛场均贡献9分4篮板。拥有丰富的大赛经验，是球队更衣室的精神领袖。"
    ],
    "high": [  # 93-94
        "NBA边缘球员，在联盟打拼4年，大部分时间在NBA与发展联盟之间往返。发展联盟时期是绝对核心，场均25分，曾获得发展联盟全明星MVP。",
        "欧洲顶级联赛西班牙ACB联赛的核心后卫，连续三个赛季场均得分超过15分。曾多次参加NBA夏季联赛试训，但未能获得稳定合同。",
        "2018年NBA二轮第45顺位被选中，在发展联盟磨练多年，技术日趋成熟。上赛季在发展联盟场均18分6助攻，是联盟最佳控卫之一。",
        "澳洲NBL联赛MVP，带领球队打入总决赛。身体素质出众，运动能力爆表，被球探评价为'最接近NBA水平的NBL球员'。"
    ],
    "medium": [  # 89-92
        "发展联盟得分王，上赛季场均轰下28.5分，曾被NBA球队召回打了15场比赛。投射能力出色，三分命中率稳定在38%以上，是纯粹的得分手。",
        "欧洲联赛法国Pro B联赛的绝对核心，场均20分8篮板。曾参加NBA选秀但落选，随后在欧洲联赛证明自己，多次获得联赛周最佳。",
        "澳洲NBL联赛全明星球员，在联赛效力三个赛季，场均15分5篮板。防守积极，篮球智商高，是球队攻防转换的关键人物。",
        "职业生涯辗转多个国家联赛，曾在菲律宾PBA、韩国KBL、日本B联赛效力。经验丰富，适应能力强，在每个联赛都能快速融入球队体系。"
    ],
    "low": [  # 85-86
        "发展联盟球员，过去两个赛季稳定出场，场均贡献10分3篮板。虽然未能获得NBA机会，但一直保持良好的职业态度和训练习惯。",
        "欧洲联赛德国Pro A联赛主力球员，场均12分4助攻。组织能力不错，能够串联球队进攻，是一名稳定的角色球员。",
        "澳洲NBL联赛球员，主要负责防守对方核心后卫。虽然进攻端数据不突出，但防守强度和比赛态度得到教练组的高度认可。",
        "NCAA一级联赛明星球员，大四赛季场均19分入选全美最佳阵容。选秀落选后在海外联赛寻求机会，渴望通过华夏篮球联赛平台证明自己的实力。"
    ]
}

# 技术标签池
SKILL_TAGS_POOL = {
    "PG": ["组织大师", "突破高手", "控场能力", "传球视野", "快攻发起者", "防守尖兵"],
    "SG": ["得分机器", "三分射手", "关键先生", "无球跑动", "后卫终结者", "外线防守"],
    "SF": ["全能前锋", "锋线摇摆人", "攻防一体", "篮板能力", "单打高手", "快攻终结"],
    "PF": ["内线强攻", "篮板怪兽", "空间四号位", "护筐能力", "挡拆高手", "二次进攻"],
    "C": ["护筐高手", "篮板机器", "内线支柱", "挡拆终结", "防守核心", "低位单打"]
}


@dataclass
class ScoutResult:
    """球探搜索结果"""
    player: Player
    career_background: str  # 过往经历介绍
    scouting_report: str  # 球探报告
    salary: int = 0  # 工资（万元）
    visible_attributes: List[str] = field(default_factory=list)  # 公开显示的3项能力值名称
    is_targeted_search: bool = False  # 是否为定向搜索
    scout_date: str = ""  # 搜索日期 (YYYY-MM-DD格式)
    expiry_date: str = ""  # 过期日期 (YYYY-MM-DD格式)


class ForeignMarket:
    """外援市场系统"""
    
    def __init__(
        self,
        data_manager: PlayerDataManager,
        llm_interface: Optional[LLMInterface] = None
    ):
        """
        初始化外援市场
        
        Args:
            data_manager: 球员数据管理器
            llm_interface: LLM接口（用于生成球员信息）
        """
        self.data_manager = data_manager
        self.llm_interface = llm_interface
        
        # 当前搜索到的外援列表（支持多个外援同时存在）
        self.scouted_players: List[ScoutResult] = []
        
        # 保留旧属性用于兼容（指向列表中第一个元素）
        self.scouted_player: Optional[ScoutResult] = None
        
        # 已生成的外援ID计数器
        self._foreign_player_counter = 0
        
        # 已使用的完整名字集合（用于保证名字不重复）
        self._used_full_names: set = set()
        
        # 名字生成计数器（用于增加随机性）
        self._name_counter = 0
        
        # 赞助系统：上次拉赞助的日期
        self._last_sponsor_date: Optional[str] = None
    
    def get_scout_cost(self, targeted: bool = False) -> int:
        """获取球探搜索费用"""
        return TARGETED_SCOUT_COST if targeted else SCOUT_COST
    
    def can_scout(self, team: Team, targeted: bool = False) -> Tuple[bool, str]:
        """
        检查球队是否可以进行球探搜索
        
        Args:
            team: 球队对象
            targeted: 是否为定向搜索
            
        Returns:
            (是否可以搜索, 原因)
        """
        cost = self.get_scout_cost(targeted)
        if team.budget < cost:
            return False, f"经费不足，需要{cost}万元，当前{team.budget}万元"
        return True, "可以进行球探搜索"
    
    def scout_foreign_player(
        self,
        team: Team,
        use_llm: bool = True,
        targeted: bool = False,
        target_position: Optional[str] = None,
        current_date: Optional[str] = None
    ) -> Tuple[bool, str, Optional[ScoutResult]]:
        """
        进行球探搜索，生成一名外援
        
        Args:
            team: 进行搜索的球队
            use_llm: 是否使用LLM生成球员信息
            targeted: 是否为定向搜索（50万，指定位置，能力值≥88）
            target_position: 定向搜索的目标位置（仅targeted=True时有效）
            current_date: 当前游戏日期 (YYYY-MM-DD格式)，用于计算有效期
            
        Returns:
            (是否成功, 消息, 搜索结果)
        """
        # 检查定向搜索参数
        if targeted and target_position not in POSITIONS:
            return False, f"无效的位置，请选择: {', '.join(POSITIONS)}", None
        
        # 检查是否可以搜索
        can_search, reason = self.can_scout(team, targeted)
        if not can_search:
            return False, reason, None
        
        # 扣除费用
        cost = self.get_scout_cost(targeted)
        team.budget -= cost
        
        # 生成外援
        if use_llm and self.llm_interface:
            result = self._generate_foreign_player_with_llm(targeted, target_position)
        else:
            result = self._generate_foreign_player_local(targeted, target_position)
        
        # 设置搜索日期和过期日期
        if current_date:
            result.scout_date = current_date
            result.expiry_date = self._calculate_expiry_date(current_date)
        
        # 添加到搜索结果列表
        self.scouted_players.append(result)
        
        # 保持向后兼容
        self.scouted_player = result
        
        search_type = "定向搜索" if targeted else "球探搜索"
        return True, f"{search_type}成功！花费{cost}万元，该外援将在市场中保留{SCOUT_RESULT_EXPIRY_DAYS}天", result
    
    def _calculate_expiry_date(self, scout_date: str) -> str:
        """
        计算搜索结果的过期日期
        
        Args:
            scout_date: 搜索日期 (YYYY-MM-DD格式)
            
        Returns:
            过期日期 (YYYY-MM-DD格式)
        """
        from datetime import datetime, timedelta
        date = datetime.strptime(scout_date, "%Y-%m-%d")
        expiry = date + timedelta(days=SCOUT_RESULT_EXPIRY_DAYS)
        return expiry.strftime("%Y-%m-%d")
    
    def check_and_expire_scouted_players(self, current_date: str) -> List[str]:
        """
        检查并清理过期的搜索结果
        
        Args:
            current_date: 当前游戏日期 (YYYY-MM-DD格式)
            
        Returns:
            过期被清理的外援名字列表
        """
        from datetime import datetime
        current = datetime.strptime(current_date, "%Y-%m-%d")
        
        expired_names = []
        remaining_players = []
        
        for result in self.scouted_players:
            if result.expiry_date:
                expiry = datetime.strptime(result.expiry_date, "%Y-%m-%d")
                if current > expiry:
                    expired_names.append(result.player.name)
                    continue
            remaining_players.append(result)
        
        self.scouted_players = remaining_players
        
        # 更新向后兼容属性
        self.scouted_player = self.scouted_players[0] if self.scouted_players else None
        
        return expired_names
    
    def clear_all_scouted_players(self) -> List[str]:
        """
        清理所有搜索到的外援（进入季后赛时调用）
        
        Returns:
            被清理的外援名字列表
        """
        cleared_names = [result.player.name for result in self.scouted_players]
        self.scouted_players = []
        self.scouted_player = None
        return cleared_names
    
    def get_scouted_player_remaining_days(self, player_id: str, current_date: str) -> int:
        """
        获取搜索结果的剩余有效天数
        
        Args:
            player_id: 外援球员ID
            current_date: 当前游戏日期 (YYYY-MM-DD格式)
            
        Returns:
            剩余天数，-1表示未找到该球员
        """
        from datetime import datetime
        
        for result in self.scouted_players:
            if result.player.id == player_id:
                if not result.expiry_date:
                    return SCOUT_RESULT_EXPIRY_DAYS  # 没有过期日期则返回默认值
                current = datetime.strptime(current_date, "%Y-%m-%d")
                expiry = datetime.strptime(result.expiry_date, "%Y-%m-%d")
                remaining = (expiry - current).days
                return max(0, remaining)
        
        return -1
    
    def get_all_scouted_players(self) -> List[ScoutResult]:
        """
        获取所有当前搜索到的外援
        
        Returns:
            搜索结果列表
        """
        return self.scouted_players
    
    def get_scouted_player_by_id(self, player_id: str) -> Optional[ScoutResult]:
        """
        根据球员ID获取搜索结果
        
        Args:
            player_id: 外援球员ID
            
        Returns:
            搜索结果，或None
        """
        for result in self.scouted_players:
            if result.player.id == player_id:
                return result
        return None
    
    def _generate_foreign_player_local(
        self,
        targeted: bool = False,
        target_position: Optional[str] = None
    ) -> ScoutResult:
        """使用本地算法生成外援"""
        # 使用加权随机生成总能力值
        overall = self._generate_weighted_overall(targeted)
        
        # 根据能力值确定经历等级
        if overall >= 95:
            career_level = "elite"
        elif overall >= 93:
            career_level = "high"
        elif overall >= 89:
            career_level = "medium"
        else:
            career_level = "low"
        
        # 选择位置（定向搜索使用指定位置）
        if targeted and target_position:
            position = target_position
        else:
            position = random.choice(POSITIONS)
        
        # 生成细项能力值（围绕总评波动）
        base = overall
        offense = self._random_attribute(base, 10)
        defense = self._random_attribute(base - 5, 15)
        three_point = self._random_attribute(base - 3, 12)
        rebounding = self._random_attribute(base - 8, 20)
        passing = self._random_attribute(base - 5, 15)
        stamina = self._random_attribute(base, 8)
        
        # 根据位置调整属性
        if position in ["PG", "SG"]:
            passing = self._random_attribute(base + 5, 10)
            rebounding = self._random_attribute(base - 15, 15)
        elif position in ["PF", "C"]:
            rebounding = self._random_attribute(base + 5, 10)
            passing = self._random_attribute(base - 10, 15)
        
        # 生成球员ID
        self._foreign_player_counter += 1
        player_id = f"foreign_{self._foreign_player_counter:04d}"
        
        # 生成名字（使用常见外援名字模板）
        name = self._generate_foreign_name()
        
        # 随机年龄（25-35岁）
        age = random.randint(25, 35)
        
        # 选择技术标签
        position_tags = SKILL_TAGS_POOL.get(position, SKILL_TAGS_POOL["SF"])
        skill_tags = random.sample(position_tags, min(3, len(position_tags)))
        
        # 选择过往经历（经历强弱不完全与能力值成正比）
        career_background = self._generate_career_background(overall, career_level)
        
        # 创建球员对象
        player = Player(
            id=player_id,
            name=name,
            team_id="",  # 未签约
            position=position,
            age=age,
            is_foreign=True,
            offense=offense,
            defense=defense,
            three_point=three_point,
            rebounding=rebounding,
            passing=passing,
            stamina=stamina,
            overall=overall,
            skill_tags=skill_tags,
            trade_index=30  # 外援交易指数较低
        )
        
        # 生成工资（70%概率与能力值正相关）
        salary = self._generate_salary(overall)
        
        # 随机选择3项公开的能力值
        visible_attributes = self._select_visible_attributes()
        
        # 生成球探报告（不包含总评）
        scouting_report = self._generate_scouting_report_hidden(
            player, career_background, visible_attributes, salary
        )
        
        return ScoutResult(
            player=player,
            career_background=career_background,
            scouting_report=scouting_report,
            salary=salary,
            visible_attributes=visible_attributes,
            is_targeted_search=targeted
        )
    
    def _generate_career_background(self, overall: int, career_level: str) -> str:
        """
        生成过往经历，经历强弱不完全与能力值成正比
        
        有20%概率选择相邻等级的经历，增加不确定性
        """
        levels = ["low", "medium", "high", "elite"]
        current_idx = levels.index(career_level)
        
        # 20%概率选择相邻等级的经历
        if random.random() < 0.20 and len(levels) > 1:
            if current_idx == 0:
                # 最低等级只能往上
                selected_level = levels[1]
            elif current_idx == len(levels) - 1:
                # 最高等级只能往下
                selected_level = levels[-2]
            else:
                # 中间等级随机上下
                selected_level = levels[current_idx + random.choice([-1, 1])]
        else:
            selected_level = career_level
        
        return random.choice(CAREER_BACKGROUNDS[selected_level])
    
    def _generate_salary(self, overall: int) -> int:
        """
        生成外援工资
        
        70%概率工资与能力值正相关
        30%概率随机（便宜的可能能力高，贵的可能能力低）
        """
        if random.random() < SALARY_CORRELATION_PROBABILITY:
            # 正相关：能力值越高，工资越高
            # 86-97 映射到 80-300万
            base_salary = int(80 + (overall - 86) * (220 / 11))
            # 添加一些随机波动 ±20%
            variance = int(base_salary * 0.2)
            salary = base_salary + random.randint(-variance, variance)
        else:
            # 随机工资
            salary = random.randint(80, MAX_SALARY)
        
        # 确保在有效范围内
        return max(80, min(MAX_SALARY, salary))
    
    def _select_visible_attributes(self) -> List[str]:
        """随机选择3项公开显示的能力值"""
        all_attributes = ["offense", "defense", "three_point", "rebounding", "passing", "stamina"]
        return random.sample(all_attributes, 3)
    
    def _generate_weighted_overall(self, targeted: bool = False) -> int:
        """
        使用加权随机生成外援总能力值
        
        普通搜索概率分布：
        - 86-88: 40% (大概率)
        - 89-90: 25%
        - 90-91: 20%
        - 92-93: 10% (小概率)
        - 94-95: 4%
        - 96-97: 1% (极低概率)
        
        定向搜索概率分布（保证≥88）：
        - 88-90: 65%
        - 90-91: 20%
        - 92-93: 10%
        - 94-95: 4%
        - 96-97: 1%
        """
        # 选择对应的权重表
        weights_table = TARGETED_OVERALL_WEIGHTS if targeted else FOREIGN_OVERALL_WEIGHTS
        
        # 构建加权列表
        ranges = []
        weights = []
        for (min_val, max_val), weight in weights_table:
            ranges.append((min_val, max_val))
            weights.append(weight)
        
        # 根据权重选择一个范围
        selected_range = random.choices(ranges, weights=weights, k=1)[0]
        
        # 在选中的范围内随机选择一个值
        return random.randint(selected_range[0], selected_range[1])
    
    def _random_attribute(self, base: int, variance: int) -> int:
        """生成围绕基准值波动的属性值"""
        value = base + random.randint(-variance, variance)
        return max(50, min(99, value))
    
    def _generate_foreign_name(self) -> str:
        """生成外援名字，按篮球强势地区分配权重，确保完整名字不重复"""
        # 增加计数器
        self._name_counter += 1
        
        # 美国名字池（篮球最强，占比最大，避免NBA球星真名）
        us_first_names = [
            "马库斯", "泰勒", "布兰登", "贾马尔", "德里克", "特雷",
            "多诺万", "杰森", "肯尼", "朱利叶斯", "埃里克", "泰伦斯",
            "雷吉", "特里", "兰斯", "内特", "昆西", "德文",
            "贾斯汀", "特拉维斯", "达雷尔", "罗德尼", "克利福德", "韦恩",
            "德隆", "拉肖恩", "泰瑞克", "贾伦", "马尔科姆", "德文特",
            "谢尔顿", "拉沃恩", "特伦斯", "达里尔", "柯蒂斯", "沃伦",
            "安德鲁", "乔", "马修", "本", "瑞安", "丹特",
            "阿隆", "乔什", "米奇", "内森", "卡梅伦", "戴森",
            "威尔", "杰克", "卢克", "山姆", "克里斯", "布洛克",
            "凯尔", "布雷特", "肖恩", "斯蒂文", "丹尼尔", "托德",
            "布拉德", "查德", "特洛伊", "达斯汀", "科迪", "泰森",
            "德怀特", "拉马尔", "杰梅因", "德安德烈", "蒙特", "贾维斯"
        ]
        us_last_names = [
            "约翰逊", "威廉姆斯", "布朗", "琼斯", "米勒", "威尔逊",
            "摩尔", "泰勒", "安德森", "托马斯", "杰克逊", "怀特",
            "哈里斯", "马丁", "克拉克", "刘易斯", "霍尔", "杨",
            "斯科特", "亚当斯", "贝克", "尼尔森", "希尔", "坎贝尔",
            "罗伯茨", "菲利普斯", "埃文斯", "特纳", "柯林斯", "爱德华兹",
            "斯图尔特", "莫里斯", "墨菲", "里德", "库克", "贝利",
            "史密斯", "汤普森", "沃克", "罗宾逊", "艾伦", "赖特",
            "格林", "卡特", "米切尔", "帕克", "霍华德", "桑德斯",
            "普莱斯", "巴恩斯", "罗斯", "亨德森", "科尔曼", "詹金斯",
            "佩里", "鲍威尔", "朗", "帕特森", "休斯", "弗洛雷斯"
        ]
        
        # 非洲名字池（篮球人才辈出，占比较大）
        africa_first_names = [
            "切杜", "伊曼纽尔", "阿约", "奥卢", "恩杜迪", "乌切",
            "奇迪", "奥比", "伊克", "塞古", "马马杜", "谢赫",
            "穆萨", "阿马杜", "伊布拉希马", "奥马尔", "卡里姆", "尤素福",
            "阿卜杜勒", "易卜拉欣", "萨迪奥", "科菲", "夸梅", "阿萨莫阿",
            "帕特里克", "塞缪尔", "约瑟夫", "本杰明", "所罗门", "以赛亚",
            "吉迪恩", "戈兰", "塔里克", "哈桑", "贾马尔", "阿里",
            "巴卡里", "迪亚洛", "阿布巴卡尔", "伊德里斯", "奥斯曼"
        ]
        africa_last_names = [
            "奥孔科沃", "奥拉德", "阿金费瓦", "奥卢瓦托比",
            "恩万科", "乌佐马", "奇内杜", "奥比纳", "伊赫纳乔",
            "迪昂", "恩迪亚耶", "迪奥普", "法尔", "恩多耶", "卡巴",
            "西索科", "库利巴利", "特拉奥雷", "凯塔", "图雷", "萨诺戈",
            "门萨", "阿皮亚", "博阿滕", "吉安", "阿尤",
            "姆巴耶", "恩迪亚", "萨尔", "巴尔德", "迪亚基特",
            "奥努阿库", "恩瓦巴", "奥科吉", "西亚卡姆"
        ]
        
        # 欧洲名字池（篮球强势，占比较大）
        # 塞尔维亚/巴尔干
        balkan_first_names = [
            "尼古拉", "博扬", "德拉甘", "米洛斯", "弗拉迪米尔",
            "内马尼亚", "斯特凡", "佐兰", "德扬", "米兰",
            "鲍里斯", "伊万", "亚历克斯", "维克托", "马尔科",
            "达尼洛", "尼科拉", "波格丹", "瓦西里耶"
        ]
        balkan_last_names = [
            "彼得罗维奇", "拉多维奇", "斯坦科维奇", "米哈伊洛维奇", "科瓦切维奇",
            "托多罗维奇", "约万诺维奇", "波波维奇", "尼科利奇", "伊利奇",
            "马蒂奇", "克拉伊诺维奇",  "特奥多西奇"
        ]
        # 西欧（西班牙、法国、德国、意大利等）
        west_eu_first_names = [
            "塞尔吉奥", "马克", "安德烈", "丹尼斯", "迪特尔", "马蒂亚斯",
            "尼科斯", "尼古拉斯", "皮埃尔", "让", "弗朗索瓦", "马塞尔",
            "阿尔贝托", "朱塞佩", "洛伦佐", "奥利弗", "马丁", "菲利普",
            "托马斯", "卢卡", "马泰奥", "安东尼奥", "胡安卡洛斯"
        ]
        west_eu_last_names = [
            "施密特", "韦伯", "穆勒", "霍夫曼", "贝克尔", "瓦格纳",
            "杜邦", "莫罗", "贝尔纳", "罗西", "科斯塔",
            "布兰科", "内格罗", "里佐", "加索尔", "卢比奥",
            "费尔南德斯", "纳瓦罗", "雷耶斯"
        ]
        
        # 澳大利亚名字池（篮球强势）
        aus_first_names = [
            "安德鲁", "乔", "马修", "本", "瑞安", "丹特",
            "米奇", "内森", "卡梅伦", "戴森", "威尔", "杰克",
            "卢克", "山姆", "克里斯", "布洛克", "帕蒂", "乔克"
        ]
        aus_last_names = [
            "米尔斯", "德拉维多瓦", "英格尔斯", "贝恩斯",
            "西蒙斯", "埃克萨姆", "梅克", "吉迪", "丹尼尔斯",
            "凯", "兰代尔", "索贝", "克里克"
        ]
        
        # 南美名字池（篮球相对弱势，占比较小）
        south_america_first_names = [
            "莱昂德罗", "安德森", "布鲁诺", "路易斯", "法昆多",
            "帕布罗", "加布里埃尔", "马塞洛"
        ]
        south_america_last_names = [
            "努内斯", "席尔瓦", "桑托斯", "斯科拉", "诺西奥尼",
            "坎帕佐", "德克", "瓦雷乔"
        ]
        
        # 其他地区名字池（占比最小）
        other_first_names = [
            "何塞", "罗伯托", "里卡多", "阿图罗", "赫克托",
            "豪尔赫", "曼努埃尔"
        ]
        other_last_names = [
            "洛佩斯", "加西亚", "马丁内斯", "埃尔南德斯", "佩雷斯",
            "罗德里格斯", "迪亚兹", "桑切斯"
        ]
        
        # 按篮球强势程度分配权重选择地区
        # 美国40%，非洲20%，欧洲25%（巴尔干15%+西欧10%），澳大利亚10%，南美3%，其他2%
        region_weights = [
            (us_first_names, us_last_names, 40),           # 美国
            (africa_first_names, africa_last_names, 20),   # 非洲
            (balkan_first_names, balkan_last_names, 15),   # 巴尔干
            (west_eu_first_names, west_eu_last_names, 10), # 西欧
            (aus_first_names, aus_last_names, 10),         # 澳大利亚
            (south_america_first_names, south_america_last_names, 3),  # 南美
            (other_first_names, other_last_names, 2),      # 其他
        ]
        
        # 尝试生成不重复的完整名字（最多尝试100次）
        for _ in range(100):
            # 按权重选择地区
            total_weight = sum(w for _, _, w in region_weights)
            r = random.randint(1, total_weight)
            cumulative = 0
            selected_first_names = us_first_names
            selected_last_names = us_last_names
            
            for first_names, last_names, weight in region_weights:
                cumulative += weight
                if r <= cumulative:
                    selected_first_names = first_names
                    selected_last_names = last_names
                    break
            
            first_name = random.choice(selected_first_names)
            last_name = random.choice(selected_last_names)
            full_name = f"{first_name}·{last_name}"
            
            if full_name not in self._used_full_names:
                self._used_full_names.add(full_name)
                return full_name
        
        # 如果100次都重复，清空已使用列表重新开始
        self._used_full_names.clear()
        first_name = random.choice(us_first_names)
        last_name = random.choice(us_last_names)
        full_name = f"{first_name}·{last_name}"
        self._used_full_names.add(full_name)
        return full_name
    
    def _generate_scouting_report(self, player: Player, career: str) -> str:
        """生成球探报告（完整版，签约后可见）"""
        position_desc = {
            "PG": "控球后卫",
            "SG": "得分后卫",
            "SF": "小前锋",
            "PF": "大前锋",
            "C": "中锋"
        }
        
        # 找出最强属性
        attrs = {
            "进攻": player.offense,
            "防守": player.defense,
            "三分": player.three_point,
            "篮板": player.rebounding,
            "传球": player.passing
        }
        best_attr = max(attrs, key=attrs.get)
        
        report = (
            f"【球探报告】\n"
            f"姓名：{player.name}\n"
            f"位置：{position_desc.get(player.position, player.position)}\n"
            f"年龄：{player.age}岁\n"
            f"总评：{player.overall}\n"
            f"过往经历：{career}\n"
            f"技术特点：{', '.join(player.skill_tags)}\n"
            f"球探评价：该球员{best_attr}能力突出，"
        )
        
        if player.overall >= 95:
            report += "是顶级外援人选，能够成为球队绝对核心。"
        elif player.overall >= 91:
            report += "实力出众，可以作为球队主要得分点。"
        elif player.overall >= 87:
            report += "能力均衡，是可靠的轮换球员。"
        else:
            report += "具有一定实力，可以补充阵容深度。"
        
        return report
    
    def _generate_scouting_report_hidden(
        self,
        player: Player,
        career: str,
        visible_attributes: List[str],
        salary: int
    ) -> str:
        """生成球探报告（隐藏版，搜索时可见）"""
        position_desc = {
            "PG": "控球后卫",
            "SG": "得分后卫",
            "SF": "小前锋",
            "PF": "大前锋",
            "C": "中锋"
        }
        
        attr_names = {
            "offense": "进攻",
            "defense": "防守",
            "three_point": "三分",
            "rebounding": "篮板",
            "passing": "传球",
            "stamina": "体力"
        }
        
        # 构建可见能力值字符串
        visible_stats = []
        for attr in visible_attributes:
            value = getattr(player, attr)
            visible_stats.append(f"{attr_names[attr]}:{value}")
        
        report = (
            f"【球探报告】\n"
            f"姓名：{player.name}\n"
            f"位置：{position_desc.get(player.position, player.position)}\n"
            f"年龄：{player.age}岁\n"
            f"工资要求：{salary}万元\n"
            f"总评：??（未知）\n"
            f"已知能力值：{' | '.join(visible_stats)}\n"
            f"其他能力值：??（未知）\n"
            f"过往经历：{career}\n"
            f"技术特点：{', '.join(player.skill_tags)}\n"
        )
        
        # 根据工资给出模糊评价（不直接透露能力值）
        if salary >= 250:
            report += "球探评价：这是一位要价很高的球员，市场上对他的评价很高，但高薪不一定代表高能力。"
        elif salary >= 180:
            report += "球探评价：这位球员的薪资要求中等偏上，应该有一定实力，但具体表现还需观察。"
        elif salary >= 120:
            report += "球探评价：这位球员的薪资要求适中，可能是性价比不错的选择，也可能能力一般。"
        else:
            report += "球探评价：这位球员要价较低，可能是潜力股，也可能确实能力有限。"
        
        return report

    def _generate_foreign_player_with_llm(
        self,
        targeted: bool = False,
        target_position: Optional[str] = None
    ) -> ScoutResult:
        """使用LLM生成外援"""
        # 使用加权随机生成总能力值
        overall = self._generate_weighted_overall(targeted)
        
        # 根据能力值确定经历等级
        if overall >= 95:
            career_level = "elite"
            career_hint = "前NBA全明星级别或总冠军成员"
        elif overall >= 93:
            career_level = "high"
            career_hint = "NBA轮换球员或欧洲顶级联赛核心"
        elif overall >= 89:
            career_level = "medium"
            career_hint = "发展联盟明星或欧洲普通联赛主力"
        else:
            career_level = "low"
            career_hint = "发展联盟球员或NCAA明星"
        
        # 选择位置（定向搜索使用指定位置）
        if targeted and target_position:
            position = target_position
        else:
            position = random.choice(POSITIONS)
        
        # 先生成名字，确保不重复
        player_name = self._generate_foreign_name()
        
        # 构建LLM提示词，传入已生成的名字
        prompt = self._build_foreign_player_prompt(overall, position, career_hint, player_name)
        
        try:
            response = self.llm_interface.chat(
                prompt,
                system_prompt="你是一个专业的篮球球探，负责评估和介绍外援球员。请按要求生成球员信息。"
            )
            
            # 解析LLM响应，传入已生成的名字
            result = self._parse_llm_response(
                response, overall, position, career_level, targeted, player_name
            )
            if result:
                return result
        except Exception as e:
            print(f"LLM生成外援失败: {e}")
        
        # LLM失败时使用本地生成
        return self._generate_foreign_player_local(targeted, target_position)
    
    def _build_foreign_player_prompt(
        self,
        overall: int,
        position: str,
        career_hint: str,
        player_name: str
    ) -> str:
        """构建生成外援的LLM提示词"""
        position_desc = {
            "PG": "控球后卫",
            "SG": "得分后卫",
            "SF": "小前锋",
            "PF": "大前锋",
            "C": "中锋"
        }
        
        random_age = random.randint(25, 35)
        
        prompt = f"""请为华夏篮球联赛生成一名外援球员的详细信息。

【球员基本信息（已确定，不可更改）】
- 姓名：{player_name}
- 总能力值：{overall}
- 位置：{position}（{position_desc.get(position, position)}）
- 年龄：{random_age}岁
- 过往经历应与能力值匹配：{career_hint}

【输出格式】
请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
```json
{{
  "age": {random_age},
  "offense": <进攻能力，{overall-10}到{min(99, overall+5)}之间>,
  "defense": <防守能力，{overall-15}到{min(99, overall+3)}之间>,
  "three_point": <三分能力，{overall-12}到{min(99, overall+5)}之间>,
  "rebounding": <篮板能力，{overall-20}到{min(99, overall+8)}之间>,
  "passing": <传球能力，{overall-15}到{min(99, overall+5)}之间>,
  "stamina": <体力，{overall-5}到{min(99, overall+5)}之间>,
  "skill_tags": ["<技术标签1>", "<技术标签2>", "<技术标签3>"],
  "career_background": "<{player_name}的过往经历介绍，80-150字，详细描述在哪些联赛效力过、担任什么角色、取得过什么成就、为什么来华夏篮球联赛等>"
}}
```

【注意事项】
1. 技术标签应该与位置和能力值相匹配
2. 过往经历必须与能力值{overall}相匹配：
   - 95-96分：应有NBA全明星或总冠军经历（极其稀有）
   - 93-94分：应有NBA轮换或欧洲顶级联赛经历（稀有）
   - 89-92分：应有发展联盟明星或欧洲联赛主力经历
   - 85-88分：应有发展联盟或NCAA经历（最常见）
3. 各项细项能力值的平均值应接近总能力值{overall}
4. 过往经历要写成一小段话（80-150字），在描述中使用球员姓名"{player_name}"
"""
        return prompt
    
    def _parse_llm_response(
        self,
        response: str,
        overall: int,
        position: str,
        career_level: str,
        targeted: bool = False,
        player_name: str = ""
    ) -> Optional[ScoutResult]:
        """解析LLM响应"""
        import json
        import re
        
        try:
            # 提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response
            
            data = json.loads(json_str)
            
            # 生成球员ID
            self._foreign_player_counter += 1
            player_id = f"foreign_{self._foreign_player_counter:04d}"
            
            # 创建球员对象，使用传入的名字
            player = Player(
                id=player_id,
                name=player_name,
                team_id="",
                position=position,
                age=data.get("age", random.randint(25, 35)),
                is_foreign=True,
                offense=self._clamp_attribute(data.get("offense", overall)),
                defense=self._clamp_attribute(data.get("defense", overall - 5)),
                three_point=self._clamp_attribute(data.get("three_point", overall - 3)),
                rebounding=self._clamp_attribute(data.get("rebounding", overall - 8)),
                passing=self._clamp_attribute(data.get("passing", overall - 5)),
                stamina=self._clamp_attribute(data.get("stamina", overall)),
                overall=overall,
                skill_tags=data.get("skill_tags", [])[:3],
                trade_index=30
            )
            
            # 获取LLM生成的过往经历
            career_background = data.get("career_background")
            if not career_background:
                career_background = self._generate_career_background(overall, career_level)
            
            # 生成工资
            salary = self._generate_salary(overall)
            
            # 随机选择3项公开的能力值
            visible_attributes = self._select_visible_attributes()
            
            # 生成球探报告（隐藏版）
            scouting_report = self._generate_scouting_report_hidden(
                player, career_background, visible_attributes, salary
            )
            
            return ScoutResult(
                player=player,
                career_background=career_background,
                scouting_report=scouting_report,
                salary=salary,
                visible_attributes=visible_attributes,
                is_targeted_search=targeted
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"解析LLM响应失败: {e}")
            return None
    
    def _clamp_attribute(self, value: int) -> int:
        """限制属性值在有效范围内"""
        return max(50, min(99, int(value)))
    
    def get_team_foreign_players(self, team: Team) -> List[Player]:
        """
        获取球队当前的所有外援
        
        Args:
            team: 球队对象
            
        Returns:
            外援球员列表
        """
        roster = self.data_manager.get_team_roster(team.id)
        return [p for p in roster if p.is_foreign]
    
    def get_foreign_count(self, team: Team) -> int:
        """
        获取球队当前外援数量
        
        Args:
            team: 球队对象
            
        Returns:
            外援数量
        """
        return len(self.get_team_foreign_players(team))
    
    def can_sign_foreign_player(self, team: Team) -> Tuple[bool, str, bool]:
        """
        检查球队是否可以签约外援
        
        Args:
            team: 球队对象
            
        Returns:
            (是否可以签约, 原因, 是否需要替换现有外援)
        """
        # 获取未被裁的外援数量
        foreign_players = self.get_team_foreign_players(team)
        active_foreign_count = len([p for p in foreign_players if not p.is_waived])
        if active_foreign_count >= MAX_FOREIGN_PLAYERS:
            return True, f"外援名额已满（{active_foreign_count}/{MAX_FOREIGN_PLAYERS}），需要替换一名现有外援", True
        return True, "可以签约", False
    
    def get_active_foreign_players(self, team: Team) -> List[Player]:
        """
        获取球队当前未被裁的外援
        
        Args:
            team: 球队对象
            
        Returns:
            未被裁的外援球员列表
        """
        roster = self.data_manager.get_team_roster(team.id)
        return [p for p in roster if p.is_foreign and not p.is_waived]
    
    def get_active_foreign_count(self, team: Team) -> int:
        """
        获取球队当前未被裁的外援数量
        
        Args:
            team: 球队对象
            
        Returns:
            未被裁的外援数量
        """
        return len(self.get_active_foreign_players(team))
    
    def sign_scouted_player(
        self,
        team: Team,
        replace_player_id: Optional[str] = None,
        scouted_player_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        签约搜索到的外援
        
        Args:
            team: 签约球队
            replace_player_id: 要替换的外援ID（当外援已满时必须提供）
            scouted_player_id: 要签约的搜索结果外援ID，如果为None则签约第一个（向后兼容）
            
        Returns:
            (是否成功, 消息, 需要替换时返回外援列表)
        """
        if not self.scouted_players:
            return False, "没有可签约的外援，请先进行球探搜索", None
        
        # 查找要签约的外援
        target_result = None
        target_index = 0
        if scouted_player_id:
            for i, result in enumerate(self.scouted_players):
                if result.player.id == scouted_player_id:
                    target_result = result
                    target_index = i
                    break
            if not target_result:
                return False, "未找到指定的外援", None
        else:
            target_result = self.scouted_players[0]
            target_index = 0
        
        # 检查外援数量限制（只计算未被裁的外援）
        active_foreign_count = self.get_active_foreign_count(team)
        needs_replacement = active_foreign_count >= MAX_FOREIGN_PLAYERS
        
        if needs_replacement:
            if not replace_player_id:
                # 返回当前外援列表供选择
                foreign_players = self.get_active_foreign_players(team)
                foreign_list = [{
                    "id": p.id,
                    "name": p.name,
                    "position": p.position,
                    "age": p.age,
                    "overall": p.overall,
                    "offense": p.offense,
                    "defense": p.defense,
                    "three_point": p.three_point,
                    "rebounding": p.rebounding,
                    "passing": p.passing,
                    "stamina": p.stamina,
                    "skill_tags": p.skill_tags,
                    "avg_points": round(p.avg_points, 1),
                    "avg_rebounds": round(p.avg_rebounds, 1),
                    "avg_assists": round(p.avg_assists, 1),
                    "games_played": p.games_played
                } for p in foreign_players]
                return False, f"球队外援名额已满（{active_foreign_count}/{MAX_FOREIGN_PLAYERS}），请选择一名外援进行替换", foreign_list
            
            # 验证要替换的球员
            replace_player = self.data_manager.get_player(replace_player_id)
            if not replace_player:
                return False, "找不到要替换的球员", None
            if not replace_player.is_foreign:
                return False, "只能替换外援球员", None
            if replace_player.team_id != team.id:
                return False, "该球员不属于您的球队", None
            if replace_player.is_waived:
                return False, "该球员已被裁，请选择其他外援", None
            
            # 标记被替换的外援为被裁状态（不从阵容中移除）
            self._waive_player(replace_player)
            replaced_name = replace_player.name
        
        # 检查经费是否足够支付工资
        salary = target_result.salary
        if team.budget < salary:
            return False, f"经费不足，签约需要{salary}万元，当前{team.budget}万元", None
        
        player = target_result.player
        
        # 扣除工资
        team.budget -= salary
        
        # 设置球员所属球队
        player.team_id = team.id
        
        # 添加到数据管理器
        self.data_manager.players[player.id] = player
        
        # 添加到球队阵容
        if player.id not in team.roster:
            team.roster.append(player.id)
        
        # 从搜索结果列表中移除已签约的外援
        player_name = player.name
        player_overall = player.overall
        self.scouted_players.pop(target_index)
        
        # 更新向后兼容属性
        self.scouted_player = self.scouted_players[0] if self.scouted_players else None
        
        if needs_replacement:
            return True, f"成功签约外援 {player_name}（替换 {replaced_name}）！支付工资{salary}万元，实际能力值：{player_overall}", None
        return True, f"成功签约外援 {player_name}！支付工资{salary}万元，实际能力值：{player_overall}", None
    
    def _waive_player(self, player: Player) -> None:
        """
        将球员标记为被裁状态
        
        被裁的球员仍保留在阵容中，但不再出战比赛，统计数据不再变化
        
        Args:
            player: 要裁掉的球员
        """
        player.is_waived = True
    
    def _remove_player_from_team(self, player: Player, team: Team) -> None:
        """
        从球队移除球员
        
        Args:
            player: 要移除的球员
            team: 球队对象
        """
        # 从球队阵容中移除
        if player.id in team.roster:
            team.roster.remove(player.id)
        
        # 从数据管理器中移除
        if player.id in self.data_manager.players:
            del self.data_manager.players[player.id]
    
    def dismiss_scouted_player(self, player_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        放弃搜索到的外援
        
        Args:
            player_id: 要放弃的外援ID，如果为None则放弃第一个（向后兼容）
            
        Returns:
            (是否成功, 消息)
        """
        if not self.scouted_players:
            return False, "没有可放弃的外援"
        
        if player_id is None:
            # 向后兼容：放弃第一个
            removed = self.scouted_players.pop(0)
            self.scouted_player = self.scouted_players[0] if self.scouted_players else None
            return True, f"已放弃外援 {removed.player.name}"
        
        # 根据ID查找并移除
        for i, result in enumerate(self.scouted_players):
            if result.player.id == player_id:
                removed = self.scouted_players.pop(i)
                self.scouted_player = self.scouted_players[0] if self.scouted_players else None
                return True, f"已放弃外援 {removed.player.name}"
        
        return False, "未找到指定的外援"
    
    def get_scouted_player(self) -> Optional[ScoutResult]:
        """获取当前搜索到的外援（向后兼容，返回第一个）"""
        return self.scouted_players[0] if self.scouted_players else None
    
    def get_scouted_player_display_info(self, player_id: Optional[str] = None, current_date: Optional[str] = None) -> Optional[Dict]:
        """
        获取搜索到的外援的显示信息（隐藏部分能力值）
        
        Args:
            player_id: 外援ID，如果为None则返回第一个（向后兼容）
            current_date: 当前日期，用于计算剩余天数
            
        Returns:
            包含可显示信息的字典，或None
        """
        if not self.scouted_players:
            return None
        
        # 查找指定外援或返回第一个
        result = None
        if player_id:
            result = self.get_scouted_player_by_id(player_id)
        else:
            result = self.scouted_players[0]
        
        if not result:
            return None
        
        player = result.player
        
        attr_names = {
            "offense": "进攻",
            "defense": "防守",
            "three_point": "三分",
            "rebounding": "篮板",
            "passing": "传球",
            "stamina": "体力"
        }
        
        # 构建可见能力值
        visible_stats = {}
        for attr in result.visible_attributes:
            visible_stats[attr_names[attr]] = getattr(player, attr)
        
        # 计算剩余天数
        remaining_days = SCOUT_RESULT_EXPIRY_DAYS
        if current_date and result.expiry_date:
            remaining_days = self.get_scouted_player_remaining_days(player.id, current_date)
        
        return {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "salary": result.salary,
            "visible_attributes": visible_stats,
            "skill_tags": player.skill_tags,
            "career_background": result.career_background,
            "scouting_report": result.scouting_report,
            "is_targeted_search": result.is_targeted_search,
            "scout_date": result.scout_date,
            "expiry_date": result.expiry_date,
            "remaining_days": remaining_days
        }
    
    def get_all_scouted_players_display_info(self, current_date: Optional[str] = None) -> List[Dict]:
        """
        获取所有搜索到的外援的显示信息
        
        Args:
            current_date: 当前日期，用于计算剩余天数
            
        Returns:
            包含所有外援可显示信息的列表
        """
        result_list = []
        for result in self.scouted_players:
            info = self.get_scouted_player_display_info(result.player.id, current_date)
            if info:
                result_list.append(info)
        return result_list
    
    def get_full_player_info(self, player_id: Optional[str] = None) -> Optional[Dict]:
        """
        获取搜索到的外援的完整信息
        
        Args:
            player_id: 外援ID，如果为None则返回第一个（向后兼容）
            
        Returns:
            包含完整信息的字典，或None
        """
        if not self.scouted_players:
            return None
        
        # 查找指定外援或返回第一个
        result = None
        if player_id:
            result = self.get_scouted_player_by_id(player_id)
        else:
            result = self.scouted_players[0]
        
        if not result:
            return None
        
        player = result.player
        
        return {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "overall": player.overall,
            "offense": player.offense,
            "defense": player.defense,
            "three_point": player.three_point,
            "rebounding": player.rebounding,
            "passing": player.passing,
            "stamina": player.stamina,
            "skill_tags": player.skill_tags,
            "career_background": result.career_background,
            "salary": result.salary,
            "scout_date": result.scout_date,
            "expiry_date": result.expiry_date
        }
    
    @staticmethod
    def calculate_match_reward(is_win: bool) -> int:
        """
        计算比赛奖励经费
        
        Args:
            is_win: 是否获胜
            
        Returns:
            奖励金额（万元）
        """
        if is_win:
            return random.randint(WIN_REWARD_MIN, WIN_REWARD_MAX)
        else:
            return random.randint(LOSE_REWARD_MIN, LOSE_REWARD_MAX)
    
    @staticmethod
    def add_match_reward(team: Team, is_win: bool) -> int:
        """
        为球队添加比赛奖励
        
        Args:
            team: 球队对象
            is_win: 是否获胜
            
        Returns:
            奖励金额（万元）
        """
        reward = ForeignMarket.calculate_match_reward(is_win)
        team.budget += reward
        return reward
    
    def can_get_sponsor(self, current_date: str) -> Tuple[bool, str, int]:
        """
        检查是否可以拉赞助
        
        Args:
            current_date: 当前游戏日期 (YYYY-MM-DD格式)
            
        Returns:
            (是否可以拉赞助, 原因, 剩余冷却天数)
        """
        if self._last_sponsor_date is None:
            return True, "可以拉赞助", 0
        
        from datetime import datetime
        last_date = datetime.strptime(self._last_sponsor_date, "%Y-%m-%d")
        current = datetime.strptime(current_date, "%Y-%m-%d")
        days_passed = (current - last_date).days
        
        if days_passed >= SPONSOR_COOLDOWN_DAYS:
            return True, "可以拉赞助", 0
        else:
            remaining = SPONSOR_COOLDOWN_DAYS - days_passed
            return False, f"赞助冷却中，还需等待{remaining}天", remaining
    
    def get_sponsor(self, team: Team, current_date: str) -> Tuple[bool, str, int]:
        """
        拉赞助获取经费
        
        Args:
            team: 球队对象
            current_date: 当前游戏日期 (YYYY-MM-DD格式)
            
        Returns:
            (是否成功, 消息, 获得的金额)
        """
        can_sponsor, reason, remaining = self.can_get_sponsor(current_date)
        if not can_sponsor:
            return False, reason, 0
        
        # 使用加权随机生成赞助金额
        amount = self._generate_sponsor_amount()
        
        # 添加到球队经费
        team.budget += amount
        
        # 更新上次赞助日期
        self._last_sponsor_date = current_date
        
        # 根据金额生成不同的消息
        if amount >= 80:
            message = f"恭喜！获得重量级赞助商青睐，获得{amount}万元赞助经费！"
        elif amount >= 50:
            message = f"不错！成功拉到{amount}万元赞助经费！"
        else:
            message = f"获得{amount}万元赞助经费"
        
        return True, message, amount
    
    def _generate_sponsor_amount(self) -> int:
        """
        使用加权随机生成赞助金额
        
        概率分布：
        - 10-29万: 40% 概率
        - 30-49万: 30% 概率
        - 50-69万: 15% 概率
        - 70-79万: 10% 概率
        - 80-100万: 5% 概率（极低）
        
        Returns:
            赞助金额（万元）
        """
        # 构建加权列表
        ranges = []
        weights = []
        for (min_val, max_val), weight in SPONSOR_AMOUNT_WEIGHTS:
            ranges.append((min_val, max_val))
            weights.append(weight)
        
        # 根据权重选择一个范围
        selected_range = random.choices(ranges, weights=weights, k=1)[0]
        
        # 在选中的范围内随机选择一个值
        return random.randint(selected_range[0], selected_range[1])
    
    def get_sponsor_status(self, current_date: str) -> Dict:
        """
        获取赞助系统状态
        
        Args:
            current_date: 当前游戏日期
            
        Returns:
            赞助状态字典
        """
        can_sponsor, reason, remaining = self.can_get_sponsor(current_date)
        return {
            "can_sponsor": can_sponsor,
            "reason": reason,
            "cooldown_remaining": remaining,
            "cooldown_days": SPONSOR_COOLDOWN_DAYS,
            "min_amount": SPONSOR_MIN_AMOUNT,
            "max_amount": SPONSOR_MAX_AMOUNT,
            "last_sponsor_date": self._last_sponsor_date
        }
    
    def get_used_names_state(self) -> Dict:
        """
        获取已使用名字的状态（用于存档）
        
        Returns:
            包含已使用完整名字和计数器的字典
        """
        # 序列化搜索结果列表
        scouted_players_data = []
        for result in self.scouted_players:
            player = result.player
            scouted_players_data.append({
                "player": {
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
                    "trade_index": player.trade_index
                },
                "career_background": result.career_background,
                "scouting_report": result.scouting_report,
                "salary": result.salary,
                "visible_attributes": result.visible_attributes,
                "is_targeted_search": result.is_targeted_search,
                "scout_date": result.scout_date,
                "expiry_date": result.expiry_date
            })
        
        return {
            "used_full_names": list(self._used_full_names),
            "name_counter": self._name_counter,
            "foreign_player_counter": self._foreign_player_counter,
            "last_sponsor_date": self._last_sponsor_date,
            "scouted_players": scouted_players_data
        }
    
    def restore_used_names_state(self, state: Dict) -> None:
        """
        从存档恢复已使用名字的状态
        
        Args:
            state: 包含已使用名字和计数器的字典
        """
        # 支持新格式
        if "used_full_names" in state:
            self._used_full_names = set(state.get("used_full_names", []))
        else:
            # 兼容旧版存档格式，初始化为空
            self._used_full_names = set()
        
        # 恢复计数器（兼容旧存档）
        self._name_counter = state.get("name_counter", 0)
        self._foreign_player_counter = state.get("foreign_player_counter", 0)
        
        # 恢复赞助日期（兼容旧存档）
        self._last_sponsor_date = state.get("last_sponsor_date", None)
        
        # 恢复搜索结果列表
        self.scouted_players = []
        scouted_players_data = state.get("scouted_players", [])
        for data in scouted_players_data:
            player_data = data.get("player", {})
            player = Player(
                id=player_data.get("id", ""),
                name=player_data.get("name", ""),
                team_id=player_data.get("team_id", ""),
                position=player_data.get("position", ""),
                age=player_data.get("age", 25),
                is_foreign=player_data.get("is_foreign", True),
                offense=player_data.get("offense", 80),
                defense=player_data.get("defense", 80),
                three_point=player_data.get("three_point", 80),
                rebounding=player_data.get("rebounding", 80),
                passing=player_data.get("passing", 80),
                stamina=player_data.get("stamina", 80),
                overall=player_data.get("overall", 80),
                skill_tags=player_data.get("skill_tags", []),
                trade_index=player_data.get("trade_index", 30)
            )
            result = ScoutResult(
                player=player,
                career_background=data.get("career_background", ""),
                scouting_report=data.get("scouting_report", ""),
                salary=data.get("salary", 0),
                visible_attributes=data.get("visible_attributes", []),
                is_targeted_search=data.get("is_targeted_search", False),
                scout_date=data.get("scout_date", ""),
                expiry_date=data.get("expiry_date", "")
            )
            self.scouted_players.append(result)
        
        # 更新向后兼容属性
        self.scouted_player = self.scouted_players[0] if self.scouted_players else None
    
    def clear_used_names(self) -> None:
        """清空已使用的名字记录（用于新赛季或重置）"""
        self._used_full_names.clear()
