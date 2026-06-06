// ============================================
// 游戏集成服务 - 移动端版本
// ============================================
import { MMKV } from 'react-native-mmkv';
import { localAI } from '../localAI';
import { ttsService } from '../tts';

const storage = new MMKV();

// 游戏类型
export type GameType = 
  | 'minecraft'
  | 'factorio'
  | 'terraria'
  | 'stardew_valley'
  | 'genshin'
  | 'lol'
  | 'valorant'
  | 'custom';

// 游戏状态
export interface GameState {
  gameType: GameType;
  isPlaying: boolean;
  currentScene: string;
  playerInfo: Record<string, any>;
  inventory: any[];
  achievements: string[];
  timestamp: number;
}

// 游戏动作
export interface GameAction {
  type: 'suggest' | 'warn' | 'celebrate' | 'help' | 'chat';
  content: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  data?: any;
}

// 游戏模板
export interface GameTemplate {
  id: string;
  name: string;
  gameType: GameType;
  description: string;
  icon: string;
  features: string[];
  tips: string[];
  commands: Record<string, string>;
}

// 预设游戏模板
const GAME_TEMPLATES: GameTemplate[] = [
  {
    id: 'minecraft',
    name: 'Minecraft',
    gameType: 'minecraft',
    description: '沙盒建造游戏，探索无限世界',
    icon: '⛏️',
    features: ['建造建议', '合成配方', '怪物应对', '红石教程'],
    tips: ['记得带火把下矿', '钻石在Y=11层最多', '苦力怕怕猫'],
    commands: {
      '合成': '查看合成配方',
      '建造': '获取建造建议',
      '攻略': '查看游戏攻略',
    },
  },
  {
    id: 'factorio',
    name: 'Factorio',
    gameType: 'factorio',
    description: '工厂建造游戏，自动化生产',
    icon: '🏭',
    features: ['工厂布局', '生产链优化', '防御设计', '电路逻辑'],
    tips: ['预留足够空间', '使用主总线设计', '及早自动化'],
    commands: {
      '布局': '查看工厂布局',
      '生产': '优化生产链',
      '防御': '设计防御系统',
    },
  },
  {
    id: 'terraria',
    name: 'Terraria',
    gameType: 'terraria',
    description: '2D沙盒冒险游戏',
    icon: '🗡️',
    features: ['Boss攻略', '装备推荐', '建筑教程', '钓鱼指南'],
    tips: ['先打克苏鲁之眼', '地牢有好装备', '蘑菇地有好东西'],
    commands: {
      'boss': '查看Boss攻略',
      '装备': '获取装备推荐',
      '建筑': '学习建筑技巧',
    },
  },
  {
    id: 'stardew_valley',
    name: 'Stardew Valley',
    gameType: 'stardew_valley',
    description: '农场模拟游戏',
    icon: '🌾',
    features: ['种植指南', '村民喜好', '钓鱼技巧', '矿洞攻略'],
    tips: ['春天种草莓', '秋天种南瓜', '雨天去钓鱼'],
    commands: {
      '种植': '查看种植指南',
      '村民': '了解村民喜好',
      '钓鱼': '学习钓鱼技巧',
    },
  },
  {
    id: 'genshin',
    name: '原神',
    gameType: 'genshin',
    description: '开放世界冒险游戏',
    icon: '⚔️',
    features: ['角色培养', '队伍搭配', '圣遗物推荐', '任务攻略'],
    tips: ['树脂别浪费', '每日委托要做', '探索度100%有成就'],
    commands: {
      '角色': '查看角色培养',
      '队伍': '推荐队伍搭配',
      '攻略': '查看任务攻略',
    },
  },
  {
    id: 'lol',
    name: '英雄联盟',
    gameType: 'lol',
    description: 'MOBA竞技游戏',
    icon: '🏆',
    features: ['英雄攻略', '出装推荐', '对线技巧', '团战策略'],
    tips: ['视野很重要', '补刀是基本功', '团战别单带'],
    commands: {
      '英雄': '查看英雄攻略',
      '出装': '获取出装推荐',
      '对线': '学习对线技巧',
    },
  },
];

// 游戏集成服务类
class GameService {
  private currentGame: GameType | null = null;
  private gameState: GameState | null = null;
  private gameHistory: Array<{ game: GameType; timestamp: number; score?: number }> = [];
  private actionCallbacks: Array<(action: GameAction) => void> = [];
  private templates: GameTemplate[] = GAME_TEMPLATES;
  
  constructor() {
    this.loadHistory();
  }
  
  // 加载历史记录
  private loadHistory(): void {
    try {
      const saved = storage.getString('game_history');
      if (saved) {
        this.gameHistory = JSON.parse(saved);
      }
    } catch (e) {
      console.error('Load game history error:', e);
    }
  }
  
  // 保存历史记录
  private saveHistory(): void {
    try {
      storage.set('game_history', JSON.stringify(this.gameHistory.slice(-50)));
    } catch (e) {
      console.error('Save game history error:', e);
    }
  }
  
  // 获取所有游戏模板
  getTemplates(): GameTemplate[] {
    return [...this.templates];
  }
  
  // 获取指定游戏模板
  getTemplate(gameType: GameType): GameTemplate | undefined {
    return this.templates.find(t => t.gameType === gameType);
  }
  
  // 开始游戏会话
  startGame(gameType: GameType): GameState {
    const template = this.getTemplate(gameType);
    
    this.currentGame = gameType;
    this.gameState = {
      gameType,
      isPlaying: true,
      currentScene: 'menu',
      playerInfo: {},
      inventory: [],
      achievements: [],
      timestamp: Date.now(),
    };
    
    // 记录历史
    this.gameHistory.push({
      game: gameType,
      timestamp: Date.now(),
    });
    this.saveHistory();
    
    // 通知开始
    this.notifyAction({
      type: 'chat',
      content: `已启动${template?.name || gameType}游戏助手！有什么可以帮你的？`,
      priority: 'low',
    });
    
    return { ...this.gameState };
  }
  
  // 结束游戏会话
  endGame(): void {
    if (this.gameState) {
      this.gameState.isPlaying = false;
      this.gameState = null;
      this.currentGame = null;
    }
  }
  
  // 获取当前游戏状态
  getGameState(): GameState | null {
    return this.gameState ? { ...this.gameState } : null;
  }
  
  // 更新游戏状态
  updateGameState(updates: Partial<GameState>): void {
    if (this.gameState) {
      this.gameState = { ...this.gameState, ...updates };
    }
  }
  
  // 添加动作回调
  onAction(callback: (action: GameAction) => void): () => void {
    this.actionCallbacks.push(callback);
    return () => {
      this.actionCallbacks = this.actionCallbacks.filter(cb => cb !== callback);
    };
  }
  
  // 通知动作
  private notifyAction(action: GameAction): void {
    this.actionCallbacks.forEach(cb => {
      try {
        cb(action);
      } catch (e) {
        console.error('Game action callback error:', e);
      }
    });
  }
  
  // 发送游戏问题
  async askGameQuestion(question: string): Promise<string> {
    if (!this.currentGame) {
      return '请先选择一个游戏开始会话';
    }
    
    const template = this.getTemplate(this.currentGame);
    const gameName = template?.name || this.currentGame;
    
    // 构建提示词
    const prompt = `你是一个${gameName}游戏专家助手。玩家问：${question}
    
请根据你的知识给出详细、实用的回答。如果是关于：
- 合成/制作：给出具体配方
- 攻略/打法：给出步骤说明
- 建筑/设计：给出布局建议
- 问题/困难：给出解决方案

保持回答简洁但完整，适合在游戏中快速查看。`;
    
    try {
      // 使用本地AI生成回复
      const response = await localAI.generateResponse(
        prompt,
        { id: 'game', name: gameName, personality: '游戏专家' } as any,
        [],
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.7, maxTokens: 500, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      // 通知动作
      this.notifyAction({
        type: 'suggest',
        content: response,
        priority: 'medium',
      });
      
      return response;
    } catch (error) {
      console.error('Game question error:', error);
      return '抱歉，处理问题时出错了，请重试';
    }
  }
  
  // 获取游戏攻略
  async getGameGuide(topic: string): Promise<string> {
    if (!this.currentGame) {
      return '请先选择一个游戏开始会话';
    }
    
    const template = this.getTemplate(this.currentGame);
    const gameName = template?.name || this.currentGame;
    
    const prompt = `请提供${gameName}游戏的"${topic}"详细攻略，包括：
1. 基础介绍
2. 具体步骤/方法
3. 注意事项
4. 实用技巧

格式清晰，适合快速查阅。`;
    
    try {
      const response = await localAI.generateResponse(
        prompt,
        { id: 'game', name: gameName, personality: '游戏攻略专家' } as any,
        [],
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.7, maxTokens: 800, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      return response;
    } catch (error) {
      console.error('Game guide error:', error);
      return '获取攻略失败，请重试';
    }
  }
  
  // 获取物品信息
  async getItemInfo(itemName: string): Promise<string> {
    if (!this.currentGame) {
      return '请先选择一个游戏开始会话';
    }
    
    const template = this.getTemplate(this.currentGame);
    const gameName = template?.name || this.currentGame;
    
    const prompt = `请介绍${gameName}游戏中的"${itemName}"物品，包括：
1. 获取方式
2. 用途/效果
3. 合成配方（如有）
4. 相关技巧`;
    
    try {
      const response = await localAI.generateResponse(
        prompt,
        { id: 'game', name: gameName, personality: '游戏百科' } as any,
        [],
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.7, maxTokens: 500, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      return response;
    } catch (error) {
      console.error('Item info error:', error);
      return '获取物品信息失败，请重试';
    }
  }
  
  // 获取随机提示
  getRandomTip(): string {
    if (!this.currentGame) {
      return '请先选择一个游戏';
    }
    
    const template = this.getTemplate(this.currentGame);
    if (template && template.tips.length > 0) {
      return template.tips[Math.floor(Math.random() * template.tips.length)];
    }
    
    return '加油！';
  }
  
  // 获取游戏历史
  getGameHistory(): Array<{ game: GameType; timestamp: number; score?: number }> {
    return [...this.gameHistory];
  }
  
  // 获取游戏统计
  getGameStats(): Record<GameType, { count: number; totalTime: number }> {
    const stats: any = {};
    
    this.gameHistory.forEach(entry => {
      if (!stats[entry.game]) {
        stats[entry.game] = { count: 0, totalTime: 0 };
      }
      stats[entry.game].count++;
    });
    
    return stats;
  }
  
  // 清除历史
  clearHistory(): void {
    this.gameHistory = [];
    this.saveHistory();
  }
  
  // 添加自定义游戏模板
  addCustomTemplate(template: Omit<GameTemplate, 'id'>): GameTemplate {
    const newTemplate: GameTemplate = {
      ...template,
      id: `custom_${Date.now()}`,
    };
    
    this.templates.push(newTemplate);
    return newTemplate;
  }
  
  // 删除自定义模板
  removeCustomTemplate(id: string): boolean {
    const index = this.templates.findIndex(t => t.id === id);
    if (index === -1 || !id.startsWith('custom_')) {
      return false;
    }
    
    this.templates.splice(index, 1);
    return true;
  }
}

// 导出单例
export const gameService = new GameService();