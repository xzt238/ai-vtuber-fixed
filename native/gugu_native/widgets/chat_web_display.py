"""
咕咕嘎嘎 AI-VTuber — QWebEngineView 聊天显示组件

完整 Markdown 渲染 + 消息操作 + 流式更新 + 主题切换

架构:
- QWebEngineView 渲染 HTML 聊天内容
- QWebChannel 双向通信（Python <-> JavaScript）
- JavaScript 端处理消息渲染、分组、动画
- Python 端管理消息数据、流式更新、操作回调

降级策略:
- 如果 QWebEngineView 不可用，自动降级为 QTextEdit 模式
"""

import os
import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot, QObject, QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMenu, QTextEdit
from PySide6.QtGui import QFont, QTextCursor, QAction

# 尝试导入 QWebEngineView
_WEBENGINE_AVAILABLE = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebChannel import QWebChannel
    _WEBENGINE_AVAILABLE = True
except ImportError:
    pass

from gugu_native.widgets.markdown_renderer import render_markdown, get_highlight_css

# 加载 qwebchannel.js 内容（用于内嵌到 HTML 中）
_QWEBCHANNEL_JS_PATH = Path(__file__).parent / "qwebchannel.js"
_QWEBCHANNEL_JS = ""
if _QWEBCHANNEL_JS_PATH.exists():
    _QWEBCHANNEL_JS = _QWEBCHANNEL_JS_PATH.read_text(encoding="utf-8")


# ============ HTML 模板 ============

_CHAT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<!-- 内嵌 qwebchannel.js — QWebChannel 桥接必须库 -->
<script>{qwebchannel_js}</script>
<!-- KaTeX CDN — LaTeX 公式渲染（全部 async，离线时不阻塞页面加载） -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" media="print" id="katex-css">
<script async src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script async src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
// KaTeX CSS 加载完成后再应用（media="print" 是加载技巧，JS 激活后才真正渲染样式）
setTimeout(function() {{
  var css = document.getElementById('katex-css');
  if (css) css.setAttribute('media', 'all');
}}, 3000);
</script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

:root {{
  --bg: {bg_color};
  --text-primary: {text_primary};
  --text-secondary: {text_secondary};
  --text-muted: {text_muted};
  --ai-bubble-bg: {ai_bubble_bg};
  --ai-bubble-border: {ai_bubble_border};
  --user-bubble-bg: {user_bubble_bg};
  --user-text-color: {user_text_color};
  --system-bg: {system_bg};
  --system-border: {system_border};
  --system-color: {system_color};
  --timestamp-bg: {timestamp_bg};
  --timestamp-border: {timestamp_border};
  --timestamp-color: {timestamp_color};
  --accent: {accent};
  --avatar-size: {avatar_size}px;
  --bubble-radius: 12px;
  --bubble-padding: 10px 16px;
  --group-gap: 12px;
  --same-gap: 4px;
  --typing-cursor: {typing_cursor_color};
}}

body {{
  font-family: "Microsoft YaHei UI", "Segoe UI", -apple-system, sans-serif;
  background-color: var(--bg);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.7;
  overflow-y: auto;
  padding: 14px 16px;
}}

/* 滚动条 */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--text-muted); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--text-secondary); }}

/* 消息行 */
.msg-row {{
  display: flex;
  align-items: flex-start;
  margin-top: var(--group-gap);
  gap: 8px;
}}
.msg-row.same-sender {{
  margin-top: var(--same-gap);
}}
.msg-row.user {{
  flex-direction: row-reverse;
}}

/* 头像 */
.avatar {{
  width: var(--avatar-size);
  height: var(--avatar-size);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: {avatar_font_size}px;
  color: white;
  flex-shrink: 0;
  line-height: 1;
}}
.avatar.ai {{
  background-color: #7c3aed;
}}
.avatar.user {{
  background-color: #4263eb;
}}
.avatar-placeholder {{
  width: var(--avatar-size);
  height: 1px;
  flex-shrink: 0;
}}

/* 气泡 */
.bubble {{
  max-width: 75%;
  padding: var(--bubble-padding);
  border-radius: var(--bubble-radius);
  word-wrap: break-word;
  overflow-wrap: break-word;
  position: relative;
}}
.bubble.ai {{
  background-color: var(--ai-bubble-bg);
  border: 1px solid var(--ai-bubble-border);
  color: var(--text-primary);
}}
.bubble.user {{
  background-color: var(--user-bubble-bg);
  color: var(--user-text-color);
}}

/* Markdown 渲染样式 */
.bubble h1, .bubble h2, .bubble h3, .bubble h4 {{
  margin: 12px 0 6px 0;
  font-weight: 600;
}}
.bubble h1 {{ font-size: 1.5em; }}
.bubble h2 {{ font-size: 1.3em; }}
.bubble h3 {{ font-size: 1.15em; }}
.bubble p {{
  margin: 4px 0;
}}
.bubble ul, .bubble ol {{
  padding-left: 20px;
  margin: 6px 0;
}}
.bubble li {{
  margin: 2px 0;
}}
.bubble blockquote {{
  border-left: 3px solid var(--accent);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--text-secondary);
}}
.bubble a {{
  color: var(--accent);
  text-decoration: none;
}}
.bubble a:hover {{
  text-decoration: underline;
}}
.bubble img {{
  max-width: 100%;
  border-radius: 8px;
}}
.bubble hr {{
  border: none;
  border-top: 1px solid var(--ai-bubble-border);
  margin: 10px 0;
}}

/* 行内代码 */
.bubble code:not(pre code) {{
  background-color: rgba(255,255,255,0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
  font-size: 0.9em;
}}

/* 代码块 */
.code-block {{
  margin: 8px 0;
  border-radius: 8px;
  overflow: hidden;
  background-color: #1e1e2e;
  border: 1px solid rgba(255,255,255,0.1);
}}
.code-block-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px;
  background-color: rgba(255,255,255,0.05);
  font-size: 12px;
  color: var(--text-muted);
}}
.code-copy-btn {{
  background: none;
  border: 1px solid var(--text-muted);
  color: var(--text-muted);
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}}
.code-copy-btn:hover {{
  background-color: var(--accent);
  color: white;
  border-color: var(--accent);
}}
.code-block pre {{
  margin: 0;
  padding: 12px;
  overflow-x: auto;
  font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
}}

/* 表格 */
.bubble table {{
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
  font-size: 13px;
}}
.bubble th, .bubble td {{
  border: 1px solid var(--ai-bubble-border);
  padding: 6px 10px;
  text-align: left;
}}
.bubble th {{
  background-color: rgba(255,255,255,0.05);
  font-weight: 600;
}}

/* 时间标签 */
.timestamp {{
  text-align: center;
  margin: 12px 0 8px 0;
}}
.timestamp span {{
  font-size: 12px;
  color: var(--timestamp-color);
  background-color: var(--timestamp-bg);
  border: 1px solid var(--timestamp-border);
  border-radius: 10px;
  padding: 3px 12px;
}}

/* 系统消息 */
.system-msg {{
  text-align: center;
  margin: 8px 0;
}}
.system-msg span {{
  font-size: 12px;
  color: var(--system-color);
  background-color: var(--system-bg);
  border: 1px solid var(--system-border);
  border-radius: 10px;
  padding: 3px 14px;
}}

/* 思考动画 */
.thinking-dots {{
  display: inline-flex;
  gap: 4px;
  padding: 4px 0;
}}
.thinking-dots .dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--text-secondary);
  animation: dotPulse 1.2s ease-in-out infinite;
}}
.thinking-dots .dot:nth-child(2) {{ animation-delay: 0.2s; }}
.thinking-dots .dot:nth-child(3) {{ animation-delay: 0.4s; }}

@keyframes dotPulse {{
  0%, 80%, 100% {{ opacity: 0.3; transform: scale(0.8); }}
  40% {{ opacity: 1; transform: scale(1); }}
}}

/* 打字光标 */
.typing-cursor {{
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: var(--typing-cursor);
  margin-left: 2px;
  animation: cursorBlink 1s step-end infinite;
  vertical-align: text-bottom;
}}
@keyframes cursorBlink {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0; }}
}}

/* 消息操作按钮（hover 显示） */
.msg-actions {{
  position: absolute;
  top: -8px;
  right: -4px;
  display: none;
  gap: 2px;
  background-color: var(--ai-bubble-bg);
  border: 1px solid var(--ai-bubble-border);
  border-radius: 8px;
  padding: 2px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  z-index: 10;
}}
.msg-row.user .msg-actions {{
  right: auto;
  left: -4px;
}}
.msg-row:hover .msg-actions {{
  display: flex;
}}
.msg-action-btn {{
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.15s;
  border: none;
  background: none;
  color: var(--text-secondary);
}}
.msg-action-btn:hover {{
  background-color: rgba(255,255,255,0.1);
  color: var(--text-primary);
}}

/* 引用消息 */
.quote-bar {{
  border-left: 3px solid var(--accent);
  padding-left: 8px;
  margin: 4px 0;
  color: var(--text-secondary);
  font-size: 12px;
}}

/* 搜索高亮 */
.search-highlight {{
  background-color: #f59f00;
  color: #000;
  border-radius: 2px;
  padding: 0 2px;
}}

/* 淡入动画 */
.msg-row {{
  animation: fadeIn 0.2s ease-out;
}}
@keyframes fadeIn {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* 图片消息 */
.bubble img.msg-image {{
  max-width: 240px;
  max-height: 200px;
  border-radius: 8px;
  display: block;
}}
</style>
</head>
<body>
<div id="chat-container"></div>

<script>
// ===== 消息数据 =====
const messages = [];
let lastRole = null;
let lastTime = 0;
const TIMESTAMP_GAP = 180000; // 3 分钟

// ===== PyBridge (QWebChannel) =====
let pyBridge = null;

// QWebChannel 初始化（在 qwebchannel.js 加载后立即执行）
new QWebChannel(qt.webChannelTransport, function(channel) {{
  pyBridge = channel.objects.pyBridge;
  // 通知 Python 端页面已就绪（在 channel 建立后，而非 DOMContentLoaded）
  if (pyBridge) pyBridge.onPageReady();
}});

// ===== 消息渲染 =====

function addMessage(msg) {{
  const container = document.getElementById('chat-container');
  const sameSender = msg.role === lastRole;
  const showTs = !sameSender || (Date.now() - lastTime > TIMESTAMP_GAP);

  // 时间标签
  if (showTs && msg.timestamp) {{
    const tsDiv = document.createElement('div');
    tsDiv.className = 'timestamp';
    tsDiv.innerHTML = '<span>' + escapeHtml(msg.timestamp) + '</span>';
    container.appendChild(tsDiv);
  }}

  // 消息行
  const row = document.createElement('div');
  row.className = 'msg-row ' + msg.role + (sameSender ? ' same-sender' : '');
  row.dataset.msgId = msg.id || '';

  // 头像
  if (!sameSender) {{
    const avatar = document.createElement('div');
    avatar.className = 'avatar ' + msg.role;
    avatar.textContent = msg.role === 'user' ? 'Me' : 'AI';
    row.appendChild(avatar);
  }} else {{
    const placeholder = document.createElement('div');
    placeholder.className = 'avatar-placeholder';
    row.appendChild(placeholder);
  }}

  // 气泡
  const bubble = document.createElement('div');
  bubble.className = 'bubble ' + msg.role;

  // 引用内容
  if (msg.quote) {{
    const quoteDiv = document.createElement('div');
    quoteDiv.className = 'quote-bar';
    quoteDiv.textContent = msg.quote;
    bubble.appendChild(quoteDiv);
  }}

  // 消息内容
  const contentDiv = document.createElement('div');
  contentDiv.className = 'msg-content';
  contentDiv.innerHTML = msg.html || escapeHtml(msg.text || '');
  bubble.appendChild(contentDiv);

  // 图片
  if (msg.image) {{
    const img = document.createElement('img');
    img.className = 'msg-image';
    img.src = msg.image;
    bubble.appendChild(img);
  }}

  // 操作按钮
  const actions = document.createElement('div');
  actions.className = 'msg-actions';
  actions.innerHTML = getActionButtons(msg.role);
  bubble.appendChild(actions);

  row.appendChild(bubble);
  container.appendChild(row);

  // 更新状态
  lastRole = msg.role;
  lastTime = Date.now();

  // 保存消息引用
  messages.push({{ ...msg, element: row, contentElement: contentDiv }});

  // 渲染 LaTeX 公式
  renderLatex(bubble);

  // 自动滚动
  scrollToBottom();
}}

function getActionButtons(role) {{
  let btns = '<button class="msg-action-btn" onclick="actionCopy(this)" title="复制">📋</button>';
  if (role === 'assistant') {{
    btns += '<button class="msg-action-btn" onclick="actionRetry(this)" title="重新生成">🔄</button>';
  }}
  btns += '<button class="msg-action-btn" onclick="actionQuote(this)" title="引用">💬</button>';
  if (role === 'user') {{
    btns += '<button class="msg-action-btn" onclick="actionEdit(this)" title="编辑重发">✏️</button>';
  }}
  return btns;
}}

// ===== 流式更新 =====

let streamingMsg = null;

function startStreaming(msgId, timestamp) {{
  // 先添加思考中占位
  const container = document.getElementById('chat-container');
  const sameSender = lastRole !== 'assistant';

  // 思考动画
  const row = document.createElement('div');
  row.className = 'msg-row assistant' + (sameSender ? '' : ' same-sender');
  row.id = 'streaming-row';

  if (!sameSender || lastRole !== 'assistant') {{
    const avatar = document.createElement('div');
    avatar.className = 'avatar ai';
    avatar.textContent = 'AI';
    row.appendChild(avatar);
  }} else {{
    const placeholder = document.createElement('div');
    placeholder.className = 'avatar-placeholder';
    row.appendChild(placeholder);
  }}

  const bubble = document.createElement('div');
  bubble.className = 'bubble ai';
  bubble.id = 'streaming-bubble';

  const contentDiv = document.createElement('div');
  contentDiv.className = 'msg-content';
  contentDiv.id = 'streaming-content';
  contentDiv.innerHTML = '<div class="thinking-dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>';

  bubble.appendChild(contentDiv);

  const actions = document.createElement('div');
  actions.className = 'msg-actions';
  actions.innerHTML = getActionButtons('assistant');
  bubble.appendChild(actions);

  row.appendChild(bubble);
  container.appendChild(row);

  streamingMsg = {{ row, bubble, contentDiv, text: '', msgId }};
  lastRole = 'assistant';
  lastTime = Date.now();

  scrollToBottom();
}}

function updateStreaming(text) {{
  if (!streamingMsg) return;
  streamingMsg.text = text;

  // 使用 pyBridge 的同步渲染方法（renderMarkdownSync 直接返回 HTML 字符串）
  if (pyBridge && pyBridge.renderMarkdownSync) {{
    try {{
      var html = pyBridge.renderMarkdownSync(text);
      if (streamingMsg) {{
        streamingMsg.contentDiv.innerHTML = html + '<span class="typing-cursor"></span>';
        scrollToBottom();
      }}
    }} catch(e) {{
      // 降级：简单转义
      streamingMsg.contentDiv.innerHTML = escapeHtml(text).replace(/\\n/g, '<br>') + '<span class="typing-cursor"></span>';
      scrollToBottom();
    }}
  }} else {{
    // 降级：简单转义
    streamingMsg.contentDiv.innerHTML = escapeHtml(text).replace(/\\n/g, '<br>') + '<span class="typing-cursor"></span>';
    scrollToBottom();
  }}
}}

function finishStreaming(text) {{
  if (!streamingMsg) return;

  // 最终渲染（使用同步方法直接获取渲染结果）
  if (pyBridge && pyBridge.renderMarkdownSync) {{
    try {{
      var html = pyBridge.renderMarkdownSync(text);
      if (streamingMsg) {{
        streamingMsg.contentDiv.innerHTML = html;
        streamingMsg.text = text;
        // 保存到消息列表
        messages.push({{
          role: 'assistant',
          text: text,
          html: html,
          element: streamingMsg.row,
          contentElement: streamingMsg.contentDiv,
          msgId: streamingMsg.msgId
        }});
        renderLatex(streamingMsg.bubble);
        streamingMsg = null;
        scrollToBottom();
      }}
    }} catch(e) {{
      streamingMsg.contentDiv.innerHTML = escapeHtml(text).replace(/\\n/g, '<br>');
      streamingMsg.text = text;
      messages.push({{
        role: 'assistant',
        text: text,
        html: streamingMsg.contentDiv.innerHTML,
        element: streamingMsg.row,
        contentElement: streamingMsg.contentDiv,
        msgId: streamingMsg.msgId
      }});
      renderLatex(streamingMsg.bubble);
      streamingMsg = null;
      scrollToBottom();
    }}
  }} else {{
    streamingMsg.contentDiv.innerHTML = escapeHtml(text).replace(/\\n/g, '<br>');
    streamingMsg.text = text;
    messages.push({{
      role: 'assistant',
      text: text,
      html: streamingMsg.contentDiv.innerHTML,
      element: streamingMsg.row,
      contentElement: streamingMsg.contentDiv,
      msgId: streamingMsg.msgId
    }});
    renderLatex(streamingMsg.bubble);
    streamingMsg = null;
    scrollToBottom();
  }}
}}

// ===== 消息操作 =====

function actionCopy(btn) {{
  const bubble = btn.closest('.bubble');
  const content = bubble.querySelector('.msg-content');
  const text = content.innerText || content.textContent;
  navigator.clipboard.writeText(text).then(() => {{
    btn.textContent = '✓';
    setTimeout(() => {{ btn.textContent = '📋'; }}, 1500);
  }});
  if (pyBridge) pyBridge.onAction('copy', text);
}}

function actionRetry(btn) {{
  const row = btn.closest('.msg-row');
  const msgId = row.dataset.msgId;
  if (pyBridge) pyBridge.onAction('retry', msgId || '');
}}

function actionQuote(btn) {{
  const bubble = btn.closest('.bubble');
  const content = bubble.querySelector('.msg-content');
  const text = content.innerText || content.textContent;
  const shortText = text.substring(0, 50) + (text.length > 50 ? '...' : '');
  if (pyBridge) pyBridge.onAction('quote', shortText);
}}

function actionEdit(btn) {{
  const row = btn.closest('.msg-row');
  const msgId = row.dataset.msgId;
  const bubble = btn.closest('.bubble');
  const content = bubble.querySelector('.msg-content');
  const text = content.innerText || content.textContent;
  if (pyBridge) pyBridge.onAction('edit', JSON.stringify({{ msgId: msgId || '', text: text }}));
}}

function copyCode(btn) {{
  const codeBlock = btn.closest('.code-block');
  const code = codeBlock.querySelector('pre')?.textContent || '';
  navigator.clipboard.writeText(code).then(() => {{
    btn.textContent = '已复制';
    setTimeout(() => {{ btn.textContent = '复制'; }}, 1500);
  }});
}}

// ===== 系统消息 =====

function addSystemMsg(text) {{
  const container = document.getElementById('chat-container');
  const div = document.createElement('div');
  div.className = 'system-msg';
  div.innerHTML = '<span>' + escapeHtml(text) + '</span>';
  container.appendChild(div);
  scrollToBottom();
}}

// ===== 时间标签 =====

function addTimestamp(text) {{
  const container = document.getElementById('chat-container');
  const div = document.createElement('div');
  div.className = 'timestamp';
  div.innerHTML = '<span>' + escapeHtml(text) + '</span>';
  container.appendChild(div);
}}

// ===== 清空 =====

function clearChat() {{
  const container = document.getElementById('chat-container');
  container.innerHTML = '';
  messages.length = 0;
  lastRole = null;
  lastTime = 0;
  streamingMsg = null;
}}

// ===== 搜索 =====

function searchMessages(query) {{
  // 清除之前的高亮
  document.querySelectorAll('.search-highlight').forEach(el => {{
    el.replaceWith(el.textContent);
  }});

  if (!query) return 0;

  let count = 0;
  const walker = document.createTreeWalker(
    document.getElementById('chat-container'),
    NodeFilter.SHOW_TEXT,
    null,
    false
  );

  const textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);

  textNodes.forEach(node => {{
    const idx = node.textContent.toLowerCase().indexOf(query.toLowerCase());
    if (idx >= 0) {{
      const span = document.createElement('span');
      span.className = 'search-highlight';
      const range = document.createRange();
      range.setStart(node, idx);
      range.setEnd(node, idx + query.length);
      range.surroundContents(span);
      count++;
    }}
  }});

  // 滚动到第一个高亮
  const first = document.querySelector('.search-highlight');
  if (first) first.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

  return count;
}}

// ===== 主题切换 =====

function setTheme(vars) {{
  const root = document.documentElement;
  Object.entries(vars).forEach(([key, value]) => {{
    root.style.setProperty('--' + key, value);
  }});
}}

// ===== 工具函数 =====

function escapeHtml(text) {{
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}}

function scrollToBottom() {{
  window.scrollTo({{
    top: document.body.scrollHeight,
    behavior: 'smooth'
  }});
}}

// ===== KaTeX 渲染 =====
function renderLatex(element) {{
  if (typeof renderMathInElement === 'function') {{
    try {{
      renderMathInElement(element || document.body, {{
        delimiters: [
          {{left: '$$', right: '$$', display: true}},
          {{left: '$', right: '$', display: false}},
          {{left: '\\\\(', right: '\\\\)', display: false}},
          {{left: '\\\\[', right: '\\\\]', display: true}}
        ],
        throwOnError: false
      }});
    }} catch(e) {{}}
  }}
}}

// ===== 初始化完成 =====
// onPageReady 已在 QWebChannel 回调中调用，无需在 DOMContentLoaded 中重复
</script>
</body>
</html>
"""


# ============ QWebChannel Bridge ============

class ChatBridge(QObject):
    """Python <-> JavaScript 桥接对象

    暴露给 JavaScript 的方法：
    - renderMarkdown(text, callback) → 调用 Python Markdown 渲染器
    - onAction(action, data) → 消息操作回调
    - onPageReady() → 页面加载完成通知
    """

    # 信号定义
    actionRequested = Signal(str, str)    # (action, data)
    pageReady = Signal()
    markdownRendered = Signal(str, str)   # (request_id, html)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._render_callbacks = {}

    @Slot(str, result=str)
    def renderMarkdownSync(self, text: str) -> str:
        """同步 Markdown 渲染（JavaScript 直接调用获取结果）"""
        from gugu_native.theme import is_dark
        return render_markdown(text, "dark" if is_dark() else "light")

    @Slot(str, str)
    def renderMarkdown(self, text: str, callback_id: str):
        """异步 Markdown 渲染（带回调 ID）"""
        from gugu_native.theme import is_dark
        html = render_markdown(text, "dark" if is_dark() else "light")
        # 通过 JS 回调返回结果
        self.markdownRendered.emit(callback_id, html)

    @Slot(str, str)
    def onAction(self, action: str, data: str):
        """JavaScript 消息操作回调"""
        self.actionRequested.emit(action, data)

    @Slot()
    def onPageReady(self):
        """页面加载完成"""
        self.pageReady.emit()


# ============ QWebEngineView 聊天显示 ============

class ChatWebDisplay(QWidget):
    """QWebEngineView 聊天显示组件

    提供与 ChatPage 兼容的接口：
    - append_user_msg(text)
    - append_ai_msg(text)
    - append_system_msg(text)
    - start_streaming(msg_id)
    - update_streaming(text)
    - finish_streaming(text)
    - clear()
    - search(query) → count
    - refresh_theme()

    信号:
    - action_copy(text)
    - action_retry(msg_id)
    - action_quote(text)
    - action_edit(msg_id, text)
    """

    # 消息操作信号
    action_copy = Signal(str)
    action_retry = Signal(str)
    action_quote = Signal(str)
    action_edit = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._web_view = None
        self._bridge = None
        self._channel = None
        self._page_ready = False
        self._pending_messages = []
        self._msg_counter = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if _WEBENGINE_AVAILABLE:
            self._init_webengine(layout)
        else:
            self._init_fallback(layout)

    def _init_webengine(self, layout):
        """初始化 QWebEngineView 模式"""
        self._bridge = ChatBridge(self)
        self._bridge.actionRequested.connect(self._on_js_action)
        self._bridge.pageReady.connect(self._on_page_ready)

        self._channel = QWebChannel(self)
        self._channel.registerObject("pyBridge", self._bridge)

        self._web_view = QWebEngineView(self)
        self._web_view.page().setWebChannel(self._channel)

        # 捕获 JS 控制台消息用于调试
        self._web_view.page().javaScriptConsoleMessage = self._on_js_console

        # 加载 HTML
        html = self._generate_html()
        self._web_view.setHtml(html, QUrl("file:///"))

        layout.addWidget(self._web_view)

    def _init_fallback(self, layout):
        """降级为 QTextEdit 模式"""
        from gugu_native.theme import get_colors
        c = get_colors()

        self._fallback_display = QTextEdit()
        self._fallback_display.setReadOnly(True)
        self._fallback_display.setFont(QFont("Microsoft YaHei UI", 10))
        self._fallback_display.setPlaceholderText("开始和 AI 对话吧 ✨")
        self._fallback_display.setFrameShape(QTextEdit.Shape.NoFrame)
        self._fallback_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c.chat_bg};
                color: {c.text_primary};
                border: none;
                border-radius: 13px;
                padding: 14px 16px;
                selection-background-color: {c.accent};
                selection-color: white;
            }}
        """)
        layout.addWidget(self._fallback_display)

    def _generate_html(self) -> str:
        """生成 HTML 页面"""
        from gugu_native.theme import get_colors, is_dark
        c = get_colors()

        return _CHAT_HTML_TEMPLATE.format(
            qwebchannel_js=_QWEBCHANNEL_JS,
            bg_color=c.chat_bg,
            text_primary=c.text_primary,
            text_secondary=c.text_secondary,
            text_muted=c.text_muted,
            ai_bubble_bg=c.ai_bubble_bg,
            ai_bubble_border=c.ai_bubble_border,
            user_bubble_bg=c.user_bubble_bg,
            user_text_color=c.user_text_color,
            system_bg=c.chat_timestamp_bg,
            system_border=c.chat_timestamp_border,
            system_color=c.system_msg_color,
            timestamp_bg=c.chat_timestamp_bg,
            timestamp_border=c.chat_timestamp_border,
            timestamp_color=c.timestamp_color,
            accent=c.accent,
            avatar_size=c.chat_avatar_size,
            avatar_font_size=max(int(c.chat_avatar_size * 0.38), 10),
            typing_cursor_color=c.chat_typing_cursor_color,
        )

    # ===== 公共接口 =====

    def append_user_msg(self, text: str, quote: str = "", timestamp: str = None):
        """添加用户消息

        Args:
            text: 消息文本
            quote: 引用文本
            timestamp: 消息时间戳(ISO格式)。
                       None = 新消息，使用当前时间；
                       "" = 历史消息无时间戳，使用当前时间作为兜底；
                       有效ISO字符串 = 解析后显示真实时间
        """
        from gugu_native.theme import format_timestamp
        if timestamp:
            # 从 iso 格式解析后格式化显示
            try:
                dt = datetime.fromisoformat(timestamp)
                ts = format_timestamp(dt)
            except (ValueError, TypeError):
                ts = format_timestamp(datetime.now())
        else:
            # None 或 ""：使用当前时间
            ts = format_timestamp(datetime.now())
        html = render_markdown(text)

        if self._web_view:
            msg_json = json.dumps({
                "role": "user",
                "text": text,
                "html": html,
                "timestamp": ts,
                "quote": quote,
                "id": str(self._next_msg_id()),
            }, ensure_ascii=False)
            self._run_js(f"addMessage({msg_json})")
        else:
            self._fallback_append_user(text)

    def append_ai_msg(self, text: str, quote: str = "", timestamp: str = None):
        """添加 AI 消息

        Args:
            text: 消息文本
            quote: 引用文本
            timestamp: 消息时间戳(ISO格式)。
                       None = 新消息，使用当前时间；
                       "" = 历史消息无时间戳，使用当前时间作为兜底；
                       有效ISO字符串 = 解析后显示真实时间
        """
        from gugu_native.theme import format_timestamp
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                ts = format_timestamp(dt)
            except (ValueError, TypeError):
                ts = format_timestamp(datetime.now())
        else:
            # None 或 ""：使用当前时间
            ts = format_timestamp(datetime.now())
        html = render_markdown(text)

        if self._web_view:
            msg_json = json.dumps({
                "role": "assistant",
                "text": text,
                "html": html,
                "timestamp": ts,
                "quote": quote,
                "id": str(self._next_msg_id()),
            }, ensure_ascii=False)
            self._run_js(f"addMessage({msg_json})")
        else:
            self._fallback_append_ai(text)

    def append_system_msg(self, text: str):
        """添加系统消息"""
        if self._web_view:
            escaped = json.dumps(text, ensure_ascii=False)
            self._run_js(f"addSystemMsg({escaped})")
        else:
            from gugu_native.theme import get_system_msg_html
            self._fallback_display.append(get_system_msg_html(text))
            self._fallback_display.moveCursor(QTextCursor.MoveOperation.End)

    def start_streaming(self, msg_id: str = ""):
        """开始流式消息"""
        from gugu_native.theme import format_timestamp
        ts = format_timestamp(datetime.now())

        if self._web_view:
            self._run_js(f"startStreaming('{msg_id}', '{ts}')")
        else:
            # QTextEdit fallback: 添加思考中占位
            from gugu_native.theme import get_colors
            c = get_colors()
            self._fallback_display.append(
                f'<div id="thinking-dots" style="margin:8px 0;text-align:center;">'
                f'<span style="color:{c.text_muted};">正在思考...</span></div>'
            )
            self._fallback_display.moveCursor(QTextCursor.MoveOperation.End)

    def update_streaming(self, text: str):
        """更新流式文本"""
        if self._web_view:
            escaped = json.dumps(text, ensure_ascii=False)
            self._run_js(f"updateStreaming({escaped})")
        else:
            # QTextEdit fallback: 简单追加
            pass

    def finish_streaming(self, text: str):
        """完成流式消息"""
        if self._web_view:
            escaped = json.dumps(text, ensure_ascii=False)
            self._run_js(f"finishStreaming({escaped})")
        else:
            # QTextEdit fallback: 替换思考占位，追加最终消息
            self._fallback_append_ai(text)

    def clear(self):
        """清空对话"""
        if self._web_view:
            self._run_js("clearChat()")
        else:
            self._fallback_display.clear()

    def search(self, query: str) -> int:
        """搜索消息"""
        if self._web_view:
            # 异步搜索，返回值通过信号获取
            escaped = json.dumps(query, ensure_ascii=False)
            self._run_js(f"searchMessages({escaped})")
            return 0
        return 0

    def refresh_theme(self):
        """刷新主题"""
        if self._web_view:
            from gugu_native.theme import get_colors, is_dark
            c = get_colors()
            vars_json = json.dumps({
                "bg": c.chat_bg,
                "text-primary": c.text_primary,
                "text-secondary": c.text_secondary,
                "text-muted": c.text_muted,
                "ai-bubble-bg": c.ai_bubble_bg,
                "ai-bubble-border": c.ai_bubble_border,
                "user-bubble-bg": c.user_bubble_bg,
                "user-text-color": c.user_text_color,
                "system-bg": c.chat_timestamp_bg,
                "system-border": c.chat_timestamp_border,
                "system-color": c.system_msg_color,
                "timestamp-bg": c.chat_timestamp_bg,
                "timestamp-border": c.chat_timestamp_border,
                "timestamp-color": c.timestamp_color,
                "accent": c.accent,
                "typing-cursor": c.chat_typing_cursor_color,
            }, ensure_ascii=False)
            self._run_js(f"setTheme({vars_json})")
        else:
            from gugu_native.theme import get_colors
            c = get_colors()
            self._fallback_display.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {c.chat_bg};
                    color: {c.text_primary};
                    border: none;
                    border-radius: 13px;
                    padding: 14px 16px;
                }}
            """)

    def append_image(self, image_path: str):
        """添加图片消息"""
        abs_path = os.path.abspath(image_path).replace("\\", "/")
        ts_text = ""
        from gugu_native.theme import format_timestamp
        ts_text = format_timestamp(datetime.now())

        if self._web_view:
            msg_json = json.dumps({
                "role": "user",
                "text": "",
                "html": "",
                "timestamp": ts_text,
                "image": f"file:///{abs_path}",
                "id": str(self._next_msg_id()),
            }, ensure_ascii=False)
            self._run_js(f"addMessage({msg_json})")

    # ===== 内部方法 =====

    def _on_js_console(self, level, message, line, source):
        """捕获 JS 控制台消息用于调试"""
        level_names = {0: "INFO", 1: "WARNING", 2: "ERROR", 3: "DEBUG"}
        level_name = level_names.get(level, str(level))
        # 只打印 WARNING 和 ERROR，避免 INFO 刷屏
        if level >= 1:
            print(f"[ChatWebDisplay JS {level_name}] {message} (line {line})")

    def _run_js(self, js_code: str):
        """执行 JavaScript 代码"""
        if self._web_view:
            if self._page_ready:
                self._web_view.page().runJavaScript(js_code)
            else:
                self._pending_messages.append(js_code)

    def _on_page_ready(self):
        """页面加载完成回调"""
        self._page_ready = True
        print(f"[ChatWebDisplay] Page ready! Executing {len(self._pending_messages)} pending messages")
        # 执行待处理的消息
        for js_code in self._pending_messages:
            self._web_view.page().runJavaScript(js_code)
        self._pending_messages.clear()

    def _on_js_action(self, action: str, data: str):
        """处理 JavaScript 操作回调"""
        if action == "copy":
            self.action_copy.emit(data)
        elif action == "retry":
            self.action_retry.emit(data)
        elif action == "quote":
            self.action_quote.emit(data)
        elif action == "edit":
            try:
                edit_data = json.loads(data)
                msg_id = edit_data.get("msgId", "")
                text = edit_data.get("text", "")
                self.action_edit.emit(msg_id, text)
            except Exception:
                pass

    def _next_msg_id(self) -> int:
        """生成下一个消息 ID"""
        self._msg_counter += 1
        return self._msg_counter

    # ===== QTextEdit 降级方法 =====

    def _fallback_append_user(self, text: str):
        """QTextEdit 降级：用户消息"""
        from gugu_native.theme import (
            get_colors, get_user_avatar_svg
        )
        c = get_colors()
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self._fallback_display.append(
            f'<table width="100%" cellspacing="0" cellpadding="0" style="margin:12px 0 0 0;">'
            f'<tr>'
            f'<td width="30%"></td>'
            f'<td align="right">'
            f'<div style="background-color:{c.user_bubble_bg};'
            f'color:{c.user_text_color};border-radius:12px;'
            f'padding:10px 16px;font-size:14px;line-height:1.7;text-align:left;">'
            f'{escaped}</div></td>'
            f'<td width="42" valign="top" align="right">'
            f'{get_user_avatar_svg(c.chat_avatar_size)}</td>'
            f'</tr></table>'
        )
        self._fallback_display.moveCursor(QTextCursor.MoveOperation.End)

    def _fallback_append_ai(self, text: str):
        """QTextEdit 降级：AI 消息"""
        from gugu_native.theme import (
            get_colors, get_ai_avatar_svg
        )
        c = get_colors()
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self._fallback_display.append(
            f'<table width="100%" cellspacing="0" cellpadding="0" style="margin:12px 0 0 0;">'
            f'<tr>'
            f'<td width="42" valign="top">'
            f'{get_ai_avatar_svg(c.chat_avatar_size)}</td>'
            f'<td align="left">'
            f'<div style="background-color:{c.ai_bubble_bg};'
            f'border:1px solid {c.ai_bubble_border};'
            f'color:{c.text_primary};border-radius:12px;'
            f'padding:10px 16px;font-size:14px;line-height:1.7;">'
            f'{escaped}</div></td>'
            f'<td width="30%"></td>'
            f'</tr></table>'
        )
        self._fallback_display.moveCursor(QTextCursor.MoveOperation.End)

    @property
    def is_webengine(self) -> bool:
        """是否使用 QWebEngineView 模式"""
        return self._web_view is not None
