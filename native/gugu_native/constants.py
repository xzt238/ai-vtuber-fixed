"""
咕咕嘎嘎 AI-VTuber — 全局常量定义

集中管理魔法数字，提高代码可维护性。
"""

# ========== 性能相关 ==========
# 内存阈值 (MB)
MEMORY_WARNING_THRESHOLD = 3500
MEMORY_CRITICAL_THRESHOLD = 5500

# GC 间隔 (ms)
GC_GEN0_INTERVAL_MS = 5000    # gen0: 每 5s
GC_GEN1_INTERVAL_MS = 30000   # gen1: 每 30s
GC_GEN2_INTERVAL_MS = 120000  # gen2: 每 120s

# ========== UI 相关 ==========
# 窗口尺寸
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 600
WINDOW_DEFAULT_WIDTH = 1280
WINDOW_DEFAULT_HEIGHT = 800

# 导航栏
NAV_EXPAND_WIDTH = 200

# 动画持续时间 (ms)
ANIMATION_DURATION_FAST = 150
ANIMATION_DURATION_NORMAL = 300
ANIMATION_DURATION_SLOW = 500

# ========== Live2D 相关 ==========
# 口型同步
LIPSYNC_UPDATE_INTERVAL_MS = 100  # 每 100ms 更新一次
LIPSYNC_MOUTH_MIN = 0.3
LIPSYNC_MOUTH_MAX = 1.0

# 模型尺寸
DEFAULT_MODEL_WIDTH = 380
DEFAULT_MODEL_HEIGHT = 535
DEFAULT_MODEL_FPS = 60

# ========== TTS 相关 ==========
# 音频队列
AUDIO_QUEUE_MAX_SIZE = 100

# 流式 TTS
STREAMING_TTS_COMPRESS_THRESHOLD = 120
STREAMING_TTS_KEEP_RECENT = 40

# ========== 对话历史 ==========
HISTORY_MAX_SIZE = 100
HISTORY_SAVE_SIZE = 200
HISTORY_DISPLAY_SIZE = 20

# ========== 录音相关 ==========
RECORDING_SAMPLE_RATE = 16000
RECORDING_CHANNELS = 1

# ========== 搜索相关 ==========
SEARCH_RESULTS_MAX = 100

# ========== 主题相关 ==========
THEME_CALLBACK_DEBOUNCE_MS = 100

# ========== 更新检查 ==========
UPDATE_CHECK_DELAY_MS = 10000  # 10 秒后检查更新

# ========== 启动画面 ==========
SPLASH_SKIP_BUTTON_DELAY_MS = 10000  # 10 秒后显示跳过按钮

# ========== 网络相关 ==========
HTTP_TIMEOUT_SECONDS = 30
WEBSOCKET_PING_INTERVAL_MS = 30000

# ========== 文件路径 ==========
CONFIG_FILENAME = "config.yaml"
HISTORY_FILENAME = "native_chat_history.json"
TTS_PREFS_FILENAME = "tts_preferences.json"
VRM_DISPLAY_CONFIG_FILENAME = "vrm_display.json"

# ========== 颜色常量 ==========
# 日志颜色
LOG_COLOR_SUCCESS = "#4ade80"
LOG_COLOR_ERROR = "#f87171"
LOG_COLOR_WARNING = "#fbbf24"
LOG_COLOR_INFO = "#60a5fa"
LOG_COLOR_DEBUG = "#a78bfa"

# ========== 消息类型 ==========
MSG_TYPE_USER = "user"
MSG_TYPE_ASSISTANT = "assistant"
MSG_TYPE_SYSTEM = "system"

# ========== 模型类型 ==========
MODEL_TYPE_LIVE2D = "live2d"
MODEL_TYPE_VRM = "vrm"

# ========== TTS 引擎 ==========
TTS_ENGINE_EDGE = "Edge TTS"
TTS_ENGINE_GPTSOVITS = "GPT-SoVITS"

# ========== 日志级别 ==========
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"
