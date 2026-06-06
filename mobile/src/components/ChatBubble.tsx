// ============================================
// GuguGaga AI VTuber Mobile - 聊天气泡组件（优化版）
// ============================================
import React, { memo } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { EMOTION_EMOJI } from '../services/emotion';
import { emotionService } from '../services/emotion';
import type { Message } from '../types';

interface ChatBubbleProps {
  message: Message;
  characterName?: string;
  characterAvatar?: string;
}

export const ChatBubble: React.FC<ChatBubbleProps> = memo(({
  message, characterName = 'AI', characterAvatar,
}) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  // 情感分析（仅 AI 回复）
  const emotion = !isUser && !isSystem ? emotionService.analyze(message.content) : null;

  if (isSystem) {
    return (
      <View style={styles.systemContainer}>
        <Text style={styles.systemText}>{message.content}</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, isUser ? styles.userContainer : styles.aiContainer]}>
      {/* AI 头像 */}
      {!isUser && (
        <View style={styles.avatarContainer}>
          <View style={[styles.avatar, styles.defaultAvatar]}>
            <Ionicons name="person" size={18} color="#fff" />
          </View>
        </View>
      )}

      {/* 消息内容 */}
      <View style={[styles.bubble, isUser ? styles.userBubble : styles.aiBubble]}>
        {/* 发送者名称 + 情感 */}
        {!isUser && (
          <View style={styles.senderRow}>
            <Text style={styles.senderName}>{characterName}</Text>
            {emotion && emotion.emotion !== 'neutral' && (
              <Text style={styles.emotionBadge}>
                {EMOTION_EMOJI[emotion.emotion]}
              </Text>
            )}
          </View>
        )}

        {/* 文本内容 */}
        <Text style={[styles.messageText, isUser ? styles.userText : styles.aiText]} selectable>
          {message.content}
        </Text>

        {/* 时间戳 */}
        <Text style={[styles.timestamp, isUser ? styles.userTimestamp : styles.aiTimestamp]}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </View>

      {/* 用户头像 */}
      {isUser && (
        <View style={styles.avatarContainer}>
          <View style={[styles.avatar, styles.userAvatar]}>
            <Ionicons name="person" size={18} color="#6366f1" />
          </View>
        </View>
      )}
    </View>
  );
});

ChatBubble.displayName = 'ChatBubble';

const styles = StyleSheet.create({
  container: { flexDirection: 'row', marginVertical: 3, marginHorizontal: 10, alignItems: 'flex-end' },
  userContainer: { justifyContent: 'flex-end' },
  aiContainer: { justifyContent: 'flex-start' },
  avatarContainer: { marginHorizontal: 6, marginBottom: 2 },
  avatar: { width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  defaultAvatar: { backgroundColor: '#6366f1' },
  userAvatar: { backgroundColor: '#e0e7ff' },
  bubble: { maxWidth: '78%', borderRadius: 18, paddingHorizontal: 14, paddingVertical: 8 },
  userBubble: { backgroundColor: '#6366f1', borderBottomRightRadius: 4 },
  aiBubble: { backgroundColor: '#f3f4f6', borderBottomLeftRadius: 4 },
  senderRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 3, gap: 6 },
  senderName: { fontSize: 11, color: '#6b7280', fontWeight: '600' },
  emotionBadge: { fontSize: 12 },
  messageText: { fontSize: 15, lineHeight: 21 },
  userText: { color: '#ffffff' },
  aiText: { color: '#1f2937' },
  timestamp: { fontSize: 10, marginTop: 3, alignSelf: 'flex-end' },
  userTimestamp: { color: 'rgba(255,255,255,0.6)' },
  aiTimestamp: { color: '#9ca3af' },
  systemContainer: { alignItems: 'center', marginVertical: 6, marginHorizontal: 20 },
  systemText: { fontSize: 12, color: '#9ca3af', backgroundColor: 'rgba(0,0,0,0.04)', paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10, overflow: 'hidden' },
});
