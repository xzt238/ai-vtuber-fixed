// ============================================
// GuguGaga AI VTuber Mobile - 淡入动画容器
// 通用的入场动画包装器
// ============================================
import React, { useEffect, useRef } from 'react';
import { View, Animated, StyleSheet } from 'react-native';

interface FadeInViewProps {
  children: React.ReactNode;
  duration?: number;
  delay?: number;
  direction?: 'up' | 'down' | 'none';
  distance?: number;
  style?: any;
}

export const FadeInView: React.FC<FadeInViewProps> = ({
  children, duration = 200, delay = 0, direction = 'up', distance = 10, style,
}) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(direction === 'up' ? distance : direction === 'down' ? -distance : 0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration, delay, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration, delay, useNativeDriver: true }),
    ]).start();
  }, []);

  return (
    <Animated.View
      style={[
        style,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      {children}
    </Animated.View>
  );
};

// 列表项动画包装器
export const FadeInListItem: React.FC<{ children: React.ReactNode; index: number; style?: any }> = ({
  children, index, style,
}) => (
  <FadeInView delay={index * 50} duration={200} direction="up" distance={8} style={style}>
    {children}
  </FadeInView>
);
