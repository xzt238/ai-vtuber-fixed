"""
咕咕嘎嘎 AI-VTuber — Markdown 渲染器

将 Markdown 文本转换为带样式的 HTML，支持:
- 标题、粗体、斜体、删除线
- 代码块（Pygments 语法高亮）
- 行内代码
- 有序/无序列表
- 表格
- 链接
- 引用块
- 图片
- LaTeX 公式 (KaTeX 占位，P2 阶段)

用于 QWebEngineView 聊天显示区的前端渲染。
"""

import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.toc import TocExtension

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


# Pygments HTML 格式化器 — 内联样式，适合嵌入 Web 页面
_formatter = None
_formatter_css = ""

if PYGMENTS_AVAILABLE:
    _formatter = HtmlFormatter(
        style="monokai",
        noclasses=True,        # 内联样式，不依赖外部 CSS
        linenos=False,
        wrapcode=True,
    )
    _formatter_css = _formatter.get_style_defs(".codehilite")


def _pygmented_code_block(code: str, lang: str = "") -> str:
    """使用 Pygments 对代码块进行语法高亮"""
    if not PYGMENTS_AVAILABLE:
        return f'<pre><code>{_escape_html(code)}</code></pre>'

    try:
        if lang:
            lexer = get_lexer_by_name(lang, stripall=True)
        else:
            lexer = guess_lexer(code)
    except ClassNotFound:
        lexer = TextLexer(stripall=True)

    return highlight(code, lexer, _formatter)


class _CodeBlockPreprocessor(markdown.preprocessors.Preprocessor):
    """自定义代码块预处理器 — 用 Pygments 替换标准代码块渲染"""

    FENCED_BLOCK_RE = markdown.preprocessors.Preprocessor.__class__.__dict__  # placeholder

    def run(self, lines):
        """处理 fenced code blocks"""
        new_lines = []
        in_code = False
        code_lines = []
        lang = ""

        i = 0
        while i < len(lines):
            line = lines[i]

            if not in_code:
                # 检查 fenced code block 开始
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_code = True
                    lang = stripped[3:].strip()
                    code_lines = []
                    i += 1
                    continue
                new_lines.append(line)
            else:
                # 在代码块中
                if line.strip() == "```":
                    # 代码块结束
                    code_text = "\n".join(code_lines)
                    highlighted = _pygmented_code_block(code_text, lang)
                    # 用占位符标记，后续替换
                    placeholder = f"<!--CODE_BLOCK_{len(new_lines)}-->"
                    new_lines.append(placeholder)
                    # 保存高亮结果
                    if not hasattr(self, '_code_blocks'):
                        self._code_blocks = {}
                    self._code_blocks[placeholder] = highlighted
                    in_code = False
                    code_lines = []
                else:
                    code_lines.append(line)
            i += 1

        return new_lines


class _CodeBlockTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """树处理器 — 在 Markdown 解析后替换代码块占位符"""

    def run(self, root):
        for elem in root.iter():
            if elem.text and "<!--CODE_BLOCK_" in elem.text:
                for placeholder, html in self._code_blocks.items():
                    if placeholder in elem.text:
                        elem.text = html
                        elem.tag = "div"
                        elem.set("class", "code-block-wrapper")
                        break
            if elem.tail and "<!--CODE_BLOCK_" in elem.tail:
                for placeholder, html in self._code_blocks.items():
                    if placeholder in elem.tail:
                        elem.tail = html
                        break
        return root


def render_markdown(text: str, theme: str = "dark") -> str:
    """将 Markdown 文本渲染为 HTML

    Args:
        text: Markdown 原始文本
        theme: "dark" 或 "light"，用于选择代码高亮主题

    Returns:
        渲染后的 HTML 字符串
    """
    if not text or not text.strip():
        return ""

    # 预处理：保护代码块
    code_blocks = {}
    processed_text = _extract_code_blocks(text, code_blocks)

    # 预处理：保护 LaTeX 公式（避免 markdown 引擎破坏 $...$ 语法）
    latex_blocks = {}
    processed_text = _extract_latex(processed_text, latex_blocks)

    # 使用 markdown 库渲染
    extensions = [
        "fenced_code",
        "tables",
        "nl2br",       # 换行转 <br>
        "sane_lists",
    ]

    try:
        md = markdown.Markdown(extensions=extensions)
        html = md.convert(processed_text)
    except Exception:
        # 降级：纯文本转 HTML
        html = _escape_html(text).replace("\n", "<br>")

    # 恢复 LaTeX 公式
    html = _restore_latex(html, latex_blocks)

    # 恢复代码块（Pygments 高亮版）
    html = _restore_code_blocks(html, code_blocks, theme)

    return html


def _extract_code_blocks(text: str, code_blocks: dict) -> str:
    """提取 fenced code blocks，用占位符替换"""
    lines = text.split("\n")
    result_lines = []
    in_code = False
    code_lines = []
    lang = ""
    block_idx = 0

    for line in lines:
        if not in_code:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = True
                lang = stripped[3:].strip()
                code_lines = []
                continue
            result_lines.append(line)
        else:
            if line.strip() == "```":
                code_text = "\n".join(code_lines)
                highlighted = _pygmented_code_block(code_text, lang)
                placeholder = f"%%CODEBLOCK_{block_idx}%%"
                code_blocks[placeholder] = highlighted
                result_lines.append(placeholder)
                block_idx += 1
                in_code = False
                code_lines = []
            else:
                code_lines.append(line)

    # 未关闭的代码块
    if in_code and code_lines:
        code_text = "\n".join(code_lines)
        highlighted = _pygmented_code_block(code_text, lang)
        placeholder = f"%%CODEBLOCK_{block_idx}%%"
        code_blocks[placeholder] = highlighted
        result_lines.append(placeholder)

    return "\n".join(result_lines)


def _restore_code_blocks(html: str, code_blocks: dict, theme: str) -> str:
    """将代码块占位符替换为高亮后的 HTML"""
    for placeholder, code_html in code_blocks.items():
        # 包裹在代码容器中
        copy_btn = (
            '<div class="code-block-header">'
            f'<span class="code-lang">{_get_lang_label(code_html)}</span>'
            '<button class="code-copy-btn" onclick="copyCode(this)">复制</button>'
            '</div>'
        )
        wrapped = f'<div class="code-block">{copy_btn}{code_html}</div>'

        # 占位符可能被 markdown 包裹在 <p> 标签中
        html = html.replace(f"<p>{placeholder}</p>", wrapped)
        html = html.replace(placeholder, wrapped)

    return html


def _get_lang_label(code_html: str) -> str:
    """从 Pygments 输出中提取语言标签"""
    try:
        if 'class="codehilite"' in code_html:
            return "code"
    except Exception:
        pass
    return "code"


def _escape_html(text: str) -> str:
    """HTML 转义"""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def get_highlight_css(theme: str = "dark") -> str:
    """获取代码高亮的 CSS 样式"""
    if not PYGMENTS_AVAILABLE:
        return ""

    if theme == "light":
        fmt = HtmlFormatter(style="friendly", noclasses=True)
    else:
        fmt = HtmlFormatter(style="monokai", noclasses=True)

    return fmt.get_style_defs(".codehilite")


import re

# LaTeX 提取/恢复 — 保护 $...$ 和 $$...$$ 不被 markdown 引擎破坏

_LATEX_DISPLAY_RE = re.compile(r'\$\$([\s\S]+?)\$\$', re.MULTILINE)
_LATEX_INLINE_RE = re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)')
_LATEX_PAREN_INLINE_RE = re.compile(r'\\\((.+?)\\\)')
_LATEX_BRACKET_DISPLAY_RE = re.compile(r'\\\[(.+?)\\\]', re.DOTALL)


def _extract_latex(text: str, latex_blocks: dict) -> str:
    """提取 LaTeX 公式，用占位符替换

    优先匹配 $$...$$ (display)，再匹配 $...$ (inline)
    """
    block_idx = 0

    # 先处理 $$...$$ (display math)
    def _replace_display(m):
        nonlocal block_idx
        placeholder = f"%%LATEX_DISPLAY_{block_idx}%%"
        latex_blocks[placeholder] = m.group(0)  # 保留原始 $$...$$
        block_idx += 1
        return placeholder

    text = _LATEX_DISPLAY_RE.sub(_replace_display, text)

    # 再处理 $...$ (inline math) — 注意避免匹配 $$ 残留
    def _replace_inline(m):
        nonlocal block_idx
        placeholder = f"%%LATEX_INLINE_{block_idx}%%"
        latex_blocks[placeholder] = m.group(0)  # 保留原始 $...$
        block_idx += 1
        return placeholder

    text = _LATEX_INLINE_RE.sub(_replace_inline, text)

    # 也处理 \(...\) 和 \[...\] 语法
    text = _LATEX_PAREN_INLINE_RE.sub(_replace_inline, text)
    text = _LATEX_BRACKET_DISPLAY_RE.sub(_replace_display, text)

    return text


def _restore_latex(html: str, latex_blocks: dict) -> str:
    """将 LaTeX 占位符恢复为原始公式（KaTeX JS 端渲染）"""
    for placeholder, latex in latex_blocks.items():
        # 占位符可能被 markdown 包裹在 <p> 标签中
        html = html.replace(f"<p>{placeholder}</p>", f"<p>{latex}</p>")
        html = html.replace(placeholder, latex)
    return html
