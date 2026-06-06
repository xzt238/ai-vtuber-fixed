// ============================================
// 角色市场页面
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Image, TextInput, ScrollView, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { characterMarket, MarketCharacter } from '../src/services/characterMarket';
import { useCharacterStore } from '../src/stores';

// 角色卡片组件
const CharacterCard = React.memo(({ character, isLiked, isDownloaded, onLike, onDownload, onPress }: {
  character: MarketCharacter;
  isLiked: boolean;
  isDownloaded: boolean;
  onLike: () => void;
  onDownload: () => void;
  onPress: () => void;
}) => (
  <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
    {/* 头像 */}
    <Image source={{ uri: character.avatar }} style={styles.avatar} />
    
    {/* 信息 */}
    <View style={styles.info}>
      <View style={styles.nameRow}>
        <Text style={styles.name} numberOfLines={1}>{character.name}</Text>
        {character.isVerified && (
          <Ionicons name="checkmark-circle" size={14} color="#6366f1" />
        )}
      </View>
      
      <Text style={styles.description} numberOfLines={2}>{character.description}</Text>
      
      {/* 标签 */}
      <View style={styles.tags}>
        {character.tags.slice(0, 3).map((tag, i) => (
          <View key={i} style={styles.tag}>
            <Text style={styles.tagText}>{tag}</Text>
          </View>
        ))}
      </View>
      
      {/* 统计 */}
      <View style={styles.stats}>
        <View style={styles.stat}>
          <Ionicons name="download" size={12} color="#64748b" />
          <Text style={styles.statText}>{formatNumber(character.downloadCount)}</Text>
        </View>
        <View style={styles.stat}>
          <Ionicons name="star" size={12} color="#f59e0b" />
          <Text style={styles.statText}>{character.rating}</Text>
        </View>
        <View style={styles.stat}>
          <Ionicons name="person" size={12} color="#64748b" />
          <Text style={styles.statText}>{character.author}</Text>
        </View>
      </View>
    </View>
    
    {/* 操作按钮 */}
    <View style={styles.actions}>
      <TouchableOpacity style={styles.actionButton} onPress={onLike}>
        <Ionicons 
          name={isLiked ? 'heart' : 'heart-outline'} 
          size={20} 
          color={isLiked ? '#ef4444' : '#9ca3af'} 
        />
        <Text style={[styles.actionText, isLiked && styles.actionTextLiked]}>
          {formatNumber(character.likeCount + (isLiked ? 1 : 0))}
        </Text>
      </TouchableOpacity>
      
      <TouchableOpacity 
        style={[styles.downloadButton, isDownloaded && styles.downloadButtonDone]} 
        onPress={onDownload}
        disabled={isDownloaded}
      >
        <Ionicons 
          name={isDownloaded ? 'checkmark' : 'download'} 
          size={16} 
          color="#fff" 
        />
        <Text style={styles.downloadButtonText}>
          {isDownloaded ? '已添加' : '添加'}
        </Text>
      </TouchableOpacity>
    </View>
  </TouchableOpacity>
));

// 格式化数字
function formatNumber(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

export default function CharacterMarketPage() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { addCharacter } = useCharacterStore();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [liked, setLiked] = useState<Set<string>>(new Set());
  const [downloaded, setDownloaded] = useState<Set<string>>(new Set());
  
  // 获取标签列表
  const tags = useMemo(() => characterMarket.getAllTags(), []);
  
  // 获取角色列表
  const characters = useMemo(() => {
    let list = characterMarket.getPublicCharacters();
    
    // 搜索过滤
    if (searchQuery) {
      list = characterMarket.searchCharacters(searchQuery);
    }
    
    // 标签过滤
    if (selectedTag) {
      list = list.filter(c => c.tags.includes(selectedTag));
    }
    
    return list;
  }, [searchQuery, selectedTag]);
  
  // 点赞
  const handleLike = useCallback((id: string) => {
    setLiked(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        characterMarket.unlikeCharacter(id);
      } else {
        next.add(id);
        characterMarket.likeCharacter(id);
      }
      return next;
    });
  }, []);
  
  // 下载/添加角色
  const handleDownload = useCallback((character: MarketCharacter) => {
    if (downloaded.has(character.id)) {
      return;
    }
    
    Alert.alert(
      '添加角色',
      `确定要添加 "${character.name}" 吗？`,
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '确定', 
          onPress: () => {
            // 添加到本地角色库
            addCharacter({
              name: character.name,
              avatar: character.avatar,
              description: character.description,
              personality: character.personality,
              systemPrompt: character.prompt || '',
              greeting: `你好！我是${character.name}。${character.description}`,
              tags: character.tags,
            });
            
            characterMarket.downloadCharacter(character.id);
            setDownloaded(prev => new Set(prev).add(character.id));
            
            Alert.alert('成功', `"${character.name}" 已添加到你的角色库`);
          }
        },
      ]
    );
  }, [downloaded, addCharacter]);
  
  // 点击角色卡片
  const handlePress = useCallback((character: MarketCharacter) => {
    Alert.alert(
      character.name,
      `${character.description}\n\n性格：${character.personality}\n\n作者：${character.author}\n下载：${formatNumber(character.downloadCount)}\n评分：${character.rating}/5`,
      [
        { text: '关闭', style: 'cancel' },
        { text: '添加角色', onPress: () => handleDownload(character) },
      ]
    );
  }, [handleDownload]);
  
  // 渲染角色卡片
  const renderItem = useCallback(({ item }: { item: MarketCharacter }) => (
    <CharacterCard
      character={item}
      isLiked={liked.has(item.id)}
      isDownloaded={downloaded.has(item.id)}
      onLike={() => handleLike(item.id)}
      onDownload={() => handleDownload(item)}
      onPress={() => handlePress(item)}
    />
  ), [liked, downloaded, handleLike, handleDownload, handlePress]);
  
  // 提取 key
  const keyExtractor = useCallback((item: MarketCharacter) => item.id, []);
  
  return (
    <>
      <Stack.Screen options={{ title: '角色市场', headerShown: true }} />
      
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {/* 搜索栏 */}
        <View style={styles.searchContainer}>
          <Ionicons name="search" size={18} color="#9ca3af" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder="搜索角色..."
            placeholderTextColor="#9ca3af"
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
          {searchQuery ? (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={18} color="#9ca3af" />
            </TouchableOpacity>
          ) : null}
        </View>
        
        {/* 标签筛选 */}
        <ScrollView 
          horizontal 
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.tagsContainer}
        >
          <TouchableOpacity
            style={[styles.filterTag, !selectedTag && styles.filterTagActive]}
            onPress={() => setSelectedTag(null)}
          >
            <Text style={[styles.filterTagText, !selectedTag && styles.filterTagTextActive]}>
              全部
            </Text>
          </TouchableOpacity>
          
          {tags.map(tag => (
            <TouchableOpacity
              key={tag}
              style={[styles.filterTag, selectedTag === tag && styles.filterTagActive]}
              onPress={() => setSelectedTag(selectedTag === tag ? null : tag)}
            >
              <Text style={[styles.filterTagText, selectedTag === tag && styles.filterTagTextActive]}>
                {tag}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        
        {/* 角色列表 */}
        <FlatList
          data={characters}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="people" size={48} color="#d1d5db" />
              <Text style={styles.emptyText}>
                {searchQuery ? '未找到匹配的角色' : '暂无角色'}
              </Text>
            </View>
          }
        />
        
        {/* 底部操作 */}
        <View style={[styles.footer, { paddingBottom: insets.bottom + 16 }]}>
          <TouchableOpacity
            style={styles.footerButton}
            onPress={() => Alert.alert('提示', '创建角色功能即将开放')}
          >
            <Ionicons name="add-circle" size={20} color="#6366f1" />
            <Text style={styles.footerButtonText}>创建我的角色</Text>
          </TouchableOpacity>
        </View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  searchContainer: {
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
    height: 40,
    fontSize: 14,
    color: '#1e293b',
  },
  tagsContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  filterTag: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  filterTagActive: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  filterTagText: {
    fontSize: 13,
    color: '#64748b',
  },
  filterTagTextActive: {
    color: '#fff',
    fontWeight: '500',
  },
  list: {
    padding: 12,
  },
  card: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#f1f5f9',
  },
  info: {
    flex: 1,
    marginLeft: 12,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
  },
  description: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 4,
    lineHeight: 16,
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 6,
  },
  tag: {
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  tagText: {
    fontSize: 10,
    color: '#64748b',
  },
  stats: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 6,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  statText: {
    fontSize: 11,
    color: '#64748b',
  },
  actions: {
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginLeft: 8,
  },
  actionButton: {
    alignItems: 'center',
  },
  actionText: {
    fontSize: 10,
    color: '#9ca3af',
    marginTop: 2,
  },
  actionTextLiked: {
    color: '#ef4444',
  },
  downloadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#6366f1',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  downloadButtonDone: {
    backgroundColor: '#10b981',
  },
  downloadButtonText: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '500',
  },
  empty: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 14,
    color: '#9ca3af',
    marginTop: 12,
  },
  footer: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  footerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    backgroundColor: '#eef2ff',
    borderRadius: 12,
  },
  footerButtonText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '600',
  },
});
