// ============================================
// 主题 Hook
// ============================================
import { useState, useEffect, useCallback } from 'react';
import { useColorScheme } from 'react-native';
import { themeManager, ThemeConfig, ThemeColors, ThemeMode } from '../services/themeManager';

// 主题 Hook
export function useTheme() {
  const [config, setConfig] = useState<ThemeConfig>(themeManager.getTheme());
  const systemColorScheme = useColorScheme();
  
  // 监听系统主题变化
  useEffect(() => {
    const isDark = systemColorScheme === 'dark';
    themeManager.updateForSystemTheme(isDark);
  }, [systemColorScheme]);
  
  // 监听主题变化
  useEffect(() => {
    const unsubscribe = themeManager.onThemeChange((newConfig) => {
      setConfig({ ...newConfig });
    });
    
    return unsubscribe;
  }, []);
  
  // 设置主题模式
  const setMode = useCallback((mode: ThemeMode) => {
    themeManager.setMode(mode);
  }, []);
  
  // 切换深色模式
  const toggleDarkMode = useCallback(() => {
    const newMode = themeManager.isDarkMode() ? 'light' : 'dark';
    themeManager.setMode(newMode);
  }, []);
  
  return {
    ...config,
    setMode,
    toggleDarkMode,
    isDark: themeManager.isDarkMode(),
  };
}

// 颜色 Hook
export function useColors(): ThemeColors {
  const { colors } = useTheme();
  return colors;
}

// 主题模式 Hook
export function useThemeMode(): [ThemeMode, (mode: ThemeMode) => void] {
  const { mode, setMode } = useTheme();
  return [mode, setMode];
}

// 深色模式 Hook
export function useDarkMode(): [boolean, () => void] {
  const { isDark, toggleDarkMode } = useTheme();
  return [isDark, toggleDarkMode];
}

export default useTheme;
