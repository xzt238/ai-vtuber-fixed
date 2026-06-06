// ============================================
// 性能优化工具
// ============================================
import { InteractionManager, Platform } from 'react-native';

// 延迟执行（在交互完成后）
export function runAfterInteractions(callback: () => void): () => void {
  const task = InteractionManager.runAfterInteractions(callback);
  return () => task.cancel();
}

// 批量处理（减少重渲染）
export function batchUpdates(updates: Array<() => void>): void {
  // 使用 requestAnimationFrame 批量执行
  requestAnimationFrame(() => {
    updates.forEach(update => update());
  });
}

// 防抖
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    
    timeout = setTimeout(() => {
      func(...args);
      timeout = null;
    }, wait);
  };
}

// 节流
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

// 内存缓存（LRU）
export class LRUCache<K, V> {
  private cache: Map<K, V>;
  private maxSize: number;
  
  constructor(maxSize: number = 100) {
    this.cache = new Map();
    this.maxSize = maxSize;
  }
  
  get(key: K): V | undefined {
    const value = this.cache.get(key);
    if (value !== undefined) {
      // 移到最后（最近使用）
      this.cache.delete(key);
      this.cache.set(key, value);
    }
    return value;
  }
  
  set(key: K, value: V): void {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.maxSize) {
      // 删除最旧的
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }
    this.cache.set(key, value);
  }
  
  has(key: K): boolean {
    return this.cache.has(key);
  }
  
  delete(key: K): boolean {
    return this.cache.delete(key);
  }
  
  clear(): void {
    this.cache.clear();
  }
  
  get size(): number {
    return this.cache.size;
  }
}

// 图片缓存管理
export class ImageCache {
  private static instance: ImageCache;
  private cache: LRUCache<string, string>;
  private loading: Map<string, Promise<string | null>>;
  
  private constructor() {
    this.cache = new LRUCache(50);
    this.loading = new Map();
  }
  
  static getInstance(): ImageCache {
    if (!ImageCache.instance) {
      ImageCache.instance = new ImageCache();
    }
    return ImageCache.instance;
  }
  
  async getImage(url: string): Promise<string | null> {
    // 检查缓存
    const cached = this.cache.get(url);
    if (cached) {
      return cached;
    }
    
    // 检查是否正在加载
    const loading = this.loading.get(url);
    if (loading) {
      return loading;
    }
    
    // 开始加载
    const promise = this.loadImage(url);
    this.loading.set(url, promise);
    
    const result = await promise;
    this.loading.delete(url);
    
    if (result) {
      this.cache.set(url, result);
    }
    
    return result;
  }
  
  private async loadImage(url: string): Promise<string | null> {
    try {
      // 预加载图片
      return url;
    } catch {
      return null;
    }
  }
  
  clear(): void {
    this.cache.clear();
    this.loading.clear();
  }
}

// 列表优化配置
export const LIST_OPTIMIZATION = {
  // FlatList 优化配置
  flatList: {
    removeClippedSubviews: true,
    maxToRenderPerBatch: 10,
    windowSize: 8,
    initialNumToRender: 10,
    updateCellsBatchingPeriod: 50,
    getItemLayout: (itemHeight: number) => (_: any, index: number) => ({
      length: itemHeight,
      offset: itemHeight * index,
      index,
    }),
  },
  
  // SectionList 优化配置
  sectionList: {
    removeClippedSubviews: true,
    maxToRenderPerBatch: 10,
    windowSize: 8,
  },
};

// 动画优化
export const ANIMATION_CONFIG = {
  // 减少动画（低性能设备）
  reduced: {
    duration: 150,
    useNativeDriver: true,
  },
  
  // 标准动画
  standard: {
    duration: 250,
    useNativeDriver: true,
  },
  
  // 慢动画
  slow: {
    duration: 350,
    useNativeDriver: true,
  },
};

// 内存监控
export class MemoryMonitor {
  private static instance: MemoryMonitor;
  private listeners: Array<(usage: MemoryInfo) => void> = [];
  private interval: NodeJS.Timeout | null = null;
  
  private constructor() {}
  
  static getInstance(): MemoryMonitor {
    if (!MemoryMonitor.instance) {
      MemoryMonitor.instance = new MemoryMonitor();
    }
    return MemoryMonitor.instance;
  }
  
  start(intervalMs: number = 5000): void {
    if (this.interval) {
      return;
    }
    
    this.interval = setInterval(() => {
      this.checkMemory();
    }, intervalMs);
  }
  
  stop(): void {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }
  
  private checkMemory(): void {
    // React Native 没有直接的内存 API，这里提供框架
    const info: MemoryInfo = {
      usedJSHeapSize: 0,
      totalJSHeapSize: 0,
      jsHeapSizeLimit: 0,
    };
    
    this.listeners.forEach(listener => listener(info));
  }
  
  onMemoryUpdate(listener: (usage: MemoryInfo) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }
}

interface MemoryInfo {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}

// 启动时间追踪
export class StartupTracker {
  private static startTime: number = Date.now();
  private static milestones: Map<string, number> = new Map();
  
  static mark(name: string): void {
    StartupTracker.milestones.set(name, Date.now() - StartupTracker.startTime);
  }
  
  static getMilestone(name: string): number | undefined {
    return StartupTracker.milestones.get(name);
  }
  
  static getAllMilestones(): Record<string, number> {
    return Object.fromEntries(StartupTracker.milestones);
  }
  
  static getTotalTime(): number {
    return Date.now() - StartupTracker.startTime;
  }
  
  static printReport(): void {
    console.log('=== Startup Performance Report ===');
    console.log(`Total time: ${StartupTracker.getTotalTime()}ms`);
    
    const milestones = StartupTracker.getAllMilestones();
    Object.entries(milestones).forEach(([name, time]) => {
      console.log(`${name}: ${time}ms`);
    });
    
    console.log('==================================');
  }
}

// 导出单例
export const imageCache = ImageCache.getInstance();
export const memoryMonitor = MemoryMonitor.getInstance();
