// ============================================
// 消息搜索页面
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, FlatList, TextInput,
  TouchableOpacity, Alert, Keyboard,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { messageSearchService, SearchResult, SearchFilter } from '../src/services/messageSearch';
import { useConversationStore, useCharacterStore } from '../src/stores';

// 搜索结果项
const SearchResultItem = React.memo(({ result, onPress }: { 
  result: SearchResult; 
  onPress: () => void;
}) => {
  const date = new Date(result.message.timestamp);
  const timeStr = `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
  
  return (
    <TouchableOpacity style={styles.resultItem} onPress={onPress} activeOpacity={0.7}>
      {/* 角色信息 */}
      <View style={styles.resultHeader}>
        <View style={styles.characterBadge}>
          <Ionicons name="person" size={12} color="#6366f1" />
          <Text style={styles.characterName} numberOfLines={1}>
            {result.character.name}
          </Text>
        </View>
        <Text style={styles.resultTime}>{timeStr}</Text>
      </View>
      
      {/* 消息内容 */}
      <Text style={styles.resultContent} numberOfLines={3}>
        {result.matchContext}
      </Text>
      
      {/* 匹配信息 */}
      <View style={styles.resultFooter}>
        <View style={styles.matchBadge}>
          <Ionicons name="search" size={10} color="#64748b" />
          <Text style={styles.matchText}>
            {result.message.role === 'user' ? '用户' : 'AI'}消息
          </Text>
        </View>
        <Text style={styles.scoreText}>匹配度: {Math.round(result.matchScore)}%</Text>
      </View>
    </TouchableOpacity>
  );
});

// 搜索历史项
const HistoryItem = React.memo(({ query, onPress, onDelete }: { 
  query: string; 
  onPress: () => void;
  onDelete: () => void;
}) => (
  <TouchableOpacity style={styles.historyItem} onPress={onPress} activeOpacity={0.7}>
    <Ionicons name="time" size={16} color="#9ca3af" />
    <Text style={styles.historyText} numberOfLines={1}>{query}</Text>
    <TouchableOpacity onPress={onDelete} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
      <Ionicons name="close" size={16} color="#d1d5db" />
    </TouchableOpacity>
  </TouchableOpacity>
));

export default function SearchPage() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { conversations } = useConversationStore();
  const { characters } = useCharacterStore();
  
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  
  // 搜索历史
  const searchHistory = useMemo(() => messageSearchService.getSearchHistory(), []);
  const popularSearches = useMemo(() => messageSearchService.getPopularSearches(), []);
  
  // 执行搜索
  const handleSearch = useCallback(async (searchQuery?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) {
      Alert.alert('提示', '请输入搜索关键词');
      return;
    }
    
    Keyboard.dismiss();
    setIsSearching(true);
    setHasSearched(true);
    
    try {
      const filter: SearchFilter = {
        query: q.trim(),
        limit: 50,
      };
      
      const searchResults = await messageSearchService.search(
        filter,
        conversations,
        characters
      );
      
      setResults(searchResults);
      
      if (searchResults.length === 0) {
        Alert.alert('搜索结果', '未找到匹配的消息');
      }
    } catch (error) {
      console.error('Search error:', error);
      Alert.alert('错误', '搜索失败');
    } finally {
      setIsSearching(false);
    }
  }, [query, conversations, characters]);
  
  // 点击搜索历史
  const handleHistoryPress = useCallback((historyQuery: string) => {
    setQuery(historyQuery);
    handleSearch(historyQuery);
  }, [handleSearch]);
  
  // 删除搜索历史
  const handleDeleteHistory = useCallback((historyQuery: string) => {
    // 这里可以实现删除单条历史
    // 暂时使用清除全部
  }, []);
  
  // 清除搜索历史
  const handleClearHistory = useCallback(() => {
    Alert.alert(
      '清除搜索历史',
      '确定要清除所有搜索历史吗？',
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '确定', 
          onPress: () => {
            messageSearchService.clearSearchHistory();
            // 刷新
          }
        },
      ]
    );
  }, []);
  
  // 点击搜索结果
  const handleResultPress = useCallback((result: SearchResult) => {
    // 跳转到对应的对话
    router.push({
      pathname: '/chat',
      params: { 
        characterId: result.character.id, 
        conversationId: result.conversation.id 
      },
    });
  }, [router]);
  
  // 渲染搜索结果
  const renderResult = useCallback(({ item }: { item: SearchResult }) => (
    <SearchResultItem
      result={item}
      onPress={() => handleResultPress(item)}
    />
  ), [handleResultPress]);
  
  // 渲染搜索历史
  const renderHistory = useCallback(() => {
    if (searchHistory.length === 0 && popularSearches.length === 0) {
      return null;
    }
    
    return (
      <View style={styles.historySection}>
        {/* 热门搜索 */}
        {popularSearches.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>热门搜索</Text>
            <View style={styles.popularTags}>
              {popularSearches.map((tag, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.popularTag}
                  onPress={() => {
                    setQuery(tag);
                    handleSearch(tag);
                  }}
                >
                  <Text style={styles.popularTagText}>{tag}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}
        
        {/* 搜索历史 */}
        {searchHistory.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>搜索历史</Text>
              <TouchableOpacity onPress={handleClearHistory}>
                <Text style={styles.clearText}>清除</Text>
              </TouchableOpacity>
            </View>
            {searchHistory.slice(0, 10).map((entry, index) => (
              <HistoryItem
                key={index}
                query={entry.query}
                onPress={() => handleHistoryPress(entry.query)}
                onDelete={() => handleDeleteHistory(entry.query)}
              />
            ))}
          </View>
        )}
      </View>
    );
  }, [searchHistory, popularSearches, handleHistoryPress, handleClearHistory]);
  
  // 渲染搜索统计
  const renderStats = useCallback(() => {
    if (!hasSearched) return null;
    
    const stats = messageSearchService.getSearchStats();
    
    return (
      <View style={styles.statsContainer}>
        <Text style={styles.statsText}>
          找到 {results.length} 条结果
        </Text>
        <Text style={styles.statsSubText}>
          共搜索 {stats.totalSearches} 次
        </Text>
      </View>
    );
  }, [hasSearched, results.length]);
  
  return (
    <>
      <Stack.Screen options={{ title: '搜索消息', headerShown: true }} />
      
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {/* 搜索栏 */}
        <View style={styles.searchBar}>
          <Ionicons name="search" size={18} color="#9ca3af" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            value={query}
            onChangeText={setQuery}
            placeholder="搜索对话历史..."
            placeholderTextColor="#9ca3af"
            returnKeyType="search"
            onSubmitEditing={() => handleSearch()}
            autoFocus
          />
          {query ? (
            <TouchableOpacity onPress={() => setQuery('')} style={styles.clearButton}>
              <Ionicons name="close-circle" size={18} color="#9ca3af" />
            </TouchableOpacity>
          ) : null}
          <TouchableOpacity 
            style={styles.searchButton} 
            onPress={() => handleSearch()}
            disabled={isSearching}
          >
            <Text style={styles.searchButtonText}>
              {isSearching ? '搜索中...' : '搜索'}
            </Text>
          </TouchableOpacity>
        </View>
        
        {/* 搜索统计 */}
        {renderStats()}
        
        {/* 内容区域 */}
        {hasSearched ? (
          <FlatList
            data={results}
            renderItem={renderResult}
            keyExtractor={(item) => item.message.id}
            contentContainerStyle={styles.resultsList}
            showsVerticalScrollIndicator={false}
            ListEmptyComponent={
              <View style={styles.empty}>
                <Ionicons name="search" size={48} color="#d1d5db" />
                <Text style={styles.emptyText}>未找到匹配的消息</Text>
                <Text style={styles.emptySubText}>尝试使用不同的关键词</Text>
              </View>
            }
          />
        ) : (
          <FlatList
            data={[]}
            renderItem={() => null}
            ListHeaderComponent={renderHistory}
            contentContainerStyle={styles.historyList}
          />
        )}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  
  // 搜索栏
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginTop: 12,
    marginBottom: 8,
    paddingHorizontal: 12,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    height: 44,
    fontSize: 15,
    color: '#1e293b',
  },
  clearButton: {
    padding: 4,
    marginRight: 8,
  },
  searchButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#6366f1',
    borderRadius: 8,
  },
  searchButtonText: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  
  // 统计
  statsContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  statsText: {
    fontSize: 13,
    color: '#64748b',
  },
  statsSubText: {
    fontSize: 11,
    color: '#9ca3af',
    marginTop: 2,
  },
  
  // 结果列表
  resultsList: {
    padding: 12,
  },
  resultItem: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  characterBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#eef2ff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  characterName: {
    fontSize: 12,
    color: '#6366f1',
    fontWeight: '500',
    maxWidth: 100,
  },
  resultTime: {
    fontSize: 11,
    color: '#9ca3af',
  },
  resultContent: {
    fontSize: 14,
    color: '#1e293b',
    lineHeight: 20,
    marginBottom: 8,
  },
  resultFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  matchBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  matchText: {
    fontSize: 11,
    color: '#64748b',
  },
  scoreText: {
    fontSize: 11,
    color: '#9ca3af',
  },
  
  // 历史
  historyList: {
    padding: 16,
  },
  historySection: {
    gap: 20,
  },
  section: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 12,
  },
  clearText: {
    fontSize: 13,
    color: '#6366f1',
  },
  popularTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  popularTag: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#f1f5f9',
    borderRadius: 16,
  },
  popularTagText: {
    fontSize: 13,
    color: '#64748b',
  },
  historyItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  historyText: {
    flex: 1,
    fontSize: 14,
    color: '#1e293b',
  },
  
  // 空状态
  empty: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 16,
    color: '#64748b',
    marginTop: 12,
  },
  emptySubText: {
    fontSize: 13,
    color: '#9ca3af',
    marginTop: 4,
  },
});
