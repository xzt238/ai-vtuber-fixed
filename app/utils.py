#!/usr/bin/env python3
"""
=====================================
工具函数模块 - 统一常用功能
=====================================

本模块是整个 AI VTuber 项目的公共工具层，旨在将分散在各处的通用逻辑集中管理，
避免代码重复，降低维护成本。

功能:
- 路径验证：防止路径遍历攻击，确保文件操作在合法目录范围内
- Python 路径设置：动态将调用者所在目录加入 sys.path，解决模块导入问题
- 错误信息友好化：将技术性的异常信息转换为面向用户的友好提示
- 临时文件管理：通过上下文管理器确保临时资源被可靠释放

设计决策:
- 所有路径操作统一使用 pathlib.Path，兼顾跨平台兼容性
- 临时文件管理采用 delete=False + finally 清理模式，
  这是因为 Windows 平台对已打开的临时文件有独占锁限制，
  必须先关闭文件句柄再删除

作者: 咕咕嘎嘎
日期: 2026-04-06
"""

# ==================== 标准库导入 ====================
import os                           # 操作系统接口：环境变量、文件大小、路径操作
import sys                          # 系统相关：sys.path 动态修改、解释器信息
import tempfile                     # 临时文件/目录的创建与管理
import shutil                       # 高级文件操作：递归删除目录等
from pathlib import Path            # 面向对象的路径处理，跨平台兼容（Windows/Linux/macOS）
from typing import Optional, Union  # 类型注解：Optional 表示可选，Union 表示多类型
from contextlib import contextmanager  # 装饰器：将普通函数变为上下文管理器（支持 with 语法）


# ============================================
# 路径相关
# ============================================

def validate_path(path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None) -> Path:
    """
    统一的路径验证 —— 安全边界检查

    本函数的核心目的是防止"路径遍历攻击"（Path Traversal）。
    攻击者可能通过传入 "../../etc/passwd" 这样的路径来访问系统敏感文件。
    通过验证解析后的路径必须在基准目录之下，可以有效阻断此类攻击。

    设计决策:
    - 使用 Path.resolve() 将所有符号链接、相对路径成分（..、.）都解析为绝对路径，
      确保比较是在"真实路径"层面进行的，不会因为符号链接绕过检查
    - 默认以当前工作目录为基准，但允许调用者指定更严格的约束范围

    Args:
        path: 要验证的路径，可以是字符串或 Path 对象
        base_dir: 基准目录（默认为当前工作目录），验证结果必须在此目录之下

    Returns:
        Path: 验证后的绝对路径对象（已解析所有符号链接和相对成分）

    Raises:
        ValueError: 路径不合法（包含无法解析的成分）或解析后的路径超出允许范围
    """
    try:
        # 将输入路径解析为绝对路径，消除所有 .. 和符号链接
        # 例如 "a/b/../c" 会解析为 "/真实路径/a/c"
        resolved = Path(path).resolve()

        # 确定基准目录：优先使用调用者传入的 base_dir，否则使用当前工作目录
        base = Path(base_dir or Path.cwd()).resolve()

        # ===== 安全边界检查 =====
        # 通过字符串前缀匹配判断 resolved 是否在 base 目录内
        # 这是路径遍历防护的核心逻辑：
        # 如果攻击者传入 "/etc/passwd"，而 base 是 "/app/data"，
        # 则 str(resolved) = "/etc/passwd" 不会以 "/app/data" 开头，检查失败
        if not str(resolved).startswith(str(base)):
            raise ValueError(f"路径超出允许范围: {path}")

        # 所有检查通过，返回安全可用的绝对路径
        return resolved
    except (OSError, RuntimeError) as e:
        # 捕获路径解析过程中可能出现的系统错误（如权限不足、路径不存在等）
        # 统一包装为 ValueError，让上层只需处理一种异常类型
        raise ValueError(f"无效路径: {e}")


def setup_python_path(app_dir: Optional[Union[str, Path]] = None):
    """
    统一的 Python 路径设置 —— 动态模块导入支持

    当项目以不同方式启动时（python main.py、python -m package、IDE 运行等），
    sys.path 中的目录可能不同，导致"明明文件存在却 ImportError"的问题。
    本函数通过将指定目录插入 sys.path 最前面，确保模块导入路径的一致性。

    设计决策:
    - 默认通过调用栈帧（inspect）自动获取调用者所在目录，
      这样调用者无需手动传入自身路径，减少出错可能
    - 使用 insert(0, ...) 插入到列表最前面，优先级最高，
      确保项目内的模块优先于系统安装的同名模块被导入
    - 插入前先检查是否已存在，避免重复添加导致 sys.path 无限增长

    Args:
        app_dir: 应用目录（默认自动获取调用者的文件所在目录）
                 如果无法获取（如交互式环境），则回退到当前工作目录
    """
    if app_dir is None:
        # ===== 自动检测调用者目录 =====
        # 通过 Python 的 inspect 模块获取调用栈信息
        # 这样设计是为了让调用者可以直接 setup_python_path() 而不用传参
        import inspect  # 延迟导入：inspect 不是所有场景都需要，放在这里减少不必要的导入开销
        frame = inspect.currentframe()          # 获取当前（本函数）的栈帧
        caller_frame = frame.f_back             # 回溯到调用者的栈帧
        caller_file = caller_frame.f_globals.get('__file__')  # 从调用者的全局变量中获取文件路径

        if caller_file:
            # 如果能获取到调用者的文件路径，取其所在目录作为 app_dir
            # 例如调用者在 /app/main.py，则 app_dir = /app/
            app_dir = Path(caller_file).parent
        else:
            # 回退方案：无法获取文件路径（如在 REPL 或 Jupyter 中运行时）
            # 使用当前工作目录作为最后手段
            app_dir = Path.cwd()

    # 将路径统一解析为绝对路径，消除歧义
    app_dir = Path(app_dir).resolve()
    app_dir_str = str(app_dir)

    # 检查是否已在 sys.path 中，避免重复插入
    # 设计原因：每次调用都插入会导致 sys.path 越来越长，影响导入搜索性能
    if app_dir_str not in sys.path:
        sys.path.insert(0, app_dir_str)  # 插入到最前面，优先级最高


# ============================================
# 临时文件管理
# ============================================

@contextmanager
def temp_file(suffix: str = "", prefix: str = "tmp", dir: Optional[str] = None, delete: bool = True):
    """
    临时文件上下文管理器（确保清理）

    功能说明：
        创建一个临时文件，在 with 块内可以通过 yield 的路径读写该文件。
        无论 with 块内是否发生异常，退出时都会自动删除临时文件（delete=True 时）。

    设计决策：
        使用 delete=False 创建临时文件，然后在 finally 中手动删除。
        这是因为 Windows 平台对已打开的临时文件有独占锁限制 ——
        如果使用 delete=True（默认行为），tempfile 会在关闭时立即删除，
        但在其他程序（或同一程序的其他线程）仍持有该文件引用时可能导致错误。
        先创建再手动删除的模式更可靠。

    Args:
        suffix: 文件后缀名，如 ".txt"、".wav"。影响临时文件的扩展名。
        prefix: 文件名前缀，默认为 "tmp"。用于在临时目录中识别文件来源。
        dir: 临时文件存放的目录。默认由操作系统决定（通常是 /tmp 或 %TEMP%）。
        delete: 是否在退出上下文时自动删除文件。默认为 True。

    Yields:
        str: 临时文件的绝对路径字符串，调用方可以用此路径进行文件读写。

    使用示例：
        with temp_file(suffix=".wav") as tmp_path:
            # 在这里可以读写 tmp_path
            with open(tmp_path, 'wb') as f:
                f.write(audio_data)
            # 退出 with 块后，tmp_path 指向的文件会被自动删除
    """
    temp_path = None
    try:
        # 使用 delete=False 创建临时文件：.NamedTemporaryFile 会创建文件但不删除它
        # 这样我们可以在 with 块内向文件写入数据，并安全地获取其路径
        with tempfile.NamedTemporaryFile(suffix=suffix, prefix=prefix, dir=dir, delete=False) as f:
            temp_path = f.name  # 保存临时文件的绝对路径
        yield temp_path  # 将路径交给调用方使用
    finally:
        # 无论 with 块内是否发生异常，都会执行清理
        if delete and temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)  # 删除临时文件
            except OSError as e:
                # 删除失败不应影响主流程（如文件被其他进程占用）
                print(f"️ 清理临时文件失败: {e}")


@contextmanager
def temp_dir(suffix: str = "", prefix: str = "tmp", dir: Optional[str] = None, delete: bool = True):
    """
    临时目录上下文管理器（确保清理）

    功能说明：
        创建一个临时目录，在 with 块内可以通过 yield 的路径在该目录下创建文件。
        退出时自动递归删除整个临时目录及其所有内容。

    设计决策：
        与 temp_file 类似，采用"创建 -> 使用 -> 清理"的三段式生命周期。
        使用 shutil.rmtree() 进行递归删除，确保目录下的所有文件和子目录都被清除。

    Args:
        suffix: 目录名后缀
        prefix: 目录名前缀，默认为 "tmp"
        dir: 父目录，临时目录将在此目录下创建
        delete: 是否在退出上下文时自动删除目录。默认为 True。

    Yields:
        str: 临时目录的绝对路径字符串。

    使用示例：
        with temp_dir(prefix="gugugaga_") as tmp_dir:
            # 在临时目录下创建文件
            output_path = os.path.join(tmp_dir, "output.wav")
            # 退出后整个 tmp_dir 及其内容都会被删除
    """
    temp_path = None
    try:
        temp_path = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)  # 创建临时目录
        yield temp_path  # 将目录路径交给调用方使用
    finally:
        if delete and temp_path and os.path.exists(temp_path):
            try:
                shutil.rmtree(temp_path)  # 递归删除整个目录及其内容
            except OSError as e:
                print(f"️ 清理临时目录失败: {e}")


# ============================================
# 错误信息友好化
# ============================================

# 异常类型到用户友好提示的映射表
# 设计意图：将技术性的异常类型名称（如 FileNotFoundError）转换为面向普通用户的
# 可理解提示语，让 AI VTuber 在对话中以更友好的方式报告错误。
ERROR_MESSAGES = {
    "FileNotFoundError": "找不到文件喵~ 请检查路径是否正确",      # 文件不存在
    "PermissionError": "没有权限访问这个文件喵~",              # 权限不足
    "TimeoutError": "操作超时了喵~ 请稍后再试",                # 请求超时
    "ConnectionError": "网络连接失败喵~ 请检查网络",            # 网络连接问题
    "ValueError": "参数不正确喵~ 请检查输入",                  # 参数错误
    "KeyError": "找不到指定的键喵~",                          # 字典键不存在
    "ImportError": "缺少必要的依赖喵~ 请安装相关包",           # 模块导入失败
    "OSError": "系统操作失败喵~",                             # 通用操作系统错误
}


def friendly_error(exception: Exception) -> str:
    """
    将异常转换为用户友好的错误信息

    功能说明：
        接收一个异常对象，根据其类型在 ERROR_MESSAGES 映射表中查找对应的友好提示。
        如果映射表中没有匹配项，则使用默认提示"出错了喵~"。
        如果异常包含原始错误消息，会附加在友好提示后面，方便调试。

    Args:
        exception: Python 异常对象（如 FileNotFoundError、ValueError 等）

    Returns:
        str: 友好的错误信息字符串。
             格式为 "{友好提示}\n详细信息: {原始错误消息}" 或仅 "{友好提示}"。

    使用示例：
        try:
            open("不存在的文件.txt")
        except Exception as e:
            msg = friendly_error(e)
            # msg = "找不到文件喵~ 请检查路径是否正确\n详细信息: [Errno 2] No such file..."
    """
    # 获取异常的类型名称（如 "FileNotFoundError"、"ValueError" 等）
    error_type = type(exception).__name__

    # 在映射表中查找对应的友好提示，未找到则使用默认值
    friendly_msg = ERROR_MESSAGES.get(error_type, "出错了喵~")

    # 如果异常携带了原始错误消息（非空字符串），则附加详细信息
    if str(exception):
        return f"{friendly_msg}\n详细信息: {exception}"
    return friendly_msg


# ============================================
# 文件大小检查
# ============================================

def check_file_size(path: Union[str, Path], max_size_mb: int = 10) -> bool:
    """
    检查文件大小是否在限制范围内

    功能说明：
        获取指定路径的文件大小，与传入的最大限制值进行比较。
        可用于在上传、处理文件前进行预检，防止处理超大文件导致内存溢出。

    Args:
        path: 文件路径，支持字符串或 Path 对象
        max_size_mb: 最大允许的文件大小，单位为兆字节(MB)，默认为 10MB

    Returns:
        bool: True 表示文件大小在限制范围内（<= max_size_mb），
              False 表示超出限制或文件无法访问。
    """
    try:
        size = os.path.getsize(path)  # 获取文件字节数
        max_bytes = max_size_mb * 1024 * 1024  # MB 转换为字节
        return size <= max_bytes
    except OSError:
        # 文件不存在或无权限访问时返回 False
        return False


def format_file_size(size_bytes: int) -> str:
    """
    将字节数格式化为人类可读的文件大小字符串

    功能说明：
        自动选择最合适的单位（B/KB/MB/GB/TB），使数字保持在易读范围内。

    Args:
        size_bytes: 文件大小，单位为字节

    Returns:
        str: 格式化后的字符串，如 "1.5 MB"、"256.0 KB"、"1024.0 B"

    使用示例：
        >>> format_file_size(1536)
        "1.5 KB"
        >>> format_file_size(1048576)
        "1.0 MB"
    """
    # 从最小单位 B 开始，每次除以 1024 直到数值小于 1024
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"  # 超过 TB 级别的罕见情况


# ============================================
# 安全的字符串操作
# ============================================

def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    生成安全的文件名（移除特殊字符）

    功能说明：
        对原始文件名进行清洗，移除所有非安全字符（仅保留字母、数字、下划线、空格、点、连字符），
        并限制最大长度。防止通过文件名注入特殊字符或路径分隔符。

    设计决策：
        - 使用正则表达式 [^\w\s.-] 匹配所有非安全字符并移除
        - 长度限制时保留文件扩展名（通过 os.path.splitext 分离），只截断文件名部分
        - 默认最大长度 255 是大多数文件系统（NTFS、ext4、APFS）的文件名长度上限

    Args:
        filename: 原始文件名，可能包含特殊字符
        max_length: 最大允许长度，默认 255（文件系统上限）

    Returns:
        str: 清洗后的安全文件名

    使用示例：
        >>> safe_filename('我的文件<>.txt')
        "我的文件.txt"
    """
    import re
    # 正则表达式 [^\w\s.-] 匹配所有"非"以下字符的内容：\w（字母数字下划线）、\s（空白）、.（点）、-（连字符）
    safe = re.sub(r'[^\w\s.-]', '', filename)
    # 如果清洗后的文件名超过最大长度，保留扩展名，只截断文件名部分
    if len(safe) > max_length:
        name, ext = os.path.splitext(safe)  # 分离文件名和扩展名
        safe = name[:max_length - len(ext)] + ext  # 截断文件名，保留扩展名
    return safe


# ============================================
# 配置加载辅助
# ============================================

def load_env_or_config(key: str, config: dict, default=None):
    """
    优先从环境变量加载，其次从配置字典

    功能说明：
        提供一个统一的配置读取接口，支持嵌套键（用点号分隔）。
        优先从环境变量获取值，其次从配置字典中逐层查找。

    设计决策：
        - 环境变量命名规则：将配置键转大写，点号替换为下划线。
          例如配置键 "llm.api_key" 对应环境变量 "LLM_API_KEY"
        - 配置字典支持嵌套：如 config = {"llm": {"api_key": "xxx"}}，
          传入 key="llm.api_key" 会逐层深入找到值

    Args:
        key: 配置键，支持点分隔的嵌套路径，如 "llm.api_key"、"tts.edge.voice"
        config: 配置字典（可能包含嵌套的字典结构）
        default: 当环境变量和配置字典中都没有该键时的兜底值

    Returns:
        配置值（类型取决于配置字典中的实际值），未找到则返回 default。

    使用示例：
        config = {"llm": {"api_key": "sk-xxx", "model": "gpt-4"}}
        load_env_or_config("llm.api_key", config, default="default-key")
        # -> "sk-xxx"（从配置字典中获取）

        load_env_or_config("llm.model", config, default="gpt-3.5")
        # -> "gpt-4"
    """
    # 尝试从环境变量获取
    # 转换规则："llm.api_key" -> "LLM_API_KEY"
    env_key = key.upper().replace('.', '_')
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value

    # 尝试从配置字典中逐层查找
    # 例如 key="llm.api_key" -> keys=["llm", "api_key"]
    # 先取 config["llm"]，再取 result["api_key"]
    keys = key.split('.')
    value = config
    for k in keys:
        if isinstance(value, dict):  # 确保当前层级是字典才能继续深入
            value = value.get(k)
        else:
            return default  # 中间某层不是字典（如值为 None、str 等），查找失败

    # 最终值可能为 None（键不存在），此时返回 default
    return value if value is not None else default


if __name__ == "__main__":
    # ===== 模块自测入口 =====
    # 直接运行此脚本时，执行基本的功能测试
    print(" 测试工具函数...")

    # 测试路径验证
    try:
        path = validate_path("test.txt")
        print(f" 路径验证: {path}")
    except ValueError as e:
        print(f" 路径验证: {e}")

    # 测试临时文件
    with temp_file(suffix=".txt") as tmp:
        print(f" 临时文件: {tmp}")
        with open(tmp, 'w') as f:
            f.write("test")

    # 测试错误信息
    try:
        raise FileNotFoundError("test.txt")
    except Exception as e:
        print(f" 友好错误: {friendly_error(e)}")

    print(" 测试完成")
