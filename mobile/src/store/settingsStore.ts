/**
 * 设置状态管理
 */

import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { STORAGE_KEYS } from '../utils/constants';
import { ThemeType, LanguageType } from '../types';

interface SettingsState {
  // 主题
  theme: ThemeType;
  // 语言
  language: LanguageType;
  // 通知
  notifications: boolean;
  // 自动同步
  autoSync: boolean;
  // LLM 提供商
  llmProvider: string;
  // LLM API Key
  llmApiKey: string;
  // LLM Base URL
  llmBaseUrl: string;
  // LLM 模型名
  llmModel: string;

  // 操作
  loadSettings: () => Promise<void>;
  setTheme: (theme: ThemeType) => void;
  setLanguage: (language: LanguageType) => void;
  setNotifications: (enabled: boolean) => void;
  setAutoSync: (enabled: boolean) => void;
  setLLMConfig: (config: {
    provider?: string;
    apiKey?: string;
    baseUrl?: string;
    model?: string;
  }) => void;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  theme: 'light',
  language: 'zh-CN',
  notifications: true,
  autoSync: true,
  llmProvider: 'openai',
  llmApiKey: '',
  llmBaseUrl: '',
  llmModel: 'gpt-3.5-turbo',

  // 加载设置
  loadSettings: async () => {
    try {
      const [theme, language, llmConfig] = await Promise.all([
        AsyncStorage.getItem(STORAGE_KEYS.THEME),
        AsyncStorage.getItem(STORAGE_KEYS.LANGUAGE),
        AsyncStorage.getItem(STORAGE_KEYS.CLOUD_LLM_CONFIG),
      ]);

      if (theme) set({ theme: theme as ThemeType });
      if (language) set({ language: language as LanguageType });
      if (llmConfig) {
        const config = JSON.parse(llmConfig);
        set({
          llmProvider: config.provider || 'openai',
          llmApiKey: config.apiKey || '',
          llmBaseUrl: config.baseUrl || '',
          llmModel: config.model || 'gpt-3.5-turbo',
        });
      }
    } catch (error) {
      console.error('[SettingsStore] 加载设置失败:', error);
    }
  },

  // 设置主题
  setTheme: (theme) => {
    set({ theme });
    AsyncStorage.setItem(STORAGE_KEYS.THEME, theme);
  },

  // 设置语言
  setLanguage: (language) => {
    set({ language });
    AsyncStorage.setItem(STORAGE_KEYS.LANGUAGE, language);
  },

  // 设置通知
  setNotifications: (enabled) => {
    set({ notifications: enabled });
  },

  // 设置自动同步
  setAutoSync: (enabled) => {
    set({ autoSync: enabled });
  },

  // 设置 LLM 配置
  setLLMConfig: (config) => {
    set((state) => {
      const newConfig = {
        provider: config.provider ?? state.llmProvider,
        apiKey: config.apiKey ?? state.llmApiKey,
        baseUrl: config.baseUrl ?? state.llmBaseUrl,
        model: config.model ?? state.llmModel,
      };
      AsyncStorage.setItem(STORAGE_KEYS.CLOUD_LLM_CONFIG, JSON.stringify(newConfig));
      return {
        llmProvider: newConfig.provider,
        llmApiKey: newConfig.apiKey,
        llmBaseUrl: newConfig.baseUrl,
        llmModel: newConfig.model,
      };
    });
  },
}));
