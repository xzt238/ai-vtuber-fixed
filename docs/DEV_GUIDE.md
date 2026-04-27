# 📋 咕咕嘎嘎 AI-VTuber 开发规范文档

## 📌 文档说明

本文档规定了项目的开发流程、代码规范、测试规范和发布流程，确保代码质量和团队协作效率。

**目标读者**: 开发者、维护者、AI 助手

**更新日期**: 2026-04-06

---

## 🔄 开发流程规范

### 1. 功能开发流程

```
1. 需求分析
   ↓
2. 设计方案 (必要时更新 ARCHITECTURE.md)
   ↓
3. 创建分支 (feature/xxx)
   ↓
4. 编写代码
   ↓
5. 编写测试
   ↓
6. 代码审查
   ↓
7. 合并主分支
   ↓
8. 更新 VERSION.md ⭐
   ↓
9. 发布版本
```

### 2. Bug 修复流程

```
1. 问题确认
   ↓
2. 创建分支 (fix/xxx)
   ↓
3. 修复代码
   ↓
4. 编写测试 (防止回归)
   ↓
5. 代码审查
   ↓
6. 合并主分支
   ↓
7. 更新 VERSION.md ⭐
   ↓
8. 发布补丁版本
```

### 3. 文档更新流程

```
1. 识别需要更新的文档
   ↓
2. 更新文档内容
   ↓
3. 更新 VERSION.md (标记为 📝 文档) ⭐
   ↓
4. 提交更改
```

---

## 📝 代码规范

### 1. Python 代码规范 (PEP 8)

#### 命名规范

```python
# ✅ 类名: PascalCase
class TTSEngine:
    pass

class OpenAudioEngine:
    pass

# ✅ 函数名: snake_case
def load_model():
    pass

def process_audio_data():
    pass

# ✅ 变量名: snake_case
user_input = "hello"
audio_file_path = "/path/to/audio.wav"

# ✅ 常量: UPPER_CASE
MAX_HISTORY = 100
DEFAULT_TIMEOUT = 30

# ✅ 私有方法/变量: _前缀
def _validate_path(path):
    pass

_internal_cache = {}
```

#### 文档字符串规范

```python
def speak(self, text: str, voice: str = "female") -> str:
    """合成语音
    
    将文本转换为语音文件。
    
    Args:
        text: 要合成的文本内容
        voice: 音色选择，可选 "female" 或 "male"
        
    Returns:
        生成的音频文件路径
        
    Raises:
        ValueError: 当 text 为空时
        RuntimeError: 当模型加载失败时
        
    Example:
        >>> engine = TTSEngine()
        >>> audio_path = engine.speak("你好", voice="female")
        >>> print(audio_path)
        /tmp/audio_12345.wav
    """
    if not text:
        raise ValueError("文本不能为空")
    
    # 实现代码...
    return audio_path
```

#### 类型提示规范

```python
from typing import Optional, List, Dict, Any, Tuple

# ✅ 函数参数和返回值类型提示
def process_message(
    message: str,
    history: List[Dict[str, str]],
    max_length: int = 100
) -> Tuple[str, List[Dict[str, str]]]:
    """处理消息"""
    # 实现代码...
    return response, updated_history

# ✅ 类属性类型提示
class Config:
    api_key: str
    base_url: str
    timeout: int = 30
    headers: Optional[Dict[str, str]] = None
```

#### 异常处理规范

```python
# ✅ 具体化异常类型
try:
    with open(file_path, "r") as f:
        data = f.read()
except FileNotFoundError:
    logger.error(f"文件不存在: {file_path}")
    raise
except PermissionError:
    logger.error(f"无权限读取文件: {file_path}")
    raise
except Exception as e:
    logger.error(f"读取文件失败: {e}")
    raise

# ❌ 避免捕获所有异常
try:
    do_something()
except:  # 不要这样做！
    pass
```

#### 资源管理规范

```python
# ✅ 使用上下文管理器
with open(file_path, "r") as f:
    data = f.read()

# ✅ 自定义上下文管理器
class AIVTuber:
    def __enter__(self):
        self._init_resources()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_resources()

# 使用
with AIVTuber() as ai:
    ai.process_message("hello")
```

### 2. YAML 配置规范

```yaml
# ✅ 使用注释说明配置项
# ==================== 语音合成 (TTS) ====================
tts:
  provider: "chattts"         # 主引擎: chattts/edge/openaudio
  
  chattts:
    model_path: "C:\\path"    # ChatTTS 模型路径
    voice: "female"           # 音色: female/male
    temperature: 0.3          # 温度 (0.1-1.0)

# ✅ 使用环境变量占位符
llm:
  minimax:
    api_key: "${MINIMAX_API_KEY}"  # 从环境变量读取

# ❌ 避免硬编码敏感信息
llm:
  minimax:
    api_key: "sk-1234567890"  # 不要这样做！
```

### 3. Git 提交规范

#### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### 类型 (type)

| 类型 | 说明 | 示例 |
|------|------|------|
| feat | 新功能 | `feat(tts): 添加 OpenAudio S1-mini 引擎` |
| fix | Bug 修复 | `fix(llm): 修复 API 调用超时问题` |
| docs | 文档更新 | `docs: 更新 ARCHITECTURE.md` |
| style | 代码格式 | `style: 格式化 main.py` |
| refactor | 重构 | `refactor(memory): 重构记忆系统` |
| perf | 性能优化 | `perf(tts): 添加音频缓存` |
| test | 测试 | `test(llm): 添加单元测试` |
| chore | 构建/工具 | `chore: 更新依赖版本` |

#### 提交示例

```bash
# 新功能
git commit -m "feat(tts): 添加 OpenAudio S1-mini 引擎

- 支持 13 种语言
- 本地部署，无需联网
- 自动设备选择 (CUDA/CPU)

Closes #123"

# Bug 修复
git commit -m "fix(llm): 修复 API 调用超时问题

- 增加重试机制
- 添加超时日志
- 优化错误处理

Fixes #456"

# 文档更新
git commit -m "docs: 更新 VERSION.md 到 v1.4.11

- 记录 OpenAudio 引擎新增
- 更新依赖安装说明"
```

---

## 🧪 测试规范

### 1. 单元测试

#### 测试文件结构

```
app/
├── tts/
│   ├── __init__.py
│   ├── openaudio.py
│   └── tests/
│       ├── __init__.py
│       ├── test_openaudio.py
│       └── test_tts_factory.py
```

#### 测试代码示例

```python
import unittest
from unittest.mock import Mock, patch
from app.tts.openaudio import OpenAudioEngine

class TestOpenAudioEngine(unittest.TestCase):
    """OpenAudio 引擎单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = OpenAudioEngine(
            model_path="/path/to/model",
            language="zh"
        )
    
    def tearDown(self):
        """测试后清理"""
        del self.engine
    
    def test_speak_success(self):
        """测试语音合成成功"""
        text = "你好世界"
        audio_path = self.engine.speak(text)
        
        self.assertIsNotNone(audio_path)
        self.assertTrue(audio_path.endswith(".wav"))
    
    def test_speak_empty_text(self):
        """测试空文本异常"""
        with self.assertRaises(ValueError):
            self.engine.speak("")
    
    @patch('app.tts.openaudio.torch.cuda.is_available')
    def test_device_selection(self, mock_cuda):
        """测试设备选择"""
        mock_cuda.return_value = True
        engine = OpenAudioEngine(model_path="/path")
        self.assertEqual(engine.device, "cuda")
        
        mock_cuda.return_value = False
        engine = OpenAudioEngine(model_path="/path")
        self.assertEqual(engine.device, "cpu")

if __name__ == '__main__':
    unittest.main()
```

#### 运行测试

```bash
# 运行所有测试
python -m unittest discover -s app -p "test_*.py"

# 运行单个测试文件
python -m unittest app.tts.tests.test_openaudio

# 运行单个测试用例
python -m unittest app.tts.tests.test_openaudio.TestOpenAudioEngine.test_speak_success

# 查看测试覆盖率
pip install coverage
coverage run -m unittest discover
coverage report
coverage html  # 生成 HTML 报告
```

### 2. 集成测试

```python
import unittest
from app.main import AIVTuber

class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.ai = AIVTuber(config_path="test_config.yaml")
    
    def tearDown(self):
        """测试后清理"""
        self.ai.stop()
    
    def test_full_conversation_flow(self):
        """测试完整对话流程"""
        # 1. 用户输入
        user_input = "你好"
        
        # 2. LLM 处理
        response = self.ai.process_message(user_input)
        self.assertIsNotNone(response)
        
        # 3. TTS 合成
        audio_path = self.ai.tts.speak(response)
        self.assertTrue(os.path.exists(audio_path))
        
        # 4. 记忆存储
        memories = self.ai.memory.get_recent(limit=1)
        self.assertEqual(len(memories), 1)
```

### 3. 性能测试

```python
import time
import unittest
from app.tts import TTSFactory

class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_tts_cache_performance(self):
        """测试 TTS 缓存性能"""
        tts = TTSFactory.create("chattts")
        text = "这是一段测试文本"
        
        # 第一次合成 (无缓存)
        start = time.time()
        audio1 = tts.speak(text)
        time1 = time.time() - start
        
        # 第二次合成 (有缓存)
        start = time.time()
        audio2 = tts.speak(text)
        time2 = time.time() - start
        
        # 缓存应该显著提升速度
        self.assertLess(time2, time1 * 0.5)
        self.assertEqual(audio1, audio2)
```

---

## 📦 版本发布规范

### 1. 版本号规则

```
v主版本.次版本.修订号

示例: v1.4.11
```

| 变更类型 | 版本号变化 | 示例 |
|---------|-----------|------|
| 重大功能、架构重构、API 不兼容 | 主版本 +1 | v1.0.0 → v2.0.0 |
| 功能改进、新增模块 | 次版本 +1 | v1.4.0 → v1.5.0 |
| Bug 修复、小改动、文档更新 | 修订号 +1 | v1.4.10 → v1.4.11 |

### 2. 发布前检查清单

#### ✅ 代码检查

- [ ] 所有测试通过
- [ ] 代码审查完成
- [ ] 无明显性能问题
- [ ] 无安全漏洞
- [ ] 依赖版本锁定

#### ✅ 文档检查

- [ ] 更新 VERSION.md ⭐
- [ ] 更新 README.md (如有必要)
- [ ] 更新 ARCHITECTURE.md (如有架构变更)
- [ ] 更新 API 文档 (如有 API 变更)

#### ✅ 配置检查

- [ ] config.yaml 示例正确
- [ ] 环境变量说明完整
- [ ] 依赖清单更新

### 3. 发布流程

#### 步骤 1: 更新 VERSION.md

```markdown
## 🟢 STABLE v1.4.11 (2026-04-06)

### ✨ 新增
- **OpenAudio S1-mini TTS 引擎** - 本地语音合成
  - 支持 13 种语言
  - 0.5B 参数，轻量高效
  - 自动设备选择 (CUDA/CPU)

### 🔧 修复
- **TTS 缓存失效** - 修复缓存键计算错误
  - 添加语言参数到缓存键
  - 修复音色参数未生效问题

### 📝 文档
- 更新版本记录到 v1.4.11
- 新增 ARCHITECTURE.md 技术架构文档
- 新增 DEV_GUIDE.md 开发规范文档
```

#### 步骤 2: 更新 README.md (如有必要)

```markdown
## 📌 当前版本

**v1.4.11** (2026-04-06)

- ✨ 新增 OpenAudio S1-mini TTS 引擎
- 🔧 修复 TTS 缓存失效问题
- 📝 完善技术文档
```

#### 步骤 3: Git 提交和打标签

```bash
# 提交更改
git add .
git commit -m "v1.4.11: 新增 OpenAudio TTS 引擎，修复缓存问题

- 新增 OpenAudio S1-mini TTS 引擎
- 修复 TTS 缓存失效问题
- 完善技术文档 (ARCHITECTURE.md, DEV_GUIDE.md)

Closes #123, #456"

# 打标签
git tag -a v1.4.11 -m "Release v1.4.11

新增功能:
- OpenAudio S1-mini TTS 引擎

Bug 修复:
- TTS 缓存失效问题

文档更新:
- ARCHITECTURE.md
- DEV_GUIDE.md"

# 推送到远程
git push origin main
git push origin v1.4.11
```

#### 步骤 4: 创建 Release (GitHub)

1. 进入 GitHub 仓库
2. 点击 "Releases" → "Draft a new release"
3. 选择标签 `v1.4.11`
4. 填写 Release 标题: `v1.4.11 - OpenAudio TTS 引擎`
5. 填写 Release 说明 (从 VERSION.md 复制)
6. 上传构建产物 (如有)
7. 点击 "Publish release"

---

## 🔧 维护规范

### 1. 日常维护任务

#### 每日任务

- [ ] 检查日志文件 (`app/logs/`)
- [ ] 监控错误率
- [ ] 检查磁盘空间

#### 每周任务

- [ ] 清理过期缓存 (`app/cache/`)
- [ ] 检查依赖更新
- [ ] 备份配置文件

#### 每月任务

- [ ] 更新依赖版本
- [ ] 性能分析和优化
- [ ] 安全审计

### 2. 依赖更新流程

```bash
# 1. 检查过期依赖
pip list --outdated

# 2. 更新依赖 (谨慎！)
pip install --upgrade <package>

# 3. 测试所有功能
python -m unittest discover

# 4. 更新 requirements.txt
pip freeze > app/requirements.txt

# 5. 更新 VERSION.md
# 记录依赖更新

# 6. 提交更改
git commit -m "chore: 更新依赖版本"
```

### 3. 日志管理

#### 日志文件位置

```
app/logs/
├── app.log           # 主程序日志
├── security.log      # 安全日志
├── tts.log           # TTS 日志
├── llm.log           # LLM 日志
└── error.log         # 错误日志
```

#### 日志轮转配置

```python
from loguru import logger

logger.add(
    "logs/app.log",
    rotation="10 MB",      # 10MB 轮转
    retention="7 days",    # 保留 7 天
    compression="zip",     # 压缩旧日志
    level="INFO"
)
```

#### 日志查看命令

```bash
# 实时查看日志
tail -f app/logs/app.log

# 查看最近 100 行
tail -n 100 app/logs/app.log

# 搜索错误日志
grep "ERROR" app/logs/app.log

# 统计错误数量
grep -c "ERROR" app/logs/app.log
```

---

## 🐛 问题排查指南

### 1. 常见问题排查

#### 问题: TTS 合成失败

```bash
# 1. 检查模型文件
ls -lh app/ChatTTS/
ls -lh app/OpenAudio\ S1-Mini/

# 2. 检查日志
grep "TTS" app/logs/app.log

# 3. 测试 TTS 引擎
python app/tts_api.py --provider chattts --text "测试"

# 4. 检查配置
cat app/config.yaml | grep -A 10 "tts:"
```

#### 问题: LLM 调用失败

```bash
# 1. 检查 API Key
echo $MINIMAX_API_KEY

# 2. 测试 API 连接
curl -X POST http://120.24.86.32:3000/v1/chat/completions \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M2.7","messages":[{"role":"user","content":"测试"}]}'

# 3. 检查日志
grep "LLM" app/logs/app.log
```

#### 问题: Web 界面无法访问

```bash
# 1. 检查端口占用
netstat -ano | grep 12393

# 2. 检查防火墙
# Windows:
netsh advfirewall firewall show rule name=all | grep 12393

# Linux:
sudo ufw status | grep 12393

# 3. 检查进程
ps aux | grep python
```

### 2. 性能问题排查

#### CPU 占用过高

```python
# 使用 cProfile 分析
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 执行代码
ai.process_message("hello")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

#### 内存占用过高

```python
# 使用 memory_profiler
from memory_profiler import profile

@profile
def process_message(text):
    # 代码...
    pass

# 运行
python -m memory_profiler app/main.py
```

#### 磁盘 I/O 过高

```bash
# Linux: 使用 iotop
sudo iotop -o

# 检查缓存大小
du -sh app/cache/

# 清理过期缓存
find app/cache/ -type f -mtime +7 -delete
```

---

## 📚 参考资料

### 1. 代码规范

- [PEP 8 -- Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Type Hints (PEP 484)](https://peps.python.org/pep-0484/)

### 2. 测试规范

- [unittest -- Unit testing framework](https://docs.python.org/3/library/unittest.html)
- [pytest Documentation](https://docs.pytest.org/)
- [coverage.py](https://coverage.readthedocs.io/)

### 3. Git 规范

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)

### 4. 内部文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 技术架构文档
- [VERSION.md](./VERSION.md) - 版本管理
- [CODE_REVIEW_REPORT.md](./CODE_REVIEW_REPORT.md) - 代码审查报告

---

## 📝 更新日志

| 日期 | 版本 | 作者 | 说明 |
|------|------|------|------|
| 2026-04-06 | v1.0.0 | 咕咕嘎嘎 | 初始版本 |

---

**文档维护**: 咕咕嘎嘎 🐱

**最后更新**: 2026-04-06
