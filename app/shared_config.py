import logging
"""
项目共享配置数据（单一数据源）

logger = logging.getLogger(__name__)

消除多处维护同一数据的重复问题：
- app/shared_config.py          ← 唯一数据源（本文件）
- settings_page.py:PROVIDER_CONFIG  ← 引用本文件
- index.html:_providerConfig        ← 通过 /api/config.js 动态加载（KI-001）
- settings_page.py:EDGE_VOICES      ← 引用本文件
- index.html:voiceOptions.edge      ← 通过 /api/config.js 动态加载

修改 PROVIDER_CONFIG / EDGE_VOICES / EXPRESSION_* 后无需手动同步 JS，
前端通过 <script src="/api/config.js"> 自动获取最新数据。
"""

import os
from pathlib import Path

# ============================================================
# LLM Provider 配置（10 个供应商）
# 前端通过 /api/config.js 动态加载，修改后自动生效（KI-001）
# ============================================================
PROVIDER_CONFIG = {
    "deepseek": {
        "label": "DeepSeek",
        "baseUrl": "https://api.deepseek.com",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
        "defaultModel": "deepseek-chat",
        "hint": "官方 base_url 不带 /v1（API 自动兼容）。chat/reasoner 将于 2026/07 弃用，建议用 v4-flash",
        "keyPlaceholder": "在 platform.deepseek.com 获取",
        "color": {"bg": "rgba(76,175,80,0.25)", "fg": "#81c784"},
    },
    "kimi": {
        "label": "Kimi",
        "baseUrl": "https://api.moonshot.cn/v1",
        "models": ["kimi-k2.6", "kimi-k2.5", "kimi-k2-thinking", "kimi-k2-thinking-turbo", "kimi-k2-0905-preview", "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
        "defaultModel": "kimi-k2.6",
        "hint": "Kimi K2.6 最新模型，256K 长上下文，支持 thinking 模式",
        "keyPlaceholder": "在 platform.kimi.com 获取",
        "color": {"bg": "rgba(156,39,176,0.25)", "fg": "#ce93d8"},
    },
    "glm": {
        "label": "智谱 GLM",
        "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["GLM-5.1", "GLM-5", "GLM-5-Turbo", "GLM-4.7", "GLM-4.7-FlashX", "GLM-4.6", "GLM-4.5-Air", "GLM-4-Long", "GLM-4.7-Flash"],
        "defaultModel": "GLM-4.7-FlashX",
        "hint": "GLM-5.1 最新旗舰，GLM-4.7-FlashX 性价比最高（免费）",
        "keyPlaceholder": "在 open.bigmodel.cn 获取",
        "color": {"bg": "rgba(33,150,243,0.25)", "fg": "#64b5f6"},
    },
    "qwen": {
        "label": "通义千问",
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3.6-max-preview", "qwen3.6-plus", "qwen3.6-flash", "qwen-max", "qwen-plus", "qwen-turbo"],
        "defaultModel": "qwen3.6-plus",
        "hint": "阿里云百炼平台，qwen3.6 系列最新，兼容 OpenAI 格式",
        "keyPlaceholder": "在 dashscope.console.aliyun.com 获取",
        "color": {"bg": "rgba(255,152,0,0.25)", "fg": "#ffb74d"},
    },
    "minimax": {
        "label": "MiniMax",
        "baseUrl": "https://api.minimaxi.com/anthropic",
        "models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.5-highspeed", "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2"],
        "defaultModel": "MiniMax-M2.7",
        "hint": "推荐 Anthropic 格式（默认），也可切换到 OpenAI 格式 api.minimaxi.com/v1",
        "keyPlaceholder": "在 minimaxi.com 获取",
        "color": {"bg": "rgba(102,126,234,0.3)", "fg": "#a8b5ff"},
    },
    "doubao": {
        "label": "豆包",
        "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-seed-1-8-250415", "doubao-seed-1-6-251015", "doubao-seed-1-6-flash-250415", "doubao-1.5-pro-32k", "doubao-1.5-pro-256k", "doubao-1.5-lite-32k"],
        "defaultModel": "doubao-1.5-pro-32k",
        "hint": "火山方舟平台，doubao-seed 系列最新旗舰，兼容 OpenAI 格式",
        "keyPlaceholder": "在 console.volcengine.com/ark 获取",
        "color": {"bg": "rgba(0,188,212,0.25)", "fg": "#4dd0e1"},
    },
    "mimo": {
        "label": "小米 MiMo",
        "baseUrl": "https://api.xiaomimimo.com/v1",
        "models": ["mimo-v2.5-pro", "mimo-v2.5", "mimo-v2.5-flash"],
        "defaultModel": "mimo-v2.5",
        "hint": "小米 MiMo V2.5，1M 长上下文，兼容 OpenAI 格式",
        "keyPlaceholder": "在 platform.xiaomimimo.com 获取",
        "color": {"bg": "rgba(255,87,34,0.25)", "fg": "#ff8a65"},
    },
    "openai": {
        "label": "OpenAI",
        "baseUrl": "https://api.openai.com/v1",
        "models": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o3", "o4-mini"],
        "defaultModel": "gpt-4o-mini",
        "hint": "OpenAI 官方 API，gpt-4.1 系列最新，也可接入兼容代理",
        "keyPlaceholder": "在 platform.openai.com 获取",
        "color": {"bg": "rgba(102,126,234,0.3)", "fg": "#a8b5ff"},
    },
    "anthropic": {
        "label": "Anthropic",
        "baseUrl": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-6-20260219", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251015", "claude-opus-4-20250514"],
        "defaultModel": "claude-sonnet-4-5-20250929",
        "hint": "Claude 4.6 Sonnet 最新旗舰，4.5 Sonnet 性价比最高",
        "keyPlaceholder": "在 console.anthropic.com 获取",
        "color": {"bg": "rgba(204,120,50,0.25)", "fg": "#e8a65d"},
    },
    "ollama": {
        "label": "Ollama (本地)",
        "baseUrl": "http://localhost:11434/v1",
        "models": [],  # 运行时动态获取
        "defaultModel": "qwen3:8b",
        "hint": "本地模型，API Key 填 ollama，模型列表自动从 Ollama 获取",
        "keyPlaceholder": "ollama",
        "color": {"bg": "rgba(76,175,80,0.25)", "fg": "#81c784"},
    },
}

# ============================================================
# 文生图 Provider 配置
# ============================================================
IMAGE_GEN_CONFIG = {
    "wanx": {
        "label": "通义万相",
        "baseUrl": "https://dashscope.aliyuncs.com",
        "models": ["wanx-v1", "wanx2.1-t2i-turbo", "wanx2.1-t2i-plus", "wanx2.1-t2i-max"],
        "defaultModel": "wanx2.1-t2i-turbo",
        "hint": "阿里云通义万相文生图，中文优化",
        "keyPlaceholder": "在 dashscope.console.aliyun.com 获取",
        "color": {"bg": "rgba(255,152,0,0.25)", "fg": "#ffb74d"},
    },
    "cogview": {
        "label": "智谱 CogView",
        "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["cogview-4", "cogview-4-plus", "cogview-3-flash"],
        "defaultModel": "cogview-4",
        "hint": "智谱AI CogView文生图，支持中文",
        "keyPlaceholder": "在 open.bigmodel.cn 获取",
        "color": {"bg": "rgba(33,150,243,0.25)", "fg": "#64b5f6"},
    },
    "kolors": {
        "label": "可图",
        "baseUrl": "https://api.kolors.com",
        "models": ["kolors", "kolors-plus"],
        "defaultModel": "kolors",
        "hint": "可图文生图，高质量",
        "keyPlaceholder": "在 kolors.com 获取",
        "color": {"bg": "rgba(156,39,176,0.25)", "fg": "#ce93d8"},
    },
    "dall_e": {
        "label": "DALL-E",
        "baseUrl": "https://api.openai.com/v1",
        "models": ["dall-e-3", "dall-e-2"],
        "defaultModel": "dall-e-3",
        "hint": "OpenAI DALL-E文生图，高质量",
        "keyPlaceholder": "在 platform.openai.com 获取",
        "color": {"bg": "rgba(102,126,234,0.3)", "fg": "#a8b5ff"},
    },
    "flux": {
        "label": "Flux",
        "baseUrl": "https://api.bfl.ml",
        "models": ["flux-pro-1.1", "flux-pro", "flux-schnell"],
        "defaultModel": "flux-pro-1.1",
        "hint": "Flux文生图，高质量",
        "keyPlaceholder": "在 bfl.ml 获取",
        "color": {"bg": "rgba(76,175,80,0.25)", "fg": "#81c784"},
    },
    "mimo": {
        "label": "小米 MiMo",
        "baseUrl": "https://api.xiaomimimo.com/v1",
        "models": ["mimo-v2.5"],
        "defaultModel": "mimo-v2.5",
        "hint": "小米MiMo文生图，使用LLM相同的API Key",
        "keyPlaceholder": "使用小米MiMo LLM的API Key",
        "color": {"bg": "rgba(255,87,34,0.25)", "fg": "#ff8a65"},
    },
}

# ============================================================
# Edge TTS 音色列表（单一数据源）
# 前端通过 /api/config.js 动态加载，修改后自动生效
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
# 前端通过 /api/config.js 动态加载，修改后自动生效
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

# ============================================================
# 项目根目录（KI-005: 单一数据源，消除 18+ 处重复计算）
# ============================================================
# shared_config.py 位于 app/ 目录下，向上两级即项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 端口配置（KI-002: 单一数据源，消除 5 处硬编码）
# ============================================================
def _load_ports():
    """从 config.yaml 加载端口配置，提供默认值"""
    try:
        import yaml
        config_path = os.path.join(PROJECT_DIR, 'app', 'config.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f) or {}
            web_cfg = cfg.get('web', {})
            return {
                'HTTP_PORT': web_cfg.get('port', 12393),
                'WS_PORT': web_cfg.get('ws_port', 12394),
            }
    except Exception as e:
        logger.info(f"[Config] 端口加载失败(使用默认值): {e}")
    return {'HTTP_PORT': 12393, 'WS_PORT': 12394}

_ports = _load_ports()
HTTP_PORT = _ports['HTTP_PORT']
WS_PORT = _ports['WS_PORT']

# ============================================================
# GPT-SoVITS 模型列表（KI-004: 单一数据源）
# ============================================================
GPT_SOVITS_MODELS = [
    {
        "name": "GPT-SoVITS 基础模型 (v3)",
        "url": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/gsv-v3.1.pt",
        "path": "GPT-SoVITS/GPT_weights_v3/gsv-v3.1.ckpt",
        "size_threshold": 1024 * 1024 * 500,  # 500MB
    },
    {
        "name": "GPT-SoVITS 基础模型 (v2)",
        "url": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s2G488k.pth",
        "path": "GPT-SoVITS/GPT_weights_v2/s2G488k.ckpt",
        "size_threshold": 1024 * 1024 * 400,  # 400MB
    },
    {
        "name": "SoVITS 模型 (v2)",
        "url": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s2G488k.pth",
        "path": "GPT-SoVITS/SoVITS_weights_v2/s2G488k.ckpt",
        "size_threshold": 1024 * 1024 * 400,
    },
    {
        "name": "BERT 中文模型",
        "url": "https://huggingface.co/google-bert/bert-base-chinese",
        "path": "GPT-SoVITS/bert/chinese-roberta-wwm-ext",
        "size_threshold": 1024 * 1024 * 400,
    },
    {
        "name": "Clap 语音模型",
        "url": "https://huggingface.co/microsoft/msclap",
        "path": "GPT-SoVITS/clap/msclap",
        "size_threshold": 1024 * 1024 * 300,
    },
]

# ============================================================
# 公共工具函数（KI-006: 消除重复代码模式）
# ============================================================

def unblock_dlls(directory: str, recursive: bool = True):
    """Windows DLL 解锁（移除从网络下载时添加的 Zone.Identifier 标记）

    .NET/pywebview 等框架拒绝加载带有 Zone.Identifier 的 DLL，
    导致程序崩溃。此函数在首次启动时调用，解除锁定。

    Args:
        directory: 要扫描的目录路径
        recursive: 是否递归子目录（默认 True）

    KI-006a: 从 launcher/launcher.py 和 scripts/setup.py 中提取的公共逻辑
    """
    if os.sys.platform != "win32":
        return
    try:
        import subprocess
        pattern = f"{directory}\\**\\*.dll" if recursive else f"{directory}\\*.dll"
        recurse_flag = f"$true" if recursive else f"$false"
        subprocess.run(
            ['powershell', '-Command',
             f'Get-ChildItem -Path "{pattern}" -Recurse:{recurse_flag} | Unblock-File'],
            capture_output=True, timeout=30
        )
    except Exception as e:
        logger.info(f"[DLL] 解锁失败: {e}")


def filter_tool_markers(text: str) -> str:
    """过滤 LLM 回复中的工具调用标记

    某些 LLM（尤其是未正确配置 function calling 的模型）会在回复中
    残留 TOOL:/ARG:/BASH:/READ:/WRITE:/EDIT: 等标记，应在前端显示前过滤。

    Args:
        text: LLM 原始回复文本

    Returns:
        过滤后的干净文本

    KI-006d: 从 app/web/__init__.py 和 app/proactive.py 中提取的公共逻辑
    """
    import re
    patterns = [
        r'TOOL:\s*\w+',
        r'ARG:\s*[^\n]+',
        r'BASH:\s*[^`\n]+',
        r'READ:\s*[^`\n]+',
        r'WRITE:\s*[^`\n]+',
        r'EDIT:\s*[^`\n]+',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text)
    return text.strip()
