// ============================================
// GuguGaga AI VTuber Mobile - 情感徽章
// 显示当前情感状态的动画组件
// ============================================
import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { EMOTION_EMOJI, EMOTION_COLOR } from '../services/emotion';
import type { Emotion } from '../services/emotion';

interface EmotionBadgeProps {
  emotion: Emotion;
  visible: boolean;
}

export const EmotionBadge: React.FC<EmotionBadgeProps> = ({ emotion, visible }) => {
  const scaleAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible && emotion !== 'neutral') {
      Animated.sequence([
        Animated.parallel([
          Animated.spring(scaleAnim, { toValue: 1.2, tension: 100, friction: 5, useNativeDriver: true }),
          Animated.timing(fadeAnim, { toValue: 1, duration: 150, useNativeDriver: true }),
        ]),
        Animated.spring(scaleAnim, { toValue: 1, tension: 100, friction: 8, useNativeDriver: true }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(scaleAnim, { toValue: 0, duration: 100, useNativeDriver: true }),
        Animated.timing(fadeAnim, { toValue: 0, duration: 100, useNativeDriver: true }),
      ]).start();
    }
  }, [emotion, visible]);

  if (!visible || emotion === 'neutral') return null;

  return (
    <Animated.View
      style={[
        styles.container,
        {
          backgroundColor: EMOTION_COLOR[emotion] + '20',
          borderColor: EMOTION_COLOR[emotion] + '40',
          opacity: fadeAnim,
          transform: [{ scale: scaleAnim }],
        },
      ]}
    >
      <Text style={styles.emoji}>{EMOTION_EMOJI[emotion]}</Text>
      <Text style={[styles.label, { color: EMOTION_COLOR[emotion] }]}>
        {emotion === 'happy' ? '开心' :
         emotion === 'sad' ? '伤心' :
         emotion === 'angry' ? '生气' :
         emotion === 'surprised' ? '惊讶' :
         emotion === 'fear' ? '害怕' :
         emotion === 'disgust' ? '厌恶' : ''}
      </Text>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12,
    borderWidth: 1, alignSelf: 'flex-start',
  },
  emoji: { fontSize: 14 },
  label: { fontSize: 12, fontWeight: '600' },
});
