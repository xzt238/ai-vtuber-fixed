// ============================================
// VAD (Voice Activity Detection) 语音活动检测
// ============================================
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV({ id: 'vad-service' });

// VAD 状态
export type VADState = 'idle' | 'active' | 'inactive';

// VAD 配置
export interface VADConfig {
  // 音量阈值 (0-1)
  volumeThreshold: number;
  
  // 激活所需连续帧数
  activationFrames: number;
  
  // 停止所需连续帧数
  deactivationFrames: number;
  
  // 是否启用
  enabled: boolean;
}

// 默认配置
const DEFAULT_CONFIG: VADConfig = {
  volumeThreshold: 0.15,
  activationFrames: 3,
  deactivationFrames: 15,
  enabled: true,
};

// VAD 事件
export interface VADEvent {
  type: 'speech_start' | 'speech_end' | 'state_change';
  state: VADState;
  timestamp: number;
  volume: number;
}

class VADService {
  private static instance: VADService;
  private config: VADConfig;
  private state: VADState = 'idle';
  private hitCount: number = 0;
  private missCount: number = 0;
  private isListening: boolean = false;
  
  // 事件回调
  private listeners: Array<(event: VADEvent) => void> = [];
  
  // 统计
  private stats = {
    totalFrames: 0,
    speechFrames: 0,
    silenceFrames: 0,
    stateTransitions: 0,
  };
  
  private constructor() {
    this.config = this.loadConfig();
  }
  
  static getInstance(): VADService {
    if (!VADService.instance) {
      VADService.instance = new VADService();
    }
    return VADService.instance;
  }
  
  // 加载配置
  private loadConfig(): VADConfig {
    try {
      const saved = storage.getString('vad_config');
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load VAD config error:', e);
    }
    return { ...DEFAULT_CONFIG };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('vad_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save VAD config error:', e);
    }
  }
  
  // 获取配置
  getConfig(): VADConfig {
    return { ...this.config };
  }
  
  // 更新配置
  updateConfig(partial: Partial<VADConfig>): void {
    this.config = { ...this.config, ...partial };
    this.saveConfig();
  }
  
  // 获取当前状态
  getState(): VADState {
    return this.state;
  }
  
  // 是否正在监听
  getIsListening(): boolean {
    return this.isListening;
  }
  
  // 开始监听
  startListening(): void {
    this.isListening = true;
    this.state = 'idle';
    this.hitCount = 0;
    this.missCount = 0;
    
    this.notifyListeners({
      type: 'state_change',
      state: 'idle',
      timestamp: Date.now(),
      volume: 0,
    });
  }
  
  // 停止监听
  stopListening(): void {
    this.isListening = false;
    
    if (this.state === 'active') {
      this.notifyListeners({
        type: 'speech_end',
        state: 'inactive',
        timestamp: Date.now(),
        volume: 0,
      });
    }
    
    this.state = 'idle';
    this.hitCount = 0;
    this.missCount = 0;
  }
  
  // 处理音频音量
  processVolume(volume: number): VADEvent | null {
    if (!this.isListening || !this.config.enabled) {
      return null;
    }
    
    this.stats.totalFrames++;
    
    const isSpeech = volume >= this.config.volumeThreshold;
    
    if (isSpeech) {
      this.stats.speechFrames++;
      this.hitCount++;
      this.missCount = 0;
    } else {
      this.stats.silenceFrames++;
      this.missCount++;
      this.hitCount = 0;
    }
    
    let event: VADEvent | null = null;
    
    // 状态转换逻辑
    switch (this.state) {
      case 'idle':
        if (this.hitCount >= this.config.activationFrames) {
          this.state = 'active';
          this.stats.stateTransitions++;
          event = {
            type: 'speech_start',
            state: 'active',
            timestamp: Date.now(),
            volume,
          };
        }
        break;
        
      case 'active':
        if (this.missCount >= this.config.deactivationFrames) {
          this.state = 'inactive';
          this.stats.stateTransitions++;
          event = {
            type: 'speech_end',
            state: 'inactive',
            timestamp: Date.now(),
            volume,
          };
        }
        break;
        
      case 'inactive':
        if (this.hitCount >= this.config.activationFrames) {
          this.state = 'active';
          this.stats.stateTransitions++;
          event = {
            type: 'speech_start',
            state: 'active',
            timestamp: Date.now(),
            volume,
          };
        } else if (this.missCount >= this.config.deactivationFrames * 2) {
          this.state = 'idle';
          event = {
            type: 'state_change',
            state: 'idle',
            timestamp: Date.now(),
            volume,
          };
        }
        break;
    }
    
    if (event) {
      this.notifyListeners(event);
    }
    
    return event;
  }
  
  // 注册事件监听
  onEvent(callback: (event: VADEvent) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }
  
  // 通知监听器
  private notifyListeners(event: VADEvent): void {
    this.listeners.forEach(listener => listener(event));
  }
  
  // 获取统计信息
  getStats() {
    return { ...this.stats };
  }
  
  // 重置统计
  resetStats(): void {
    this.stats = {
      totalFrames: 0,
      speechFrames: 0,
      silenceFrames: 0,
      stateTransitions: 0,
    };
  }
  
  // 是否检测到语音
  isSpeechDetected(): boolean {
    return this.state === 'active';
  }
  
  // 重置状态
  reset(): void {
    this.state = 'idle';
    this.hitCount = 0;
    this.missCount = 0;
  }
}

// 单例
export const vadService = VADService.getInstance();

export default vadService;
