// ============================================
// GuguGaga AI VTuber Mobile - 类型定义
// ============================================

// 情感类型
export type Emotion = 'happy' | 'sad' | 'angry' | 'surprised' | 'neutral' | 'love' | 'thinking';

// 用户相关
export interface User {
  id: string;
  name: string;
  avatar?: string;
  preferences: UserPreferences;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  fontSize: number;
  soundEnabled: boolean;
  vibrationEnabled: boolean;
  autoSave: boolean;
}

// 角色相关
export interface Character {
  id: string;
  name: string;
  avatar: string;
  description: string;
  personality: string;
  voiceId?: string;
  systemPrompt: string;
  greeting: string;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
}

// 对话相关
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  audioUrl?: string;
  imageUrl?: string;
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  characterId: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  summary?: string;
}

// 记忆相关
export interface Memory {
  id: string;
  characterId: string;
  content: string;
  importance: number;
  type: 'short_term' | 'long_term' | 'episodic';
  tags: string[];
  createdAt: Date;
  lastAccessed: Date;
  accessCount: number;
}

// AI 相关
export interface AIConfig {
  provider: LLMProvider;
  model: string;
  apiKey: string;
  baseUrl?: string;
  temperature: number;
  maxTokens: number;
  topP: number;
  frequencyPenalty: number;
  presencePenalty: number;
}

export type LLMProvider = 
  | 'openai'
  | 'claude'
  | 'gemini'
  | 'qwen'
  | 'deepseek'
  | 'zhipu'
  | 'baichuan'
  | 'minimax'
  | 'moonshot'
  | 'spark'
  | 'hunyuan'
  | 'local';

// TTS 相关
export interface TTSConfig {
  provider: TTSProvider;
  voiceId: string;
  speed: number;
  pitch: number;
  volume: number;
  emotion?: string;
}

export type TTSProvider = 
  | 'edge-tts'
  | 'azure'
  | 'google'
  | 'openai'
  | 'volcano'
  | 'minimax'
  | 'local';

// ASR 相关
export interface ASRConfig {
  provider: ASRProvider;
  language: string;
  continuous: boolean;
  punctuation: boolean;
}

export type ASRProvider = 
  | 'whisper'
  | 'azure'
  | 'google'
  | 'baidu'
  | 'aliyun'
  | 'local';

// 直播相关
export interface LiveConfig {
  platform: LivePlatform;
  roomId: string;
  autoReply: boolean;
  replyDelay: number;
  giftThanks: boolean;
  danmakuFilter: string[];
}

export type LivePlatform = 
  | 'bilibili'
  | 'douyin'
  | 'kuaishou'
  | 'douyu'
  | 'huya'
  | 'youtube'
  | 'twitch'
  | 'tiktok'
  | 'weixin';

// 设置相关
export interface AppSettings {
  ai: AIConfig;
  tts: TTSConfig;
  asr: ASRConfig;
  live: LiveConfig;
  user: UserPreferences;
}

// 状态相关
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AppState {
  isInitialized: boolean;
  isLoading: boolean;
  error: string | null;
  currentScreen: string;
}

// 事件相关
export interface AppEvent {
  type: string;
  payload: any;
  timestamp: Date;
}

// 导航相关
export type RootStackParamList = {
  Main: undefined;
  Chat: { characterId: string; conversationId?: string };
  CharacterDetail: { characterId: string };
  Settings: undefined;
  SettingsAI: undefined;
  SettingsTTS: undefined;
  SettingsLive: undefined;
  Memory: { characterId: string };
  About: undefined;
};

export type MainTabParamList = {
  Chat: undefined;
  Characters: undefined;
  Live: undefined;
  Memory: undefined;
  Settings: undefined;
};
