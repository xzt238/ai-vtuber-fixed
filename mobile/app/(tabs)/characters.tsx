// ============================================
// GuguGaga AI VTuber Mobile - 角色 Tab（性能优化版）
// ============================================
import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { SearchBar } from '../../src/components/SearchBar';
import { useCharacterStore, useConversationStore } from '../../src/stores';
import { DEFAULT_CHARACTERS } from '../../src/utils/constants';
import type { Character } from '../../src/types';

// 角色卡片 memo
const CharacterItem = React.memo(({ item, onChat, onDelete }: {
  item: Character; onChat: () => void; onDelete: () => void;
}) => (
  <TouchableOpacity style={styles.card} onPress={onChat} onLongPress={onDelete} activeOpacity={0.7}>
    <View style={styles.cardAvatar}>
      <Ionicons name="person" size={24} color="#6366f1" />
    </View>
    <View style={styles.cardInfo}>
      <Text style={styles.cardName} numberOfLines={1}>{item.name}</Text>
      <Text style={styles.cardDesc} numberOfLines={1}>{item.description}</Text>
      {item.tags.length > 0 && (
        <View style={styles.tagsRow}>
          {item.tags.slice(0, 2).map((tag, i) => (
            <View key={i} style={styles.tag}><Text style={styles.tagText}>{tag}</Text></View>
          ))}
        </View>
      )}
    </View>
    <TouchableOpacity style={styles.chatBtn} onPress={onChat} activeOpacity={0.7}>
      <Ionicons name="chatbubble" size={16} color="#fff" />
    </TouchableOpacity>
  </TouchableOpacity>
));

// 预设角色 memo
const DefaultCard = React.memo(({ item, onAdd }: { item: typeof DEFAULT_CHARACTERS[0]; onAdd: () => void }) => (
  <TouchableOpacity style={styles.defaultCard} onPress={onAdd} activeOpacity={0.7}>
    <View style={styles.defaultAvatar}>
      <Ionicons name="person-add" size={20} color="#6366f1" />
    </View>
    <Text style={styles.defaultName} numberOfLines={1}>{item.name}</Text>
  </TouchableOpacity>
));

export default function CharactersTab() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [query, setQuery] = useState('');

  const { characters, loadCharacters, addCharacter, deleteCharacter } = useCharacterStore();
  const { createConversation } = useConversationStore();

  useEffect(() => { loadCharacters(); }, []);

  const filtered = useMemo(() =>
    characters.filter(c =>
      c.name.toLowerCase().includes(query.toLowerCase()) ||
      c.description.toLowerCase().includes(query.toLowerCase())
    ),
    [characters, query]
  );

  const handleChat = useCallback((character: Character) => {
    const conv = createConversation(character.id);
    router.push({ pathname: '/chat', params: { characterId: character.id, conversationId: conv.id } });
  }, [router, createConversation]);

  const handleDelete = useCallback((character: Character) => {
    Alert.alert('删除角色', `确定删除 "${character.name}"？`, [
      { text: '取消', style: 'cancel' },
      { text: '删除', style: 'destructive', onPress: () => deleteCharacter(character.id) },
    ]);
  }, [deleteCharacter]);

  const handleAddDefault = useCallback((data: typeof DEFAULT_CHARACTERS[0]) => {
    addCharacter({
      name: data.name, avatar: '', description: data.description,
      personality: data.personality, systemPrompt: data.systemPrompt,
      greeting: data.greeting, tags: data.tags, voiceId: '',
    });
    Alert.alert('成功', `"${data.name}" 已添加`);
  }, [addCharacter]);

  const renderItem = useCallback(({ item }: { item: Character }) => (
    <CharacterItem
      item={item}
      onChat={() => handleChat(item)}
      onDelete={() => handleDelete(item)}
    />
  ), [handleChat, handleDelete]);

  const renderDefault = useCallback(({ item }: { item: typeof DEFAULT_CHARACTERS[0] }) => (
    <DefaultCard item={item} onAdd={() => handleAddDefault(item)} />
  ), [handleAddDefault]);

  const renderEmpty = useCallback(() => (
    <View style={styles.empty}>
      <Ionicons name="people" size={48} color="#d1d5db" />
      <Text style={styles.emptyTitle}>还没有角色</Text>
      <Text style={styles.emptySub}>从预设角色中选择</Text>
    </View>
  ), []);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.title}>角色列表</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity 
            style={styles.headerBtn} 
            onPress={() => router.push('/character-market')} 
            activeOpacity={0.7}
          >
            <Ionicons name="storefront" size={20} color="#6366f1" />
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.headerBtn} 
            onPress={() => router.push('/voice-call')} 
            activeOpacity={0.7}
          >
            <Ionicons name="call" size={20} color="#6366f1" />
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.headerBtn} 
            onPress={() => router.push('/game-assistant')} 
            activeOpacity={0.7}
          >
            <Ionicons name="game-controller" size={20} color="#6366f1" />
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.headerBtn} 
            onPress={() => router.push('/group-chat')} 
            activeOpacity={0.7}
          >
            <Ionicons name="people" size={20} color="#6366f1" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.addBtn} onPress={() => router.push('/character-editor')} activeOpacity={0.7}>
            <Ionicons name="add" size={22} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>

      <SearchBar value={query} onChangeText={setQuery} placeholder="搜索角色..." />

      {/* 预设角色 */}
      {characters.length === 0 && (
        <View style={styles.defaultsSection}>
          <Text style={styles.sectionLabel}>预设角色</Text>
          <FlatList
            data={DEFAULT_CHARACTERS}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(item) => item.name}
            renderItem={renderDefault}
            contentContainerStyle={styles.defaultList}
            removeClippedSubviews={true}
          />
        </View>
      )}

      <FlatList
        data={filtered}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={characters.length > 0 ? renderEmpty : undefined}
        showsVerticalScrollIndicator={false}
        removeClippedSubviews={true}
        maxToRenderPerBatch={10}
        windowSize={8}
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
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerBtn: {
    width: 36, height: 36, borderRadius: 18, backgroundColor: '#eef2ff',
    justifyContent: 'center', alignItems: 'center',
  },
  title: { fontSize: 22, fontWeight: '700', color: '#1f2937' },
  addBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#6366f1', justifyContent: 'center', alignItems: 'center' },
  defaultsSection: { paddingVertical: 12 },
  sectionLabel: { fontSize: 13, fontWeight: '600', color: '#6b7280', marginHorizontal: 18, marginBottom: 8 },
  defaultList: { paddingHorizontal: 10 },
  defaultCard: {
    width: 80, alignItems: 'center', backgroundColor: '#fff', borderRadius: 12,
    padding: 10, marginHorizontal: 6,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 2, elevation: 1,
  },
  defaultAvatar: {
    width: 40, height: 40, borderRadius: 20, backgroundColor: '#e0e7ff',
    justifyContent: 'center', alignItems: 'center', marginBottom: 6,
  },
  defaultName: { fontSize: 12, fontWeight: '500', color: '#1f2937', textAlign: 'center' },
  listContent: { paddingVertical: 6 },
  card: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    marginHorizontal: 14, marginVertical: 3, padding: 14, borderRadius: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 2, elevation: 1,
  },
  cardAvatar: {
    width: 48, height: 48, borderRadius: 24, backgroundColor: '#e0e7ff',
    justifyContent: 'center', alignItems: 'center', marginRight: 10,
  },
  cardInfo: { flex: 1 },
  cardName: { fontSize: 15, fontWeight: '700', color: '#1f2937', marginBottom: 2 },
  cardDesc: { fontSize: 12, color: '#6b7280', marginBottom: 4 },
  tagsRow: { flexDirection: 'row' },
  tag: { backgroundColor: '#e0e7ff', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 8, marginRight: 4 },
  tagText: { fontSize: 10, color: '#6366f1', fontWeight: '500' },
  chatBtn: {
    width: 36, height: 36, borderRadius: 18, backgroundColor: '#6366f1',
    justifyContent: 'center', alignItems: 'center', marginLeft: 8,
  },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 60 },
  emptyTitle: { fontSize: 17, fontWeight: '600', color: '#4b5563', marginTop: 12 },
  emptySub: { fontSize: 13, color: '#9ca3af', marginTop: 4 },
});
