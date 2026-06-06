// ============================================
// 游戏助手页面
// ============================================
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Alert,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { gameService, GameType, GameTemplate, GameState, GameAction } from '../src/services/game';

// 游戏卡片组件
const GameCard = React.memo(({ 
  template, 
  isSelected, 
  onSelect 
}: { 
  template: GameTemplate; 
  isSelected: boolean;
  onSelect: () => void;
}) => (
  <TouchableOpacity
    style={[styles.gameCard, isSelected && styles.gameCardSelected]}
    onPress={onSelect}
    activeOpacity={0.7}
  >
    <Text style={styles.gameIcon}>{template.icon}</Text>
    <Text style={[styles.gameName, isSelected && styles.gameNameSelected]} numberOfLines={1}>
      {template.name}
    </Text>
    <Text style={[styles.gameDesc, isSelected && styles.gameDescSelected]} numberOfLines={2}>
      {template.description}
    </Text>
    <View style={styles.featureTags}>
      {template.features.slice(0, 2).map((feature, index) => (
        <View key={index} style={[styles.featureTag, isSelected && styles.featureTagSelected]}>
          <Text style={[styles.featureText, isSelected && styles.featureTextSelected]}>
            {feature}
          </Text>
        </View>
      ))}
    </View>
  </TouchableOpacity>
));

// 消息组件
const MessageBubble = React.memo(({ message, isUser }: { message: string; isUser: boolean }) => (
  <View style={[styles.messageBubble, isUser ? styles.userBubble : styles.aiBubble]}>
    <Text style={[styles.messageText, isUser ? styles.userText : styles.aiText]}>
      {message}
    </Text>
  </View>
));

// 功能按钮组件
const ActionButton = React.memo(({ 
  icon, 
  label, 
  onPress, 
  color = '#6366f1' 
}: { 
  icon: string; 
  label: string; 
  onPress: () => void;
  color?: string;
}) => (
  <TouchableOpacity style={[styles.actionButton, { backgroundColor: color + '15' }]} onPress={onPress}>
    <Ionicons name={icon as any} size={20} color={color} />
    <Text style={[styles.actionLabel, { color }]}>{label}</Text>
  </TouchableOpacity>
));

export default function GameAssistantScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const flatListRef = useRef<FlatList>(null);
  
  const [selectedGame, setSelectedGame] = useState<GameType | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [messages, setMessages] = useState<Array<{ id: string; text: string; isUser: boolean }>>([]);
  const [inputText, setInputText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  
  // 获取游戏模板
  const templates = useMemo(() => gameService.getTemplates(), []);
  
  // 选择游戏
  const handleSelectGame = useCallback((gameType: GameType) => {
    setSelectedGame(gameType);
    const state = gameService.startGame(gameType);
    setGameState(state);
    setMessages([]);
    
    // 添加欢迎消息
    const template = gameService.getTemplate(gameType);
    if (template) {
      setMessages([{
        id: 'welcome',
        text: `已启动 ${template.name} 游戏助手！\n\n${template.description}\n\n你可以问我任何关于这个游戏的问题，比如：\n• 合成配方\n• 游戏攻略\n• 物品信息\n• 建造建议`,
        isUser: false,
      }]);
    }
  }, []);
  
  // 发送消息
  const handleSend = useCallback(async () => {
    if (!inputText.trim() || !selectedGame || isGenerating) return;
    
    const userMessage = inputText.trim();
    setInputText('');
    
    // 添加用户消息
    setMessages(prev => [...prev, {
      id: `user_${Date.now()}`,
      text: userMessage,
      isUser: true,
    }]);
    
    setIsGenerating(true);
    
    try {
      // 获取AI回复
      const response = await gameService.askGameQuestion(userMessage);
      
      // 添加AI回复
      setMessages(prev => [...prev, {
        id: `ai_${Date.now()}`,
        text: response,
        isUser: false,
      }]);
    } catch (error) {
      console.error('Send message error:', error);
      setMessages(prev => [...prev, {
        id: `error_${Date.now()}`,
        text: '抱歉，处理消息时出错了，请重试',
        isUser: false,
      }]);
    } finally {
      setIsGenerating(false);
    }
  }, [inputText, selectedGame, isGenerating]);
  
  // 获取攻略
  const handleGetGuide = useCallback(async (topic: string) => {
    if (!selectedGame || isGenerating) return;
    
    setIsGenerating(true);
    
    try {
      const guide = await gameService.getGameGuide(topic);
      setMessages(prev => [...prev, {
        id: `guide_${Date.now()}`,
        text: `📖 ${topic}攻略\n\n${guide}`,
        isUser: false,
      }]);
    } catch (error) {
      console.error('Get guide error:', error);
    } finally {
      setIsGenerating(false);
    }
  }, [selectedGame, isGenerating]);
  
  // 获取随机提示
  const handleGetTip = useCallback(() => {
    const tip = gameService.getRandomTip();
    setMessages(prev => [...prev, {
      id: `tip_${Date.now()}`,
      text: `💡 小提示：${tip}`,
      isUser: false,
    }]);
  }, []);
  
  // 获取物品信息
  const handleGetItemInfo = useCallback(async () => {
    if (!selectedGame) return;
    
    Alert.prompt(
      '查询物品',
      '输入物品名称',
      async (itemName) => {
        if (itemName) {
          setIsGenerating(true);
          try {
            const info = await gameService.getItemInfo(itemName);
            setMessages(prev => [...prev, {
              id: `item_${Date.now()}`,
              text: `📦 ${itemName}\n\n${info}`,
              isUser: false,
            }]);
          } catch (error) {
            console.error('Get item info error:', error);
          } finally {
            setIsGenerating(false);
          }
        }
      }
    );
  }, [selectedGame]);
  
  // 清除聊天
  const handleClearChat = useCallback(() => {
    Alert.alert(
      '清除聊天',
      '确定要清除所有聊天记录吗？',
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '清除', 
          style: 'destructive',
          onPress: () => {
            setMessages([]);
            if (selectedGame) {
              const template = gameService.getTemplate(selectedGame);
              if (template) {
                setMessages([{
                  id: 'welcome_new',
                  text: `聊天已清除。继续问我关于 ${template.name} 的问题吧！`,
                  isUser: false,
                }]);
              }
            }
          }
        },
      ]
    );
  }, [selectedGame]);
  
  // 渲染游戏选择界面
  const renderGameSelection = () => (
    <View style={styles.selectionContainer}>
      <View style={styles.selectionHeader}>
        <Ionicons name="game-controller" size={48} color="#6366f1" />
        <Text style={styles.selectionTitle}>游戏助手</Text>
        <Text style={styles.selectionSubtitle}>
          选择你正在玩的游戏，获取实时帮助和攻略
        </Text>
      </View>
      
      <FlatList
        data={templates}
        renderItem={({ item }) => (
          <GameCard
            template={item}
            isSelected={selectedGame === item.gameType}
            onSelect={() => handleSelectGame(item.gameType)}
          />
        )}
        keyExtractor={(item) => item.id}
        numColumns={2}
        contentContainerStyle={styles.gameList}
        columnWrapperStyle={styles.gameRow}
      />
    </View>
  );
  
  // 渲染聊天界面
  const renderChat = () => {
    const template = selectedGame ? gameService.getTemplate(selectedGame) : null;
    
    return (
      <KeyboardAvoidingView 
        style={styles.chatContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={90}
      >
        {/* 头部 */}
        <View style={[styles.chatHeader, { paddingTop: insets.top + 10 }]}>
          <TouchableOpacity onPress={() => setSelectedGame(null)} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle}>{template?.icon} {template?.name}</Text>
            <Text style={styles.headerSubtitle}>游戏助手</Text>
          </View>
          <TouchableOpacity onPress={handleClearChat} style={styles.clearButton}>
            <Ionicons name="trash-outline" size={20} color="#6b7280" />
          </TouchableOpacity>
        </View>
        
        {/* 功能按钮 */}
        <ScrollView 
          horizontal 
          showsHorizontalScrollIndicator={false}
          style={styles.actionBar}
          contentContainerStyle={styles.actionBarContent}
        >
          <ActionButton icon="bulb" label="随机提示" onPress={handleGetTip} />
          <ActionButton icon="search" label="查询物品" onPress={handleGetItemInfo} />
          {template?.tips.slice(0, 3).map((tip, index) => (
            <ActionButton 
              key={index}
              icon="bookmark" 
              label={tip.length > 8 ? tip.substring(0, 8) + '...' : tip} 
              onPress={() => handleGetGuide(tip)} 
              color="#10b981"
            />
          ))}
        </ScrollView>
        
        {/* 消息列表 */}
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={({ item }) => (
            <MessageBubble message={item.text} isUser={item.isUser} />
          )}
          keyExtractor={(item) => item.id}
          style={styles.messageList}
          contentContainerStyle={styles.messageListContent}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        />
        
        {/* 输入栏 */}
        <View style={[styles.inputBar, { paddingBottom: insets.bottom + 10 }]}>
          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={setInputText}
            placeholder="问我任何游戏问题..."
            placeholderTextColor="#9ca3af"
            multiline
            maxLength={500}
            editable={!isGenerating}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || isGenerating) && styles.sendButtonDisabled]}
            onPress={handleSend}
            disabled={!inputText.trim() || isGenerating}
          >
            {isGenerating ? (
              <Ionicons name="hourglass" size={20} color="#fff" />
            ) : (
              <Ionicons name="send" size={20} color="#fff" />
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    );
  };
  
  return (
    <>
      <Stack.Screen options={{ title: '游戏助手', headerShown: false }} />
      <View style={styles.container}>
        {selectedGame ? renderChat() : renderGameSelection()}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  // 游戏选择界面
  selectionContainer: {
    flex: 1,
    paddingTop: 60,
  },
  selectionHeader: {
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  selectionTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1f2937',
    marginTop: 12,
  },
  selectionSubtitle: {
    fontSize: 15,
    color: '#6b7280',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 22,
  },
  gameList: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  gameRow: {
    justifyContent: 'space-between',
  },
  gameCard: {
    width: '48%',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  gameCardSelected: {
    backgroundColor: '#6366f1',
    shadowColor: '#6366f1',
    shadowOpacity: 0.3,
  },
  gameIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  gameName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 4,
  },
  gameNameSelected: {
    color: '#fff',
  },
  gameDesc: {
    fontSize: 12,
    color: '#6b7280',
    lineHeight: 18,
    marginBottom: 8,
  },
  gameDescSelected: {
    color: '#e0e7ff',
  },
  featureTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
  },
  featureTag: {
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  featureTagSelected: {
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  featureText: {
    fontSize: 10,
    color: '#6b7280',
  },
  featureTextSelected: {
    color: '#e0e7ff',
  },
  // 聊天界面
  chatContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },
  chatHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#6b7280',
  },
  clearButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionBar: {
    backgroundColor: '#f9fafb',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  actionBarContent: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 8,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 4,
  },
  actionLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
  messageList: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  messageListContent: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  messageBubble: {
    maxWidth: '80%',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 16,
    marginBottom: 8,
  },
  userBubble: {
    backgroundColor: '#6366f1',
    borderBottomRightRadius: 4,
    alignSelf: 'flex-end',
  },
  aiBubble: {
    backgroundColor: '#fff',
    borderBottomLeftRadius: 4,
    alignSelf: 'flex-start',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  userText: {
    color: '#fff',
  },
  aiText: {
    color: '#1f2937',
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingTop: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    gap: 8,
  },
  textInput: {
    flex: 1,
    backgroundColor: '#f3f4f6',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    maxHeight: 100,
    color: '#1f2937',
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#6366f1',
    justifyContent: 'center',
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#d1d5db',
  },
});