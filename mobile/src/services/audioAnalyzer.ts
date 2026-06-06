// 音频分析器 - 用于口型同步
// 分析音频流的音量和频率，生成口型同步参数

export interface AudioAnalysisResult {
  volume: number; // 0-1 音量
  pitch: number; // 0-1 音高
  vowel: 'a' | 'i' | 'u' | 'e' | 'o'; // 母音
  isSilent: boolean; // 是否静音
}

class AudioAnalyzer {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private frequencyData: Uint8Array | null = null;
  private isInitialized = false;
  
  // 初始化音频分析器
  async initialize(): Promise<boolean> {
    try {
      // 在 React Native 中，我们需要使用 expo-av 或其他方式获取音频流
      // 这里提供一个基础框架
      
      if (typeof window !== 'undefined' && window.AudioContext) {
        this.audioContext = new AudioContext();
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        
        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
        this.frequencyData = new Uint8Array(bufferLength);
        
        this.isInitialized = true;
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('AudioAnalyzer init error:', error);
      return false;
    }
  }
  
  // 连接音频源
  connectSource(audioElement: HTMLAudioElement): boolean {
    if (!this.audioContext || !this.analyser) return false;
    
    try {
      const source = this.audioContext.createMediaElementSource(audioElement);
      source.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      return true;
    } catch (error) {
      console.error('Connect source error:', error);
      return false;
    }
  }
  
  // 分析当前音频帧
  analyze(): AudioAnalysisResult {
    if (!this.isInitialized || !this.analyser || !this.dataArray) {
      return {
        volume: 0,
        pitch: 0,
        vowel: 'a',
        isSilent: true
      };
    }
    
    // 获取时域数据（音量）
    this.analyser.getByteTimeDomainData(this.dataArray);
    
    // 计算 RMS 音量
    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) {
      const amplitude = (this.dataArray[i] - 128) / 128;
      sum += amplitude * amplitude;
    }
    const rms = Math.sqrt(sum / this.dataArray.length);
    const volume = Math.min(1, rms * 3); // 放大并限制在 0-1
    
    // 获取频域数据（音高和母音）
    this.analyser.getByteFrequencyData(this.frequencyData!);
    
    // 计算主频率
    let maxFreq = 0;
    let maxFreqIndex = 0;
    for (let i = 0; i < this.frequencyData!.length; i++) {
      if (this.frequencyData![i] > maxFreq) {
        maxFreq = this.frequencyData![i];
        maxFreqIndex = i;
      }
    }
    
    // 归一化音高 (0-1)
    const pitch = maxFreqIndex / this.frequencyData!.length;
    
    // 根据频率分布估算母音
    const vowel = this.estimateVowel(this.frequencyData!);
    
    return {
      volume,
      pitch,
      vowel,
      isSilent: volume < 0.05
    };
  }
  
  // 根据频率分布估算母音
  private estimateVowel(frequencyData: Uint8Array): 'a' | 'i' | 'u' | 'e' | 'o' {
    // 简化的母音识别
    // 实际应用中需要更复杂的频率分析
    
    const lowFreq = this.getAverageAmplitude(frequencyData, 0, 0.2);
    const midFreq = this.getAverageAmplitude(frequencyData, 0.2, 0.5);
    const highFreq = this.getAverageAmplitude(frequencyData, 0.5, 1.0);
    
    // 基于频率分布的简单规则
    if (lowFreq > midFreq && lowFreq > highFreq) {
      return 'o'; // 低频为主 -> o
    } else if (highFreq > midFreq) {
      return 'i'; // 高频为主 -> i
    } else if (midFreq > lowFreq * 1.5) {
      return 'e'; // 中频突出 -> e
    } else if (lowFreq > midFreq * 0.8) {
      return 'a'; // 低中频均衡 -> a
    } else {
      return 'u'; // 其他情况 -> u
    }
  }
  
  // 获取指定频率范围的平均振幅
  private getAverageAmplitude(data: Uint8Array, start: number, end: number): number {
    const startIndex = Math.floor(start * data.length);
    const endIndex = Math.floor(end * data.length);
    let sum = 0;
    
    for (let i = startIndex; i < endIndex; i++) {
      sum += data[i];
    }
    
    return sum / (endIndex - startIndex);
  }
  
  // 清理资源
  dispose() {
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.analyser = null;
    this.dataArray = null;
    this.frequencyData = null;
    this.isInitialized = false;
  }
}

// 单例模式
export const audioAnalyzer = new AudioAnalyzer();

// 用于 React Native 的简化版本
// 不依赖 Web Audio API，而是接收外部音量数据
export class SimpleLipSync {
  private currentVolume = 0;
  private targetVolume = 0;
  private smoothing = 0.3;
  private timer: NodeJS.Timeout | null = null;
  
  // 设置目标音量 (0-1)
  setVolume(volume: number) {
    this.targetVolume = Math.min(1, Math.max(0, volume));
  }
  
  // 模拟说话时的口型变化
  startSimulation() {
    if (this.timer) return;
    
    this.timer = setInterval(() => {
      // 平滑过渡
      this.currentVolume += (this.targetVolume - this.currentVolume) * this.smoothing;
      
      // 添加随机波动
      if (this.targetVolume > 0) {
        this.currentVolume += (Math.random() - 0.5) * 0.1;
        this.currentVolume = Math.min(1, Math.max(0, this.currentVolume));
      }
    }, 50);
  }
  
  // 停止模拟
  stopSimulation() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.currentVolume = 0;
    this.targetVolume = 0;
  }
  
  // 获取当前音量
  getVolume(): number {
    return this.currentVolume;
  }
  
  // 获取当前母音（简化版）
  getVowel(): 'a' | 'i' | 'u' | 'e' | 'o' {
    if (this.currentVolume < 0.1) return 'a';
    
    const vowels: Array<'a' | 'i' | 'u' | 'e' | 'o'> = ['a', 'i', 'u', 'e', 'o'];
    const index = Math.floor(Math.random() * vowels.length);
    return vowels[index];
  }
}

// 导出简化版实例
export const simpleLipSync = new SimpleLipSync();
