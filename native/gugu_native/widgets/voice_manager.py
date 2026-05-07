"""
实时语音管理器 — sounddevice + Silero VAD

功能:
- 实时麦克风输入
- Silero VAD 语音活动检测（Python ONNX Runtime 版）
- 自动分段：检测到语音开始/结束
- 语音段发送给后端 ASR 识别（异步 QThread，不阻塞录音）
- 静音超时自动结束当前语音段

v1.9.78: ASR 识别移到独立 QThread，不再阻塞录音线程和主线程
         stop_listening() 不再同步调用 ASR，消除关闭延迟
         backend 属性移除不必要的 main-thread guard
"""

import os
import io
import time
import wave
import tempfile
import threading
from PySide6.QtCore import QObject, Signal, Slot, QThread


class _ASRWorker(QThread):
    """ASR 识别工作线程 — 在独立线程中调用后端 ASR，不阻塞录音/主线程

    v1.9.78: 新增，解决 ASR 阻塞录音线程和 stop_listening() 阻塞 UI 的问题
    """
    result_ready = Signal(str)       # 识别成功
    error_occurred = Signal(str)     # 识别失败

    def __init__(self, backend, wav_path, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._wav_path = wav_path

    def run(self):
        try:
            if self._backend and hasattr(self._backend, 'asr'):
                text = self._backend.asr.recognize(self._wav_path)
                if text:
                    # FunASR 输出中文字间会加空格,需要去除
                    text = text.replace(" ", "").strip()
                    self.result_ready.emit(text)
            else:
                self.error_occurred.emit("后端未初始化，无法识别语音")
        except Exception as e:
            self.error_occurred.emit(f"ASR 识别失败: {e}")
        finally:
            # 清理临时文件
            try:
                os.unlink(self._wav_path)
            except Exception:
                pass


class RealtimeVoiceManager(QObject):
    """
    实时语音管理器

    信号:
        speech_recognized(text): ASR 识别结果
        vad_state_changed(is_speaking): 语音活动状态变化
        error_occurred(error_msg): 错误
        listening_changed(is_listening): 监听状态变化

    v1.9.78: 移除 audio_data_ready 信号（频谱可视化已移除）
    """

    speech_recognized = Signal(str)          # 识别文本
    vad_state_changed = Signal(bool)         # is_speaking
    error_occurred = Signal(str)             # error message
    listening_changed = Signal(bool)         # is_listening

    def __init__(self, backend=None, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._is_listening = False
        self._sample_rate = 16000
        self._channels = 1
        self._frame_size = 512  # Silero VAD 推荐 512 for 16kHz

        # Silero VAD 模型
        self._vad_model = None
        self._vad_ready = False

        # 录音状态
        self._audio_buffer = []
        self._is_speaking = False
        self._silence_start = None
        self._silence_timeout = 1.5  # 静音 1.5 秒自动结束

        # VAD 阈值
        self._speech_threshold = 0.5
        self._silence_threshold = 0.3

        # 线程控制
        self._stop_event = threading.Event()
        self._thread = None
        self._buffer_lock = threading.Lock()  # v1.9.73: 保护 _audio_buffer 和 _is_speaking

        # v1.9.78: ASR 工作线程追踪
        self._asr_workers = []

    def cleanup(self):
        """清理资源 — 供 PerformanceManager 调用

        注意: 只清理临时缓冲区，不销毁 backend/VAD 等长期资源
        否则 force_cleanup 会导致语音功能永久失效
        """
        self.stop_listening()
        self._audio_buffer = []
        # 等待所有 ASR 工作线程结束
        for worker in self._asr_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)
        self._asr_workers.clear()
        print("[VoiceManager] cleanup completed")

    @property
    def backend(self):
        # v1.9.78: 直接返回 _backend，移除 main-thread guard
        # 理由: backend 由 setter 设置（main.py 中 main_window.voice_manager.backend = self._backend），
        # 一旦设置就不会为 None。ASR 工作线程通过 _backend 直接访问，不需要 Qt widget 查找。
        # 如果 _backend 确实为 None（backend 尚未初始化），ASR worker 会发出 "后端未初始化" 错误。
        return self._backend

    @backend.setter
    def backend(self, value):
        self._backend = value

    @property
    def is_listening(self):
        return self._is_listening

    def _init_vad(self):
        """初始化 Silero VAD 模型"""
        if self._vad_ready:
            return True

        try:
            import torch
            # 尝试加载 Silero VAD 模型
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                trust_repo=True
            )
            self._vad_model = model
            self._vad_ready = True
            print("[VoiceManager] Silero VAD 加载成功")
            return True
        except ImportError:
            print("[VoiceManager] PyTorch 未安装，使用能量检测 VAD")
            self._vad_ready = False
            return False
        except Exception as e:
            print(f"[VoiceManager] Silero VAD 加载失败: {e}，使用能量检测 VAD")
            self._vad_ready = False
            return False

    def _detect_speech_energy(self, audio_chunk):
        """能量检测 VAD（降级方案，不依赖 Silero）"""
        try:
            import numpy as np
            if isinstance(audio_chunk, bytes):
                data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                data = np.array(audio_chunk, dtype=np.float32)

            rms = float(np.sqrt(np.mean(data ** 2)))
            return min(rms * 10.0, 1.0)  # 归一化到 0-1
        except Exception:
            return 0.0

    def _detect_speech_silero(self, audio_chunk):
        """Silero VAD 检测"""
        if not self._vad_ready or self._vad_model is None:
            return self._detect_speech_energy(audio_chunk)

        try:
            import torch
            if isinstance(audio_chunk, bytes):
                import numpy as np
                data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                data = np.array(audio_chunk, dtype=np.float32)

            audio_tensor = torch.from_numpy(data).unsqueeze(0)

            with torch.no_grad():
                speech_prob = self._vad_model(audio_tensor, self._sample_rate).item()

            return speech_prob
        except Exception:
            return self._detect_speech_energy(audio_chunk)

    def start_listening(self):
        """开始实时监听"""
        if self._is_listening:
            return

        # v1.9.78: 检查 backend 可用性
        if self._backend is None:
            self.error_occurred.emit("后端尚未初始化，请稍后再试")
            return

        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            self.error_occurred.emit("需要 sounddevice 和 numpy: pip install sounddevice numpy")
            return

        self._is_listening = True
        self._stop_event.clear()
        self.listening_changed.emit(True)

        # v1.9.73: VAD 初始化移到录音线程中执行
        # 原因: torch.hub.load() 在主线程会阻塞 Qt 事件循环
        # 且 import torch 如果 CUDA 不匹配可能触发原生 segfault 直接闪退
        # 在子线程中初始化，失败则降级到能量检测 VAD

        # 启动录音线程
        self._thread = threading.Thread(target=self._recording_loop, daemon=True)
        self._thread.start()

    def stop_listening(self):
        """停止实时监听

        v1.9.78: 不再同步调用 _finalize_speech_segment()
        只设置停止标志，让录音线程自行退出并处理剩余音频
        这消除了 stop_listening() 阻塞 UI 的问题
        """
        if not self._is_listening:
            return

        self._is_listening = False
        self._stop_event.set()
        self.listening_changed.emit(False)

        # v1.9.78: 不再在这里同步调用 _finalize_speech_segment()
        # 录音线程退出时会自动处理剩余音频（异步 ASR）
        # 只等待线程结束，timeout 缩短（不再有 ASR 阻塞）
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _recording_loop(self):
        """录音主循环"""
        import sounddevice as sd
        import numpy as np

        # v1.9.73: 在录音线程中初始化 VAD（避免主线程阻塞/闪退）
        self._init_vad()

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype='int16',
                blocksize=self._frame_size,
            ) as stream:
                print("[VoiceManager] 实时监听已启动")

                while not self._stop_event.is_set():
                    try:
                        data, overflowed = stream.read(self._frame_size)
                        if overflowed:
                            print("[VoiceManager] 音频缓冲区溢出")

                        # 转为 float32 用于 VAD
                        audio_float = data.flatten().astype(np.float32) / 32768.0

                        # VAD 检测
                        speech_prob = self._detect_speech_silero(audio_float)
                        is_speech = speech_prob > self._speech_threshold

                        if is_speech:
                            if not self._is_speaking:
                                # 开始说话
                                with self._buffer_lock:
                                    self._is_speaking = True
                                self._silence_start = None
                                self.vad_state_changed.emit(True)

                            # 累积音频数据
                            with self._buffer_lock:
                                self._audio_buffer.append(data.copy())

                        elif self._is_speaking:
                            # 说话中但当前帧静音
                            with self._buffer_lock:
                                self._audio_buffer.append(data.copy())

                            if self._silence_start is None:
                                self._silence_start = time.time()
                            elif time.time() - self._silence_start > self._silence_timeout:
                                # 静音超时，结束当前语音段
                                self._finalize_speech_segment()

                    except Exception as e:
                        if not self._stop_event.is_set():
                            print(f"[VoiceManager] 录音错误: {e}")
                        break

        except Exception as e:
            self.error_occurred.emit(f"录音启动失败: {e}")
            self._is_listening = False
            self.listening_changed.emit(False)
            return

        # v1.9.78: 录音循环结束后，处理剩余的语音段
        # 这是 stop_listening() 不再同步处理的主要原因
        if self._is_speaking and self._audio_buffer:
            self._finalize_speech_segment()

        print("[VoiceManager] 实时监听已停止")

    def _finalize_speech_segment(self):
        """结束当前语音段，异步启动 ASR 识别

        v1.9.78: 不再同步调用 backend.asr.recognize()
        改为写入临时 WAV 文件后启动 _ASRWorker QThread
        这样录音线程可以立即继续录音，ASR 在独立线程运行
        """
        # 先在锁内提取数据，再在锁外发射信号（避免持锁发信号导致死锁）
        audio_data = None
        merge_error = None
        with self._buffer_lock:
            self._is_speaking = False
            should_emit_vad = True

            if not self._audio_buffer:
                self._audio_buffer = []
                # 先释放锁再发信号
            else:
                try:
                    import numpy as np
                    audio_data = np.concatenate(self._audio_buffer, axis=0)
                    self._audio_buffer = []
                except Exception as e:
                    self._audio_buffer = []
                    merge_error = f"音频合并失败: {e}"

        # 在锁外发射信号（避免 Qt 信号回调中再次获取锁导致死锁）
        if should_emit_vad:
            self.vad_state_changed.emit(False)
        if merge_error:
            self.error_occurred.emit(merge_error)
            return
        if audio_data is None:
            return

        # 以下操作不需要锁（audio_data 是局部变量）
        try:
            # 过滤太短的语音段
            duration = len(audio_data) / self._sample_rate
            if duration < 0.5:
                return

            # 保存为临时 WAV 文件
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_path = tmp.name
            tmp.close()

            with wave.open(tmp_path, 'wb') as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self._sample_rate)
                wf.writeframes(audio_data.tobytes())

            # v1.9.78: 异步 ASR — 启动独立 QThread，不阻塞当前线程
            worker = _ASRWorker(self._backend, tmp_path)
            worker.result_ready.connect(self._on_asr_result)
            worker.error_occurred.connect(self.error_occurred.emit)
            worker.finished.connect(lambda: self._cleanup_asr_worker(worker))
            self._asr_workers.append(worker)
            worker.start()

        except Exception as e:
            self.error_occurred.emit(f"语音段处理失败: {e}")

    def _on_asr_result(self, text: str):
        """ASR 识别完成回调 — 转发识别结果"""
        if text:
            self.speech_recognized.emit(text)

    def _cleanup_asr_worker(self, worker):
        """清理已完成的 ASR 工作线程"""
        try:
            if worker in self._asr_workers:
                self._asr_workers.remove(worker)
        except Exception:
            pass
