"""
ChatPage 音频 Mixin

包含 TTS 播放、口型同步、录音、ASR、实时语音相关的功能。
"""

import os
import random
import logging
from typing import Optional

from PySide6.QtCore import QTimer, QUrl, Slot
from PySide6.QtMultimedia import QMediaPlayer

logger = logging.getLogger('ChatPage.Audio')


class ChatPageAudioMixin:
    """音频处理 Mixin"""

    def _on_tts_audio_ready(self, audio_path: str, seq: int = 0):
        """TTS 合成完成回调 — 统一排队，不中断当前播放

        排序缓冲区机制（seq > 0 时生效）：
        - TTS 句子可能乱序完成（并行合成），用 seq 序号保证播放顺序
        - 新音频先入 _tts_pending 缓冲区，按序释放到 _audio_queue
        - 播放决策统一由 _try_play_next() 处理，避免竞态条件
        """
        if not audio_path or not os.path.exists(audio_path):
            return

        # 流式 TTS：先入排序缓冲区
        if seq > 0:
            self._tts_pending[seq] = audio_path
        else:
            # 非流式（主动说话等）：直接排队
            if audio_path not in self._audio_queue:
                self._audio_queue.append(audio_path)

        # 尝试释放连续的排序序号并播放
        self._try_play_next()

    def _try_play_next(self):
        """统一的播放调度 — 释放排序缓冲区 + 播放下一首

        所有播放决策集中在此方法，避免多处重复释放导致竞态条件。
        """
        # 1. 释放所有连续的排序序号到播放队列
        while self._tts_next_play_seq in self._tts_pending:
            na = self._tts_pending.pop(self._tts_next_play_seq)
            self._tts_next_play_seq += 1
            if na not in self._audio_queue:
                self._audio_queue.append(na)

        # 2. 检查是否正在播放（用标志位而非 QMediaPlayer 实时状态）
        if self._is_audio_playing():
            return  # 正在播放，等 _on_playback_state_changed 回调时再调度

        # 3. 空闲状态：播放队列头
        if self._audio_queue:
            next_audio = self._audio_queue.pop(0)
            if os.path.exists(next_audio):
                self._play_audio(next_audio)

    def _is_audio_playing(self) -> bool:
        """检查音频是否正在播放（比直接检查 QMediaPlayer 更可靠）"""
        if not self._media_player:
            return False
        state = self._media_player.playbackState()
        return state == QMediaPlayer.PlaybackState.PlayingState

    def _cleanup_tts_worker(self, worker):
        """清理已完成的 TTSWorker"""
        try:
            self._tts_workers.remove(worker)
        except ValueError:
            pass

    def _play_audio(self, file_path: str):
        """播放音频（含 Live2D 口型同步）"""
        try:
            self._media_player.setSource(QUrl.fromLocalFile(file_path))
            self._media_player.play()
            # 启动口型同步动画
            self._start_lipsync()
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")

    def _start_lipsync(self):
        """TTS 播放时驱动 Live2D 口型动画"""
        if not self._animation_controller:
            return

        # 先停止旧的口型同步定时器
        if hasattr(self, '_lipsync_timer') and self._lipsync_timer:
            self._lipsync_timer.stop()
            self._lipsync_timer = None

        # 使用 QMediaPlayer 的播放状态来控制口型同步
        self._lipsync_timer = QTimer(self)
        self._lipsync_timer.timeout.connect(self._lipsync_tick)
        self._lipsync_timer.start(100)  # 每 100ms 更新一次（10 fps）

        # 监听播放结束
        try:
            self._media_player.playbackStateChanged.disconnect(self._on_playback_state_changed)
        except (RuntimeError, TypeError):
            pass
        self._media_player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _lipsync_tick(self):
        """口型同步定时更新 — 模拟嘴巴开合"""
        if not self.isVisible():
            return
        if not self._animation_controller:
            return
        if not self._media_player or self._media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return
        # 简易口型同步：用随机值模拟嘴巴开合
        mouth_open = random.uniform(0.3, 1.0)
        self._animation_controller.set_mouth_open(mouth_open)

    def _on_playback_state_changed(self, state):
        """播放结束 → 播队首"""
        if state != QMediaPlayer.PlaybackState.PlayingState:
            if self._animation_controller:
                self._animation_controller.set_mouth_open(0.0)
            if hasattr(self, '_lipsync_timer') and self._lipsync_timer:
                self._lipsync_timer.stop()
                self._lipsync_timer = None
            # 统一走 _try_play_next
            self._try_play_next()

    def _toggle_recording(self, checked: bool):
        """切换录音状态"""
        if checked:
            self.record_btn.setText("停止")
            self.chat_display.append_system_msg("开始录音...")
            try:
                import sounddevice as sd
                import numpy as np

                self._sd = sd
                self._np = np
                self._recording_data = []
                self._sample_rate = 16000

                def audio_callback(indata, frames, time_info, status):
                    self._recording_data.append(indata.copy())

                self._recording_stream = sd.InputStream(
                    samplerate=self._sample_rate,
                    channels=1,
                    dtype='float32',
                    callback=audio_callback
                )
                self._recording_stream.start()
            except ImportError:
                self.chat_display.append_system_msg("录音需要 sounddevice 库，请安装: pip install sounddevice")
                self.record_btn.setChecked(False)
                self.record_btn.setText("录音")
            except Exception as e:
                self.chat_display.append_system_msg(f"录音启动失败: {e}")
                self.record_btn.setChecked(False)
                self.record_btn.setText("录音")
        else:
            self.record_btn.setText("录音")
            try:
                if hasattr(self, '_recording_stream') and self._recording_stream:
                    self._recording_stream.stop()
                    self._recording_stream.close()
                    self._recording_stream = None

                    if self._recording_data:
                        audio = self._np.concatenate(self._recording_data, axis=0)
                        import tempfile
                        tmp = tempfile.NamedTemporaryFile(
                            suffix=".wav", delete=False, dir=PROJECT_DIR
                        )
                        tmp_path = tmp.name
                        tmp.close()

                        import wave
                        with wave.open(tmp_path, 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(self._sample_rate)
                            audio_int16 = (audio * 32767).astype(self._np.int16)
                            wf.writeframes(audio_int16.tobytes())

                        self._recording_file = tmp_path
                        self.chat_display.append_system_msg("录音结束，正在识别...")

                        if self.backend:
                            from gugu_native.workers.chat_workers import ASRWorker
                            self._asr_worker = ASRWorker(self.backend, tmp_path)
                            self._asr_worker.finished.connect(self._on_asr_result)
                            self._asr_worker.error.connect(self._on_asr_error)
                            self._asr_worker.start()
                        else:
                            self.chat_display.append_system_msg("后端未初始化，无法识别语音")

                    self._recording_data = []
            except Exception as e:
                self.chat_display.append_system_msg(f"录音停止失败: {e}")

    @Slot(str)
    def _on_asr_result(self, text: str):
        """ASR 识别完成"""
        if self._recording_file:
            try:
                os.unlink(self._recording_file)
            except Exception:
                pass
            self._recording_file = None

        if text:
            self.input_field.setText(text)
            self._send_message()
        else:
            self.chat_display.append_system_msg("未能识别语音内容")

    @Slot(str)
    def _on_asr_error(self, error_msg: str):
        """ASR 识别失败"""
        if self._recording_file:
            try:
                os.unlink(self._recording_file)
            except Exception:
                pass
            self._recording_file = None
        self.chat_display.append_system_msg(f"语音识别失败: {error_msg}")

    def _toggle_realtime_voice(self, checked: bool):
        """切换实时语音模式"""
        main_window = self.window()
        if not hasattr(main_window, 'voice_manager') or main_window.voice_manager is None:
            self.chat_display.append_system_msg("语音管理器未初始化")
            self.realtime_btn.setChecked(False)
            return

        voice_mgr = main_window.voice_manager

        if checked and (not hasattr(main_window, 'backend') or main_window.backend is None):
            self.chat_display.append_system_msg("AI 后端尚未就绪，请稍后再试")
            self.realtime_btn.setChecked(False)
            return

        if checked:
            try:
                voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
            except (RuntimeError, TypeError):
                pass
            voice_mgr.speech_recognized.connect(self._on_realtime_speech)
            voice_mgr.start_listening()
            if not voice_mgr.is_listening:
                self.realtime_btn.setChecked(False)
                try:
                    voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
                except (RuntimeError, TypeError):
                    pass
                return
            self.realtime_btn.setText("监听中")
        else:
            voice_mgr.stop_listening()
            self.realtime_btn.setText("实时语音")
            try:
                voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
            except (RuntimeError, TypeError):
                pass

    def _on_realtime_speech(self, text: str):
        """实时语音识别完成"""
        if text:
            # 如果正在流式回复，先停止并终结当前消息
            if self._is_streaming:
                self._stop_streaming()

            # 停止当前 TTS 播放
            if self._media_player and self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._media_player.stop()

            # 清空旧的音频队列和排序缓冲区
            self._audio_queue.clear()
            self._tts_pending.clear()
            self._tts_next_play_seq = 1
            self._tts_seq_counter = 0

            # 断开旧的播放状态监听
            try:
                self._media_player.playbackStateChanged.disconnect(self._on_playback_state_changed)
            except (RuntimeError, TypeError):
                pass

            self.input_field.setText(text)
            # 延迟 50ms 发送，确保状态清理完全生效
            QTimer.singleShot(50, self._send_message)
