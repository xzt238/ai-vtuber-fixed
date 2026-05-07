"""
ChatTTS 语音合成引擎

专为对话场景设计的 TTS 引擎，特点是：
- 笑声、停顿自然，适合聊天场景
- 语气词（"嗯~"、"哈哈"）表现力强
- 支持 fine-grained 控制（[laugh]、[uv_break] 等标记）
- 中英文混合效果好

安装: pip install ChatTTS
GPU: 推荐 4GB+ 显存，也支持 CPU（速度较慢）

⚠️ 注意: ChatTTS 采用 CC BY-NC 4.0 许可，**非商业用途**。
    如需商用请使用其他引擎（CosyVoice、Edge TTS）。

作者: 咕咕嘎嘎
日期: 2026-05-06
"""

import os
import time
import tempfile
import threading
from typing import Optional, Dict, Any

from app.tts import TTSEngine


class ChatTTSEngine(TTSEngine):
    """
    ChatTTS 语音合成引擎

    专为 AI 女友场景优化：
    - 笑声和停顿让对话更自然
    - 语气词让 AI 听起来更像真人
    - 开箱即用，无需训练

    使用方式:
        engine = ChatTTSEngine({"device": "cuda"})
        path = engine.speak("你好呀，今天开心吗？")
    """

    # 单例模型（避免重复加载）
    _model = None
    _model_lock = threading.Lock()
    _model_loaded = False

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 ChatTTS 引擎

        Args:
            config: 引擎配置
                - device: 推理设备 ("cuda"/"cpu")，默认 "auto"
                - temperature: 生成温度，默认 0.3
                - top_p: top_p 采样，默认 0.7
                - top_k: top_k 采样，默认 20
                - speaker_id: 说话人 ID（随机种子），默认 None（随机）
        """
        self.config = config
        self.device = config.get("device", "auto")
        self.temperature = config.get("temperature", 0.3)
        self.top_p = config.get("top_p", 0.7)
        self.top_k = config.get("top_k", 20)
        self.speaker_id = config.get("speaker_id", None)

        # 音频输出目录
        self._output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "app", "cache"
        )
        os.makedirs(self._output_dir, exist_ok=True)

        # 预生成说话人嵌入（如果指定了 speaker_id）
        self._spk_emb = None

    def _lazy_load_model(self):
        """延迟加载 ChatTTS 模型（首次使用时加载）"""
        if self._model_loaded:
            return True

        with self._model_lock:
            if self._model_loaded:
                return True

            try:
                import ChatTTS
                print("[ChatTTS] 正在加载模型...")
                self.__class__._model = ChatTTS.Chat()

                # 选择设备
                if self.device == "auto":
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                else:
                    device = self.device

                self._model.load(compile=False, device=device)
                self.__class__._model_loaded = True
                print(f"[ChatTTS] 模型加载完成 (device={device})")

                # 如果指定了 speaker_id，预生成说话人嵌入
                if self.speaker_id is not None:
                    self._spk_emb = self._model.sample_random_speaker(
                        torch.manual_seed(self.speaker_id).seed() if isinstance(self.speaker_id, int)
                        else None
                    )

                return True
            except ImportError:
                print("[ChatTTS] ChatTTS 未安装，请运行: pip install ChatTTS")
                return False
            except Exception as e:
                print(f"[ChatTTS] 模型加载失败: {e}")
                return False

    def speak(self, text: str, output_path: str = None, **kwargs) -> Optional[str]:
        """
        合成语音

        Args:
            text: 要合成的文本
            output_path: 输出路径，None 时自动生成

        Returns:
            音频文件路径，失败时返回 None
        """
        if not text or not text.strip():
            return None

        # 延迟加载模型
        if not self._lazy_load_model():
            return None

        try:
            import torch
            import numpy as np

            # 文本预处理：为 AI 女友场景添加自然标记
            processed_text = self._preprocess_text(text)

            # 生成输出路径
            if not output_path:
                output_path = os.path.join(
                    self._output_dir,
                    f"chattts_{int(time.time()*1000)}.wav"
                )

            # 推理参数
            params = self._model.InferCodeParams(
                temperature=kwargs.get("temperature", self.temperature),
                top_P=kwargs.get("top_p", self.top_p),
                top_K=kwargs.get("top_k", self.top_k),
                spk_emb=self._spk_emb,
            )

            # 合成
            wavs = self._model.infer(processed_text, params_infer_code=params)

            # 保存为 WAV
            if wavs and len(wavs) > 0:
                audio_data = wavs[0]
                if isinstance(audio_data, torch.Tensor):
                    audio_data = audio_data.cpu().numpy()
                if isinstance(audio_data, np.ndarray):
                    audio_data = (audio_data * 32767).astype(np.int16)
                    self._save_wav(audio_data, output_path, sample_rate=24000)
                    return output_path

            print("[ChatTTS] 合成结果为空")
            return None

        except Exception as e:
            print(f"[ChatTTS] 合成失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _preprocess_text(self, text: str) -> str:
        """
        文本预处理 — 为 AI 女友场景添加自然标记

        ChatTTS 支持的特殊标记:
        - [laugh] 笑声
        - [uv_break] 停顿
        - [lbreak] 长停顿
        """
        # 清理 markdown 格式
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # 粗体
        text = re.sub(r'\*(.*?)\*', r'\1', text)       # 斜体
        text = re.sub(r'`(.*?)`', r'\1', text)          # 代码

        # 移除 emoji（ChatTTS 不能处理）
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+', '', text)

        # 在某些关键词前添加笑声标记（让 AI 听起来更活泼）
        laugh_keywords = ['哈哈', '嘻', '嘿嘿', '好耶', '太棒', '爱你', '么么']
        for kw in laugh_keywords:
            if kw in text:
                text = text.replace(kw, f'[laugh]{kw}')
                break  # 只添加一次，避免过度

        # 在逗号/句号前添加自然停顿
        text = text.replace('，', '[uv_break]，')
        text = text.replace('。', '[uv_break]。')

        # 清理多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _save_wav(self, audio_data, output_path: str, sample_rate: int = 24000):
        """保存 numpy 数组为 WAV 文件"""
        import wave
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)          # 单声道
            wf.setsampwidth(2)          # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

    def is_available(self) -> bool:
        """检查 ChatTTS 是否已安装"""
        try:
            import ChatTTS
            return True
        except ImportError:
            return False

    def get_voices(self) -> list:
        """获取可用音色（ChatTTS 用 speaker_id 控制）"""
        return [
            {"id": "random", "name": "随机音色"},
            {"id": "1", "name": "音色 #1 (女声)"},
            {"id": "2", "name": "音色 #2 (女声)"},
            {"id": "3", "name": "音色 #3 (女声)"},
            {"id": "42", "name": "音色 #42 (温柔)"},
        ]

    def stop(self):
        """停止当前播放"""
        super().stop()
