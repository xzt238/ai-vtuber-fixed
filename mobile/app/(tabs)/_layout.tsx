// ============================================
// GuguGaga AI VTuber Mobile - Tab 布局（性能优化版）
// 使用 lazy loading + freeze on blur 减少内存
// ============================================
import React, { useMemo } from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Platform, StyleSheet } from 'react-native';

// 图标组件缓存
const ChatIcon = React.memo(({ color, size }: { color: string; size: number }) => (
  <Ionicons name="chatbubbles" size={size} color={color} />
));
const PeopleIcon = React.memo(({ color, size }: { color: string; size: number }) => (
  <Ionicons name="people" size={size} color={color} />
));
const VideoIcon = React.memo(({ color, size }: { color: string; size: number }) => (
  <Ionicons name="videocam" size={size} color={color} />
));
const BrainIcon = React.memo(({ color, size }: { color: string; size: number }) => (
  <Ionicons name="bulb" size={size} color={color} />
));
const SettingsIcon = React.memo(({ color, size }: { color: string; size: number }) => (
  <Ionicons name="settings" size={size} color={color} />
));

export default function TabLayout() {
  // Tab 样式缓存
  const tabScreenOptions = useMemo(() => ({
    headerShown: false,
    tabBarActiveTintColor: '#6366f1',
    tabBarInactiveTintColor: '#9ca3af',
    tabBarStyle: styles.tabBar,
    tabBarLabelStyle: styles.tabLabel,
    // 性能优化：切换时冻结不可见 Tab
    freezeOnBlur: true,
    // 减少 Tab 切换动画时间
    animationEnabled: false,
  }), []);

  return (
    <Tabs screenOptions={tabScreenOptions}>
      <Tabs.Screen
        name="index"
        options={{
          title: '对话',
          tabBarIcon: ChatIcon,
          // 预加载但延迟渲染
          lazy: true,
        }}
      />
      <Tabs.Screen
        name="characters"
        options={{
          title: '角色',
          tabBarIcon: PeopleIcon,
          lazy: true,
        }}
      />
      <Tabs.Screen
        name="live"
        options={{
          title: '直播',
          tabBarIcon: VideoIcon,
          lazy: true,
        }}
      />
      <Tabs.Screen
        name="memory"
        options={{
          title: '记忆',
          tabBarIcon: BrainIcon,
          lazy: true,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: '设置',
          tabBarIcon: SettingsIcon,
          lazy: true,
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    paddingBottom: Platform.OS === 'ios' ? 20 : 8,
    paddingTop: 6,
    height: Platform.OS === 'ios' ? 85 : 60,
    // 性能优化
    elevation: 0,
    shadowOpacity: 0,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '600',
  },
});
