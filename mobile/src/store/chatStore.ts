/**
 * 对话状态管理
 */

import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { STORAGE_KEYS } from '../utils/constants';
import { ChatMessage, ChatSession } from '../types/chat';

interface ChatState {
  // 当前会话
  currentSession: ChatSession | null;
  // 会话列表
  sessions: ChatSession[];
  // 发送中状态
  isSending: boolean;
  // 流式响应
  streamingContent: string;

  // 操作
  loadSessions: () => Promise<void>;
  createSession: (characterId: string) => ChatSession;
  setCurrentSession: (session: ChatSession | null) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (messageId: string, content: string) => void;
  setSending: (sending: boolean) => void;
  setStreamingContent: (content: string) => void;
  clearCurrentSession: () => void;
  getMessages: () => ChatMessage[];
  getHistory: (limit?: number) => ChatMessage[];
}

// 持久化会话数据到 AsyncStorage
const persistSessions = async (sessions: ChatSession[], currentSession: ChatSession | null) => {
  try {
    await AsyncStorage.setItem(STORAGE_KEYS.CHAT_SESSIONS, JSON.stringify({
      sessions,
      currentSessionId: currentSession?.id || null,
    }));
  } catch (error) {
    console.error('[ChatStore] 持久化会话失败:', error);
  }
};

export const useChatStore = create<ChatState>((set, get) => ({
  currentSession: null,
  sessions: [],
  isSending: false,
  streamingContent: '',

  // 从 AsyncStorage 加载会话
  loadSessions: async () => {
    try {
      const data = await AsyncStorage.getItem(STORAGE_KEYS.CHAT_SESSIONS);
      if (data) {
        const { sessions, currentSessionId } = JSON.parse(data);
        const currentSession = sessions.find((s: ChatSession) => s.id === currentSessionId) || null;
        set({ sessions: sessions || [], currentSession });
        console.log(`[ChatStore] 加载了 ${(sessions || []).length} 个会话`);
      }
    } catch (error) {
      console.error('[ChatStore] 加载会话失败:', error);
    }
  },

  // 创建新会话
  createSession: (characterId: string) => {
    const session: ChatSession = {
      id: `session_${Date.now()}`,
      characterId,
      title: '新对话',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    set((state) => {
      const updated = {
        sessions: [...state.sessions, session],
        currentSession: session,
      };
      persistSessions(updated.sessions, updated.currentSession);
      return updated;
    });
    return session;
  },

  // 设置当前会话
  setCurrentSession: (session) => {
    set((state) => {
      persistSessions(state.sessions, session);
      return { currentSession: session };
    });
  },

  // 添加消息
  addMessage: (message) => {
    set((state) => {
      if (!state.currentSession) return state;

      const updatedSession = {
        ...state.currentSession,
        messages: [...state.currentSession.messages, message],
        updatedAt: Date.now(),
      };

      const updatedSessions = state.sessions.map((s) =>
        s.id === updatedSession.id ? updatedSession : s
      );

      persistSessions(updatedSessions, updatedSession);

      return {
        currentSession: updatedSession,
        sessions: updatedSessions,
      };
    });
  },

  // 更新消息内容（用于流式响应）
  updateMessage: (messageId, content) => {
    set((state) => {
      if (!state.currentSession) return state;

      const updatedMessages = state.currentSession.messages.map((m) =>
        m.id === messageId ? { ...m, content } : m
      );

      const updatedSession = {
        ...state.currentSession,
        messages: updatedMessages,
        updatedAt: Date.now(),
      };

      const updatedSessions = state.sessions.map((s) =>
        s.id === updatedSession.id ? updatedSession : s
      );

      persistSessions(updatedSessions, updatedSession);

      return {
        currentSession: updatedSession,
        sessions: updatedSessions,
      };
    });
  },

  // 设置发送状态
  setSending: (sending) => set({ isSending: sending }),

  // 设置流式内容
  setStreamingContent: (content) => set({ streamingContent: content }),

  // 清空当前会话
  clearCurrentSession: () => {
    set((state) => {
      if (!state.currentSession) return state;
      const updatedSession = {
        ...state.currentSession,
        messages: [],
        updatedAt: Date.now(),
      };
      const updatedSessions = state.sessions.map((s) =>
        s.id === updatedSession.id ? updatedSession : s
      );
      persistSessions(updatedSessions, updatedSession);
      return {
        currentSession: updatedSession,
        sessions: updatedSessions,
      };
    });
  },

  // 获取当前消息
  getMessages: () => {
    return get().currentSession?.messages || [];
  },

  // 获取历史消息（最近 N 条）
  getHistory: (limit = 20) => {
    const messages = get().currentSession?.messages || [];
    return messages.slice(-limit);
  },
}));
