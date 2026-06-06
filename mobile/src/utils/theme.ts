// ============================================
// GuguGaga AI VTuber - 主题配置
// 参考星野/猫箱的精美设计风格
// ============================================

// 颜色系统
export const COLORS = {
  // 主色调
  primary: '#6366f1',
  primaryLight: '#818cf8',
  primaryDark: '#4f46e5',
  
  // 情感色彩
  happy: '#10b981',
  sad: '#6b7280',
  angry: '#ef4444',
  surprised: '#f59e0b',
  love: '#ec4899',
  thinking: '#8b5cf6',
  shy: '#f472b6',
  excited: '#f97316',
  
  // 中性色
  background: '#f8fafc',
  surface: '#ffffff',
  surfaceVariant: '#f1f5f9',
  onSurface: '#1e293b',
  onSurfaceVariant: '#64748b',
  
  // 边框和分割线
  outline: '#e2e8f0',
  outlineVariant: '#cbd5e1',
  
  // 状态色
  success: '#22c55e',
  warning: '#eab308',
  error: '#ef4444',
  info: '#3b82f6',
  
  // 渐变
  gradientPrimary: ['#6366f1', '#8b5cf6'],
  gradientSecondary: ['#ec4899', '#f472b6'],
  gradientWarm: ['#f97316', '#f59e0b'],
  gradientCool: ['#06b6d4', '#3b82f6'],
  
  // 阴影
  shadow: 'rgba(0, 0, 0, 0.1)',
  shadowDark: 'rgba(0, 0, 0, 0.2)',
};

// 字体系统
export const FONTS = {
  // 字体大小
  xs: 10,
  sm: 12,
  md: 14,
  lg: 16,
  xl: 18,
  xxl: 24,
  xxxl: 32,
  display: 48,
  
  // 字体权重
  light: '300' as const,
  regular: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
  
  // 行高
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
};

// 间距系统
export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 48,
};

// 圆角系统
export const BORDER_RADIUS = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  full: 9999,
};

// 阴影系统
export const SHADOWS = {
  sm: {
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.18,
    shadowRadius: 1.0,
    elevation: 1,
  },
  md: {
    shadowColor: COLORS.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
    elevation: 3,
  },
  lg: {
    shadowColor: COLORS.shadowDark,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  xl: {
    shadowColor: COLORS.shadowDark,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.30,
    shadowRadius: 4.65,
    elevation: 8,
  },
};

// 动画配置
export const ANIMATIONS = {
  // 时长
  duration: {
    fast: 150,
    normal: 250,
    slow: 350,
    slower: 500,
  },
  
  // 缓动函数
  easing: {
    // React Native 内置
    ease: 'ease',
    easeIn: 'ease-in',
    easeOut: 'ease-out',
    easeInOut: 'ease-in-out',
  },
  
  // 弹簧动画配置
  spring: {
    gentle: { damping: 15, stiffness: 150 },
    bouncy: { damping: 10, stiffness: 180 },
    stiff: { damping: 20, stiffness: 200 },
  },
};

// 组件样式预设
export const COMPONENT_STYLES = {
  // 卡片
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: BORDER_RADIUS.lg,
    padding: SPACING.lg,
    ...SHADOWS.md,
  },
  
  // 按钮
  button: {
    primary: {
      backgroundColor: COLORS.primary,
      borderRadius: BORDER_RADIUS.md,
      paddingVertical: SPACING.md,
      paddingHorizontal: SPACING.xl,
    },
    secondary: {
      backgroundColor: 'transparent',
      borderRadius: BORDER_RADIUS.md,
      paddingVertical: SPACING.md,
      paddingHorizontal: SPACING.xl,
      borderWidth: 1,
      borderColor: COLORS.primary,
    },
    ghost: {
      backgroundColor: 'transparent',
      borderRadius: BORDER_RADIUS.md,
      paddingVertical: SPACING.md,
      paddingHorizontal: SPACING.xl,
    },
  },
  
  // 输入框
  input: {
    backgroundColor: COLORS.surfaceVariant,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    fontSize: FONTS.md,
    color: COLORS.onSurface,
  },
  
  // 头像
  avatar: {
    small: { width: 32, height: 32, borderRadius: 16 },
    medium: { width: 48, height: 48, borderRadius: 24 },
    large: { width: 64, height: 64, borderRadius: 32 },
    xlarge: { width: 96, height: 96, borderRadius: 48 },
  },
  
  // 分割线
  divider: {
    height: 1,
    backgroundColor: COLORS.outline,
    marginVertical: SPACING.md,
  },
};

// 情感主题
export const EMOTION_THEMES = {
  neutral: {
    primary: COLORS.primary,
    background: COLORS.background,
    accent: COLORS.primaryLight,
  },
  happy: {
    primary: COLORS.happy,
    background: '#f0fdf4',
    accent: '#86efac',
  },
  sad: {
    primary: COLORS.sad,
    background: '#f8fafc',
    accent: '#94a3b8',
  },
  angry: {
    primary: COLORS.angry,
    background: '#fef2f2',
    accent: '#fca5a5',
  },
  surprised: {
    primary: COLORS.surprised,
    background: '#fffbeb',
    accent: '#fcd34d',
  },
  love: {
    primary: COLORS.love,
    background: '#fdf2f8',
    accent: '#f9a8d4',
  },
  thinking: {
    primary: COLORS.thinking,
    background: '#faf5ff',
    accent: '#c4b5fd',
  },
};

// 获取情感颜色
export function getEmotionColor(emotion: string): string {
  const emotionColors: Record<string, string> = {
    neutral: COLORS.primary,
    happy: COLORS.happy,
    sad: COLORS.sad,
    angry: COLORS.angry,
    surprised: COLORS.surprised,
    love: COLORS.love,
    thinking: COLORS.thinking,
    shy: COLORS.shy,
    excited: COLORS.excited,
  };
  return emotionColors[emotion] || COLORS.primary;
}

// 获取情感 Emoji
export function getEmotionEmoji(emotion: string): string {
  const emojis: Record<string, string> = {
    neutral: '😐',
    happy: '😊',
    sad: '😢',
    angry: '😠',
    surprised: '😮',
    love: '🥰',
    thinking: '🤔',
    shy: '😳',
    excited: '🤩',
  };
  return emojis[emotion] || '😐';
}

// 获取情感主题
export function getEmotionTheme(emotion: string) {
  const themes: Record<string, typeof EMOTION_THEMES.neutral> = EMOTION_THEMES;
  return themes[emotion] || EMOTION_THEMES.neutral;
}

export default {
  COLORS,
  FONTS,
  SPACING,
  BORDER_RADIUS,
  SHADOWS,
  ANIMATIONS,
  COMPONENT_STYLES,
  EMOTION_THEMES,
  getEmotionColor,
  getEmotionEmoji,
  getEmotionTheme,
};
