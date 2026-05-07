"""
CosyVoice 语音合成引擎

阿里通义实验室出品的 TTS 引擎，核心优势：
- 音色自然，中文效果优秀
- 支持指令控制语速/情感（开心、伤心、温柔等）
- 支持声音克隆（3s 参考音频）
- Apache 2.0 许可，可商用

部署方式：FastAPI 服务端模式
- 本地启动 CosyVoice 服务: python server.py --port 50000
- 本引擎通过 HTTP API 调用，与 CosyVoice 解耦

对 AI 女友场景来说，CosyVoice 的情感控制是杀手锏：
- 用户开心时 → 指令 "开心" → AI 声音变得轻快
- 用户伤心时 → 指令 "温柔" → AI 声音变温柔
- 日常聊天 → 指令 "自然" → 正常语气

作者: 咕咕嘎嘎
日期: 2026-05-06
"""

import os
import time
import json
from typing import Optional, Dict, Any

from app.tts import TTSEngine


# 情绪 → CosyVoice 指令映射
EMOTION_INSTRUCTION_MAP = {
    "happy": "开心",
    "sad": "伤心",
    "angry": "愤怒",
    "surprised": "惊讶",
    "shy": "害羞",
    "love": "温柔",
    "neutral": "自然",
    "default": "自然",
}


class CosyVoiceEngine(TTSEngine):
    """
    CosyVoice 语音合成引擎（FastAPI 服务端模式）

    通过 HTTP API 与 CosyVoice 服务端通信，支持：
    - 流式合成（SSE）
    - 情感控制（指令模式）
    - 声音克隆（参考音频模式）
    - 多说话人选择

    使用前提：
    1. 安装 CosyVoice: pip install cosyvoice
    2. 启动服务端: python cosyvoice/server.py --port 50000
    3. 配置 server_url 指向服务地址

    配置示例 (config.yaml):
        tts:
          provider: cosyvoice
          cosyvoice:
            server_url: "http://127.0.0.1:50000"
            mode: "instruction"     # instruction / clone / cross_lingual
            speaker_id: "中文女"
            emotion: "自然"
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 CosyVoice 引擎

        Args:
            config: 引擎配置
                - server_url: CosyVoice 服务端地址，默认 "http://127.0.0.1:50000"
                - mode: 合成模式 ("instruction"/"clone"/"cross_lingual")
                - speaker_id: 说话人名称
                - emotion: 默认情感指令
                - reference_audio: 参考音频路径（clone 模式）
                - reference_text: 参考音频对应文本（clone 模式）
        """
        self.config = config
        self.server_url = config.get("server_url", "http://127.0.0.1:50000").rstrip("/")
        self.mode = config.get("mode", "instruction")
        self.speaker_id = config.get("speaker_id", "中文女")
        self.default_emotion = config.get("emotion", "自然")
        self.reference_audio = config.get("reference_audio", None)
        self.reference_text = config.get("reference_text", None)

        # 音频输出目录
        self._output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "app", "cache"
        )
        os.makedirs(self._output_dir, exist_ok=True)

        # HTTP 会话
        self._session = None

    def _get_session(self):
        """获取 HTTP 会话（延迟创建）"""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({"Content-Type": "application/json"})
        return self._session

    def speak(self, text: str, output_path: str = None, emotion: str = None, **kwargs) -> Optional[str]:
        """
        合成语音

        Args:
            text: 要合成的文本
            output_path: 输出路径，None 时自动生成
            emotion: 情感指令（覆盖默认值），如 "happy"/"sad"/"love"

        Returns:
            音频文件路径，失败时返回 None
        """
        if not text or not text.strip():
            return None

        try:
            session = self._get_session()

            # 生成输出路径
            if not output_path:
                output_path = os.path.join(
                    self._output_dir,
                    f"cosyvoice_{int(time.time()*1000)}.wav"
                )

            # 清理文本
            import re
            clean_text = re.sub(r'[\*\`#]', '', text)  # 移除 markdown 符号
            clean_text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]+', '', clean_text)
            clean_text = clean_text.strip()

            if not clean_text:
                return None

            # 根据模式构建请求
            if self.mode == "clone" and self.reference_audio:
                # 声音克隆模式
                payload = {
                    "mode": "clone",
                    "text": clean_text,
                    "reference_audio": self.reference_audio,
                    "reference_text": self.reference_text or "",
                }
            elif self.mode == "cross_lingual" and self.reference_audio:
                # 跨语言克隆模式
                payload = {
                    "mode": "cross_lingual",
                    "text": clean_text,
                    "reference_audio": self.reference_audio,
                }
            else:
                # 指令模式（默认）— 支持情感控制
                emotion_instruction = self.default_emotion
                if emotion and emotion in EMOTION_INSTRUCTION_MAP:
                    emotion_instruction = EMOTION_INSTRUCTION_MAP[emotion]
                elif kwargs.get("emotion"):
                    em = kwargs["emotion"]
                    if em in EMOTION_INSTRUCTION_MAP:
                        emotion_instruction = EMOTION_INSTRUCTION_MAP[em]

                payload = {
                    "mode": "instruction",
                    "text": clean_text,
                    "speaker_id": self.speaker_id,
                    "instruction": emotion_instruction,
                }

            # 调用 CosyVoice API
            response = session.post(
                f"{self.server_url}/api/tts",
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                # 检查响应类型
                content_type = response.headers.get("content-type", "")
                if "audio" in content_type or "octet-stream" in content_type:
                    # 直接返回音频数据
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                elif "json" in content_type:
                    # JSON 格式响应
                    result = response.json()
                    if result.get("audio_path"):
                        # 服务端返回的音频路径
                        import shutil
                        src = result["audio_path"]
                        if os.path.exists(src) and src != output_path:
                            shutil.copy2(src, output_path)
                        return output_path
                    elif result.get("audio_base64"):
                        # Base64 编码的音频
                        import base64
                        audio_bytes = base64.b64decode(result["audio_base64"])
                        with open(output_path, 'wb') as f:
                            f.write(audio_bytes)
                        return output_path
            else:
                print(f"[CosyVoice] API 错误: {response.status_code} {response.text[:200]}")
                return None

        except Exception as e:
            print(f"[CosyVoice] 合成失败: {e}")
            return None

    def speak_with_emotion(self, text: str, emotion: str = "neutral", output_path: str = None) -> Optional[str]:
        """
        带情感合成的便捷方法

        Args:
            text: 文本
            emotion: 情绪类型
            output_path: 输出路径

        Returns:
            音频文件路径
        """
        return self.speak(text, output_path=output_path, emotion=emotion)

    def is_available(self) -> bool:
        """检查 CosyVoice 服务端是否可用"""
        try:
            session = self._get_session()
            response = session.get(f"{self.server_url}/api/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_voices(self) -> list:
        """获取可用说话人列表"""
        try:
            session = self._get_session()
            response = session.get(f"{self.server_url}/api/speakers", timeout=5)
            if response.status_code == 200:
                return response.json().get("speakers", [])
        except Exception:
            pass
        # 默认列表
        return [
            {"id": "中文女", "name": "中文女声 (默认)"},
            {"id": "中文男", "name": "中文男声"},
            {"id": "日语男", "name": "日语男声"},
            {"id": "粤语女", "name": "粤语女声"},
            {"id": "英文女", "name": "英文女声"},
            {"id": "英文男", "name": "英文男声"},
        ]

    def stop(self):
        """停止当前播放"""
        super().stop()
