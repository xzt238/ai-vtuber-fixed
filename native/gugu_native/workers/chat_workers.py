import time
import logging
"""
聊天对话 Worker 线程 — StreamChatWorker + TTSWorker + ASRWorker
"""

logger = logging.getLogger(__name__)

import os
from PySide6.QtCore import QThread, Signal, QMutex


class StreamChatWorker(QThread):
    """流式对话线程 — 调用 backend.llm.stream_chat() 并逐 chunk 更新 UI

    支持两种 TTS 模式：
    - streaming_tts=True: 流式分句，检测到句子结束立即发出 sentence_ready 信号
    - streaming_tts=False: 整段合成，等待完整回复后一次性合成 TTS
    """
    chunk_received = Signal(str)
    sentence_ready = Signal(str)
    finished_stream = Signal(dict)
    error = Signal(str)
    tool_call_status = Signal(str)

    _SENTENCE_ENDS = set('。！？.!?')

    def __init__(self, backend, text, history, streaming_tts=False) -> None:
        """内部方法"""
        super().__init__()
        self.backend = backend
        self.text = text
        self.history = history
        self.streaming_tts = streaming_tts
        self._stop_requested = False
        self._mutex = QMutex()
        self._sentence_buffer = ""

    def stop_stream(self) -> None:
        """Stop stream"""
        self._mutex.lock()
        self._stop_requested = True
        self._mutex.unlock()

    def is_stop_requested(self) -> None:
        """Is stop requested"""
        self._mutex.lock()
        val = self._stop_requested
        self._mutex.unlock()
        return val

    def _extract_sentences(self, chunk_text: str) -> None:
        """内部方法"""
        self._mutex.lock()
        try:
            self._sentence_buffer += chunk_text
            sentences = []
            i = 0
            while i < len(self._sentence_buffer):
                if self._sentence_buffer[i] in self._SENTENCE_ENDS:
                    end = i + 1
                    while end < len(self._sentence_buffer) and self._sentence_buffer[end] in self._SENTENCE_ENDS:
                        end += 1
                    sentence = self._sentence_buffer[:end].strip()
                    if sentence:
                        sentences.append(sentence)
                    self._sentence_buffer = self._sentence_buffer[end:]
                    i = 0
                else:
                    i += 1
            return sentences
        finally:
            self._mutex.unlock()

    def _get_and_clear_remaining_buffer(self) -> None:
        """内部方法"""
        self._mutex.lock()
        try:
            remaining = self._sentence_buffer.strip()
            self._sentence_buffer = ""
            return remaining
        finally:
            self._mutex.unlock()

    def run(self) -> None:
        """Run"""
        try:
            full_prompt = self.text  # 记忆由 LLM 内部 MemoryRAGInjector 统一处理

            def on_chunk(chunk_text: str) -> None:
                """On chunk"""
                if self.is_stop_requested():
                    return
                self.chunk_received.emit(chunk_text)
                if self.streaming_tts and chunk_text:
                    sentences = self._extract_sentences(chunk_text)
                    for s in sentences:
                        self.sentence_ready.emit(s)

            def on_tool_call(tool_name: str, display_text: str, tool_args: dict) -> None:
                """On tool call"""
                self.tool_call_status.emit(display_text)

            result = self.backend.llm.stream_chat(
                full_prompt,
                list(self.history),
                callback=on_chunk,
                memory_system=self.backend.memory,
                on_tool_call=on_tool_call
            )

            reply = result.get("text", "")
            action = result.get("action")
            stream_error = result.get("_stream_error")

            if not reply and not stream_error:
                # 带退避的重试：2秒延迟 + 最多1次
                if not hasattr(self, '_retry_count'):
                    self._retry_count = 0
                if self._retry_count < 1:
                    self._retry_count += 1
                    # 分段延迟（总计2秒，每0.5秒检查stop标志）
                    import time
                    for _ in range(4):
                        if self.is_stop_requested():
                            break
                        time.sleep(0.5)
                    if not self.is_stop_requested():
                        result = self.backend.llm.stream_chat(
                            full_prompt,
                            list(self.history),
                            callback=on_chunk,
                            memory_system=self.backend.memory,
                            on_tool_call=on_tool_call
                        )
                        reply = result.get("text", "")
                        action = result.get("action")
                        stream_error = result.get("_stream_error")

            if not reply and stream_error:
                reply = f"LLM 请求失败: {stream_error}"
            elif not reply:
                reply = "（LLM 未返回内容）"

            if action and isinstance(action, dict) and action.get("type") == "execute":
                cmd = action.get("command", "")
                exec_result = self.backend.executor.execute(cmd)
                if exec_result["success"]:
                    output = exec_result.get("stdout", "") or exec_result.get("stderr", "")
                    reply = f"命令执行完成！\n{output}"
                else:
                    reply = f"命令执行失败: {exec_result.get('error', '未知错误')}"

            if "BASH:" in reply or "READ:" in reply or "WRITE:" in reply or "EDIT:" in reply:
                tool_result = self.backend._handle_local_tool(reply)
                if tool_result:
                    reply = f"{reply}\n\n本地工具结果:\n{tool_result}"

            self.backend.record_interaction(self.text, reply)

            if self.streaming_tts:
                remaining = self._get_and_clear_remaining_buffer()
                if remaining:
                    self.sentence_ready.emit(remaining)

            audio_path = None
            if not self.streaming_tts:
                try:
                    audio_path = self.backend.speak(reply)
                except Exception as e:
                    logger.info(f"[StreamChatWorker] TTS 合成失败: {e}")

            self.finished_stream.emit({
                "text": reply,
                "audio_path": audio_path
            })

        except Exception as e:
            if not self.is_stop_requested():
                self.error.emit(str(e))


class TTSWorker(QThread):
    """TTS 合成线程 — 后台调用 backend.speak()，避免阻塞 UI"""
    audio_ready = Signal(str)
    error = Signal(str)

    def __init__(self, backend, text, parent=None) -> None:
        """内部方法"""
        super().__init__(parent)
        self.backend = backend
        self.text = text

    def run(self) -> None:
        """Run"""
        try:
            audio_path = self.backend.speak(self.text)
            if audio_path and os.path.exists(audio_path):
                self.audio_ready.emit(audio_path)
        except Exception as e:
            self.error.emit(str(e))


class ASRWorker(QThread):
    """ASR 识别线程 — 录音结束后调用 backend.asr 识别"""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, backend, audio_path) -> None:
        """内部方法"""
        super().__init__()
        self.backend = backend
        self.audio_path = audio_path

    def run(self) -> None:
        """Run"""
        try:
            text = self.backend.asr.recognize(self.audio_path)
            self.finished.emit(text or "")
        except Exception as e:
            self.error.emit(str(e))
