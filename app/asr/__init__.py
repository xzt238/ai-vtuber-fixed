#!/usr/bin/env python3
"""
=====================================
语音识别模块 (ASR) - 优化版
=====================================

【模块功能概述】
本模块实现了 AI VTuber 系统的语音识别（ASR, Automatic Speech Recognition）功能，
负责将用户的语音输入转换为文本，供 LLM 处理。

【架构设计】
采用"抽象基类 + 多种实现 + 工厂模式 + 管理器"的四层架构：
1. ASREngine (抽象基类) —— 定义 recognize() 和 is_available() 接口
2. 具体引擎类 —— FasterWhisperASR、WhisperASR、FunASRASR 各自实现识别逻辑
3. ASRFactory (工厂类) —— 根据 config 中的 provider 字段创建对应的引擎实例
4. ASRManager (管理器) —— 管理多个引擎实例，支持动态切换和自动 fallback

【三种引擎对比】
- FasterWhisperASR: 本地推理，基于 CTranslate2 加速，支持 GPU/CPU 自动选择，
  模型预热用静音音频避免首次识别卡顿
- WhisperASR: 调用 OpenAI Whisper API（云端），需要 API Key，
  适合无本地 GPU 或需要最高精度的场景
- FunASRASR: 本地推理，基于阿里达摩院 FunASR/Paraformer，
  懒加载设计——首次调用 recognize() 时才加载模型，减少启动时间

【与其他模块的关系】
- 被 voice/__init__.py 调用，将录音结果传给 ASR 进行识别
- 被 web/__init__.py 的 WebSocket 处理器调用，处理浏览器端录音的识别请求
- ASRManager 的 provider 切换可通过 web 面板实时操作

【输入/输出】
- 输入：音频文件路径（WAV 格式，16kHz 单声道）和配置字典
- 输出：识别出的文本字符串（str），失败时返回 None

优化点:
- 模型预热（用静音音频触发首次推理，消除冷启动延迟）
- 批处理支持（recognize_batch 顺序处理多个音频文件）
- 更好的错误处理（ImportError 提示安装命令，异常捕获不中断服务）
- 懒加载（FunASR 延迟到首次使用时加载，加速启动）
- 自动 Fallback（ASRManager 当前引擎失败时自动尝试其他可用引擎）

作者: 咕咕嘎嘎
日期: 2026-04-01
"""

import os
import tempfile
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path


# =====================================================================
# 第1层：抽象基类
# =====================================================================

class ASREngine(ABC):
    """
    【抽象基类】语音识别引擎接口

    所有 ASR 引擎实现都必须继承此类，并实现以下两个抽象方法：
    - recognize(audio_path) → str|None: 识别音频文件中的文本
    - is_available() → bool: 检查引擎是否可用（模型是否加载成功等）

    【设计意图】
    通过抽象基类统一所有 ASR 后端的接口，使上层代码（voice、web 模块）
    可以不关心具体使用哪种 ASR 引擎，实现解耦。
    """
    
    @abstractmethod
    def recognize(self, audio_path: str) -> Optional[str]:
        """
        【抽象方法】识别音频文件中的文本

        【参数说明】
            audio_path (str): 音频文件的绝对/相对路径，通常为 WAV 格式

        【返回值】
            Optional[str]: 识别出的文本；识别失败或音频无效时返回 None

        【实现要求】
            子类必须实现此方法，处理文件不存在、格式不支持等异常情况
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        【抽象方法】检查引擎是否可用

        【返回值】
            bool: True 表示引擎已就绪可识别；False 表示模型未加载或配置错误

        【实现要求】
            - 本地模型：检查 model 对象是否为 None
            - API 模型：检查 API Key 是否已配置
        """
        pass


# =====================================================================
# 第2层：具体引擎实现
# =====================================================================

class FasterWhisperASR(ASREngine):
    """
    【本地引擎】Faster-Whisper 语音识别

    基于 OpenAI Whisper 模型的 CTranslate2 优化版本，支持 GPU 推理加速。
    这是系统推荐的默认 ASR 后端，在本地 GPU 上推理速度极快。

    【关键特性】
    - 自动设备选择（auto → 优先 GPU，回退 CPU）
    - 模型预热：构造时自动用静音音频触发首次推理，消除冷启动延迟
    - 支持 HuggingFace 镜像配置（国内用户可加速下载）
    - 批处理接口（recognize_batch）顺序处理多个音频

    【配置参数】（通过 config 字典传入）
        model_size: 模型大小，可选 tiny/base/small/medium/large/large-v2/large-v3
        device: 推理设备，auto/cuda/cpu
        compute_type: 计算精度，float16/float32/int8 等
        download_root: HuggingFace 模型缓存目录（可选）
        language: 识别语言，默认 zh（中文）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化 Faster-Whisper ASR 引擎

        【参数说明】
            config (Dict[str, Any]): 引擎配置字典，包含模型大小、设备、精度等参数

        【初始化流程】
            1. 保存配置到 self.config
            2. 初始化模型引用 self.model = None
            3. 标记预热状态 self._warmed_up = False
            4. 调用 _load_model() 加载模型并预热
        """
        self.config = config
        self.model = None           # 模型引用，加载成功后指向 WhisperModel 实例
        self._warmed_up = False     # 预热标记，避免重复预热
        self._load_model()          # 构造时立即加载模型
    
    def _load_model(self):
        """
        【内部方法】加载 Faster-Whisper 模型

        【执行流程】
            1. 从 faster_whisper 包导入 WhisperModel（延迟导入，避免未安装时报错）
            2. 从 config 读取模型参数（model_size/device/compute_type/download_root）
            3. 如果配置了 download_root，设置 HF_HOME 环境变量指定模型缓存位置
            4. 创建 WhisperModel 实例（此时模型加载到内存/GPU）
            5. 调用 _warmup() 进行模型预热

        【错误处理】
            - ImportError: faster-whisper 未安装，打印安装提示
            - Exception: 模型加载失败（如 CUDA OOM），打印错误信息
            两种情况都将 self.model 设为 None，后续 recognize() 返回 None
        """
        try:
            from faster_whisper import WhisperModel
            
            # 从配置中读取模型参数，提供合理的默认值
            model_size = self.config.get("model_size", "base")       # 默认 base 模型（约 74MB）
            device = self.config.get("device", "auto")               # 自动选择设备
            compute_type = self.config.get("compute_type", "float16") # 默认半精度（速度与精度平衡）
            download_root = self.config.get("download_root", None)   # 可选的模型缓存目录
            
            # 设置 HuggingFace 镜像（国内加速下载）
            # 通过设置 HF_HOME 环境变量，让 HuggingFace Hub 将模型缓存到指定目录
            if download_root:
                os.environ["HF_HOME"] = download_root
            
            print(f" 加载 Faster-Whisper 模型: {model_size} ({device})...")
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type
            )
            print(" Faster-Whisper 模型加载完成!")
            
            # 模型加载成功后立即预热，消除首次推理的冷启动延迟
            self._warmup()
            
        except ImportError:
            print("️ faster-whisper 未安装: pip install faster-whisper")
            self.model = None
        except Exception as e:
            print(f"️ Faster-Whisper 加载失败: {e}")
            self.model = None
    
    def _warmup(self):
        """
        【内部方法】模型预热 —— 消除首次推理的冷启动延迟

        【原理】
            深度学习模型的首次推理通常较慢，因为需要：
            1. 分配 GPU 显存
            2. 编译计算图（JIT）
            3. 初始化各种缓存

            通过在构造时用一段静音音频触发一次推理，让这些初始化工作提前完成，
            后续用户实际使用时就不会感受到明显的延迟。

        【实现细节】
            1. 生成 1 秒的静音音频（16kHz，全零 float32 数组）
            2. 保存为临时 WAV 文件
            3. 用 transcribe() 对静音音频进行一次推理
            4. 删除临时文件
            5. 标记 _warmed_up = True 防止重复预热

        【错误处理】
            预热失败不会影响正常功能（_warmed_up 保持 False，后续调用会再次尝试）
        """
        # 如果模型未加载或已预热过，跳过
        if self.model is None or self._warmed_up:
            return
        
        try:
            print(" 预热 ASR 模型...")
            import numpy as np
            import soundfile as sf
            
            # 生成 1 秒静音音频（16000 采样点，float32 格式）
            sample_rate = 16000
            audio = np.zeros(sample_rate, dtype=np.float32)
            
            # 将静音音频写入临时 WAV 文件（delete=False 因为 Windows 下文件可能被锁定）
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, audio, sample_rate)
                tmp_path = tmp.name
            
            # 对静音音频执行一次完整推理，触发模型初始化
            # 使用 list() 消耗生成器，确保推理完整执行
            list(self.model.transcribe(tmp_path, language="zh"))
            
            # 清理临时文件
            os.unlink(tmp_path)
            
            self._warmed_up = True
            print(" ASR 模型预热完成!")
        except Exception as e:
            print(f"️ ASR 预热失败: {e}")
    
    def recognize(self, audio_path: str) -> Optional[str]:
        """
        【核心方法】识别音频文件中的文本

        【参数说明】
            audio_path (str): 待识别的音频文件路径（WAV 格式）

        【返回值】
            Optional[str]: 识别出的文本，去除首尾空白；
                          模型未加载或识别失败时返回 None

        【实现细节】
            - 使用 beam_size=5 的束搜索解码（精度与速度的平衡）
            - 将所有分段的文本拼接为一个完整字符串
        """
        if self.model is None:
            return None
        
        try:
            language = self.config.get("language", "zh")
            # transcribe() 返回一个生成器，迭代得到 (segment, info) 元组
            # segment 包含 text（文本）、start（开始时间）、end（结束时间）
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5     # 束搜索宽度，越大越准但越慢
            )
            # 拼接所有分段文本
            text = "".join([seg.text for seg in segments])
            return text.strip() if text else None
        except Exception as e:
            print(f"️ 识别错误: {e}")
            return None
    
    def recognize_batch(self, audio_paths: List[str]) -> List[Optional[str]]:
        """
        【批处理方法】批量识别多个音频文件

        【参数说明】
            audio_paths (List[str]): 音频文件路径列表

        【返回值】
            List[Optional[str]]: 与输入等长的识别结果列表，每个元素是对应文本或 None

        【设计意图】
            当前实现为顺序处理（非并行），因为 Faster-Whisper 的 GPU 推理
            一次只能处理一个音频。未来可考虑批处理 API（如果 CTranslate2 支持）。
        """
        results = []
        for path in audio_paths:
            results.append(self.recognize(path))
        return results
    
    def is_available(self) -> bool:
        """检查引擎是否可用（模型是否成功加载）"""
        return self.model is not None


class WhisperASR(ASREngine):
    """
    【云端引擎】OpenAI Whisper API 语音识别

    通过 HTTP API 调用 OpenAI 的 Whisper 语音识别服务。
    适合没有本地 GPU 或需要最高识别精度的场景。

    【特点】
    - 无需本地模型，减少内存/GPU 占用
    - 需要网络连接和 API Key
    - 支持自定义 base_url（可用于代理或兼容 API）

    【配置参数】
        api_key: OpenAI API Key（必需）
        model: 模型名称，默认 whisper-1
        base_url: API 基础 URL，默认 https://api.openai.com/v1
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化 Whisper API 客户端

        【参数说明】
            config (Dict[str, Any]): 包含 api_key、model、base_url 的配置字典
        """
        self.config = config
        self.api_key = config.get("api_key", "")                                        # API 密钥
        self.model = config.get("model", "whisper-1")                                   # 模型名称
        self.base_url = config.get("base_url", "https://api.openai.com/v1")             # API 地址
    
    def recognize(self, audio_path: str) -> Optional[str]:
        """
        【核心方法】通过 API 识别音频

        【参数说明】
            audio_path (str): 音频文件路径

        【返回值】
            Optional[str]: 识别文本或 None

        【实现细节】
            使用 requests 库发送 multipart/form-data 请求：
            - file 字段：音频文件二进制数据
            - model 字段：使用的模型名称
            - language 字段：指定识别语言（zh）
            超时设置为 60 秒，避免大音频文件导致请求挂起
        """
        if not self.api_key:
            print("️ 请配置 OpenAI API Key")
            return None
        
        try:
            import requests
            
            # 以二进制模式打开音频文件，作为 multipart 上传
            with open(audio_path, "rb") as f:
                files = {"file": f}     # 文件字段
                headers = {"Authorization": f"Bearer {self.api_key}"}  # Bearer Token 认证
                data = {"model": self.model, "language": "zh"}         # 表单参数
                
                response = requests.post(
                    f"{self.base_url}/audio/transcriptions",  # API 端点
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=60   # 60秒超时
                )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("text", "").strip()
            else:
                print(f"️ Whisper API错误: {response.status_code}")
                return None
        except Exception as e:
            print(f"️ 识别错误: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查 API Key 是否已配置（有 Key 即视为可用）"""
        return bool(self.api_key)


class FunASRASR(ASREngine):
    """
    【本地引擎】FunASR 语音识别 —— 懒加载版

    基于阿里达摩院开源的 Paraformer 模型，中文识别效果优秀。

    【关键设计 —— 懒加载】
    与 FasterWhisperASR 的立即加载不同，FunASRASR 采用懒加载策略：
    - 构造时不加载模型（self.model = None）
    - 首次调用 recognize() 或 is_available() 时，_ensure_model() 检测到模型为 None，触发加载
    - 这样可以将模型加载延迟到实际需要时，加速系统启动

    【配置参数】
        model: 模型名称，默认 paraformer-zh
        device: 推理设备，默认 cuda
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化 FunASR 配置，但不加载模型（懒加载）

        【参数说明】
            config (Dict[str, Any]): 引擎配置字典
        """
        self.config = config
        self.model = None  # 延迟加载标志：None 表示模型尚未初始化
    
    def _ensure_model(self):
        """
        【懒加载守卫】确保模型已加载

        如果 self.model 为 None（首次调用），触发 _load_model()。
        后续调用直接返回，不再重复加载。

        【设计意图】
        将模型加载的开销从构造时间推迟到首次使用时间。
        如果用户从未使用 ASR 功能，模型就永远不会被加载。
        """
        if self.model is not None:
            return
        
        # 首次加载时打印调用栈，帮助开发者定位触发加载的位置
        import traceback as tb
        try:
            self._load_model()
        except Exception as e:
            print(f"️ FunASR 加载失败: {e}")
            tb.print_exc()
    
    def _load_model(self):
        """
        【内部方法】加载 FunASR 模型

        【执行流程】
            1. 计算项目根目录下的 models/ 缓存路径
            2. 设置 MODELSCOPE_CACHE 环境变量（必须在导入 funasr 之前设置）
            3. 检查本地是否有模型缓存，有则直接加载，无则从 ModelScope 下载
            4. 创建 AutoModel 实例

        【注意事项】
            - MODELSCOPE_CACHE 必须在 import funasr 之前设置，否则不生效
            - 使用 disable_update=True 避免加载后自动检查更新
        """
        try:
            # 计算模型缓存目录：项目根目录/models/
            project_root = Path(__file__).parent.parent.parent
            models_cache = project_root / "models"
            models_cache.mkdir(parents=True, exist_ok=True)

            # 关键：必须在导入 funasr 之前设置缓存环境变量
            os.environ["MODELSCOPE_CACHE"] = str(models_cache)
            
            from funasr import AutoModel
            
            model_name = self.config.get("model", "paraformer-zh")
            device = self.config.get("device", "cuda")
            
            print(f" 加载 FunASR 模型: {model_name}...")
            print(f" 缓存目录: {models_cache}")
            
            # 检查本地是否有预下载的模型缓存
            # Paraformer 模型的 ModelScope 缓存路径格式固定
            model_cache_path = models_cache / "modelscope" / "hub" / "iic" / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
            
            if model_cache_path.exists():
                # 本地缓存存在，直接从本地加载（无需网络）
                print(" 找到本地模型缓存!")
                self.model = AutoModel(
                    model=str(model_cache_path),
                    device=device,
                    disable_update=True     # 禁用自动更新检查
                )
            else:
                # 本地无缓存，从 ModelScope 下载（可能较慢）
                print(" 未找到缓存，下载模型...")
                self.model = AutoModel(model=model_name, device=device)
            
            print(" FunASR 模型加载完成!")
        except ImportError:
            print("️ funasr 未安装: pip install funasr")
            self.model = None
        except Exception as e:
            print(f"️ FunASR 加载失败: {e}")
            self.model = None
    
    def recognize(self, audio_path: str) -> Optional[str]:
        """
        【核心方法】识别音频文件

        【参数说明】
            audio_path (str): 音频文件路径

        【返回值】
            Optional[str]: 识别文本或 None

        【实现细节】
            1. 先调用 _ensure_model() 确保模型已加载（懒加载）
            2. 用 torchaudio 加载音频文件
            3. 重采样到 16kHz（FunASR 要求的采样率）
            4. 如果是多声道，混音为单声道
            5. 调用 model.generate() 执行识别
            6. batch_size_s=300 表示最多处理 300 秒的音频
        """
        self._ensure_model()  # 懒加载：首次调用时才加载模型
        if self.model is None:
            return None
        
        try:
            import torch
            import torchaudio
            
            # 直接加载 WAV 文件（前端已转换为 WAV 格式）
            # 返回 waveform（张量）和 sample_rate（采样率）
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # 重采样到 16kHz（FunASR/Paraformer 要求的输入采样率）
            if sample_rate != 16000:
                waveform = torchaudio.functional.resample(waveform, sample_rate, 16000)

            # 多声道混音为单声道（取平均值）
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
            
            # 转换为 NumPy 数组供 FunASR 使用
            audio_data = waveform.squeeze().numpy()
            
            # 调用 Paraformer 模型进行语音识别
            result = self.model.generate(
                input=audio_data,
                batch_size_s=300,    # 批处理大小（以秒为单位），控制显存使用
                hotword=""           # 热词增强（空字符串表示不使用）
            )
            # result 格式: [{"text": "识别结果", "key": "..."}]
            if result and len(result) > 0:
                text = result[0]["text"]
                # FunASR Paraformer 在中文字间插入空格，需要去除
                return text.replace(" ", "").strip()
            return None
        except Exception as e:
            print(f"️ 识别错误: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查引擎是否可用（先触发懒加载，再检查模型是否成功加载）"""
        self._ensure_model()  # 先确保模型加载
        return self.model is not None



# =====================================================================
# 第3层：工厂类
# =====================================================================

class ASRFactory:
    """
    【工厂类】ASR 引擎工厂

    根据配置中的 provider 字段，创建对应的 ASR 引擎实例。
    这是工厂模式的标准实现，将对象的创建逻辑与使用逻辑解耦。

    【使用方式】
        asr = ASRFactory.create({"provider": "faster_whisper", "faster_whisper": {...}})
        text = asr.recognize("audio.wav")

    【支持的 provider 值】
        - "faster_whisper": 创建 FasterWhisperASR（默认）
        - "whisper": 创建 WhisperASR（OpenAI API）
        - "funasr": 创建 FunASRASR（阿里 Paraformer）
    """
    
    @staticmethod
    def create(config: Dict[str, Any]) -> ASREngine:
        """
        【静态工厂方法】根据配置创建 ASR 引擎实例

        【参数说明】
            config (Dict[str, Any]): 配置字典，必须包含 "provider" 字段
                                    以及对应引擎的子配置（如 "faster_whisper": {...}）

        【返回值】
            ASREngine: 对应的引擎实例

        【容错】如果 provider 不识别，回退到 FasterWhisperASR
        """
        # 从配置中读取 provider，默认使用 faster_whisper
        provider = config.get("provider", "faster_whisper")
        
        if provider == "faster_whisper":
            # 创建 Faster-Whisper 引擎，传入其专属配置
            return FasterWhisperASR(config.get("faster_whisper", {}))
        elif provider == "whisper":
            # 创建 OpenAI Whisper API 引擎
            return WhisperASR(config.get("whisper", {}))
        elif provider == "funasr":
            # 创建 FunASR 引擎
            return FunASRASR(config.get("funasr", {}))
        else:
            # 未知 provider：警告并回退到 Faster-Whisper
            print(f"️ 未知的ASR provider: {provider}，使用Faster-Whisper")
            return FasterWhisperASR(config.get("faster_whisper", {}))


# =====================================================================
# 第4层：管理器
# =====================================================================

class ASRManager:
    """
    【管理器】ASR Provider 管理器 —— 支持动态切换和自动 Fallback

    【核心功能】
    1. 预加载：启动时尝试加载所有已配置的 ASR Provider
    2. 动态切换：运行时通过 switch_provider() 切换当前引擎
    3. 自动 Fallback：当前引擎识别失败时，自动尝试其他可用引擎
    4. 查询接口：获取当前/可用 Provider 列表

    【使用场景】
    - 用户在 web 面板上切换 ASR 引擎（如从 FunASR 切换到 Whisper API）
    - 当前引擎因网络/资源问题不可用时，自动回退到其他引擎
    - 多引擎协同工作（如本地引擎实时识别 + API 引擎兜底）

    【数据结构】
        self._engines: Dict[str, ASREngine] —— 所有已加载的引擎映射 {provider名: 引擎实例}
        self._current_provider: str —— 当前使用的 provider 名称
        self._current_engine: ASREngine —— 当前引擎实例（与 _current_provider 对应）
    """
    
    # 支持的 Provider 列表（预加载时按此顺序尝试）
    SUPPORTED_PROVIDERS = ["funasr", "faster_whisper", "whisper"]
    
    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化 ASR 管理器

        【参数说明】
            config (Dict[str, Any]): ASR 配置字典，包含各 provider 的子配置

        【初始化流程】
            1. 保存配置和当前 provider 设置
            2. 初始化引擎字典和当前引擎引用
            3. 调用 _preload_engines() 预加载所有可用引擎
        """
        self.config = config
        self._engines: Dict[str, ASREngine] = {}       # 所有已加载的引擎
        self._current_provider = config.get("provider", "funasr")  # 当前 provider
        self._current_engine: Optional[ASREngine] = None          # 当前引擎实例
        
        # 预加载所有配置了的 Provider
        self._preload_engines()
    
    def _preload_engines(self):
        """
        【内部方法】预加载所有已配置的 ASR Provider

        【执行流程】
            1. 遍历 SUPPORTED_PROVIDERS 列表
            2. 对于每个有配置的 provider，使用 ASRFactory 创建引擎
            3. 如果引擎可用（is_available() 返回 True），加入 _engines 字典
            4. 加载失败则跳过（不影响其他引擎）
            5. 设置当前引擎：优先使用配置中指定的 provider，否则回退到第一个可用的

        【设计意图】
            一次性加载所有引擎，后续切换时无需重新初始化。
            每个引擎的加载失败都被独立捕获，不影响其他引擎。
        """
        for provider in self.SUPPORTED_PROVIDERS:
            try:
                provider_config = self.config.get(provider, {})
                if provider_config:  # 只加载有配置的 provider（空字典则跳过）
                    # 构造临时 config，让 ASRFactory 知道要创建哪种引擎
                    engine = ASRFactory.create({
                        "provider": provider,
                        provider: provider_config
                    })
                    if engine.is_available():
                        self._engines[provider] = engine
                        print(f"[ASR Manager] 已加载: {provider}")
            except Exception as e:
                print(f"[ASR Manager] 加载 {provider} 失败: {e}")
        
        # 设置当前引擎：优先使用配置指定的 provider
        if self._current_provider in self._engines:
            self._current_engine = self._engines[self._current_provider]
        elif self._engines:
            # 配置指定的 provider 不可用，回退到第一个可用引擎
            self._current_provider = list(self._engines.keys())[0]
            self._current_engine = self._engines[self._current_provider]
    
    def recognize(self, audio_path: str, provider: str = None) -> Optional[str]:
        """
        【核心方法】识别音频（带自动 Fallback）

        【参数说明】
            audio_path (str): 音频文件路径
            provider (str, optional): 指定使用哪个 provider；
                                     为 None 时使用当前 provider

        【返回值】
            Optional[str]: 识别文本；所有引擎都失败时返回 None

        【Fallback 逻辑】
            1. 如果指定了 provider 且与当前不同，先切换
            2. 用当前引擎识别
            3. 如果当前引擎为 None（无可用引擎），遍历其他引擎尝试识别
            4. 第一个成功识别的引擎会成为新的当前引擎
        """
        # 如果指定了 provider 且与当前不同，执行切换
        if provider and provider != self._current_provider:
            self.switch_provider(provider)
        
        # 使用当前引擎识别
        if self._current_engine:
            return self._current_engine.recognize(audio_path)
        
        # 当前引擎不可用，遍历其他引擎作为 Fallback
        for prov, engine in self._engines.items():
            if prov != self._current_provider and engine.is_available():
                print(f"[ASR Manager] Fallback 到 {prov}")
                self._current_provider = prov
                self._current_engine = engine
                return engine.recognize(audio_path)
        
        # 所有引擎都不可用
        return None
    
    def switch_provider(self, provider: str) -> bool:
        """
        【切换方法】动态切换 ASR Provider

        【参数说明】
            provider (str): 目标 provider 名称（如 "funasr"、"whisper"）

        【返回值】
            bool: True 切换成功；False 切换失败（provider 未加载或不可用）

        【切换条件】
            1. provider 必须在 _engines 字典中（已预加载）
            2. provider 对应的引擎 is_available() 必须返回 True
        """
        # 已经是当前 provider，无需切换
        if provider == self._current_provider:
            return True
        
        # 检查 provider 是否已加载
        if provider not in self._engines:
            print(f"[ASR Manager] Provider '{provider}' 未加载")
            return False
        
        # 检查引擎是否可用
        if not self._engines[provider].is_available():
            print(f"[ASR Manager] Provider '{provider}' 不可用")
            return False
        
        # 执行切换
        self._current_provider = provider
        self._current_engine = self._engines[provider]
        print(f"[ASR Manager] 已切换到: {provider}")
        return True
    
    def get_current_provider(self) -> str:
        """获取当前使用的 Provider 名称"""
        return self._current_provider
    
    def get_available_providers(self) -> List[str]:
        """获取所有可用（已加载且 is_available() 为 True）的 Provider 列表"""
        return [p for p, e in self._engines.items() if e.is_available()]
    
    def is_available(self) -> bool:
        """检查当前引擎是否可用（引擎存在且可用）"""
        return self._current_engine is not None and self._current_engine.is_available()


# =====================================================================
# 模块测试入口
# =====================================================================

if __name__ == "__main__":
    # 测试配置：使用 Faster-Whisper 本地引擎
    test_config = {
        "provider": "faster_whisper",
        "faster_whisper": {
            "model_size": "base",      # 使用 base 模型（平衡速度与精度）
            "device": "cuda",           # 使用 GPU
            "compute_type": "float16"   # 半精度推理
        }
    }
    
    # 通过工厂创建引擎
    asr = ASRFactory.create(test_config)
    print(f" ASR引擎创建成功: {type(asr).__name__}")
    print(f"   可用状态: {asr.is_available()}")
