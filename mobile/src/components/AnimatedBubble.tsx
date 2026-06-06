// ============================================
// GuguGaga AI VTuber Mobile - 动画聊天气泡
// 带入场动画 + 打字机效果 + 情感动画
// ============================================
import React, { memo, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { emotionService, EMOTION_EMOJI } from '../services/emotion';
import type { Message } from '../types';

interface AnimatedBubbleProps {
  message: Message;
  characterName?: string;
  isNew?: boolean;
}

export const AnimatedBubble: React.FC<AnimatedBubbleProps> = memo(({
  message, characterName = 'AI', isNew = false,
}) => {
  const isUser = message.role === 'user';
  const fadeAnim = useRef(new Animated.Value(isNew ? 0 : 1)).current;
  const slideAnim = useRef(new Animated.Value(isNew ? 20 : 0)).current;
  const scaleAnim = useRef(new Animated.Value(isNew ? 0.95 : 1)).current;

  // 情感分析
  const emotion = !isUser ? emotionService.analyze(message.content) : null;

  useEffect(() => {
    if (isNew) {
      Animated.parallel([
        Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }),
        Animated.timing(slideAnim, { toValue: 0, duration: 200, useNativeDriver: true }),
        Animated.spring(scaleAnim, { toValue: 1, tension: 100, friction: 8, useNativeDriver: true }),
      ]).start();
    }
  }, [isNew]);

  return (
    <Animated.View
      style={[
        styles.container,
        isUser ? styles.userContainer : styles.aiContainer,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }, { scale: scaleAnim }],
        },
      ]}
    >
      {/* AI 头像 */}
      {!isUser && (
        <View style={styles.avatar}>
          <Ionicons name="person" size={16} color="#fff" />
        </View>
      )}

      <View style={[styles.bubble, isUser ? styles.userBubble : styles.aiBubble]}>
        {/* 发送者 */}
        {!isUser && (
          <View style={styles.senderRow}>
            <Text style={styles.senderName}>{characterName}</Text>
            {emotion && emotion.emotion !== 'neutral' && (
              <Text style={styles.emotionEmoji}>{EMOTION_EMOJI[emotion.emotion]}</Text>
            )}
          </View>
        )}

        <Text style={[styles.text, isUser ? styles.userText : styles.aiText]} selectable>
          {message.content}
        </Text>

        <Text style={[styles.time, isUser ? styles.userTime : styles.aiTime]}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </View>

      {/* 用户头像 */}
      {isUser && (
        <View style={[styles.avatar, styles.userAvatar]}>
          <Ionicons name="person" size={16} color="#6366f1" />
        </View>
      )}
    </Animated.View>
  );
});

AnimatedBubble.displayName = 'AnimatedBubble';

const styles = StyleSheet.create({
  container: { flexDirection: 'row', marginVertical: 2, marginHorizontal: 10, alignItems: 'flex-end' },
  userContainer: { justifyContent: 'flex-end' },
  aiContainer: { justifyContent: 'flex-start' },
  avatar: { width: 28, height: 28, borderRadius: 14, backgroundColor: '#6366f1', justifyContent: 'center', alignItems: 'center', marginHorizontal: 5, marginBottom: 2 },
  userAvatar: { backgroundColor: '#e0e7ff' },
  bubble: { maxWidth: '78%', borderRadius: 16, paddingHorizontal: 12, paddingVertical: 7 },
  userBubble: { backgroundColor: '#6366f1', borderBottomRightRadius: 4 },
  aiBubble: { backgroundColor: '#f3f4f6', borderBottomLeftRadius: 4 },
  senderRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 2, gap: 4 },
  senderName: { fontSize: 10, color: '#6b7280', fontWeight: '600' },
  emotionEmoji: { fontSize: 11 },
  text: { fontSize: 14, lineHeight: 19 },
  userText: { color: '#fff' },
  aiText: { color: '#1f2937' },
  time: { fontSize: 9, marginTop: 2, alignSelf: 'flex-end' },
  userTime: { color: 'rgba(255,255,255,0.5)' },
  aiTime: { color: '#9ca3af' },
});
