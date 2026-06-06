// ============================================
// 主题 Provider 组件
// ============================================
import React, { createContext, useContext, ReactNode } from 'react';
import { useTheme, useColors, useThemeMode, useDarkMode } from '../hooks/useTheme';
import { ThemeConfig, ThemeColors, ThemeMode } from '../services/themeManager';

// 主题上下文类型
interface ThemeContextType {
  config: ThemeConfig;
  colors: ThemeColors;
  mode: ThemeMode;
  isDark: boolean;
  setMode: (mode: ThemeMode) => void;
  toggleDarkMode: () => void;
}

// 创建上下文
const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Provider Props
interface ThemeProviderProps {
  children: ReactNode;
}

// Provider 组件
export function ThemeProvider({ children }: ThemeProviderProps) {
  const theme = useTheme();
  
  const value: ThemeContextType = {
    config: theme,
    colors: theme.colors,
    mode: theme.mode,
    isDark: theme.isDark,
    setMode: theme.setMode,
    toggleDarkMode: theme.toggleDarkMode,
  };
  
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

// 使用主题的 Hook
export function useThemeContext(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeContext must be used within a ThemeProvider');
  }
  return context;
}

// 导出
export default ThemeProvider;
