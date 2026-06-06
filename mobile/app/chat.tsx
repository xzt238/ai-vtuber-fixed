// ============================================
// GuguGaga AI VTuber Mobile - 聊天页面（动画增强版）
// ============================================
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, TextInput, FlatList,
  KeyboardAvoidingView, Platform, Alert, Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { AnimatedBubble } from '../src/components/AnimatedBubble';
import { AnimatedButton } from '../src/components/AnimatedButton';
import { TypingIndicator } from '../src/components/TypingIndicator';
import { EmotionBadge } from '../src/components/EmotionBadge';
import { FadeInView } from '../src/components/FadeInView';
import Live2DView from '../src/components/live2d/Live2DView';
import { ttsService } from '../src/services/tts';
import { asrService } from '../src/services/asr';
import { ragService } from '../src/services/rag';
import { emotionService } from '../src/services/emotion';
import type { Emotion } from '../src/services/emotion';
import { apiService } from '../src/services/api';
import { localAI } from '../src/services/localAI';
import { modelManager, ModelConfig } from '../src/services/modelManager';
import { useConversationStore, useCharacterStore, useSettingsStore } from '../src/stores';
import type { Message } from '../src/types';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

export default function ChatPage() {
  const { characterId, conversationId } = useLocalSearchParams<{ characterId: string; conversationId?: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [inputText, setInputText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState<Emotion>('neutral');
  const [isTalking, setIsTalking] = useState(false);
  const [live2dMessage, setLive2dMessage] = useState('');
  const [showLive2D, setShowLive2D] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastMessageId, setLastMessageId] = useState<string | null>(null);
  const [currentModel, setCurrentModelState] = useState<ModelConfig | null>(modelManager.getCurrentModel());

  const flatListRef = useRef<FlatList>(null);
  const isMounted = useRef(true);

  const { characters } = useCharacterStore();
  const { conversations, addMessage, createConversation, setCurrentConversation } = useConversationStore();
  const { settings } = useSettingsStore();

  const character = useMemo(() => characters.find(c => c.id === characterId), [characters, characterId]);
  const conversation = useMemo(() =>
    conversations.find(c => c.id === conversationId) || (conversations.length > 0 ? conversations[0] : null),
    [conversations, conversationId]
  );
  const messages = useMemo(() => conversation?.messages || [], [conversation]);

  useEffect(() => { return () => { isMounted.current = false; }; }, []);

  // 初始化模型
  useEffect(() => {
    const initModel = async () => {
      const model = await modelManager.loadSavedModel();
      if (model && isMounted.current) {
        setCurrentModelState(model);
      }
    };
    initModel();
    
    // 监听模型变更
    const unsubscribe = modelManager.onModelChange((model) => {
      if (isMounted.current) {
        setCurrentModelState(model);
      }
    });
    
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (!conversation && characterId) {
      const newConv = createConversation(characterId);
      setCurrentConversation(newConv);
    }
  }, [characterId]);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => flatListRef.current?.scrollToEnd({ animated: true }));
  }, []);

  // 发送消息
  const handleSend = useCallback(async () => {
    if (!inputText.trim() || !character || !conversation || isGenerating) return;

    const userText = inputText.trim();
    setInputText('');
    setError(null);

    addMessage(conversation.id, { role: 'user', content: userText });
    scrollToBottom();

    const userEmotion = emotionService.analyze(userText);
    setCurrentEmotion(userEmotion.emotion);

    try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); } catch {}

    setIsGenerating(true);
    try {
      const ragContext = await ragService.buildContext(userText);
      const enhancedPrompt = ragContext ? `${ragContext}\n\n请基于以上参考资料回答。` : userText;

      let aiResponse: string;
      if (apiService.isInitialized()) {
        const chatMessages = messages.map(m => ({ role: m.role, content: m.content }));
        chatMessages.push({ role: 'user', content: enhancedPrompt });
        aiResponse = await apiService.chat(chatMessages, character);
      } else {
        aiResponse = await localAI.generateResponse(enhancedPrompt, character, messages, settings.ai);
      }

      if (!isMounted.current) return;

      const aiEmotion = emotionService.analyze(aiResponse);
      setCurrentEmotion(aiEmotion.emotion);

      addMessage(conversation.id, { role: 'assistant', content: aiResponse });
      setLastMessageId(`msg_${Date.now()}`);
      scrollToBottom();

      setLive2dMessage(aiResponse.length > 40 ? aiResponse.substring(0, 40) + '...' : aiResponse);

      if (settings.user.soundEnabled) {
        setIsTalking(true);
        await ttsService.speak(aiResponse, {
          emotion: aiEmotion.emotion,
          rate: settings.tts.speed,
        });
      }
    } catch {
      if (isMounted.current) setError('回复生成失败');
    } finally {
      if (isMounted.current) { setIsGenerating(false); setIsTalking(false); }
    }
  }, [inputText, character, conversation, isGenerating, settings, messages, addMessage, scrollToBottom]);

  // 语音输入
  const handleVoicePress = useCallback(async () => {
    if (isRecording) {
      setIsRecording(false);
      try {
        const uri = await asrService.stopRecording();
        if (uri) {
          const text = await asrService.recognize(uri, { provider: 'whisper', apiKey: settings.ai.apiKey, language: 'zh' });
          if (text && !text.startsWith('[')) setInputText(text);
          else Alert.alert('语音识别', '未能识别');
        }
      } catch { Alert.alert('识别失败', '请检查网络'); }
    } else {
      try {
        setIsRecording(true);
        try { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium); } catch {}
        await asrService.startRecording();
      } catch { setIsRecording(false); Alert.alert('录音失败', '请检查麦克风权限'); }
    }
  }, [isRecording, settings]);

  const handleLive2DTapHead = useCallback(() => {
    const responses = ['嘿嘿，你摸我头干嘛~', '哎呀，好痒呀！', '嘻嘻，你喜欢我吗？'];
    const response = responses[Math.floor(Math.random() * responses.length)];
    setLive2dMessage(response);
    if (settings.user.soundEnabled) ttsService.speak(response, { ...settings.tts, emotion: 'happy' });
  }, [settings]);

  // 渲染
  const renderMessage = useCallback(({ item, index }: { item: Message; index: number }) => (
    <AnimatedBubble
      message={item}
      characterName={character?.name || 'AI'}
      isNew={item.id === lastMessageId}
    />
  ), [character?.name, lastMessageId]);

  const renderEmpty = useCallback(() => (
    <FadeInView style={styles.emptyContainer}>
      <Ionicons name="chatbubbles" size={48} color="#d1d5db" />
      <Text style={styles.emptyTitle}>开始对话</Text>
      <Text style={styles.emptySubtitle}>{character ? `和${character.name}聊天吧` : '选择一个角色开始'}</Text>
    </FadeInView>
  ), [character]);

  const canSend = useMemo(() => inputText.trim().length > 0 && !isGenerating, [inputText, isGenerating]);

  if (!characterId || !character) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{!characterId ? '未指定角色' : '角色不存在'}</Text>
        <AnimatedButton onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>返回</Text>
        </AnimatedButton>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'} keyboardVerticalOffset={0}>
        {/* 头部 */}
        <FadeInView style={[styles.header, { paddingTop: insets.top + 6 }]}>
          <AnimatedButton onPress={() => router.back()} style={styles.headerBtn}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </AnimatedButton>
          <View style={styles.headerInfo}>
            <Text style={styles.characterName} numberOfLines={1}>{character.name}</Text>
            <Text style={[styles.status, { color: isGenerating ? '#f59e0b' : isTalking ? '#3b82f6' : '#10b981' }]}>
              {isGenerating ? '思考中...' : isTalking ? '说话中...' : '在线'}
            </Text>
          </View>
          <EmotionBadge emotion={currentEmotion} visible={currentEmotion !== 'neutral'} />
          <AnimatedButton onPress={() => router.push('/model-select')} style={styles.headerBtn}>
            <Ionicons name="cube" size={20} color={currentModel ? '#6366f1' : '#6b7280'} />
          </AnimatedButton>
          <AnimatedButton onPress={() => setShowLive2D(!showLive2D)} style={styles.headerBtn}>
            <Ionicons name={showLive2D ? 'eye' : 'eye-off'} size={20} color="#6b7280" />
          </AnimatedButton>
        </FadeInView>

        {/* Live2D */}
        {showLive2D && (
          <View style={styles.live2dContainer}>
            <Live2DView emotion={currentEmotion} isTalking={isTalking} message={live2dMessage} onTapHead={handleLive2DTapHead} />
          </View>
        )}

        {/* 错误提示 */}
        {error && (
          <FadeInView style={styles.errorBanner}>
            <Ionicons name="warning" size={14} color="#f59e0b" />
            <Text style={styles.errorBannerText}>{error}</Text>
            <AnimatedButton onPress={() => setError(null)}>
              <Ionicons name="close" size={14} color="#9ca3af" />
            </AnimatedButton>
          </FadeInView>
        )}

        {/* 消息列表 */}
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.messageList}
          ListEmptyComponent={renderEmpty}
          ListFooterComponent={<TypingIndicator characterName={character.name} visible={isGenerating} />}
          onContentSizeChange={scrollToBottom}
          style={styles.messageFlatList}
          keyboardDismissMode="on-drag"
          removeClippedSubviews={true}
          maxToRenderPerBatch={15}
          windowSize={10}
        />

        {/* 输入区域 */}
        <FadeInView style={[styles.inputBar, { paddingBottom: insets.bottom + 6 }]}>
          <AnimatedButton
            onPress={handleVoicePress}
            style={[styles.voiceBtn, isRecording && styles.voiceBtnActive]}
            scaleTo={0.9}
          >
            <Ionicons name={isRecording ? 'stop-circle' : 'mic-outline'} size={22} color={isRecording ? '#ef4444' : '#6b7280'} />
          </AnimatedButton>

          <TextInput
            style={styles.input}
            value={inputText}
            onChangeText={setInputText}
            placeholder={isRecording ? '录音中...' : '输入消息...'}
            placeholderTextColor="#9ca3af"
            multiline
            maxLength={2000}
            editable={!isGenerating && !isRecording}
          />

          <AnimatedButton
            onPress={handleSend}
            disabled={!canSend}
            style={[styles.sendBtn, !canSend && styles.sendBtnDisabled]}
            scaleTo={0.85}
          >
            <Ionicons name="send" size={16} color={canSend ? '#fff' : '#9ca3af'} />
          </AnimatedButton>
        </FadeInView>
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  header: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    paddingHorizontal: 10, paddingBottom: 8, borderBottomWidth: 1, borderBottomColor: '#e5e7eb', zIndex: 10, gap: 6,
  },
  headerBtn: { padding: 8 },
  headerInfo: { flex: 1 },
  characterName: { fontSize: 16, fontWeight: '700', color: '#1f2937' },
  status: { fontSize: 11, marginTop: 1 },
  live2dContainer: { height: SCREEN_HEIGHT * 0.25, minHeight: 140, maxHeight: 220 },
  messageFlatList: { flex: 1 },
  messageList: { paddingVertical: 6 },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 40 },
  emptyTitle: { fontSize: 17, fontWeight: '600', color: '#4b5563', marginTop: 12 },
  emptySubtitle: { fontSize: 13, color: '#9ca3af', marginTop: 4 },
  errorBanner: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fef3c7',
    paddingHorizontal: 14, paddingVertical: 6, gap: 6,
  },
  errorBannerText: { flex: 1, fontSize: 12, color: '#92400e' },
  inputBar: {
    flexDirection: 'row', alignItems: 'flex-end', backgroundColor: '#fff',
    paddingHorizontal: 8, paddingTop: 6, borderTopWidth: 1, borderTopColor: '#e5e7eb', gap: 6,
  },
  voiceBtn: { padding: 9, borderRadius: 22, backgroundColor: '#f3f4f6' },
  voiceBtnActive: { backgroundColor: '#fef2f2' },
  input: {
    flex: 1, backgroundColor: '#f3f4f6', borderRadius: 18,
    paddingHorizontal: 14, paddingVertical: 9, fontSize: 15, maxHeight: 85, color: '#1f2937',
  },
  sendBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#6366f1', justifyContent: 'center', alignItems: 'center' },
  sendBtnDisabled: { backgroundColor: '#e5e7eb' },
  errorContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { fontSize: 15, color: '#ef4444', marginBottom: 14 },
  backBtn: { backgroundColor: '#6366f1', paddingHorizontal: 20, paddingVertical: 10, borderRadius: 18 },
  backBtnText: { color: '#fff', fontSize: 14, fontWeight: '600' },
});
