// ============================================
// 语音通话服务
// ============================================
import { MMKV } from 'react-native-mmkv';
import { ttsService } from './tts';
import { asrService } from './asr';
import { localAI } from './localAI';
import { emotionService } from './emotion';
import { simpleLipSync } from '../components/live2d';
import type { Character, Message } from '../types';
import type { Emotion } from './emotion';

const storage = new MMKV({ id: 'voice-call' });

// 通话状态
export type CallStatus = 'idle' | 'calling' | 'connected' | 'ended';

// 通话配置
export interface VoiceCallConfig {
  autoListen: boolean; // 自动监听
  silenceTimeout: number; // 静音超时 (ms)
  maxCallDuration: number; // 最大通话时长 (ms)
  enableEmotion: boolean; // 启用情感分析
  enableLipSync: boolean; // 启用口型同步
  voiceId: string; // 语音 ID
}

// 通话状态
export interface VoiceCallState {
  status: CallStatus;
  character: Character | null;
  duration: number; // 通话时长 (ms)
  isSpeaking: boolean; // AI 是否在说话
  isListening: boolean; // 是否在监听用户
  currentEmotion: Emotion;
  messages: Message[];
}

// 默认配置
const DEFAULT_CONFIG: VoiceCallConfig = {
  autoListen: true,
  silenceTimeout: 3000,
  maxCallDuration: 300000, // 5分钟
  enableEmotion: true,
  enableLipSync: true,
  voiceId: 'zh-female-1',
};

class VoiceCallService {
  private static instance: VoiceCallService;
  private config: VoiceCallConfig;
  private state: VoiceCallState;
  private callTimer: NodeJS.Timeout | null = null;
  private silenceTimer: NodeJS.Timeout | null = null;
  private durationTimer: NodeJS.Timeout | null = null;
  private stateCallbacks: Array<(state: VoiceCallState) => void> = [];
  
  private constructor() {
    this.config = this.loadConfig();
    this.state = this.getInitialState();
  }
  
  static getInstance(): VoiceCallService {
    if (!VoiceCallService.instance) {
      VoiceCallService.instance = new VoiceCallService();
    }
    return VoiceCallService.instance;
  }
  
  // 加载配置
  private loadConfig(): VoiceCallConfig {
    try {
      const saved = storage.getString('voice_call_config');
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load voice call config error:', e);
    }
    return { ...DEFAULT_CONFIG };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('voice_call_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save voice call config error:', e);
    }
  }
  
  // 获取初始状态
  private getInitialState(): VoiceCallState {
    return {
      status: 'idle',
      character: null,
      duration: 0,
      isSpeaking: false,
      isListening: false,
      currentEmotion: 'neutral',
      messages: [],
    };
  }
  
  // 更新状态
  private updateState(partial: Partial<VoiceCallState>): void {
    this.state = { ...this.state, ...partial };
    this.notifyStateChange();
  }
  
  // 通知状态变化
  private notifyStateChange(): void {
    this.stateCallbacks.forEach(cb => cb(this.state));
  }
  
  // 获取当前状态
  getState(): VoiceCallState {
    return { ...this.state };
  }
  
  // 更新配置
  updateConfig(partial: Partial<VoiceCallConfig>): void {
    this.config = { ...this.config, ...partial };
    this.saveConfig();
  }
  
  // 获取配置
  getConfig(): VoiceCallConfig {
    return { ...this.config };
  }
  
  // 发起通话
  async startCall(character: Character): Promise<boolean> {
    if (this.state.status !== 'idle') {
      console.warn('Already in a call');
      return false;
    }
    
    this.updateState({
      status: 'calling',
      character,
      duration: 0,
      messages: [],
      currentEmotion: 'neutral',
    });
    
    // 模拟拨号延迟
    await this.delay(1500);
    
    // 连接成功
    this.updateState({ status: 'connected' });
    
    // 开始计时
    this.startDurationTimer();
    
    // AI 打招呼
    await this.speak(character.greeting || `你好！我是${character.name}。`);
    
    // 如果自动监听，开始监听
    if (this.config.autoListen) {
      this.startListening();
    }
    
    return true;
  }
  
  // 结束通话
  async endCall(): Promise<void> {
    if (this.state.status === 'idle') {
      return;
    }
    
    // 停止所有定时器
    this.stopAllTimers();
    
    // 停止语音
    await ttsService.stop();
    
    // 停止监听
    this.stopListening();
    
    // AI 说再见
    if (this.state.character) {
      await this.speak(`好的，那我们下次再聊！再见~`);
    }
    
    this.updateState({
      status: 'ended',
      isSpeaking: false,
      isListening: false,
    });
    
    // 延迟重置状态
    setTimeout(() => {
      this.updateState(this.getInitialState());
    }, 2000);
  }
  
  // AI 说话
  private async speak(text: string): Promise<void> {
    if (this.state.status !== 'connected') {
      return;
    }
    
    this.updateState({ isSpeaking: true });
    
    // 启动口型同步
    if (this.config.enableLipSync) {
      simpleLipSync.startSimulation();
      simpleLipSync.setVolume(0.5);
    }
    
    try {
      // 分析情感
      let emotion: Emotion = 'neutral';
      if (this.config.enableEmotion) {
        const analysis = emotionService.analyze(text);
        emotion = analysis.emotion;
        this.updateState({ currentEmotion: emotion });
      }
      
      // 语音合成
      await ttsService.speak(text, {
        voice: this.config.voiceId,
        emotion,
      });
      
      // 添加到消息列表
      this.addMessage('assistant', text);
      
    } catch (error) {
      console.error('Speak error:', error);
    } finally {
      this.updateState({ isSpeaking: false });
      
      if (this.config.enableLipSync) {
        simpleLipSync.stopSimulation();
      }
    }
  }
  
  // 开始监听
  private startListening(): void {
    if (this.state.isListening) {
      return;
    }
    
    this.updateState({ isListening: true });
    this.resetSilenceTimer();
    
    // 这里需要集成实际的语音识别
    // 模拟监听
    this.simulateListening();
  }
  
  // 停止监听
  private stopListening(): void {
    this.updateState({ isListening: false });
    this.clearSilenceTimer();
  }
  
  // 模拟监听（实际实现需要 ASR）
  private async simulateListening(): Promise<void> {
    // 这里应该调用 ASR 服务
    // 暂时模拟
  }
  
  // 处理用户语音输入
  async handleUserSpeech(text: string): Promise<void> {
    if (this.state.status !== 'connected' || !this.state.character) {
      return;
    }
    
    // 停止监听
    this.stopListening();
    
    // 添加用户消息
    this.addMessage('user', text);
    
    // 重置静音计时器
    this.resetSilenceTimer();
    
    // 生成 AI 回复
    try {
      const response = await localAI.generateResponse(
        text,
        this.state.character,
        this.state.messages.slice(-10),
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.8, maxTokens: 200, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      // AI 回复
      await this.speak(response);
      
    } catch (error) {
      console.error('Generate response error:', error);
      await this.speak('抱歉，我没有听清楚，能再说一遍吗？');
    }
    
    // 继续监听
    if (this.state.status === 'connected' && this.config.autoListen) {
      this.startListening();
    }
  }
  
  // 添加消息
  private addMessage(role: 'user' | 'assistant', content: string): void {
    const message: Message = {
      id: `msg_${Date.now()}_${role}`,
      role,
      content,
      timestamp: new Date(),
    };
    
    this.updateState({
      messages: [...this.state.messages, message],
    });
  }
  
  // 开始计时
  private startDurationTimer(): void {
    this.durationTimer = setInterval(() => {
      this.updateState({
        duration: this.state.duration + 1000,
      });
      
      // 检查最大时长
      if (this.state.duration >= this.config.maxCallDuration) {
        this.endCall();
      }
    }, 1000);
  }
  
  // 重置静音计时器
  private resetSilenceTimer(): void {
    this.clearSilenceTimer();
    
    this.silenceTimer = setTimeout(() => {
      // 静音超时，AI 主动说话
      if (this.state.status === 'connected') {
        this.speak('你还在吗？有什么想聊的吗？');
      }
    }, this.config.silenceTimeout);
  }
  
  // 清除静音计时器
  private clearSilenceTimer(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
  }
  
  // 停止所有定时器
  private stopAllTimers(): void {
    if (this.callTimer) {
      clearTimeout(this.callTimer);
      this.callTimer = null;
    }
    
    if (this.durationTimer) {
      clearInterval(this.durationTimer);
      this.durationTimer = null;
    }
    
    this.clearSilenceTimer();
  }
  
  // 延迟
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // 注册状态回调
  onStateChange(callback: (state: VoiceCallState) => void): () => void {
    this.stateCallbacks.push(callback);
    return () => {
      this.stateCallbacks = this.stateCallbacks.filter(cb => cb !== callback);
    };
  }
  
  // 格式化时长
  formatDuration(ms: number): string {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}:${(minutes % 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
    }
    return `${minutes}:${(seconds % 60).toString().padStart(2, '0')}`;
  }
  
  // 是否在通话中
  isInCall(): boolean {
    return this.state.status !== 'idle' && this.state.status !== 'ended';
  }
}

// 单例
export const voiceCallService = VoiceCallService.getInstance();

export default voiceCallService;
