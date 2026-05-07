"""
对话文本增强器 v2 — 让 AI 回复在 TTS 合成时更自然

从 ChatTTS 的文本预处理逻辑中提取并增强，作为 GPT-SoVITS 的前置处理模块。
v2 新增：自动检测情感词、中文语气词增强、情绪扩散、统一清理逻辑。

核心功能:
1. 自动检测：LLM 未使用标记时，从自然语言中检测笑声/感叹词并插入 TTS 标记
2. 情感标记替换：将 [laugh]/[uv_break]/[lbreak] 等 ChatTTS 标记转为 GPT-SoVITS 文本
3. 智能笑声变体：根据上下文情绪自动调整笑声强度（大笑/轻笑/偷笑）
4. 情绪扩散：让标记影响周围句子的语气（笑声后轻松、叹气后低落）
5. 中文语言学增强：句末语气词、重复强调、口语填充词
6. 统一清理：合并所有 markdown/emoji/符号清理，避免重复处理
7. 停顿增强：在笑声/语气词前插入逗号停顿

使用方式:
    from app.tts.text_enhancer import enhance_text
    enhanced = enhance_text("你猜怎么着[uv_break]今天下雪了！[laugh]")
    # → "你猜怎么着，今天下雪了！，哈哈哈哈，～"

作者: 咕咕嘎嘎
日期: 2026-05-06
更新: 2026-05-07 v2 增强版
"""

import re


# ============================================================================
# 配置
# ============================================================================

# 模块级配置（从 config.yaml 加载，有默认值）
_config = {
    "style": "companion",
    "auto_detect": True,
    "chinese_features": True,
    "emotion_diffusion": True,
    "max_markers_per_reply": 3,
}


def configure_enhancement(config: dict):
    """从外部配置更新增强参数（由 app 启动时调用）"""
    _config.update(config)


# ============================================================================
# 常量
# ============================================================================

# 笑声/欢快关键词 — 在这些词前加停顿，让 TTS 不会把笑声和正文粘连
LAUGH_KEYWORDS = ['哈哈', '哈哈哈', '嘻嘻', '嘿嘿', '呵呵', '好耶', '太棒了', '太好了', '耶']

# 语气词/感叹词 — 前面加短停顿，听起来更自然
INTERJECTION_WORDS = ['嗯', '啊', '哦', '诶', '哎', '哇', '呀', '呢', '嘛', '呐', '哼', '呜']

# 情感标记（LLM 输出的标记 → GPT-SoVITS 可合成的文本）
#
# ChatTTS 官方标记（核心）:
#   [laugh]    → 笑声    → "，哈哈，"（后续由 _enhance_laugh_variety 智能调整强度）
#   [uv_break] → 短停顿  → "，"（逗号停顿，相当于换气）
#   [lbreak]   → 长停顿  → "……"（省略号，较长停顿）
#
# 设计原则:
#   所有标记必须在 Step 1 中被替换为 GPT-SoVITS 能理解的纯文本，
#   否则会在 Step 8 被正则 `\[[\w_]+\]` 静默删除（零效果）。
EMOTION_MARKERS = {
    # ---- ChatTTS 官方标记（LLM 通过 TTS_EXPRESSION 提示词主动输出）----
    '[laugh]': '，哈哈，',          # 笑声 → 停顿 + 笑声词（后续可变体）
    '[uv_break]': '，',             # 短停顿 → 逗号（换气/强调/转折）
    '[lbreak]': '……',              # 长停顿 → 省略号（话题切换/重大转折）

    # ---- 中文情感标记（LLM 有时输出这些）----
    '[笑]': '，哈哈，',
    '[笑声]': '，哈哈，',
    '[大笑]': '，哈哈哈哈，',       # 大笑 → 更强烈的笑声
    '[轻笑]': '，呵呵，',           # 轻笑 → 温和的笑
    '[偷笑]': '，嘻嘻，',           # 偷笑 → 小声的笑
    '[苦笑]': '，唉，哈哈，',       # 苦笑 → 叹气+笑
    '[开心]': '，',
    '[撒娇]': '～',
    '[叹气]': '，唉，',
    '[惊讶]': '，啊，',
    '[思考]': '，嗯，',
    '[害羞]': '，',
    '[生气]': '，哼，',
    '[哭泣]': '，呜呜，',
    '[啜泣]': '，呜，',
    '[难过]': '，唉，',

    # ---- 英文/通用标记 ----
    '[sigh]': '，唉，',
    '[gasp]': '，啊，',
    '*laughs*': '，哈哈，',
    '*sighs*': '，唉，',
}

# 自动检测规则：将自然语言中的情感词转为 TTS 标记
# 当 LLM 不使用 [laugh] 标记时，这些规则确保笑声/情感仍被正确处理
AUTO_DETECT_RULES = [
    # (pattern, marker_to_insert, description)
    # --- 笑声检测 ---
    (r'哈哈', '[laugh]', '标准笑声'),
    (r'嘻嘻', '[laugh]', '偷笑'),
    (r'嘿嘿', '[laugh]', '憨笑'),
    (r'呵呵', '[laugh]', '轻笑'),
]

# 句末语气词映射 — 让 TTS 读出自然的语气变化
# 当句子以这些模式结尾时，追加语气词让声音更有感情
# 只在 style="companion" 模式下启用
SENTENCE_END_PARTICLES = {
    # particle: [pattern1, pattern2, ...]
    # 声明语气 → 嘛/啦
    '嘛': [r'当然[是会]', r'本来就', r'明明就', r'就是[要说]'],
    '啦': [r'好[的呀啊]$', r'行[的呀啊]$', r'没问题$', r'知道[了呀]$'],
    # 感叹语气 → 呀/喔/呢
    '呀': [r'好[大美棒可爱]+', r'真[是好].{0,2}', r'太.{0,3}[了]'],
    '喔': [r'原来[如是]', r'这样[啊的]', r'我知[道了]'],
    '呢': [r'在哪', r'什么时候', r'怎么[办会样]', r'为什么'],
}

# 重复词增强 — 让 TTS 读出强调语气
# "好！" → "好好！"（强调），"对呀" → "对对呀"（肯定）
REPETITION_PATTERNS = [
    (r'(?<!好)(好)([！!])', r'\1\1\2'),       # 好！→ 好好！（强调）
    (r'(?<!对)(对)([哦呀啊])', r'\1\1\2'),     # 对呀 → 对对呀（肯定）
]

# 口语填充词触发点 — 在这些词后面可能插入填充词
FILLER_TRIGGERS = ['我觉得', '我想', '大概是', '可能是', '应该说']
FILLER_WORDS = ['嗯，', '那个，', '就是，']


# ============================================================================
# 增强函数
# ============================================================================

def _auto_detect_markers(text: str, style: str = "companion") -> str:
    """
    自动检测情感词并插入 TTS 标记

    当 LLM 未使用 [laugh]/[uv_break] 等标记时，
    扫描自然语言中的笑声词，自动插入对应标记。
    后续由 Step 1 的 EMOTION_MARKERS 统一替换为 GPT-SoVITS 文本。

    策略：在检测到的词前方插入标记，不替换原词（保留可读性）。
    限制：每种模式只处理第一次出现，且总标记数受 max_markers_per_reply 限制。
    只在 style="companion" 时启用。
    """
    if style != "companion":
        return text
    if not _config.get("auto_detect", True):
        return text

    # 如果文本中已经有 TTS 标记，减少自动插入
    existing_markers = sum(1 for m in EMOTION_MARKERS.keys() if m in text)
    max_auto = _config.get("max_markers_per_reply", 3) - existing_markers
    if max_auto <= 0:
        return text  # 已有足够标记，不再自动插入

    inserted = 0
    for pattern, marker, _ in AUTO_DETECT_RULES:
        if inserted >= max_auto:
            break
        # 避免重复插入：如果标记已存在于笑声词前方，跳过
        # 检查是否已有对应标记紧贴在这个词前面
        marker_prefix = marker.rstrip(']') + ']'  # 完整标记如 [laugh]
        if marker_prefix + pattern.replace('\\', '') in text:
            continue  # 已有标记+词组合，跳过
        # 在匹配的词前插入标记
        new_text = re.sub(
            rf'({pattern})',
            f'{marker}\\1',
            text,
            count=1
        )
        if new_text != text:
            text = new_text
            inserted += 1

    return text


def _enhance_laugh_variety(text: str) -> str:
    """
    智能笑声变体 — 根据上下文情绪自动调整笑声强度

    避免所有 [laugh] 都变成千篇一律的"哈哈"：
    - 兴奋上下文（感叹号、感叹词）→ 大笑 "哈哈哈哈"
    - 平淡上下文（句号、逗号）    → 轻笑 "呵呵"
    - 默认                         → 标准笑 "哈哈"

    只处理 EMOTION_MARKERS 替换后产生的 "，哈哈，" 模式，
    不影响用户原始文本中的笑声词。
    """
    laugh_pattern = '，哈哈，'
    if laugh_pattern not in text:
        return text

    result = []
    i = 0
    while i < len(text):
        pos = text.find(laugh_pattern, i)
        if pos == -1:
            result.append(text[i:])
            break

        result.append(text[i:pos])

        # 分析笑声前面的上下文（取前面最多8个字符，避免跨分句影响）
        context_before = text[max(0, pos - 8):pos]

        # 判断笑声强度
        excited = bool(re.search(r'[！!]{1,}|太.{0,2}[了！!]|好[耶呀哇！!]|真的[！!]|超[级很]?', context_before))
        calm = bool(re.search(r'[。.…]+$|也好|也罢|算了|不过|嗯，', context_before))

        if excited:
            result.append('，哈哈哈哈，')
        elif calm:
            result.append('，呵呵，')
        else:
            result.append(laugh_pattern)

        i = pos + len(laugh_pattern)

    return ''.join(result)


def _diffuse_emotion(text: str) -> str:
    """
    情绪扩散 — 让 TTS 标记影响周围句子的语气

    核心思想：标记不仅做局部替换，还通过标点符号的微调
    来影响 GPT-SoVITS 对周围文本的韵律生成。

    实现策略（纯文本，无音频操作）：
    - 笑声后：在紧接的文字前加 ～（延长音，暗示轻松语气）
    - 叹气后：在下一子句前加 ……（省略号，暗示低落）
    - 惊讶后：在下一子句前加 ！（强调语气）

    注意：此步骤在 EMOTION_MARKERS 替换（Step 1）之后执行，
    通过检测替换后的文本模式来工作。
    """
    if not _config.get("emotion_diffusion", True):
        return text

    # 笑声后的语气扩散
    # 模式：，哈哈，[后续文字] → ，哈哈，～[后续文字]
    text = re.sub(
        r'(，(?:哈哈|呵呵|嘻嘻|嘿嘿|哈哈哈哈)，)([^，。！？…～])',
        r'\1～\2',
        text,
        count=1
    )

    # 叹气后的语气扩散
    # 模式：，唉，[后续文字] → ，唉，……[后续文字]
    text = re.sub(
        r'(，唉，)([^，。！？…])',
        r'\1……\2',
        text,
        count=1
    )

    # 惊讶后的语气扩散
    # 模式：，啊，[后续文字] → ，啊！[后续文字]
    text = re.sub(
        r'(，啊，)([^，。！？])',
        r'\1！\2',
        text,
        count=1
    )

    return text


def _enhance_chinese_features(text: str, style: str = "companion") -> str:
    """
    中文语言学增强 — 让 TTS 输出更自然的中文口语

    1. 句末语气词：在特定句式后追加 嘛/啦/呀/喔/呢
    2. 重复强调：好！→ 好好！/ 对呀 → 对对呀
    3. 口语填充词：在思考性表达后插入 嗯/那个/就是

    只在 style="companion" 时启用。
    使用确定性策略（基于文本特征判断），避免随机性导致同输入不同输出。
    """
    if style != "companion":
        return text
    if not _config.get("chinese_features", True):
        return text

    # 1. 句末语气词 — 只在句末标点前追加语气词
    # 找到句末标点（。！？!?.），在标点前插入语气词
    for particle, patterns in SENTENCE_END_PARTICLES.items():
        for pattern in patterns:
            # 在句末标点前的匹配句式后追加语气词
            # 模式：匹配句式 + 句末标点 → 匹配句式 + 语气词 + 标点
            def _add_particle(match, p=particle):
                matched = match.group(0)
                # 如果已有语气词，不重复添加
                if matched.endswith(p):
                    return matched
                # 在标点前插入语气词
                return matched[:-1] + p + matched[-1]

            # 只匹配句式 + 句末标点的情况
            text = re.sub(
                pattern + r'[。！？.!?]',
                _add_particle,
                text,
                count=1
            )

    # 2. 重复强调
    for pattern, replacement in REPETITION_PATTERNS:
        text = re.sub(pattern, replacement, text, count=1)

    # 3. 口语填充词 — 确定性策略：基于文本长度决定是否插入
    # 长文本（>30字）才考虑插入，短文本不需要填充
    if len(text) > 30:
        for trigger in FILLER_TRIGGERS:
            if trigger in text:
                # 确定性：用文本长度的奇偶性决定是否插入
                # 避免使用 random，保证同输入同输出
                idx = text.index(trigger)
                if idx % 3 == 0:  # 约33%概率（确定性）
                    filler = FILLER_WORDS[idx % len(FILLER_WORDS)]
                    text = text.replace(trigger, f'{trigger}{filler}', 1)
                break  # 只处理第一个触发的填充词

    return text


# ============================================================================
# 主增强函数
# ============================================================================

def enhance_text(text: str, style: str = None) -> str:
    """
    对话文本增强 — 让 TTS 合成更自然

    Args:
        text: 原始文本（LLM 输出）
        style: 增强风格（可选，覆盖配置）
            - "companion": AI 伴侣风格（笑声停顿更明显）
            - "neutral": 中性风格（仅做基础清洗，少加停顿）
            - "off": 关闭增强（仅做最基本清理）

    Returns:
        增强后的文本，适合送入 TTS 引擎合成
    """
    if not text or not text.strip():
        return text

    # 使用传入 style 或配置中的 style
    effective_style = style if style is not None else _config.get("style", "companion")

    if effective_style == "off":
        # 关闭增强，仅做最基本清理
        text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
        return text.strip()

    # ===== 第0步：自动检测情感词 → 插入 TTS 标记 =====
    # 当 LLM 未使用标记时，从自然语言中检测笑声/感叹词
    text = _auto_detect_markers(text, effective_style)

    # ===== 第1步：情感标记替换 =====
    # 将 [laugh]/[uv_break]/[lbreak] 等 ChatTTS 标记转为 GPT-SoVITS 可合成的文本
    # 必须在 Step 8 清理残余标记之前完成替换，否则标记会被静默删除
    for marker, replacement in EMOTION_MARKERS.items():
        text = text.replace(marker, replacement)

    # ===== 第2步：智能笑声变体 =====
    # 根据上下文情绪调整笑声强度（"哈哈" → "哈哈哈哈"/"呵呵"）
    text = _enhance_laugh_variety(text)

    # ===== 第2b步：情绪扩散 =====
    # 让情感标记影响周围句子的语气（通过标点微调）
    text = _diffuse_emotion(text)

    # ===== 第2.5步：中文语言学增强 =====
    # 句末语气词、重复强调、口语填充词
    text = _enhance_chinese_features(text, effective_style)

    # ===== 第3步：清理 markdown 格式 =====
    # 统一处理所有 markdown 格式（合并自 gptsovits.py，避免重复处理）
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)         # **bold** → bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)               # *italic* → italic
    text = re.sub(r'`([^`]+)`', r'\1', text)               # `code` → code
    text = re.sub(r'#{1,6}\s*', '', text)                   # ## heading → 删除
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)    # [link](url) → text
    text = re.sub(r'-{2,}', '，', text)                     # --- 横线 → 逗号
    text = re.sub(r'(?<=[，,。.！!？?；;：:])\s*[-*+]\s*', '', text)  # 标点后列表标记
    text = re.sub(r'^\s*[-*+]\s*', '', text, flags=re.MULTILINE)      # 行首列表标记
    text = re.sub(r'\([^)]*\)', '', text)                    # (说明性文字) → 删除

    # ===== 第4步：清理 emoji 和符号 =====
    # 统一处理所有 emoji/符号（合并自 gptsovits.py）
    # 注意: \u 只支持4位十六进制，\U 支持8位，不能在 [] 内混用跨 BMP 范围
    # ⚠️ 省略号（… U+2026）必须保护！它是 GPT-SoVITS 的韵律控制标点
    # 通用符号区 [\u2000-\u2BFF] 包含 U+2026，必须排除
    text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # 表情符号
    text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # 符号/图标
    text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # 交通/地图
    text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # 旗帜
    text = re.sub(r'[\u2600-\u27BF]', '', text)          # 杂项符号 + 装饰符号
    text = re.sub(r'[\u2460-\u24FF]', '', text)          # 圈号 ①-⑳
    text = re.sub(r'[\U0001F100-\U0001F2FF]', '', text)  # Enclosed Alphanumeric Supplement
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)  # 4字节 emoji（兜底）
    # 通用符号区，排除省略号 … (U+2026) 和波浪号 ～ (U+FF5E)
    text = re.sub(r'[\u2000-\u2025\u2027-\u2BFF]', '', text)
    # 波浪号 → 延长音（保留语感）
    text = text.replace('~', '～')

    # ===== 第4.5步：TTS 引擎特定文本规范化 =====
    # 从 gptsovits.py 迁移的引擎特定处理
    text = text.replace('\n', '，').replace('\r', '')     # 换行 → 逗号
    # 连字符处理（GPT-SoVITS 会把 - 读成"减"）
    text = text.replace('-', '，')
    text = re.sub(r'([a-zA-Z0-9])，([a-zA-Z0-9])', r'\1-\2', text)  # 恢复英文复合词连字符

    # ===== 第5步：笑声/语气词停顿增强 =====
    if effective_style == "companion":
        # 在笑声关键词后加逗号停顿（"哈哈，你好" 而非 "哈哈你好" 一口气读完）
        for kw in LAUGH_KEYWORDS:
            if kw in text:
                text = re.sub(
                    rf'({re.escape(kw)})([^\s，。！？,.!?～哈嘻嘿呵])',
                    r'\1，\2',
                    text,
                    count=1
                )

        # 在句首语气词后加逗号（"嗯，" "啊，"），让 TTS 稍作停顿
        for iw in INTERJECTION_WORDS:
            text = re.sub(
                rf'(^|[，。！？,.!?])\s*({re.escape(iw)})($|[^，。！？,.！？～…])',
                r'\1\2，\3',
                text,
                count=1
            )

    # ===== 第6步：清理残留中括号标记 =====
    # 移除 [xxx] 格式的标记（未被 Step 1 替换的残余）
    text = re.sub(r'\[[\w_]+\]', '', text)

    # ===== 第7步：清理多余空白和标点 =====
    text = re.sub(r'\s+', ' ', text)              # 多空格 → 单空格
    text = re.sub(r'，{2,}', '，', text)           # 连续逗号 → 单个
    text = re.sub(r'。{2,}', '。', text)           # 连续句号 → 单个
    # 标点后紧跟逗号的冗余模式（如 "！，" "？，" "……，"）
    text = re.sub(r'([！!？?])，', r'\1', text)    # ！，→ ！
    text = re.sub(r'……，', '……', text)             # ……，→ ……
    # 连续重复词清理（如 "，唉，唉，" → "，唉，"）
    # 出现场景：LLM 同时输出 [sigh] 标记和"唉"字
    text = re.sub(r'(，(?:唉|嗯|啊|哈|哼|呜)，)\1', r'\1', text)
    # 上面的模式没匹配到的话，试这个（单逗号间隔）
    text = re.sub(r'((?:唉|嗯|啊|哈|哼|呜)，)\1', r'\1', text)
    text = re.sub(r'^[，,、；：]+', '', text)       # 清理句首标点
    text = text.strip()

    # ===== 第7.5步：清理连续标点（合并自 gptsovits.py）=====
    # LLM 异常输出的连续标点（如 。，，。。等）
    for punct_group in [
        r'([。\.]{2,})', r'([！!]{2,})', r'([？?]{2,})',
        r'([，,]{2,})', r'([、]{2,})', r'([；;]{2,})', r'([：:]{2,})'
    ]:
        text = re.sub(punct_group, lambda m: m.group(1)[0], text)
    # 清理标点+空格混合
    text = re.sub(r'([。！？.!?])\s+([。！？.!?])', r'\1\2', text)
    # 清理句首残留标点
    text = re.sub(r'^[，,、；：。！？.!?]+', '', text)
    text = text.strip()

    return text
