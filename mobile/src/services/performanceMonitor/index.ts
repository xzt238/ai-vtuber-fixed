// ============================================
// 性能监控服务 - 移动端版本
// ============================================
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV();

// 性能指标类型
export interface PerformanceMetrics {
  timestamp: number;
  fps: number;
  memoryUsed: number;     // MB
  memoryTotal: number;    // MB
  cpuUsage: number;       // 0-100
  batteryLevel: number;   // 0-100
  networkType: string;
  networkSpeed: number;   // KB/s
  renderTime: number;     // ms
  jsThreadTime: number;   // ms
}

// 性能警告
export interface PerformanceWarning {
  id: string;
  type: 'fps' | 'memory' | 'cpu' | 'network' | 'battery';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  value: number;
  threshold: number;
  timestamp: number;
}

// 性能统计
export interface PerformanceStats {
  avgFps: number;
  minFps: number;
  maxFps: number;
  avgMemory: number;
  maxMemory: number;
  avgCpu: number;
  maxCpu: number;
  totalWarnings: number;
  criticalWarnings: number;
}

// 监控配置
export interface MonitorConfig {
  enabled: boolean;
  interval: number;        // 采样间隔 (ms)
  historySize: number;     // 历史记录数量
  fpsThreshold: number;    // FPS 警告阈值
  memoryThreshold: number; // 内存警告阈值 (MB)
  cpuThreshold: number;    // CPU 警告阈值
  showOverlay: boolean;    // 显示悬浮窗
  position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
}

// 默认配置
const DEFAULT_CONFIG: MonitorConfig = {
  enabled: false,
  interval: 1000,
  historySize: 60,
  fpsThreshold: 30,
  memoryThreshold: 500,
  cpuThreshold: 80,
  showOverlay: false,
  position: 'top-right',
};

// 阈值配置
const THRESHOLDS = {
  fps: { warning: 30, critical: 15 },
  memory: { warning: 500, critical: 800 },
  cpu: { warning: 80, critical: 95 },
  battery: { warning: 20, critical: 10 },
};

// 性能监控服务类
class PerformanceMonitorService {
  private config: MonitorConfig;
  private metrics: PerformanceMetrics[] = [];
  private warnings: PerformanceWarning[] = [];
  private isRunning = false;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private callbacks: Array<(metrics: PerformanceMetrics) => void> = [];
  private warningCallbacks: Array<(warning: PerformanceWarning) => void> = [];
  
  constructor() {
    this.config = { ...DEFAULT_CONFIG };
    this.loadConfig();
  }
  
  // 加载配置
  private loadConfig(): void {
    try {
      const saved = storage.getString('perf_monitor_config');
      if (saved) {
        this.config = { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load perf config error:', e);
    }
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('perf_monitor_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save perf config error:', e);
    }
  }
  
  // 获取配置
  getConfig(): MonitorConfig {
    return { ...this.config };
  }
  
  // 更新配置
  updateConfig(updates: Partial<MonitorConfig>): void {
    this.config = { ...this.config, ...updates };
    this.saveConfig();
    
    if (this.config.enabled && !this.isRunning) {
      this.start();
    } else if (!this.config.enabled && this.isRunning) {
      this.stop();
    }
  }
  
  // 开始监控
  start(): void {
    if (this.isRunning) return;
    
    this.isRunning = true;
    this.intervalId = setInterval(() => {
      this.collectMetrics();
    }, this.config.interval);
    
    console.log('Performance monitor started');
  }
  
  // 停止监控
  stop(): void {
    if (!this.isRunning) return;
    
    this.isRunning = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    
    console.log('Performance monitor stopped');
  }
  
  // 收集指标
  private collectMetrics(): void {
    const metrics: PerformanceMetrics = {
      timestamp: Date.now(),
      fps: this.getFPS(),
      memoryUsed: this.getMemoryUsed(),
      memoryTotal: this.getMemoryTotal(),
      cpuUsage: this.getCPUUsage(),
      batteryLevel: this.getBatteryLevel(),
      networkType: this.getNetworkType(),
      networkSpeed: this.getNetworkSpeed(),
      renderTime: this.getRenderTime(),
      jsThreadTime: this.getJSThreadTime(),
    };
    
    // 保存指标
    this.metrics.push(metrics);
    if (this.metrics.length > this.config.historySize) {
      this.metrics.shift();
    }
    
    // 检查警告
    this.checkWarnings(metrics);
    
    // 通知回调
    this.callbacks.forEach(cb => {
      try {
        cb(metrics);
      } catch (e) {
        console.error('Metrics callback error:', e);
      }
    });
  }
  
  // 获取FPS (模拟)
  private getFPS(): number {
    // 在实际实现中，这里会使用 React Native 的 Performance API
    return 55 + Math.random() * 10;
  }
  
  // 获取内存使用 (模拟)
  private getMemoryUsed(): number {
    return 200 + Math.random() * 100;
  }
  
  // 获取总内存 (模拟)
  private getMemoryTotal(): number {
    return 4096;
  }
  
  // 获取CPU使用率 (模拟)
  private getCPUUsage(): number {
    return 20 + Math.random() * 30;
  }
  
  // 获取电量 (模拟)
  private getBatteryLevel(): number {
    return 70 + Math.random() * 30;
  }
  
  // 获取网络类型 (模拟)
  private getNetworkType(): string {
    const types = ['WiFi', '4G', '5G', '3G'];
    return types[Math.floor(Math.random() * types.length)];
  }
  
  // 获取网络速度 (模拟)
  private getNetworkSpeed(): number {
    return 1000 + Math.random() * 5000;
  }
  
  // 获取渲染时间 (模拟)
  private getRenderTime(): number {
    return 8 + Math.random() * 10;
  }
  
  // 获取JS线程时间 (模拟)
  private getJSThreadTime(): number {
    return 5 + Math.random() * 8;
  }
  
  // 检查警告
  private checkWarnings(metrics: PerformanceMetrics): void {
    // FPS 警告
    if (metrics.fps < THRESHOLDS.fps.critical) {
      this.addWarning('fps', 'critical', `FPS 极低: ${Math.round(metrics.fps)}`, metrics.fps, THRESHOLDS.fps.critical);
    } else if (metrics.fps < THRESHOLDS.fps.warning) {
      this.addWarning('fps', 'medium', `FPS 偏低: ${Math.round(metrics.fps)}`, metrics.fps, THRESHOLDS.fps.warning);
    }
    
    // 内存警告
    if (metrics.memoryUsed > THRESHOLDS.memory.critical) {
      this.addWarning('memory', 'critical', `内存使用过高: ${Math.round(metrics.memoryUsed)}MB`, metrics.memoryUsed, THRESHOLDS.memory.critical);
    } else if (metrics.memoryUsed > THRESHOLDS.memory.warning) {
      this.addWarning('memory', 'medium', `内存使用偏高: ${Math.round(metrics.memoryUsed)}MB`, metrics.memoryUsed, THRESHOLDS.memory.warning);
    }
    
    // CPU 警告
    if (metrics.cpuUsage > THRESHOLDS.cpu.critical) {
      this.addWarning('cpu', 'critical', `CPU 使用过高: ${Math.round(metrics.cpuUsage)}%`, metrics.cpuUsage, THRESHOLDS.cpu.critical);
    } else if (metrics.cpuUsage > THRESHOLDS.cpu.warning) {
      this.addWarning('cpu', 'medium', `CPU 使用偏高: ${Math.round(metrics.cpuUsage)}%`, metrics.cpuUsage, THRESHOLDS.cpu.warning);
    }
    
    // 电量警告
    if (metrics.batteryLevel < THRESHOLDS.battery.critical) {
      this.addWarning('battery', 'critical', `电量极低: ${Math.round(metrics.batteryLevel)}%`, metrics.batteryLevel, THRESHOLDS.battery.critical);
    } else if (metrics.batteryLevel < THRESHOLDS.battery.warning) {
      this.addWarning('battery', 'medium', `电量偏低: ${Math.round(metrics.batteryLevel)}%`, metrics.batteryLevel, THRESHOLDS.battery.warning);
    }
  }
  
  // 添加警告
  private addWarning(
    type: PerformanceWarning['type'],
    severity: PerformanceWarning['severity'],
    message: string,
    value: number,
    threshold: number
  ): void {
    const warning: PerformanceWarning = {
      id: `warning_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      severity,
      message,
      value,
      threshold,
      timestamp: Date.now(),
    };
    
    this.warnings.push(warning);
    if (this.warnings.length > 100) {
      this.warnings.shift();
    }
    
    // 通知警告回调
    this.warningCallbacks.forEach(cb => {
      try {
        cb(warning);
      } catch (e) {
        console.error('Warning callback error:', e);
      }
    });
  }
  
  // 获取当前指标
  getCurrentMetrics(): PerformanceMetrics | null {
    return this.metrics.length > 0 ? this.metrics[this.metrics.length - 1] : null;
  }
  
  // 获取历史指标
  getMetricsHistory(): PerformanceMetrics[] {
    return [...this.metrics];
  }
  
  // 获取警告
  getWarnings(): PerformanceWarning[] {
    return [...this.warnings];
  }
  
  // 清除警告
  clearWarnings(): void {
    this.warnings = [];
  }
  
  // 获取统计
  getStats(): PerformanceStats {
    if (this.metrics.length === 0) {
      return {
        avgFps: 0,
        minFps: 0,
        maxFps: 0,
        avgMemory: 0,
        maxMemory: 0,
        avgCpu: 0,
        maxCpu: 0,
        totalWarnings: 0,
        criticalWarnings: 0,
      };
    }
    
    const fps = this.metrics.map(m => m.fps);
    const memory = this.metrics.map(m => m.memoryUsed);
    const cpu = this.metrics.map(m => m.cpuUsage);
    
    return {
      avgFps: fps.reduce((a, b) => a + b, 0) / fps.length,
      minFps: Math.min(...fps),
      maxFps: Math.max(...fps),
      avgMemory: memory.reduce((a, b) => a + b, 0) / memory.length,
      maxMemory: Math.max(...memory),
      avgCpu: cpu.reduce((a, b) => a + b, 0) / cpu.length,
      maxCpu: Math.max(...cpu),
      totalWarnings: this.warnings.length,
      criticalWarnings: this.warnings.filter(w => w.severity === 'critical').length,
    };
  }
  
  // 添加指标回调
  onMetrics(callback: (metrics: PerformanceMetrics) => void): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }
  
  // 添加警告回调
  onWarning(callback: (warning: PerformanceWarning) => void): () => void {
    this.warningCallbacks.push(callback);
    return () => {
      this.warningCallbacks = this.warningCallbacks.filter(cb => cb !== callback);
    };
  }
  
  // 检查是否运行中
  getIsRunning(): boolean {
    return this.isRunning;
  }
  
  // 获取性能评分 (0-100)
  getPerformanceScore(): number {
    const current = this.getCurrentMetrics();
    if (!current) return 100;
    
    let score = 100;
    
    // FPS 评分 (40%)
    if (current.fps < 30) score -= 40;
    else if (current.fps < 45) score -= 20;
    else if (current.fps < 55) score -= 10;
    
    // 内存评分 (30%)
    if (current.memoryUsed > 800) score -= 30;
    else if (current.memoryUsed > 500) score -= 15;
    else if (current.memoryUsed > 300) score -= 5;
    
    // CPU 评分 (30%)
    if (current.cpuUsage > 90) score -= 30;
    else if (current.cpuUsage > 70) score -= 15;
    else if (current.cpuUsage > 50) score -= 5;
    
    return Math.max(0, score);
  }
  
  // 获取性能等级
  getPerformanceGrade(): { grade: string; color: string; description: string } {
    const score = this.getPerformanceScore();
    
    if (score >= 90) {
      return { grade: 'A+', color: '#10b981', description: '优秀' };
    } else if (score >= 80) {
      return { grade: 'A', color: '#22c55e', description: '良好' };
    } else if (score >= 70) {
      return { grade: 'B', color: '#f59e0b', description: '一般' };
    } else if (score >= 60) {
      return { grade: 'C', color: '#f97316', description: '较差' };
    } else {
      return { grade: 'D', color: '#ef4444', description: '很差' };
    }
  }
  
  // 导出数据
  exportData(): string {
    return JSON.stringify({
      config: this.config,
      metrics: this.metrics,
      warnings: this.warnings,
      stats: this.getStats(),
      score: this.getPerformanceScore(),
      grade: this.getPerformanceGrade(),
    }, null, 2);
  }
  
  // 清除数据
  clearData(): void {
    this.metrics = [];
    this.warnings = [];
  }
}

// 导出单例
export const performanceMonitor = new PerformanceMonitorService();