/**
 * 咕咕嘎嘎 AI VTuber 移动端应用
 *
 * 主要功能：
 * - 与AI进行文字对话
 * - 云端 LLM 对接
 * - 基础角色系统
 * - 基础记忆系统
 * - 服务器配置
 */

import React, { useEffect, useState } from 'react';
import { StatusBar, LogBox, View, ActivityIndicator, Text } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import AppNavigator from './navigation/AppNavigator';
import { useAppStore } from './store/appStore';
import { COLORS } from './utils/constants';

// 忽略特定警告
LogBox.ignoreLogs([
  'Non-serializable values were found in the navigation state',
]);

const App: React.FC = () => {
  const { initialize, isInitialized, isLoading, onboardingCompleted, completeOnboarding } =
    useAppStore();

  useEffect(() => {
    const initApp = async () => {
      try {
        await initialize();
        console.log('[App] 应用初始化完成');
      } catch (error) {
        console.error('[App] 初始化失败:', error);
      }
    };

    initApp();
  }, []);

  // 完成引导回调
  const handleCompleteOnboarding = async () => {
    await completeOnboarding();
  };

  // 加载中状态
  if (isLoading || !isInitialized) {
    return (
      <GestureHandlerRootView style={{ flex: 1 }}>
        <SafeAreaProvider>
          <View
            style={{
              flex: 1,
              justifyContent: 'center',
              alignItems: 'center',
              backgroundColor: COLORS.white,
            }}
          >
            <ActivityIndicator size="large" color={COLORS.primary} />
            <Text style={{ marginTop: 16, fontSize: 16, color: COLORS.textSecondary }}>
              正在初始化...
            </Text>
          </View>
        </SafeAreaProvider>
      </GestureHandlerRootView>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar
          barStyle="dark-content"
          backgroundColor="#FFFFFF"
          translucent={false}
        />
        <NavigationContainer>
          <AppNavigator
            onboardingCompleted={onboardingCompleted}
            onCompleteOnboarding={handleCompleteOnboarding}
          />
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
};

export default App;
