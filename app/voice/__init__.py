#!/usr/bin/env python3
"""
=====================================
语音输入模块 (Voice Input)
=====================================

【模块功能概述】
本模块负责 AI VTuber 系统的语音输入功能——从麦克风采集用户的语音数据，
并将其保存为音频文件，供 ASR 模块进行语音识别。

【两种输入方式】
1. VoiceInput —— 本地麦克风录音
   - 基于 sounddevice 库直接访问系统音频设备
   - 适合桌面端使用场景
   - 支持 VAD（语音活动检测）和音量计算

2. WebVoiceInput —— 浏览器端 WebRTC 录音
   - 基于 JavaScript MediaRecorder API
   - 通过 WebSocket 将音频数据发送到服务端
   - 适合 Web 端使用场景
   - 提供完整的 HTML/CSS/JS 代码生成

【工厂模式】
VoiceInputFactory 根据使用场景（本地 vs Web）创建对应的输入实例。

【与其他模块的关系】
- VoiceInput 被 web/__init__.py 的 WebSocket 处理器使用
- 录音产出的 WAV 文件被传给 asr/__init__.py 进行识别
- WebVoiceInput 的 HTML/JS 代码被嵌入到 web 面板页面中

【音频规格】
- 采样率：16000 Hz（ASR 标准输入格式）
- 声道：单声道
- 位深：16-bit PCM（WAV 格式）
- 编码：PCM（无压缩）

作者: 咕咕嘎嘎
日期: 2026-03-27
"""

import os
import tempfile
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any


# =====================================================================
# 本地麦克风录音
# =====================================================================

class VoiceInput:
    """
    【核心类】本地语音输入管理器

    通过 sounddevice 库访问系统麦克风，实时采集音频数据，
    并在录音结束时将音频保存为 WAV 文件。

    【核心功能】
    1. 麦克风录音：使用 sounddevice.InputStream 进行实时音频采集
    2. 语音活动检测（VAD）：通过音量阈值判断是否有语音输入
    3. 音频处理：将采集到的 float32 音频数据转换为 16-bit PCM WAV 文件

    【配置参数】（通过 config 字典传入）
        enabled (bool): 是否启用语音输入，默认 True
        device: 音频设备标识符，"default" 表示系统默认麦克风
        threshold (float): VAD 音量阈值，默认 0.01
        max_duration (int): 最大录音时长（秒），默认 30
        silence_duration (int): 静音判定时长（秒），默认 2

    【回调机制】
        通过 set_callback() 设置录音完成回调函数，
        录音结束后自动调用回调，将音频文件路径传递给调用者。

    【使用流程】
        voice = VoiceInput(config)
        voice.set_callback(on_audio_ready)
        voice.start()     # 开始录音
        # ... 用户说话 ...
        path = voice.stop()  # 停止录音，返回 WAV 文件路径
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化语音输入管理器

        【参数说明】
            config (Dict[str, Any]): 配置字典，包含启用状态、设备、阈值等参数

        【初始化内容】
            - 保存配置参数
            - 初始化录音状态为 False
            - 初始化音频数据缓冲区为空列表
            - 回调函数初始为 None（需通过 set_callback 设置）
        """
        self.config = config
        self.enabled = config.get("enabled", True)          # 是否启用
        self.device = config.get("device", "default")       # 音频设备
        self.threshold = config.get("threshold", 0.01)      # VAD 音量阈值
        self.max_duration = config.get("max_duration", 30)  # 最大录音时长（秒）
        self.silence_duration = config.get("silence_duration", 2)  # 静音判定时长
        
        self.is_recording = False   # 当前是否正在录音
        self.audio_data = []        # 音频数据缓冲区（每帧是一个 numpy 数组）
        self.callback = None        # 录音完成回调函数
        self.recorder = None        # sounddevice.InputStream 实例
    
    def is_available(self) -> bool:
        """
        【检查方法】检测语音输入是否可用

        【返回值】
            bool: True 表示可用；False 表示不可用

        【检测流程】
            1. 检查 enabled 配置是否为 True
            2. 检查 sounddevice 是否已安装
            3. 检查系统是否有可用的输入设备（麦克风）
            4. 任何一步失败都返回 False
        """
        if not self.enabled:
            return False
        
        # 检查音频设备和 sounddevice 库
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            if devices is None:
                return False
            # 检查是否有默认输入设备且该设备有输入通道
            default_input = sd.query_devices(kind='input')
            return default_input is not None and default_input.get('max_input_channels', 0) > 0
        except ImportError:
            print("️ sounddevice未安装: pip install sounddevice")
            return False
        except OSError as e:
            print(f"️ 无法访问麦克风: {e}")
            return False
        except Exception as e:
            print(f"️ 麦克风错误: {e}")
            return False
    
    def set_callback(self, callback: Callable):
        """
        【设置回调】注册录音完成时的回调函数

        【参数说明】
            callback (Callable): 回调函数，接收一个参数（音频文件路径 str）
        """
        self.callback = callback
    
    def start(self) -> bool:
        """
        【开始录音】启动麦克风录音

        【返回值】
            bool: True 表示录音已成功启动；False 表示启动失败

        【执行流程】
            1. 检查是否已在录音（防止重复启动）
            2. 检查语音输入是否可用
            3. 创建 sounddevice.InputStream，配置：
               - device: 使用的音频设备
               - channels=1: 单声道（ASR 要求）
               - samplerate=16000: 16kHz 采样率（ASR 标准格式）
               - dtype='float32': 32 位浮点格式
               - callback: 每帧数据的回调函数
            4. 启动录音流

        【音频回调说明】
            sounddevice 的 InputStream 会在收到音频数据时调用回调：
            - indata: 音频数据数组（shape: [frames, channels]）
            - frames: 帧数（每次回调的数据量）
            - time: 时间戳信息
            - status: 流状态（如有溢出/欠载会设置标志位）
        """
        if self.is_recording:
            return False
        
        if not self.is_available():
            print("️ 语音输入不可用")
            return False
        
        try:
            import sounddevice as sd
            import numpy as np
            
            self.is_recording = True
            self.audio_data = []  # 重置音频缓冲区
            
            # 定义音频数据回调函数（sounddevice 在收到数据时自动调用）
            def callback(indata, frames, time, status):
                """
                【内部回调】音频录制数据回调函数（sounddevice 自动调用）

                【参数说明】
                    indata: 音频数据数组
                    frames: 每帧采样数
                    time: 时间戳信息
                    status: 录音状态错误信息

                【返回值】
                    无（直接写入缓冲区）
                """
                if status:
                    print(f"录音状态: {status}")
                
                # 计算当前帧的音量（RMS，均方根）
                # np.linalg.norm 计算向量的 L2 范数，除以 frames 归一化
                volume = np.linalg.norm(indata) / frames

                # 将音频数据副本加入缓冲区（必须 copy，因为 indata 是共享缓冲区）
                self.audio_data.append(indata.copy())
                
                # 语音活动检测（VAD）：音量超过阈值表示检测到声音
                # 注意：当前实现只做检测标记，实际的静音断句逻辑需要外部实现
                if volume > self.threshold:
                    # 检测到声音（可在此处扩展实现静音自动停止录音）
                    pass
            
            # 创建并启动音频输入流
            self.recorder = sd.InputStream(
                device=self.device,       # 音频设备
                channels=1,               # 单声道
                samplerate=16000,         # 16kHz 采样率
                dtype='float32',          # 32位浮点
                callback=callback         # 音频数据回调
            )
            self.recorder.start()
            
            print(" 开始录音...")
            return True
            
        except Exception as e:
            print(f"️ 开始录音失败: {e}")
            self.is_recording = False
            return False
    
    def stop(self) -> Optional[str]:
        """
        【停止录音】停止录音并保存为 WAV 文件

        【返回值】
            Optional[str]: 保存的 WAV 文件路径；未在录音或无数据时返回 None

        【执行流程】
            1. 停止并关闭音频输入流
            2. 检查是否有录音数据
            3. 用 numpy.concatenate 合并所有音频帧
            4. 转换为 16-bit PCM 格式并保存为 WAV 文件
            5. 调用回调函数通知调用者

        【音频格式转换】
            sounddevice 使用 float32（-1.0~1.0），WAV 文件使用 int16（-32768~32767）
            转换公式：int16_value = float32_value * 32767
        """
        if not self.is_recording:
            return None
        
        try:
            import sounddevice as sd
            import numpy as np
            
            # 停止并关闭音频流
            self.recorder.stop()
            self.recorder.close()
            self.is_recording = False
            
            # 检查是否有录音数据
            if not self.audio_data:
                return None
            
            # 合并所有音频帧（每帧是一个 numpy 数组，沿第0轴拼接）
            audio = np.concatenate(self.audio_data)
            
            # 保存为 WAV 文件
            # delete=False: 不自动删除临时文件（因为调用者需要读取）
            import wave
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            
            with wave.open(temp_file.name, 'wb') as f:
                f.setnchannels(1)          # 单声道
                f.setsampwidth(2)          # 2字节 = 16位
                f.setframerate(16000)      # 16kHz 采样率
                # float32 → int16 格式转换（乘以 32767 并截断为整数）
                audio_int = (audio * 32767).astype('int16')
                f.writeframes(audio_int.tobytes())
            
            print(f" 录音完成: {temp_file.name}")
            
            # 触发回调函数，通知调用者录音完成
            if self.callback:
                self.callback(temp_file.name)
            
            return temp_file.name
            
        except Exception as e:
            print(f"️ 停止录音失败: {e}")
            return None
    
    def cancel(self):
        """
        【取消录音】停止录音并丢弃所有数据

        与 stop() 不同，cancel() 不会保存音频文件，也不会触发回调。
        用于用户主动取消录音的场景。
        """
        if self.is_recording:
            try:
                self.recorder.stop()
                self.recorder.close()
            except:
                pass  # 忽略关闭时的异常
            self.is_recording = False
            self.audio_data = []  # 清空缓冲区，丢弃所有数据
            print(" 录音已取消")


# =====================================================================
# 浏览器端 WebRTC 录音
# =====================================================================

class WebVoiceInput:
    """
    【Web 端类】浏览器语音输入（通过 WebRTC）

    提供完整的 HTML/CSS/JS 代码，在浏览器中实现：
    1. 获取麦克风权限（MediaRecorder API）
    2. 实时录音（按住说话模式）
    3. 音频编码（WebM/Opus 格式）
    4. Base64 编码并通过 WebSocket 发送到服务端

    【交互方式】
    - 按住按钮录音（mousedown/touchstart）
    - 松开按钮停止并发送（mouseup/touchend）
    - 鼠标移出按钮取消录音（mouseleave）

    【前端技术栈】
    - MediaRecorder API: 浏览器原生录音 API
    - WebRTC getUserMedia: 获取麦克风权限
    - WebSocket: 实时传输音频数据
    - FileReader: 将音频 Blob 转为 Base64

    【服务端对接】
    音频数据通过 WebSocket 以 JSON 格式发送：
    {"type": "audio", "data": "data:audio/webm;base64,..."}
    服务端（web/__init__.py）接收后解码为 WAV，传给 ASR 识别。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化 Web 语音输入

        【参数说明】
            config (Dict[str, Any]): 配置字典（当前仅使用 enabled 字段）
        """
        self.config = config
        self.enabled = config.get("enabled", True)
    
    def get_html(self) -> str:
        """
        【生成 HTML】获取 Web 语音输入的完整 HTML/JS 代码

        【返回值】
            str: 包含录音按钮、状态显示和 JavaScript 逻辑的 HTML 字符串。
                 需要嵌入到 web 面板页面中使用。

        【JavaScript 核心逻辑】
            - startVoice(): 获取麦克风权限，创建 MediaRecorder，开始录音
            - stopVoice(): 停止录音，合并音频数据，Base64 编码后通过 WebSocket 发送
            - cancelVoice(): 取消录音，关闭麦克风

        【注意事项】
            需要外部定义全局 WebSocket 变量 `ws` 才能发送音频数据。
            音频格式为 audio/webm;codecs=opus，服务端需要做格式转换。
        """
        return """
<!-- 语音输入控制面板 -->
<div class="voice-input-panel">
    <!-- 按住说话按钮 -->
    <button id="voice-btn" class="voice-btn" onmousedown="startVoice()" onmouseup="stopVoice()" onmouseleave="cancelVoice()">
        <span class="mic-icon"></span>
        <span class="mic-text">按住说话</span>
    </button>
    <!-- 状态文本 -->
    <div id="voice-status" class="voice-status">点击按钮开始录音</div>
</div>

<script>
// 语音输入相关变量
let mediaRecorder = null;     // MediaRecorder 实例
let audioChunks = [];         // 音频数据块缓冲区
let isRecording = false;      // 录音状态标志

// 开始录音 —— 获取麦克风权限并创建 MediaRecorder
async function startVoice() {
    try {
        // 请求麦克风权限（返回 Promise）
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // 创建 MediaRecorder，指定输出格式为 WebM/Opus
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });
        
        audioChunks = [];  // 重置音频缓冲区
        
        // 当有音频数据可用时，将其加入缓冲区
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        // 录音停止时的处理逻辑
        mediaRecorder.onstop = () => {
            // 合并所有音频数据块为一个 Blob
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            
            // 使用 FileReader 将 Blob 转为 Base64 Data URL
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64 = reader.result;  // data:audio/webm;base64,...
                
                // 通过 WebSocket 将 Base64 音频数据发送到服务端
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'audio',
                        data: base64
                    }));
                }
            };
            reader.readAsDataURL(audioBlob);
            
            // 关闭麦克风流，释放设备
            stream.getTracks().forEach(track => track.stop());
        };
        
        // 开始录音，每 100ms 触发一次 ondataavailable
        mediaRecorder.start(100);
        isRecording = true;
        
        // 更新 UI：添加录音动画样式
        document.getElementById('voice-btn').classList.add('recording');
        document.getElementById('voice-status').textContent = '录音中...';
        
    } catch (e) {
        console.error('获取麦克风失败:', e);
        alert('无法获取麦克风权限: ' + e.message);
    }
}

// 停止录音 —— 合并发送音频数据
function stopVoice() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();   // 停止录音（触发 onstop 回调）
        isRecording = false;
        
        // 更新 UI：移除录音动画
        document.getElementById('voice-btn').classList.remove('recording');
        document.getElementById('voice-status').textContent = '处理中...';
    }
}

// 取消录音 —— 丢弃音频数据
function cancelVoice() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        // 关闭麦克风流
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => stream.getTracks().forEach(track => track.stop()))
            .catch(() => {});
        
        // 更新 UI
        document.getElementById('voice-btn').classList.remove('recording');
        document.getElementById('voice-status').textContent = '已取消';
    }
}

// WebSocket 变量需在外部定义:
// function setupVoiceWebSocket(websocket) {
//     window.ws = websocket;
// }
"""
    
    def get_css(self) -> str:
        """
        【生成 CSS】获取语音输入面板的样式代码

        【返回值】
            str: CSS 样式字符串，包含按钮样式、录音动画、状态文本等。

        【视觉设计】
            - 圆形渐变按钮（紫色渐变）
            - 录音状态时切换为粉红渐变 + 脉冲动画
            - 按下时缩小效果
            - 半透明状态文本
        """
        return """
.voice-input-panel {
    text-align: center;
    padding: 20px;
}

/* 录音按钮 —— 圆形，紫色渐变 */
.voice-btn {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    border: none;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

/* 悬停放大效果 */
.voice-btn:hover {
    transform: scale(1.05);
}

/* 录音状态 —— 粉红渐变 + 脉冲动画 */
.voice-btn.recording {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    animation: pulse 1s infinite;
}

/* 按下缩小效果 */
.voice-btn:active {
    transform: scale(0.95);
}

/* 麦克风图标 */
.mic-icon {
    font-size: 32px;
    margin-bottom: 5px;
}

/* 按钮文字 */
.mic-text {
    font-size: 12px;
}

/* 状态文本 */
.voice-status {
    margin-top: 10px;
    font-size: 12px;
    color: rgba(255,255,255,0.7);
}

/* 脉冲动画 —— 录音时的呼吸灯效果 */
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(240, 147, 251, 0.7); }
    50% { box-shadow: 0 0 0 15px rgba(240, 147, 251, 0); }
}
"""


# =====================================================================
# 工厂类
# =====================================================================

class VoiceInputFactory:
    """
    【工厂类】语音输入工厂

    根据使用场景创建对应的语音输入实例：
    - 本地模式 → VoiceInput（sounddevice 麦克风录音）
    - Web 模式 → WebVoiceInput（浏览器 WebRTC 录音）
    """
    
    @staticmethod
    def create(config: Dict[str, Any], use_web: bool = False):
        """
        【静态工厂方法】创建语音输入实例

        【参数说明】
            config (Dict[str, Any]): 语音输入配置字典
            use_web (bool): 是否使用 Web 模式（默认 False → 本地模式）

        【返回值】
            VoiceInput 或 WebVoiceInput: 对应的语音输入实例
        """
        if use_web:
            return WebVoiceInput(config)
        else:
            return VoiceInput(config)


# =====================================================================
# 模块测试
# =====================================================================

if __name__ == "__main__":
    # 测试配置
    config = {
        "enabled": True,
        "device": "default",
        "threshold": 0.01,
        "max_duration": 30
    }
    
    # 通过工厂创建语音输入实例
    voice = VoiceInputFactory.create(config)
    print(f"语音输入可用: {voice.is_available()}")
