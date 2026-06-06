// ============================================
// 语音通话页面
// ============================================
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  Animated, Dimensions, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { voiceCallService, VoiceCallState } from '../src/services/voiceCall';
import { useCharacterStore } from '../src/stores';
import type { Character } from '../src/types';
import type { Emotion } from '../src/services/emotion';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// 情感颜色
const EMOTION_COLORS: Record<string, string> = {
  neutral: '#6366f1',
  happy: '#10b981',
  sad: '#6b7280',
  angry: '#ef4444',
  surprised: '#f59e0b',
  love: '#ec4899',
  thinking: '#8b5cf6',
  fear: '#f97316',
  disgust: '#84cc16',
};

// 情感 Emoji
const EMOTION_EMOJIS: Record<string, string> = {
  neutral: '😐',
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😮',
  love: '🥰',
  thinking: '🤔',
  fear: '😨',
  disgust: '🤢',
};

export default function VoiceCallPage() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { characters } = useCharacterStore();
  
  const [callState, setCallState] = useState<VoiceCallState>(voiceCallService.getState());
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  
  // 动画值
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const waveAnim = useRef(new Animated.Value(0)).current;
  
  // 监听通话状态
  useEffect(() => {
    const unsubscribe = voiceCallService.onStateChange((state) => {
      setCallState(state);
    });
    
    return unsubscribe;
  }, []);
  
  // 脉冲动画（通话中）
  useEffect(() => {
    if (callState.status === 'connected') {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.1,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      
      return () => pulse.stop();
    }
  }, [callState.status]);
  
  // 波浪动画（说话中）
  useEffect(() => {
    if (callState.isSpeaking) {
      const wave = Animated.loop(
        Animated.timing(waveAnim, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        })
      );
      wave.start();
      
      return () => wave.stop();
    } else {
      waveAnim.setValue(0);
    }
  }, [callState.isSpeaking]);
  
  // 选择角色
  const handleSelectCharacter = useCallback((character: Character) => {
    setSelectedCharacter(character);
  }, []);
  
  // 发起通话
  const handleStartCall = useCallback(async () => {
    if (!selectedCharacter) {
      Alert.alert('提示', '请先选择一个角色');
      return;
    }
    
    const success = await voiceCallService.startCall(selectedCharacter);
    if (!success) {
      Alert.alert('错误', '无法发起通话');
    }
  }, [selectedCharacter]);
  
  // 结束通话
  const handleEndCall = useCallback(async () => {
    Alert.alert(
      '结束通话',
      '确定要结束通话吗？',
      [
        { text: '取消', style: 'cancel' },
        { text: '确定', onPress: () => voiceCallService.endCall() },
      ]
    );
  }, []);
  
  // 模拟用户说话（测试用）
  const handleSimulateSpeech = useCallback(() => {
    const testMessages = [
      '你好呀！',
      '今天天气怎么样？',
      '你喜欢什么？',
      '给我讲个故事吧',
      '再见',
    ];
    const randomMessage = testMessages[Math.floor(Math.random() * testMessages.length)];
    voiceCallService.handleUserSpeech(randomMessage);
  }, []);
  
  // 渲染选择界面
  const renderSelection = () => (
    <View style={styles.selectionContainer}>
      <View style={styles.selectionHeader}>
        <Ionicons name="call" size={64} color="#6366f1" />
        <Text style={styles.selectionTitle}>语音通话</Text>
        <Text style={styles.selectionSubtitle}>
          选择一个角色开始语音聊天
        </Text>
      </View>
      
      {/* 角色列表 */}
      <View style={styles.characterList}>
        {characters.slice(0, 6).map((character) => (
          <TouchableOpacity
            key={character.id}
            style={[
              styles.characterItem,
              selectedCharacter?.id === character.id && styles.characterItemSelected,
            ]}
            onPress={() => handleSelectCharacter(character)}
          >
            <View style={styles.characterAvatar}>
              <Ionicons name="person" size={24} color="#6366f1" />
            </View>
            <Text style={styles.characterName} numberOfLines={1}>
              {character.name}
            </Text>
            {selectedCharacter?.id === character.id && (
              <Ionicons name="checkmark-circle" size={20} color="#10b981" />
            )}
          </TouchableOpacity>
        ))}
      </View>
      
      {/* 拨号按钮 */}
      <TouchableOpacity
        style={[
          styles.callButton,
          !selectedCharacter && styles.callButtonDisabled,
        ]}
        onPress={handleStartCall}
        disabled={!selectedCharacter}
      >
        <Ionicons name="call" size={32} color="#fff" />
        <Text style={styles.callButtonText}>开始通话</Text>
      </TouchableOpacity>
    </View>
  );
  
  // 渲染通话界面
  const renderCall = () => {
    const emotionColor = EMOTION_COLORS[callState.currentEmotion] || '#6366f1';
    const emotionEmoji = EMOTION_EMOJIS[callState.currentEmotion] || '😐';
    
    return (
      <View style={styles.callContainer}>
        {/* 背景 */}
        <View style={[styles.callBackground, { backgroundColor: emotionColor + '20' }]} />
        
        {/* 角色信息 */}
        <View style={styles.callCharacterInfo}>
          <Animated.View
            style={[
              styles.callAvatar,
              { transform: [{ scale: pulseAnim }] },
              callState.isSpeaking && { borderColor: emotionColor },
            ]}
          >
            <Ionicons name="person" size={48} color={emotionColor} />
          </Animated.View>
          
          <Text style={styles.callCharacterName}>
            {callState.character?.name || '未知'}
          </Text>
          
          <Text style={styles.callStatus}>
            {callState.status === 'calling' ? '正在连接...' :
             callState.status === 'connected' ? '通话中' : '已结束'}
          </Text>
          
          {/* 时长 */}
          {callState.status === 'connected' && (
            <Text style={styles.callDuration}>
              {voiceCallService.formatDuration(callState.duration)}
            </Text>
          )}
          
          {/* 情感 */}
          {callState.status === 'connected' && (
            <View style={styles.emotionBadge}>
              <Text style={styles.emotionEmoji}>{emotionEmoji}</Text>
              <Text style={styles.emotionText}>{callState.currentEmotion}</Text>
            </View>
          )}
        </View>
        
        {/* 波浪效果 */}
        {callState.isSpeaking && (
          <View style={styles.waveContainer}>
            {[0, 1, 2].map((i) => (
              <Animated.View
                key={i}
                style={[
                  styles.wave,
                  {
                    backgroundColor: emotionColor,
                    opacity: waveAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [0.3, 0],
                    }),
                    transform: [{
                      scale: waveAnim.interpolate({
                        inputRange: [0, 1],
                        outputRange: [1, 2 + i * 0.5],
                      }),
                    }],
                  },
                ]}
              />
            ))}
          </View>
        )}
        
        {/* 状态指示器 */}
        <View style={styles.statusIndicators}>
          {callState.isListening && (
            <View style={styles.statusItem}>
              <Ionicons name="mic" size={16} color="#10b981" />
              <Text style={styles.statusText}>正在听</Text>
            </View>
          )}
          
          {callState.isSpeaking && (
            <View style={styles.statusItem}>
              <Ionicons name="volume-high" size={16} color={emotionColor} />
              <Text style={[styles.statusText, { color: emotionColor }]}>正在说</Text>
            </View>
          )}
        </View>
        
        {/* 消息预览 */}
        {callState.messages.length > 0 && (
          <View style={styles.messagePreview}>
            <Text style={styles.messagePreviewText} numberOfLines={2}>
              {callState.messages[callState.messages.length - 1].content}
            </Text>
          </View>
        )}
        
        {/* 操作按钮 */}
        <View style={styles.callActions}>
          {/* 模拟说话（测试） */}
          <TouchableOpacity
            style={styles.actionButton}
            onPress={handleSimulateSpeech}
          >
            <Ionicons name="chatbubble" size={24} color="#6366f1" />
            <Text style={styles.actionText}>模拟说话</Text>
          </TouchableOpacity>
          
          {/* 结束通话 */}
          <TouchableOpacity
            style={[styles.actionButton, styles.endCallButton]}
            onPress={handleEndCall}
          >
            <Ionicons name="call" size={24} color="#fff" />
            <Text style={[styles.actionText, styles.endCallText]}>结束</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };
  
  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {callState.status === 'idle' ? renderSelection() : renderCall()}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  
  // 选择界面
  selectionContainer: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  selectionHeader: {
    alignItems: 'center',
    marginBottom: 32,
  },
  selectionTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1e293b',
    marginTop: 16,
  },
  selectionSubtitle: {
    fontSize: 14,
    color: '#64748b',
    marginTop: 8,
  },
  characterList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 32,
  },
  characterItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  characterItemSelected: {
    borderColor: '#6366f1',
    backgroundColor: '#eef2ff',
  },
  characterAvatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#e0e7ff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  characterName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1e293b',
    maxWidth: 80,
  },
  callButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingVertical: 16,
    backgroundColor: '#6366f1',
    borderRadius: 16,
  },
  callButtonDisabled: {
    backgroundColor: '#cbd5e1',
  },
  callButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  
  // 通话界面
  callContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  callBackground: {
    ...StyleSheet.absoluteFillObject,
  },
  callCharacterInfo: {
    alignItems: 'center',
    marginBottom: 48,
  },
  callAvatar: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#6366f1',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
  callCharacterName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1e293b',
    marginTop: 16,
  },
  callStatus: {
    fontSize: 14,
    color: '#64748b',
    marginTop: 4,
  },
  callDuration: {
    fontSize: 32,
    fontWeight: '300',
    color: '#1e293b',
    marginTop: 8,
    fontVariant: ['tabular-nums'],
  },
  emotionBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#fff',
    borderRadius: 20,
    marginTop: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  emotionEmoji: {
    fontSize: 16,
  },
  emotionText: {
    fontSize: 12,
    color: '#64748b',
    textTransform: 'capitalize',
  },
  
  // 波浪效果
  waveContainer: {
    position: 'absolute',
    top: SCREEN_HEIGHT * 0.25,
    alignItems: 'center',
    justifyContent: 'center',
  },
  wave: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: 60,
  },
  
  // 状态指示器
  statusIndicators: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 24,
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#fff',
    borderRadius: 20,
  },
  statusText: {
    fontSize: 12,
    color: '#64748b',
  },
  
  // 消息预览
  messagePreview: {
    width: SCREEN_WIDTH - 48,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    marginBottom: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  messagePreviewText: {
    fontSize: 13,
    color: '#64748b',
    lineHeight: 18,
  },
  
  // 操作按钮
  callActions: {
    flexDirection: 'row',
    gap: 24,
  },
  actionButton: {
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  actionText: {
    fontSize: 12,
    color: '#64748b',
  },
  endCallButton: {
    backgroundColor: '#ef4444',
  },
  endCallText: {
    color: '#fff',
  },
});
