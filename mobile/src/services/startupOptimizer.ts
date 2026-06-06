// ============================================
// 启动优化器
// ============================================
import * as FileSystem from 'expo-file-system';
import { MMKV } from 'react-native-mmkv';
import { StartupTracker } from '../utils/performance';

const storage = new MMKV({ id: 'startup-optimizer' });

// 启动配置
interface StartupConfig {
  // 预加载项
  preloadModels: boolean;
  preloadCharacters: boolean;
  preloadConversations: boolean;
  
  // 缓存策略
  enableImageCache: boolean;
  enableDataCache: boolean;
  cacheExpiration: number; // 毫秒
  
  // 优化策略
  lazyLoadTabs: boolean;
  deferNonCritical: boolean;
  batchInitialLoad: boolean;
}

// 默认配置
const DEFAULT_CONFIG: StartupConfig = {
  preloadModels: true,
  preloadCharacters: true,
  preloadConversations: true,
  enableImageCache: true,
  enableDataCache: true,
  cacheExpiration: 24 * 60 * 60 * 1000, // 24小时
  lazyLoadTabs: true,
  deferNonCritical: true,
  batchInitialLoad: true,
};

class StartupOptimizer {
  private static instance: StartupOptimizer;
  private config: StartupConfig;
  private isInitialized = false;
  private initPromise: Promise<void> | null = null;
  
  private constructor() {
    this.config = this.loadConfig();
  }
  
  static getInstance(): StartupOptimizer {
    if (!StartupOptimizer.instance) {
      StartupOptimizer.instance = new StartupOptimizer();
    }
    return StartupOptimizer.instance;
  }
  
  // 加载配置
  private loadConfig(): StartupConfig {
    try {
      const saved = storage.getString('startup_config');
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load startup config error:', e);
    }
    return { ...DEFAULT_CONFIG };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('startup_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save startup config error:', e);
    }
  }
  
  // 更新配置
  updateConfig(partial: Partial<StartupConfig>): void {
    this.config = { ...this.config, ...partial };
    this.saveConfig();
  }
  
  // 获取配置
  getConfig(): StartupConfig {
    return { ...this.config };
  }
  
  // 初始化（只执行一次）
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }
    
    if (this.initPromise) {
      return this.initPromise;
    }
    
    this.initPromise = this.doInitialize();
    await this.initPromise;
    this.isInitialized = true;
  }
  
  // 实际初始化逻辑
  private async doInitialize(): Promise<void> {
    StartupTracker.mark('optimizer_start');
    
    try {
      // 1. 确保目录存在
      await this.ensureDirectories();
      StartupTracker.mark('directories_ready');
      
      // 2. 清理过期缓存
      await this.cleanExpiredCache();
      StartupTracker.mark('cache_cleaned');
      
      // 3. 预加载关键数据
      if (this.config.batchInitialLoad) {
        await this.preloadCriticalData();
      }
      StartupTracker.mark('preload_complete');
      
      // 4. 延迟加载非关键数据
      if (this.config.deferNonCritical) {
        this.deferNonCriticalLoad();
      }
      
      StartupTracker.mark('optimizer_complete');
      
    } catch (error) {
      console.error('Startup optimizer error:', error);
    }
  }
  
  // 确保目录存在
  private async ensureDirectories(): Promise<void> {
    const directories = [
      `${FileSystem.documentDirectory}models/`,
      `${FileSystem.documentDirectory}characters/`,
      `${FileSystem.documentDirectory}conversations/`,
      `${FileSystem.cacheDirectory}images/`,
      `${FileSystem.cacheDirectory}ai-cache/`,
    ];
    
    for (const dir of directories) {
      try {
        await FileSystem.makeDirectoryAsync(dir, { intermediates: true });
      } catch {
        // 目录可能已存在
      }
    }
  }
  
  // 清理过期缓存
  private async cleanExpiredCache(): Promise<void> {
    try {
      const cacheDir = `${FileSystem.cacheDirectory}images/`;
      const info = await FileSystem.getInfoAsync(cacheDir);
      
      if (!info.exists) {
        return;
      }
      
      const files = await FileSystem.readDirectoryAsync(cacheDir);
      const now = Date.now();
      
      for (const file of files) {
        try {
          const filePath = `${cacheDir}${file}`;
          const fileInfo = await FileSystem.getInfoAsync(filePath);
          
          if (fileInfo.exists && fileInfo.modificationTime) {
            const age = now - fileInfo.modificationTime;
            if (age > this.config.cacheExpiration) {
              await FileSystem.deleteAsync(filePath, { idempotent: true });
            }
          }
        } catch {
          // 忽略单个文件错误
        }
      }
    } catch (error) {
      console.error('Clean expired cache error:', error);
    }
  }
  
  // 预加载关键数据
  private async preloadCriticalData(): Promise<void> {
    // 这里可以预加载角色、对话等数据
    // 实际实现需要与各服务协调
  }
  
  // 延迟加载非关键数据
  private deferNonCriticalLoad(): void {
    // 使用 setTimeout 延迟加载
    setTimeout(() => {
      this.loadNonCriticalData();
    }, 2000);
  }
  
  // 加载非关键数据
  private async loadNonCriticalData(): Promise<void> {
    // 预加载图片、统计信息等
  }
  
  // 获取缓存大小
  async getCacheSize(): Promise<number> {
    try {
      const cacheDir = `${FileSystem.cacheDirectory}`;
      const info = await FileSystem.getInfoAsync(cacheDir);
      
      if (!info.exists) {
        return 0;
      }
      
      // 递归计算大小
      return await this.getDirectorySize(cacheDir);
    } catch {
      return 0;
    }
  }
  
  // 递归获取目录大小
  private async getDirectorySize(path: string): Promise<number> {
    let totalSize = 0;
    
    try {
      const files = await FileSystem.readDirectoryAsync(path);
      
      for (const file of files) {
        const filePath = `${path}${file}`;
        const info = await FileSystem.getInfoAsync(filePath);
        
        if (info.exists) {
          if (info.isDirectory) {
            totalSize += await this.getDirectorySize(`${filePath}/`);
          } else {
            totalSize += info.size || 0;
          }
        }
      }
    } catch {
      // 忽略错误
    }
    
    return totalSize;
  }
  
  // 清除所有缓存
  async clearAllCache(): Promise<void> {
    try {
      const cacheDir = `${FileSystem.cacheDirectory}`;
      await FileSystem.deleteAsync(cacheDir, { idempotent: true });
      await FileSystem.makeDirectoryAsync(cacheDir, { intermediates: true });
    } catch (error) {
      console.error('Clear cache error:', error);
    }
  }
  
  // 格式化缓存大小
  formatCacheSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    } else if (bytes < 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    } else {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }
  }
}

// 单例
export const startupOptimizer = StartupOptimizer.getInstance();

export default startupOptimizer;
