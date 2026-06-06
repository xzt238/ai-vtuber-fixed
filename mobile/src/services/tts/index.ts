// ============================================
// TTS 语音合成服务 - 增强版
// ============================================
import * as Speech from 'expo-speech';
import { simpleLipSync } from '../audioAnalyzer';

export interface TTSConfig {
  language?: string;
  pitch?: number; // 0.5 - 2.0
  rate?: number; // 0.5 - 2.0
  voice?: string;
  emotion?: string;
  name?: string;
  style?: string;
}

// 语音预设
export const VOICE_PRESETS: Record<string, TTSConfig> = {
  // 中文语音
  'zh-female-1': { language: 'zh-CN', pitch: 1.2, rate: 1.0, voice: 'zh-CN-language' },
  'zh-female-2': { language: 'zh-CN', pitch: 1.3, rate: 0.9, voice: 'zh-CN-language' },
  'zh-male-1': { language: 'zh-CN', pitch: 0.8, rate: 1.0, voice: 'zh-CN-language' },
  'zh-male-2': { language: 'zh-CN', pitch: 0.7, rate: 1.1, voice: 'zh-CN-language' },
  
  // 日语语音
  'ja-female-1': { language: 'ja-JP', pitch: 1.4, rate: 1.0, voice: 'ja-JP-language' },
  'ja-female-2': { language: 'ja-JP', pitch: 1.5, rate: 0.9, voice: 'ja-JP-language' },
  'ja-male-1': { language: 'ja-JP', pitch: 0.8, rate: 1.0, voice: 'ja-JP-language' },
  
  // 英语语音
  'en-female-1': { language: 'en-US', pitch: 1.1, rate: 1.0, voice: 'en-US-language' },
  'en-female-2': { language: 'en-US', pitch: 1.2, rate: 0.9, voice: 'en-US-language' },
  'en-male-1': { language: 'en-US', pitch: 0.8, rate: 1.0, voice: 'en-US-language' },
  'en-male-2': { language: 'en-US', pitch: 0.7, rate: 1.1, voice: 'en-US-language' },
  
  // 韩语语音
  'ko-female-1': { language: 'ko-KR', pitch: 1.3, rate: 1.0, voice: 'ko-KR-language' },
  'ko-male-1': { language: 'ko-KR', pitch: 0.8, rate: 1.0, voice: 'ko-KR-language' },
  
  // 特殊风格
  'cute': { language: 'zh-CN', pitch: 1.6, rate: 0.9 },
  'cool': { language: 'zh-CN', pitch: 0.7, rate: 1.1 },
  'energetic': { language: 'zh-CN', pitch: 1.3, rate: 1.2 },
  'calm': { language: 'zh-CN', pitch: 1.0, rate: 0.8 },
};

// 情感参数映射
const EMOTION_PARAMS: Record<string, Partial<TTSConfig>> = {
  neutral: { pitch: 1.0, rate: 1.0 },
  happy: { pitch: 1.2, rate: 1.1 },
  sad: { pitch: 0.9, rate: 0.9 },
  angry: { pitch: 1.1, rate: 1.2 },
  surprised: { pitch: 1.3, rate: 1.1 },
  love: { pitch: 1.1, rate: 0.95 },
  thinking: { pitch: 0.95, rate: 0.9 },
  shy: { pitch: 1.15, rate: 0.85 },
  excited: { pitch: 1.25, rate: 1.15 },
};

class TTSService {
  private currentVoice: string = 'zh-female-1';
  private isSpeaking: boolean = false;
  private onSpeakStart?: () => void;
  private onSpeakEnd?: () => void;
  private onSpeakProgress?: (text: string) => void;
  
  // 设置回调
  setCallbacks(callbacks: {
    onStart?: () => void;
    onEnd?: () => void;
    onProgress?: (text: string) => void;
  }) {
    this.onSpeakStart = callbacks.onStart;
    this.onSpeakEnd = callbacks.onEnd;
    this.onSpeakProgress = callbacks.onProgress;
  }
  
  // 设置语音
  setVoice(voiceName: string) {
    if (VOICE_PRESETS[voiceName]) {
      this.currentVoice = voiceName;
    }
  }
  
  // 获取当前语音配置
  getVoiceConfig(): TTSConfig {
    return { ...VOICE_PRESETS[this.currentVoice] };
  }
  
  // 获取所有可用语音
  getAvailableVoices(): Array<{ name: string; label: string; config: TTSConfig }> {
    return Object.entries(VOICE_PRESETS).map(([name, config]) => ({
      name,
      label: this.getVoiceLabel(name),
      config
    }));
  }
  
  // 获取语音标签
  private getVoiceLabel(name: string): string {
    const labels: Record<string, string> = {
      'zh-female-1': '中文女声 1',
      'zh-female-2': '中文女声 2',
      'zh-male-1': '中文男声 1',
      'zh-male-2': '中文男声 2',
      'ja-female-1': '日语女声 1',
      'ja-female-2': '日语女声 2',
      'ja-male-1': '日语男声 1',
      'en-female-1': '英语女声 1',
      'en-female-2': '英语女声 2',
      'en-male-1': '英语男声 1',
      'en-male-2': '英语男声 2',
      'ko-female-1': '韩语女声 1',
      'ko-male-1': '韩语男声 1',
      'cute': '可爱风格',
      'cool': '冷酷风格',
      'energetic': '活力风格',
      'calm': '平静风格',
    };
    return labels[name] || name;
  }
  
  // 说话
  async speak(text: string, config?: Partial<TTSConfig>): Promise<void> {
    if (this.isSpeaking) {
      await this.stop();
    }
    
    const voiceConfig = {
      ...VOICE_PRESETS[this.currentVoice],
      ...config
    };
    
    // 应用情感参数
    if (config?.emotion && EMOTION_PARAMS[config.emotion]) {
      const emotionParams = EMOTION_PARAMS[config.emotion];
      voiceConfig.pitch = (voiceConfig.pitch || 1) * (emotionParams.pitch || 1);
      voiceConfig.rate = (voiceConfig.rate || 1) * (emotionParams.rate || 1);
    }
    
    // 限制参数范围
    voiceConfig.pitch = Math.max(0.5, Math.min(2, voiceConfig.pitch || 1));
    voiceConfig.rate = Math.max(0.5, Math.min(2, voiceConfig.rate || 1));
    
    this.isSpeaking = true;
    this.onSpeakStart?.();
    
    // 启动口型同步
    simpleLipSync.startSimulation();
    simpleLipSync.setVolume(0.5);
    
    try {
      await Speech.speak(text, {
        language: voiceConfig.language || 'zh-CN',
        pitch: voiceConfig.pitch,
        rate: voiceConfig.rate,
        voice: voiceConfig.voice,
        onStart: () => {
          this.onSpeakProgress?.(text);
        },
        onDone: () => {
          this.isSpeaking = false;
          simpleLipSync.stopSimulation();
          this.onSpeakEnd?.();
        },
        onStopped: () => {
          this.isSpeaking = false;
          simpleLipSync.stopSimulation();
          this.onSpeakEnd?.();
        },
        onError: () => {
          this.isSpeaking = false;
          simpleLipSync.stopSimulation();
          this.onSpeakEnd?.();
        }
      });
    } catch (error) {
      this.isSpeaking = false;
      simpleLipSync.stopSimulation();
      this.onSpeakEnd?.();
      console.error('TTS error:', error);
    }
  }
  
  // 停止说话
  async stop(): Promise<void> {
    if (this.isSpeaking) {
      await Speech.stop();
      this.isSpeaking = false;
      simpleLipSync.stopSimulation();
      this.onSpeakEnd?.();
    }
  }
  
  // 暂停
  async pause(): Promise<void> {
    if (this.isSpeaking) {
      await Speech.pause();
    }
  }
  
  // 恢复
  async resume(): Promise<void> {
    await Speech.resume();
  }
  
  // 是否正在说话
  getIsSpeaking(): boolean {
    return this.isSpeaking;
  }
  
  // 获取可用语音列表（系统级）
  async getSystemVoices(): Promise<Speech.Voice[]> {
    try {
      return await Speech.getAvailableVoicesAsync();
    } catch (error) {
      console.error('Get system voices error:', error);
      return [];
    }
  }
  
  // 添加语气词（让语音更自然）
  addFillerWords(text: string, emotion: string): string {
    const fillers: Record<string, string[]> = {
      happy: ['嗯~', '哈哈', '嘻嘻'],
      sad: ['唉...', '嗯...', '哎...'],
      angry: ['哼！', '真是的！'],
      surprised: ['哇！', '诶？', '真的吗？'],
      love: ['嘻嘻~', '嗯哼~'],
      thinking: ['嗯...', '让我想想...', '这个嘛...'],
      shy: ['那个...', '嗯...'],
      excited: ['太棒了！', '耶！', '好耶！'],
    };
    
    const emotionFillers = fillers[emotion] || fillers.neutral;
    const filler = emotionFillers[Math.floor(Math.random() * emotionFillers.length)];
    
    // 30% 概率添加语气词
    if (Math.random() < 0.3) {
      return `${filler} ${text}`;
    }
    return text;
  }
  
  // 分段说话（长文本）
  async speakLongText(text: string, config?: Partial<TTSConfig>): Promise<void> {
    // 按标点符号分段
    const segments = text.split(/([。！？.!?\n])/).reduce((acc: string[], curr, i, arr) => {
      if (i % 2 === 0) {
        const segment = curr + (arr[i + 1] || '');
        if (segment.trim()) {
          acc.push(segment.trim());
        }
      }
      return acc;
    }, []);
    
    // 逐段播放
    for (const segment of segments) {
      if (!this.isSpeaking) break;
      await this.speak(segment, config);
      // 段间停顿
      await new Promise(resolve => setTimeout(resolve, 200));
    }
  }
}

// 单例
export const ttsService = new TTSService();

// 默认导出
export default ttsService;
