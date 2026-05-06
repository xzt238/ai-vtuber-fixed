#!/usr/bin/env python3
"""
=====================================
工具系统 - 统一管理 (参考 Claude Code)
=====================================

【模块功能概述】
本模块实现了 AI VTuber 系统的"工具系统"——让 AI 能够执行各种操作，
类似于 Claude Code / GitHub Copilot 的工具调用机制。
AI 可以通过自然语言意图调用这些工具，实现文件读写、命令执行、代码搜索等功能。

【架构设计】
采用"基类 + 具体实现 + 工厂模式"的经典架构：

1. Tool (抽象基类)
   - 定义 name（工具名）、description（描述）、execute()（执行）的统一接口
   - 提供 is_read_only() 和 is_available() 查询接口

2. 具体工具类（9 种）
   - 文件操作：ReadTool、WriteTool、EditTool
   - 搜索工具：GlobTool（文件名搜索）、GrepTool（文本内容搜索）、LSTool（目录列表）
   - 执行工具：BashTool（Shell 命令执行）
   - 智能工具：ThinkTool（深度思考）、ArchitectTool（架构分析）

3. ToolFactory (工厂类)
   - 工具名称 → 工具类的映射注册表
   - 统一的 create/list/execute 接口

4. 便捷函数（模块级）
   - read/write/edit/glob/grep/ls/bash/think/architect
   - 每个函数是对 ToolFactory.execute() 的一层薄封装

【安全设计】
- 所有文件操作工具都使用 Path.resolve() 防止路径遍历攻击
- BashTool 使用 shell=False + shlex.split() 防止命令注入
- ReadTool 标记为 is_read_only()，可在只读模式下使用
- 所有操作都有完善的异常处理和错误信息返回

【与其他模块的关系】
- 被 llm/__init__.py 调用，AI 通过 function calling / tool use 触发
- 工具执行结果被注入到 LLM 对话上下文中
- web 面板可通过 ToolFactory.list_tools() 展示可用工具列表

【输入/输出】
- 输入：工具名称 + 参数字典（通过 execute() 或便捷函数传入）
- 输出：结果字典 {"success": bool, ...}，成功时包含具体数据，失败时包含 error 信息

14种工具: bash/read/write/edit/glob/grep/ls/think/architect/notebook等

作者: 咕咕嘎嘎
日期: 2026-04-02
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess
import shlex
import glob as glob_module
import re
import os
import sys


# v1.9.60: Windows 桌面模式隐藏 CMD 窗口的辅助函数
def _win_subprocess_kwargs():
    """桌面模式下 subprocess 调用添加 SW_HIDE + CREATE_NO_WINDOW"""
    if sys.platform != "win32" or os.getenv("GUGUGAGA_DESKTOP") != "1":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return {"startupinfo": si, "creationflags": subprocess.CREATE_NO_WINDOW}


# =====================================================================
# 工具基类
# =====================================================================

class Tool:
    """
    【抽象基类】工具基类

    定义所有工具的统一接口规范。每个具体工具必须继承此类，
    并实现 execute() 方法（核心执行逻辑）。

    【接口规范】
    - name (property): 工具名称，自动从类名生成（如 ReadTool → "read"）
    - description (property): 工具功能描述，用于展示给 AI 选择
    - execute(**kwargs): 执行工具操作，返回结果字典
    - is_available(): 检查工具是否可用（依赖是否安装等）
    - is_read_only(): 标记工具是否只读（用于权限控制）

    【结果字典格式】
        成功: {"success": True, "content": "...", "message": "..."}
        失败: {"success": False, "error": "错误信息"}
    """
    
    @property
    def name(self) -> str:
        """
        【属性】自动生成工具名称

        从类名中提取：去除 "Tool" 后缀，转小写。
        例如：ReadTool → "read"，EditTool → "edit"。

        【设计意图】
            避免在每个子类中重复定义 name 字段。
            子类只需遵循 "XxxTool" 的命名规范即可自动获得正确的工具名。
        """
        return self.__class__.__name__.lower().replace('Tool', '')
    
    @property
    def description(self) -> str:
        """
        【属性】工具功能描述（子类应重写此属性）

        用于在工具列表中展示，帮助 AI 或用户了解工具用途。
        """
        return "Tool description"
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        【核心方法】执行工具操作（子类必须重写）

        【参数说明】
            **kwargs: 工具参数，每个工具的参数不同

        【返回值】
            Dict[str, Any]: 包含 success 字段的结果字典
        """
        return {"success": False, "error": "Not implemented"}
    
    def is_available(self) -> bool:
        """检查工具是否可用（默认始终可用）"""
        return True
    
    def is_read_only(self) -> bool:
        """检查工具是否只读（默认非只读）"""
        return False


# =====================================================================
# 文件操作工具
# =====================================================================

class ReadTool(Tool):
    """
    【文件工具】读取文件内容

    以文本模式读取指定文件的前 N 行内容。
    支持路径解析和错误处理，防止路径遍历攻击。

    【参数】
        path (str): 文件路径（必需）
        limit (int): 最多读取的行数，默认 100

    【安全措施】
        - 使用 Path.resolve() 解析真实路径，防止 ../ 攻击
        - 异常处理覆盖 FileNotFoundError、PermissionError 等
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "读取文件内容"
    
    def execute(self, path: str, limit: int = 100) -> Dict[str, Any]:
        """
        【执行】读取文件内容

        【参数说明】
            path (str): 文件路径
            limit (int): 最大读取行数，防止读取超大文件

        【返回值】
            {"success": True, "content": "文件内容"} 或
            {"success": False, "error": "错误信息"}
        """
        try:
            # 输入验证：路径不能为空且必须是字符串
            if not path or not isinstance(path, str):
                return {"success": False, "error": "路径不能为空"}
            
            # 安全措施：解析真实路径，防止路径遍历攻击（如 ../../../etc/passwd）
            from pathlib import Path as PathLib
            try:
                resolved_path = PathLib(path).resolve()
            except (OSError, RuntimeError) as e:
                return {"success": False, "error": f"无效路径: {e}"}
            
            # 以 UTF-8 编码读取文件，限制行数
            with open(resolved_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:limit]
            return {"success": True, "content": ''.join(lines)}
        except FileNotFoundError:
            return {"success": False, "error": "文件不存在"}
        except PermissionError:
            return {"success": False, "error": "权限不足"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def is_read_only(self) -> bool:
        """
        【功能说明】检查工具是否为只读模式

        【返回值】
            bool: 返回 True，读取操作是只读的
        """
        return True  # 读取操作是只读的


class WriteTool(Tool):
    """
    【文件工具】写入文件内容

    将文本内容写入指定文件（覆盖模式）。

    【参数】
        path (str): 文件路径（必需）
        content (str): 要写入的内容（必需）

    【安全措施】
        - 路径遍历防护
        - 内容类型验证（必须是字符串）
        - 权限检查
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "写入文件内容"
    
    def execute(self, path: str, content: str) -> Dict[str, Any]:
        """
        【执行】写入文件

        【参数说明】
            path (str): 文件路径
            content (str): 写入内容

        【返回值】
            {"success": True, "message": "已写入 xxx"} 或
            {"success": False, "error": "错误信息"}
        """
        try:
            if not path or not isinstance(path, str):
                return {"success": False, "error": "路径不能为空"}
            
            if not isinstance(content, str):
                return {"success": False, "error": "内容必须是字符串"}
            
            # 路径遍历防护
            from pathlib import Path as PathLib
            try:
                resolved_path = PathLib(path).resolve()
            except (OSError, RuntimeError) as e:
                return {"success": False, "error": f"无效路径: {e}"}
            
            # 以 UTF-8 写入（覆盖模式）
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "message": f"已写入 {path}"}
        except PermissionError:
            return {"success": False, "error": "权限不足"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class EditTool(Tool):
    """
    【文件工具】精确编辑文件（查找替换）

    在文件中查找指定文本并将其替换为新文本。
    只替换第一次出现的匹配项，防止意外修改多处。

    【参数】
        path (str): 文件路径（必需）
        old_text (str): 要查找的旧文本（必需）
        new_text (str): 替换的新文本（必需）

    【安全措施】
        - old_text 为空时拒绝执行（防止清空文件）
        - 多处匹配时只替换第一处并发出警告
        - 路径遍历防护
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "精确编辑文件"
    
    def execute(self, path: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """
        【执行】查找并替换文件中的文本

        【参数说明】
            path (str): 文件路径
            old_text (str): 被替换的原始文本
            new_text (str): 替换后的新文本

        【返回值】
            {"success": True, "message": "已编辑 xxx"} 或
            {"success": False, "error": "错误信息"}

        【安全检查】
            1. 路径非空且为字符串
            2. old_text 非空（防止误操作清空内容）
            3. old_text 必须在文件中存在
            4. 多处匹配时只替换第一处
        """
        try:
            if not path or not isinstance(path, str):
                return {"success": False, "error": "路径不能为空"}
            
            if not old_text:
                return {"success": False, "error": "旧文本不能为空"}
            
            # 路径遍历防护
            from pathlib import Path as PathLib
            try:
                resolved_path = PathLib(path).resolve()
            except (OSError, RuntimeError) as e:
                return {"success": False, "error": f"无效路径: {e}"}
            
            # 读取文件全部内容
            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查旧文本是否存在
            if old_text not in content:
                return {"success": False, "error": "未找到要替换的文本"}
            
            # 检查匹配次数，多处匹配时发出警告
            count = content.count(old_text)
            if count > 1:
                print(f"⚠️ 警告: 找到 {count} 处匹配，只替换第一处")
            
            # 只替换第一次出现（count=1 限制替换次数）
            content = content.replace(old_text, new_text, 1)
            
            # 写回文件
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {"success": True, "message": f"已编辑 {path}"}
        except FileNotFoundError:
            return {"success": False, "error": "文件不存在"}
        except PermissionError:
            return {"success": False, "error": "权限不足"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# =====================================================================
# 搜索工具
# =====================================================================

class GlobTool(Tool):
    """
    【搜索工具】文件名搜索（Glob 模式匹配）

    使用 Unix 风格的通配符模式搜索文件名。
    支持递归搜索（** 通配符）。

    【参数】
        pattern (str): 搜索模式，默认 "*"（所有文件）
        path (str): 搜索根目录，默认 "."（当前目录）

    【示例】
        pattern="*.py", path="." → 搜索所有 Python 文件
        pattern="*.txt", path="./docs" → 搜索 docs 目录下的文本文件
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "搜索文件名"
    
    def execute(self, pattern: str = "*", path: str = ".") -> Dict[str, Any]:
        """
        【执行】使用 Glob 模式搜索文件

        【返回值】
            {"success": True, "files": ["path1", "path2", ...]} — 最多返回 50 个结果
        """
        try:
            files = glob_module.glob(f"{path}/**/{pattern}", recursive=True)
            return {"success": True, "files": files[:50]}  # 限制结果数量，防止过多
        except Exception as e:
            return {"success": False, "error": str(e)}


class GrepTool(Tool):
    """
    【搜索工具】文本内容搜索（Grep 风格）

    在指定目录的 Python 文件中搜索包含指定文本的行。
    使用系统 grep 命令实现（仅限 Unix/macOS，Windows 需 WSL 或 Git Bash）。

    【参数】
        pattern (str): 搜索的文本模式（必需）
        path (str): 搜索根目录，默认 "."

    【限制】
        - 仅搜索 *.py 文件
        - 最多返回 20 行匹配结果
        - 10 秒超时
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "搜索文本内容"
    
    def execute(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        """
        【执行】使用 grep 搜索文本内容

        【返回值】
            {"success": True, "matches": ["匹配行1", "匹配行2", ...]}
        """
        try:
            # 调用系统 grep 命令（-r 递归，--include 限定文件类型）
            result = subprocess.run(
                ['grep', '-r', pattern, path, '--include=*.py'],
                capture_output=True,
                text=True,
                timeout=10,  # 10秒超时，防止搜索大量文件时卡住
                **_win_subprocess_kwargs(),
            )
            # 按换行分割，最多返回 20 行
            lines = result.stdout.split('\n')[:20]
            return {"success": True, "matches": [l for l in lines if l]}
        except Exception as e:
            return {"success": False, "error": str(e)}


class LSTool(Tool):
    """
    【搜索工具】列出目录内容

    列出指定目录下的文件和子目录，类似 Unix ls 命令。

    【参数】
        path (str): 目录路径，默认 "."（当前目录）

    【输出格式】
        每行一个条目，格式为 "d dirname"（目录）或 "- filename"（文件）。
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "列出目录内容"
    
    def execute(self, path: str = ".") -> Dict[str, Any]:
        """
        【执行】列出目录内容

        【返回值】
            {"success": True, "items": ["d dirname", "- filename", ...]}
            最多返回 50 个条目
        """
        try:
            p = Path(path)
            items = []
            for item in p.iterdir():
                # 用 "d" 标记目录，"-" 标记文件
                items.append(f"{'d' if item.is_dir() else '-'} {item.name}")
            return {"success": True, "items": items[:50]}
        except Exception as e:
            return {"success": False, "error": str(e)}


# =====================================================================
# 执行工具
# =====================================================================

class BashTool(Tool):
    """
    【执行工具】Shell 命令执行

    在系统 shell 中执行命令并返回结果。
    使用 shlex.split() 安全拆分命令参数，避免 shell=True 的命令注入风险。

    【参数】
        command (str): 要执行的命令（必需）
        timeout (int): 超时时间（秒），默认 30

    【安全措施】
        - shell=False: 不使用 shell 解释器，直接执行命令
        - shlex.split(): 安全拆分命令参数（处理引号和转义）
        - 超时保护：防止命令长时间运行
        - 输出捕获：stdout 和 stderr 分别捕获

    【返回值】
        包含 returncode、stdout、stderr 的完整结果字典
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "执行 shell 命令"
    
    def execute(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        【执行】安全地执行 Shell 命令

        【参数说明】
            command (str): Shell 命令字符串（如 "ls -la"）
            timeout (int): 超时秒数

        【返回值】
            {"success": bool, "stdout": "...", "stderr": "...", "returncode": int}
        """
        import shlex
        try:
            # 使用 shlex.split() 安全拆分命令
            # 例如 "echo 'hello world'" → ["echo", "hello world"]
            # 避免 shell=True 的命令注入风险
            cmd_parts = shlex.split(command) if command else []
            result = subprocess.run(
                cmd_parts,
                shell=False,          # 不使用 shell，直接执行
                capture_output=True,  # 捕获 stdout 和 stderr
                text=True,            # 以文本模式返回（而非字节）
                timeout=timeout,      # 超时保护
                **_win_subprocess_kwargs(),
            )
            return {
                "success": result.returncode == 0,  # 退出码 0 表示成功
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "命令超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# =====================================================================
# 智能工具（轻量级，无外部依赖）
# =====================================================================

class ThinkTool(Tool):
    """
    【智能工具】深度思考

    让 AI 展示其思考过程。这是一个"透传"工具——
    它不做任何实际计算，只是将 AI 的思考内容原样返回。
    用于让 AI 在执行复杂任务前先整理思路。

    【参数】
        thought (str): 思考内容（必需）

    【设计意图】
        参考 Claude Code 的 Think 工具。
        实际效果取决于 AI 是否被指示使用此工具。
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "进行深度思考"
    
    def execute(self, thought: str) -> Dict[str, Any]:
        """将思考内容原样返回"""
        return {"success": True, "thought": thought}


class ArchitectTool(Tool):
    """
    【智能工具】代码架构分析

    分析指定目录下的代码架构，检测使用的编程语言和框架。
    简化版实现，仅通过文件扩展名判断语言类型。

    【参数】
        path (str): 项目目录路径，默认 "."（当前目录）

    【返回值】
        {"success": True, "languages": ["Python", "JavaScript", ...]}

    【改进方向】
        可扩展为检测框架（Django/Flask/FastAPI）、包管理器、目录结构等。
    """
    
    @property
    def description(self) -> str:
        """
        【属性】获取工具描述

        【返回值】
            str: 工具功能描述
        """
        return "分析代码架构"
    
    def execute(self, path: str = ".") -> Dict[str, Any]:
        """
        【执行】分析目录下的编程语言分布

        通过递归扫描文件扩展名来判断使用了哪些编程语言。
        """
        # 简化版：仅通过扩展名判断语言
        p = Path(path)
        langs = set()
        for f in p.rglob("*"):
            if f.suffix == '.py':
                langs.add('Python')
            elif f.suffix == '.js':
                langs.add('JavaScript')
        
        return {"success": True, "languages": list(langs)}


# =====================================================================
# 工具工厂
# =====================================================================

class ToolFactory:
    """
    【工厂类】工具工厂 —— 统一的工具注册表和创建入口

    维护一个工具名称 → 工具类的映射表，提供统一的创建、列表和执行接口。
    所有工具通过 _tools 类变量注册，新增工具只需在此字典中添加一行。

    【注册表格式】
        _tools = {
            "工具名": 工具类,
            ...
        }

    【使用方式】
        # 创建工具实例
        tool = ToolFactory.create("read")
        result = tool.execute(path="file.txt")

        # 直接执行
        result = ToolFactory.execute("bash", command="ls")

        # 列出所有工具
        tools = ToolFactory.list_tools()
    """
    
    # 工具注册表 —— 名称到工具类的映射
    _tools = {
        "bash": BashTool,           # Shell 命令执行
        "read": ReadTool,           # 读取文件
        "write": WriteTool,         # 写入文件
        "edit": EditTool,           # 编辑文件（查找替换）
        "glob": GlobTool,           # 文件名搜索
        "grep": GrepTool,           # 文本内容搜索
        "ls": LSTool,               # 列出目录
        "think": ThinkTool,         # 深度思考
        "architect": ArchitectTool, # 架构分析
    }
    
    @classmethod
    def create(cls, tool_name: str) -> Optional[Tool]:
        """
        【类方法】根据名称创建工具实例

        【参数说明】
            tool_name (str): 工具名称（如 "read"、"bash"）

        【返回值】
            Optional[Tool]: 工具实例；名称不存在时返回 None
        """
        tool_class = cls._tools.get(tool_name)
        return tool_class() if tool_class else None
    
    @classmethod
    def list_tools(cls) -> List[Dict[str, str]]:
        """
        【类方法】列出所有已注册的工具

        【返回值】
            List[Dict[str, str]]: [{"name": "read", "description": "读取文件内容"}, ...]
        """
        return [
            {"name": name, "description": tool_class().description}
            for name, tool_class in cls._tools.items()
        ]
    
    @classmethod
    def execute(cls, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        【类方法】一步到位：创建工具 + 执行 + 返回结果

        【参数说明】
            tool_name (str): 工具名称
            **kwargs: 传递给工具 execute() 的参数

        【返回值】
            Dict[str, Any]: 工具执行结果

        【设计意图】
            简化调用链：无需先 create 再 execute，一行代码完成。
        """
        tool = cls.create(tool_name)
        if tool:
            return tool.execute(**kwargs)
        return {"success": False, "error": f"Tool {tool_name} not found"}


# =====================================================================
# 模块测试
# =====================================================================

if __name__ == "__main__":
    # 列出所有可用工具
    print("可用工具:")
    for tool in ToolFactory.list_tools():
        print(f"  - {tool['name']}: {tool['description']}")
