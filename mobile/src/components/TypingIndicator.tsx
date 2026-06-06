// ============================================
// GuguGaga AI VTuber Mobile - 打字指示器动画
// 三个点逐个跳动
// ============================================
import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';

interface TypingIndicatorProps {
  characterName?: string;
  visible: boolean;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ characterName = 'AI', visible }) => {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      // 淡入
      Animated.timing(fadeAnim, { toValue: 1, duration: 150, useNativeDriver: true }).start();

      // 点动画循环
      const createDotAnimation = (anim: Animated.Value, delay: number) =>
        Animated.loop(
          Animated.sequence([
            Animated.delay(delay),
            Animated.timing(anim, { toValue: -4, duration: 200, useNativeDriver: true }),
            Animated.timing(anim, { toValue: 0, duration: 200, useNativeDriver: true }),
          ])
        );

      const anim1 = createDotAnimation(dot1, 0);
      const anim2 = createDotAnimation(dot2, 150);
      const anim3 = createDotAnimation(dot3, 300);

      anim1.start();
      anim2.start();
      anim3.start();

      return () => {
        anim1.stop();
        anim2.stop();
        anim3.stop();
      };
    } else {
      Animated.timing(fadeAnim, { toValue: 0, duration: 100, useNativeDriver: true }).start();
    }
  }, [visible]);

  if (!visible) return null;

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>{characterName[0]}</Text>
      </View>
      <View style={styles.bubble}>
        <Animated.View style={[styles.dot, { transform: [{ translateY: dot1 }] }]} />
        <Animated.View style={[styles.dot, { transform: [{ translateY: dot2 }] }]} />
        <Animated.View style={[styles.dot, { transform: [{ translateY: dot3 }] }]} />
      </View>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row', alignItems: 'flex-end', marginHorizontal: 10, marginVertical: 4,
  },
  avatar: {
    width: 28, height: 28, borderRadius: 14, backgroundColor: '#6366f1',
    justifyContent: 'center', alignItems: 'center', marginHorizontal: 5,
  },
  avatarText: { color: '#fff', fontSize: 10, fontWeight: '600' },
  bubble: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: '#f3f4f6', borderRadius: 16, paddingHorizontal: 14, paddingVertical: 10,
  },
  dot: {
    width: 7, height: 7, borderRadius: 3.5, backgroundColor: '#9ca3af',
  },
});
