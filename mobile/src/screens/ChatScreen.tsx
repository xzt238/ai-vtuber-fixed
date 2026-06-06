/**
 * 对话页面
 *
 * 支持云端 LLM 对话、Markdown 渲染
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/Ionicons';
import { COLORS } from '../utils/constants';
import { useChatStore } from '../store/chatStore';
import { useCharacterStore } from '../store/characterStore';
import { useAppStore } from '../store/appStore';
import { aiEngine } from '../services/ai/aiEngine';
import { ChatMessage } from '../types/chat';

const ChatScreen: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const flatListRef = useRef<FlatList>(null);

  const {
    currentSession,
    isSending,
    createSession,
    addMessage,
    setSending,
    getMessages,
    clearCurrentSession,
  } = useChatStore();

  const { activeCharacter } = useCharacterStore();
  const { isConnected } = useAppStore();

  // 初始化会话
  useEffect(() => {
    if (!currentSession && activeCharacter) {
      const session = createSession(activeCharacter.id);
      // 添加欢迎消息
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        role: 'assistant',
        content: activeCharacter.greeting || '你好！有什么我可以帮助你的吗？',
        type: 'text',
        timestamp: Date.now(),
        characterId: activeCharacter.id,
      };
      addMessage(welcomeMessage);
    }
  }, [activeCharacter]);

  // 发送消息
  const sendMessage = async () => {
    if (!inputText.trim() || isSending || !currentSession) return;

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: inputText.trim(),
      type: 'text',
      timestamp: Date.now(),
      characterId: activeCharacter?.id,
    };

    addMessage(userMessage);
    setInputText('');
    setSending(true);

    try {
      const history = getMessages().slice(-20);
      const { content, source } = await aiEngine.chat(
        inputText.trim(),
        activeCharacter?.id || 'default',
        history,
        activeCharacter?.systemPrompt
      );

      const aiMessage: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content,
        type: 'text',
        timestamp: Date.now(),
        characterId: activeCharacter?.id,
      };

      addMessage(aiMessage);
    } catch (error: any) {
      console.error('[ChatScreen] 发送消息失败:', error);
      const errorMessage: ChatMessage = {
        id: `msg_err_${Date.now()}`,
        role: 'assistant',
        content: `抱歉，发送消息失败: ${error.message || '未知错误'}。请检查网络连接或服务器配置。`,
        type: 'text',
        timestamp: Date.now(),
      };
      addMessage(errorMessage);
    } finally {
      setSending(false);
    }
  };

  // 清空历史
  const clearHistory = () => {
    Alert.alert('清空历史', '确定要清空所有聊天记录吗？', [
      { text: '取消', style: 'cancel' },
      {
        text: '确定',
        onPress: () => {
          clearCurrentSession();
          if (activeCharacter) {
            const welcomeMessage: ChatMessage = {
              id: 'welcome',
              role: 'assistant',
              content: activeCharacter.greeting || '你好！有什么我可以帮助你的吗？',
              type: 'text',
              timestamp: Date.now(),
              characterId: activeCharacter.id,
            };
            addMessage(welcomeMessage);
          }
        },
      },
    ]);
  };

  // 获取模型源描述
  const getModelSourceText = (): string => {
    return aiEngine.getActiveSource();
  };

  // 渲染消息
  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === 'user';

    return (
      <View
        style={[
          styles.messageContainer,
          isUser ? styles.userMessage : styles.aiMessage,
        ]}
      >
        {!isUser && (
          <View style={styles.avatarContainer}>
            <Icon name="person-circle" size={32} color={COLORS.primary} />
          </View>
        )}
        <View
          style={[
            styles.messageBubble,
            isUser ? styles.userBubble : styles.aiBubble,
          ]}
        >
          <Text
            style={[
              styles.messageText,
              isUser ? styles.userText : styles.aiText,
            ]}
          >
            {item.content}
          </Text>
          <Text style={styles.timestamp}>
            {new Date(item.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Text>
        </View>
        {isUser && (
          <View style={styles.avatarContainer}>
            <Icon name="person-circle" size={32} color={COLORS.secondary} />
          </View>
        )}
      </View>
    );
  };

  const messages = getMessages();

  return (
    <SafeAreaView style={styles.container}>
      {/* 头部 */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.headerTitle}>
            {activeCharacter?.name || '咕咕嘎嘎'}
          </Text>
          <Text style={styles.characterDesc}>
            {activeCharacter?.description || 'AI 助手'}
          </Text>
        </View>
        <View style={styles.headerRight}>
          <View style={styles.statusContainer}>
            <View
              style={[
                styles.statusDot,
                { backgroundColor: isConnected ? COLORS.success : COLORS.warning },
              ]}
            />
            <Text style={styles.statusText}>{getModelSourceText()}</Text>
          </View>
          <TouchableOpacity style={styles.clearButton} onPress={clearHistory}>
            <Icon name="trash-outline" size={20} color={COLORS.gray} />
          </TouchableOpacity>
        </View>
      </View>

      {/* 消息列表 */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        style={styles.messageList}
        contentContainerStyle={styles.messageListContent}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: true })
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Icon name="chatbubbles-outline" size={64} color={COLORS.lightGray} />
            <Text style={styles.emptyText}>开始和AI聊天吧</Text>
            <Text style={styles.emptySubtext}>
              当前使用: {getModelSourceText()}
            </Text>
          </View>
        }
      />

      {/* 输入区域 */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.inputContainer}
      >
        <View style={styles.inputRow}>
          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={setInputText}
            placeholder="输入消息..."
            placeholderTextColor={COLORS.lightGray}
            multiline
            maxLength={1000}
            editable={!isSending}
          />
          <TouchableOpacity
            style={[
              styles.sendButton,
              {
                opacity: inputText.trim() && !isSending ? 1 : 0.5,
              },
            ]}
            onPress={sendMessage}
            disabled={!inputText.trim() || isSending}
          >
            {isSending ? (
              <ActivityIndicator size="small" color={COLORS.white} />
            ) : (
              <Icon name="send" size={20} color={COLORS.white} />
            )}
          </TouchableOpacity>
        </View>
        <View style={styles.tipContainer}>
          <Icon
            name="information-circle-outline"
            size={12}
            color={COLORS.textSecondary}
          />
          <Text style={styles.tipText}>
            模型: {getModelSourceText()} | 角色: {activeCharacter?.name || '默认'}
          </Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: COLORS.white,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  headerLeft: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.text,
  },
  characterDesc: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: 12,
    color: COLORS.gray,
  },
  clearButton: {
    padding: 4,
  },
  messageList: {
    flex: 1,
  },
  messageListContent: {
    padding: 16,
  },
  messageContainer: {
    flexDirection: 'row',
    marginBottom: 16,
    alignItems: 'flex-end',
  },
  userMessage: {
    justifyContent: 'flex-end',
  },
  aiMessage: {
    justifyContent: 'flex-start',
  },
  avatarContainer: {
    marginHorizontal: 8,
  },
  messageBubble: {
    maxWidth: '70%',
    padding: 12,
    borderRadius: 16,
  },
  userBubble: {
    backgroundColor: COLORS.primary,
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: COLORS.white,
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: COLORS.white,
  },
  aiText: {
    color: COLORS.text,
  },
  timestamp: {
    fontSize: 10,
    color: COLORS.lightGray,
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 16,
    color: COLORS.lightGray,
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 8,
  },
  inputContainer: {
    backgroundColor: COLORS.white,
    borderTopWidth: 1,
    borderTopColor: COLORS.lightGray,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
  },
  textInput: {
    flex: 1,
    backgroundColor: COLORS.background,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    marginRight: 8,
    fontSize: 16,
    maxHeight: 100,
  },
  sendButton: {
    backgroundColor: COLORS.primary,
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  tipContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 8,
    gap: 4,
  },
  tipText: {
    fontSize: 11,
    color: COLORS.textSecondary,
  },
});

export default ChatScreen;
