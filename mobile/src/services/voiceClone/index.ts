// ============================================
// 语音克隆服务 - 移动端版本
// ============================================
import { MMKV } from 'react-native-mmkv';
import * as FileSystem from 'expo-file-system';

const storage = new MMKV();

// 语音克隆引擎
export type VoiceCloneEngine = 
  | 'gpt_sovits'     // GPT-SoVITS
  | 'bark'           // Bark
  | 'tortoise'       // Tortoise TTS
  | 'coqui'          // Coqui TTS
  | 'elevenlabs'     // ElevenLabs
  | 'azure'          // Azure Custom Voice
  | 'custom';        // 自定义API

// 克隆状态
export type CloneStatus = 
  | 'idle'           // 空闲
  | 'uploading'      // 上传中
  | 'processing'     // 处理中
  | 'training'       // 训练中
  | 'ready'          // 就绪
  | 'error';         // 错误

// 音频样本
export interface AudioSample {
  id: string;
  name: string;
  uri: string;
  duration: number;  // 秒
  transcription?: string;
  createdAt: Date;
}

// 克隆语音模型
export interface CloneVoiceModel {
  id: string;
  name: string;
  description: string;
  engine: VoiceCloneEngine;
  status: CloneStatus;
  samples: AudioSample[];
  modelId?: string;   // 云端模型ID
  progress: number;   // 0-100
  createdAt: Date;
  updatedAt: Date;
}

// TTS 配置
export interface CloneTTSConfig {
  modelId: string;
  text: string;
  language?: string;
  speed?: number;
  pitch?: number;
  emotion?: string;
}

// 引擎配置
const ENGINE_CONFIGS: Record<VoiceCloneEngine, {
  name: string;
  description: string;
  icon: string;
  minSamples: number;
  maxSamples: number;
  recommendedDuration: number; // 秒
  supportedFormats: string[];
  isCloud: boolean;
}> = {
  gpt_sovits: {
    name: 'GPT-SoVITS',
    description: '高质量语音克隆，需要3-10分钟音频',
    icon: '🎙️',
    minSamples: 1,
    maxSamples: 20,
    recommendedDuration: 300,
    supportedFormats: ['wav', 'mp3', 'm4a'],
    isCloud: true,
  },
  bark: {
    name: 'Bark',
    description: '快速语音克隆，支持多语言',
    icon: '🐕',
    minSamples: 1,
    maxSamples: 5,
    recommendedDuration: 60,
    supportedFormats: ['wav', 'mp3'],
    isCloud: true,
  },
  tortoise: {
    name: 'Tortoise TTS',
    description: '高质量但较慢的克隆',
    icon: '🐢',
    minSamples: 1,
    maxSamples: 10,
    recommendedDuration: 120,
    supportedFormats: ['wav', 'mp3', 'flac'],
    isCloud: true,
  },
  coqui: {
    name: 'Coqui TTS',
    description: '开源语音克隆方案',
    icon: '🐸',
    minSamples: 1,
    maxSamples: 15,
    recommendedDuration: 180,
    supportedFormats: ['wav', 'mp3'],
    isCloud: true,
  },
  elevenlabs: {
    name: 'ElevenLabs',
    description: '商业级语音克隆，效果最佳',
    icon: '🔊',
    minSamples: 1,
    maxSamples: 25,
    recommendedDuration: 300,
    supportedFormats: ['wav', 'mp3', 'm4a', 'flac'],
    isCloud: true,
  },
  azure: {
    name: 'Azure Custom Voice',
    description: '微软自定义语音',
    icon: '☁️',
    minSamples: 10,
    maxSamples: 200,
    recommendedDuration: 600,
    supportedFormats: ['wav'],
    isCloud: true,
  },
  custom: {
    name: '自定义API',
    description: '使用自定义语音克隆API',
    icon: '⚙️',
    minSamples: 1,
    maxSamples: 50,
    recommendedDuration: 120,
    supportedFormats: ['wav', 'mp3'],
    isCloud: true,
  },
};

// 预设克隆语音
const PRESET_VOICES: CloneVoiceModel[] = [
  {
    id: 'preset_sakura',
    name: '樱花',
    description: '温柔治愈的女声',
    engine: 'gpt_sovits',
    status: 'ready',
    samples: [],
    modelId: 'preset_sakura_v1',
    progress: 100,
    createdAt: new Date('2026-01-01'),
    updatedAt: new Date('2026-01-01'),
  },
  {
    id: 'preset_kuro',
    name: '黑猫',
    description: '傲娇可爱的女声',
    engine: 'gpt_sovits',
    status: 'ready',
    samples: [],
    modelId: 'preset_kuro_v1',
    progress: 100,
    createdAt: new Date('2026-01-01'),
    updatedAt: new Date('2026-01-01'),
  },
  {
    id: 'preset_hoshi',
    name: '星空',
    description: '元气满满的男声',
    engine: 'gpt_sovits',
    status: 'ready',
    samples: [],
    modelId: 'preset_hoshi_v1',
    progress: 100,
    createdAt: new Date('2026-01-01'),
    updatedAt: new Date('2026-01-01'),
  },
];

// 语音克隆服务类
class VoiceCloneService {
  private models: CloneVoiceModel[] = [];
  private currentModel: CloneVoiceModel | null = null;
  private callbacks: Array<(event: string, data: any) => void> = [];
  
  constructor() {
    this.loadModels();
  }
  
  // 加载模型
  private loadModels(): void {
    try {
      const saved = storage.getString('voice_clone_models');
      if (saved) {
        const parsed = JSON.parse(saved);
        this.models = parsed.map((m: any) => ({
          ...m,
          createdAt: new Date(m.createdAt),
          updatedAt: new Date(m.updatedAt),
          samples: m.samples.map((s: any) => ({
            ...s,
            createdAt: new Date(s.createdAt),
          })),
        }));
      }
      
      // 添加预设语音
      const presetIds = this.models.filter(m => m.id.startsWith('preset_')).map(m => m.id);
      PRESET_VOICES.forEach(preset => {
        if (!presetIds.includes(preset.id)) {
          this.models.push(preset);
        }
      });
    } catch (e) {
      console.error('Load voice clone models error:', e);
    }
  }
  
  // 保存模型
  private saveModels(): void {
    try {
      storage.set('voice_clone_models', JSON.stringify(this.models));
    } catch (e) {
      console.error('Save voice clone models error:', e);
    }
  }
  
  // 获取所有引擎配置
  getEngineConfigs(): Record<VoiceCloneEngine, typeof ENGINE_CONFIGS[VoiceCloneEngine]> {
    return { ...ENGINE_CONFIGS };
  }
  
  // 获取引擎配置
  getEngineConfig(engine: VoiceCloneEngine): typeof ENGINE_CONFIGS[VoiceCloneEngine] {
    return ENGINE_CONFIGS[engine];
  }
  
  // 获取所有模型
  getModels(): CloneVoiceModel[] {
    return [...this.models];
  }
  
  // 获取预设模型
  getPresetModels(): CloneVoiceModel[] {
    return this.models.filter(m => m.id.startsWith('preset_'));
  }
  
  // 获取用户自定义模型
  getUserModels(): CloneVoiceModel[] {
    return this.models.filter(m => !m.id.startsWith('preset_'));
  }
  
  // 获取指定模型
  getModel(id: string): CloneVoiceModel | undefined {
    return this.models.find(m => m.id === id);
  }
  
  // 创建新模型
  createModel(name: string, description: string, engine: VoiceCloneEngine): CloneVoiceModel {
    const model: CloneVoiceModel = {
      id: `clone_${Date.now()}`,
      name,
      description,
      engine,
      status: 'idle',
      samples: [],
      progress: 0,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    this.models.push(model);
    this.saveModels();
    
    this.notify('model_created', { model });
    
    return model;
  }
  
  // 删除模型
  deleteModel(id: string): boolean {
    const index = this.models.findIndex(m => m.id === id);
    if (index === -1 || id.startsWith('preset_')) return false;
    
    this.models.splice(index, 1);
    
    if (this.currentModel?.id === id) {
      this.currentModel = null;
    }
    
    this.saveModels();
    this.notify('model_deleted', { id });
    
    return true;
  }
  
  // 添加音频样本
  async addSample(modelId: string, audioUri: string, name: string): Promise<AudioSample | null> {
    const model = this.getModel(modelId);
    if (!model) return null;
    
    const sample: AudioSample = {
      id: `sample_${Date.now()}`,
      name,
      uri: audioUri,
      duration: 0, // 需要实际获取
      createdAt: new Date(),
    };
    
    model.samples.push(sample);
    model.updatedAt = new Date();
    this.saveModels();
    
    this.notify('sample_added', { model, sample });
    
    return sample;
  }
  
  // 删除音频样本
  removeSample(modelId: string, sampleId: string): boolean {
    const model = this.getModel(modelId);
    if (!model) return false;
    
    const index = model.samples.findIndex(s => s.id === sampleId);
    if (index === -1) return false;
    
    model.samples.splice(index, 1);
    model.updatedAt = new Date();
    this.saveModels();
    
    return true;
  }
  
  // 开始训练
  async startTraining(modelId: string): Promise<boolean> {
    const model = this.getModel(modelId);
    if (!model) return false;
    
    const config = ENGINE_CONFIGS[model.engine];
    
    // 检查样本数量
    if (model.samples.length < config.minSamples) {
      this.notify('error', { 
        message: `至少需要 ${config.minSamples} 个音频样本`,
        model 
      });
      return false;
    }
    
    // 更新状态
    model.status = 'uploading';
    model.progress = 0;
    this.saveModels();
    this.notify('training_started', { model });
    
    // 模拟训练过程
    this.simulateTraining(model);
    
    return true;
  }
  
  // 模拟训练过程
  private async simulateTraining(model: CloneVoiceModel): Promise<void> {
    const stages = [
      { status: 'uploading' as CloneStatus, progress: 20, delay: 1000 },
      { status: 'processing' as CloneStatus, progress: 40, delay: 1500 },
      { status: 'training' as CloneStatus, progress: 60, delay: 2000 },
      { status: 'training' as CloneStatus, progress: 80, delay: 1500 },
      { status: 'ready' as CloneStatus, progress: 100, delay: 500 },
    ];
    
    for (const stage of stages) {
      await new Promise(resolve => setTimeout(resolve, stage.delay));
      
      model.status = stage.status;
      model.progress = stage.progress;
      model.updatedAt = new Date();
      this.saveModels();
      
      this.notify('training_progress', { 
        model, 
        status: stage.status, 
        progress: stage.progress 
      });
    }
    
    model.modelId = `model_${model.id}_${Date.now()}`;
    this.saveModels();
    this.notify('training_complete', { model });
  }
  
  // 使用克隆语音生成TTS
  async generateSpeech(config: CloneTTSConfig): Promise<string | null> {
    const model = this.getModel(config.modelId);
    if (!model || model.status !== 'ready') {
      this.notify('error', { message: '语音模型未就绪' });
      return null;
    }
    
    this.notify('tts_started', { model, text: config.text });
    
    // 模拟TTS生成
    await new Promise(resolve => setTimeout(resolve, 500));
    
    this.notify('tts_complete', { model, text: config.text });
    
    // 返回模拟的音频URI
    return `${FileSystem.cacheDirectory}tts_${Date.now()}.wav`;
  }
  
  // 获取当前模型
  getCurrentModel(): CloneVoiceModel | null {
    return this.currentModel;
  }
  
  // 设置当前模型
  setCurrentModel(modelId: string): boolean {
    const model = this.getModel(modelId);
    if (!model || model.status !== 'ready') return false;
    
    this.currentModel = model;
    this.notify('model_changed', { model });
    
    return true;
  }
  
  // 获取模型统计
  getStats(): {
    totalModels: number;
    readyModels: number;
    trainingModels: number;
    totalSamples: number;
  } {
    return {
      totalModels: this.models.length,
      readyModels: this.models.filter(m => m.status === 'ready').length,
      trainingModels: this.models.filter(m => 
        m.status === 'uploading' || m.status === 'processing' || m.status === 'training'
      ).length,
      totalSamples: this.models.reduce((sum, m) => sum + m.samples.length, 0),
    };
  }
  
  // 添加事件回调
  onEvent(callback: (event: string, data: any) => void): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }
  
  // 通知事件
  private notify(event: string, data: any): void {
    this.callbacks.forEach(cb => {
      try {
        cb(event, data);
      } catch (e) {
        console.error('Voice clone callback error:', e);
      }
    });
  }
  
  // 获取状态描述
  getStatusDescription(status: CloneStatus): string {
    const descriptions: Record<CloneStatus, string> = {
      idle: '等待开始',
      uploading: '上传音频中...',
      processing: '处理音频中...',
      training: '训练模型中...',
      ready: '就绪',
      error: '出错',
    };
    return descriptions[status];
  }
  
  // 获取状态颜色
  getStatusColor(status: CloneStatus): string {
    const colors: Record<CloneStatus, string> = {
      idle: '#6b7280',
      uploading: '#3b82f6',
      processing: '#f59e0b',
      training: '#8b5cf6',
      ready: '#10b981',
      error: '#ef4444',
    };
    return colors[status];
  }
}

// 导出单例
export const voiceCloneService = new VoiceCloneService();