// ============================================
// 语音打断服务
// ============================================
import { vadService, VADEvent } from '../vad';
import { ttsService } from '../tts';
import { voiceCallService } from '../voiceCall';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV({ id: 'interrupt-service' });

// 打断配置
export interface InterruptConfig {
  // 是否启用语音打断
  enabled: boolean;
  
  // 打断灵敏度 (1-10)
  sensitivity: number;
  
  // 打断后延迟 (ms)
  delayAfterInterrupt: number;
  
  // 是否打断 AI 说话
  interruptSpeaking: boolean;
  
  // 是否打断 AI 思考
  interruptThinking: boolean;
}

// 默认配置
const DEFAULT_CONFIG: InterruptConfig = {
  enabled: true,
  sensitivity: 5,
  delayAfterInterrupt: 300,
  interruptSpeaking: true,
  interruptThinking: false,
};

// 打断事件
export interface InterruptEvent {
  type: 'interrupt_started' | 'interrupt_completed' | 'interrupt_cancelled';
  timestamp: number;
  reason: string;
}

class InterruptService {
  private static instance: InterruptService;
  private config: InterruptConfig;
  private isInterrupting: boolean = false;
  private interruptTimeout: NodeJS.Timeout | null = null;
  
  // 事件回调
  private listeners: Array<(event: InterruptEvent) => void> = [];
  
  // 状态
  private state = {
    totalInterrupts: 0,
    successfulInterrupts: 0,
    cancelledInterrupts: 0,
    lastInterruptTime: 0,
  };
  
  private constructor() {
    this.config = this.loadConfig();
    this.setupVADListener();
  }
  
  static getInstance(): InterruptService {
    if (!InterruptService.instance) {
      InterruptService.instance = new InterruptService();
    }
    return InterruptService.instance;
  }
  
  // 加载配置
  private loadConfig(): InterruptConfig {
    try {
      const saved = storage.getString('interrupt_config');
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load interrupt config error:', e);
    }
    return { ...DEFAULT_CONFIG };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('interrupt_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save interrupt config error:', e);
    }
  }
  
  // 获取配置
  getConfig(): InterruptConfig {
    return { ...this.config };
  }
  
  // 更新配置
  updateConfig(partial: Partial<InterruptConfig>): void {
    this.config = { ...this.config, ...partial };
    this.saveConfig();
  }
  
  // 设置 VAD 监听器
  private setupVADListener(): void {
    vadService.onEvent((event: VADEvent) => {
      if (!this.config.enabled) return;
      
      if (event.type === 'speech_start') {
        this.handleSpeechStart(event);
      }
    });
  }
  
  // 处理语音开始
  private handleSpeechStart(event: VADEvent): void {
    // 检查是否需要打断
    const shouldInterrupt = this.shouldInterrupt();
    
    if (shouldInterrupt) {
      this.performInterrupt('用户开始说话');
    }
  }
  
  // 是否应该打断
  private shouldInterrupt(): boolean {
    // 检查是否正在说话
    const isSpeaking = ttsService.getIsSpeaking();
    const isInCall = voiceCallService.isInCall();
    
    if (isSpeaking && this.config.interruptSpeaking) {
      return true;
    }
    
    if (isInCall) {
      return true;
    }
    
    return false;
  }
  
  // 执行打断
  private async performInterrupt(reason: string): Promise<void> {
    if (this.isInterrupting) return;
    
    this.isInterrupting = true;
    this.state.totalInterrupts++;
    this.state.lastInterruptTime = Date.now();
    
    // 通知打断开始
    this.notifyListeners({
      type: 'interrupt_started',
      timestamp: Date.now(),
      reason,
    });
    
    try {
      // 停止 TTS
      await ttsService.stop();
      
      // 如果在通话中，暂停 AI 回复
      if (voiceCallService.isInCall()) {
        // 通话中的打断逻辑
      }
      
      // 延迟后完成打断
      await this.delay(this.config.delayAfterInterrupt);
      
      this.state.successfulInterrupts++;
      
      // 通知打断完成
      this.notifyListeners({
        type: 'interrupt_completed',
        timestamp: Date.now(),
        reason,
      });
      
    } catch (error) {
      console.error('Interrupt error:', error);
      
      this.state.cancelledInterrupts++;
      
      // 通知打断取消
      this.notifyListeners({
        type: 'interrupt_cancelled',
        timestamp: Date.now(),
        reason: '打断失败',
      });
      
    } finally {
      this.isInterrupting = false;
    }
  }
  
  // 手动触发打断
  async triggerInterrupt(reason: string = '手动打断'): Promise<boolean> {
    if (!this.config.enabled) return false;
    
    await this.performInterrupt(reason);
    return true;
  }
  
  // 是否正在打断
  getIsInterrupting(): boolean {
    return this.isInterrupting;
  }
  
  // 注册事件监听
  onEvent(callback: (event: InterruptEvent) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }
  
  // 通知监听器
  private notifyListeners(event: InterruptEvent): void {
    this.listeners.forEach(listener => listener(event));
  }
  
  // 获取统计信息
  getStats() {
    return { ...this.state };
  }
  
  // 重置统计
  resetStats(): void {
    this.state = {
      totalInterrupts: 0,
      successfulInterrupts: 0,
      cancelledInterrupts: 0,
      lastInterruptTime: 0,
    };
  }
  
  // 延迟
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // 启用/禁用
  setEnabled(enabled: boolean): void {
    this.config.enabled = enabled;
    this.saveConfig();
  }
  
  // 是否启用
  isEnabled(): boolean {
    return this.config.enabled;
  }
}

// 单例
export const interruptService = InterruptService.getInstance();

export default interruptService;
