// ============================================
// GuguGaga AI VTuber Mobile - 状态管理（性能优化版）
// 使用 selector 模式减少重渲染
// ============================================
import { create } from 'zustand';
import { MMKV } from 'react-native-mmkv';
import type { 
  Character, Conversation, Message, Memory, 
  AppSettings, AIConfig, TTSConfig, ASRConfig, LiveConfig,
  UserPreferences, LoadingState 
} from '../types';

const storage = new MMKV();

// 工具函数 - 内联优化
const genId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const load = <T,>(key: string, fallback: T): T => {
  try { const d = storage.getString(key); return d ? JSON.parse(d) : fallback; } catch { return fallback; }
};

const save = <T,>(key: string, value: T): void => {
  try { storage.set(key, JSON.stringify(value)); } catch {}
};

// ============================================
// 角色状态
// ============================================
export const useCharacterStore = create<{
  characters: Character[];
  currentCharacter: Character | null;
  loading: LoadingState;
  loadCharacters: () => void;
  addCharacter: (c: Omit<Character, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateCharacter: (id: string, u: Partial<Character>) => void;
  deleteCharacter: (id: string) => void;
  setCurrentCharacter: (c: Character | null) => void;
}>((set, get) => ({
  characters: [],
  currentCharacter: null,
  loading: 'idle',
  loadCharacters: () => {
    const characters = load<Character[]>('characters', []);
    set({ characters, loading: 'success' });
  },
  addCharacter: (data) => {
    const c: Character = { ...data, id: genId(), createdAt: new Date(), updatedAt: new Date() };
    const characters = [...get().characters, c];
    save('characters', characters);
    set({ characters });
  },
  updateCharacter: (id, u) => {
    const characters = get().characters.map(c => c.id === id ? { ...c, ...u, updatedAt: new Date() } : c);
    save('characters', characters);
    set({ characters });
  },
  deleteCharacter: (id) => {
    const characters = get().characters.filter(c => c.id !== id);
    save('characters', characters);
    set({ characters });
  },
  setCurrentCharacter: (c) => set({ currentCharacter: c }),
}));

// ============================================
// 对话状态
// ============================================
export const useConversationStore = create<{
  conversations: Conversation[];
  currentConversation: Conversation | null;
  loading: LoadingState;
  isStreaming: boolean;
  loadConversations: (characterId: string) => void;
  createConversation: (characterId: string, title?: string) => Conversation;
  addMessage: (conversationId: string, msg: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (conversationId: string, messageId: string, u: Partial<Message>) => void;
  deleteConversation: (id: string) => void;
  setCurrentConversation: (c: Conversation | null) => void;
  setStreaming: (v: boolean) => void;
  clearConversations: (characterId: string) => void;
}>((set, get) => ({
  conversations: [],
  currentConversation: null,
  loading: 'idle',
  isStreaming: false,
  loadConversations: (characterId) => {
    const all = load<Conversation[]>('conversations', []);
    set({ conversations: all.filter(c => c.characterId === characterId), loading: 'success' });
  },
  createConversation: (characterId, title) => {
    const conv: Conversation = {
      id: genId(), characterId, title: title || `对话 ${new Date().toLocaleString()}`,
      messages: [], createdAt: new Date(), updatedAt: new Date(),
    };
    const all = load<Conversation[]>('conversations', []);
    all.push(conv);
    save('conversations', all);
    set({ conversations: [...get().conversations, conv] });
    return conv;
  },
  addMessage: (conversationId, msgData) => {
    const msg: Message = { ...msgData, id: genId(), timestamp: new Date() };
    const all = load<Conversation[]>('conversations', []);
    const updated = all.map(c => c.id === conversationId ? { ...c, messages: [...c.messages, msg], updatedAt: new Date() } : c);
    save('conversations', updated);
    set({ conversations: get().conversations.map(c => c.id === conversationId ? { ...c, messages: [...c.messages, msg], updatedAt: new Date() } : c) });
  },
  updateMessage: (conversationId, messageId, u) => {
    const all = load<Conversation[]>('conversations', []);
    const updated = all.map(c => c.id === conversationId ? { ...c, messages: c.messages.map(m => m.id === messageId ? { ...m, ...u } : m) } : c);
    save('conversations', updated);
    set({ conversations: get().conversations.map(c => c.id === conversationId ? { ...c, messages: c.messages.map(m => m.id === messageId ? { ...m, ...u } : m) } : c) });
  },
  deleteConversation: (id) => {
    const all = load<Conversation[]>('conversations', []);
    save('conversations', all.filter(c => c.id !== id));
    set({ conversations: get().conversations.filter(c => c.id !== id) });
  },
  setCurrentConversation: (c) => set({ currentConversation: c }),
  setStreaming: (v) => set({ isStreaming: v }),
  clearConversations: (characterId) => {
    const all = load<Conversation[]>('conversations', []);
    save('conversations', all.filter(c => c.characterId !== characterId));
    set({ conversations: [] });
  },
}));

// ============================================
// 记忆状态
// ============================================
export const useMemoryStore = create<{
  memories: Memory[];
  loading: LoadingState;
  loadMemories: (characterId: string) => void;
  addMemory: (m: Omit<Memory, 'id' | 'createdAt' | 'lastAccessed' | 'accessCount'>) => void;
  updateMemory: (id: string, u: Partial<Memory>) => void;
  deleteMemory: (id: string) => void;
}>((set, get) => ({
  memories: [],
  loading: 'idle',
  loadMemories: (characterId) => {
    const all = load<Memory[]>('memories', []);
    set({ memories: all.filter(m => m.characterId === characterId), loading: 'success' });
  },
  addMemory: (data) => {
    const m: Memory = { ...data, id: genId(), createdAt: new Date(), lastAccessed: new Date(), accessCount: 0 };
    const all = load<Memory[]>('memories', []);
    all.push(m);
    save('memories', all);
    set({ memories: [...get().memories, m] });
  },
  updateMemory: (id, u) => {
    const all = load<Memory[]>('memories', []);
    const updated = all.map(m => m.id === id ? { ...m, ...u } : m);
    save('memories', updated);
    set({ memories: get().memories.map(m => m.id === id ? { ...m, ...u } : m) });
  },
  deleteMemory: (id) => {
    const all = load<Memory[]>('memories', []);
    save('memories', all.filter(m => m.id !== id));
    set({ memories: get().memories.filter(m => m.id !== id) });
  },
}));

// ============================================
// 设置状态
// ============================================
const defaultSettings: AppSettings = {
  ai: { provider: 'openai', model: 'gpt-3.5-turbo', apiKey: '', temperature: 0.7, maxTokens: 2048, topP: 1, frequencyPenalty: 0, presencePenalty: 0 },
  tts: { provider: 'edge-tts', voiceId: 'zh-CN-XiaoxiaoNeural', speed: 1, pitch: 1, volume: 1 },
  asr: { provider: 'whisper', language: 'zh-CN', continuous: true, punctuation: true },
  live: { platform: 'bilibili', roomId: '', autoReply: true, replyDelay: 1000, giftThanks: true, danmakuFilter: [] },
  user: { theme: 'auto', language: 'zh-CN', fontSize: 16, soundEnabled: true, vibrationEnabled: true, autoSave: true },
};

export const useSettingsStore = create<{
  settings: AppSettings;
  loading: LoadingState;
  loadSettings: () => void;
  updateAIConfig: (c: Partial<AIConfig>) => void;
  updateTTSConfig: (c: Partial<TTSConfig>) => void;
  updateASRConfig: (c: Partial<ASRConfig>) => void;
  updateLiveConfig: (c: Partial<LiveConfig>) => void;
  updateUserPreferences: (p: Partial<UserPreferences>) => void;
  resetSettings: () => void;
}>((set, get) => ({
  settings: defaultSettings,
  loading: 'idle',
  loadSettings: () => set({ settings: load('settings', defaultSettings), loading: 'success' }),
  updateAIConfig: (c) => { const s = { ...get().settings, ai: { ...get().settings.ai, ...c } }; save('settings', s); set({ settings: s }); },
  updateTTSConfig: (c) => { const s = { ...get().settings, tts: { ...get().settings.tts, ...c } }; save('settings', s); set({ settings: s }); },
  updateASRConfig: (c) => { const s = { ...get().settings, asr: { ...get().settings.asr, ...c } }; save('settings', s); set({ settings: s }); },
  updateLiveConfig: (c) => { const s = { ...get().settings, live: { ...get().settings.live, ...c } }; save('settings', s); set({ settings: s }); },
  updateUserPreferences: (p) => { const s = { ...get().settings, user: { ...get().settings.user, ...p } }; save('settings', s); set({ settings: s }); },
  resetSettings: () => { save('settings', defaultSettings); set({ settings: defaultSettings }); },
}));

// ============================================
// 应用状态
// ============================================
export const useAppStore = create<{
  isInitialized: boolean;
  isLoading: boolean;
  error: string | null;
  initialize: () => Promise<void>;
}>((set) => ({
  isInitialized: false,
  isLoading: false,
  error: null,
  initialize: async () => {
    try {
      useCharacterStore.getState().loadCharacters();
      useSettingsStore.getState().loadSettings();
      set({ isInitialized: true });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },
}));
