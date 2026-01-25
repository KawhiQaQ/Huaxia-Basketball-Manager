"""
华夏篮球联赛教练模拟器 - 主入口

游戏主程序，包含球队选择、主菜单和游戏循环
Requirements: 1.1, 1.2, 1.3, 1.4, 10.1
"""
import os
import sys
from typing import Optional, Dict, List

from src.models import Team, Player, GameState, Standing
from src.player_data_manager import PlayerDataManager
from src.season_manager import SeasonManager
from src.match_engine import MatchEngine
from src.training_system import TrainingSystem, TRAINING_PROGRAMS
from src.trade_system import TradeSystem
from src.injury_system import InjurySystem
from src.storage_manager import StorageManager, SaveLoadError, CorruptedSaveError
from src.llm_interface import LLMInterface
from src.game_controller import GameController


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """打印标题头"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_separator():
    """打印分隔线"""
    print("-" * 60)


class CoachSimulator:
    """华夏篮球联赛教练模拟器主类"""
    
    def __init__(self):
        """初始化模拟器"""
        self.data_manager = PlayerDataManager()
        self.storage_manager = StorageManager()
        self.teams: Dict[str, Team] = {}
        self.players: Dict[str, Player] = {}
        self.player_team_id: Optional[str] = None
        self.game_controller: Optional[GameController] = None
        self.season_manager: Optional[SeasonManager] = None
        self.match_engine: Optional[MatchEngine] = None
        self.training_system: Optional[TrainingSystem] = None
        self.trade_system: Optional[TradeSystem] = None
        self.injury_system: Optional[InjurySystem] = None
        self.llm_interface: Optional[LLMInterface] = None
        self.running = True
    
    def start(self):
        """启动游戏"""
        clear_screen()
        self._show_welcome()
        
        while self.running:
            choice = self._show_start_menu()
            
            if choice == "1":
                self._new_game()
            elif choice == "2":
                self._load_game()
            elif choice == "3":
                self._show_about()
            elif choice == "4":
                self._quit_game()
            else:
                print("\n无效选择，请重新输入。")
    
    def _show_welcome(self):
        """显示欢迎界面"""
        print_header("华夏篮球联赛教练模拟器")
        print("""
    欢迎来到华夏篮球联赛教练模拟器！
    
    在这里，你将扮演一支球队的主教练，
    通过训练、交易和比赛策略，带领球队走向冠军！
    
    游戏特色：
    - 20支球队可供选择
    - 基于AI的智能比赛模拟
    - 完整的常规赛和季后赛体验
    - 球员训练和交易系统
        """)
    
    def _show_start_menu(self) -> str:
        """显示开始菜单"""
        print_separator()
        print("\n请选择：")
        print("  1. 新游戏")
        print("  2. 读取存档")
        print("  3. 关于游戏")
        print("  4. 退出")
        print()
        return input("请输入选项 (1-4): ").strip()
    
    def _new_game(self):
        """开始新游戏"""
        # 加载球队和球员数据
        self.teams, self.players = self.data_manager.load_all_data()
        
        if not self.teams:
            print("\n错误：无法加载球队数据，请检查 player_data/teams.json 文件。")
            return
        
        # 显示球队选择界面
        selected_team = self._show_team_selection()
        
        if selected_team:
            self._initialize_game(selected_team)
            self._main_game_loop()
    
    def _show_team_selection(self) -> Optional[Team]:
        """
        显示球队选择界面
        
        Requirements: 1.1, 1.2
        
        Returns:
            选中的球队，取消则返回None
        """
        clear_screen()
        print_header("选择你的球队")
        
        # 将球队按状态分组显示
        teams_list = list(self.teams.values())
        
        # 按状态分类
        contending = [t for t in teams_list if t.status == "contending"]
        stable = [t for t in teams_list if t.status == "stable"]
        rebuilding = [t for t in teams_list if t.status == "rebuilding"]
        
        print("\n【争冠球队】")
        self._print_team_group(contending, 1)
        
        start_idx = len(contending) + 1
        print("\n【稳定球队】")
        self._print_team_group(stable, start_idx)
        
        start_idx += len(stable)
        print("\n【重建球队】")
        self._print_team_group(rebuilding, start_idx)
        
        print_separator()
        print("\n输入球队编号选择，或输入 0 返回主菜单")
        
        # 创建编号到球队的映射
        all_teams = contending + stable + rebuilding
        team_map = {str(i+1): team for i, team in enumerate(all_teams)}
        
        while True:
            choice = input("\n请选择球队 (1-20): ").strip()
            
            if choice == "0":
                return None
            
            if choice in team_map:
                selected_team = team_map[choice]
                
                # 显示球队详情并确认
                if self._confirm_team_selection(selected_team):
                    return selected_team
            else:
                print("无效选择，请输入 1-20 之间的数字。")
    
    def _print_team_group(self, teams: List[Team], start_idx: int):
        """打印球队分组"""
        for i, team in enumerate(teams):
            idx = start_idx + i
            roster = self.data_manager.get_team_roster(team.id)
            avg_overall = sum(p.overall for p in roster) / len(roster) if roster else 0
            print(f"  {idx:2d}. {team.name:<12} ({team.city}) - 平均能力值: {avg_overall:.1f}")
    
    def _confirm_team_selection(self, team: Team) -> bool:
        """
        确认球队选择
        
        Requirements: 1.3
        """
        clear_screen()
        print_header(f"球队详情 - {team.name}")
        
        # 显示球队信息
        print(f"\n城市: {team.city}")
        print(f"状态: {self._get_status_name(team.status)}")
        
        # 显示阵容
        roster = self.data_manager.get_team_roster(team.id)
        print(f"\n阵容 ({len(roster)}人):")
        print_separator()
        print(f"{'姓名':<10} {'位置':<4} {'年龄':<4} {'总评':<4} {'特点'}")
        print_separator()
        
        # 按总评排序
        roster.sort(key=lambda p: p.overall, reverse=True)
        
        for player in roster[:10]:  # 显示前10名球员
            tags = ", ".join(player.skill_tags[:2]) if player.skill_tags else "-"
            foreign = "[外]" if player.is_foreign else ""
            print(f"{player.name:<10}{foreign} {player.position:<4} {player.age:<4} {player.overall:<4} {tags}")
        
        if len(roster) > 10:
            print(f"  ... 还有 {len(roster) - 10} 名球员")
        
        print_separator()
        print("\n确认选择这支球队吗？")
        print("  1. 确认")
        print("  2. 返回重新选择")
        
        choice = input("\n请选择 (1/2): ").strip()
        return choice == "1"
    
    def _get_status_name(self, status: str) -> str:
        """获取状态中文名"""
        status_names = {
            "contending": "争冠",
            "stable": "稳定",
            "rebuilding": "重建"
        }
        return status_names.get(status, status)
    
    def _initialize_game(self, selected_team: Team):
        """
        初始化游戏
        
        Requirements: 1.2, 1.4
        """
        # 设置玩家控制的球队
        self.player_team_id = selected_team.id
        
        # 重置所有球队的控制状态
        for team in self.teams.values():
            team.is_player_controlled = False
        
        # 标记选中的球队为玩家控制
        selected_team.is_player_controlled = True
        
        # 初始化各个系统
        self._init_game_systems()
        
        print(f"\n恭喜！你已成为 {selected_team.name} 的主教练！")
        print("赛季即将开始，祝你好运！")
        input("\n按回车键继续...")
    
    def _init_game_systems(self):
        """初始化游戏系统"""
        # 初始化LLM接口
        try:
            self.llm_interface = LLMInterface()
            # 测试LLM连接
            print("\n正在测试LLM连接...")
            success, message = self.llm_interface.test_connection()
            if success:
                print(f"✅ {message}")
                print(f"   模型: {self.llm_interface.model}")
                print(f"   端点: {self.llm_interface.base_url}")
            else:
                print(f"❌ {message}")
                print("   将使用本地模拟算法（功能受限）")
                self.llm_interface = None
        except Exception as e:
            self.llm_interface = None
            print(f"\n❌ LLM接口初始化失败: {e}")
            print("   将使用本地模拟算法（功能受限）")
        
        # 初始化赛季管理器
        teams_list = list(self.teams.values())
        self.season_manager = SeasonManager(teams_list)
        self.season_manager.generate_alternating_schedule()
        
        # 初始化比赛引擎
        self.match_engine = MatchEngine(
            llm_interface=self.llm_interface,
            data_manager=self.data_manager
        )
        
        # 初始化训练系统
        self.training_system = TrainingSystem(self.data_manager)
        
        # 初始化交易系统
        self.trade_system = TradeSystem(
            data_manager=self.data_manager,
            llm_interface=self.llm_interface
        )
        
        # 初始化伤病系统
        self.injury_system = InjurySystem()
        
        # 初始化游戏控制器
        self.game_controller = GameController(
            season_manager=self.season_manager,
            match_engine=self.match_engine,
            training_system=self.training_system,
            injury_system=self.injury_system,
            teams=self.teams,
            players=self.players,
            player_team_id=self.player_team_id
        )

    def _main_game_loop(self):
        """
        主游戏循环
        
        Requirements: 10.1
        """
        while self.running and self.game_controller:
            clear_screen()
            self._show_game_status()
            choice = self._show_main_menu()
            
            if choice == "1":
                self._advance_day()
            elif choice == "2":
                self._view_roster()
            elif choice == "3":
                self._training_menu()
            elif choice == "4":
                self._trade_menu()
            elif choice == "5":
                self._view_standings()
            elif choice == "6":
                self._view_schedule()
            elif choice == "7":
                self._save_game()
            elif choice == "8":
                if self._confirm_exit():
                    break
            else:
                print("\n无效选择，请重新输入。")
                input("按回车键继续...")
    
    def _show_game_status(self):
        """显示游戏状态"""
        if not self.game_controller:
            return
        
        status = self.game_controller.get_season_status()
        team = self.teams.get(self.player_team_id)
        team_name = team.name if team else "未知"
        
        print_header(f"华夏篮球联赛教练模拟器 - {team_name}")
        
        # 显示日期和赛季进度
        print(f"\n当前日期: {status['current_date']}")
        day_type = "比赛日" if status['day_type'] == "match_day" else "训练日"
        print(f"今日类型: {day_type}")
        print(f"赛季进度: {status['games_played']}/{status['total_games']} ({status['progress_pct']:.1f}%)")
        
        # 显示球队战绩
        if self.season_manager:
            standing = self.season_manager.get_team_standing(self.player_team_id)
            if standing:
                rank = self.season_manager.get_team_rank(self.player_team_id)
                print(f"当前战绩: {standing.wins}胜 {standing.losses}负 (排名第{rank})")
        
        # 显示今日比赛
        today_game = self.game_controller.get_player_team_today_game()
        if today_game:
            home_team = self.teams.get(today_game.home_team_id)
            away_team = self.teams.get(today_game.away_team_id)
            if home_team and away_team:
                is_home = today_game.home_team_id == self.player_team_id
                opponent = away_team if is_home else home_team
                location = "主场" if is_home else "客场"
                print(f"\n今日比赛: vs {opponent.name} ({location})")
    
    def _show_main_menu(self) -> str:
        """显示主菜单"""
        print_separator()
        print("\n主菜单:")
        print("  1. 推进日期")
        print("  2. 查看阵容")
        print("  3. 训练球员")
        print("  4. 交易中心")
        print("  5. 查看排行榜")
        print("  6. 查看赛程")
        print("  7. 保存游戏")
        print("  8. 返回主菜单")
        print()
        return input("请选择 (1-8): ").strip()
    
    def _advance_day(self):
        """推进日期"""
        if not self.game_controller:
            return
        
        clear_screen()
        print_header("推进日期")
        
        status = self.game_controller.get_season_status()
        
        # 检查赛季是否结束
        if status.get('champion'):
            champion_team = self.teams.get(status['champion'])
            champion_name = champion_team.name if champion_team else "未知"
            print(f"\n赛季已结束！冠军: {champion_name}")
            input("\n按回车键继续...")
            return
        
        print(f"\n当前日期: {status['current_date']}")
        print("\n选择推进方式:")
        print("  1. 推进一天")
        print("  2. 跳到下一个比赛日")
        print("  0. 返回")
        
        choice = input("\n请选择: ").strip()
        
        if choice == "1":
            self._advance_one_day()
        elif choice == "2":
            self._skip_to_next_game()
        elif choice == "0":
            return
    
    def _advance_one_day(self):
        """推进一天"""
        if not self.game_controller:
            return
        
        print("\n正在推进日期...")
        
        try:
            result = self.game_controller.advance_date(
                days=1,
                auto_simulate_matches=True,
                use_llm=self.llm_interface is not None
            )
            
            # 显示结果
            for day_result in result.get("day_results", []):
                self._show_day_result(day_result)
            
        except Exception as e:
            print(f"\n推进日期时出错: {e}")
        
        input("\n按回车键继续...")
    
    def _skip_to_next_game(self):
        """跳到下一个比赛日"""
        if not self.game_controller:
            return
        
        next_date = self.game_controller.get_next_game_date()
        if not next_date:
            print("\n没有更多比赛了。")
            input("\n按回车键继续...")
            return
        
        days = self.game_controller.get_days_until(next_date)
        print(f"\n将跳过 {days} 天到 {next_date}")
        
        confirm = input("确认？(y/n): ").strip().lower()
        if confirm != 'y':
            return
        
        print("\n正在模拟...")
        
        try:
            result = self.game_controller.skip_to_next_game(
                auto_simulate_matches=True,
                use_llm=self.llm_interface is not None
            )
            
            if result:
                # 只显示比赛日的结果
                for day_result in result.get("day_results", []):
                    if day_result.get("matches_played"):
                        self._show_day_result(day_result)
            
        except Exception as e:
            print(f"\n跳转时出错: {e}")
        
        input("\n按回车键继续...")
    
    def _show_day_result(self, day_result: dict):
        """显示单日结果"""
        date = day_result.get("date", "")
        day_type = day_result.get("day_type", "")
        matches = day_result.get("matches_played", [])
        recovered = day_result.get("recovered_players", [])
        injuries = day_result.get("new_injuries", [])
        
        print(f"\n--- {date} ---")
        
        if matches:
            print("\n比赛结果:")
            for match in matches:
                home_team = self.teams.get(match.home_team_id)
                away_team = self.teams.get(match.away_team_id)
                home_name = home_team.name if home_team else match.home_team_id
                away_name = away_team.name if away_team else match.away_team_id
                
                # 高亮玩家球队的比赛
                is_player_game = (match.home_team_id == self.player_team_id or 
                                  match.away_team_id == self.player_team_id)
                prefix = "★ " if is_player_game else "  "
                
                print(f"{prefix}{home_name} {match.home_score} - {match.away_score} {away_name}")
                
                # 如果是玩家球队的比赛，显示更多详情
                if is_player_game and match.narrative:
                    print(f"    {match.narrative[:100]}...")
        
        if recovered:
            print("\n伤愈复出:")
            for player in recovered:
                print(f"  {player.name} 已恢复健康")
        
        if injuries:
            print("\n新增伤病:")
            for player, days in injuries:
                print(f"  {player.name} 受伤，预计休战 {days} 天")
    
    def _view_roster(self):
        """查看阵容"""
        clear_screen()
        team = self.teams.get(self.player_team_id)
        if not team:
            print("无法获取球队信息")
            input("\n按回车键继续...")
            return
        
        print_header(f"{team.name} - 球队阵容")
        
        roster = self.data_manager.get_team_roster(self.player_team_id)
        roster.sort(key=lambda p: p.overall, reverse=True)
        
        print(f"\n{'#':<3} {'姓名':<10} {'位置':<4} {'年龄':<4} {'总评':<4} {'进攻':<4} {'防守':<4} {'三分':<4} {'状态'}")
        print_separator()
        
        for i, player in enumerate(roster, 1):
            status = "伤病" if player.is_injured else "健康"
            foreign = "[外]" if player.is_foreign else ""
            print(f"{i:<3} {player.name:<10}{foreign} {player.position:<4} {player.age:<4} "
                  f"{player.overall:<4} {player.offense:<4} {player.defense:<4} "
                  f"{player.three_point:<4} {status}")
        
        print_separator()
        print("\n选项:")
        print("  1. 查看球员详情")
        print("  0. 返回")
        
        choice = input("\n请选择: ").strip()
        
        if choice == "1":
            self._view_player_detail(roster)
    
    def _view_player_detail(self, roster: List[Player]):
        """查看球员详情"""
        player_num = input("输入球员编号: ").strip()
        
        try:
            idx = int(player_num) - 1
            if 0 <= idx < len(roster):
                player = roster[idx]
                self._show_player_detail(player)
        except ValueError:
            print("无效输入")
    
    def _show_player_detail(self, player: Player):
        """显示球员详细信息"""
        clear_screen()
        print_header(f"球员详情 - {player.name}")
        
        print(f"\n基本信息:")
        print(f"  位置: {player.position}")
        print(f"  年龄: {player.age}")
        print(f"  外援: {'是' if player.is_foreign else '否'}")
        print(f"  状态: {'伤病 (剩余' + str(player.injury_days) + '天)' if player.is_injured else '健康'}")
        
        print(f"\n能力值:")
        print(f"  总评: {player.overall}")
        print(f"  进攻: {player.offense}")
        print(f"  防守: {player.defense}")
        print(f"  三分: {player.three_point}")
        print(f"  篮板: {player.rebounding}")
        print(f"  传球: {player.passing}")
        print(f"  体力: {player.stamina}")
        
        if player.skill_tags:
            print(f"\n技术标签: {', '.join(player.skill_tags)}")
        
        if player.games_played > 0:
            print(f"\n赛季数据 ({player.games_played}场):")
            print(f"  场均得分: {player.avg_points:.1f}")
            print(f"  场均篮板: {player.avg_rebounds:.1f}")
            print(f"  场均助攻: {player.avg_assists:.1f}")
            print(f"  场均抢断: {player.avg_steals:.1f}")
            print(f"  场均盖帽: {player.avg_blocks:.1f}")
            print(f"  场均失误: {player.avg_turnovers:.1f}")
            print(f"  场均时间: {player.avg_minutes:.1f}分钟")
        
        input("\n按回车键返回...")

    def _training_menu(self):
        """训练菜单"""
        if not self.game_controller or not self.training_system:
            return
        
        # 检查是否为训练日
        if not self.game_controller.can_train():
            clear_screen()
            print_header("训练")
            print("\n今天是比赛日，无法进行训练。")
            input("\n按回车键返回...")
            return
        
        clear_screen()
        print_header("训练中心")
        
        team = self.teams.get(self.player_team_id)
        if not team:
            return
        
        print("\n可用训练项目:")
        programs = TRAINING_PROGRAMS
        for i, prog in enumerate(programs, 1):
            attr_name = self._get_attr_name(prog.target_attribute)
            print(f"  {i}. {prog.name} (提升{attr_name} +{prog.boost_min}-{prog.boost_max})")
        
        print("\n  0. 返回")
        
        choice = input("\n选择训练项目: ").strip()
        
        if choice == "0":
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(programs):
                program = programs[idx]
                self._execute_team_training(team, program)
        except ValueError:
            print("无效输入")
            input("\n按回车键继续...")
    
    def _get_attr_name(self, attr: str) -> str:
        """获取属性中文名"""
        attr_names = {
            "offense": "进攻",
            "defense": "防守",
            "three_point": "三分",
            "rebounding": "篮板",
            "passing": "传球",
            "stamina": "体力"
        }
        return attr_names.get(attr, attr)
    
    def _execute_team_training(self, team: Team, program):
        """执行球队训练"""
        print(f"\n正在进行 {program.name}...")
        
        try:
            results = self.training_system.apply_team_training(team, program)
            
            print("\n训练结果:")
            roster = self.data_manager.get_team_roster(team.id)
            
            for player in roster:
                boost = results.get(player.id, 0)
                if boost > 0:
                    attr_name = self._get_attr_name(program.target_attribute)
                    print(f"  {player.name}: {attr_name} +{boost}")
                elif player.is_injured:
                    print(f"  {player.name}: 因伤缺席训练")
            
        except Exception as e:
            print(f"\n训练失败: {e}")
        
        input("\n按回车键继续...")
    
    def _trade_menu(self):
        """交易菜单"""
        clear_screen()
        print_header("交易中心")
        
        print("\n选项:")
        print("  1. 发起交易")
        print("  2. 自由球员市场")
        print("  3. 查看交易历史")
        print("  0. 返回")
        
        choice = input("\n请选择: ").strip()
        
        if choice == "1":
            self._initiate_trade()
        elif choice == "2":
            self._free_agent_market()
        elif choice == "3":
            self._view_trade_history()
    
    def _initiate_trade(self):
        """发起交易"""
        clear_screen()
        print_header("发起交易")
        
        # 选择交易对象球队
        print("\n选择交易对象球队:")
        other_teams = [t for t in self.teams.values() if t.id != self.player_team_id]
        
        for i, team in enumerate(other_teams, 1):
            print(f"  {i}. {team.name}")
        
        print("\n  0. 返回")
        
        choice = input("\n选择球队: ").strip()
        
        if choice == "0":
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(other_teams):
                target_team = other_teams[idx]
                self._trade_with_team(target_team)
        except ValueError:
            print("无效输入")
            input("\n按回车键继续...")
    
    def _trade_with_team(self, target_team: Team):
        """与指定球队交易"""
        clear_screen()
        print_header(f"与 {target_team.name} 交易")
        
        # 显示双方阵容
        my_roster = self.data_manager.get_team_roster(self.player_team_id)
        their_roster = self.data_manager.get_team_roster(target_team.id)
        
        print("\n我方球员:")
        for i, p in enumerate(my_roster, 1):
            print(f"  {i}. {p.name} ({p.position}, 总评{p.overall})")
        
        print(f"\n{target_team.name} 球员:")
        for i, p in enumerate(their_roster, 1):
            print(f"  {i}. {p.name} ({p.position}, 总评{p.overall})")
        
        print("\n输入交易内容 (格式: 我方球员编号,对方球员编号)")
        print("例如: 1,3 表示用我方1号球员换对方3号球员")
        print("输入 0 返回")
        
        trade_input = input("\n交易内容: ").strip()
        
        if trade_input == "0":
            return
        
        try:
            parts = trade_input.split(",")
            if len(parts) != 2:
                print("格式错误")
                input("\n按回车键继续...")
                return
            
            my_idx = int(parts[0].strip()) - 1
            their_idx = int(parts[1].strip()) - 1
            
            if not (0 <= my_idx < len(my_roster) and 0 <= their_idx < len(their_roster)):
                print("球员编号无效")
                input("\n按回车键继续...")
                return
            
            my_player = my_roster[my_idx]
            their_player = their_roster[their_idx]
            
            # 创建交易提案
            from src.models import TradeProposal
            proposal = TradeProposal(
                offering_team_id=self.player_team_id,
                receiving_team_id=target_team.id,
                players_offered=[my_player.id],
                players_requested=[their_player.id]
            )
            
            print(f"\n正在提交交易: {my_player.name} 换 {their_player.name}...")
            
            success, message = self.trade_system.propose_trade(proposal)
            
            if success:
                print(f"\n✓ {message}")
            else:
                print(f"\n✗ {message}")
            
        except ValueError:
            print("输入格式错误")
        
        input("\n按回车键继续...")
    
    def _free_agent_market(self):
        """自由球员市场"""
        clear_screen()
        print_header("自由球员市场")
        
        free_agents = self.trade_system.get_free_agents()
        
        if not free_agents:
            print("\n目前没有可签约的自由球员。")
            input("\n按回车键返回...")
            return
        
        print("\n可签约球员:")
        for i, player in enumerate(free_agents, 1):
            print(f"  {i}. {player.name} ({player.position}, 总评{player.overall})")
        
        print("\n  0. 返回")
        
        choice = input("\n选择要签约的球员: ").strip()
        
        if choice == "0":
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(free_agents):
                player = free_agents[idx]
                success, message = self.trade_system.sign_free_agent(
                    self.player_team_id, player.id
                )
                print(f"\n{message}")
        except ValueError:
            print("无效输入")
        
        input("\n按回车键继续...")
    
    def _view_trade_history(self):
        """查看交易历史"""
        clear_screen()
        print_header("交易历史")
        
        history = self.trade_system.get_trade_history()
        
        if not history:
            print("\n本赛季暂无交易记录。")
        else:
            print("\n交易记录:")
            for i, record in enumerate(history, 1):
                print(f"  {i}. {record}")
        
        input("\n按回车键返回...")
    
    def _view_standings(self):
        """
        查看排行榜
        
        Requirements: 9.1, 9.4
        """
        clear_screen()
        
        if not self.season_manager:
            return
        
        # 检查是否在季后赛阶段
        if self.season_manager.is_regular_season_over():
            self._show_standings_with_playoffs()
        else:
            self._show_regular_standings()
        
        input("\n按回车键返回...")
    
    def _show_regular_standings(self):
        """显示常规赛排行榜"""
        print_header("联赛排行榜")
        
        standings = self.season_manager.get_standings()
        
        print(f"\n{'排名':<4} {'球队':<14} {'胜':<4} {'负':<4} {'胜率':<8} {'落后'}")
        print_separator()
        
        for i, standing in enumerate(standings, 1):
            team = self.teams.get(standing.team_id)
            team_name = team.name if team else standing.team_id
            
            # 高亮玩家球队
            prefix = "★" if standing.team_id == self.player_team_id else " "
            
            gb = "-" if standing.games_behind == 0 else f"{standing.games_behind:.1f}"
            print(f"{prefix}{i:<3} {team_name:<14} {standing.wins:<4} {standing.losses:<4} "
                  f"{standing.win_pct:.3f}   {gb}")
    
    def _show_standings_with_playoffs(self):
        """
        显示排行榜和季后赛对阵
        
        Requirements: 9.4
        """
        print_header("季后赛")
        
        # 显示当前轮次
        round_name = self.season_manager.get_playoff_round_name()
        round_names = {
            "play_in": "附加赛",
            "quarter": "四分之一决赛",
            "semi": "半决赛",
            "final": "总决赛",
            "champion": "赛季结束"
        }
        print(f"\n当前阶段: {round_names.get(round_name, round_name)}")
        
        # 检查是否有冠军
        champion = self.season_manager.get_champion()
        if champion:
            champion_team = self.teams.get(champion)
            champion_name = champion_team.name if champion_team else champion
            print(f"\n🏆 本赛季冠军: {champion_name} 🏆")
            print_separator()
        
        # 显示季后赛对阵
        bracket = self.season_manager.get_playoff_bracket()
        
        if bracket:
            self._display_playoff_bracket(bracket)
        
        # 显示常规赛最终排名
        print("\n常规赛最终排名:")
        print_separator()
        standings = self.season_manager.get_standings()
        
        print(f"{'排名':<4} {'球队':<14} {'胜':<4} {'负':<4} {'胜率':<8}")
        for i, standing in enumerate(standings[:12], 1):  # 只显示季后赛球队
            team = self.teams.get(standing.team_id)
            team_name = team.name if team else standing.team_id
            prefix = "★" if standing.team_id == self.player_team_id else " "
            print(f"{prefix}{i:<3} {team_name:<14} {standing.wins:<4} {standing.losses:<4} "
                  f"{standing.win_pct:.3f}")
    
    def _display_playoff_bracket(self, bracket: dict):
        """
        显示季后赛对阵表
        
        Requirements: 9.4
        """
        from src.models import PlayoffSeries
        
        print("\n季后赛对阵:")
        print_separator()
        
        # 显示附加赛
        play_in_series = [(k, v) for k, v in bracket.items() 
                          if k.startswith("play_in_") and isinstance(v, PlayoffSeries)]
        if play_in_series:
            print("\n【附加赛】(三战两胜)")
            for series_id, series in sorted(play_in_series):
                self._print_series(series)
        
        # 显示四分之一决赛
        quarter_series = [(k, v) for k, v in bracket.items() 
                          if k.startswith("quarter_") and isinstance(v, PlayoffSeries)]
        if quarter_series:
            print("\n【四分之一决赛】(七战四胜)")
            for series_id, series in sorted(quarter_series):
                self._print_series(series)
        
        # 显示半决赛
        semi_series = [(k, v) for k, v in bracket.items() 
                       if k.startswith("semi_") and isinstance(v, PlayoffSeries)]
        if semi_series:
            print("\n【半决赛】(七战四胜)")
            for series_id, series in sorted(semi_series):
                self._print_series(series)
        
        # 显示总决赛
        if "final" in bracket and isinstance(bracket["final"], PlayoffSeries):
            print("\n【总决赛】(七战四胜)")
            self._print_series(bracket["final"])
    
    def _print_series(self, series):
        """打印系列赛信息"""
        from src.models import PlayoffSeries
        
        team1 = self.teams.get(series.team1_id)
        team2 = self.teams.get(series.team2_id)
        team1_name = team1.name if team1 else series.team1_id
        team2_name = team2.name if team2 else series.team2_id
        
        # 高亮玩家球队
        if series.team1_id == self.player_team_id:
            team1_name = f"★{team1_name}"
        if series.team2_id == self.player_team_id:
            team2_name = f"★{team2_name}"
        
        status = ""
        if series.is_complete:
            winner = self.teams.get(series.winner_id)
            winner_name = winner.name if winner else series.winner_id
            status = f" → {winner_name} 晋级"
        
        print(f"  {team1_name} {series.team1_wins} - {series.team2_wins} {team2_name}{status}")
    
    def _view_schedule(self):
        """查看赛程"""
        clear_screen()
        print_header("赛程表")
        
        if not self.season_manager:
            return
        
        # 获取玩家球队的剩余比赛
        remaining = self.season_manager.get_team_remaining_games(self.player_team_id)
        
        print(f"\n剩余比赛 ({len(remaining)}场):")
        print_separator()
        
        for game in remaining[:10]:  # 显示最近10场
            home_team = self.teams.get(game.home_team_id)
            away_team = self.teams.get(game.away_team_id)
            
            is_home = game.home_team_id == self.player_team_id
            opponent = away_team if is_home else home_team
            opponent_name = opponent.name if opponent else "未知"
            location = "主场" if is_home else "客场"
            
            print(f"  {game.date}  vs {opponent_name} ({location})")
        
        if len(remaining) > 10:
            print(f"\n  ... 还有 {len(remaining) - 10} 场比赛")
        
        input("\n按回车键返回...")
    
    def _save_game(self):
        """保存游戏"""
        clear_screen()
        print_header("保存游戏")
        
        # 显示现有存档
        saves = self.storage_manager.list_saves()
        
        print("\n存档槽位:")
        for slot in range(1, 11):
            save_info = next((s for s in saves if s[0] == slot), None)
            if save_info:
                _, save_time, team_name, phase = save_info
                print(f"  {slot}. [{team_name}] {phase} - {save_time}")
            else:
                print(f"  {slot}. [空]")
        
        print("\n  0. 返回")
        
        choice = input("\n选择存档槽位 (1-10): ").strip()
        
        if choice == "0":
            return
        
        try:
            slot = int(choice)
            if 1 <= slot <= 10:
                # 检查是否覆盖
                if self.storage_manager.save_exists(slot):
                    confirm = input("该槽位已有存档，是否覆盖？(y/n): ").strip().lower()
                    if confirm != 'y':
                        return
                
                # 创建游戏状态
                state = self._create_game_state()
                
                self.storage_manager.save_game(state, slot)
                print(f"\n游戏已保存到槽位 {slot}")
            else:
                print("无效的槽位号")
        except ValueError:
            print("无效输入")
        except SaveLoadError as e:
            print(f"\n保存失败: {e}")
        
        input("\n按回车键继续...")
    
    def _create_game_state(self) -> GameState:
        """创建当前游戏状态"""
        standings = self.season_manager.get_standings() if self.season_manager else []
        schedule = self.season_manager.schedule if self.season_manager else []
        playoff_bracket = self.season_manager.get_playoff_bracket() if self.season_manager else {}
        current_date = self.game_controller.current_date if self.game_controller else "2024-10-15"
        season_phase = "playoff" if (self.season_manager and self.season_manager.is_regular_season_over()) else "regular"
        
        return GameState(
            current_date=current_date,
            player_team_id=self.player_team_id,
            season_phase=season_phase,
            teams=self.teams,
            players=self.players,
            standings=standings,
            schedule=schedule,
            playoff_bracket=playoff_bracket,
            free_agents=self.trade_system.free_agents if self.trade_system else [],
            foreign_used_names={}  # 命令行版本暂不支持外援市场
        )
    
    def _load_game(self):
        """读取存档"""
        clear_screen()
        print_header("读取存档")
        
        saves = self.storage_manager.list_saves()
        
        if not saves:
            print("\n没有可用的存档。")
            input("\n按回车键返回...")
            return
        
        print("\n可用存档:")
        for slot, save_time, team_name, phase in saves:
            print(f"  {slot}. [{team_name}] {phase} - {save_time}")
        
        print("\n  0. 返回")
        
        choice = input("\n选择存档槽位: ").strip()
        
        if choice == "0":
            return
        
        try:
            slot = int(choice)
            state, message = self.storage_manager.try_load_game(slot)
            
            if state:
                self._restore_game_state(state)
                print(f"\n{message}")
                input("\n按回车键开始游戏...")
                self._main_game_loop()
            else:
                print(f"\n{message}")
                input("\n按回车键返回...")
                
        except ValueError:
            print("无效输入")
            input("\n按回车键返回...")
    
    def _restore_game_state(self, state: GameState):
        """恢复游戏状态"""
        self.teams = state.teams
        self.players = state.players
        self.player_team_id = state.player_team_id
        
        # 更新数据管理器
        self.data_manager.teams = self.teams
        self.data_manager.players = self.players
        
        # 重新初始化游戏系统
        self._init_game_systems()
        
        # 恢复赛季状态
        if self.season_manager:
            self.season_manager.schedule = state.schedule
            self.season_manager.standings = {s.team_id: s for s in state.standings}
            self.season_manager.playoff_bracket = state.playoff_bracket
            self.season_manager.current_date = state.current_date
        
        # 恢复游戏控制器日期
        if self.game_controller:
            self.game_controller._current_date = state.current_date
        
        # 恢复自由球员
        if self.trade_system:
            self.trade_system.free_agents = state.free_agents
    
    def _show_about(self):
        """显示关于信息"""
        clear_screen()
        print_header("关于游戏")
        print("""
    华夏篮球联赛教练模拟器 v1.0
    
    一款基于AI的篮球经理模拟游戏
    
    游戏特色:
    - 20支球队可供选择
    - 基于大语言模型的智能比赛模拟
    - 完整的42场常规赛 + 季后赛体验
    - 球员训练系统
    - 球员交易和自由市场
    - 伤病系统
    - 存档/读档功能
    
    操作提示:
    - 比赛日无法训练，请合理安排时间
    - 注意球员伤病状态
    - 交易时考虑球队需求和球员价值
        """)
        input("\n按回车键返回...")
    
    def _confirm_exit(self) -> bool:
        """确认退出"""
        print("\n是否保存游戏后退出？")
        print("  1. 保存并退出")
        print("  2. 直接退出（不保存）")
        print("  3. 取消")
        
        choice = input("\n请选择: ").strip()
        
        if choice == "1":
            self._save_game()
            return True
        elif choice == "2":
            return True
        else:
            return False
    
    def _quit_game(self):
        """退出游戏"""
        print("\n感谢游玩华夏篮球联赛教练模拟器！再见！")
        self.running = False


def main():
    """主函数"""
    simulator = CoachSimulator()
    simulator.start()


if __name__ == "__main__":
    main()
