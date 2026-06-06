/**
 * 记忆状态管理
 */

import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { STORAGE_KEYS } from '../utils/constants';

// 记忆类型
export type MemoryType = 'working' | 'episodic' | 'semantic' | 'fact';

// 记忆条目
export interface MemoryItem {
  id: string;
  type: MemoryType;
  content: string;
  timestamp: number;
  importance: number;
  characterId?: string;
  sessionId?: string;
}

interface MemoryState {
  // 记忆列表
  memories: MemoryItem[];
  // 当前标签
  activeTab: MemoryType;
  // 加载状态
  isLoading: boolean;

  // 操作
  loadMemories: () => Promise<void>;
  addMemory: (memory: Omit<MemoryItem, 'id' | 'timestamp'>) => void;
  deleteMemory: (id: string) => void;
  setActiveTab: (tab: MemoryType) => void;
  getFilteredMemories: () => MemoryItem[];
  getStats: () => Record<MemoryType, number>;
  clearMemories: () => Promise<void>;
}

export const useMemoryStore = create<MemoryState>((set, get) => ({
  memories: [],
  activeTab: 'working',
  isLoading: false,

  // 加载记忆
  loadMemories: async () => {
    try {
      set({ isLoading: true });
      const data = await AsyncStorage.getItem(STORAGE_KEYS.MEMORY_DATA);
      if (data) {
        const memories = JSON.parse(data);
        set({ memories, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      console.error('[MemoryStore] 加载记忆失败:', error);
      set({ isLoading: false });
    }
  },

  // 添加记忆
  addMemory: (memory) => {
    const newMemory: MemoryItem = {
      ...memory,
      id: `memory_${Date.now()}`,
      timestamp: Date.now(),
    };
    set((state) => {
      const updated = [newMemory, ...state.memories];
      AsyncStorage.setItem(STORAGE_KEYS.MEMORY_DATA, JSON.stringify(updated));
      return { memories: updated };
    });
  },

  // 删除记忆
  deleteMemory: (id) => {
    set((state) => {
      const updated = state.memories.filter((m) => m.id !== id);
      AsyncStorage.setItem(STORAGE_KEYS.MEMORY_DATA, JSON.stringify(updated));
      return { memories: updated };
    });
  },

  // 设置当前标签
  setActiveTab: (tab) => set({ activeTab: tab }),

  // 获取过滤后的记忆
  getFilteredMemories: () => {
    const { memories, activeTab } = get();
    return memories
      .filter((m) => m.type === activeTab)
      .sort((a, b) => b.timestamp - a.timestamp);
  },

  // 获取统计信息
  getStats: () => {
    const { memories } = get();
    return {
      working: memories.filter((m) => m.type === 'working').length,
      episodic: memories.filter((m) => m.type === 'episodic').length,
      semantic: memories.filter((m) => m.type === 'semantic').length,
      fact: memories.filter((m) => m.type === 'fact').length,
    };
  },

  // 清空记忆
  clearMemories: async () => {
    set({ memories: [] });
    await AsyncStorage.removeItem(STORAGE_KEYS.MEMORY_DATA);
  },
}));
