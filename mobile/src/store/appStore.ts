/**
 * 应用状态管理
 *
 * 使用Zustand管理全局状态
 */

import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { STORAGE_KEYS, API_CONFIG } from '../utils/constants';
import { apiClient } from '../services/api/apiClient';
import { useCharacterStore } from './characterStore';
import { useSettingsStore } from './settingsStore';
import { localAI } from '../services/localAI';
import { useChatStore } from './chatStore';

interface AppState {
  // 初始化状态
  isInitialized: boolean;
  isLoading: boolean;

  // 引导状态
  onboardingCompleted: boolean;

  // 连接状态
  isConnected: boolean;
  serverUrl: string;

  // 用户信息
  deviceId: string | null;
  userId: string | null;

  // 操作
  initialize: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
  setServerUrl: (url: string) => Promise<void>;
  checkConnection: () => Promise<boolean>;
  logout: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  // 初始状态
  isInitialized: false,
  isLoading: false,
  onboardingCompleted: false,
  isConnected: false,
  serverUrl: API_CONFIG.BASE_URL,
  deviceId: null,
  userId: null,

  // 初始化应用
  initialize: async () => {
    try {
      set({ isLoading: true });

      // 并行加载存储数据
      const [serverUrl, deviceId, onboardingCompleted] = await Promise.all([
        AsyncStorage.getItem(STORAGE_KEYS.SERVER_URL),
        AsyncStorage.getItem(STORAGE_KEYS.DEVICE_ID),
        AsyncStorage.getItem(STORAGE_KEYS.ONBOARDING_COMPLETED),
      ]);

      if (serverUrl) {
        set({ serverUrl });
        await apiClient.setServerUrl(serverUrl);
      }

      if (deviceId) {
        set({ deviceId });
        apiClient.setDeviceId(deviceId);
      }

      // 加载其他 store + 初始化本地 AI
      await Promise.all([
        useCharacterStore.getState().loadCharacters(),
        useSettingsStore.getState().loadSettings(),
        useChatStore.getState().loadSessions(),
        localAI.initialize(),
      ]);

      // 检查连接
      const isConnected = await get().checkConnection();

      set({
        isConnected,
        isInitialized: true,
        isLoading: false,
        onboardingCompleted: onboardingCompleted === 'true',
      });

      console.log('[App] 初始化完成');
    } catch (error) {
      console.error('[App] 初始化失败:', error);
      set({ isLoading: false });
    }
  },

  // 完成引导
  completeOnboarding: async () => {
    await AsyncStorage.setItem(STORAGE_KEYS.ONBOARDING_COMPLETED, 'true');
    set({ onboardingCompleted: true });
  },

  // 设置服务器地址
  setServerUrl: async (url: string) => {
    try {
      set({ serverUrl: url });
      await apiClient.setServerUrl(url);
      await AsyncStorage.setItem(STORAGE_KEYS.SERVER_URL, url);

      // 检查新连接
      const isConnected = await get().checkConnection();
      set({ isConnected });
    } catch (error) {
      console.error('[App] 设置服务器地址失败:', error);
    }
  },

  // 检查连接
  checkConnection: async () => {
    try {
      const isConnected = await apiClient.checkConnection();
      set({ isConnected });
      return isConnected;
    } catch {
      set({ isConnected: false });
      return false;
    }
  },

  // 登出
  logout: async () => {
    try {
      await AsyncStorage.multiRemove([
        STORAGE_KEYS.DEVICE_ID,
        STORAGE_KEYS.USER_ID,
      ]);
      set({
        deviceId: null,
        userId: null,
        isConnected: false,
      });
    } catch (error) {
      console.error('[App] 登出失败:', error);
    }
  },
}));
