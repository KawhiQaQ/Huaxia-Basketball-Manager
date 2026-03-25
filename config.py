"""
华夏篮球联赛教练模拟器 - LLM API配置文件

支持配置国内大语言模型API（如DeepSeek、Qwen等）
"""
import os


class LLMConfig:
    """LLM API配置类"""
    
    # API密钥 - 优先从环境变量读取
    # API_KEY: str = os.getenv("LLM_API_KEY", "")
    API_KEY: str = "your_api_key"
    
    # API端点 - 默认使用DeepSeek
    BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    
    # 模型名称
    MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
    
    # 请求超时时间（秒）
    TIMEOUT: int = 90
    
    # 最大重试次数
    MAX_RETRIES: int = 3
    
    # 温度参数（控制随机性）
    TEMPERATURE: float = 0.7
    
    # 最大token数
    MAX_TOKENS: int = 8000
    
    # 并发请求配置
    # 最大并发请求数（同时发送的LLM请求数量）
    # 建议值: 3-5，过高可能触发API限流
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("LLM_MAX_CONCURRENT", "5"))
    
    # 是否启用并发模拟（批量模拟AI比赛时使用）
    ENABLE_CONCURRENT_SIMULATION: bool = os.getenv("LLM_ENABLE_CONCURRENT", "true").lower() == "true"


class SimulationConfig:
    """模拟配置类 - 用于调试切换LLM/本地算法"""
    
    # 是否使用LLM进行比赛模拟
    USE_LLM: bool = True


class GameConfig:
    """游戏配置类"""
    
    # 数据文件路径
    PLAYER_DATA_DIR: str = "player_data"
    SAVES_DIR: str = "saves"
    
    # 球员数据文件
    PLAYERS_FILE: str = "players.json"
    TEAMS_FILE: str = "teams.json"
    
    # 赛季配置
    REGULAR_SEASON_GAMES: int = 42
    TOTAL_TEAMS: int = 20
    PLAYOFF_TEAMS: int = 12
    
    # 属性范围
    MIN_ATTRIBUTE: int = 0
    MAX_ATTRIBUTE: int = 99
    
    # 训练提升范围
    TRAINING_MIN_BOOST: int = 1
    TRAINING_MAX_BOOST: int = 3
    
    # 伤病配置
    INJURY_PROBABILITY: float = 0.01
    INJURY_MIN_DAYS: int = 3
    INJURY_MAX_DAYS: int = 21
    
    # 季后赛AI能力值调整范围
    PLAYOFF_AI_ADJUSTMENT_MIN: int = -2
    PLAYOFF_AI_ADJUSTMENT_MAX: int = 2
