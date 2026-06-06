// ============================================
// 视觉输入服务 - 移动端版本
// ============================================
import { MMKV } from 'react-native-mmkv';
import { localAI } from '../localAI';

const storage = new MMKV();

// 视觉分析类型
export type VisionAnalysisType = 
  | 'object_detection'
  | 'scene_description'
  | 'text_recognition'
  | 'face_detection'
  | 'emotion_recognition'
  | 'color_analysis'
  | 'general';

// 视觉结果
export interface VisionResult {
  id: string;
  type: VisionAnalysisType;
  description: string;
  objects: DetectedObject[];
  text: string;
  emotions: DetectedEmotion[];
  colors: ColorInfo[];
  confidence: number;
  timestamp: number;
  imageUrl?: string;
}

// 检测到的物体
export interface DetectedObject {
  name: string;
  confidence: number;
  boundingBox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

// 检测到的情感
export interface DetectedEmotion {
  emotion: string;
  confidence: number;
  person?: string;
}

// 颜色信息
export interface ColorInfo {
  color: string;
  hex: string;
  percentage: number;
}

// 视觉配置
export interface VisionConfig {
  analysisType: VisionAnalysisType;
  maxObjects: number;
  includeColors: boolean;
  includeEmotions: boolean;
  language: string;
}

// 默认配置
const DEFAULT_CONFIG: VisionConfig = {
  analysisType: 'general',
  maxObjects: 10,
  includeColors: true,
  includeEmotions: true,
  language: 'zh',
};

// 视觉分析服务类
class VisionService {
  private config: VisionConfig = DEFAULT_CONFIG;
  private analysisHistory: VisionResult[] = [];
  private callbacks: Array<(result: VisionResult) => void> = [];
  
  constructor() {
    this.loadHistory();
  }
  
  // 加载历史记录
  private loadHistory(): void {
    try {
      const saved = storage.getString('vision_history');
      if (saved) {
        this.analysisHistory = JSON.parse(saved).map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp).getTime(),
        }));
      }
    } catch (e) {
      console.error('Load vision history error:', e);
    }
  }
  
  // 保存历史记录
  private saveHistory(): void {
    try {
      storage.set('vision_history', JSON.stringify(this.analysisHistory.slice(-50)));
    } catch (e) {
      console.error('Save vision history error:', e);
    }
  }
  
  // 更新配置
  updateConfig(updates: Partial<VisionConfig>): void {
    this.config = { ...this.config, ...updates };
  }
  
  // 获取配置
  getConfig(): VisionConfig {
    return { ...this.config };
  }
  
  // 添加分析回调
  onAnalysis(callback: (result: VisionResult) => void): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }
  
  // 通知分析结果
  private notifyResult(result: VisionResult): void {
    this.callbacks.forEach(cb => {
      try {
        cb(result);
      } catch (e) {
        console.error('Vision callback error:', e);
      }
    });
  }
  
  // 分析图像（基于描述）
  async analyzeImage(imageDescription: string, analysisType: VisionAnalysisType = 'general'): Promise<VisionResult> {
    const resultId = `vision_${Date.now()}`;
    
    // 构建提示词
    let prompt = '';
    switch (analysisType) {
      case 'object_detection':
        prompt = `请识别以下图像中的物体，列出所有可识别的物体名称和位置：${imageDescription}`;
        break;
      case 'scene_description':
        prompt = `请详细描述以下图像的场景，包括环境、光线、氛围等：${imageDescription}`;
        break;
      case 'text_recognition':
        prompt = `请识别以下图像中的所有文字内容：${imageDescription}`;
        break;
      case 'emotion_recognition':
        prompt = `请分析以下图像中人物的情感状态：${imageDescription}`;
        break;
      case 'color_analysis':
        prompt = `请分析以下图像的主要颜色组成：${imageDescription}`;
        break;
      default:
        prompt = `请全面分析以下图像，包括物体识别、场景描述、情感分析等：${imageDescription}`;
    }
    
    try {
      // 使用本地AI生成分析结果
      const response = await localAI.generateResponse(
        prompt,
        { id: 'vision', name: '视觉分析', personality: '图像分析专家' } as any,
        [],
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.7, maxTokens: 500, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      // 解析结果
      const result: VisionResult = {
        id: resultId,
        type: analysisType,
        description: response,
        objects: this.extractObjects(response),
        text: this.extractText(response),
        emotions: this.extractEmotions(response),
        colors: this.extractColors(response),
        confidence: 0.85,
        timestamp: Date.now(),
      };
      
      // 保存到历史
      this.analysisHistory.push(result);
      this.saveHistory();
      
      // 通知回调
      this.notifyResult(result);
      
      return result;
    } catch (error) {
      console.error('Vision analysis error:', error);
      throw error;
    }
  }
  
  // 从文本中提取物体
  private extractObjects(text: string): DetectedObject[] {
    const objects: DetectedObject[] = [];
    const objectPatterns = [
      /(?:识别到|检测到|发现|有|包含).*?([^\s,，。、]+(?:人|物|车|建筑|树|花|动物|家具|设备|工具|食物|饮品))/g,
      /([^\s,，。、]+(?:人|物|车|建筑|树|花|动物|家具|设备|工具|食物|饮品))/g,
    ];
    
    objectPatterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        if (match[1] && match[1].length > 1) {
          objects.push({
            name: match[1],
            confidence: 0.8,
          });
        }
      }
    });
    
    return objects.slice(0, this.config.maxObjects);
  }
  
  // 从文本中提取文字
  private extractText(text: string): string {
    const textPatterns = [
      /(?:文字|内容|写着|显示).*?["""](.+?)["""']/g,
      /["""](.+?)["""']/g,
    ];
    
    for (const pattern of textPatterns) {
      const match = pattern.exec(text);
      if (match && match[1]) {
        return match[1];
      }
    }
    
    return '';
  }
  
  // 从文本中提取情感
  private extractEmotions(text: string): DetectedEmotion[] {
    const emotions: DetectedEmotion[] = [];
    const emotionKeywords: Record<string, string[]> = {
      '开心': ['开心', '高兴', '快乐', '愉快', '喜悦', '微笑', '笑'],
      '悲伤': ['悲伤', '难过', '伤心', '沮丧', '忧郁', '哭'],
      '愤怒': ['愤怒', '生气', '恼怒', '暴怒', '不满'],
      '惊讶': ['惊讶', '吃惊', '震惊', '意外', '惊喜'],
      '恐惧': ['恐惧', '害怕', '惊恐', '担忧', '紧张'],
      '平静': ['平静', '冷静', '镇定', '放松', '自然'],
    };
    
    Object.entries(emotionKeywords).forEach(([emotion, keywords]) => {
      const found = keywords.some(keyword => text.includes(keyword));
      if (found) {
        emotions.push({
          emotion,
          confidence: 0.75,
        });
      }
    });
    
    return emotions;
  }
  
  // 从文本中提取颜色
  private extractColors(text: string): ColorInfo[] {
    const colors: ColorInfo[] = [];
    const colorKeywords: Record<string, string> = {
      '红色': '#FF0000',
      '蓝色': '#0000FF',
      '绿色': '#00FF00',
      '黄色': '#FFFF00',
      '紫色': '#800080',
      '橙色': '#FFA500',
      '粉色': '#FFC0CB',
      '黑色': '#000000',
      '白色': '#FFFFFF',
      '灰色': '#808080',
      '棕色': '#A52A2A',
    };
    
    Object.entries(colorKeywords).forEach(([color, hex]) => {
      if (text.includes(color)) {
        colors.push({
          color,
          hex,
          percentage: 20,
        });
      }
    });
    
    return colors;
  }
  
  // 获取分析历史
  getHistory(): VisionResult[] {
    return [...this.analysisHistory];
  }
  
  // 清除历史
  clearHistory(): void {
    this.analysisHistory = [];
    this.saveHistory();
  }
  
  // 获取统计信息
  getStats(): {
    totalAnalyses: number;
    byType: Record<VisionAnalysisType, number>;
    averageConfidence: number;
  } {
    const byType: Record<VisionAnalysisType, number> = {
      object_detection: 0,
      scene_description: 0,
      text_recognition: 0,
      face_detection: 0,
      emotion_recognition: 0,
      color_analysis: 0,
      general: 0,
    };
    
    let totalConfidence = 0;
    
    this.analysisHistory.forEach(result => {
      byType[result.type]++;
      totalConfidence += result.confidence;
    });
    
    return {
      totalAnalyses: this.analysisHistory.length,
      byType,
      averageConfidence: this.analysisHistory.length > 0 
        ? totalConfidence / this.analysisHistory.length 
        : 0,
    };
  }
  
  // 分析摄像头画面描述
  async analyzeCameraFeed(feedDescription: string): Promise<VisionResult> {
    return this.analyzeImage(feedDescription, 'general');
  }
  
  // 识别文字
  async recognizeText(imageDescription: string): Promise<string> {
    const result = await this.analyzeImage(imageDescription, 'text_recognition');
    return result.text || result.description;
  }
  
  // 检测物体
  async detectObjects(imageDescription: string): Promise<DetectedObject[]> {
    const result = await this.analyzeImage(imageDescription, 'object_detection');
    return result.objects;
  }
  
  // 分析情感
  async analyzeEmotions(imageDescription: string): Promise<DetectedEmotion[]> {
    const result = await this.analyzeImage(imageDescription, 'emotion_recognition');
    return result.emotions;
  }
  
  // 分析颜色
  async analyzeColors(imageDescription: string): Promise<ColorInfo[]> {
    const result = await this.analyzeImage(imageDescription, 'color_analysis');
    return result.colors;
  }
  
  // 描述场景
  async describeScene(imageDescription: string): Promise<string> {
    const result = await this.analyzeImage(imageDescription, 'scene_description');
    return result.description;
  }
}

// 导出单例
export const visionService = new VisionService();