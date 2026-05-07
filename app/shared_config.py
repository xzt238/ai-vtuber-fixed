"""
项目共享配置数据（单一数据源）

消除三处维护同一数据的重复问题：
- app/shared_config.py          ← 唯一数据源（本文件）
- settings_page.py:PROVIDER_CONFIG  ← 引用本文件
- index.html:_providerConfig        ← 需手动同步（JS 无法 import Python）
- settings_page.py:EDGE_VOICES      ← 引用本文件
- index.html:voiceOptions.edge      ← 需手动同步

⚠️ JS 文件无法自动 import Python，修改后需手动同步到 index.html。
   详见 docs/CHANGE_IMPACT_MAP.md
"""

# ============================================================
# LLM Provider 配置（10 个供应商）
# 修改此数据后需同步到: index.html 的 _providerConfig 对象
# ============================================================
PROVIDER_CONFIG = {
    "deepseek": {
        "label": "DeepSeek",
        "baseUrl": "https://api.deepseek.com",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
        "defaultModel": "deepseek-chat",
        "keyPlaceholder": "在 platform.deepseek.com 获取",
    },
    "kimi": {
        "label": "Kimi",
        "baseUrl": "https://api.moonshot.cn/v1",
        "models": ["kimi-k2.6", "kimi-k2.5", "kimi-k2-thinking", "kimi-k2-thinking-turbo", "kimi-k2-0905-preview", "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
        "defaultModel": "kimi-k2.6",
        "keyPlaceholder": "在 platform.kimi.com 获取",
    },
    "glm": {
        "label": "智谱 GLM",
        "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["GLM-5.1", "GLM-5", "GLM-5-Turbo", "GLM-4.7", "GLM-4.7-FlashX", "GLM-4.6", "GLM-4.5-Air", "GLM-4-Long", "GLM-4.7-Flash"],
        "defaultModel": "GLM-4.7-FlashX",
        "keyPlaceholder": "在 open.bigmodel.cn 获取",
    },
    "qwen": {
        "label": "通义千问",
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3.6-max-preview", "qwen3.6-plus", "qwen3.6-flash", "qwen-max", "qwen-plus", "qwen-turbo"],
        "defaultModel": "qwen3.6-plus",
        "keyPlaceholder": "在 dashscope.console.aliyun.com 获取",
    },
    "minimax": {
        "label": "MiniMax",
        "baseUrl": "https://api.minimaxi.com/anthropic",
        "models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.5-highspeed", "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2"],
        "defaultModel": "MiniMax-M2.7",
        "keyPlaceholder": "在 minimaxi.com 获取",
    },
    "doubao": {
        "label": "豆包",
        "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-seed-1-8-250415", "doubao-seed-1-6-251015", "doubao-seed-1-6-flash-250415", "doubao-1.5-pro-32k", "doubao-1.5-pro-256k", "doubao-1.5-lite-32k"],
        "defaultModel": "doubao-1.5-pro-32k",
        "keyPlaceholder": "在 console.volcengine.com/ark 获取",
    },
    "mimo": {
        "label": "小米 MiMo",
        "baseUrl": "https://api.xiaomimimo.com/v1",
        "models": ["mimo-v2.5-pro", "mimo-v2.5", "mimo-v2.5-flash"],
        "defaultModel": "mimo-v2.5",
        "keyPlaceholder": "在 platform.xiaomimimo.com 获取",
    },
    "openai": {
        "label": "OpenAI",
        "baseUrl": "https://api.openai.com/v1",
        "models": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o3", "o4-mini"],
        "defaultModel": "gpt-4o-mini",
        "keyPlaceholder": "在 platform.openai.com 获取",
    },
    "anthropic": {
        "label": "Anthropic",
        "baseUrl": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-6-20260219", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251015", "claude-opus-4-20250514"],
        "defaultModel": "claude-sonnet-4-5-20250929",
        "keyPlaceholder": "在 console.anthropic.com 获取",
    },
    "ollama": {
        "label": "Ollama (本地)",
        "baseUrl": "http://localhost:11434/v1",
        "models": [],  # 运行时动态获取
        "defaultModel": "qwen3:8b",
        "keyPlaceholder": "ollama",
    },
}

# ============================================================
# Edge TTS 音色列表（单一数据源）
# 修改此数据后需同步到: index.html 的 voiceOptions.edge 数组
# ============================================================
EDGE_VOICES = [
    ("zh-CN-XiaoxiaoNeural", "中文女声 (标准)"),
    ("zh-CN-XiaoyiNeural", "中文女声 (年轻)"),
    ("zh-CN-YunxiNeural", "中文男声 (云希)"),
    ("zh-CN-YunyangNeural", "中文男声 (云扬)"),
    ("zh-HK-HiuGaaiNeural", "粤语女声"),
    ("zh-HK-HiuMaanNeural", "粤语女声2"),
    ("zh-TW-HsiaoChenNeural", "台湾女声"),
    ("zh-TW-HsiaoYuNeural", "台湾女声2"),
]

# ============================================================
# 表情关键词映射（单一数据源）
# 修改此数据后需同步到: index.html 的 expressionKeywords / expressionMap
# ============================================================
EXPRESSION_KEYWORDS = {
    "happy": ["开心", "高兴", "快乐", "好开心", "哈哈", "笑", "太棒", "太好了", "嘻", "棒", "赞", "爱你", "喜欢", "么么哒", "可爱", "萌"],
    "smile": ["微笑", "嗯", "好的", "可以", "行", "没问题", "了解", "知道", "明白", "懂", "是", "对"],
    "shine": ["哇", "啊", "惊讶", "惊喜", "厉害", "太厉害", "真的吗", "真的假的", "天哪", "我的天", "哇塞", "哇哦", "好厉害", "惊了"],
    "sad": ["难过", "伤心", "哭", "悲伤", "遗憾", "可惜", "唉", "郁闷", "烦"],
    "angry": ["生气", "愤怒", "哼", "气死", "可恶", "烦死了"],
    "surprised": ["惊讶", "震惊", "什么", "怎么", "为什么", "啥", "啥情况"],
}

EXPRESSION_MAP = {
    "happy": "f02",
    "smile": "f03",
    "shine": "f04",
    "neutral": "f01",
    "sad": "f03",      # Shizuku 没有悲伤表情，用微笑代替
    "angry": "f03",    # 生气用微笑
    "surprised": "f04", # 惊讶用闪亮
}

# ============================================================
# 互斥体名称（单一数据源）
# launcher 和 native 模式必须使用相同前缀才能互相检测
# ============================================================
MUTEX_NAME_BASE = "Local\\GuguGagaAI-VTuber"
MUTEX_NAME_LAUNCHER = MUTEX_NAME_BASE + "_Launcher"
MUTEX_NAME_NATIVE = MUTEX_NAME_BASE + "_Native"
