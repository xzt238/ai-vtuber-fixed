# 咕咕嘎嘎 AI-VTuber 工具系统升级可行性报告

> 版本: v1.9.61 规划
> 日期: 2026-05-01
> 作者: AI 助手

---

## 一、现状诊断

### 1.1 核心问题：工具系统"建了但没用起来"

经过完整代码审查，发现以下 **5 个致命缺陷**：

| # | 问题 | 严重程度 | 说明 |
|---|------|---------|------|
| 1 | **LLM 不支持原生 Function Calling** | 🔴 P0 | 三个 LLM 引擎都没有向 API 传 `tools` 参数，LLM 根本不知道有工具可用 |
| 2 | **本地工具没有 JSON Schema** | 🔴 P0 | 9 个工具类只有 `name` + `description`，没有参数模式定义，无法生成 API 所需的 `tools` 字段 |
| 3 | **MCP 服务器配置为空** | 🟡 P1 | `config.yaml` 中 `mcp.servers: {}`，用户打开 MCP 面板只看到"暂无服务器" |
| 4 | **LLM 工具调用不可视化** | 🟡 P1 | LLM 自动触发的工具调用(BASH:/READ:/ACTION:execute)不发送 `tool_call_start/end` 事件，前端看不到 |
| 5 | **工具提示词太简陋** | 🟡 P1 | 系统提示只说"你可以使用工具"，没列出工具名、参数格式、调用示例 |

### 1.2 当前数据流（断裂的）

```
用户消息 → LLM.chat() → 返回 {text, action}
                           ├─ action.type=="execute" → ToolExecutor.execute() → 结果拼入reply
                           └─ reply包含"BASH:/READ:/WRITE:/EDIT:" → _handle_local_tool() → 结果拼入reply
                              → 最终reply → TTS + 前端聊天区
                              → 工具可视化面板：❌ 看不到
```

前端手动触发的流程倒是通的：
```
前端按钮 → WS {type:"tool"} → _handle_tool() → ToolFactory/MCP
                                    ├─ WS tool_call_start (前端可视化)
                                    ├─ WS tool_result
                                    └─ WS tool_call_end
```

### 1.3 已有资产盘点

**后端** (可用，但需补全):
- `app/tools/__init__.py` — 9 个内置工具 + ToolFactory 工厂
- `app/mcp/__init__.py` — MCPToolBridge + MCPTransport (stdio)，架构完整
- `app/web/__init__.py` — WebSocket 工具消息路由 (tool/mcp/tool_viz)

**前端** (可用，需增强):
- 工具可视化面板 — 列出工具 + 实时调用卡片
- MCP 面板 — 服务器管理 + 工具列表
- 工具执行面板 — 执行队列

---

## 二、行业标杆调研

### 2.1 Open-LLM-VTuber（7.2k ⭐，最值得借鉴）

**核心架构**：三层工具调用模式

| 模式 | 适用 LLM | 工具格式 | 检测方式 |
|------|---------|---------|---------|
| OpenAI 模式 | GPT-4/DeepSeek 等 | `tools` 参数 + `tool_calls` 响应 | API 原生返回 |
| Claude 模式 | Claude 3+ 等 | `tool_use` blocks | API 原生返回 |
| Prompt 模式 | 不支持 FC 的模型 | 文本 JSON 注入系统提示 | `StreamJSONDetector` 解析 |

**关键设计**：
1. **ToolAdapter** — MCP 工具 → 三种 LLM 格式转换器
2. **自动降级** — 如果 LLM 返回 `__API_NOT_SUPPORT_TOOLS__`，自动切到 Prompt 模式
3. **多轮工具调用循环** — 工具结果 → 注入对话历史 → 继续 LLM 调用 → 直到无更多工具调用
4. **共享 + 每会话** — ServerRegistry(共享) + ToolManager/ToolExecutor(每会话)

**借鉴价值**: ⭐⭐⭐⭐⭐ — 架构设计最完善，三层降级是标准做法

### 2.2 Open Interpreter（58k ⭐，最激进的方案）

**核心设计**: 单一 `execute` 工具

```json
{
  "name": "execute",
  "parameters": {
    "language": {"enum": ["python", "shell", "javascript"]},
    "code": {"type": "string"}
  }
}
```

**关键设计**：
1. 只暴露一个 `execute` 工具，LLM 通过 `language` + `code` 调用
2. 三种模式：tool_calling → function_calling → text（自动降级）
3. 文本模式解析 Markdown 代码块 ` ```python\ncode\n``` `
4. 动态语言枚举 — 每次请求前注入当前可用语言

**借鉴价值**: ⭐⭐⭐⭐ — 单一工具设计简洁，但不适合 VTuber 场景（需要丰富工具而非代码执行）

### 2.3 Claude Desktop（Anthropic 官方）

**核心设计**: JSON 配置文件管理 MCP 服务器

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

**借鉴价值**: ⭐⭐⭐⭐⭐ — 配置格式就是 MCP 标准，我们的 MCPTransport 已兼容

---

## 三、本地 MCP 服务器清单

以下 MCP 服务器 **完全本地运行，不需要任何 API Key**：

| 名称 | npm 包 | 功能 | 适用场景 | 配置命令 |
|------|--------|------|---------|---------|
| **Filesystem** | `@modelcontextprotocol/server-filesystem` | 读写本地文件/目录 | AI 操作用户文件 | `npx -y @modelcontextprotocol/server-filesystem C:\Users\x\Desktop` |
| **Memory** | `@modelcontextprotocol/server-memory` | 持久化知识图谱 | AI 长期记忆增强 | `npx -y @modelcontextprotocol/server-memory` |
| **Sequential Thinking** | `@modelcontextprotocol/server-sequential-thinking` | 结构化逐步推理 | AI 复杂推理 | `npx -y @modelcontextprotocol/server-sequential-thinking` |
| **Fetch** | `@modelcontextprotocol/server-fetch` | HTTP 请求/网页抓取 | AI 查询网页 | `npx -y @modelcontextprotocol/server-fetch` |
| **SQLite** | `@modelcontextprotocol/server-sqlite` | 本地 SQLite 数据库 | AI 查询数据 | `npx -y @modelcontextprotocol/server-sqlite --db-path ./data.db` |
| **Git** | `@modelcontextprotocol/server-git` | 本地 Git 操作 | AI 管理代码 | `npx -y @modelcontextprotocol/server-git --repository C:\path\to\repo` |
| **Puppeteer** | `@modelcontextprotocol/server-puppeteer` | 浏览器自动化 | AI 网页交互 | `npx -y @modelcontextprotocol/server-puppeteer` |

**需要 API Key 的**（暂不推荐预配置）：
- Brave Search (`BRAVE_API_KEY`)
- GitHub (`GITHUB_TOKEN`)
- Google Maps (`GOOGLE_MAPS_API_KEY`)

---

## 四、升级方案设计

### Phase 1：LLM 原生 Function Calling 支持（P0，核心必做）

#### 4.1.1 给本地工具添加 JSON Schema

每个 Tool 子类新增 `parameters_schema` 属性：

```python
class ReadTool(Tool):
    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "limit": {"type": "integer", "description": "最大读取行数", "default": 100}
            },
            "required": ["path"]
        }
```

ToolFactory 新增 `get_tools_schema()` 方法，生成 OpenAI/Claude 格式的 tools 列表。

#### 4.1.2 三引擎添加 tools 参数

**OpenAILLM** (覆盖 DeepSeek/Kimi/Qwen/GLM/Doubao/Mimo/Ollama):
```python
data["tools"] = self._format_tools_openai(tool_schemas)
```

**AnthropicLLM**:
```python
data["tools"] = self._format_tools_claude(tool_schemas)
```

**MiniMaxLLM** (根据 base_url 判断格式):
```python
if "/anthropic" in self.base_url:
    data["tools"] = self._format_tools_claude(tool_schemas)
else:
    data["tools"] = self._format_tools_openai(tool_schemas)
```

#### 4.1.3 工具调用循环

```
LLM.chat(tools=schemas) → 返回 tool_calls
    → 执行工具 → 结果注入对话历史
    → LLM.chat(历史+工具结果) → 继续对话
    → 直到 LLM 不再调用工具，返回最终文本
```

#### 4.1.4 Prompt 模式降级

对于不支持 Function Calling 的模型（如部分本地 Ollama 模型）：
- 将工具列表 + JSON Schema 格式化为文本，注入系统提示
- 解析 LLM 输出中的 JSON 工具调用 `{"tool": "read", "args": {"path": "..."}}`
- 执行后结果同样注入对话历史

### Phase 2：内置工具前端展示（P1）

#### 4.2.1 工具面板增强

当前 `toolVizListAll()` 已经能返回本地 + MCP 工具列表，但展示太简陋。

改进：
1. 每个工具显示：**名称 + 描述 + 参数表 + 来源标签(本地/MCP) + 只读标记**
2. 工具开关 — 每个工具可单独启用/禁用
3. 工具分类 — 文件操作 / 搜索 / 执行 / 智能 / MCP

```
┌─────────────────────────────────────┐
│ 🔧 工具箱                           │
├─────────────────────────────────────┤
│ 📁 文件操作                          │
│  ├ read   读取文件  [只读] [✓启用]   │
│  ├ write  写入文件  [✓启用]          │
│  └ edit   编辑文件  [✓启用]          │
│ 🔍 搜索工具                          │
│  ├ glob   搜索文件名 [只读] [✓启用]   │
│  ├ grep   搜索内容   [只读] [✓启用]   │
│  └ ls     列出目录   [只读] [✓启用]   │
│ ⚡ 执行工具                          │
│  └ bash   执行命令  [✓启用]          │
│ 🧠 智能工具                          │
│  ├ think  深度思考   [只读] [✓启用]   │
│  └ architect 架构分析 [只读] [✓启用]  │
│ 🔌 MCP 工具                          │
│  └ (无MCP服务器连接)                 │
└─────────────────────────────────────┘
```

### Phase 3：预配置本地 MCP 服务器（P1）

#### 4.3.1 config.yaml 默认配置

```yaml
mcp:
  enabled: true
  servers:
    filesystem:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "."]
      description: "本地文件系统操作"
      enabled: false  # 默认关闭，用户自行开启
    memory:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-memory"]
      description: "持久化知识图谱"
      enabled: false
    fetch:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-fetch"]
      description: "HTTP 请求/网页抓取"
      enabled: false
    sequential-thinking:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-sequential-thinking"]
      description: "结构化逐步推理"
      enabled: false
```

> **注意**: 默认 `enabled: false`，因为 npx 首次下载需要网络。用户在 MCP 面板中一键开启。

#### 4.3.2 MCP 面板增强

1. 服务器列表显示：**名称 + 描述 + 连接状态 + 工具数量 + 启用开关**
2. 一键启用/禁用（改 config + 重连）
3. 连接失败时显示错误原因（npx 未安装 / 网络问题等）

### Phase 4：LLM 工具调用可视化打通（P1）

#### 4.4.1 统一工具调用事件

当前问题：LLM 自动调用的工具走 `_handle_local_tool()` 或 `ToolExecutor.execute()`，不经过 WebSocket。

修复：在 `main.py` 的工具执行路径中，添加 `tool_call_start` / `tool_call_end` 事件发送：

```python
# 工具执行前
ws.broadcast({"type": "tool_call_start", "tool": name, "args": args, "call_id": id, "source": "llm"})

# 工具执行后
ws.broadcast({"type": "tool_call_end", "tool": name, "result": result, "call_id": id, "source": "llm"})
```

这样无论是用户手动触发还是 LLM 自动触发，工具调用都会在前端可视化面板中显示。

---

## 五、实施优先级和依赖关系

```
Phase 1 (P0): LLM Function Calling 支持
  ├─ 4.1.1 工具 JSON Schema ← 无依赖，先做
  ├─ 4.1.2 三引擎 tools 参数 ← 依赖 4.1.1
  ├─ 4.1.3 工具调用循环 ← 依赖 4.1.2
  └─ 4.1.4 Prompt 模式降级 ← 依赖 4.1.3

Phase 2 (P1): 前端工具展示增强
  ├─ 4.2.1 工具面板 ← 独立，可与 Phase 1 并行

Phase 3 (P1): 预配置本地 MCP
  ├─ 4.3.1 config 默认配置 ← 独立
  └─ 4.3.2 MCP 面板增强 ← 依赖 4.3.1

Phase 4 (P1): 工具调用可视化打通
  └─ 4.4.1 统一事件 ← 依赖 Phase 1
```

**建议实施顺序**: 4.1.1 → 4.1.2 → 4.1.3 → 4.4.1 → 4.2.1 → 4.1.4 → 4.3.1 → 4.3.2

---

## 六、工作量估算

| 阶段 | 改动文件 | 预计工作量 |
|------|---------|-----------|
| 4.1.1 工具 Schema | `app/tools/__init__.py` | 小（9 个工具加属性） |
| 4.1.2 三引擎 tools | `app/llm/__init__.py` | 中（3 个引擎，OpenAI/Anthropic/MiniMax 格式） |
| 4.1.3 调用循环 | `app/llm/__init__.py` + `app/main.py` | 大（核心逻辑重构） |
| 4.1.4 Prompt 降级 | `app/llm/__init__.py` + `app/llm/prompts.py` | 中 |
| 4.2.1 前端展示 | `app/web/static/index.html` | 中 |
| 4.3.1 MCP 预配置 | `app/config.yaml` | 小 |
| 4.3.2 MCP 面板 | `app/web/static/index.html` + `app/web/__init__.py` | 中 |
| 4.4.1 可视化打通 | `app/main.py` + `app/web/__init__.py` | 小 |

---

## 七、风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| Function Calling 改动大，可能影响现有对话流程 | 🟡 | 分步实施，每步都保留旧路径作为 fallback |
| 部分 LLM 不支持 tools 参数（如本地 Ollama） | 🟡 | Prompt 模式降级 |
| npx 首次下载 MCP 服务器需要网络 | 🟢 | 默认 enabled:false，用户手动开启 |
| BashTool 安全风险（LLM 执行任意命令） | 🔴 | 白名单机制 + 用户确认弹窗 |
| MCP 子进程管理复杂（崩溃/超时） | 🟡 | 已有 _close_process + 重连机制 |

---

## 八、总结

### 核心结论

1. **工具系统"骨架"已经搭好**（ToolFactory + MCPToolBridge + 前端面板），但**神经没连上** — LLM 不知道有工具、工具调用不可视化、MCP 没配置服务器。

2. **最关键的一步是 Phase 1**：让 LLM 通过原生 Function Calling 调用工具。这一步做好后，工具系统才真正"活"起来。

3. **Open-LLM-VTuber 的三层降级方案**是最成熟的参考实现：OpenAI Tool Calling → Claude Tool Use → Prompt 文本模式。

4. **本地 MCP 服务器**（filesystem/memory/fetch 等）可以让用户零成本扩展工具能力，只需 `npx` 即可运行。

5. **内置 9 个工具必须展示在前端**，让用户清楚知道 AI 能做什么。当前面板虽然能列出工具，但展示效果太简陋，需要增强为分类卡片式展示。

### 下一步行动

如果你认可这个方案，我建议从 **Phase 1 的 4.1.1（工具 JSON Schema）** 开始实施。这是最小改动但最关键的步骤，后续所有工作都依赖它。
