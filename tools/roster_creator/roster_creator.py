"""
球员/球队自定义生成工具
独立于游戏主体的小工具，用于创建自定义的 players.json 和 teams.json 文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import uuid
from typing import Dict, List, Optional

# 位置选项
POSITIONS = ["PG", "SG", "SF", "PF", "C"]
POSITION_NAMES = {"PG": "控球后卫", "SG": "得分后卫", "SF": "小前锋", "PF": "大前锋", "C": "中锋"}

# 球队状态选项
TEAM_STATUS = ["contending", "stable", "rebuilding"]
STATUS_NAMES = {"contending": "争冠", "stable": "稳定", "rebuilding": "重建"}

# 技能标签选项（按位置分类）
SKILL_TAGS_BY_POSITION = {
    "控球后卫 (PG)": [
        "组织核心", "控场大师", "助攻优先", "突破犀利", "挡拆发起者",
        "快攻指挥官", "节奏掌控者", "传球大师", "抢断高手", "压迫防守",
        "替补控卫", "双能卫", "持球投威胁", "关键球处理", "场上教练"
    ],
    "得分后卫 (SG)": [
        "得分机器", "三分射手", "神射手", "无球跑动专家", "底角三分",
        "中距离杀手", "急停跳投", "后撤步大师", "造犯规高手", "关键先生",
        "外线火力", "持球单打", "得分爆发力", "空切高手", "反击快下"
    ],
    "小前锋 (SF)": [
        "全能前锋", "锋线摇摆人", "3D球员", "侧翼防守者", "攻防一体",
        "外线投射", "突破终结", "快攻箭头", "单打好手", "错位杀手",
        "防守尖兵", "补防专家", "轮换锋线", "年轻锋线", "运动能力强"
    ],
    "大前锋 (PF)": [
        "空间型四号位", "机动四号位", "低位单打", "背身技术", "面框进攻",
        "前场篮板", "拼抢积极", "挡拆顺下", "策应高手", "高位策应",
        "延阻防守", "协防意识", "蓝领球员", "内线蓝领", "能量球员"
    ],
    "中锋 (C)": [
        "内线支柱", "护筐高手", "护框精英", "篮板机器", "精英篮板手",
        "低位怪兽", "内线终结者", "空间型五号位", "挡拆掩护", "吃饼高手",
        "二次进攻", "篮下终结", "防守核心", "盖帽高手", "禁区守护者"
    ],
    "通用技能": [
        "领袖", "更衣室领袖", "老将", "经验丰富", "潜力新星",
        "年轻球员", "外援核心", "团队配合", "高球商", "大心脏",
        "铁人", "体力充沛", "防守积极", "防守悍将", "防守潜力",
        "三分火力", "稳定输出", "效率球员", "垃圾时间杀手", "板凳匪徒"
    ]
}

# 所有技能标签（扁平列表，用于兼容）
SKILL_TAGS = []
for tags in SKILL_TAGS_BY_POSITION.values():
    SKILL_TAGS.extend(tags)

# 颜色主题
COLORS = {
    "bg": "#f0f2f5",
    "card_bg": "#ffffff",
    "primary": "#1976D2",
    "primary_light": "#E3F2FD",
    "accent": "#FF5722",
    "text": "#212121",
    "text_secondary": "#757575",
    "border": "#E0E0E0",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "danger": "#F44336",
    "foreign": "#9C27B0"
}


class ScrollableFrame(ttk.Frame):
    """可滚动的Frame容器"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
    
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")



class PlayerEditor(ttk.Frame):
    """单个球员编辑器"""
    
    def __init__(self, parent, player_data: Optional[Dict] = None, on_delete=None, index=0):
        super().__init__(parent)
        self.on_delete = on_delete
        self.player_id = player_data.get("id") if player_data else f"player_{uuid.uuid4().hex[:8]}"
        self.index = index
        self.is_locked = True  # 默认锁定
        self.editable_widgets = []  # 保存所有可编辑控件
        self.editable_scales = []  # 保存所有滑块控件
        
        self._create_widgets()
        if player_data:
            self._load_data(player_data)
        self._apply_lock_state()  # 应用初始锁定状态
    
    def _create_widgets(self):
        # 主卡片
        self.card = tk.Frame(self, bg=COLORS["card_bg"], relief=tk.RIDGE, bd=1)
        self.card.pack(fill=tk.X, padx=6, pady=4)
        
        # 顶部栏
        top_bar = tk.Frame(self.card, bg=COLORS["primary_light"], height=28)
        top_bar.pack(fill=tk.X)
        top_bar.pack_propagate(False)
        
        self.index_label = tk.Label(top_bar, text=f" #{self.index + 1}", 
                                    bg=COLORS["primary_light"], fg=COLORS["primary"],
                                    font=("Microsoft YaHei UI", 9, "bold"))
        self.index_label.pack(side=tk.LEFT, padx=5)
        
        delete_btn = tk.Button(top_bar, text="✕ 删除", fg="white", bg=COLORS["danger"],
                               relief=tk.FLAT, font=("Microsoft YaHei UI", 8),
                               cursor="hand2", command=self._on_delete, padx=8)
        delete_btn.pack(side=tk.RIGHT, padx=5, pady=3)
        
        # 锁定按钮
        self.lock_btn = tk.Button(top_bar, text="🔒 已锁定", fg="white", bg=COLORS["text_secondary"],
                                  relief=tk.FLAT, font=("Microsoft YaHei UI", 8),
                                  cursor="hand2", command=self._toggle_lock, padx=8)
        self.lock_btn.pack(side=tk.RIGHT, padx=5, pady=3)
        
        # 内容区
        content = tk.Frame(self.card, bg=COLORS["card_bg"], padx=12, pady=10)
        content.pack(fill=tk.X)
        
        # 第一行：基本信息
        row1 = tk.Frame(content, bg=COLORS["card_bg"])
        row1.pack(fill=tk.X, pady=4)
        
        self._add_label_entry(row1, "姓名", 10)
        self.name_var = self._last_var
        self.name_entry = self._last_widget
        
        self._add_label_spinbox(row1, "年龄", 18, 45, 25, 4)
        self.age_var = self._last_var
        self.age_spinbox = self._last_widget
        
        tk.Label(row1, text="位置", bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(15, 5))
        self.position_var = tk.StringVar(value="PG")
        self.pos_combo = ttk.Combobox(row1, textvariable=self.position_var, values=POSITIONS,
                                 width=5, state="readonly", font=("Microsoft YaHei UI", 10))
        self.pos_combo.pack(side=tk.LEFT)
        self.editable_widgets.append(self.pos_combo)
        
        # 外援标记
        self.is_foreign_var = tk.BooleanVar(value=False)
        foreign_frame = tk.Frame(row1, bg=COLORS["foreign"], padx=8, pady=2)
        self.foreign_check = tk.Checkbutton(foreign_frame, text="外援", variable=self.is_foreign_var,
                                       bg=COLORS["foreign"], fg="white", selectcolor=COLORS["foreign"],
                                       activebackground=COLORS["foreign"], activeforeground="white",
                                       font=("Microsoft YaHei UI", 9, "bold"))
        self.foreign_check.pack()
        foreign_frame.pack(side=tk.LEFT, padx=15)
        self.editable_widgets.append(self.foreign_check)
        
        # 第二行：能力值
        row2 = tk.Frame(content, bg=COLORS["card_bg"])
        row2.pack(fill=tk.X, pady=6)
        
        self.stat_vars = {}
        self.stat_entries = {}
        self.stat_entry_widgets = {}  # 保存Entry控件引用
        stats = [("进攻", "offense", "#E53935"), ("防守", "defense", "#1E88E5"),
                 ("三分", "three_point", "#43A047"), ("传球", "passing", "#FB8C00"),
                 ("篮板", "rebounding", "#6D4C41"), ("体力", "stamina", "#546E7A")]
        
        for label, key, color in stats:
            frame = tk.Frame(row2, bg=COLORS["card_bg"])
            frame.pack(side=tk.LEFT, padx=6)
            
            tk.Label(frame, text=label, bg=COLORS["card_bg"], fg=color,
                    font=("Microsoft YaHei UI", 8, "bold")).pack()
            
            var = tk.IntVar(value=70)
            self.stat_vars[key] = var
            
            # 数值输入框（可编辑）
            entry_var = tk.StringVar(value="70")
            entry = tk.Entry(frame, textvariable=entry_var, width=3, justify=tk.CENTER,
                            bg=color, fg="white", font=("Microsoft YaHei UI", 10, "bold"),
                            relief=tk.FLAT, insertbackground="white")
            entry.pack(pady=2)
            self.stat_entries[key] = entry_var
            self.stat_entry_widgets[key] = entry
            self.editable_widgets.append(entry)
            
            # 输入框变化时同步到滑块
            def on_entry_change(sv, k=key, v=var):
                try:
                    val = int(sv.get())
                    if 1 <= val <= 99:
                        v.set(val)
                        self._calculate_overall()
                except ValueError:
                    pass
            entry_var.trace_add("write", lambda *args, sv=entry_var, k=key, v=var: on_entry_change(sv, k, v))
            
            # 滑块
            def on_scale_change(value, k=key, ev=entry_var):
                ev.set(str(int(float(value))))
                self._calculate_overall()
            
            scale = ttk.Scale(frame, from_=1, to=99, variable=var, length=55,
                             command=lambda v, k=key, ev=entry_var: on_scale_change(v, k, ev))
            scale.pack()
            self.editable_scales.append(scale)
        
        # 第三行：总评和交易指数
        row3 = tk.Frame(content, bg=COLORS["card_bg"])
        row3.pack(fill=tk.X, pady=6)
        
        # 总评框
        overall_box = tk.Frame(row3, bg=COLORS["primary"], padx=12, pady=6)
        overall_box.pack(side=tk.LEFT)
        tk.Label(overall_box, text="总评", bg=COLORS["primary"], fg="white",
                font=("Microsoft YaHei UI", 8)).pack()
        self.overall_var = tk.StringVar(value="70")
        tk.Label(overall_box, textvariable=self.overall_var, bg=COLORS["primary"], fg="white",
                font=("Microsoft YaHei UI", 16, "bold")).pack()
        
        # 自动计算（默认关闭）
        self.auto_overall_var = tk.BooleanVar(value=False)
        self.auto_check = tk.Checkbutton(row3, text="自动", variable=self.auto_overall_var,
                      bg=COLORS["card_bg"], font=("Microsoft YaHei UI", 9))
        self.auto_check.pack(side=tk.LEFT, padx=8)
        self.editable_widgets.append(self.auto_check)
        
        tk.Label(row3, text="手动:", bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.overall_spinbox = ttk.Spinbox(row3, textvariable=self.overall_var, from_=1, to=99, width=4,
                   font=("Microsoft YaHei UI", 10))
        self.overall_spinbox.pack(side=tk.LEFT, padx=3)
        self.editable_widgets.append(self.overall_spinbox)
        
        tk.Label(row3, text="交易指数:", bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(20, 5))
        self.trade_index_var = tk.StringVar(value="30")
        self.trade_spinbox = ttk.Spinbox(row3, textvariable=self.trade_index_var, from_=1, to=100, width=4,
                   font=("Microsoft YaHei UI", 10))
        self.trade_spinbox.pack(side=tk.LEFT)
        self.editable_widgets.append(self.trade_spinbox)
        
        # 第四行：技能标签
        row4 = tk.Frame(content, bg=COLORS["card_bg"])
        row4.pack(fill=tk.X, pady=4)
        
        tk.Label(row4, text="技能标签:", bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.tags_var = tk.StringVar()
        self.tags_entry = ttk.Entry(row4, textvariable=self.tags_var, width=30,
                 font=("Microsoft YaHei UI", 9))
        self.tags_entry.pack(side=tk.LEFT, padx=5)
        self.editable_widgets.append(self.tags_entry)
        
        self.tags_btn = tk.Button(row4, text="选择", bg=COLORS["primary"], fg="white", relief=tk.FLAT,
                 font=("Microsoft YaHei UI", 9), cursor="hand2", padx=10,
                 command=self._select_tags)
        self.tags_btn.pack(side=tk.LEFT, padx=5)
    
    def _add_label_entry(self, parent, text, width):
        tk.Label(parent, text=text, bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self._last_var = tk.StringVar()
        self._last_widget = ttk.Entry(parent, textvariable=self._last_var, width=width,
                 font=("Microsoft YaHei UI", 10))
        self._last_widget.pack(side=tk.LEFT)
        self.editable_widgets.append(self._last_widget)
    
    def _add_label_spinbox(self, parent, text, from_, to, default, width):
        tk.Label(parent, text=text, bg=COLORS["card_bg"], fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(15, 5))
        self._last_var = tk.StringVar(value=str(default))
        self._last_widget = ttk.Spinbox(parent, textvariable=self._last_var, from_=from_, to=to, width=width,
                   font=("Microsoft YaHei UI", 10))
        self._last_widget.pack(side=tk.LEFT)
        self.editable_widgets.append(self._last_widget)
    
    def _calculate_overall(self):
        if not self.auto_overall_var.get():
            return
        try:
            vals = {k: self.stat_vars[k].get() for k in self.stat_vars}
            overall = int(vals["offense"] * 0.25 + vals["defense"] * 0.2 + vals["three_point"] * 0.15 +
                         vals["passing"] * 0.15 + vals["rebounding"] * 0.15 + vals["stamina"] * 0.1)
            self.overall_var.set(str(overall))
        except (ValueError, tk.TclError):
            pass
    
    def _select_tags(self):
        if self.is_locked:
            return  # 锁定状态下不允许选择标签
        dialog = TagSelectorDialog(self.winfo_toplevel(), self.tags_var.get())
        self.wait_window(dialog)
        if dialog.result:
            self.tags_var.set(", ".join(dialog.result))
    
    def _toggle_lock(self):
        """切换锁定状态"""
        self.is_locked = not self.is_locked
        self._apply_lock_state()
    
    def _apply_lock_state(self):
        """应用锁定状态到所有可编辑控件"""
        if self.is_locked:
            self.lock_btn.config(text="🔒 已锁定", bg=COLORS["text_secondary"])
            state = "disabled"
            readonly_state = "disabled"
        else:
            self.lock_btn.config(text="🔓 编辑中", bg=COLORS["success"])
            state = "normal"
            readonly_state = "readonly"
        
        # 禁用/启用普通控件
        for widget in self.editable_widgets:
            try:
                if isinstance(widget, ttk.Combobox):
                    widget.config(state=readonly_state if not self.is_locked else "disabled")
                elif isinstance(widget, (tk.Checkbutton,)):
                    widget.config(state=state)
                elif isinstance(widget, (ttk.Entry, ttk.Spinbox, tk.Entry)):
                    widget.config(state=state)
            except tk.TclError:
                pass
        
        # 禁用/启用滑块
        for scale in self.editable_scales:
            try:
                scale.config(state=state)
            except tk.TclError:
                pass
        
        # 禁用/启用标签选择按钮
        if hasattr(self, 'tags_btn'):
            self.tags_btn.config(state=state)
    
    def _on_delete(self):
        self._cleanup()  # 清理资源
        if self.on_delete:
            self.on_delete(self)
    
    def _cleanup(self):
        """清理资源，防止内存泄漏"""
        # 移除所有 trace 回调
        for key, entry_var in self.stat_entries.items():
            try:
                for trace_id in entry_var.trace_info():
                    entry_var.trace_remove(trace_id[0], trace_id[1])
            except (tk.TclError, ValueError):
                pass
        
        # 清空控件列表
        self.editable_widgets.clear()
        self.editable_scales.clear()
    
    def set_index(self, index):
        self.index = index
        self.index_label.config(text=f" #{index + 1}")
    
    def _load_data(self, data: Dict):
        self.player_id = data.get("id", self.player_id)
        self.name_var.set(data.get("name", ""))
        self.age_var.set(str(data.get("age", 25)))
        self.position_var.set(data.get("position", "PG"))
        self.is_foreign_var.set(data.get("is_foreign", False))
        
        for key in self.stat_vars:
            val = data.get(key, 70)
            self.stat_vars[key].set(val)
            self.stat_entries[key].set(str(val))
        
        self.overall_var.set(str(data.get("overall", 70)))
        self.trade_index_var.set(str(data.get("trade_index", 30)))
        self.tags_var.set(", ".join(data.get("skill_tags", [])))
    
    def get_data(self) -> Dict:
        tags_str = self.tags_var.get().strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        
        return {
            "age": int(self.age_var.get() or 25),
            "avg_assists": 0, "avg_blocks": 0, "avg_minutes": 0, "avg_points": 0,
            "avg_rebounds": 0, "avg_steals": 0, "avg_turnovers": 0,
            "defense": self.stat_vars["defense"].get(),
            "games_played": 0, "id": self.player_id, "injury_days": 0,
            "is_foreign": self.is_foreign_var.get(), "is_injured": False,
            "name": self.name_var.get(),
            "offense": self.stat_vars["offense"].get(),
            "overall": int(self.overall_var.get() or 70),
            "passing": self.stat_vars["passing"].get(),
            "position": self.position_var.get(),
            "rebounding": self.stat_vars["rebounding"].get(),
            "skill_tags": tags,
            "stamina": self.stat_vars["stamina"].get(),
            "team_id": "",
            "three_point": self.stat_vars["three_point"].get(),
            "total_assists": 0, "total_blocks": 0, "total_minutes": 0,
            "total_points": 0, "total_rebounds": 0, "total_steals": 0, "total_turnovers": 0,
            "trade_index": int(self.trade_index_var.get() or 30)
        }



class TagSelectorDialog(tk.Toplevel):
    """技能标签选择对话框 - 按位置分类，支持滚动"""
    
    def __init__(self, parent, current_tags: str):
        super().__init__(parent)
        self.title("选择技能标签")
        self.geometry("580x500")
        self.configure(bg=COLORS["bg"])
        self.result = None
        
        current = set(t.strip() for t in current_tags.split(",") if t.strip())
        
        # 标题栏
        title_frame = tk.Frame(self, bg=COLORS["primary"], height=45)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="🏷️ 选择技能标签 (最多3个)", bg=COLORS["primary"], fg="white",
                font=("Microsoft YaHei UI", 12, "bold")).pack(expand=True)
        
        # 提示信息
        tip_frame = tk.Frame(self, bg=COLORS["warning"], padx=10, pady=5)
        tip_frame.pack(fill=tk.X)
        tk.Label(tip_frame, text="💡 提示：标签按位置分类仅供参考，所有标签均可混用选择", 
                bg=COLORS["warning"], fg=COLORS["text"],
                font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        
        # 已选标签显示
        self.selected_frame = tk.Frame(self, bg=COLORS["primary_light"], padx=10, pady=8)
        self.selected_frame.pack(fill=tk.X)
        tk.Label(self.selected_frame, text="已选择:", bg=COLORS["primary_light"], 
                fg=COLORS["text_secondary"], font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.selected_label = tk.Label(self.selected_frame, text="无", bg=COLORS["primary_light"],
                                       fg=COLORS["primary"], font=("Microsoft YaHei UI", 9, "bold"))
        self.selected_label.pack(side=tk.LEFT, padx=5)
        
        # 滚动区域
        scroll_container = tk.Frame(self, bg=COLORS["bg"])
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(scroll_container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS["bg"])
        
        self.scrollable_frame.bind("<Configure>", 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定鼠标滚轮
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        
        # 按位置分类显示标签
        self.tag_vars = {}
        position_colors = {
            "控球后卫 (PG)": "#2196F3",
            "得分后卫 (SG)": "#F44336", 
            "小前锋 (SF)": "#4CAF50",
            "大前锋 (PF)": "#FF9800",
            "中锋 (C)": "#9C27B0",
            "通用技能": "#607D8B"
        }
        
        for position, tags in SKILL_TAGS_BY_POSITION.items():
            color = position_colors.get(position, COLORS["primary"])
            
            # 位置标题
            pos_frame = tk.Frame(self.scrollable_frame, bg=color, padx=10, pady=5)
            pos_frame.pack(fill=tk.X, padx=5, pady=(10, 5))
            tk.Label(pos_frame, text=position, bg=color, fg="white",
                    font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)
            
            # 标签网格
            tag_container = tk.Frame(self.scrollable_frame, bg=COLORS["card_bg"], padx=10, pady=8)
            tag_container.pack(fill=tk.X, padx=5)
            
            for i, tag in enumerate(tags):
                var = tk.BooleanVar(value=tag in current)
                var.trace_add("write", lambda *args: self._update_selected())
                self.tag_vars[tag] = var
                
                cb = tk.Checkbutton(tag_container, text=tag, variable=var, 
                                   bg=COLORS["card_bg"], activebackground=COLORS["card_bg"],
                                   font=("Microsoft YaHei UI", 9), anchor="w",
                                   selectcolor=COLORS["card_bg"])
                cb.grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=2)
        
        # 按钮区
        btn_frame = tk.Frame(self, bg=COLORS["bg"], pady=12)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="清空选择", bg=COLORS["warning"], fg="white",
                 font=("Microsoft YaHei UI", 10), relief=tk.FLAT, padx=15, pady=5,
                 cursor="hand2", command=self._clear_all).pack(side=tk.LEFT, padx=15)
        
        tk.Button(btn_frame, text="取消", bg=COLORS["border"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 10), relief=tk.FLAT, padx=20, pady=5,
                 cursor="hand2", command=self.destroy).pack(side=tk.RIGHT, padx=10)
        
        tk.Button(btn_frame, text="确定", bg=COLORS["primary"], fg="white",
                 font=("Microsoft YaHei UI", 10, "bold"), relief=tk.FLAT, padx=25, pady=5,
                 cursor="hand2", command=self._confirm).pack(side=tk.RIGHT)
        
        self.transient(parent)
        self.grab_set()
        
        # 居中显示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
        # 初始化已选显示
        self._update_selected()
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _update_selected(self):
        """更新已选标签显示"""
        selected = [tag for tag, var in self.tag_vars.items() if var.get()]
        if selected:
            text = ", ".join(selected[:3])
            if len(selected) > 3:
                text += f" (+{len(selected)-3})"
            color = COLORS["danger"] if len(selected) > 3 else COLORS["primary"]
        else:
            text = "无"
            color = COLORS["text_secondary"]
        self.selected_label.config(text=text, fg=color)
    
    def _clear_all(self):
        """清空所有选择"""
        for var in self.tag_vars.values():
            var.set(False)
    
    def _confirm(self):
        selected = [tag for tag, var in self.tag_vars.items() if var.get()]
        if len(selected) > 3:
            messagebox.showwarning("提示", f"已选择 {len(selected)} 个标签，最多只能选择3个！\n请取消部分选择。", parent=self)
            return
        self.result = selected
        self.destroy()


class TeamEditor(ttk.Frame):
    """球队编辑器"""
    
    def __init__(self, parent, team_data: Optional[Dict] = None, on_select=None, on_delete=None, is_selected=False):
        super().__init__(parent)
        self.on_select = on_select
        self.on_delete = on_delete
        self.team_id = team_data.get("id") if team_data else f"team_{uuid.uuid4().hex[:6]}"
        self.players: List[str] = []
        self.is_selected = is_selected
        
        self._create_widgets()
        if team_data:
            self._load_data(team_data)
    
    def _create_widgets(self):
        bg = COLORS["primary_light"] if self.is_selected else COLORS["card_bg"]
        
        self.frame = tk.Frame(self, bg=bg, relief=tk.RIDGE, bd=1, padx=10, pady=8)
        self.frame.pack(fill=tk.X, padx=4, pady=3)
        
        # 第一行：球队名和城市 + 删除按钮
        row1 = tk.Frame(self.frame, bg=bg)
        row1.pack(fill=tk.X, pady=2)
        
        tk.Label(row1, text="队名:", bg=bg, fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.name_var, width=12,
                 font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT, padx=(3, 10))
        
        tk.Label(row1, text="城市:", bg=bg, fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.city_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.city_var, width=8,
                 font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT, padx=3)
        
        # 删除按钮（放在第一行右侧）
        delete_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="white",
                              relief=tk.FLAT, font=("Microsoft YaHei UI", 9, "bold"), 
                              cursor="hand2", width=2, command=self._on_delete)
        delete_btn.pack(side=tk.RIGHT, padx=2)
        
        # 第二行：状态和球员数
        row2 = tk.Frame(self.frame, bg=bg)
        row2.pack(fill=tk.X, pady=2)
        
        tk.Label(row2, text="状态:", bg=bg, fg=COLORS["text_secondary"],
                font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="stable")
        status_combo = ttk.Combobox(row2, textvariable=self.status_var, values=TEAM_STATUS,
                                    width=10, state="readonly", font=("Microsoft YaHei UI", 9))
        status_combo.pack(side=tk.LEFT, padx=(3, 15))
        
        self.player_count_label = tk.Label(row2, text="👥 0人", bg=bg, fg=COLORS["primary"],
                                          font=("Microsoft YaHei UI", 9, "bold"))
        self.player_count_label.pack(side=tk.LEFT)
        
        # 编辑按钮
        edit_btn = tk.Button(row2, text="编辑球员 →", bg=COLORS["primary"], fg="white",
                            relief=tk.FLAT, font=("Microsoft YaHei UI", 9), cursor="hand2",
                            padx=10, command=self._on_select)
        edit_btn.pack(side=tk.RIGHT)
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        bg = COLORS["primary_light"] if selected else COLORS["card_bg"]
        self.frame.configure(bg=bg)
        for widget in self.frame.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=bg)
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg=bg)
    
    def _on_select(self):
        if self.on_select:
            self.on_select(self)
    
    def _on_delete(self):
        if self.on_delete:
            self.on_delete(self)
    
    def _load_data(self, data: Dict):
        self.team_id = data.get("id", self.team_id)
        self.name_var.set(data.get("name", ""))
        self.city_var.set(data.get("city", ""))
        self.status_var.set(data.get("status", "stable"))
        self.players = data.get("roster", [])
        self._update_player_count()
    
    def _update_player_count(self):
        count = len(self.players)
        color = COLORS["success"] if count >= 12 else (COLORS["warning"] if count >= 8 else COLORS["danger"])
        self.player_count_label.config(text=f"👥 {count}人", fg=color)
    
    def set_players(self, player_ids: List[str]):
        self.players = player_ids
        self._update_player_count()
    
    def get_data(self) -> Dict:
        return {
            "id": self.team_id,
            "name": self.name_var.get(),
            "city": self.city_var.get(),
            "status": self.status_var.get(),
            "is_player_controlled": False,
            "roster": self.players
        }



class RosterCreatorApp:
    """主应用程序"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🏀 华夏篮球联赛 球员/球队自定义生成工具")
        self.root.geometry("1200x750")
        self.root.configure(bg=COLORS["bg"])
        
        self.teams: List[TeamEditor] = []
        self.players: Dict[str, List[PlayerEditor]] = {}
        self.current_team: Optional[TeamEditor] = None
        
        self._setup_style()
        self._create_menu()
        self._create_ui()
    
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], font=("Microsoft YaHei UI", 9))
        style.configure("TButton", font=("Microsoft YaHei UI", 9))
        style.configure("TEntry", font=("Microsoft YaHei UI", 10))
        style.configure("TSpinbox", font=("Microsoft YaHei UI", 10))
        style.configure("TCombobox", font=("Microsoft YaHei UI", 10))
    
    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建项目", command=self._new_project)
        file_menu.add_command(label="导入数据", command=self._import_data)
        file_menu.add_separator()
        file_menu.add_command(label="导出数据", command=self._export_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self._show_help)
    
    def _create_ui(self):
        # 顶部标题栏
        header = tk.Frame(self.root, bg=COLORS["primary"], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🏀 华夏篮球联赛 球员/球队自定义生成工具", bg=COLORS["primary"], fg="white",
                font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.LEFT, padx=20, pady=10)
        
        # 顶部按钮
        btn_frame = tk.Frame(header, bg=COLORS["primary"])
        btn_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Button(btn_frame, text="📂 导入", bg="white", fg=COLORS["primary"],
                 font=("Microsoft YaHei UI", 10), relief=tk.FLAT, padx=15, cursor="hand2",
                 command=self._import_data).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="💾 导出", bg=COLORS["success"], fg="white",
                 font=("Microsoft YaHei UI", 10, "bold"), relief=tk.FLAT, padx=15, cursor="hand2",
                 command=self._export_data).pack(side=tk.LEFT, padx=5)
        
        # 主内容区
        main_frame = tk.Frame(self.root, bg=COLORS["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：球队列表
        left_panel = tk.Frame(main_frame, bg=COLORS["card_bg"], relief=tk.RIDGE, bd=1)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 球队标题
        team_header = tk.Frame(left_panel, bg=COLORS["card_bg"], padx=10, pady=10)
        team_header.pack(fill=tk.X)
        
        tk.Label(team_header, text="球队列表", bg=COLORS["card_bg"], fg=COLORS["text"],
                font=("Microsoft YaHei UI", 12, "bold")).pack(side=tk.LEFT)
        
        self.team_count_label = tk.Label(team_header, text="(0/20)", bg=COLORS["card_bg"],
                                        fg=COLORS["text_secondary"], font=("Microsoft YaHei UI", 10))
        self.team_count_label.pack(side=tk.LEFT, padx=5)
        
        # 球队工具栏
        team_toolbar = tk.Frame(left_panel, bg=COLORS["card_bg"], padx=10, pady=5)
        team_toolbar.pack(fill=tk.X)
        
        tk.Button(team_toolbar, text="+ 添加球队", bg=COLORS["primary"], fg="white",
                 font=("Microsoft YaHei UI", 9), relief=tk.FLAT, padx=10, cursor="hand2",
                 command=self._add_team).pack(side=tk.LEFT)
        
        tk.Button(team_toolbar, text="- 删除", bg=COLORS["danger"], fg="white",
                 font=("Microsoft YaHei UI", 9), relief=tk.FLAT, padx=10, cursor="hand2",
                 command=self._delete_team).pack(side=tk.LEFT, padx=5)
        
        # 球队滚动区域
        self.team_scroll = ScrollableFrame(left_panel)
        self.team_scroll.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.team_frame = self.team_scroll.scrollable_frame
        
        # 右侧：球员编辑区
        right_panel = tk.Frame(main_frame, bg=COLORS["card_bg"], relief=tk.RIDGE, bd=1)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 球员标题
        player_header = tk.Frame(right_panel, bg=COLORS["card_bg"], padx=10, pady=10)
        player_header.pack(fill=tk.X)
        
        self.current_team_label = tk.Label(player_header, text="请先选择一支球队",
                                          bg=COLORS["card_bg"], fg=COLORS["text"],
                                          font=("Microsoft YaHei UI", 12, "bold"))
        self.current_team_label.pack(side=tk.LEFT)
        
        self.player_count_label = tk.Label(player_header, text="", bg=COLORS["card_bg"],
                                          fg=COLORS["text_secondary"], font=("Microsoft YaHei UI", 10))
        self.player_count_label.pack(side=tk.LEFT, padx=10)
        
        # 球员工具栏
        player_toolbar = tk.Frame(right_panel, bg=COLORS["card_bg"], padx=10, pady=5)
        player_toolbar.pack(fill=tk.X)
        
        tk.Button(player_toolbar, text="+ 添加球员", bg=COLORS["primary"], fg="white",
                 font=("Microsoft YaHei UI", 9), relief=tk.FLAT, padx=10, cursor="hand2",
                 command=self._add_player).pack(side=tk.LEFT)
        
        tk.Label(player_toolbar, text="建议每队12人", bg=COLORS["card_bg"],
                fg=COLORS["text_secondary"], font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=15)
        
        # 球员滚动区域
        self.player_scroll = ScrollableFrame(right_panel)
        self.player_scroll.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.player_frame = self.player_scroll.scrollable_frame
    
    def _update_team_count(self):
        count = len(self.teams)
        color = COLORS["success"] if count == 20 else (COLORS["warning"] if count >= 15 else COLORS["text_secondary"])
        self.team_count_label.config(text=f"({count}/20)", fg=color)
    
    def _update_player_count(self):
        if not self.current_team:
            self.player_count_label.config(text="")
            return
        team_id = self.current_team.team_id
        count = len(self.players.get(team_id, []))
        color = COLORS["success"] if count >= 12 else (COLORS["warning"] if count >= 8 else COLORS["danger"])
        self.player_count_label.config(text=f"({count}人)", fg=color)
    
    def _add_team(self):
        if len(self.teams) >= 20:
            messagebox.showwarning("提示", "最多只能创建20支球队")
            return
        
        team = TeamEditor(self.team_frame, on_select=self._select_team, on_delete=self._delete_team_direct)
        team.pack(fill=tk.X, pady=2)
        self.teams.append(team)
        self.players[team.team_id] = []
        self._update_team_count()
    
    def _delete_team_direct(self, team: TeamEditor):
        """直接删除指定球队"""
        name = team.name_var.get() or "未命名"
        if messagebox.askyesno("确认删除", f"确定要删除球队「{name}」吗？\n该球队的所有球员也将被删除。"):
            team_id = team.team_id
            self.teams.remove(team)
            team.destroy()
            
            if team_id in self.players:
                del self.players[team_id]
            
            # 如果删除的是当前选中的球队，清空右侧
            if self.current_team == team:
                self.current_team = None
                self._clear_player_frame()
                self.current_team_label.config(text="请先选择一支球队")
                self._update_player_count()
            
            self._update_team_count()
    
    def _delete_team(self):
        """工具栏删除按钮（删除当前选中的球队）"""
        if not self.current_team:
            messagebox.showinfo("提示", "请先选择要删除的球队")
            return
        self._delete_team_direct(self.current_team)
    
    def _select_team(self, team: TeamEditor):
        # 取消之前选中的高亮
        if self.current_team:
            self.current_team.set_selected(False)
        
        self.current_team = team
        team.set_selected(True)
        
        name = team.name_var.get() or "未命名"
        self.current_team_label.config(text=f"当前球队: {name}")
        self._refresh_player_list()
        self._update_player_count()
    
    def _clear_player_frame(self):
        for widget in self.player_frame.winfo_children():
            widget.pack_forget()  # 只是隐藏，不销毁
    
    def _refresh_player_list(self):
        # 先隐藏所有
        for widget in self.player_frame.winfo_children():
            widget.pack_forget()
        
        if not self.current_team:
            return
        
        team_id = self.current_team.team_id
        if team_id not in self.players:
            self.players[team_id] = []
        
        # 重新显示当前球队的球员
        for i, player in enumerate(self.players[team_id]):
            # 确保球员编辑器的父容器是player_frame
            if player.winfo_exists():
                player.set_index(i)
                player.pack(fill=tk.X, pady=2)
    
    def _add_player(self):
        if not self.current_team:
            messagebox.showinfo("提示", "请先选择一支球队")
            return
        
        team_id = self.current_team.team_id
        if team_id not in self.players:
            self.players[team_id] = []
        
        index = len(self.players[team_id])
        player = PlayerEditor(self.player_frame, on_delete=self._delete_player, index=index)
        player.pack(fill=tk.X, pady=2)
        self.players[team_id].append(player)
        self._update_player_count()
        
        # 更新球队的球员数显示
        self.current_team.players = [p.player_id for p in self.players[team_id]]
        self.current_team._update_player_count()
    
    def _delete_player(self, player: PlayerEditor):
        if not self.current_team:
            return
        
        team_id = self.current_team.team_id
        if team_id in self.players and player in self.players[team_id]:
            self.players[team_id].remove(player)
            player.destroy()
            
            # 更新序号
            for i, p in enumerate(self.players[team_id]):
                p.set_index(i)
            
            self._update_player_count()
            
            # 更新球队的球员数显示
            self.current_team.players = [p.player_id for p in self.players[team_id]]
            self.current_team._update_player_count()
    
    def _new_project(self):
        if messagebox.askyesno("新建项目", "确定要新建项目吗？\n当前未保存的数据将丢失。"):
            # 销毁所有球员编辑器
            for team_id, player_list in self.players.items():
                for player in player_list:
                    if player.winfo_exists():
                        player.destroy()
            
            # 销毁所有球队
            for team in self.teams:
                team.destroy()
            
            self.teams.clear()
            self.players.clear()
            self.current_team = None
            self.current_team_label.config(text="请先选择一支球队")
            self._update_team_count()
            self._update_player_count()
    
    def _import_data(self):
        # 让用户选择 players.json 或 teams.json 文件
        file_path = filedialog.askopenfilename(
            title="选择 players.json 或 teams.json 文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        
        # 获取文件所在目录
        folder = os.path.dirname(file_path)
        players_file = os.path.join(folder, "players.json")
        teams_file = os.path.join(folder, "teams.json")
        
        # 检查两个文件是否都存在
        missing_files = []
        if not os.path.exists(players_file):
            missing_files.append("players.json")
        if not os.path.exists(teams_file):
            missing_files.append("teams.json")
        
        if missing_files:
            messagebox.showerror("错误", 
                f"在目录 {folder} 中找不到以下文件:\n" + 
                "\n".join(f"• {f}" for f in missing_files) +
                "\n\n请确保 players.json 和 teams.json 在同一个文件夹中。")
            return
        
        try:
            with open(players_file, "r", encoding="utf-8") as f:
                players_data = json.load(f)
            with open(teams_file, "r", encoding="utf-8") as f:
                teams_data = json.load(f)
            
            # 清空现有数据 - 先销毁所有球员编辑器
            for team_id, player_list in self.players.items():
                for player in player_list:
                    if player.winfo_exists():
                        player.destroy()
            
            for team in self.teams:
                team.destroy()
            self.teams.clear()
            self.players.clear()
            
            # 导入球队
            for team_id, team_info in teams_data.get("teams", {}).items():
                team = TeamEditor(self.team_frame, team_data=team_info, on_select=self._select_team, on_delete=self._delete_team_direct)
                team.pack(fill=tk.X, pady=2)
                self.teams.append(team)
                self.players[team_id] = []
            
            # 导入球员（先不显示，等用户选择球队时再显示）
            total_players = 0
            for player_id, player_info in players_data.get("players", {}).items():
                team_id = player_info.get("team_id")
                if team_id and team_id in self.players:
                    player_info["id"] = player_id
                    index = len(self.players[team_id])
                    player = PlayerEditor(self.player_frame, player_data=player_info,
                                         on_delete=self._delete_player, index=index)
                    # 不立即pack，等选择球队时再显示
                    self.players[team_id].append(player)
                    total_players += 1
            
            # 更新球队球员数显示
            for team in self.teams:
                player_count = len(self.players.get(team.team_id, []))
                team.players = [p.player_id for p in self.players.get(team.team_id, [])]
                team._update_player_count()
            
            self.current_team = None
            self.current_team_label.config(text="请先选择一支球队查看/编辑球员")
            self._update_team_count()
            self._update_player_count()
            
            messagebox.showinfo("导入成功", 
                              f"成功导入数据！\n\n"
                              f"• 球队: {len(self.teams)} 支\n"
                              f"• 球员: {total_players} 人\n\n"
                              f"点击左侧球队的「编辑球员」按钮查看和修改球员信息。")
            
        except Exception as e:
            messagebox.showerror("导入失败", f"错误: {str(e)}")
    
    def _export_data(self):
        if not self.teams:
            messagebox.showwarning("提示", "没有可导出的数据，请先创建球队和球员")
            return
        
        folder = filedialog.askdirectory(title="选择导出目录")
        if not folder:
            return
        
        try:
            teams_output = {"teams": {}}
            players_output = {"players": {}}
            
            for team in self.teams:
                team_data = team.get_data()
                team_id = team_data["id"]
                
                player_ids = []
                if team_id in self.players:
                    for player_editor in self.players[team_id]:
                        player_data = player_editor.get_data()
                        player_data["team_id"] = team_id
                        players_output["players"][player_data["id"]] = player_data
                        player_ids.append(player_data["id"])
                
                team_data["roster"] = player_ids
                teams_output["teams"][team_id] = team_data
            
            players_file = os.path.join(folder, "players.json")
            teams_file = os.path.join(folder, "teams.json")
            
            with open(players_file, "w", encoding="utf-8") as f:
                json.dump(players_output, f, ensure_ascii=False, indent=2)
            
            with open(teams_file, "w", encoding="utf-8") as f:
                json.dump(teams_output, f, ensure_ascii=False, indent=2)
            
            total_players = len(players_output["players"])
            messagebox.showinfo("导出成功", 
                              f"已导出 {len(self.teams)} 支球队，{total_players} 名球员\n\n"
                              f"文件位置:\n{players_file}\n{teams_file}")
            
        except Exception as e:
            messagebox.showerror("导出失败", f"错误: {str(e)}")
    
    def _show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("500x450")
        help_window.configure(bg=COLORS["bg"])
        
        # 标题
        tk.Label(help_window, text="使用说明", bg=COLORS["primary"], fg="white",
                font=("Microsoft YaHei UI", 12, "bold"), pady=10).pack(fill=tk.X)
        
        help_text = """
1. 创建球队
   • 点击「+ 添加球队」创建新球队
   • 填写球队名称、城市和状态
   • 最多可创建20支球队

2. 编辑球员
   • 选择球队后点击「+ 添加球员」
   • 拖动滑块调整各项能力值
   • 系统自动计算总评（可手动修改）
   • 建议每队配置12名球员

3. 导入/导出
   • 可导入现有的 players.json 和 teams.json
   • 编辑完成后导出到指定目录
   • 将文件放入 player_data 目录即可使用

4. 能力值说明
   • 进攻/防守/三分/传球/篮板/体力: 1-99
   • 总评: 综合能力评分
   • 交易指数: 影响AI交易意愿 (1-100)

5. 技能标签
   • 每个球员最多选择3个技能标签
   • 点击「选择」按钮从预设列表中选择
        """
        
        text_widget = tk.Text(help_window, bg=COLORS["card_bg"], fg=COLORS["text"],
                             font=("Microsoft YaHei UI", 10), padx=20, pady=15,
                             relief=tk.FLAT, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert("1.0", help_text)
        text_widget.config(state=tk.DISABLED)
        
        help_window.transient(self.root)
        help_window.grab_set()


def main():
    root = tk.Tk()
    app = RosterCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
