#!/usr/bin/env python3
"""
=====================================
语音合成模块 (TTS) - v1.7
=====================================

【模块功能概述】
本模块实现 AI VTuber 系统的语音合成（TTS, Text-To-Speech）功能，
负责将 LLM 生成的文本回复转换为语音音频，供用户收听。

【架构设计】
采用"抽象基类 + 具体引擎 + 工厂模式"的三层架构：
1. TTSEngine (抽象基类) —— 定义 speak()/is_available()/stop() 接口
2. EdgeTTS (具体引擎) —— 基于 Microsoft Edge 在线 TTS 服务的免费引擎（备用/保底）
3. GPTSoVITSEngine (具体引擎，外部文件) —— 基于本地推理的音色克隆引擎（主用）
4. TTSFactory (工厂类) —— 根据 config 创建引擎，支持主引擎失败自动切换备用引擎

【两种引擎对比】
- EdgeTTS: 免费在线服务，音质好，无需 GPU，但依赖网络；
  支持多种中文音色和语速/音调/音量调节；内置文本哈希缓存和文件清理机制
- GPTSoVITS: 本地推理，支持音色克隆（只需几分钟参考音频）；
  音色更自然，但需要 GPU 和较大显存；实现在 tts/gptsovits.py 中

【缓存机制（EdgeTTS 专属）】
- 文本哈希缓存：用 MD5(text)[:16] 作为缓存键，避免重复合成相同文本
- 限频清理：音频文件每 60 秒最多清理一次，缓存文件每 120 秒最多清理一次
- 保留策略：音频文件保留最近 50 个，缓存文件保留最近 100 个

【打断机制】
TTSEngine 基类维护类级别的播放状态（_is_playing / _current_process），
新合成请求到来时自动终止上一个播放进程，实现"打断式"语音输出。

【与其他模块的关系】
- 被 web/__init__.py 调用，将 LLM 回复转换为语音并通过 SSE 流式推送
- 被 main.py 初始化，作为 pipeline 的一环（LLM → TTS → 播放）
- TTS 缓存与 tts_cache.py 配合（后者提供磁盘级 MD5 缓存）

【输入/输出】
- 输入：文本字符串（str）和可选的输出路径
- 输出：音频文件路径（str，WAV 格式）；失败时返回错误信息字符串

保留引擎:
- Edge TTS (备用，保底)
- GPT-SoVITS (主用，音色克隆)

作者: 咕咕嘎嘎
日期: 2026-04-20
"""

import os
import time
import asyncio
import tempfile
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path


# =====================================================================
# 第1层：抽象基类
# =====================================================================

class TTSEngine(ABC):
    """
    【抽象基类】TTS 语音合成引擎接口

    定义所有 TTS 引擎必须实现的接口方法。

    【类级别状态（跨实例共享）】
        _current_process: 当前正在播放音频的子进程（用于打断）
        _current_audio_file: 当前正在播放的音频文件路径
        _is_playing: 是否正在播放

    【设计意图】
        这些状态是类变量（而非实例变量），因为同一时间只能播放一个音频。
        任何 TTSEngine 实例都可以打断当前播放——实现全局打断机制。
    """

    # 类级别的播放状态（所有 TTS 实例共享，实现全局唯一播放）
    _current_process = None       # 当前播放音频的子进程对象（subprocess.Popen）
    _current_audio_file = None    # 当前播放的音频文件路径
    _is_playing = False           # 是否正在播放的标志

    @abstractmethod
    def speak(self, text: str, output_path: str = None) -> Optional[str]:
        """
        【抽象方法】合成语音

        【参数说明】
            text (str): 要合成的文本
            output_path (str, optional): 输出音频文件路径；为 None 时自动生成

        【返回值】
            Optional[str]: 生成的音频文件路径；失败时返回 None 或错误信息
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        【抽象方法】检查引擎是否可用

        【返回值】
            bool: True 表示引擎可用（依赖已安装、配置正确等）
        """
        pass

    def stop(self):
        """
        【打断方法】停止当前正在播放的音频

        通过终止播放子进程实现打断。这是"打断式语音输出"的核心——
        当新的 TTS 请求到来时，调用 stop() 终止上一个音频的播放。

        【线程安全】
            调用 terminate() 可能会失败（进程已结束等），用 try/except 静默处理。
        """
        if self._current_process:
            try:
                self._current_process.terminate()  # 终止播放子进程
                self._current_process = None
            except:
                pass
        self._is_playing = False

    def get_voices(self) -> list:
        """获取可用音色列表（子类可重写）"""
        return []


# =====================================================================
# 第2层：具体引擎实现
# =====================================================================

class EdgeTTS(TTSEngine):
    """
    【在线引擎】Microsoft Edge TTS 语音合成

    使用 Microsoft Edge 浏览器的在线 TTS 服务（免费，无需 API Key）。
    通过 edge-tts Python 库调用，支持多种中文音色和参数调节。

    【音色列表】
        - 中文普通话：XiaoxiaoNeural（标准女声）、XiaoyiNeural（年轻女声）、
          YunxiNeural（男声）、YunyangNeural（男声）
        - 粤语：HiuGaaiNeural、HiuMaanNeural
        - 台湾腔：HsiaoChenNeural、HsiaoYuNeural

    【缓存机制】
        1. 内存缓存：self._text_cache 字典，以文本哈希为键，缓存文件路径
        2. 磁盘缓存：self._cache_dir 目录下的 WAV 文件
        3. 限频清理：避免每次合成都扫描文件系统

    【配置参数】
        voice: 音色名称，默认 "zh-CN-XiaoxiaoNeural"
        rate: 语速，默认 "+0%"（可调 -50%~+100%）
        pitch: 音调，默认 "+0Hz"（可调 -20Hz~+20Hz）
        volume: 音量，默认 "+0%"（可调 -50%~+100%）
        max_retries: 最大重试次数，默认 3
        retry_delay: 重试延迟基数（秒），使用指数退避
    """

    # 内置音色映射表（供 web 面板选择）
    VOICES = {
        "zh-CN": {
            "XiaoxiaoNeural": "中文女声 (标准)",
            "XiaoyiNeural": "中文女声 (年轻)",
            "YunxiNeural": "中文男声 (云希)",
            "YunyangNeural": "中文男声 (云扬)",
        },
        "zh-HK": {
            "HiuGaaiNeural": "粤语女声",
            "HiuMaanNeural": "粤语女声",
        },
        "zh-TW": {
            "HsiaoChenNeural": "台湾女声",
            "HsiaoYuNeural": "台湾女声",
        }
    }

    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化 Edge TTS 引擎

        【参数说明】
            config (Dict[str, Any]): 引擎配置字典

        【初始化内容】
            1. 读取语音参数（音色、语速、音调、音量）
            2. 设置音频文件保留数量上限（50 个）
            3. 初始化文本缓存字典和缓存目录
            4. 设置重试参数和清理节流时间戳
        """
        self.config = config
        self.voice = config.get("voice", "zh-CN-XiaoxiaoNeural")  # 音色
        self.rate = config.get("rate", "+0%")                       # 语速
        self.pitch = config.get("pitch", "+0Hz")                    # 音调
        self.volume = config.get("volume", "+0%")                   # 音量

        # 音频文件清理策略：保留最近 N 个文件
        self._max_audio_files = 50

        # 文本缓存（避免重复合成相同文本）
        self._text_cache: Dict[str, str] = {}   # {文本哈希: 缓存文件路径}
        self._cache_dir = self._get_cache_dir()  # 缓存目录路径
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # 重试配置
        self._max_retries = config.get("max_retries", 3)       # 最大重试次数
        self._retry_delay = config.get("retry_delay", 1.0)    # 重试延迟基数（秒）
        
        # 限频清理的时间戳（避免每次合成都扫描文件系统）
        self._last_audio_cleanup = 0    # 上次音频清理时间
        self._last_cache_cleanup = 0    # 上次缓存清理时间

    def _get_cache_dir(self) -> Path:
        """
        【内部方法】获取 TTS 缓存目录路径

        【返回值】
            Path: 缓存目录路径（app/web/static/audio_cache/）

        【路径计算】
            从当前文件位置向上两级找到项目根目录，
            再定位到 web/static/audio_cache/ 目录。
        """
        tts_file = os.path.abspath(__file__)
        app_dir = os.path.dirname(os.path.dirname(tts_file))
        cache_dir = os.path.join(app_dir, "web", "static", "audio_cache")
        return Path(cache_dir)
    
    def _should_cleanup_audio(self) -> bool:
        """
        【节流方法】限频检查是否需要清理音频文件

        每 60 秒最多触发一次清理，避免频繁的文件系统扫描影响性能。

        【返回值】
            bool: True 表示应该执行清理
        """
        now = time.time()
        if (now - self._last_audio_cleanup) > 60:
            self._last_audio_cleanup = now
            return True
        return False
    
    def _should_cleanup_cache(self) -> bool:
        """
        【节流方法】限频检查是否需要清理缓存文件

        每 120 秒最多触发一次清理（比音频清理频率更低，因为缓存更重要）。
        """
        now = time.time()
        if (now - self._last_cache_cleanup) > 120:
            self._last_cache_cleanup = now
            return True
        return False

    def _get_text_hash(self, text: str) -> str:
        """
        【内部方法】计算文本的 MD5 哈希（取前16位）

        【参数说明】
            text (str): 待哈希的文本

        【返回值】
            str: 16 位十六进制哈希字符串

        【用途】
            作为缓存的键，避免重复合成相同文本。
            取前 16 位足够避免哈希冲突，同时保持缓存文件名简洁。
        """
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def _get_cache_path(self, text: str) -> Optional[Path]:
        """
        【内部方法】查询缓存中是否已有该文本的合成结果

        【查询策略】
            1. 先查内存缓存字典（最快）
            2. 再查磁盘缓存目录（兜底，应对进程重启后内存缓存丢失的情况）

        【返回值】
            Optional[Path]: 缓存的音频文件路径；无缓存时返回 None
        """
        text_hash = self._get_text_hash(text)

        # 1. 查内存缓存
        cached = self._text_cache.get(text_hash)
        if cached and Path(cached).exists():
            return Path(cached)

        # 2. 查磁盘缓存（按修改时间倒序排列，取最新的一个）
        cache_files = sorted(
            self._cache_dir.glob(f"{text_hash}_*.wav"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if cache_files:
            return cache_files[0]

        return None

    def _save_to_cache(self, text: str, output_path: str):
        """
        【内部方法】将合成结果记录到内存缓存

        【设计意图】
            不复制文件，只记录文件路径。因为 Edge TTS 已经将音频写入 output_path，
            只需在内存中记录"这段文本对应的文件路径"即可。

        【参数说明】
            text (str): 已合成的文本
            output_path (str): 音频文件路径
        """
        text_hash = self._get_text_hash(text)
        self._text_cache[text_hash] = str(Path(output_path).resolve())

    def _cleanup_old_audio(self):
        """
        【内部方法】清理旧音频文件（保留最近 N 个）

        扫描音频输出目录，按修改时间排序，删除超出上限的旧文件。
        使用 try/except 静默处理删除失败（文件可能被占用）。
        """
        try:
            audio_dir = Path(self._get_output_path()).parent
            # 按修改时间倒序排列（最新的在前）
            audio_files = sorted(
                audio_dir.glob("response_*.wav"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            # 删除超出保留数量的旧文件
            for f in audio_files[self._max_audio_files:]:
                try:
                    f.unlink()
                except OSError:
                    pass
        except Exception:
            pass

    def _cleanup_cache(self):
        """
        【内部方法】清理缓存目录（保留最近 100 个）

        与 _cleanup_old_audio 类似，但操作缓存目录，保留数量更大。
        """
        try:
            cache_files = sorted(
                self._cache_dir.glob("*.wav"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            for f in cache_files[100:]:
                try:
                    f.unlink()
                except OSError:
                    pass
        except Exception:
            pass

    def _get_output_path(self) -> str:
        """
        【内部方法】生成统一的音频输出路径

        【返回值】
            str: 音频文件完整路径，格式为 app/web/static/audio/response_{timestamp}.wav

        【命名规则】
            使用毫秒级时间戳作为文件名，确保唯一性。
        """
        tts_file = os.path.abspath(__file__)
        app_dir = os.path.dirname(os.path.dirname(tts_file))
        audio_dir = os.path.join(app_dir, "web", "static", "audio")
        os.makedirs(audio_dir, exist_ok=True)
        return os.path.join(audio_dir, f'response_{int(time.time()*1000)}.wav')

    def speak(self, text: str, output_path: str = None, **kwargs) -> Optional[str]:
        """
        【核心方法】合成语音 —— 带缓存、打断和重试机制

        【参数说明】
            text (str): 要合成的文本
            output_path (str, optional): 指定输出路径；为 None 时自动生成
            **kwargs: 接受额外参数（兼容 GPT-SoVITS 的 project 等专有参数）

        【返回值】
            Optional[str]: 生成的音频文件路径；重试全部失败时返回错误信息字符串

        【执行流程】
            1. 打断当前正在播放的音频（terminate 子进程）
            2. 检查缓存（如果未指定输出路径）
            3. 生成输出路径（如果未指定）
            4. 重试循环：调用 _synthesize() 合成音频
            5. 合成成功后保存到缓存，并触发限频清理
            6. 重试使用指数退避策略（delay * 2^attempt）

        【v1.6 改进】
            接受 **kwargs 忽略未知参数，使接口兼容 GPT-SoVITS 等引擎的专有参数。
        """
        # 1. 打断当前播放 —— 新请求到来时终止上一个音频
        if self._is_playing and self._current_process:
            try:
                self._current_process.terminate()
                self._current_process = None
            except:
                pass
            self._is_playing = False

        # 2. 检查缓存（仅在未指定输出路径时才查缓存）
        if not output_path:
            cached = self._get_cache_path(text)
            if cached:
                return str(cached)  # 缓存命中，直接返回

        # 3. 自动生成输出路径
        if output_path is None:
            output_path = self._get_output_path()

        # 4. 重试循环
        last_error = None
        for attempt in range(self._max_retries):
            try:
                result = self._synthesize(text, output_path)
                if result:
                    # 合成成功 → 保存缓存
                    self._save_to_cache(text, output_path)
                    # 触发限频清理（仅在节流时间窗口允许时才执行）
                    if self._should_cleanup_audio():
                        self._cleanup_old_audio()
                    if self._should_cleanup_cache():
                        self._cleanup_cache()
                    return result
            except Exception as e:
                last_error = e
                # 指数退避重试：1s → 2s → 4s
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (2 ** attempt))

        # 所有重试都失败
        return f"合成错误: {str(last_error)}"

    def _synthesize(self, text: str, output_path: str) -> Optional[str]:
        """
        【内部方法】调用 Edge TTS 进行实际的语音合成

        【参数说明】
            text (str): 要合成的文本
            output_path (str): 输出 WAV 文件路径

        【返回值】
            Optional[str]: 成功时返回 output_path；失败时返回 None

        【事件循环处理】
            edge-tts 是异步库，需要在事件循环中运行。
            分两种情况处理：
            1. 已有运行中的事件循环 → 用 ThreadPoolExecutor 在新线程中运行 asyncio.run()
            2. 没有事件循环 → 直接调用 asyncio.run()

            这避免了 "RuntimeError: This event loop is already running" 的经典错误。
        """
        import edge_tts

        # 定义异步合成函数
        async def synthesize():
            communicate = edge_tts.Communicate(
                text,
                self.voice,     # 音色
                rate=self.rate,       # 语速
                pitch=self.pitch,     # 音调
                volume=self.volume,   # 音量
            )
            await communicate.save(output_path)  # 合成并保存为 WAV

        # 检查是否已有运行中的事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 已有事件循环在运行 → 在独立线程中运行 asyncio.run()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                f = pool.submit(asyncio.run, synthesize())
                f.result()  # 等待结果（阻塞直到合成完成）
        else:
            # 没有事件循环 → 直接运行
            asyncio.run(synthesize())
        
        return output_path

    def is_available(self) -> bool:
        """检查 edge-tts 库是否已安装"""
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    def get_voices(self) -> list:
        """获取内置的音色映射表"""
        return self.VOICES


# =====================================================================
# 辅助函数
# =====================================================================

def _get_gptsovits_model_dir() -> str:
    """
    【辅助函数】统一计算 GPT-SoVITS 模型目录的绝对路径

    【返回值】
        str: GPT-SoVITS 目录的绝对路径（项目根目录/GPT-SoVITS/）

    【路径计算】
        从当前文件（tts/__init__.py）向上两级找到项目根目录，
        再拼接 "GPT-SoVITS" 子目录名。

    【设计意图】
        集中路径计算逻辑，避免在多个地方重复路径计算代码。
        GPTSoVITSEngine 的 root_dir 参数默认使用此函数的结果。
    """
    tts_pkg_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(tts_pkg_dir)
    return os.path.join(app_dir, "GPT-SoVITS")


# =====================================================================
# 第3层：工厂类
# =====================================================================

class TTSFactory:
    """
    【工厂类】TTS 引擎工厂

    根据 config 中的 provider 字段创建对应的 TTS 引擎实例。
    支持主引擎 + 备用引擎的自动降级机制。

    【降级策略】
        1. 尝试创建主引擎（config["provider"]），检查 is_available()
        2. 主引擎失败 → 依次尝试 fallback_engines 列表中的备用引擎
        3. 所有引擎都失败 → 强制使用 EdgeTTS 作为最后保底

    【使用方式】
        tts = TTSFactory.create({"provider": "gptsovits", "gptsovits": {...}})
        path = tts.speak("你好世界")
    """

    @staticmethod
    def create(config: Dict[str, Any]) -> TTSEngine:
        """
        【静态工厂方法】创建 TTS 引擎（带自动降级）

        【参数说明】
            config (Dict[str, Any]): TTS 配置字典，包含：
                - provider: 主引擎名称（如 "gptsovits"、"edge"）
                - fallback_engines: 备用引擎列表（默认 ["edge"]）
                - {引擎名}: 各引擎的专属配置

        【返回值】
            TTSEngine: 可用的 TTS 引擎实例
        """
        provider = config.get("provider", "gptsovits")  # 主引擎，默认 GPT-SoVITS
        fallback_providers = config.get("fallback_engines", ["edge"])  # 备用引擎列表

        # 1. 尝试创建主引擎
        try:
            tts = TTSFactory._create_engine(provider, config.get(provider, {}), config)
            if tts and tts.is_available():
                return tts
        except Exception as e:
            print(f"[TTS] 主引擎 {provider} 加载失败: {e}")

        # 2. 主引擎失败，依次尝试备用引擎
        for fb_provider in fallback_providers:
            try:
                tts = TTSFactory._create_engine(fb_provider, config.get(fb_provider, {}), config)
                if tts and tts.is_available():
                    print(f"[TTS] 切换到备用引擎: {fb_provider}")
                    return tts
            except Exception as e:
                print(f"[TTS] 备用引擎 {fb_provider} 加载失败: {e}")

        # 3. 所有引擎都失败，强制使用 EdgeTTS 作为最后保底
        return TTSFactory._create_engine("edge", config.get("edge", {}), config)

    @staticmethod
    def _create_engine(provider: str, provider_config: Dict, full_config: Dict) -> TTSEngine:
        """
        【内部静态方法】根据 provider 名称创建具体的引擎实例

        【参数说明】
            provider (str): 引擎名称（"edge" 或 "gptsovits"）
            provider_config (Dict): 该引擎的专属配置
            full_config (Dict): 完整的 TTS 配置（用于跨引擎共享参数）

        【返回值】
            TTSEngine: 对应的引擎实例

        【异常】
            未知 provider 时抛出 ValueError
        """
        if provider == "edge":
            return EdgeTTS(provider_config)
        elif provider == "gptsovits":
            # GPT-SoVITS 的实现在单独的文件中（tts/gptsovits.py）
            from .gptsovits import GPTSoVITSEngine
            # 复制配置并设置默认的模型根目录
            provider_config = dict(provider_config)  # 避免修改原始配置
            provider_config.setdefault("root_dir", _get_gptsovits_model_dir())
            return GPTSoVITSEngine(provider_config)
        else:
            raise ValueError(f"未知 TTS 提供商: {provider}")
