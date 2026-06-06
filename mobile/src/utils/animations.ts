// ============================================
// 动画工具库
// ============================================
import { Animated, Easing, Platform } from 'react-native';

// 动画配置
export const ANIMATION_CONFIG = {
  // 时长
  duration: {
    fast: 150,
    normal: 250,
    slow: 350,
    slower: 500,
  },
  
  // 缓动函数
  easing: {
    ease: Easing.ease,
    easeIn: Easing.in(Easing.ease),
    easeOut: Easing.out(Easing.ease),
    easeInOut: Easing.inOut(Easing.ease),
    bounce: Easing.bounce,
    elastic: Easing.elastic(1),
    back: Easing.back(1.5),
  },
  
  // 弹簧配置
  spring: {
    gentle: { tension: 100, friction: 10 },
    bouncy: { tension: 180, friction: 12 },
    stiff: { tension: 200, friction: 15 },
    slow: { tension: 80, friction: 8 },
  },
};

// 淡入动画
export function fadeIn(
  animatedValue: Animated.Value,
  duration: number = ANIMATION_CONFIG.duration.normal,
  toValue: number = 1
): Animated.CompositeAnimation {
  return Animated.timing(animatedValue, {
    toValue,
    duration,
    easing: ANIMATION_CONFIG.easing.easeOut,
    useNativeDriver: true,
  });
}

// 淡出动画
export function fadeOut(
  animatedValue: Animated.Value,
  duration: number = ANIMATION_CONFIG.duration.normal
): Animated.CompositeAnimation {
  return Animated.timing(animatedValue, {
    toValue: 0,
    duration,
    easing: ANIMATION_CONFIG.easing.easeIn,
    useNativeDriver: true,
  });
}

// 从下方滑入
export function slideInUp(
  animatedValue: Animated.Value,
  distance: number = 50,
  duration: number = ANIMATION_CONFIG.duration.normal
): Animated.CompositeAnimation {
  return Animated.timing(animatedValue, {
    toValue: 0,
    duration,
    easing: ANIMATION_CONFIG.easing.easeOut,
    useNativeDriver: true,
  });
}

// 滑出到下方
export function slideOutDown(
  animatedValue: Animated.Value,
  distance: number = 50,
  duration: number = ANIMATION_CONFIG.duration.normal
): Animated.CompositeAnimation {
  return Animated.timing(animatedValue, {
    toValue: distance,
    duration,
    easing: ANIMATION_CONFIG.easing.easeIn,
    useNativeDriver: true,
  });
}

// 缩放动画
export function scale(
  animatedValue: Animated.Value,
  toValue: number = 1,
  duration: number = ANIMATION_CONFIG.duration.fast
): Animated.CompositeAnimation {
  return Animated.timing(animatedValue, {
    toValue,
    duration,
    easing: ANIMATION_CONFIG.easing.easeOut,
    useNativeDriver: true,
  });
}

// 弹簧动画
export function spring(
  animatedValue: Animated.Value,
  toValue: number = 1,
  config: { tension: number; friction: number } = ANIMATION_CONFIG.spring.gentle
): Animated.CompositeAnimation {
  return Animated.spring(animatedValue, {
    toValue,
    ...config,
    useNativeDriver: true,
  });
}

// 脉冲动画
export function pulse(
  animatedValue: Animated.Value,
  minScale: number = 0.95,
  maxScale: number = 1.05,
  duration: number = 1000
): Animated.CompositeAnimation {
  return Animated.loop(
    Animated.sequence([
      Animated.timing(animatedValue, {
        toValue: maxScale,
        duration: duration / 2,
        easing: ANIMATION_CONFIG.easing.easeInOut,
        useNativeDriver: true,
      }),
      Animated.timing(animatedValue, {
        toValue: minScale,
        duration: duration / 2,
        easing: ANIMATION_CONFIG.easing.easeInOut,
        useNativeDriver: true,
      }),
    ])
  );
}

// 摇晃动画
export function shake(
  animatedValue: Animated.Value,
  distance: number = 10,
  duration: number = 500
): Animated.CompositeAnimation {
  return Animated.sequence([
    Animated.timing(animatedValue, {
      toValue: distance,
      duration: duration / 6,
      useNativeDriver: true,
    }),
    Animated.timing(animatedValue, {
      toValue: -distance,
      duration: duration / 3,
      useNativeDriver: true,
    }),
    Animated.timing(animatedValue, {
      toValue: distance / 2,
      duration: duration / 6,
      useNativeDriver: true,
    }),
    Animated.timing(animatedValue, {
      toValue: 0,
      duration: duration / 6,
      useNativeDriver: true,
    }),
  ]);
}

// 旋转动画
export function rotate(
  animatedValue: Animated.Value,
  toValue: number = 1,
  duration: number = ANIMATION_CONFIG.duration.slow
): Animated.CompositeAnimation {
  return Animated.timing(animatedValue, {
    toValue,
    duration,
    easing: ANIMATION_CONFIG.easing.easeInOut,
    useNativeDriver: true,
  });
}

// 连续旋转
export function spin(
  animatedValue: Animated.Value,
  duration: number = 1000
): Animated.CompositeAnimation {
  return Animated.loop(
    Animated.timing(animatedValue, {
      toValue: 1,
      duration,
      easing: Easing.linear,
      useNativeDriver: true,
    })
  );
}

// 组合动画：淡入 + 滑入
export function fadeInSlideIn(
  fadeValue: Animated.Value,
  slideValue: Animated.Value,
  slideDistance: number = 30,
  duration: number = ANIMATION_CONFIG.duration.normal
): Animated.CompositeAnimation {
  return Animated.parallel([
    fadeIn(fadeValue, duration),
    slideInUp(slideValue, slideDistance, duration),
  ]);
}

// 组合动画：淡出 + 滑出
export function fadeOutSlideOut(
  fadeValue: Animated.Value,
  slideValue: Animated.Value,
  slideDistance: number = 30,
  duration: number = ANIMATION_CONFIG.duration.normal
): Animated.CompositeAnimation {
  return Animated.parallel([
    fadeOut(fadeValue, duration),
    slideOutDown(slideValue, slideDistance, duration),
  ]);
}

// 序列动画
export function sequence(
  ...animations: Animated.CompositeAnimation[]
): Animated.CompositeAnimation {
  return Animated.sequence(animations);
}

// 并行动画
export function parallel(
  ...animations: Animated.CompositeAnimation[]
): Animated.CompositeAnimation {
  return Animated.parallel(animations);
}

// 延迟
export function delay(ms: number): Animated.CompositeAnimation {
  return Animated.delay(ms);
}

// 创建动画值
export function createValue(initialValue: number = 0): Animated.Value {
  return new Animated.Value(initialValue);
}

// 创建二维动画值
export function createValueXY(x: number = 0, y: number = 0): Animated.ValueXY {
  return new Animated.ValueXY({ x, y });
}

// 插值
export function interpolate(
  animatedValue: Animated.Value,
  inputRange: number[],
  outputRange: number[] | string[],
  extrapolate: 'clamp' | 'extend' | 'identity' = 'clamp'
): Animated.AnimatedInterpolation<number | string> {
  return animatedValue.interpolate({
    inputRange,
    outputRange,
    extrapolate,
  });
}

// 动画 Hook 辅助
export function useAnimatedValue(initialValue: number = 0): Animated.Value {
  const ref = React.useRef<Animated.Value | null>(null);
  
  if (ref.current === null) {
    ref.current = new Animated.Value(initialValue);
  }
  
  return ref.current;
}

// 导出 React 用于 Hook
import React from 'react';
