// ============================================
// 模型选择页面
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Image, Alert, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { modelManager, ModelConfig, PRESET_MODELS } from '../src/services/modelManager';

// 模型卡片组件
const ModelCard = React.memo(({ model, isSelected, isDownloaded, onSelect, onDownload }: {
  model: ModelConfig;
  isSelected: boolean;
  isDownloaded: boolean;
  onSelect: () => void;
  onDownload: () => void;
}) => {
  const [loading, setLoading] = useState(false);
  
  const handlePress = useCallback(async () => {
    if (isDownloaded || model.isDefault) {
      onSelect();
    } else {
      setLoading(true);
      await onDownload();
      setLoading(false);
    }
  }, [isDownloaded, model.isDefault, onSelect, onDownload]);
  
  return (
    <TouchableOpacity
      style={[styles.card, isSelected && styles.cardSelected]}
      onPress={handlePress}
      activeOpacity={0.7}
    >
      {/* 缩略图 */}
      <View style={styles.thumbnailContainer}>
        <Image
          source={{ uri: model.thumbnail }}
          style={styles.thumbnail}
          defaultSource={{ uri: 'https://img.icons8.com/color/96/000000/user-male-circle.png' }}
        />
        {isSelected && (
          <View style={styles.selectedBadge}>
            <Ionicons name="checkmark-circle" size={24} color="#10b981" />
          </View>
        )}
        {!isDownloaded && !model.isDefault && (
          <View style={styles.downloadBadge}>
            <Ionicons name="cloud-download" size={16} color="#fff" />
          </View>
        )}
      </View>
      
      {/* 信息 */}
      <View style={styles.info}>
        <Text style={styles.name} numberOfLines={1}>{model.name}</Text>
        {model.nameJa && (
          <Text style={styles.nameSub} numberOfLines={1}>{model.nameJa}</Text>
        )}
        <Text style={styles.author} numberOfLines={1}>by {model.author}</Text>
        
        {/* 标签 */}
        <View style={styles.tags}>
          {model.tags.slice(0, 2).map((tag, i) => (
            <View key={i} style={styles.tag}>
              <Text style={styles.tagText}>{tag}</Text>
            </View>
          ))}
          <View style={[styles.tag, styles.typeTag]}>
            <Text style={styles.typeTagText}>{model.type.toUpperCase()}</Text>
          </View>
        </View>
        
        {/* 状态 */}
        <View style={styles.status}>
          {isDownloaded || model.isDefault ? (
            <View style={styles.statusReady}>
              <Ionicons name="checkmark-circle" size={12} color="#10b981" />
              <Text style={styles.statusReadyText}>可用</Text>
            </View>
          ) : loading ? (
            <ActivityIndicator size="small" color="#6366f1" />
          ) : (
            <View style={styles.statusDownload}>
              <Ionicons name="download" size={12} color="#6366f1" />
              <Text style={styles.statusDownloadText}>点击下载</Text>
            </View>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
});

export default function ModelSelectPage() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const [currentModelId, setCurrentModelId] = useState<string | null>(
    modelManager.getCurrentModel()?.id || null
  );
  const [downloading, setDownloading] = useState<Set<string>>(new Set());
  
  // 获取模型列表
  const models = useMemo(() => {
    return PRESET_MODELS.map(model => ({
      ...model,
      isDownloaded: modelManager.isModelDownloaded(model.id) || model.isDefault,
    }));
  }, []);
  
  // 选择模型
  const handleSelect = useCallback(async (modelId: string) => {
    const success = await modelManager.setCurrentModel(modelId);
    if (success) {
      setCurrentModelId(modelId);
      Alert.alert('成功', '模型已切换', [
        { text: '确定', onPress: () => router.back() }
      ]);
    } else {
      Alert.alert('错误', '模型切换失败');
    }
  }, [router]);
  
  // 下载模型
  const handleDownload = useCallback(async (modelId: string) => {
    setDownloading(prev => new Set(prev).add(modelId));
    
    const success = await modelManager.downloadModel(modelId);
    
    setDownloading(prev => {
      const next = new Set(prev);
      next.delete(modelId);
      return next;
    });
    
    if (success) {
      await handleSelect(modelId);
    } else {
      Alert.alert('错误', '模型下载失败');
    }
  }, [handleSelect]);
  
  // 渲染模型卡片
  const renderItem = useCallback(({ item }: { item: ModelConfig & { isDownloaded?: boolean } }) => (
    <ModelCard
      model={item}
      isSelected={currentModelId === item.id}
      isDownloaded={item.isDownloaded || false}
      onSelect={() => handleSelect(item.id)}
      onDownload={() => handleDownload(item.id)}
    />
  ), [currentModelId, handleSelect, handleDownload]);
  
  // 提取 key
  const keyExtractor = useCallback((item: ModelConfig) => item.id, []);
  
  return (
    <>
      <Stack.Screen options={{ title: '选择模型', headerShown: true }} />
      
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {/* 说明 */}
        <View style={styles.header}>
          <Ionicons name="cube" size={20} color="#6366f1" />
          <Text style={styles.headerText}>
            选择你的虚拟形象，支持 Live2D 和 VRM 3D 模型
          </Text>
        </View>
        
        {/* 模型列表 */}
        <FlatList
          data={models}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          numColumns={2}
          contentContainerStyle={styles.list}
          columnWrapperStyle={styles.row}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="cube-outline" size={48} color="#d1d5db" />
              <Text style={styles.emptyText}>暂无模型</Text>
            </View>
          }
        />
        
        {/* 底部操作 */}
        <View style={[styles.footer, { paddingBottom: insets.bottom + 16 }]}>
          <TouchableOpacity
            style={styles.footerButton}
            onPress={() => Alert.alert('提示', '自定义模型上传功能即将开放')}
          >
            <Ionicons name="add-circle" size={20} color="#6366f1" />
            <Text style={styles.footerButtonText}>导入自定义模型</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={styles.footerButton}
            onPress={() => Alert.alert('提示', '模型市场功能即将开放')}
          >
            <Ionicons name="storefront" size={20} color="#6366f1" />
            <Text style={styles.footerButtonText}>模型市场</Text>
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 16,
    backgroundColor: '#eef2ff',
    borderBottomWidth: 1,
    borderBottomColor: '#c7d2fe',
  },
  headerText: {
    flex: 1,
    fontSize: 13,
    color: '#4f46e5',
  },
  list: {
    padding: 12,
  },
  row: {
    justifyContent: 'space-between',
  },
  card: {
    width: '48%',
    backgroundColor: '#fff',
    borderRadius: 16,
    marginBottom: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardSelected: {
    borderWidth: 2,
    borderColor: '#6366f1',
  },
  thumbnailContainer: {
    position: 'relative',
    width: '100%',
    height: 150,
    backgroundColor: '#f1f5f9',
  },
  thumbnail: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  selectedBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
  downloadBadge: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    backgroundColor: '#6366f1',
    borderRadius: 12,
    padding: 4,
  },
  info: {
    padding: 12,
  },
  name: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1e293b',
  },
  nameSub: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
  },
  author: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 4,
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 8,
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
  typeTag: {
    backgroundColor: '#eef2ff',
  },
  typeTagText: {
    fontSize: 10,
    color: '#6366f1',
    fontWeight: '600',
  },
  status: {
    marginTop: 8,
    height: 20,
    justifyContent: 'center',
  },
  statusReady: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statusReadyText: {
    fontSize: 11,
    color: '#10b981',
  },
  statusDownload: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statusDownloadText: {
    fontSize: 11,
    color: '#6366f1',
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
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  footerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 16,
    backgroundColor: '#eef2ff',
    borderRadius: 20,
  },
  footerButtonText: {
    fontSize: 13,
    color: '#6366f1',
    fontWeight: '500',
  },
});
