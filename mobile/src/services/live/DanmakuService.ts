// ============================================
// 直播弹幕服务
// ============================================
import { MMKV } from 'react-native-mmkv';
import { localAI } from '../localAI';
import { emotionService } from '../emotion';

const storage = new MMKV({ id: 'danmaku-service' });

// 弹幕类型
export type DanmakuType = 'text' | 'gift' | 'follow' | 'share' | 'system';

// 弹幕消息
export interface DanmakuMessage {
  id: string;
  type: DanmakuType;
  userId: string;
  username: string;
  content: string;
  giftName?: string;
  giftCount?: number;
  timestamp: number;
  platform: string;
}

// 弹幕配置
export interface DanmakuConfig {
  // 是否启用
  enabled: boolean;
  
  // 自动回复
  autoReply: boolean;
  
  // 回复延迟 (ms)
  replyDelay: number;
  
  // 回复概率 (0-1)
  replyChance: number;
  
  // 礼物感谢
  giftThanks: boolean;
  
  // 关注感谢
  followThanks: boolean;
  
  // 过滤词
  filterWords: string[];
  
  // 最大回复长度
  maxReplyLength: number;
}

// 默认配置
const DEFAULT_CONFIG: DanmakuConfig = {
  enabled: true,
  autoReply: true,
  replyDelay: 1000,
  replyChance: 0.3,
  giftThanks: true,
  followThanks: true,
  filterWords: [],
  maxReplyLength: 100,
};

// 平台连接状态
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

class DanmakuService {
  private static instance: DanmakuService;
  private config: DanmakuConfig;
  private status: ConnectionStatus = 'disconnected';
  private platform: string = '';
  private roomId: string = '';
  
  // 弹幕队列
  private danmakuQueue: DanmakuMessage[] = [];
  private replyQueue: Array<{ danmaku: DanmakuMessage; reply: string }> = [];
  
  // 事件回调
  private listeners: Array<(event: any) => void> = [];
  
  // 统计
  private stats = {
    totalDanmaku: 0,
    totalReplies: 0,
    totalGifts: 0,
    totalFollows: 0,
    startTime: 0,
  };
  
  // WebSocket
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  
  private constructor() {
    this.config = this.loadConfig();
  }
  
  static getInstance(): DanmakuService {
    if (!DanmakuService.instance) {
      DanmakuService.instance = new DanmakuService();
    }
    return DanmakuService.instance;
  }
  
  // 加载配置
  private loadConfig(): DanmakuConfig {
    try {
      const saved = storage.getString('danmaku_config');
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load danmaku config error:', e);
    }
    return { ...DEFAULT_CONFIG };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('danmaku_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save danmaku config error:', e);
    }
  }
  
  // 获取配置
  getConfig(): DanmakuConfig {
    return { ...this.config };
  }
  
  // 更新配置
  updateConfig(partial: Partial<DanmakuConfig>): void {
    this.config = { ...this.config, ...partial };
    this.saveConfig();
  }
  
  // 连接到直播平台
  async connect(platform: string, roomId: string): Promise<boolean> {
    if (this.status === 'connected') {
      await this.disconnect();
    }
    
    this.platform = platform;
    this.roomId = roomId;
    this.status = 'connecting';
    
    this.notifyListeners({
      type: 'status_change',
      status: 'connecting',
    });
    
    try {
      // 根据平台选择连接方式
      const success = await this.connectToPlatform(platform, roomId);
      
      if (success) {
        this.status = 'connected';
        this.stats.startTime = Date.now();
        
        this.notifyListeners({
          type: 'status_change',
          status: 'connected',
          platform,
          roomId,
        });
        
        return true;
      } else {
        throw new Error('连接失败');
      }
      
    } catch (error) {
      console.error('Connect error:', error);
      this.status = 'error';
      
      this.notifyListeners({
        type: 'status_change',
        status: 'error',
        error: error instanceof Error ? error.message : '连接失败',
      });
      
      return false;
    }
  }
  
  // 连接到具体平台
  private async connectToPlatform(platform: string, roomId: string): Promise<boolean> {
    // 这里实现各平台的 WebSocket 连接
    // 暂时模拟连接成功
    
    switch (platform) {
      case 'bilibili':
        return this.connectToBilibili(roomId);
      case 'douyin':
        return this.connectToDouyin(roomId);
      case 'kuaishou':
        return this.connectToKuaishou(roomId);
      default:
        console.warn(`Unsupported platform: ${platform}`);
        return this.simulateConnection();
    }
  }
  
  // 连接到 B站
  private async connectToBilibili(roomId: string): Promise<boolean> {
    // B站弹幕 WebSocket 连接
    // 实际实现需要调用 B站 API
    return this.simulateConnection();
  }
  
  // 连接到抖音
  private async connectToDouyin(roomId: string): Promise<boolean> {
    // 抖音弹幕连接
    return this.simulateConnection();
  }
  
  // 连接到快手
  private async connectToKuaishou(roomId: string): Promise<boolean> {
    // 快手弹幕连接
    return this.simulateConnection();
  }
  
  // 模拟连接（开发测试用）
  private async simulateConnection(): Promise<boolean> {
    return new Promise((resolve) => {
      setTimeout(() => {
        // 模拟接收弹幕
        this.startSimulatedDanmaku();
        resolve(true);
      }, 1000);
    });
  }
  
  // 模拟弹幕（开发测试用）
  private startSimulatedDanmaku(): void {
    const simulatedUsers = [
      { id: 'user1', name: '小明' },
      { id: 'user2', name: '小红' },
      { id: 'user3', name: '小刚' },
      { id: 'user4', name: '小丽' },
      { id: 'user5', name: '小王' },
    ];
    
    const simulatedMessages = [
      '你好呀！',
      '主播好可爱',
      '今天聊什么？',
      '哈哈哈',
      '666',
      '太厉害了',
      '学到了',
      '支持一下',
    ];
    
    // 每隔 3-8 秒生成一条弹幕
    const generateDanmaku = () => {
      if (this.status !== 'connected') return;
      
      const user = simulatedUsers[Math.floor(Math.random() * simulatedUsers.length)];
      const message = simulatedMessages[Math.floor(Math.random() * simulatedMessages.length)];
      
      const danmaku: DanmakuMessage = {
        id: `danmaku_${Date.now()}`,
        type: 'text',
        userId: user.id,
        username: user.name,
        content: message,
        timestamp: Date.now(),
        platform: this.platform,
      };
      
      this.handleDanmaku(danmaku);
      
      // 随机间隔
      const interval = 3000 + Math.random() * 5000;
      setTimeout(generateDanmaku, interval);
    };
    
    setTimeout(generateDanmaku, 2000);
  }
  
  // 处理弹幕
  private async handleDanmaku(danmaku: DanmakuMessage): Promise<void> {
    this.stats.totalDanmaku++;
    this.danmakuQueue.push(danmaku);
    
    // 通知监听器
    this.notifyListeners({
      type: 'danmaku',
      danmaku,
    });
    
    // 检查是否需要回复
    if (this.config.autoReply && danmaku.type === 'text') {
      await this.processReply(danmaku);
    }
    
    // 处理礼物
    if (danmaku.type === 'gift' && this.config.giftThanks) {
      await this.thankForGift(danmaku);
    }
    
    // 处理关注
    if (danmaku.type === 'follow' && this.config.followThanks) {
      await this.thankForFollow(danmaku);
    }
  }
  
  // 处理回复
  private async processReply(danmaku: DanmakuMessage): Promise<void> {
    // 检查回复概率
    if (Math.random() > this.config.replyChance) {
      return;
    }
    
    // 检查过滤词
    if (this.hasFilterWord(danmaku.content)) {
      return;
    }
    
    // 延迟回复
    await this.delay(this.config.replyDelay);
    
    try {
      // 生成回复
      const reply = await this.generateReply(danmaku);
      
      if (reply) {
        this.stats.totalReplies++;
        
        // 添加到回复队列
        this.replyQueue.push({ danmaku, reply });
        
        // 通知监听器
        this.notifyListeners({
          type: 'reply',
          danmaku,
          reply,
        });
      }
      
    } catch (error) {
      console.error('Generate reply error:', error);
    }
  }
  
  // 生成回复
  private async generateReply(danmaku: DanmakuMessage): Promise<string | null> {
    // 使用本地 AI 生成回复
    const prompt = `用户"${danmaku.username}"说：${danmaku.content}\n请用简短友好的方式回复：`;
    
    try {
      const reply = await localAI.generateResponse(
        prompt,
        { id: 'danmaku', name: '主播', systemPrompt: '你是一个直播主播，正在和观众互动' } as any,
        [],
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.8, maxTokens: 50, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      // 截断到最大长度
      if (reply.length > this.config.maxReplyLength) {
        return reply.substring(0, this.config.maxReplyLength) + '...';
      }
      
      return reply;
      
    } catch (error) {
      console.error('Generate reply error:', error);
      return null;
    }
  }
  
  // 感谢礼物
  private async thankForGift(danmaku: DanmakuMessage): Promise<void> {
    this.stats.totalGifts++;
    
    const thanksMessage = `谢谢${danmaku.username}送的${danmaku.giftName || '礼物'}！`;
    
    this.notifyListeners({
      type: 'gift_thanks',
      danmaku,
      message: thanksMessage,
    });
  }
  
  // 感谢关注
  private async thankForFollow(danmaku: DanmakuMessage): Promise<void> {
    this.stats.totalFollows++;
    
    const thanksMessage = `谢谢${danmaku.username}的关注！`;
    
    this.notifyListeners({
      type: 'follow_thanks',
      danmaku,
      message: thanksMessage,
    });
  }
  
  // 检查过滤词
  private hasFilterWord(content: string): boolean {
    return this.config.filterWords.some(word => content.includes(word));
  }
  
  // 断开连接
  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.status = 'disconnected';
    
    this.notifyListeners({
      type: 'status_change',
      status: 'disconnected',
    });
  }
  
  // 获取状态
  getStatus(): ConnectionStatus {
    return this.status;
  }
  
  // 获取弹幕队列
  getDanmakuQueue(): DanmakuMessage[] {
    return [...this.danmakuQueue];
  }
  
  // 获取回复队列
  getReplyQueue(): Array<{ danmaku: DanmakuMessage; reply: string }> {
    return [...this.replyQueue];
  }
  
  // 清空队列
  clearQueues(): void {
    this.danmakuQueue = [];
    this.replyQueue = [];
  }
  
  // 注册事件监听
  onEvent(callback: (event: any) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }
  
  // 通知监听器
  private notifyListeners(event: any): void {
    this.listeners.forEach(listener => listener(event));
  }
  
  // 获取统计信息
  getStats() {
    return {
      ...this.stats,
      uptime: this.stats.startTime > 0 ? Date.now() - this.stats.startTime : 0,
      queueSize: this.danmakuQueue.length,
      replyQueueSize: this.replyQueue.length,
    };
  }
  
  // 重置统计
  resetStats(): void {
    this.stats = {
      totalDanmaku: 0,
      totalReplies: 0,
      totalGifts: 0,
      totalFollows: 0,
      startTime: 0,
    };
  }
  
  // 延迟
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // 是否已连接
  isConnected(): boolean {
    return this.status === 'connected';
  }
  
  // 获取平台
  getPlatform(): string {
    return this.platform;
  }
  
  // 获取房间号
  getRoomId(): string {
    return this.roomId;
  }
}

// 单例
export const danmakuService = DanmakuService.getInstance();

export default danmakuService;
