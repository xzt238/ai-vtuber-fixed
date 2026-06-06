// ============================================
// GuguGaga AI VTuber Mobile - 根布局（动画增强版）
// ============================================
import React, { useEffect, useCallback } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAppStore } from '../src/stores';

export default function RootLayout() {
  const { initialize } = useAppStore();

  const init = useCallback(() => { initialize(); }, []);

  useEffect(() => { init(); }, [init]);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          // 转场动画
          animation: 'slide_from_right',
          animationDuration: 200,
          contentStyle: { backgroundColor: '#f8fafc' },
          // 性能优化
          freezeOnBlur: true,
          // 手势
          gestureEnabled: true,
          gestureDirection: 'horizontal',
          fullScreenGestureEnabled: true,
        }}
      >
        {/* Tab 页面 */}
        <Stack.Screen name="(tabs)" options={{ animation: 'fade' }} />
        
        {/* 聊天页面 */}
        <Stack.Screen 
          name="chat" 
          options={{ 
            animation: 'slide_from_bottom',
            animationDuration: 250,
            gestureEnabled: false,
          }} 
        />
        
        {/* 模型选择 */}
        <Stack.Screen 
          name="model-select" 
          options={{ 
            animation: 'slide_from_bottom',
            presentation: 'modal',
          }} 
        />
        
        {/* 角色市场 */}
        <Stack.Screen 
          name="character-market" 
          options={{ animation: 'slide_from_right' }} 
        />
        
        {/* 角色编辑器 */}
        <Stack.Screen 
          name="character-editor" 
          options={{ 
            animation: 'slide_from_bottom',
            presentation: 'modal',
          }} 
        />
        
        {/* 群聊 */}
        <Stack.Screen 
          name="group-chat" 
          options={{ animation: 'slide_from_right' }} 
        />
        
        {/* 语音通话 */}
        <Stack.Screen 
          name="voice-call" 
          options={{ 
            animation: 'fade',
            gestureEnabled: false,
          }} 
        />
        
        {/* 搜索 */}
        <Stack.Screen 
          name="search" 
          options={{ animation: 'slide_from_bottom' }} 
        />
        
        {/* 关于 */}
        <Stack.Screen 
          name="about" 
          options={{ animation: 'slide_from_right' }} 
        />
      </Stack>
    </SafeAreaProvider>
  );
}
