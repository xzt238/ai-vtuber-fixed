#!/usr/bin/env python3
"""
=====================================
MCP (Model Context Protocol) 工具桥接模块
=====================================

v1.9.52: 新增功能
将 Anthropic 的 MCP 协议集成到咕咕嘎嘎工具系统中，
让 AI 可以调用外部 MCP 服务器提供的工具（如文件系统、GitHub、数据库等）。

架构设计:
    1. MCPToolBridge: 核心桥接类，管理 MCP 服务器连接和工具调用
    2. stdio transport: 通过子进程 stdin/stdout 与 MCP 服务器通信
    3. MCP: 前缀路由: 工具名以 "MCP:" 开头的走 MCP 通道
    4. 与现有 ToolFactory 共存: 不修改原工具系统，通过桥接扩展

MCP 协议核心概念:
    - Server: 提供工具的 MCP 服务器（独立进程）
    - Tool: 服务器暴露的可调用工具
    - Resource: 服务器暴露的可读资源（暂不实现）
    - Transport: 通信方式（stdio / SSE）

配置来源: config.yaml → mcp 节

作者: 咕咕嘎嘎
日期: 2026-05-01
"""

import asyncio
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import AIVTuber


class MCPTransport:
    """
    MCP stdio 传输层

    通过子进程 stdin/stdout 与 MCP 服务器通信。
    每个请求是一个 JSON-RPC 消息，响应也是 JSON-RPC。
    """

    def __init__(self, command: str, args: List[str] = None, env: Dict[str, str] = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process = None
        self._lock = threading.Lock()
        self._request_id = 0
        self._connected = False

    def connect(self) -> bool:
        """启动 MCP 服务器子进程并完成初始化握手"""
        try:
            import os
            env = os.environ.copy()
            env.update(self.env)

            cmd = [self.command] + self.args
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0,
            )

            # 发送 initialize 请求
            result = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "gugugaga-ai-vtuber",
                    "version": "1.9.52"
                }
            })

            if result is None:
                print(f"[MCP] 初始化握手失败: {self.command}")
                self._close_process()
                return False

            # 发送 initialized 通知
            self._send_notification("notifications/initialized", {})

            self._connected = True
            print(f"[MCP] 连接成功: {self.command}")
            return True

        except Exception as e:
            print(f"[MCP] 连接异常: {e}")
            self._close_process()
            return False

    def disconnect(self):
        """断开与 MCP 服务器的连接"""
        self._connected = False
        self._close_process()

    def _close_process(self):
        """安全关闭子进程"""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

    def _send_request(self, method: str, params: dict = None) -> Optional[dict]:
        """发送 JSON-RPC 请求并等待响应"""
        if not self._process or self._process.poll() is not None:
            return None

        with self._lock:
            self._request_id += 1
            req_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params:
            request["params"] = params

        try:
            # 写入请求（每个消息以换行符结尾）
            msg = json.dumps(request) + "\n"
            self._process.stdin.write(msg.encode("utf-8"))
            self._process.stdin.flush()

            # 读取响应（逐行读取，直到获得匹配的 id）
            # 设置超时防止永久阻塞
            start = time.time()
            timeout = 30  # 30秒超时

            while time.time() - start < timeout:
                # 非阻塞检查进程是否还活着
                if self._process.poll() is not None:
                    return None

                try:
                    line = self._process.stdout.readline()
                    if not line:
                        time.sleep(0.1)
                        continue

                    line = line.decode("utf-8").strip()
                    if not line:
                        continue

                    response = json.loads(line)

                    # 检查是否是我们请求的响应
                    if response.get("id") == req_id:
                        if "error" in response:
                            print(f"[MCP] 请求错误: {response['error']}")
                            return None
                        return response.get("result")

                    # 忽略不匹配的响应（可能是通知等）
                except json.JSONDecodeError:
                    continue
                except Exception:
                    time.sleep(0.1)
                    continue

            print(f"[MCP] 请求超时: {method}")
            return None

        except Exception as e:
            print(f"[MCP] 发送请求异常: {e}")
            return None

    def _send_notification(self, method: str, params: dict = None):
        """发送 JSON-RPC 通知（不期望响应）"""
        if not self._process or self._process.poll() is not None:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params

        try:
            msg = json.dumps(notification) + "\n"
            self._process.stdin.write(msg.encode("utf-8"))
            self._process.stdin.flush()
        except Exception as e:
            print(f"[MCP] 发送通知异常: {e}")

    def call_tool(self, tool_name: str, arguments: dict = None) -> Optional[dict]:
        """调用 MCP 服务器上的工具"""
        params = {
            "name": tool_name,
        }
        if arguments:
            params["arguments"] = arguments

        return self._send_request("tools/call", params)

    def list_tools(self) -> List[dict]:
        """列出 MCP 服务器提供的所有工具"""
        result = self._send_request("tools/list", {})
        if result and "tools" in result:
            return result["tools"]
        return []

    @property
    def is_connected(self) -> bool:
        """检查连接是否仍然活跃"""
        return (self._connected and
                self._process is not None and
                self._process.poll() is None)


class MCPServerConfig:
    """MCP 服务器配置"""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.command = config.get("command", "")
        self.args = config.get("args", [])
        self.env = config.get("env", {})
        self.enabled = config.get("enabled", True)
        self.description = config.get("description", "")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "enabled": self.enabled,
            "description": self.description,
        }


class MCPToolBridge:
    """
    MCP 工具桥接器

    负责管理多个 MCP 服务器连接，并将 MCP 工具映射到本地工具系统。
    提供统一的工具调用接口，让 LLM 可以透明地使用 MCP 工具。

    工具名路由:
        - "MCP:server_name:tool_name" → 走 MCP 通道
        - 其他 → 走本地 ToolFactory

    使用方式:
        bridge = MCPToolBridge(app)
        bridge.start()          # 启动所有 MCP 服务器
        tools = bridge.list_all_tools()  # 列出所有工具（含 MCP）
        result = bridge.execute("MCP:github:create_issue", title="hello")
    """

    def __init__(self, app: "AIVTuber"):
        self.app = app
        self.logger = getattr(app, 'logger', None) or print
        self._servers: Dict[str, MCPServerConfig] = {}
        self._transports: Dict[str, MCPTransport] = {}
        self._tool_cache: Dict[str, List[dict]] = {}  # server_name -> [tool_defs]
        self._running = False

        # 从配置加载 MCP 服务器定义
        mcp_config = app.config.config.get("mcp", {})
        servers = mcp_config.get("servers", {})
        for name, server_conf in servers.items():
            cfg = MCPServerConfig(name, server_conf)
            if cfg.enabled and cfg.command:
                self._servers[name] = cfg

    def start(self):
        """启动所有 MCP 服务器连接"""
        if self._running:
            return
        self._running = True

        if not self._servers:
            print("[MCP] 未配置 MCP 服务器 (config.yaml → mcp.servers)")
            return

        print(f"[MCP] 启动 {len(self._servers)} 个 MCP 服务器...")
        for name, cfg in self._servers.items():
            self._connect_server(name, cfg)

    def stop(self):
        """停止所有 MCP 服务器连接"""
        self._running = False
        for name, transport in list(self._transports.items()):
            try:
                transport.disconnect()
                print(f"[MCP] 已断开: {name}")
            except Exception as e:
                print(f"[MCP] 断开异常 ({name}): {e}")
        self._transports.clear()
        self._tool_cache.clear()

    def _connect_server(self, name: str, cfg: MCPServerConfig):
        """连接单个 MCP 服务器"""
        try:
            transport = MCPTransport(
                command=cfg.command,
                args=cfg.args,
                env=cfg.env,
            )

            if transport.connect():
                self._transports[name] = transport
                # 缓存工具列表
                tools = transport.list_tools()
                self._tool_cache[name] = tools
                print(f"[MCP] {name}: {len(tools)} 个工具可用")
            else:
                print(f"[MCP] {name}: 连接失败")
        except Exception as e:
            print(f"[MCP] {name}: 连接异常 - {e}")

    def list_all_tools(self) -> List[dict]:
        """列出所有可用工具（本地 + MCP）"""
        # 本地工具
        from tools import ToolFactory
        local_tools = ToolFactory.list_tools()

        result = []
        for t in local_tools:
            result.append({
                "name": t["name"],
                "description": t["description"],
                "source": "local",
            })

        # MCP 工具
        for server_name, tools in self._tool_cache.items():
            for t in tools:
                tool_name = t.get("name", "?")
                mcp_name = f"MCP:{server_name}:{tool_name}"
                result.append({
                    "name": mcp_name,
                    "description": t.get("description", ""),
                    "source": "mcp",
                    "server": server_name,
                    "inputSchema": t.get("inputSchema", {}),
                })

        return result

    def list_mcp_tools(self, server_name: str = None) -> List[dict]:
        """列出 MCP 工具（可选按服务器过滤）"""
        result = []
        for sname, tools in self._tool_cache.items():
            if server_name and sname != server_name:
                continue
            for t in tools:
                tool_name = t.get("name", "?")
                mcp_name = f"MCP:{sname}:{tool_name}"
                result.append({
                    "name": mcp_name,
                    "description": t.get("description", ""),
                    "server": sname,
                    "inputSchema": t.get("inputSchema", {}),
                })
        return result

    def list_servers(self) -> List[dict]:
        """列出所有 MCP 服务器状态"""
        result = []
        for name, cfg in self._servers.items():
            transport = self._transports.get(name)
            result.append({
                "name": name,
                "command": cfg.command,
                "args": cfg.args,
                "description": cfg.description,
                "connected": transport.is_connected if transport else False,
                "tool_count": len(self._tool_cache.get(name, [])),
            })
        return result

    def execute(self, tool_name: str, arguments: dict = None) -> dict:
        """
        执行工具调用

        路由逻辑:
            - 以 "MCP:" 开头 → 走 MCP 通道
            - 其他 → 走本地 ToolFactory
        """
        if tool_name.startswith("MCP:"):
            return self._execute_mcp(tool_name, arguments)
        else:
            from tools import ToolFactory
            return ToolFactory.execute(tool_name, **(arguments or {}))

    def _execute_mcp(self, tool_name: str, arguments: dict = None) -> dict:
        """执行 MCP 工具调用"""
        # 解析 "MCP:server_name:tool_name" 格式
        parts = tool_name.split(":", 2)
        if len(parts) != 3:
            return {"success": False, "error": f"无效 MCP 工具名: {tool_name}"}

        _, server_name, mcp_tool_name = parts

        transport = self._transports.get(server_name)
        if not transport or not transport.is_connected:
            # 尝试重新连接
            cfg = self._servers.get(server_name)
            if cfg:
                self._connect_server(server_name, cfg)
                transport = self._transports.get(server_name)

            if not transport or not transport.is_connected:
                return {"success": False, "error": f"MCP 服务器 {server_name} 未连接"}

        try:
            result = transport.call_tool(mcp_tool_name, arguments)
            if result is None:
                return {"success": False, "error": f"MCP 工具调用失败: {tool_name}"}

            # MCP 返回 content 数组
            content = result.get("content", [])
            is_error = result.get("isError", False)

            # 提取文本内容
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_parts.append(item.get("text", str(item)))
                else:
                    text_parts.append(str(item))

            return {
                "success": not is_error,
                "content": "\n".join(text_parts),
                "error": "\n".join(text_parts) if is_error else None,
            }
        except Exception as e:
            return {"success": False, "error": f"MCP 调用异常: {e}"}

    def add_server(self, name: str, config: dict) -> dict:
        """动态添加 MCP 服务器"""
        if name in self._servers:
            return {"success": False, "error": f"服务器 {name} 已存在"}

        cfg = MCPServerConfig(name, config)
        if not cfg.command:
            return {"success": False, "error": "缺少 command 参数"}

        self._servers[name] = cfg
        self._connect_server(name, cfg)

        transport = self._transports.get(name)
        if transport and transport.is_connected:
            return {"success": True, "message": f"MCP 服务器 {name} 已添加并连接"}
        else:
            return {"success": False, "error": f"MCP 服务器 {name} 连接失败"}

    def remove_server(self, name: str) -> dict:
        """动态移除 MCP 服务器"""
        if name not in self._servers:
            return {"success": False, "error": f"服务器 {name} 不存在"}

        # 断开连接
        transport = self._transports.pop(name, None)
        if transport:
            transport.disconnect()

        self._servers.pop(name, None)
        self._tool_cache.pop(name, None)

        return {"success": True, "message": f"MCP 服务器 {name} 已移除"}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def server_count(self) -> int:
        return len(self._servers)

    @property
    def connected_count(self) -> int:
        return sum(1 for t in self._transports.values() if t.is_connected)
