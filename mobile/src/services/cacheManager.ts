// ============================================
// 缓存管理服务
// ============================================
import * as FileSystem from 'expo-file-system';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV({ id: 'cache-manager' });

// 缓存项
interface CacheItem<T> {
  data: T;
  timestamp: number;
  expiry: number; // 过期时间戳
}

// 缓存配置
interface CacheConfig {
  maxSize: number; // 最大缓存条目数
  defaultTTL: number; // 默认过期时间（毫秒）
  enablePersistence: boolean; // 是否持久化到文件
}

// 默认配置
const DEFAULT_CONFIG: CacheConfig = {
  maxSize: 1000,
  defaultTTL: 24 * 60 * 60 * 1000, // 24小时
  enablePersistence: true,
};

class CacheManager {
  private static instance: CacheManager;
  private config: CacheConfig;
  private memoryCache: Map<string, CacheItem<any>>;
  
  private constructor() {
    this.config = DEFAULT_CONFIG;
    this.memoryCache = new Map();
    this.loadFromStorage();
  }
  
  static getInstance(): CacheManager {
    if (!CacheManager.instance) {
      CacheManager.instance = new CacheManager();
    }
    return CacheManager.instance;
  }
  
  // 从存储加载
  private loadFromStorage(): void {
    try {
      const saved = storage.getString('cache_data');
      if (saved) {
        const parsed = JSON.parse(saved);
        const now = Date.now();
        
        // 只加载未过期的项
        Object.entries(parsed).forEach(([key, item]: [string, any]) => {
          if (item.expiry > now) {
            this.memoryCache.set(key, item);
          }
        });
      }
    } catch (e) {
      console.error('Load cache error:', e);
    }
  }
  
  // 保存到存储
  private saveToStorage(): void {
    if (!this.config.enablePersistence) {
      return;
    }
    
    try {
      const obj: Record<string, CacheItem<any>> = {};
      this.memoryCache.forEach((value, key) => {
        obj[key] = value;
      });
      storage.set('cache_data', JSON.stringify(obj));
    } catch (e) {
      console.error('Save cache error:', e);
    }
  }
  
  // 获取缓存
  get<T>(key: string): T | null {
    const item = this.memoryCache.get(key);
    
    if (!item) {
      return null;
    }
    
    // 检查是否过期
    if (Date.now() > item.expiry) {
      this.memoryCache.delete(key);
      return null;
    }
    
    return item.data as T;
  }
  
  // 设置缓存
  set<T>(key: string, data: T, ttl?: number): void {
    // 检查是否需要清理
    if (this.memoryCache.size >= this.config.maxSize) {
      this.evictOldest();
    }
    
    const now = Date.now();
    const item: CacheItem<T> = {
      data,
      timestamp: now,
      expiry: now + (ttl || this.config.defaultTTL),
    };
    
    this.memoryCache.set(key, item);
    this.saveToStorage();
  }
  
  // 检查是否存在
  has(key: string): boolean {
    const item = this.memoryCache.get(key);
    
    if (!item) {
      return false;
    }
    
    // 检查是否过期
    if (Date.now() > item.expiry) {
      this.memoryCache.delete(key);
      return false;
    }
    
    return true;
  }
  
  // 删除缓存
  delete(key: string): boolean {
    const result = this.memoryCache.delete(key);
    if (result) {
      this.saveToStorage();
    }
    return result;
  }
  
  // 清除所有缓存
  clear(): void {
    this.memoryCache.clear();
    this.saveToStorage();
  }
  
  // 清除过期缓存
  clearExpired(): number {
    const now = Date.now();
    let count = 0;
    
    this.memoryCache.forEach((item, key) => {
      if (now > item.expiry) {
        this.memoryCache.delete(key);
        count++;
      }
    });
    
    if (count > 0) {
      this.saveToStorage();
    }
    
    return count;
  }
  
  // 驱逐最旧的项
  private evictOldest(): void {
    let oldestKey: string | null = null;
    let oldestTime = Infinity;
    
    this.memoryCache.forEach((item, key) => {
      if (item.timestamp < oldestTime) {
        oldestTime = item.timestamp;
        oldestKey = key;
      }
    });
    
    if (oldestKey) {
      this.memoryCache.delete(oldestKey);
    }
  }
  
  // 获取缓存大小
  getSize(): number {
    return this.memoryCache.size;
  }
  
  // 获取缓存统计
  getStats(): {
    size: number;
    maxSize: number;
    hitRate: number;
  } {
    return {
      size: this.memoryCache.size,
      maxSize: this.config.maxSize,
      hitRate: 0, // 需要实现命中率追踪
    };
  }
  
  // 更新配置
  updateConfig(partial: Partial<CacheConfig>): void {
    this.config = { ...this.config, ...partial };
  }
  
  // 批量获取
  mget<T>(keys: string[]): Map<string, T | null> {
    const result = new Map<string, T | null>();
    keys.forEach(key => {
      result.set(key, this.get<T>(key));
    });
    return result;
  }
  
  // 批量设置
  mset<T>(entries: Map<string, T>, ttl?: number): void {
    entries.forEach((data, key) => {
      this.set(key, data, ttl);
    });
  }
  
  // 带回调的获取（缓存未命中时执行回调）
  async getOrSet<T>(
    key: string,
    factory: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    const cached = this.get<T>(key);
    if (cached !== null) {
      return cached;
    }
    
    const data = await factory();
    this.set(key, data, ttl);
    return data;
  }
}

// 单例
export const cacheManager = CacheManager.getInstance();

export default cacheManager;
