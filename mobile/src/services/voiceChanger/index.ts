// ============================================
// 变声服务 - 移动端版本
// ============================================
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV();

// 音效类型
export type VoiceEffect = 
  | 'normal'      // 正常
  | 'male'        // 男声
  | 'female'      // 女声
  | 'child'       // 童声
  | 'elder'       // 老人声
  | 'cartoon'     // 卡通声
  | 'robot'       // 机器人
  | 'deep'        // 低沉
  | 'high'        // 高亢
  | 'echo'        // 回声
  | 'whisper'     // 耳语
  | 'monster'     // 怪兽
  | 'alien'       // 外星人
  | 'chipmunk'    // 花栗鼠
  | 'darth_vader' // 黑武士
  | 'custom';     // 自定义

// 音效配置
export interface VoiceEffectConfig {
  id: VoiceEffect;
  name: string;
  description: string;
  icon: string;
  params: VoiceParams;
}

// 语音参数
export interface VoiceParams {
  pitch: number;      // 音高 (-12 到 +12 半音)
  formant: number;    // 共振峰 (0.5 到 2.0)
  rate: number;       // 语速 (0.5 到 2.0)
  reverb: number;     // 混响 (0 到 1)
  echo: number;       // 回声 (0 到 1)
  distortion: number; // 失真 (0 到 1)
  chorus: number;     // 合唱 (0 到 1)
  volume: number;     // 音量 (0 到 1)
}

// 预设音效
const VOICE_EFFECTS: VoiceEffectConfig[] = [
  {
    id: 'normal',
    name: '正常',
    description: '原始声音',
    icon: '🎤',
    params: { pitch: 0, formant: 1.0, rate: 1.0, reverb: 0, echo: 0, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'male',
    name: '男声',
    description: '低沉的男声',
    icon: '👨',
    params: { pitch: -4, formant: 0.85, rate: 0.95, reverb: 0.1, echo: 0, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'female',
    name: '女声',
    description: '温柔的女声',
    icon: '👩',
    params: { pitch: 4, formant: 1.15, rate: 1.05, reverb: 0.1, echo: 0, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'child',
    name: '童声',
    description: '可爱的童声',
    icon: '👶',
    params: { pitch: 8, formant: 1.3, rate: 1.1, reverb: 0.1, echo: 0, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'elder',
    name: '老人声',
    description: '沧桑的老人声',
    icon: '👴',
    params: { pitch: -2, formant: 0.9, rate: 0.85, reverb: 0.2, echo: 0.1, distortion: 0.05, chorus: 0, volume: 1.0 },
  },
  {
    id: 'cartoon',
    name: '卡通声',
    description: '有趣的卡通声',
    icon: '🐭',
    params: { pitch: 6, formant: 1.4, rate: 1.2, reverb: 0.1, echo: 0.1, distortion: 0, chorus: 0.2, volume: 1.0 },
  },
  {
    id: 'robot',
    name: '机器人',
    description: '机械的机器人声',
    icon: '🤖',
    params: { pitch: 0, formant: 1.0, rate: 0.9, reverb: 0.3, echo: 0.2, distortion: 0.4, chorus: 0.3, volume: 1.0 },
  },
  {
    id: 'deep',
    name: '低沉',
    description: '深沉的声音',
    icon: '🎸',
    params: { pitch: -8, formant: 0.7, rate: 0.9, reverb: 0.2, echo: 0.1, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'high',
    name: '高亢',
    description: '尖锐的高音',
    icon: '🎺',
    params: { pitch: 10, formant: 1.5, rate: 1.1, reverb: 0.1, echo: 0, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'echo',
    name: '回声',
    description: '山谷回声效果',
    icon: '🏔️',
    params: { pitch: 0, formant: 1.0, rate: 1.0, reverb: 0.5, echo: 0.6, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'whisper',
    name: '耳语',
    description: '轻声细语',
    icon: '🤫',
    params: { pitch: -1, formant: 0.95, rate: 0.8, reverb: 0.3, echo: 0.1, distortion: 0.1, chorus: 0, volume: 0.6 },
  },
  {
    id: 'monster',
    name: '怪兽',
    description: '恐怖的怪兽声',
    icon: '👹',
    params: { pitch: -10, formant: 0.6, rate: 0.8, reverb: 0.4, echo: 0.3, distortion: 0.5, chorus: 0.2, volume: 1.2 },
  },
  {
    id: 'alien',
    name: '外星人',
    description: '神秘的外星声',
    icon: '👽',
    params: { pitch: 3, formant: 1.6, rate: 1.1, reverb: 0.4, echo: 0.4, distortion: 0.2, chorus: 0.5, volume: 1.0 },
  },
  {
    id: 'chipmunk',
    name: '花栗鼠',
    description: '可爱的花栗鼠声',
    icon: '🐿️',
    params: { pitch: 12, formant: 1.8, rate: 1.3, reverb: 0.1, echo: 0, distortion: 0, chorus: 0, volume: 1.0 },
  },
  {
    id: 'darth_vader',
    name: '黑武士',
    description: '沉重的呼吸声',
    icon: '⚔️',
    params: { pitch: -6, formant: 0.75, rate: 0.85, reverb: 0.3, echo: 0.2, distortion: 0.3, chorus: 0.1, volume: 1.1 },
  },
];

// 变声服务类
class VoiceChangerService {
  private currentEffect: VoiceEffect = 'normal';
  private currentParams: VoiceParams;
  private effects: VoiceEffectConfig[] = VOICE_EFFECTS;
  private customEffects: VoiceEffectConfig[] = [];
  private callbacks: Array<(effect: VoiceEffect, params: VoiceParams) => void> = [];
  
  constructor() {
    this.currentParams = this.getEffectConfig('normal').params;
    this.loadSavedSettings();
  }
  
  // 加载保存的设置
  private loadSavedSettings(): void {
    try {
      const savedEffect = storage.getString('voice_effect');
      const savedParams = storage.getString('voice_params');
      
      if (savedEffect && this.isValidEffect(savedEffect)) {
        this.currentEffect = savedEffect as VoiceEffect;
      }
      
      if (savedParams) {
        this.currentParams = JSON.parse(savedParams);
      }
      
      // 加载自定义音效
      const savedCustom = storage.getString('custom_voice_effects');
      if (savedCustom) {
        this.customEffects = JSON.parse(savedCustom);
      }
    } catch (e) {
      console.error('Load voice settings error:', e);
    }
  }
  
  // 保存设置
  private saveSettings(): void {
    try {
      storage.set('voice_effect', this.currentEffect);
      storage.set('voice_params', JSON.stringify(this.currentParams));
      storage.set('custom_voice_effects', JSON.stringify(this.customEffects));
    } catch (e) {
      console.error('Save voice settings error:', e);
    }
  }
  
  // 验证音效是否有效
  private isValidEffect(effect: string): boolean {
    return this.effects.some(e => e.id === effect) || 
           this.customEffects.some(e => e.id === effect);
  }
  
  // 获取所有音效
  getAllEffects(): VoiceEffectConfig[] {
    return [...this.effects, ...this.customEffects];
  }
  
  // 获取预设音效
  getPresetEffects(): VoiceEffectConfig[] {
    return [...this.effects];
  }
  
  // 获取自定义音效
  getCustomEffects(): VoiceEffectConfig[] {
    return [...this.customEffects];
  }
  
  // 获取音效配置
  getEffectConfig(effect: VoiceEffect): VoiceEffectConfig {
    const preset = this.effects.find(e => e.id === effect);
    if (preset) return preset;
    
    const custom = this.customEffects.find(e => e.id === effect);
    if (custom) return custom;
    
    // 返回默认配置
    return this.effects[0];
  }
  
  // 设置当前音效
  setEffect(effect: VoiceEffect): void {
    this.currentEffect = effect;
    this.currentParams = this.getEffectConfig(effect).params;
    this.saveSettings();
    this.notifyChange();
  }
  
  // 获取当前音效
  getCurrentEffect(): VoiceEffect {
    return this.currentEffect;
  }
  
  // 获取当前参数
  getCurrentParams(): VoiceParams {
    return { ...this.currentParams };
  }
  
  // 更新参数
  updateParams(params: Partial<VoiceParams>): void {
    this.currentParams = { ...this.currentParams, ...params };
    this.saveSettings();
    this.notifyChange();
  }
  
  // 重置参数
  resetParams(): void {
    this.currentParams = this.getEffectConfig(this.currentEffect).params;
    this.saveSettings();
    this.notifyChange();
  }
  
  // 添加变更回调
  onEffectChange(callback: (effect: VoiceEffect, params: VoiceParams) => void): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }
  
  // 通知变更
  private notifyChange(): void {
    this.callbacks.forEach(cb => {
      try {
        cb(this.currentEffect, this.currentParams);
      } catch (e) {
        console.error('Voice change callback error:', e);
      }
    });
  }
  
  // 创建自定义音效
  createCustomEffect(name: string, description: string, params: VoiceParams): VoiceEffectConfig {
    const id = `custom_${Date.now()}` as VoiceEffect;
    const newEffect: VoiceEffectConfig = {
      id,
      name,
      description,
      icon: '🎵',
      params,
    };
    
    this.customEffects.push(newEffect);
    this.saveSettings();
    
    return newEffect;
  }
  
  // 更新自定义音效
  updateCustomEffect(id: VoiceEffect, updates: Partial<VoiceEffectConfig>): boolean {
    const index = this.customEffects.findIndex(e => e.id === id);
    if (index === -1) return false;
    
    this.customEffects[index] = { ...this.customEffects[index], ...updates };
    this.saveSettings();
    
    return true;
  }
  
  // 删除自定义音效
  deleteCustomEffect(id: VoiceEffect): boolean {
    const index = this.customEffects.findIndex(e => e.id === id);
    if (index === -1) return false;
    
    this.customEffects.splice(index, 1);
    
    // 如果删除的是当前音效，切换到正常
    if (this.currentEffect === id) {
      this.setEffect('normal');
    }
    
    this.saveSettings();
    return true;
  }
  
  // 获取参数范围
  getParamRange(param: keyof VoiceParams): { min: number; max: number; step: number } {
    const ranges: Record<keyof VoiceParams, { min: number; max: number; step: number }> = {
      pitch: { min: -12, max: 12, step: 1 },
      formant: { min: 0.5, max: 2.0, step: 0.05 },
      rate: { min: 0.5, max: 2.0, step: 0.05 },
      reverb: { min: 0, max: 1, step: 0.05 },
      echo: { min: 0, max: 1, step: 0.05 },
      distortion: { min: 0, max: 1, step: 0.05 },
      chorus: { min: 0, max: 1, step: 0.05 },
      volume: { min: 0, max: 1.5, step: 0.05 },
    };
    
    return ranges[param];
  }
  
  // 处理音频数据（模拟）
  processAudio(audioData: ArrayBuffer): ArrayBuffer {
    // 在实际实现中，这里会使用 Web Audio API 或原生音频处理
    // 目前返回原始数据
    return audioData;
  }
  
  // 获取音效描述
  getEffectDescription(effect: VoiceEffect): string {
    const config = this.getEffectConfig(effect);
    return `${config.name}: ${config.description}`;
  }
  
  // 获取音效预览文本
  getEffectPreview(effect: VoiceEffect): string {
    const config = this.getEffectConfig(effect);
    const params = config.params;
    
    const features: string[] = [];
    
    if (params.pitch > 0) features.push('高音');
    if (params.pitch < 0) features.push('低音');
    if (params.reverb > 0.3) features.push('混响');
    if (params.echo > 0.3) features.push('回声');
    if (params.distortion > 0.3) features.push('失真');
    if (params.chorus > 0.3) features.push('合唱');
    
    return features.length > 0 ? features.join(', ') : '正常';
  }
}

// 导出单例
export const voiceChangerService = new VoiceChangerService();