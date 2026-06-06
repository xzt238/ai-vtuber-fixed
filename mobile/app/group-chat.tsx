// ============================================
// 多角色群聊页面
// ============================================
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, FlatList, TextInput,
  TouchableOpacity, Image, KeyboardAvoidingView, Platform,
  Alert, Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter, Stack } from 'expo-router';
import { groupChatService, GroupMessage, PRESET_SCENARIOS } from '../src/services/groupChat';
import { useCharacterStore } from '../src/stores';
import type { Character } from '../src/types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// 头像组件
const Avatar = React.memo(({ uri, size = 36, isTyping }: { uri: string; size?: number; isTyping?: boolean }) => (
  <View style={[styles.avatarContainer, { width: size, height: size }]}>
    <Image source={{ uri }} style={[styles.avatar, { width: size, height: size, borderRadius: size / 2 }]} />
    {isTyping && (
      <View style={styles.typingIndicator}>
        <View style={styles.typingDot} />
        <View style={[styles.typingDot, styles.typingDotDelay1]} />
        <View style={[styles.typingDot, styles.typingDotDelay2]} />
      </View>
    )}
  </View>
));

// 消息气泡组件
const MessageBubble = React.memo(({ message, isOwn }: { message: GroupMessage; isOwn: boolean }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  
  if (isSystem) {
    return (
      <View style={styles.systemMessage}>
        <Text style={styles.systemMessageText}>{message.content}</Text>
      </View>
    );
  }
  
  return (
    <View style={[styles.messageRow, isUser && styles.messageRowOwn]}>
      {/* AI 头像 */}
      {!isUser && (
        <Avatar uri={message.characterAvatar || 'https://img.icons8.com/color/96/user-male-circle.png'} />
      )}
      
      <View style={[styles.messageBubble, isUser && styles.messageBubbleOwn]}>
        {/* 角色名称 */}
        {!isUser && message.characterName && (
          <Text style={styles.characterName}>{message.characterName}</Text>
        )}
        
        {/* 消息内容 */}
        <Text style={[styles.messageText, isUser && styles.messageTextOwn]}>
          {message.content}
        </Text>
        
        {/* 时间 */}
        <Text style={[styles.messageTime, isUser && styles.messageTimeOwn]}>
          {formatTime(message.timestamp)}
        </Text>
      </View>
      
      {/* 用户头像 */}
      {isUser && (
        <Avatar uri="https://img.icons8.com/color/96/user-male-circle.png" />
      )}
    </View>
  );
});

// 格式化时间
function formatTime(date: Date): string {
  const d = new Date(date);
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

// 场景选择卡片
const ScenarioCard = React.memo(({ scenario, onPress }: { 
  scenario: typeof PRESET_SCENARIOS[0]; 
  onPress: () => void;
}) => (
  <TouchableOpacity style={styles.scenarioCard} onPress={onPress} activeOpacity={0.7}>
    <View style={styles.scenarioIcon}>
      <Ionicons name="people" size={24} color="#6366f1" />
    </View>
    <Text style={styles.scenarioName}>{scenario.name}</Text>
    <Text style={styles.scenarioDesc} numberOfLines={2}>{scenario.description}</Text>
    <Text style={styles.scenarioCount}>{scenario.characterIds.length} 个角色</Text>
  </TouchableOpacity>
));

export default function GroupChatPage() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { characters } = useCharacterStore();
  
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<GroupMessage[]>([]);
  const [activeCharacters, setActiveCharacters] = useState<Character[]>([]);
  const [typingCharacters, setTypingCharacters] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showScenarios, setShowScenarios] = useState(true);
  
  const flatListRef = useRef<FlatList>(null);
  const isMounted = useRef(true);
  
  // 初始化
  useEffect(() => {
    return () => { isMounted.current = false; };
  }, []);
  
  // 监听群聊状态更新
  useEffect(() => {
    const unsubscribe = groupChatService.onUpdate((state) => {
      if (!isMounted.current) return;
      
      setMessages([...state.messages]);
      setActiveCharacters([...state.activeCharacters]);
      setTypingCharacters([...state.typingCharacters]);
      setIsGenerating(state.isGenerating);
    });
    
    // 加载现有群聊
    const currentChat = groupChatService.getCurrentChat();
    if (currentChat) {
      setMessages([...currentChat.messages]);
      setActiveCharacters([...currentChat.activeCharacters]);
      setTypingCharacters([...currentChat.typingCharacters]);
      setIsGenerating(currentChat.isGenerating);
      setShowScenarios(false);
    }
    
    return unsubscribe;
  }, []);
  
  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => flatListRef.current?.scrollToEnd({ animated: true }));
  }, []);
  
  // 消息变化时滚动
  useEffect(() => {
    scrollToBottom();
  }, [messages, typingCharacters]);
  
  // 开始群聊场景
  const handleStartScenario = useCallback((scenarioId: string) => {
    // 尝试加载预设场景
    let config = groupChatService.loadScenario(scenarioId, characters);
    
    // 如果预设场景没有找到，尝试加载自定义场景
    if (!config) {
      config = groupChatService.loadCustomScenario(scenarioId, characters);
    }
    
    if (config) {
      setShowScenarios(false);
    } else {
      Alert.alert('错误', '无法加载场景，请确保有足够的角色');
    }
  }, [characters]);
  
  // 创建自定义场景
  const handleCreateCustomScenario = useCallback(() => {
    if (characters.length < 2) {
      Alert.alert('提示', '至少需要 2 个角色才能创建群聊');
      return;
    }
    
    // 简化版：使用前 2-3 个角色
    const selectedCharacters = characters.slice(0, Math.min(3, characters.length));
    
    Alert.prompt(
      '创建群聊',
      '输入群聊名称',
      (name) => {
        if (!name) return;
        
        Alert.prompt(
          '群聊描述',
          '输入群聊描述（可选）',
          (description) => {
            const scenario = groupChatService.createCustomScenario({
              name,
              description: description || '',
              characterIds: selectedCharacters.map(c => c.id),
              systemPrompt: `你们正在进行一场名为"${name}"的群聊。请保持各自的性格特点，友好互动。`,
            });
            
            // 加载新创建的场景
            handleStartScenario(scenario.id);
          }
        );
      },
      'plain-text',
      '我的群聊'
    );
  }, [characters, handleStartScenario]);
  
  // 发送消息
  const handleSend = useCallback(async () => {
    if (!inputText.trim()) return;
    
    const text = inputText.trim();
    setInputText('');
    
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch {}
    
    await groupChatService.sendUserMessage(text);
  }, [inputText]);
  
  // 结束群聊
  const handleEndChat = useCallback(() => {
    Alert.alert(
      '结束群聊',
      '确定要结束当前群聊吗？',
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '确定', 
          onPress: () => {
            groupChatService.endGroupChat();
            setShowScenarios(true);
            setMessages([]);
            setActiveCharacters([]);
          }
        },
      ]
    );
  }, []);
  
  // 渲染消息
  const renderMessage = useCallback(({ item }: { item: GroupMessage }) => (
    <MessageBubble message={item} isOwn={item.role === 'user'} />
  ), []);
  
  // 提取 key
  const keyExtractor = useCallback((item: GroupMessage) => item.id, []);
  
  // 获取 Item Layout
  const getItemLayout = useCallback((data: any, index: number) => ({
    length: 80,
    offset: 80 * index,
    index,
  }), []);
  
  // 获取所有场景
  const allScenarios = useMemo(() => groupChatService.getAllScenarios(), []);
  
  // 场景选择界面
  if (showScenarios) {
    return (
      <>
        <Stack.Screen options={{ title: '多角色群聊', headerShown: true }} />
        
        <View style={[styles.container, { paddingTop: insets.top }]}>
          {/* 说明 */}
          <View style={styles.scenarioHeader}>
            <Ionicons name="people-circle" size={48} color="#6366f1" />
            <Text style={styles.scenarioTitle}>多角色群聊</Text>
            <Text style={styles.scenarioSubtitle}>
              选择一个场景，让多个 AI 角色一起聊天互动
            </Text>
          </View>
          
          {/* 场景列表 */}
          <FlatList
            data={allScenarios}
            renderItem={({ item }) => (
              <ScenarioCard 
                scenario={item} 
                onPress={() => handleStartScenario(item.id)} 
              />
            )}
            keyExtractor={(item) => item.id}
            numColumns={2}
            contentContainerStyle={styles.scenarioList}
            columnWrapperStyle={styles.scenarioRow}
          />
          
          {/* 自定义群聊 */}
          <View style={[styles.customButton, { paddingBottom: insets.bottom + 16 }]}>
            <TouchableOpacity
              style={styles.customButtonInner}
              onPress={handleCreateCustomScenario}
            >
              <Ionicons name="add-circle" size={20} color="#6366f1" />
              <Text style={styles.customButtonText}>创建自定义群聊</Text>
            </TouchableOpacity>
          </View>
        </View>
      </>
    );
  }
  
  // 群聊界面
  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      
      <KeyboardAvoidingView 
        style={styles.container} 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {/* 头部 */}
        <View style={[styles.header, { paddingTop: insets.top + 6 }]}>
          <TouchableOpacity onPress={() => setShowScenarios(true)} style={styles.headerBtn}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          
          {/* 活跃角色头像 */}
          <View style={styles.headerCharacters}>
            {activeCharacters.slice(0, 4).map((char, index) => (
              <Avatar 
                key={char.id} 
                uri={char.avatar} 
                size={28}
                isTyping={typingCharacters.includes(char.id)}
              />
            ))}
            {activeCharacters.length > 4 && (
              <View style={styles.moreCharacters}>
                <Text style={styles.moreCharactersText}>+{activeCharacters.length - 4}</Text>
              </View>
            )}
          </View>
          
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle} numberOfLines={1}>
              {groupChatService.getCurrentChat()?.config.name || '群聊'}
            </Text>
            <Text style={styles.headerSubtitle}>
              {activeCharacters.length} 个角色在线
            </Text>
          </View>
          
          <TouchableOpacity onPress={handleEndChat} style={styles.headerBtn}>
            <Ionicons name="close-circle" size={24} color="#ef4444" />
          </TouchableOpacity>
        </View>
        
        {/* 正在输入提示 */}
        {typingCharacters.length > 0 && (
          <View style={styles.typingBar}>
            {typingCharacters.map(charId => {
              const char = activeCharacters.find(c => c.id === charId);
              return char ? (
                <View key={charId} style={styles.typingItem}>
                  <Avatar uri={char.avatar} size={20} />
                  <Text style={styles.typingText}>{char.name} 正在输入...</Text>
                </View>
              ) : null;
            })}
          </View>
        )}
        
        {/* 消息列表 */}
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={keyExtractor}
          contentContainerStyle={styles.messageList}
          showsVerticalScrollIndicator={false}
          onScrollToIndexFailed={() => {}}
        />
        
        {/* 输入栏 */}
        <View style={[styles.inputContainer, { paddingBottom: insets.bottom + 8 }]}>
          <TextInput
            style={styles.input}
            value={inputText}
            onChangeText={setInputText}
            placeholder="发送消息..."
            placeholderTextColor="#9ca3af"
            multiline
            maxLength={500}
            editable={!isGenerating}
          />
          
          <TouchableOpacity
            style={[styles.sendButton, !inputText.trim() && styles.sendButtonDisabled]}
            onPress={handleSend}
            disabled={!inputText.trim() || isGenerating}
          >
            <Ionicons 
              name="send" 
              size={20} 
              color={inputText.trim() ? '#fff' : '#9ca3af'} 
            />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  
  // 场景选择
  scenarioHeader: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 16,
  },
  scenarioTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1e293b',
    marginTop: 12,
  },
  scenarioSubtitle: {
    fontSize: 14,
    color: '#64748b',
    marginTop: 8,
    textAlign: 'center',
  },
  scenarioList: {
    padding: 12,
  },
  scenarioRow: {
    justifyContent: 'space-between',
  },
  scenarioCard: {
    width: (SCREEN_WIDTH - 36) / 2,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  scenarioIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#eef2ff',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  scenarioName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  scenarioDesc: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 16,
    marginBottom: 8,
  },
  scenarioCount: {
    fontSize: 11,
    color: '#6366f1',
    fontWeight: '500',
  },
  customButton: {
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  customButtonInner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    backgroundColor: '#eef2ff',
    borderRadius: 12,
  },
  customButtonText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '600',
  },
  
  // 群聊界面
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingBottom: 10,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerBtn: {
    padding: 6,
  },
  headerCharacters: {
    flexDirection: 'row',
    marginLeft: 8,
  },
  moreCharacters: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#e5e7eb',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: -8,
  },
  moreCharactersText: {
    fontSize: 10,
    color: '#64748b',
    fontWeight: '600',
  },
  headerInfo: {
    flex: 1,
    marginLeft: 8,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
  },
  headerSubtitle: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
  },
  
  // 头像
  avatarContainer: {
    position: 'relative',
  },
  avatar: {
    backgroundColor: '#f1f5f9',
  },
  typingIndicator: {
    position: 'absolute',
    bottom: -2,
    right: -2,
    flexDirection: 'row',
    backgroundColor: '#6366f1',
    borderRadius: 8,
    paddingHorizontal: 4,
    paddingVertical: 2,
    gap: 2,
  },
  typingDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#fff',
  },
  typingDotDelay1: {
    opacity: 0.7,
  },
  typingDotDelay2: {
    opacity: 0.4,
  },
  
  // 输入栏
  typingBar: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#eef2ff',
    gap: 8,
  },
  typingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  typingText: {
    fontSize: 11,
    color: '#6366f1',
  },
  
  // 消息列表
  messageList: {
    padding: 12,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-end',
  },
  messageRowOwn: {
    justifyContent: 'flex-end',
  },
  messageBubble: {
    maxWidth: '70%',
    backgroundColor: '#fff',
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    padding: 10,
    marginLeft: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  messageBubbleOwn: {
    backgroundColor: '#6366f1',
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 4,
    marginLeft: 0,
    marginRight: 8,
  },
  characterName: {
    fontSize: 11,
    color: '#6366f1',
    fontWeight: '600',
    marginBottom: 4,
  },
  messageText: {
    fontSize: 14,
    color: '#1e293b',
    lineHeight: 20,
  },
  messageTextOwn: {
    color: '#fff',
  },
  messageTime: {
    fontSize: 10,
    color: '#9ca3af',
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  messageTimeOwn: {
    color: 'rgba(255, 255, 255, 0.7)',
  },
  systemMessage: {
    alignItems: 'center',
    marginVertical: 8,
  },
  systemMessageText: {
    fontSize: 12,
    color: '#9ca3af',
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  
  // 输入栏
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 12,
    paddingTop: 8,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 100,
    backgroundColor: '#f1f5f9',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 14,
    color: '#1e293b',
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#6366f1',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
  sendButtonDisabled: {
    backgroundColor: '#e5e7eb',
  },
});
