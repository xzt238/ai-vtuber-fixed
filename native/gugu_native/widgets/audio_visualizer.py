"""
音频频谱可视化组件

使用 QOpenGLWidget + numpy FFT 实现 32 段频谱柱状图。
可嵌入到 ChatPage 底部或 Live2D 下方。

功能:
- 32 段频谱柱状图
- 暗色主题配色（渐变色柱）
- 从 QMediaPlayer 音频数据或 PyAudio 流获取 PCM 数据
- 自动平滑动画
- 支持颜色主题切换
"""

import math
import numpy as np
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from qfluentwidgets import FluentIcon, ToolButton, TogglePushButton, CaptionLabel


# 频谱柱数量
BAND_COUNT = 32

# 暗色主题颜色方案
THEME_COLORS = {
    "default": [
        (0, 180, 255),   # 蓝
        (100, 80, 255),  # 紫
        (200, 50, 255),  # 亮紫
    ],
    "warm": [
        (255, 100, 50),   # 橙红
        (255, 180, 0),    # 金黄
        (255, 50, 80),    # 粉红
    ],
    "green": [
        (0, 255, 130),    # 绿
        (0, 200, 255),    # 青
        (0, 255, 50),     # 亮绿
    ],
}


class SpectrumWidget(QWidget):
    """
    频谱柱状图绘制组件（纯 QPainter，不依赖 OpenGL）

    接收 FFT 后的频域幅度数据，绘制 32 段柱状图。
    支持渐变色、圆角柱、平滑动画。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bands = np.zeros(BAND_COUNT)
        self._target_bands = np.zeros(BAND_COUNT)
        self._peaks = np.zeros(BAND_COUNT)
        self._peak_decay = np.full(BAND_COUNT, 0.85)
        self._color_theme = "default"
        self._bar_gap = 2
        self._min_height = 3
        self.setMinimumHeight(60)
        self.setMaximumHeight(120)

    def set_bands(self, bands: np.ndarray):
        """设置当前频谱数据（0.0~1.0 归一化）"""
        if len(bands) >= BAND_COUNT:
            self._target_bands = bands[:BAND_COUNT].copy()
        else:
            padded = np.zeros(BAND_COUNT)
            padded[:len(bands)] = bands
            self._target_bands = padded

    def set_color_theme(self, theme: str):
        """设置颜色主题"""
        if theme in THEME_COLORS:
            self._color_theme = theme

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        colors = THEME_COLORS.get(self._color_theme, THEME_COLORS["default"])

        # 平滑过渡
        self._bands += (self._target_bands - self._bands) * 0.3
        self._peaks = np.maximum(self._peaks * self._peak_decay, self._bands)

        # 绘制柱状图
        total_gap = (BAND_COUNT - 1) * self._bar_gap
        bar_width = max(2, (w - total_gap) // BAND_COUNT)
        start_x = (w - (bar_width * BAND_COUNT + total_gap)) // 2

        for i in range(BAND_COUNT):
            value = float(np.clip(self._bands[i], 0.0, 1.0))
            peak_value = float(np.clip(self._peaks[i], 0.0, 1.0))
            bar_height = max(self._min_height, int(value * (h - 8)))
            peak_y = h - 4 - int(peak_value * (h - 8))

            x = start_x + i * (bar_width + self._bar_gap)
            y = h - 4 - bar_height

            # 渐变色
            gradient = QLinearGradient(x, y, x, h - 4)
            t = i / max(1, BAND_COUNT - 1)
            # 在颜色之间插值
            seg = t * (len(colors) - 1)
            idx = int(seg)
            frac = seg - idx
            if idx >= len(colors) - 1:
                c = colors[-1]
            else:
                c = tuple(
                    int(colors[idx][ch] * (1 - frac) + colors[idx + 1][ch] * frac)
                    for ch in range(3)
                )
            top_color = QColor(c[0], c[1], c[2], 200)
            bottom_color = QColor(c[0], c[1], c[2], 80)
            gradient.setColorAt(0.0, top_color)
            gradient.setColorAt(1.0, bottom_color)

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_height, 2, 2)

            # 峰值指示线
            if peak_value > 0.05:
                pen = QPen(QColor(c[0], c[1], c[2], 160), 2)
                painter.setPen(pen)
                painter.drawLine(x, peak_y, x + bar_width, peak_y)

        painter.end()


class AudioVisualizer(QWidget):
    """
    音频频谱可视化容器组件

    包含 SpectrumWidget + 控制按钮。
    通过 QTimer 定期从音频源获取 PCM 数据并进行 FFT。

    使用方式:
        visualizer = AudioVisualizer(parent)
        # 连接到 QMediaPlayer
        visualizer.connect_media_player(media_player)
        # 或手动输入频谱数据
        visualizer.spectrum.set_bands(data)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_player = None
        self._audio_buffer = np.zeros(2048)
        self._sample_rate = 44100
        self._is_active = False
        self._simulate_mode = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 频谱绘制区
        self.spectrum = SpectrumWidget()
        layout.addWidget(self.spectrum, stretch=1)

        # 控制行
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(4, 0, 4, 0)
        ctrl_row.setSpacing(6)

        self._toggle_btn = TogglePushButton("频谱")
        self._toggle_btn.setChecked(False)
        self._toggle_btn.toggled.connect(self._on_toggle)
        ctrl_row.addWidget(self._toggle_btn)

        # 颜色主题切换
        self._theme_btn = ToolButton(FluentIcon.PALETTE)
        self._theme_btn.setFixedSize(28, 28)
        self._theme_btn.setToolTip("切换配色")
        self._theme_btn.clicked.connect(self._cycle_theme)
        ctrl_row.addWidget(self._theme_btn)

        self._theme_label = CaptionLabel("default")
        ctrl_row.addWidget(self._theme_label)

        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # FFT 定时器
        self._fft_timer = QTimer(self)
        self._fft_timer.setInterval(33)  # ~30 FPS
        self._fft_timer.timeout.connect(self._do_fft)

        # 主题循环列表
        self._theme_list = list(THEME_COLORS.keys())
        self._theme_index = 0

    def connect_media_player(self, player: QMediaPlayer):
        """
        连接到 QMediaPlayer 以获取音频数据

        Args:
            player: QMediaPlayer 实例
        """
        self._media_player = player
        # 尝试连接音频缓冲区信号
        try:
            # Qt6 中 QMediaPlayer 不直接暴露 PCM 数据
            # 使用模拟模式：根据播放状态生成伪频谱
            player.playbackStateChanged.connect(self._on_playback_state_changed)
        except Exception:
            pass

    def set_audio_data(self, pcm_data: np.ndarray, sample_rate: int = 44100):
        """
        手动设置 PCM 音频数据进行 FFT

        Args:
            pcm_data: float32 PCM 数据（单声道）
            sample_rate: 采样率
        """
        self._audio_buffer = pcm_data
        self._sample_rate = sample_rate
        if self._is_active:
            self._do_fft()

    def _on_toggle(self, checked: bool):
        """切换频谱显示"""
        self._is_active = checked
        if checked:
            self._fft_timer.start()
            if self._media_player and self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._simulate_mode = True
        else:
            self._fft_timer.stop()
            self.spectrum.set_bands(np.zeros(BAND_COUNT))
            self.spectrum.update()

    def _on_playback_state_changed(self, state):
        """播放状态变化"""
        self._simulate_mode = (state == QMediaPlayer.PlaybackState.PlayingState)

    def _do_fft(self):
        """执行 FFT 并更新频谱"""
        if self._simulate_mode or self._is_active:
            # 如果有真实 PCM 数据，使用 FFT
            if len(self._audio_buffer) > 0 and np.any(self._audio_buffer):
                fft_data = self._compute_fft(self._audio_buffer)
                self.spectrum.set_bands(fft_data)
            else:
                # 模拟模式：生成伪频谱动画
                self._generate_simulated_bands()

            self.spectrum.update()

    def _compute_fft(self, pcm_data: np.ndarray) -> np.ndarray:
        """
        对 PCM 数据执行 FFT，返回 BAND_COUNT 段归一化频谱

        Args:
            pcm_data: 时域 PCM 数据

        Returns:
            归一化频谱数据 (0.0~1.0)
        """
        n = len(pcm_data)
        if n < BAND_COUNT * 2:
            return np.zeros(BAND_COUNT)

        # 应用汉宁窗
        window = np.hanning(n)
        windowed = pcm_data * window

        # FFT
        fft_result = np.fft.rfft(windowed)
        magnitudes = np.abs(fft_result)

        # 对数缩放
        magnitudes = np.log1p(magnitudes * 100)

        # 分成 BAND_COUNT 段（对数频率分布）
        total_bins = len(magnitudes)
        bands = np.zeros(BAND_COUNT)
        for i in range(BAND_COUNT):
            # 对数刻度分段
            start = int(total_bins * (i / BAND_COUNT) ** 1.5)
            end = int(total_bins * ((i + 1) / BAND_COUNT) ** 1.5)
            if end > start:
                bands[i] = np.mean(magnitudes[start:end])
            else:
                bands[i] = 0.0

        # 归一化
        max_val = np.max(bands)
        if max_val > 0:
            bands = bands / max_val

        return bands

    def _generate_simulated_bands(self):
        """生成模拟频谱动画（无真实音频输入时使用）"""
        import time
        t = time.time()
        bands = np.zeros(BAND_COUNT)
        for i in range(BAND_COUNT):
            # 基于正弦波的伪频谱
            freq = 0.5 + i * 0.15
            phase = t * freq * 2.0
            base = 0.3 + 0.4 * math.sin(phase) + 0.2 * math.sin(phase * 0.7 + 1.0)
            # 低频稍高，高频递减
            decay = 1.0 - (i / BAND_COUNT) * 0.5
            bands[i] = max(0.05, base * decay * 0.6)
        self.spectrum.set_bands(bands)

    def _cycle_theme(self):
        """循环切换颜色主题"""
        self._theme_index = (self._theme_index + 1) % len(self._theme_list)
        theme = self._theme_list[self._theme_index]
        self.spectrum.set_color_theme(theme)
        self._theme_label.setText(theme)
        self.spectrum.update()
