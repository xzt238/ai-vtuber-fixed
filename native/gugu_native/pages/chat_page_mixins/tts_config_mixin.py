"""
ChatPage TTS 配置 Mixin

包含 TTS 引擎切换、音色配置、对话历史持久化相关的功能。
"""

import os
import json
import logging
from typing import Optional
from datetime import datetime

from PySide6.QtCore import Slot

from gugu_native.workers.chat_workers import TTSWorker
from gugu_native.utils.path_utils import get_history_path, get_tts_prefs_path, path_exists

logger = logging.getLogger('ChatPage.TTSConfig')


class ChatPageTTSConfigMixin:
    """TTS 配置 Mixin"""

    def _populate_edge_voices_chat(self) -> None:
        """填充 Edge TTS 音色列表"""
        from app.shared_config import EDGE_VOICES
        self.voice_combo.clear()
        for voice_id, label in EDGE_VOICES:
            self.voice_combo.addItem(f"{label}", userData=voice_id)

    def _populate_gptsovits_voices_chat(self) -> None:
        """填充 GPT-SoVITS 音色列表"""
        self.voice_combo.clear()
        if not self.backend:
            self.voice_combo.addItem("默认音色", userData="default")
            return
        try:
            tts = self.backend.tts
            if tts and hasattr(tts, 'get_voices'):
                voices = tts.get_voices()
                if voices:
                    for v in voices:
                        if isinstance(v, dict):
                            value = str(v.get('value', v.get('name', '')))
                            label = str(v.get('label', value))
                            self.voice_combo.addItem(label, userData=value)
                        else:
                            self.voice_combo.addItem(str(v), userData=str(v))
                    return
        except Exception as e:
            logger.error(f"Failed to get GPT-SoVITS voices: {e}")
        self.voice_combo.addItem("默认音色", userData="default")

    def _on_tts_engine_changed_chat(self, index: int) -> None:
        """Chat 页 TTS 引擎切换"""
        engine = self.tts_combo.currentText()
        if engine == "Edge TTS":
            self._populate_edge_voices_chat()
        elif engine == "GPT-SoVITS":
            self._populate_gptsovits_voices_chat()
        self._apply_tts_to_backend()

    def _on_voice_changed_chat(self, index: int) -> None:
        """Chat 页音色切换"""
        self._apply_tts_to_backend()

    def _on_speed_changed(self, value: int) -> None:
        """TTS 速度滑块变更"""
        speed = value / 100.0
        if self.backend:
            tts_section = self.backend.config.config.setdefault("tts", {})
            provider = tts_section.get("provider", "edge")
            sub = tts_section.setdefault(provider, {})
            sub["speed"] = speed
            if hasattr(self.backend, 'tts') and self.backend.tts:
                if hasattr(self.backend.tts, 'set_speed'):
                    self.backend.tts.set_speed(speed)

    def _on_volume_changed(self, value: int) -> None:
        """TTS 音量滑块变更"""
        volume = value / 100.0
        self._audio_output.setVolume(min(volume, 1.0))

    def _on_tts_mode_toggled(self, checked: bool) -> None:
        """TTS 流式/整段模式切换"""
        if checked:
            self.tts_mode_btn.setText("流式")
        else:
            self.tts_mode_btn.setText("整段")

    def _get_voice_id_chat(self) -> str:
        """获取当前选中音色 ID"""
        idx = self.voice_combo.currentIndex()
        if idx >= 0:
            user_data = self.voice_combo.itemData(idx)
            if user_data:
                return str(user_data)
        return self.voice_combo.currentText()

    def _apply_tts_to_backend(self) -> None:
        """将当前 TTS 选择应用到后端 — 使用线程安全的 rebuild_tts()"""
        if not self.backend:
            return
        engine = self.tts_combo.currentText()
        voice_id = self._get_voice_id_chat()
        provider_map = {"Edge TTS": "edge", "GPT-SoVITS": "gptsovits"}
        provider = provider_map.get(engine, "edge")

        tts_section = self.backend.config.config.setdefault("tts", {})
        tts_section["provider"] = provider
        if voice_id:
            sub = tts_section.setdefault(provider, {})
            sub["voice"] = voice_id
            if provider == "gptsovits":
                sub["project"] = voice_id

        # 使用线程安全的重建方法
        self.backend.rebuild_tts()

        # GPT-SoVITS 项目设置
        if provider == "gptsovits" and hasattr(self.backend.tts, 'set_project'):
            self.backend.tts.set_project(voice_id)

        # 持久化
        try:
            tts_prefs = {"engine": engine, "provider": provider, "voice": voice_id}
            prefs_file = get_tts_prefs_path()
            with open(prefs_file, "w", encoding="utf-8") as f:
                json.dump(tts_prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"TTS preferences save failed: {e}")

    def sync_tts_from_settings(self, engine: str, voice_id: str) -> None:
        """从设置页同步 TTS 配置到 Chat 页"""
        self.tts_combo.blockSignals(True)
        self.voice_combo.blockSignals(True)

        idx = self.tts_combo.findText(engine)
        if idx >= 0:
            self.tts_combo.setCurrentIndex(idx)

        if engine == "Edge TTS":
            self._populate_edge_voices_chat()
        elif engine == "GPT-SoVITS":
            self._populate_gptsovits_voices_chat()

        for i in range(self.voice_combo.count()):
            if str(self.voice_combo.itemData(i) or "") == voice_id:
                self.voice_combo.setCurrentIndex(i)
                break

        self.tts_combo.blockSignals(False)
        self.voice_combo.blockSignals(False)

    # ========== 对话历史持久化 ==========

    def _get_history_path(self) -> None:
        """获取对话历史文件路径"""
        return get_history_path()

    def _save_chat_history(self) -> None:
        """保存对话历史到 JSON"""
        try:
            messages = getattr(self, '_chat_messages', [])
            if not messages:
                return
            messages = messages[-200:]
            # 为缺少 time 的旧消息补充时间戳
            for m in messages:
                if not m.get('time'):
                    m['time'] = datetime.now().isoformat()
            with open(self._get_history_path(), "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def _load_chat_history(self) -> None:
        """加载对话历史（仅渲染最近20条，完整历史保存在 _chat_messages 中供 LLM 上下文使用）"""
        if not self.chat_display:
            return
        try:
            path = self._get_history_path()
            if not path_exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                messages = json.load(f)
            # 完整历史保存供 LLM 上下文使用
            self._chat_messages = messages[-100:]
            # 仅渲染最近20条到 UI
            display_messages = self._chat_messages[-20:]
            for msg in display_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                time_str = msg.get("time", "")
                if role == "user":
                    self.chat_display.append_user_msg(content, timestamp=time_str)
                elif role == "assistant":
                    self.chat_display.append_ai_msg(content, timestamp=time_str)
        except Exception as e:
            pass

    def clear_chat(self) -> None:
        """清空对话"""
        if self.chat_display:
            self.chat_display.clear()
        self._chat_messages = []
        self._save_chat_history()

    # ========== 主动说话回调 ==========

    def _on_proactive_speech(self, text: str) -> None:
        """处理 AI 主动说话回调"""
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self,
            "_handle_proactive_speech",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text)
        )

    @Slot(str)
    def _handle_proactive_speech(self, text: str) -> None:
        """在 UI 线程中处理主动说话（TTS 合成在后台线程）"""
        if not text:
            return

        if self._chat_display_ready and self.chat_display:
            self.chat_display.append_system_msg("AI 主动说话")
            self.chat_display.append_ai_msg(text)
        else:
            self._pending_chat_messages.append(("system", "AI 主动说话", None))
            self._pending_chat_messages.append(("assistant", text, None))
        self._record_message("assistant", text)

        # 统一通过 AnimationController 检测情绪
        if self._animation_controller:
            self._animation_controller.trigger_emotion_from_text(text)

        if self.backend:
            worker = TTSWorker(self.backend, text, parent=self)
            worker.audio_ready.connect(self._on_tts_audio_ready)
            worker.error.connect(lambda e: logger.error(f"Proactive speech TTS failed: {e}"))
            worker.finished.connect(lambda: self._cleanup_tts_worker(worker))
            self._tts_workers.append(worker)
            worker.start()

        self._save_chat_history()
