// ============================================
// GuguGaga AI VTuber Mobile - 对话 Tab（性能优化版）
// ============================================
import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useCharacterStore, useConversationStore } from '../../src/stores';
import type { Character, Conversation } from '../../src/types';

// 对话卡片 memo 组件
const ConversationCard = React.memo(({ item, character, onPress }: {
  item: Conversation; character?: Character; onPress: () => void;
}) => (
  <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
    <View style={styles.cardAvatar}>
      <Ionicons name="person" size={22} color="#6366f1" />
    </View>
    <View style={styles.cardInfo}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardName} numberOfLines={1}>{character?.name || '未知角色'}</Text>
        <Text style={styles.cardTime}>{new Date(item.updatedAt).toLocaleDateString()}</Text>
      </View>
      <Text style={styles.cardPreview} numberOfLines={1}>
        {item.messages[item.messages.length - 1]?.content || '暂无消息'}
      </Text>
    </View>
    <Ionicons name="chevron-forward" size={18} color="#9ca3af" />
  </TouchableOpacity>
));

// 角色选择器 memo 组件
const CharacterChip = React.memo(({ character, isSelected, onPress }: {
  character: Character; isSelected: boolean; onPress: () => void;
}) => (
  <TouchableOpacity
    style={[styles.chip, isSelected && styles.chipSelected]}
    onPress={onPress}
    activeOpacity={0.7}
  >
    <View style={styles.chipAvatar}>
      <Ionicons name="person" size={16} color="#6366f1" />
    </View>
    <Text style={styles.chipName} numberOfLines={1}>{character.name}</Text>
  </TouchableOpacity>
));

export default function ChatTab() {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const { characters, loadCharacters } = useCharacterStore();
  const { conversations, loadConversations } = useConversationStore();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => { loadCharacters(); }, []);

  useEffect(() => {
    if (selectedId) loadConversations(selectedId);
  }, [selectedId]);

  // useMemo 缓存排序后的对话列表
  const recentConversations = useMemo(() =>
    [...conversations].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()).slice(0, 10),
    [conversations]
  );

  // useCallback 缓存回调
  const handleNewChat = useCallback((character: Character) => {
    router.push({ pathname: '/chat', params: { characterId: character.id } });
  }, [router]);

  const handleContinueChat = useCallback((conv: Conversation) => {
    router.push({ pathname: '/chat', params: { characterId: conv.characterId, conversationId: conv.id } });
  }, [router]);

  const handleCharacterPress = useCallback((character: Character) => {
    setSelectedId(character.id);
    handleNewChat(character);
  }, [handleNewChat]);

  // FlatList 优化配置
  const flatListConfig = useMemo(() => ({
    removeClippedSubviews: true,
    maxToRenderPerBatch: 10,
    windowSize: 8,
    initialNumToRender: 8,
    getItemLayout: (_: any, index: number) => ({
      length: 76, offset: 76 * index, index,
    }),
  }), []);

  // 渲染函数
  const renderConversation = useCallback(({ item }: { item: Conversation }) => {
    const character = characters.find(c => c.id === item.characterId);
    return (
      <ConversationCard
        item={item}
        character={character}
        onPress={() => handleContinueChat(item)}
      />
    );
  }, [characters, handleContinueChat]);

  const renderCharacterChip = useCallback(({ item }: { item: Character }) => (
    <CharacterChip
      character={item}
      isSelected={selectedId === item.id}
      onPress={() => handleCharacterPress(item)}
    />
  ), [selectedId, handleCharacterPress]);

  const renderEmpty = useCallback(() => (
    <View style={styles.empty}>
      <Ionicons name="chatbubbles" size={48} color="#d1d5db" />
      <Text style={styles.emptyTitle}>开始对话</Text>
      <Text style={styles.emptySub}>选择一个角色开始</Text>
      {characters.length > 0 && (
        <TouchableOpacity style={styles.startBtn} onPress={() => handleNewChat(characters[0])}>
          <Ionicons name="add" size={18} color="#fff" />
          <Text style={styles.startBtnText}>开始新对话</Text>
        </TouchableOpacity>
      )}
    </View>
  ), [characters, handleNewChat]);

  const keyExtractor = useCallback((item: Conversation) => item.id, []);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* 头部 */}
      <View style={styles.header}>
        <Text style={styles.title}>对话</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={styles.headerBtn}
            onPress={() => router.push('/search')}
            activeOpacity={0.7}
          >
            <Ionicons name="search" size={20} color="#6366f1" />
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.addBtn}
            onPress={() => characters.length > 0 ? handleNewChat(characters[0]) : Alert.alert('提示', '请先创建角色')}
            activeOpacity={0.7}
          >
            <Ionicons name="add" size={22} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>

      {/* 角色选择器 */}
      {characters.length > 0 && (
        <View style={styles.selector}>
          <FlatList
            data={characters}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(item) => item.id}
            renderItem={renderCharacterChip}
            contentContainerStyle={styles.chipList}
            removeClippedSubviews={true}
          />
        </View>
      )}

      {/* 对话列表 */}
      <FlatList
        data={recentConversations}
        renderItem={renderConversation}
        keyExtractor={keyExtractor}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={renderEmpty}
        showsVerticalScrollIndicator={false}
        {...flatListConfig}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 18, paddingVertical: 14, backgroundColor: '#fff',
    borderBottomWidth: 1, borderBottomColor: '#e5e7eb',
  },
  title: { fontSize: 22, fontWeight: '700', color: '#1f2937' },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerBtn: {
    width: 36, height: 36, borderRadius: 18, backgroundColor: '#eef2ff',
    justifyContent: 'center', alignItems: 'center',
  },
  addBtn: {
    width: 36, height: 36, borderRadius: 18, backgroundColor: '#6366f1',
    justifyContent: 'center', alignItems: 'center',
  },
  selector: { backgroundColor: '#fff', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#e5e7eb' },
  chipList: { paddingHorizontal: 10 },
  chip: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#f3f4f6',
    paddingHorizontal: 10, paddingVertical: 6, borderRadius: 16, marginHorizontal: 4,
  },
  chipSelected: { backgroundColor: '#e0e7ff' },
  chipAvatar: {
    width: 22, height: 22, borderRadius: 11, backgroundColor: '#e0e7ff',
    justifyContent: 'center', alignItems: 'center', marginRight: 6,
  },
  chipName: { fontSize: 13, fontWeight: '500', color: '#1f2937', maxWidth: 60 },
  listContent: { paddingVertical: 6 },
  card: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    marginHorizontal: 14, marginVertical: 3, padding: 14, borderRadius: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 2, elevation: 1,
  },
  cardAvatar: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: '#e0e7ff',
    justifyContent: 'center', alignItems: 'center', marginRight: 10,
  },
  cardInfo: { flex: 1 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 },
  cardName: { fontSize: 15, fontWeight: '600', color: '#1f2937', flex: 1 },
  cardTime: { fontSize: 11, color: '#9ca3af', marginLeft: 8 },
  cardPreview: { fontSize: 13, color: '#6b7280' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 60 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#4b5563', marginTop: 12 },
  emptySub: { fontSize: 13, color: '#9ca3af', marginTop: 4 },
  startBtn: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#6366f1',
    paddingHorizontal: 20, paddingVertical: 10, borderRadius: 20, marginTop: 20,
  },
  startBtnText: { color: '#fff', fontSize: 14, fontWeight: '600', marginLeft: 6 },
});
