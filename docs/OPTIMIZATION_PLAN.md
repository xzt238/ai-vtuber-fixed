# AI VTuber 优化计划

## 🎯 优化目标
提升代码质量、安全性、性能和可维护性

## 📋 优化清单

### 🔴 P0 - 立即修复（安全/稳定性）

#### 1. 资源泄漏修复
**问题**: ToolExecutor 和 SubAgent 的资源可能未正确释放
**影响**: 长时间运行可能导致内存泄漏、线程泄漏
**方案**:
```python
# main.py - AIVTuber 类添加上下文管理器
def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self.stop()
    return False

# 确保 stop() 方法完整清理所有资源
def stop(self):
    # 1. 停止 Web 服务
    # 2. 关闭线程池
    # 3. 关闭 HTTP Session
    # 4. 清理临时文件
```

#### 2. 异常处理改进
**问题**: 过于宽泛的 `except Exception` 可能隐藏真实错误
**方案**:
```python
# 具体化异常类型
try:
    ...
except FileNotFoundError as e:
    logger.error(f"文件不存在: {e}")
except PermissionError as e:
    logger.error(f"权限不足: {e}")
except subprocess.TimeoutExpired as e:
    logger.error(f"命令超时: {e}")
except Exception as e:
    logger.exception(f"未预期错误: {e}")
    raise  # 重新抛出，避免吞掉错误
```

#### 3. 历史记录管理优化
**问题**: `process_message()` 逻辑混乱，有注释代码
**方案**:
```python
def process_message(self, text: str) -> Dict[str, Any]:
    # 1. 清理注释代码
    # 2. 统一历史记录添加逻辑
    # 3. 修复 MAX_HISTORY 限制逻辑
    
    # 正确的限制方式
    if len(self.history) > self.MAX_HISTORY * 2:
        # 保留最近的对话，删除旧的
        self.history = self.history[-(self.MAX_HISTORY * 2):]
```

### 🟡 P1 - 重要优化（代码质量）

#### 4. 消除代码重复
**问题**: 路径验证、sys.path 操作重复
**方案**:
```python
# 创建 utils.py 统一工具函数
def validate_path(path: str, base_dir: str = None) -> Path:
    """统一的路径验证"""
    from pathlib import Path
    resolved = Path(path).resolve()
    base = Path(base_dir or Path.cwd()).resolve()
    if not str(resolved).startswith(str(base)):
        raise ValueError("路径超出允许范围")
    return resolved

def setup_python_path():
    """统一的 Python 路径设置"""
    import sys
    from pathlib import Path
    app_dir = Path(__file__).parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
```

#### 5. 统一配置管理
**方案**:
```python
# config.py - 统一配置加载
class ConfigManager:
    def __init__(self):
        self.config = self._load_config()
        self.env = self._load_env()
    
    def get(self, key: str, default=None):
        # 优先级: 环境变量 > 配置文件 > 默认值
        env_key = key.upper().replace('.', '_')
        return os.getenv(env_key) or self._get_nested(key) or default
```

#### 6. 日志系统改进
**方案**:
```python
# logger.py - 统一日志配置
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, level: str = "INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 文件处理器（自动轮转）
    file_handler = RotatingFileHandler(
        f"logs/{name}.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

### 🟢 P2 - 性能优化

#### 7. TTS 缓存机制
**方案**:
```python
# tts/__init__.py - 添加缓存
import hashlib
from pathlib import Path

class TTSCache:
    def __init__(self, cache_dir: str = "cache/tts"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_key(self, text: str, voice: str) -> str:
        return hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    
    def get(self, text: str, voice: str) -> Optional[str]:
        key = self.get_cache_key(text, voice)
        cache_file = self.cache_dir / f"{key}.wav"
        return str(cache_file) if cache_file.exists() else None
    
    def set(self, text: str, voice: str, audio_path: str):
        key = self.get_cache_key(text, voice)
        cache_file = self.cache_dir / f"{key}.wav"
        shutil.copy(audio_path, cache_file)
```

#### 8. 记忆系统优化
**方案**:
```python
# memory/__init__.py - 使用向量数据库
# 可选方案:
# 1. ChromaDB (轻量级，适合本地)
# 2. FAISS (高性能)
# 3. Qdrant (功能完整)

from chromadb import Client
from chromadb.config import Settings

class MemorySystem:
    def __init__(self, config: Dict):
        self.client = Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="memory/chroma"
        ))
        self.collection = self.client.get_or_create_collection("memories")
    
    def search(self, query: str, top_k: int = 3):
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        return results
```

#### 9. 异步处理优化
**方案**:
```python
# 使用 asyncio 处理 I/O 密集型操作
import asyncio

class AIVTuber:
    async def process_message_async(self, text: str):
        # 并发执行多个任务
        tasks = [
            self.memory.search_async(text),
            self.llm.chat_async(text),
        ]
        results = await asyncio.gather(*tasks)
        return results
```

### 📝 P3 - 用户体验优化

#### 10. Web 界面改进
- 添加加载动画
- 优化错误提示
- 添加快捷键支持
- 响应式布局优化

#### 11. 错误信息友好化
```python
# 用户友好的错误信息
ERROR_MESSAGES = {
    "FileNotFoundError": "找不到文件喵~ 请检查路径是否正确",
    "PermissionError": "没有权限访问这个文件喵~",
    "TimeoutError": "操作超时了喵~ 请稍后再试",
}
```

## 🚀 实施计划

### 第一阶段（本周）- P0 问题
- [ ] 修复资源泄漏
- [ ] 改进异常处理
- [ ] 优化历史记录管理

### 第二阶段（下周）- P1 问题
- [ ] 消除代码重复
- [ ] 统一配置管理
- [ ] 改进日志系统

### 第三阶段（后续）- P2/P3 优化
- [ ] TTS 缓存
- [ ] 记忆系统优化
- [ ] Web 界面改进

## 📊 预期效果

- **稳定性**: 消除资源泄漏，减少崩溃
- **性能**: TTS 缓存提升 50%+ 响应速度
- **可维护性**: 代码重复减少 30%+
- **用户体验**: 错误提示更友好，界面更流畅

---

咕咕嘎嘎 - 2026-04-06
