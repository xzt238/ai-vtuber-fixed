// ============================================
// 多角色群聊服务
// ============================================
import { MMKV } from 'react-native-mmkv';
import { localAI } from './localAI';
import { emotionService } from './emotion';
import type { Character, Message } from '../types';

const storage = new MMKV({ id: 'group-chat' });

// 群聊配置
export interface GroupChatConfig {
  id: string;
  name: string;
  description?: string;
  characterIds: string[]; // 参与的角色 ID 列表
  maxCharacters: number; // 最大角色数
  autoReply: boolean; // 是否自动回复
  replyDelay: number; // 回复延迟 (ms)
  replyChance: number; // 回复概率 (0-1)
  createdAt: Date;
  updatedAt: Date;
}

// 群聊消息
export interface GroupMessage extends Message {
  characterId?: string; // 发送消息的角色 ID（用户消息为空）
  characterName?: string;
  characterAvatar?: string;
  isTyping?: boolean; // 是否正在输入
}

// 群聊状态
export interface GroupChatState {
  config: GroupChatConfig;
  messages: GroupMessage[];
  activeCharacters: Character[];
  isGenerating: boolean;
  typingCharacters: Set<string>; // 正在输入的角色 ID
}

// 预设群聊场景
export const PRESET_SCENARIOS: Array<{
  id: string;
  name: string;
  description: string;
  characterIds: string[];
  systemPrompt: string;
}> = [
  {
    id: 'daily-chat',
    name: '日常闲聊',
    description: '轻松愉快的日常对话',
    characterIds: ['preset-sakura', 'preset-kuro', 'preset-sora'],
    systemPrompt: '你们是好朋友，正在进行轻松愉快的日常聊天。每个人都有自己的性格特点，会互相回应和互动。',
  },
  {
    id: 'study-group',
    name: '学习小组',
    description: '一起讨论学习问题',
    characterIds: ['preset-luna', 'preset-yuki'],
    systemPrompt: '你们是一个学习小组的成员，正在讨论学习问题。月光负责讲解知识，雪兔负责提问和总结。',
  },
  {
    id: 'party',
    name: '派对模式',
    description: '热闹的多人派对',
    characterIds: ['preset-sora', 'preset-kuro', 'preset-yuki', 'preset-sakura'],
    systemPrompt: '你们正在参加一个热闹的派对！气氛活跃，大家会互相调侃、开玩笑，分享有趣的事情。',
  },
  {
    id: 'adventure',
    name: '冒险小队',
    description: '组队冒险的故事',
    characterIds: ['preset-sora', 'preset-luna', 'preset-kuro'],
    systemPrompt: '你们是一个冒险小队，正在探索神秘的世界。星空是队长，月光是军师，黑猫是刺客。请即兴创作冒险故事。',
  },
];

// 自定义场景
export interface CustomScenario {
  id: string;
  name: string;
  description: string;
  characterIds: string[];
  systemPrompt: string;
  createdAt: Date;
}

class GroupChatService {
  private currentChat: GroupChatState | null = null;
  private messageQueue: Array<{ characterId: string; content: string }> = [];
  private isProcessing = false;
  private updateCallbacks: Array<(state: GroupChatState) => void> = [];
  private customScenarios: CustomScenario[] = [];
  
  constructor() {
    this.loadState();
    this.loadCustomScenarios();
  }
  
  // 加载状态
  private loadState() {
    try {
      const saved = storage.getString('current_group_chat');
      if (saved) {
        const parsed = JSON.parse(saved);
        // 恢复日期对象
        parsed.config.createdAt = new Date(parsed.config.createdAt);
        parsed.config.updatedAt = new Date(parsed.config.updatedAt);
        parsed.messages = parsed.messages.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }));
        this.currentChat = parsed;
      }
    } catch (e) {
      console.error('Load group chat state error:', e);
    }
  }
  
  // 保存状态
  private saveState() {
    try {
      if (this.currentChat) {
        storage.set('current_group_chat', JSON.stringify(this.currentChat));
      } else {
        storage.delete('current_group_chat');
      }
    } catch (e) {
      console.error('Save group chat state error:', e);
    }
  }
  
  // 创建群聊
  createGroupChat(config: Omit<GroupChatConfig, 'id' | 'createdAt' | 'updatedAt'>): GroupChatConfig {
    const now = new Date();
    const newConfig: GroupChatConfig = {
      ...config,
      id: `group_${Date.now()}`,
      createdAt: now,
      updatedAt: now,
    };
    
    this.currentChat = {
      config: newConfig,
      messages: [],
      activeCharacters: [],
      isGenerating: false,
      typingCharacters: new Set(),
    };
    
    this.saveState();
    return newConfig;
  }
  
  // 加载预设场景
  loadScenario(scenarioId: string, characters: Character[]): GroupChatConfig | null {
    const scenario = PRESET_SCENARIOS.find(s => s.id === scenarioId);
    if (!scenario) return null;
    
    // 过滤出存在的角色
    const activeCharacters = characters.filter(c => 
      scenario.characterIds.includes(c.id)
    );
    
    if (activeCharacters.length === 0) return null;
    
    const config = this.createGroupChat({
      name: scenario.name,
      description: scenario.description,
      characterIds: activeCharacters.map(c => c.id),
      maxCharacters: 5,
      autoReply: true,
      replyDelay: 1000,
      replyChance: 0.7,
    });
    
    if (this.currentChat) {
      this.currentChat.activeCharacters = activeCharacters;
      
      // 添加系统消息
      this.addSystemMessage(scenario.systemPrompt);
      
      this.saveState();
      this.notifyUpdate();
    }
    
    return config;
  }
  
  // 获取当前群聊
  getCurrentChat(): GroupChatState | null {
    return this.currentChat;
  }
  
  // 添加系统消息
  addSystemMessage(content: string) {
    if (!this.currentChat) return;
    
    const message: GroupMessage = {
      id: `msg_${Date.now()}_system`,
      role: 'system',
      content,
      timestamp: new Date(),
    };
    
    this.currentChat.messages.push(message);
    this.saveState();
  }
  
  // 发送用户消息
  async sendUserMessage(content: string): Promise<void> {
    if (!this.currentChat) return;
    
    // 添加用户消息
    const userMessage: GroupMessage = {
      id: `msg_${Date.now()}_user`,
      role: 'user',
      content,
      timestamp: new Date(),
    };
    
    this.currentChat.messages.push(userMessage);
    this.notifyUpdate();
    
    // 触发 AI 回复
    if (this.currentChat.config.autoReply) {
      await this.triggerAIReplies(content);
    }
    
    this.saveState();
  }
  
  // 触发 AI 回复
  private async triggerAIReplies(userMessage: string) {
    if (!this.currentChat || this.currentChat.activeCharacters.length === 0) return;
    
    this.currentChat.isGenerating = true;
    this.notifyUpdate();
    
    // 随机选择要回复的角色
    const charactersToReply = this.currentChat.activeCharacters.filter(() => 
      Math.random() < this.currentChat!.config.replyChance
    );
    
    // 至少一个角色回复
    if (charactersToReply.length === 0 && this.currentChat.activeCharacters.length > 0) {
      const randomIndex = Math.floor(Math.random() * this.currentChat.activeCharacters.length);
      charactersToReply.push(this.currentChat.activeCharacters[randomIndex]);
    }
    
    // 按顺序生成回复
    for (const character of charactersToReply) {
      await this.generateCharacterReply(character, userMessage);
      
      // 回复间隔
      if (charactersToReply.indexOf(character) < charactersToReply.length - 1) {
        await this.delay(this.currentChat.config.replyDelay);
      }
    }
    
    this.currentChat.isGenerating = false;
    this.notifyUpdate();
    this.saveState();
  }
  
  // 生成角色回复
  private async generateCharacterReply(character: Character, userMessage: string) {
    if (!this.currentChat) return;
    
    // 显示正在输入
    this.currentChat.typingCharacters.add(character.id);
    this.notifyUpdate();
    
    try {
      // 构建上下文
      const contextMessages = this.currentChat.messages.slice(-10);
      const context = contextMessages.map(m => {
        if (m.role === 'system') return `[系统] ${m.content}`;
        if (m.role === 'user') return `[用户] ${m.content}`;
        if (m.characterId) return `[${m.characterName}] ${m.content}`;
        return m.content;
      }).join('\n');
      
      // 生成回复
      const prompt = `${character.systemPrompt}\n\n当前对话:\n${context}\n\n用户说: ${userMessage}\n\n请以${character.name}的身份回复，保持角色性格，回复简短自然：`;
      
      // 使用本地 AI 生成回复
      const conversationHistory = this.currentChat!.messages.slice(-5).map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
      }));
      
      const reply = await localAI.generateResponse(
        prompt, 
        character, 
        conversationHistory, 
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.8, maxTokens: 200, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      // 分析情感
      const emotion = emotionService.analyze(reply);
      
      // 添加角色消息
      const characterMessage: GroupMessage = {
        id: `msg_${Date.now()}_${character.id}`,
        role: 'assistant',
        content: reply,
        timestamp: new Date(),
        characterId: character.id,
        characterName: character.name,
        characterAvatar: character.avatar,
      };
      
      this.currentChat.messages.push(characterMessage);
      this.notifyUpdate();
      
    } catch (error) {
      console.error(`Generate reply for ${character.name} error:`, error);
    } finally {
      // 移除正在输入状态
      this.currentChat.typingCharacters.delete(character.id);
      this.notifyUpdate();
    }
  }
  
  // 手动触发指定角色回复
  async triggerCharacterReply(characterId: string, context?: string): Promise<void> {
    if (!this.currentChat) return;
    
    const character = this.currentChat.activeCharacters.find(c => c.id === characterId);
    if (!character) return;
    
    const lastUserMessage = context || 
      this.currentChat.messages.filter(m => m.role === 'user').pop()?.content || 
      '请继续说话';
    
    await this.generateCharacterReply(character, lastUserMessage);
    this.saveState();
  }
  
  // 获取消息列表
  getMessages(): GroupMessage[] {
    return this.currentChat?.messages || [];
  }
  
  // 获取活跃角色
  getActiveCharacters(): Character[] {
    return this.currentChat?.activeCharacters || [];
  }
  
  // 获取正在输入的角色
  getTypingCharacters(): string[] {
    return this.currentChat ? [...this.currentChat.typingCharacters] : [];
  }
  
  // 是否正在生成
  isGenerating(): boolean {
    return this.currentChat?.isGenerating || false;
  }
  
  // 清空消息
  clearMessages() {
    if (this.currentChat) {
      this.currentChat.messages = [];
      this.saveState();
      this.notifyUpdate();
    }
  }
  
  // 结束群聊
  endGroupChat() {
    this.currentChat = null;
    this.saveState();
    this.notifyUpdate();
  }
  
  // 注册更新回调
  onUpdate(callback: (state: GroupChatState) => void) {
    this.updateCallbacks.push(callback);
    return () => {
      this.updateCallbacks = this.updateCallbacks.filter(cb => cb !== callback);
    };
  }
  
  // 通知更新
  private notifyUpdate() {
    if (this.currentChat) {
      this.updateCallbacks.forEach(cb => cb(this.currentChat!));
    }
  }
  
  // 延迟
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // 获取预设场景
  getPresetScenarios() {
    return PRESET_SCENARIOS;
  }
  
  // 加载自定义场景
  private loadCustomScenarios(): void {
    try {
      const saved = storage.getString('custom_scenarios');
      if (saved) {
        this.customScenarios = JSON.parse(saved).map((s: any) => ({
          ...s,
          createdAt: new Date(s.createdAt),
        }));
      }
    } catch (e) {
      console.error('Load custom scenarios error:', e);
    }
  }
  
  // 保存自定义场景
  private saveCustomScenarios(): void {
    try {
      storage.set('custom_scenarios', JSON.stringify(this.customScenarios));
    } catch (e) {
      console.error('Save custom scenarios error:', e);
    }
  }
  
  // 创建自定义场景
  createCustomScenario(scenario: Omit<CustomScenario, 'id' | 'createdAt'>): CustomScenario {
    const newScenario: CustomScenario = {
      ...scenario,
      id: `custom_${Date.now()}`,
      createdAt: new Date(),
    };
    
    this.customScenarios.push(newScenario);
    this.saveCustomScenarios();
    
    return newScenario;
  }
  
  // 获取自定义场景
  getCustomScenarios(): CustomScenario[] {
    return [...this.customScenarios];
  }
  
  // 删除自定义场景
  deleteCustomScenario(id: string): boolean {
    const index = this.customScenarios.findIndex(s => s.id === id);
    if (index === -1) {
      return false;
    }
    
    this.customScenarios.splice(index, 1);
    this.saveCustomScenarios();
    return true;
  }
  
  // 获取所有场景（预设 + 自定义）
  getAllScenarios(): Array<CustomScenario | typeof PRESET_SCENARIOS[0]> {
    return [...PRESET_SCENARIOS, ...this.customScenarios];
  }
  
  // 加载自定义场景
  loadCustomScenario(scenarioId: string, characters: Character[]): GroupChatConfig | null {
    const scenario = this.customScenarios.find(s => s.id === scenarioId);
    if (!scenario) return null;
    
    // 过滤出存在的角色
    const activeCharacters = characters.filter(c => 
      scenario.characterIds.includes(c.id)
    );
    
    if (activeCharacters.length === 0) return null;
    
    const config = this.createGroupChat({
      name: scenario.name,
      description: scenario.description,
      characterIds: activeCharacters.map(c => c.id),
      maxCharacters: 5,
      autoReply: true,
      replyDelay: 1000,
      replyChance: 0.7,
    });
    
    if (this.currentChat) {
      this.currentChat.activeCharacters = activeCharacters;
      
      // 添加系统消息
      this.addSystemMessage(scenario.systemPrompt);
      
      this.saveState();
      this.notifyUpdate();
    }
    
    return config;
  }
}

// 单例
export const groupChatService = new GroupChatService();

export default groupChatService;
