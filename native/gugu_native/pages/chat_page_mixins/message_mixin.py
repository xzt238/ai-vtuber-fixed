"""
ChatPage 消息处理 Mixin

包含消息发送、流式对话、搜索、消息操作相关的功能。
"""

import os
import logging
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from qfluentwidgets import FluentIcon

from gugu_native.workers.chat_workers import StreamChatWorker

logger = logging.getLogger('ChatPage.Message')


class ChatPageMessageMixin:
    """消息处理 Mixin"""

    def _send_message(self, text: str = "") -> None:
        """发送消息"""
        if self._is_streaming:
            return

        if isinstance(text, bool):
            text = ""

        text = text or self.input_field.text()

        # 处理待发送的图片（OCR/视觉理解）
        if self._pending_image:
            text = self._process_pending_image(text)
            if not text:
                return

        if not text:
            return
        if not self.backend:
            self.append_message_safe("system", "后端未初始化，请先在设置页面配置 API Key")
            return

        # TTS 预热懒加载 — 首次对话时触发预热
        if not getattr(self, '_tts_prewarmed', True):
            self._tts_prewarmed = True
            main_window = self.window()
            if main_window and hasattr(main_window, '_prewarm_tts'):
                import threading
                threading.Thread(target=main_window._prewarm_tts, daemon=True).start()
                logger.info("TTS prewarm triggered by first conversation")

        # 获取引用文本
        quote = self.input_field.quote_text
        if quote:
            if self._chat_display_ready and self.chat_display:
                self.chat_display.append_user_msg(text, quote=quote)
            else:
                self._pending_chat_messages.append(("user", text, None))
            if quote:
                text = f"[引用: {quote}]\n{text}"
            self.input_field.clear_quote()
        else:
            self.append_message_safe("user", text)

        # 记录用户消息到历史
        self._record_message("user", text)

        self.input_field.clear()
        self._set_streaming_state(True)
        self._current_ai_text = ""

        # 重置流式 TTS 排序状态
        self._tts_seq_counter = 0
        self._tts_next_play_seq = 1
        self._tts_pending.clear()

        # 添加正在思考占位
        if self._chat_display_ready and self.chat_display:
            self.chat_display.start_streaming()

        # 获取对话历史
        history = list(self.backend.history) if hasattr(self.backend, 'history') else []

        # 启动流式对话线程
        streaming_tts = self.tts_mode_btn.isChecked()
        worker = StreamChatWorker(self.backend, text, history, streaming_tts=streaming_tts)
        self._worker = worker
        self._active_worker_id = id(worker)
        worker.chunk_received.connect(self._on_chunk)
        worker.sentence_ready.connect(self._on_sentence_ready)
        worker.finished_stream.connect(self._on_stream_finished)
        worker.error.connect(self._on_error)
        worker.tool_call_status.connect(self._on_tool_call_status)
        worker.start()

    def _stop_streaming(self) -> None:
        """停止流式对话"""
        if self._worker and self._is_streaming:
            self._worker.stop_stream()
            # 终结当前流式消息占位
            if self._current_ai_text:
                self.chat_display.finish_streaming(self._current_ai_text)
                self._record_message("assistant", self._current_ai_text)
            else:
                self.chat_display.finish_streaming("(已停止)")
            self.chat_display.append_system_msg("已停止生成")
            self._current_ai_text = ""
            self._set_streaming_state(False)
            # 清空音频队列和等待中的 TTS Worker
            self._audio_queue.clear()
            self._tts_pending.clear()
            self._tts_next_play_seq = 1
            self._tts_seq_counter = 0
            for w in self._tts_workers:
                if w.isRunning():
                    w.quit()
                    w.wait(500)
            self._tts_workers.clear()

    def _on_send_or_stop(self) -> None:
        """发送/停止按钮点击——根据当前状态路由"""
        if self._is_streaming:
            self._stop_streaming()
        else:
            self._send_message()

    def _set_streaming_state(self, streaming: bool) -> None:
        """流式状态切换"""
        self._is_streaming = streaming
        if streaming:
            self.send_btn.setText(" 停止")
            self.send_btn.setIcon(FluentIcon.CANCEL)
            self.send_btn.setStyleSheet(self._stop_style)
        else:
            self.send_btn.setText(" 发送")
            self.send_btn.setIcon(FluentIcon.SEND)
            self.send_btn.setStyleSheet(self._send_style)
        self.input_field.setEnabled(not streaming)

    @Slot(str)
    def _on_tool_call_status(self, display_text: str) -> None:
        """FC 工具调用状态提示"""
        self.chat_display.append_system_msg(display_text)

    @Slot(str)
    def _on_chunk(self, chunk_text: str) -> None:
        """收到流式文本片段"""
        self._current_ai_text += chunk_text
        self.chat_display.update_streaming(self._current_ai_text)

    @Slot(str)
    def _on_sentence_ready(self, sentence: str) -> None:
        """流式 TTS：检测到完整句子，在后台线程合成音频"""
        if not sentence or not self.backend:
            return
        self._tts_seq_counter += 1
        seq = self._tts_seq_counter

        def _tts_task(text, seq_num) -> None:
            try:
                audio_path = self.backend.speak(text)
                if audio_path and os.path.exists(audio_path):
                    self._tts_audio_signal.emit(audio_path, seq_num)
            except Exception as e:
                logger.error(f"Streaming TTS sentence failed: {e}")

        self._tts_executor.submit(_tts_task, sentence, seq)

    @Slot(dict)
    def _on_stream_finished(self, result: dict) -> None:
        """流式对话完成"""
        if not self._is_streaming:
            return

        sender = self.sender()
        if sender is not None and sender is not self._worker:
            return

        reply_text = result.get("text", "")
        if reply_text and reply_text != self._current_ai_text:
            self._current_ai_text = reply_text

        # 完成流式
        self.chat_display.finish_streaming(self._current_ai_text or "(无回复)")

        # FC UI 指令处理
        ui_actions = result.get("_ui_actions", [])
        for action in ui_actions:
            if action.get("type") == "change_expression" and self._animation_controller:
                emotion = action.get("emotion", "neutral")
                self._animation_controller.trigger_emotion(emotion, lock_duration=5.0)
                logger.info(f"FC expression command: {emotion}")

        # 自动表情检测
        if reply_text and not any(a.get("type") == "change_expression" for a in ui_actions):
            if self._animation_controller:
                self._animation_controller.trigger_emotion_from_text(reply_text)

        # 播放 TTS 音频
        audio_path = result.get("audio_path")
        is_streaming_tts = self._worker and getattr(self._worker, 'streaming_tts', False)
        if audio_path and os.path.exists(audio_path) and not is_streaming_tts:
            self._play_audio(audio_path)

        # 记录消息
        self._record_message("assistant", self._current_ai_text or reply_text)

        self._current_ai_text = ""
        self._set_streaming_state(False)
        self._save_chat_history()

    @Slot(str)
    def _on_error(self, error_msg: str) -> None:
        """处理错误"""
        self.chat_display.append_system_msg(f"错误: {error_msg}")
        self._current_ai_text = ""
        self._set_streaming_state(False)

    # ========== 消息操作回调 ==========

    def _on_action_copy(self, text: str) -> None:
        """复制消息"""
        QApplication.clipboard().setText(text)

    def _on_action_retry(self, msg_id: str) -> None:
        """重试（重新生成最后一条 AI 回复）"""
        if self._is_streaming:
            return
        last_user_msg = None
        for msg in reversed(self._chat_messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        if last_user_msg and self.backend:
            self.chat_display.append_system_msg("重新生成...")
            self.input_field.setText(last_user_msg)
            self._send_message()

    def _on_action_quote(self, text: str) -> None:
        """引用消息"""
        self._pending_quote = text
        self.input_field.set_quote(text)
        self.input_field.setFocus()

    def _on_action_edit(self, msg_id: str, text: str) -> None:
        """编辑重发"""
        self.input_field.setText(text)
        self.input_field.setFocus()

    def _toggle_search(self) -> None:
        """切换搜索栏"""
        self.search_bar.show_search()

    def _on_search(self, keyword: str) -> None:
        """搜索消息"""
        if not keyword:
            return
        results = []
        for i, msg in enumerate(self._chat_messages):
            if keyword.lower() in msg.get("content", "").lower():
                results.append(i)
        self.search_bar.set_results(results)

    def _on_search_navigate(self, index: int) -> None:
        """搜索结果导航"""
        if 0 <= index < len(self._chat_messages):
            self.chat_display.scroll_to_message(index)
