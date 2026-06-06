# 🎙️ 实时语音打断功能使用指南

**版本**: v1.17.4  
**更新日期**: 2026-06-04

---

## 📋 功能概述

实时语音打断功能允许用户**在AI说话时插嘴**，AI会立即停止说话并听取用户新输入。

### 核心特性

| 特性 | 说明 |
|------|------|
| **VAD状态机** | 高精度语音活动检测，减少误触发 |
| **自动打断** | 检测到用户说话时自动打断AI |
| **上下文保持** | 保存已听到的回复，保持对话连续性 |
| **可配置** | 支持调整VAD阈值、打断冷却时间等参数 |

---

## 🔧 配置说明

### config.yaml 配置

```yaml
# VAD语音活动检测配置
vad:
  enabled: true                    # 启用VAD
  model: silero                    # VAD模型
  prob_threshold: 0.4              # 语音概率阈值 (0-1)
  db_threshold: 60                 # 音量阈值 (dB)
  required_hits: 3                 # 激活所需连续帧数
  required_misses: 24              # 停止所需连续帧数

# 语音打断配置
interrupt:
  enabled: true                    # 启用打断功能
  auto_interrupt: true             # 自动打断（检测到用户说话时）
  save_heard_response: true        # 保存已听到的回复
  max_interrupt_history: 100       # 最大打断历史记录数
  interrupt_cooldown_ms: 500       # 打断冷却时间(毫秒)
```

### 参数调优建议

| 参数 | 低值 | 中值 | 高值 | 说明 |
|------|------|------|------|------|
| `prob_threshold` | 0.2 | 0.4 | 0.6 | 越低越灵敏，但误触发多 |
| `db_threshold` | 40 | 60 | 80 | 越低越灵敏，但噪音干扰多 |
| `required_hits` | 1 | 3 | 5 | 越低响应越快，但误触发多 |
| `required_misses` | 12 | 24 | 36 | 越低停止越快，但可能截断 |
| `interrupt_cooldown_ms` | 200 | 500 | 1000 | 越低打断越频繁 |

---

## 💻 使用示例

### 基础使用

```python
from app.voice.interrupt_voice import get_interruptible_voice

# 创建语音输入实例
voice = get_interruptible_voice({
    "enabled": True,
    "vad_threshold": 0.4,
    "db_threshold": 60
})

# 设置回调函数
async def on_speech_ready(wav_path):
    print(f"语音已保存: {wav_path}")
    # 这里可以调用ASR进行语音识别

async def on_interrupt(heard_response):
    print(f"AI被打断，已听到: {heard_response}")

voice.set_callbacks(
    on_speech_ready=on_speech_ready,
    on_interrupt=on_interrupt
)

# 初始化
await voice.initialize()

# 开始录音
await voice.start()

# 设置AI说话状态
voice.set_ai_speaking(True, "这是一段很长的回答...")

# 当用户说话时，AI会自动被打断

# 停止录音
await voice.stop()
```

### 集成到对话流程

```python
class DialogueManager:
    def __init__(self):
        self.voice = get_interruptible_voice()
        self.voice.set_callbacks(
            on_speech_ready=self.on_user_speech,
            on_interrupt=self.on_ai_interrupted
        )
    
    async def on_user_speech(self, wav_path):
        """用户说完话"""
        # 1. ASR识别
        text = await self.asr.recognize(wav_path)
        
        # 2. LLM生成回复
        response = await self.llm.generate(text)
        
        # 3. TTS合成并播放
        self.voice.set_ai_speaking(True, response)
        await self.tts.speak(response)
        self.voice.set_ai_speaking(False)
    
    async def on_ai_interrupted(self, heard_response):
        """AI被打断"""
        # 1. 停止TTS播放
        await self.tts.stop()
        
        # 2. 保存上下文
        self.context.save_interrupt(heard_response)
        
        # 3. 准备接收新输入
        print("AI已停止说话，等待用户输入...")
```

---

## 📊 状态监控

### 获取统计信息

```python
stats = voice.get_stats()
print(f"录音状态: {stats['is_recording']}")
print(f"AI说话状态: {stats['is_ai_speaking']}")
print(f"VAD状态: {stats['vad_stats']['state']}")
print(f"打断次数: {stats['interrupt_stats']['interrupt_count']}")
```

### VAD状态说明

| 状态 | 说明 |
|------|------|
| `IDLE` | 等待用户说话 |
| `ACTIVE` | 用户正在说话 |
| `INACTIVE` | 用户已停止说话 |

---

## 🎯 最佳实践

### 1. 环境优化

- **安静环境**: 降低 `db_threshold` 到 40-50
- **嘈杂环境**: 提高 `db_threshold` 到 70-80
- **远场录音**: 增加 `required_hits` 到 5

### 2. 响应速度优化

- **快速响应**: 降低 `required_hits` 到 1-2
- **稳定响应**: 保持 `required_hits` 在 3-5
- **避免误触发**: 增加 `required_hits` 到 5+

### 3. 打断体验优化

- **频繁打断**: 降低 `interrupt_cooldown_ms` 到 200-300
- **稳定打断**: 保持 `interrupt_cooldown_ms` 在 500-1000
- **避免误打**: 增加 `interrupt_cooldown_ms` 到 1000+

---

## ⚠️ 注意事项

### 1. 硬件要求

- **麦克风**: 需要可用的麦克风设备
- **CPU**: VAD处理需要一定的CPU资源
- **内存**: 音频缓冲需要约50-100MB内存

### 2. 已知限制

- **不支持耳机**: 当前实现不区分用户声音和AI回声
- **单用户**: 仅支持单用户打断
- **本地处理**: VAD在本地处理，不支持云端

### 3. 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 无法打断 | VAD未启用 | 检查 `vad.enabled` 配置 |
| 误触发多 | 阈值太低 | 提高 `prob_threshold` 和 `db_threshold` |
| 响应慢 | required_hits太高 | 降低 `required_hits` |
| 打断不生效 | cooldown太高 | 降低 `interrupt_cooldown_ms` |

---

## 📈 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| VAD延迟 | <50ms | 每帧处理时间 |
| 打断延迟 | <500ms | 从检测到打断的时间 |
| CPU占用 | <5% | VAD处理的CPU占用 |
| 内存占用 | <100MB | 音频缓冲的内存占用 |
| 误触发率 | <5% | 错误触发的比例 |

---

**文档完成时间**: 2026-06-04 08:55:00  
**文档作者**: 齐活林（Qi）· 交付总监
