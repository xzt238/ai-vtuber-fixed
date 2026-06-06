// ============================================
// VRM/Live2D 模型资源管理器
// ============================================
import * as FileSystem from 'expo-file-system';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV({ id: 'model-manager' });

// 模型类型
export type ModelType = 'live2d' | 'vrm' | '3d';

// 模型配置接口
export interface ModelConfig {
  id: string;
  name: string;
  nameJa?: string;
  nameEn?: string;
  type: ModelType;
  thumbnail: string; // 缩略图 URL 或本地路径
  modelUrl: string; // 模型文件 URL
  author: string;
  description: string;
  tags: string[];
  animations?: string[]; // 可用动画列表
  expressions?: string[]; // 可用表情列表
  fileSize?: number; // 文件大小 (bytes)
  downloadCount?: number;
  rating?: number; // 1-5
  isDefault?: boolean;
  isDownloaded?: boolean;
  localPath?: string; // 本地缓存路径
}

// 预设模型库
export const PRESET_MODELS: ModelConfig[] = [
  // Live2D 预设
  {
    id: 'live2d-haru',
    name: '春日未来',
    nameJa: '春日みらい',
    nameEn: 'Haru Mirai',
    type: 'live2d',
    thumbnail: 'https://cdn.jsdelivr.net/gh/niconi233/live2d_models@master/haru/haru_thumbnail.png',
    modelUrl: 'https://cdn.jsdelivr.net/gh/niconi233/live2d_models@master/haru/haru.model3.json',
    author: 'Live2D Inc.',
    description: '活泼可爱的少女，喜欢唱歌和跳舞',
    tags: ['可爱', '少女', '活泼'],
    animations: ['idle', 'happy', 'sad', 'angry', 'surprised'],
    expressions: ['neutral', 'happy', 'sad', 'angry', 'surprised', 'love'],
    isDefault: true,
  },
  {
    id: 'live2d-shizuku',
    name: '雫',
    nameJa: 'しずく',
    nameEn: 'Shizuku',
    type: 'live2d',
    thumbnail: 'https://cdn.jsdelivr.net/gh/niconi233/live2d_models@master/shizuku/shizuku_thumbnail.png',
    modelUrl: 'https://cdn.jsdelivr.net/gh/niconi233/live2d_models@master/shizuku/shizuku.model3.json',
    author: 'Live2D Inc.',
    description: '温柔文静的少女，喜欢读书',
    tags: ['温柔', '文静', '知性'],
    animations: ['idle', 'happy', 'sad', 'thinking'],
    expressions: ['neutral', 'happy', 'sad', 'thinking'],
  },
  {
    id: 'live2d-unitychan',
    name: 'Unity酱',
    nameJa: 'ユニティちゃん',
    nameEn: 'Unity-chan',
    type: 'live2d',
    thumbnail: 'https://cdn.jsdelivr.net/gh/unity-chan/UnityChan@master/README/UnityChan_logo.png',
    modelUrl: 'https://cdn.jsdelivr.net/gh/niconi233/live2d_models@master/unitychan/unitychan.model3.json',
    author: 'Unity Technologies',
    description: 'Unity 官方吉祥物，充满活力',
    tags: ['活力', '元气', '官方'],
    animations: ['idle', 'happy', 'dance'],
    expressions: ['neutral', 'happy', 'excited'],
  },
  
  // VRM 预设
  {
    id: 'vrm-sample',
    name: 'VRM示例角色',
    nameEn: 'VRM Sample',
    type: 'vrm',
    thumbnail: 'https://github.com/pixiv/three-vrm/raw/dev/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample/VRM1_Constraint_Twist_Sample.jpg',
    modelUrl: 'https://pixiv.github.io/three-vrm/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample/VRM1_Constraint_Twist_Sample.vrm',
    author: 'pixiv',
    description: 'VRM 标准示例角色',
    tags: ['示例', '标准'],
    animations: ['idle', 'walk', 'run'],
    expressions: ['neutral', 'happy', 'sad', 'angry', 'surprised'],
  },
  {
    id: 'vrm-avatar',
    name: '虚拟形象',
    nameEn: 'Virtual Avatar',
    type: 'vrm',
    thumbnail: 'https://img.icons8.com/color/96/000000/user-male-circle.png',
    modelUrl: 'https://cdn.jsdelivr.net/gh/niconi233/vrm_models@master/avatar/avatar.vrm',
    author: 'GuguGaga',
    description: '通用虚拟形象',
    tags: ['通用', '简约'],
    animations: ['idle', 'talk', 'gesture'],
    expressions: ['neutral', 'happy', 'sad'],
  },
  
  // 简单 3D 预设（无需外部模型）
  {
    id: '3d-cube',
    name: '方块君',
    nameEn: 'Cube-kun',
    type: '3d',
    thumbnail: 'https://img.icons8.com/color/96/000000/cube.png',
    modelUrl: 'builtin://cube',
    author: 'GuguGaga',
    description: '简约方块角色，轻量级',
    tags: ['简约', '轻量'],
    isDefault: true,
  },
  {
    id: '3d-sphere',
    name: '球球',
    nameEn: 'Sphere-chan',
    type: '3d',
    thumbnail: 'https://img.icons8.com/color/96/000000/sphere.png',
    modelUrl: 'builtin://sphere',
    author: 'GuguGaga',
    description: '圆润球形角色',
    tags: ['可爱', '圆润'],
    isDefault: true,
  },
];

class ModelManager {
  private currentModel: ModelConfig | null = null;
  private downloadedModels: Map<string, string> = new Map(); // id -> localPath
  private modelChangeCallbacks: Array<(model: ModelConfig) => void> = [];
  
  constructor() {
    this.loadDownloadedModels();
  }
  
  // 加载已下载模型列表
  private loadDownloadedModels() {
    try {
      const saved = storage.getString('downloaded_models');
      if (saved) {
        const parsed = JSON.parse(saved);
        this.downloadedModels = new Map(Object.entries(parsed));
      }
    } catch (e) {
      console.error('Load downloaded models error:', e);
    }
  }
  
  // 保存已下载模型列表
  private saveDownloadedModels() {
    try {
      const obj = Object.fromEntries(this.downloadedModels);
      storage.set('downloaded_models', JSON.stringify(obj));
    } catch (e) {
      console.error('Save downloaded models error:', e);
    }
  }
  
  // 获取所有预设模型
  getPresetModels(): ModelConfig[] {
    return PRESET_MODELS.map(model => ({
      ...model,
      isDownloaded: this.isModelDownloaded(model.id),
      localPath: this.downloadedModels.get(model.id),
    }));
  }
  
  // 获取当前模型
  getCurrentModel(): ModelConfig | null {
    return this.currentModel;
  }
  
  // 设置当前模型
  async setCurrentModel(modelId: string): Promise<boolean> {
    const model = PRESET_MODELS.find(m => m.id === modelId);
    if (!model) {
      console.error('Model not found:', modelId);
      return false;
    }
    
    // 检查是否需要下载
    if (!model.isDefault && !this.isModelDownloaded(modelId)) {
      const downloaded = await this.downloadModel(modelId);
      if (!downloaded) return false;
    }
    
    this.currentModel = {
      ...model,
      isDownloaded: true,
      localPath: this.downloadedModels.get(modelId) || model.modelUrl,
    };
    
    // 保存选择
    storage.set('current_model_id', modelId);
    
    // 通知回调
    if (this.currentModel) {
      this.modelChangeCallbacks.forEach(cb => cb(this.currentModel!));
    }
    
    return true;
  }
  
  // 加载保存的模型选择
  async loadSavedModel(): Promise<ModelConfig | null> {
    const savedId = storage.getString('current_model_id');
    if (savedId) {
      await this.setCurrentModel(savedId);
    } else {
      // 默认使用第一个默认模型
      const defaultModel = PRESET_MODELS.find(m => m.isDefault);
      if (defaultModel) {
        await this.setCurrentModel(defaultModel.id);
      }
    }
    return this.currentModel;
  }
  
  // 检查模型是否已下载
  isModelDownloaded(modelId: string): boolean {
    return this.downloadedModels.has(modelId);
  }
  
  // 下载模型
  async downloadModel(modelId: string): Promise<boolean> {
    const model = PRESET_MODELS.find(m => m.id === modelId);
    if (!model) return false;
    
    // 内置模型不需要下载
    if (model.modelUrl.startsWith('builtin://')) {
      this.downloadedModels.set(modelId, model.modelUrl);
      this.saveDownloadedModels();
      return true;
    }
    
    try {
      const dir = `${FileSystem.documentDirectory}models/${modelId}/`;
      await FileSystem.makeDirectoryAsync(dir, { intermediates: true });
      
      // 下载模型文件
      const modelFileName = model.modelUrl.split('/').pop() || 'model';
      const localPath = `${dir}${modelFileName}`;
      
      const download = await FileSystem.downloadAsync(
        model.modelUrl,
        localPath
      );
      
      if (download.status === 200) {
        this.downloadedModels.set(modelId, localPath);
        this.saveDownloadedModels();
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Download model error:', error);
      return false;
    }
  }
  
  // 删除下载的模型
  async deleteModel(modelId: string): Promise<boolean> {
    const localPath = this.downloadedModels.get(modelId);
    if (!localPath || localPath.startsWith('builtin://')) {
      return false;
    }
    
    try {
      const dir = `${FileSystem.documentDirectory}models/${modelId}/`;
      await FileSystem.deleteAsync(dir, { idempotent: true });
      this.downloadedModels.delete(modelId);
      this.saveDownloadedModels();
      return true;
    } catch (error) {
      console.error('Delete model error:', error);
      return false;
    }
  }
  
  // 获取模型本地路径
  getModelPath(modelId: string): string | null {
    const model = PRESET_MODELS.find(m => m.id === modelId);
    if (!model) return null;
    
    if (model.modelUrl.startsWith('builtin://')) {
      return model.modelUrl;
    }
    
    return this.downloadedModels.get(modelId) || null;
  }
  
  // 注册模型变更回调
  onModelChange(callback: (model: ModelConfig) => void) {
    this.modelChangeCallbacks.push(callback);
    return () => {
      this.modelChangeCallbacks = this.modelChangeCallbacks.filter(cb => cb !== callback);
    };
  }
  
  // 获取已下载模型列表
  getDownloadedModels(): ModelConfig[] {
    return PRESET_MODELS
      .filter(m => this.isModelDownloaded(m.id))
      .map(m => ({
        ...m,
        isDownloaded: true,
        localPath: this.downloadedModels.get(m.id),
      }));
  }
  
  // 清除所有下载
  async clearAllDownloads(): Promise<void> {
    try {
      const dir = `${FileSystem.documentDirectory}models/`;
      await FileSystem.deleteAsync(dir, { idempotent: true });
      this.downloadedModels.clear();
      this.saveDownloadedModels();
    } catch (error) {
      console.error('Clear downloads error:', error);
    }
  }
}

// 单例
export const modelManager = new ModelManager();

export default modelManager;
