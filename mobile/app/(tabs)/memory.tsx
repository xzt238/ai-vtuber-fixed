// ============================================
// GuguGaga AI VTuber Mobile - 记忆 Tab（性能优化版）
// ============================================
import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, TextInput, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useMemoryStore, useCharacterStore } from '../../src/stores';
import type { Memory } from '../../src/types';

// 记忆卡片 memo
const MemoryCard = React.memo(({ item, onDelete }: { item: Memory; onDelete: () => void }) => (
  <TouchableOpacity style={styles.card} onLongPress={onDelete} activeOpacity={0.8}>
    <View style={styles.cardHeader}>
      <View style={styles.typeRow}>
        <Ionicons
          name={item.type === 'short_term' ? 'time' : item.type === 'long_term' ? 'infinite' : 'videocam'}
          size={14} color="#6366f1"
        />
        <Text style={styles.typeText}>
          {item.type === 'short_term' ? '短期' : item.type === 'long_term' ? '长期' : '情景'}
        </Text>
      </View>
      <View style={styles.stars}>
        {Array.from({ length: 5 }).map((_, i) => (
          <Ionicons key={i} name="star" size={10} color={i < item.importance ? '#f59e0b' : '#d1d5db'} />
        ))}
      </View>
    </View>
    <Text style={styles.cardContent} numberOfLines={3}>{item.content}</Text>
    <Text style={styles.cardTime}>{new Date(item.createdAt).toLocaleDateString()}</Text>
  </TouchableOpacity>
));

// 角色 Chip memo
const CharChip = React.memo(({ name, isSelected, onPress }: { name: string; isSelected: boolean; onPress: () => void }) => (
  <TouchableOpacity style={[styles.chip, isSelected && styles.chipSelected]} onPress={onPress} activeOpacity={0.7}>
    <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>{name}</Text>
  </TouchableOpacity>
));

export default function MemoryTab() {
  const insets = useSafeAreaInsets();
  const { memories, loadMemories, addMemory, deleteMemory } = useMemoryStore();
  const { characters, loadCharacters } = useCharacterStore();

  const [query, setQuery] = useState('');
  const [selectedCharId, setSelectedCharId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<'all' | 'short_term' | 'long_term' | 'episodic'>('all');

  useEffect(() => { loadCharacters(); }, []);
  useEffect(() => { if (selectedCharId) loadMemories(selectedCharId); }, [selectedCharId]);

  const filtered = useMemo(() =>
    memories.filter(m => {
      if (filterType !== 'all' && m.type !== filterType) return false;
      if (query && !m.content.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    }),
    [memories, filterType, query]
  );

  const handleAdd = useCallback(() => {
    if (!selectedCharId) { Alert.alert('提示', '请先选择角色'); return; }
    Alert.prompt('添加记忆', '输入内容', [
      { text: '取消', style: 'cancel' },
      { text: '添加', onPress: (content) => {
        if (content) {
          addMemory({ characterId: selectedCharId, content, importance: 5, type: 'long_term', tags: [] });
          Alert.alert('已添加');
        }
      }},
    ]);
  }, [selectedCharId, addMemory]);

  const handleDelete = useCallback((m: Memory) => {
    Alert.alert('删除', '确定删除？', [
      { text: '取消', style: 'cancel' },
      { text: '删除', style: 'destructive', onPress: () => deleteMemory(m.id) },
    ]);
  }, [deleteMemory]);

  const renderCard = useCallback(({ item }: { item: Memory }) => (
    <MemoryCard item={item} onDelete={() => handleDelete(item)} />
  ), [handleDelete]);

  const renderChip = useCallback(({ item }: { item: typeof characters[0] }) => (
    <CharChip name={item.name} isSelected={selectedCharId === item.id} onPress={() => setSelectedCharId(item.id)} />
  ), [selectedCharId]);

  const renderEmpty = useCallback(() => (
    <View style={styles.empty}>
      <Ionicons name="bulb" size={48} color="#d1d5db" />
      <Text style={styles.emptyTitle}>暂无记忆</Text>
      <Text style={styles.emptySub}>{selectedCharId ? '点击 + 添加记忆' : '选择角色查看'}</Text>
    </View>
  ), [selectedCharId]);

  const filterTypes: Array<{ key: typeof filterType; label: string }> = [
    { key: 'all', label: '全部' },
    { key: 'short_term', label: '短期' },
    { key: 'long_term', label: '长期' },
    { key: 'episodic', label: '情景' },
  ];

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.title}>记忆库</Text>
        <TouchableOpacity style={styles.addBtn} onPress={handleAdd} activeOpacity={0.7}>
          <Ionicons name="add" size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* 角色选择 */}
      <View style={styles.chipBar}>
        <FlatList
          data={characters}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={(item) => item.id}
          renderItem={renderChip}
          contentContainerStyle={styles.chipList}
          removeClippedSubviews={true}
        />
      </View>

      {/* 搜索 */}
      <View style={styles.searchBar}>
        <Ionicons name="search" size={18} color="#9ca3af" />
        <TextInput style={styles.searchInput} value={query} onChangeText={setQuery}
          placeholder="搜索记忆..." placeholderTextColor="#9ca3af" />
      </View>

      {/* 筛选 */}
      <View style={styles.filterBar}>
        {filterTypes.map(f => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterChip, filterType === f.key && styles.filterChipActive]}
            onPress={() => setFilterType(f.key)}
            activeOpacity={0.7}
          >
            <Text style={[styles.filterText, filterType === f.key && styles.filterTextActive]}>{f.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* 列表 */}
      <FlatList
        data={filtered}
        renderItem={renderCard}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={renderEmpty}
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
  title: { fontSize: 22, fontWeight: '700', color: '#1f2937' },
  addBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#6366f1', justifyContent: 'center', alignItems: 'center' },
  chipBar: { backgroundColor: '#fff', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#e5e7eb' },
  chipList: { paddingHorizontal: 10 },
  chip: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 16, backgroundColor: '#f3f4f6', marginHorizontal: 4 },
  chipSelected: { backgroundColor: '#6366f1' },
  chipText: { fontSize: 13, fontWeight: '500', color: '#4b5563' },
  chipTextSelected: { color: '#fff' },
  searchBar: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    marginHorizontal: 14, marginVertical: 10, borderRadius: 10, paddingHorizontal: 12,
  },
  searchInput: { flex: 1, height: 40, fontSize: 15, color: '#1f2937', marginLeft: 8 },
  filterBar: { flexDirection: 'row', paddingHorizontal: 14, marginBottom: 8 },
  filterChip: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 14, backgroundColor: '#f3f4f6', marginRight: 6 },
  filterChipActive: { backgroundColor: '#e0e7ff' },
  filterText: { fontSize: 12, fontWeight: '500', color: '#6b7280' },
  filterTextActive: { color: '#6366f1' },
  listContent: { paddingVertical: 6 },
  card: { backgroundColor: '#fff', marginHorizontal: 14, marginVertical: 3, padding: 14, borderRadius: 10, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 2, elevation: 1 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  typeRow: { flexDirection: 'row', alignItems: 'center' },
  typeText: { fontSize: 11, color: '#6366f1', marginLeft: 4, fontWeight: '500' },
  stars: { flexDirection: 'row' },
  cardContent: { fontSize: 14, color: '#1f2937', lineHeight: 20, marginBottom: 6 },
  cardTime: { fontSize: 11, color: '#9ca3af' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 60 },
  emptyTitle: { fontSize: 17, fontWeight: '600', color: '#4b5563', marginTop: 12 },
  emptySub: { fontSize: 13, color: '#9ca3af', marginTop: 4 },
});
