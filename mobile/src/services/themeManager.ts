// ============================================
// 主题管理服务
// ============================================
import { MMKV } from 'react-native-mmkv';
import { useColorScheme } from 'react-native';

const storage = new MMKV({ id: 'theme-manager' });

// 主题类型
export type ThemeMode = 'light' | 'dark' | 'system';

// 主题颜色配置
export interface ThemeColors {
  // 背景
  background: string;
  surface: string;
  surfaceVariant: string;
  
  // 文本
  text: string;
  textSecondary: string;
  textTertiary: string;
  
  // 主色调
  primary: string;
  primaryLight: string;
  primaryDark: string;
  
  // 状态色
  success: string;
  warning: string;
  error: string;
  info: string;
  
  // 边框
  border: string;
  borderLight: string;
  
  // 阴影
  shadow: string;
  
  // 特殊
  card: string;
  input: string;
  tabBar: string;
}

// 浅色主题
export const LIGHT_THEME: ThemeColors = {
  background: '#f8fafc',
  surface: '#ffffff',
  surfaceVariant: '#f1f5f9',
  
  text: '#1e293b',
  textSecondary: '#64748b',
  textTertiary: '#94a3b8',
  
  primary: '#6366f1',
  primaryLight: '#818cf8',
  primaryDark: '#4f46e5',
  
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
  
  border: '#e2e8f0',
  borderLight: '#f1f5f9',
  
  shadow: 'rgba(0, 0, 0, 0.1)',
  
  card: '#ffffff',
  input: '#f1f5f9',
  tabBar: '#ffffff',
};

// 深色主题
export const DARK_THEME: ThemeColors = {
  background: '#0f172a',
  surface: '#1e293b',
  surfaceVariant: '#334155',
  
  text: '#f1f5f9',
  textSecondary: '#94a3b8',
  textTertiary: '#64748b',
  
  primary: '#818cf8',
  primaryLight: '#a5b4fc',
  primaryDark: '#6366f1',
  
  success: '#34d399',
  warning: '#fbbf24',
  error: '#f87171',
  info: '#60a5fa',
  
  border: '#334155',
  borderLight: '#1e293b',
  
  shadow: 'rgba(0, 0, 0, 0.3)',
  
  card: '#1e293b',
  input: '#334155',
  tabBar: '#1e293b',
};

// 主题配置
export interface ThemeConfig {
  mode: ThemeMode;
  colors: ThemeColors;
}

class ThemeManager {
  private static instance: ThemeManager;
  private config: ThemeConfig;
  private listeners: Array<(config: ThemeConfig) => void> = [];
  
  private constructor() {
    this.config = this.loadConfig();
  }
  
  static getInstance(): ThemeManager {
    if (!ThemeManager.instance) {
      ThemeManager.instance = new ThemeManager();
    }
    return ThemeManager.instance;
  }
  
  // 加载配置
  private loadConfig(): ThemeConfig {
    try {
      const saved = storage.getString('theme_config');
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          mode: parsed.mode || 'system',
          colors: parsed.mode === 'dark' ? DARK_THEME : LIGHT_THEME,
        };
      }
    } catch (e) {
      console.error('Load theme config error:', e);
    }
    
    return {
      mode: 'system',
      colors: LIGHT_THEME,
    };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('theme_config', JSON.stringify({
        mode: this.config.mode,
      }));
    } catch (e) {
      console.error('Save theme config error:', e);
    }
  }
  
  // 获取当前主题
  getTheme(): ThemeConfig {
    return { ...this.config };
  }
  
  // 获取主题颜色
  getColors(): ThemeColors {
    return { ...this.config.colors };
  }
  
  // 获取主题模式
  getMode(): ThemeMode {
    return this.config.mode;
  }
  
  // 设置主题模式
  setMode(mode: ThemeMode): void {
    this.config.mode = mode;
    this.updateColors();
    this.saveConfig();
    this.notifyListeners();
  }
  
  // 更新颜色（根据模式）
  private updateColors(): void {
    switch (this.config.mode) {
      case 'light':
        this.config.colors = LIGHT_THEME;
        break;
      case 'dark':
        this.config.colors = DARK_THEME;
        break;
      case 'system':
        // 这里需要获取系统主题
        // 暂时默认浅色
        this.config.colors = LIGHT_THEME;
        break;
    }
  }
  
  // 根据系统主题更新
  updateForSystemTheme(isDark: boolean): void {
    if (this.config.mode === 'system') {
      this.config.colors = isDark ? DARK_THEME : LIGHT_THEME;
      this.notifyListeners();
    }
  }
  
  // 是否深色模式
  isDarkMode(): boolean {
    return this.config.colors === DARK_THEME;
  }
  
  // 注册监听器
  onThemeChange(callback: (config: ThemeConfig) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }
  
  // 通知监听器
  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.config));
  }
  
  // 获取主题样式
  getStyles() {
    const colors = this.config.colors;
    
    return {
      container: {
        backgroundColor: colors.background,
      },
      card: {
        backgroundColor: colors.card,
        shadowColor: colors.shadow,
      },
      text: {
        color: colors.text,
      },
      textSecondary: {
        color: colors.textSecondary,
      },
      input: {
        backgroundColor: colors.input,
        color: colors.text,
      },
      border: {
        borderColor: colors.border,
      },
      primary: {
        backgroundColor: colors.primary,
      },
    };
  }
}

// 单例
export const themeManager = ThemeManager.getInstance();

export default themeManager;
