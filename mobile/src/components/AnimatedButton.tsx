// ============================================
// GuguGaga AI VTuber Mobile - 动画按钮
// 按压缩放 + 触觉反馈
// ============================================
import React, { useRef, useCallback } from 'react';
import { TouchableOpacity, Animated, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';

interface AnimatedButtonProps {
  children: React.ReactNode;
  onPress?: () => void;
  onLongPress?: () => void;
  disabled?: boolean;
  style?: any;
  haptic?: boolean;
  scaleTo?: number;
}

export const AnimatedButton: React.FC<AnimatedButtonProps> = ({
  children, onPress, onLongPress, disabled = false, style, haptic = true, scaleTo = 0.95,
}) => {
  const scaleAnim = useRef(new Animated.Value(1)).current;

  const handlePressIn = useCallback(() => {
    Animated.spring(scaleAnim, {
      toValue: scaleTo,
      tension: 200,
      friction: 10,
      useNativeDriver: true,
    }).start();
  }, [scaleTo]);

  const handlePressOut = useCallback(() => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      tension: 200,
      friction: 10,
      useNativeDriver: true,
    }).start();
  }, []);

  const handlePress = useCallback(() => {
    if (haptic) {
      try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); } catch {}
    }
    onPress?.();
  }, [onPress, haptic]);

  return (
    <TouchableOpacity
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      onPress={handlePress}
      onLongPress={onLongPress}
      disabled={disabled}
      activeOpacity={1}
    >
      <Animated.View style={[style, { transform: [{ scale: scaleAnim }] }]}>
        {children}
      </Animated.View>
    </TouchableOpacity>
  );
};
