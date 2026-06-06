// ============================================
// 多 Agent 系统 - 多个 AI 角色协作
// ============================================
import { MMKV } from 'react-native-mmkv';
import { localAI } from '../localAI';
import { emotionService } from '../emotion';
import type { Character, Message } from '../../types';

const storage = new MMKV({ id: 'multi-agent' });

// Agent 角色
export interface AgentRole {
  id: string;
  name: string;
  description: string;
  personality: string;
  speakingStyle: string;
  avatar: string;
  expertise: string[]; // 专长领域
}

// Agent 消息
export interface AgentMessage {
  id: string;
  agentId: string;
  agentName: string;
  content: string;
  timestamp: Date;
  messageType: 'text' | 'action' | 'thought';
  emotion?: string;
  targetAgentId?: string; // @某个 Agent
}

// 协作模式
export type CollaborationMode = 
  | 'discussion'    // 讨论模式：所有 Agent 自由发言
  | 'debate'        // 辩论模式：正反方辩论
  | 'collaboration' // 协作模式：分工合作
  | 'mentor'        // 导师模式：一个主导，其他辅助
  | 'storytelling'; // 故事模式：接力讲故事

// 多 Agent 配置
export interface MultiAgentConfig {
  // 协作模式
  mode: CollaborationMode;
  
  // 最大 Agent 数量
  maxAgents: number;
  
  // 回复延迟 (ms)
  replyDelay: number;
  
  // 是否启用
  enabled: boolean;
  
  // 自动发言概率
  autoSpeakChance: number;
}

// 默认配置
const DEFAULT_CONFIG: MultiAgentConfig = {
  mode: 'discussion',
  maxAgents: 5,
  replyDelay: 800,
  enabled: true,
  autoSpeakChance: 0.6,
};

// 预设 Agent 角色
export const PRESET_AGENTS: AgentRole[] = [
  {
    id: 'agent-leader',
    name: '领导者',
    description: '负责组织和协调讨论',
    personality: '果断、有条理、善于总结',
    speakingStyle: '简洁明了，善于归纳',
    avatar: '👔',
    expertise: ['组织', '协调', '决策'],
  },
  {
    id: 'agent-thinker',
    name: '思考者',
    description: '负责深入分析和思考',
    personality: '理性、逻辑性强、善于分析',
    speakingStyle: '条理清晰，喜欢用数据说话',
    avatar: '🤔',
    expertise: ['分析', '逻辑', '研究'],
  },
  {
    id: 'agent-creative',
    name: '创意者',
    description: '负责提供创意和新想法',
    personality: '活泼、有想象力、思维跳跃',
    speakingStyle: '充满激情，喜欢用比喻',
    avatar: '💡',
    expertise: ['创意', '想象', '灵感'],
  },
  {
    id: 'agent-critic',
    name: '批评者',
    description: '负责发现问题和提出改进',
    personality: '严谨、注重细节、追求完美',
    speakingStyle: '直接指出问题，提供建议',
    avatar: '🔍',
    expertise: ['审查', '改进', '质量'],
  },
  {
    id: 'agent-synthesizer',
    name: '综合者',
    description: '负责整合各方观点',
    personality: '包容、善于沟通、寻求共识',
    speakingStyle: '善于总结，寻找共同点',
    avatar: '🤝',
    expertise: ['整合', '沟通', '共识'],
  },
];

class MultiAgentService {
  private static instance: MultiAgentService;
  private config: MultiAgentConfig;
  private agents: Map<string, { role: AgentRole; character?: Character }> = new Map();
  private messages: AgentMessage[] = [];
  private currentDiscussion: string = '';
  private isActive: boolean = false;
  
  // 事件回调
  private listeners: Array<(event: any) => void> = [];
  
  private constructor() {
    this.config = this.loadConfig();
  }
  
  static getInstance(): MultiAgentService {
    if (!MultiAgentService.instance) {
      MultiAgentService.instance = new MultiAgentService();
    }
    return MultiAgentService.instance;
  }
  
  // 加载配置
  private loadConfig(): MultiAgentConfig {
    try {
      const saved = storage.getString('multi_agent_config');
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load multi-agent config error:', e);
    }
    return { ...DEFAULT_CONFIG };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('multi_agent_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save multi-agent config error:', e);
    }
  }
  
  // 获取配置
  getConfig(): MultiAgentConfig {
    return { ...this.config };
  }
  
  // 更新配置
  updateConfig(partial: Partial<MultiAgentConfig>): void {
    this.config = { ...this.config, ...partial };
    this.saveConfig();
  }
  
  // 添加 Agent
  addAgent(role: AgentRole, character?: Character): boolean {
    if (this.agents.size >= this.config.maxAgents) {
      return false;
    }
    
    this.agents.set(role.id, { role, character });
    
    this.notifyListeners({
      type: 'agent_added',
      agent: role,
    });
    
    return true;
  }
  
  // 移除 Agent
  removeAgent(agentId: string): boolean {
    if (!this.agents.has(agentId)) {
      return false;
    }
    
    this.agents.delete(agentId);
    
    this.notifyListeners({
      type: 'agent_removed',
      agentId,
    });
    
    return true;
  }
  
  // 获取所有 Agent
  getAgents(): Array<{ role: AgentRole; character?: Character }> {
    return Array.from(this.agents.values());
  }
  
  // 开始讨论
  async startDiscussion(topic: string): Promise<boolean> {
    if (this.agents.size < 2) {
      console.warn('Need at least 2 agents to start discussion');
      return false;
    }
    
    this.currentDiscussion = topic;
    this.isActive = true;
    this.messages = [];
    
    // 添加系统消息
    this.addMessage({
      id: `msg_${Date.now()}`,
      agentId: 'system',
      agentName: '系统',
      content: `讨论主题：${topic}`,
      timestamp: new Date(),
      messageType: 'text',
    });
    
    this.notifyListeners({
      type: 'discussion_started',
      topic,
    });
    
    // 触发第一个 Agent 发言
    await this.triggerNextAgent();
    
    return true;
  }
  
  // 停止讨论
  stopDiscussion(): void {
    this.isActive = false;
    
    this.notifyListeners({
      type: 'discussion_stopped',
    });
  }
  
  // 用户发言
  async userSpeak(content: string): Promise<void> {
    if (!this.isActive) return;
    
    // 添加用户消息
    this.addMessage({
      id: `msg_${Date.now()}_user`,
      agentId: 'user',
      agentName: '用户',
      content,
      timestamp: new Date(),
      messageType: 'text',
    });
    
    // 触发 Agent 回复
    await this.triggerAgentReply(content);
  }
  
  // 触发 Agent 回复
  private async triggerAgentReply(userMessage: string): Promise<void> {
    const agents = Array.from(this.agents.values());
    
    // 根据模式选择回复策略
    switch (this.config.mode) {
      case 'discussion':
        await this.discussionReply(agents, userMessage);
        break;
      case 'debate':
        await this.debateReply(agents, userMessage);
        break;
      case 'collaboration':
        await this.collaborationReply(agents, userMessage);
        break;
      case 'mentor':
        await this.mentorReply(agents, userMessage);
        break;
      case 'storytelling':
        await this.storytellingReply(agents, userMessage);
        break;
    }
  }
  
  // 讨论模式回复
  private async discussionReply(agents: Array<{ role: AgentRole; character?: Character }>, userMessage: string): Promise<void> {
    // 随机选择 1-2 个 Agent 回复
    const replyCount = Math.random() > 0.5 ? 2 : 1;
    const selectedAgents = this.selectRandomAgents(agents, replyCount);
    
    for (const agent of selectedAgents) {
      await this.delay(this.config.replyDelay);
      await this.generateAgentReply(agent, userMessage);
    }
  }
  
  // 辩论模式回复
  private async debateReply(agents: Array<{ role: AgentRole; character?: Character }>, userMessage: string): Promise<void> {
    // 正反方轮流发言
    const half = Math.ceil(agents.length / 2);
    const proAgents = agents.slice(0, half);
    const conAgents = agents.slice(half);
    
    // 正方发言
    for (const agent of proAgents) {
      await this.delay(this.config.replyDelay);
      await this.generateAgentReply(agent, userMessage, '支持');
    }
    
    // 反方发言
    for (const agent of conAgents) {
      await this.delay(this.config.replyDelay);
      await this.generateAgentReply(agent, userMessage, '反对');
    }
  }
  
  // 协作模式回复
  private async collaborationReply(agents: Array<{ role: AgentRole; character?: Character }>, userMessage: string): Promise<void> {
    // 根据专长分配任务
    for (const agent of agents) {
      if (this.isAgentExpertIn(agent, userMessage)) {
        await this.delay(this.config.replyDelay);
        await this.generateAgentReply(agent, userMessage);
        break;
      }
    }
  }
  
  // 导师模式回复
  private async mentorReply(agents: Array<{ role: AgentRole; character?: Character }>, userMessage: string): Promise<void> {
    // 导师先发言
    const mentor = agents[0];
    await this.delay(this.config.replyDelay);
    await this.generateAgentReply(mentor, userMessage);
    
    // 其他 Agent 补充
    for (let i = 1; i < agents.length; i++) {
      if (Math.random() < this.config.autoSpeakChance) {
        await this.delay(this.config.replyDelay * 0.5);
        await this.generateAgentReply(agents[i], userMessage, '补充');
      }
    }
  }
  
  // 故事模式回复
  private async storytellingReply(agents: Array<{ role: AgentRole; character?: Character }>, userMessage: string): Promise<void> {
    // 接力讲故事
    const lastAgent = this.getLastSpeaker();
    const nextAgent = this.getNextAgent(lastAgent?.agentId);
    
    if (nextAgent) {
      await this.delay(this.config.replyDelay);
      await this.generateAgentReply(nextAgent, userMessage, '继续');
    }
  }
  
  // 生成 Agent 回复
  private async generateAgentReply(
    agent: { role: AgentRole; character?: Character },
    context: string,
    stance?: string
  ): Promise<void> {
    try {
      // 构建提示词
      const prompt = this.buildAgentPrompt(agent, context, stance);
      
      // 使用本地 AI 生成回复
      const character = agent.character || {
        id: agent.role.id,
        name: agent.role.name,
        systemPrompt: `你是${agent.role.name}，${agent.role.description}。${agent.role.personality}。说话风格：${agent.role.speakingStyle}`,
      } as Character;
      
      const reply = await localAI.generateResponse(
        prompt,
        character,
        [],
        { provider: 'local', model: 'local', apiKey: '', temperature: 0.9, maxTokens: 150, topP: 1, frequencyPenalty: 0, presencePenalty: 0 }
      );
      
      if (reply) {
        // 分析情感
        const emotion = emotionService.analyze(reply);
        
        // 添加消息
        this.addMessage({
          id: `msg_${Date.now()}_${agent.role.id}`,
          agentId: agent.role.id,
          agentName: agent.role.name,
          content: reply,
          timestamp: new Date(),
          messageType: 'text',
          emotion: emotion.emotion,
        });
        
        this.notifyListeners({
          type: 'agent_spoke',
          agent: agent.role,
          message: reply,
        });
      }
      
    } catch (error) {
      console.error(`Generate reply for ${agent.role.name} error:`, error);
    }
  }
  
  // 构建 Agent 提示词
  private buildAgentPrompt(
    agent: { role: AgentRole; character?: Character },
    context: string,
    stance?: string
  ): string {
    let prompt = `你是${agent.role.name}，${agent.role.description}。
    
性格特点：${agent.role.personality}
说话风格：${agent.role.speakingStyle}
专长领域：${agent.role.expertise.join('、')}

当前讨论：${this.currentDiscussion}
用户说：${context}`;
    
    if (stance) {
      prompt += `\n你的立场：${stance}`;
    }
    
    prompt += `\n\n请以${agent.role.name}的身份回复，保持角色特点，回复简洁（50字以内）：`;
    
    return prompt;
  }
  
  // 选择随机 Agent
  private selectRandomAgents(agents: Array<{ role: AgentRole; character?: Character }>, count: number): Array<{ role: AgentRole; character?: Character }> {
    const shuffled = [...agents].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, count);
  }
  
  // 检查 Agent 是否是专家
  private isAgentExpertIn(agent: { role: AgentRole; character?: Character }, topic: string): boolean {
    const topicLower = topic.toLowerCase();
    return agent.role.expertise.some(exp => topicLower.includes(exp.toLowerCase()));
  }
  
  // 获取上一个发言者
  private getLastSpeaker(): AgentMessage | null {
    const agentMessages = this.messages.filter(m => m.agentId !== 'system' && m.agentId !== 'user');
    return agentMessages.length > 0 ? agentMessages[agentMessages.length - 1] : null;
  }
  
  // 获取下一个 Agent
  private getNextAgent(lastAgentId?: string): { role: AgentRole; character?: Character } | null {
    const agents = Array.from(this.agents.values());
    if (agents.length === 0) return null;
    
    if (!lastAgentId) return agents[0];
    
    const lastIndex = agents.findIndex(a => a.role.id === lastAgentId);
    const nextIndex = (lastIndex + 1) % agents.length;
    
    return agents[nextIndex];
  }
  
  // 触发下一个 Agent
  private async triggerNextAgent(): Promise<void> {
    const agents = Array.from(this.agents.values());
    if (agents.length === 0) return;
    
    const lastSpeaker = this.getLastSpeaker();
    const nextAgent = this.getNextAgent(lastSpeaker?.agentId);
    
    if (nextAgent) {
      await this.delay(this.config.replyDelay);
      await this.generateAgentReply(nextAgent, this.currentDiscussion);
    }
  }
  
  // 添加消息
  private addMessage(message: AgentMessage): void {
    this.messages.push(message);
    
    // 限制消息数量
    if (this.messages.length > 100) {
      this.messages = this.messages.slice(-100);
    }
  }
  
  // 获取消息
  getMessages(): AgentMessage[] {
    return [...this.messages];
  }
  
  // 清空消息
  clearMessages(): void {
    this.messages = [];
  }
  
  // 获取预设 Agent
  getPresetAgents(): AgentRole[] {
    return [...PRESET_AGENTS];
  }
  
  // 是否活跃
  getIsActive(): boolean {
    return this.isActive;
  }
  
  // 获取当前讨论主题
  getCurrentTopic(): string {
    return this.currentDiscussion;
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
  
  // 延迟
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// 单例
export const multiAgentService = MultiAgentService.getInstance();

export default multiAgentService;
