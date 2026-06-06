/**
 * 网络状态管理
 *
 * 监控网络连接状态，提供断网重连机制
 */

import { Platform } from 'react-native';

type NetworkStatus = 'connected' | 'disconnected' | 'unknown';
type NetworkListener = (status: NetworkStatus) => void;

class NetworkManager {
  private status: NetworkStatus = 'unknown';
  private listeners: Set<NetworkListener> = new Set();
  private checkInterval: ReturnType<typeof setInterval> | null = null;
  private serverUrl: string = '';

  constructor() {
    this.startMonitoring();
  }

  // 开始监控
  private startMonitoring(): void {
    // 定期检查网络状态
    this.checkInterval = setInterval(() => {
      this.checkNetwork();
    }, 30000); // 每30秒检查一次
  }

  // 停止监控
  stopMonitoring(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  // 设置服务器地址
  setServerUrl(url: string): void {
    this.serverUrl = url;
  }

  // 检查网络
  private async checkNetwork(): Promise<void> {
    if (!this.serverUrl) return;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${this.serverUrl}/api/v1/status`, {
        method: 'GET',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const newStatus: NetworkStatus = response.ok ? 'connected' : 'disconnected';
      if (newStatus !== this.status) {
        this.status = newStatus;
        this.notifyListeners();
      }
    } catch {
      if (this.status !== 'disconnected') {
        this.status = 'disconnected';
        this.notifyListeners();
      }
    }
  }

  // 获取当前状态
  getStatus(): NetworkStatus {
    return this.status;
  }

  // 是否已连接
  isConnected(): boolean {
    return this.status === 'connected';
  }

  // 添加监听器
  addListener(listener: NetworkListener): () => void {
    this.listeners.add(listener);
    // 立即通知当前状态
    listener(this.status);
    // 返回取消监听函数
    return () => {
      this.listeners.delete(listener);
    };
  }

  // 通知监听器
  private notifyListeners(): void {
    this.listeners.forEach((listener) => {
      try {
        listener(this.status);
      } catch (error) {
        console.error('[NetworkManager] 监听器回调失败:', error);
      }
    });
  }

  // 强制检查
  async forceCheck(): Promise<NetworkStatus> {
    await this.checkNetwork();
    return this.status;
  }
}

// 导出单例
export const networkManager = new NetworkManager();
