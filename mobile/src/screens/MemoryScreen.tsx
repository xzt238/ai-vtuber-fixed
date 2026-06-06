/**
 * 记忆页面
 *
 * 查看记忆系统状态、浏览不同类型记忆
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/Ionicons';
import { COLORS } from '../utils/constants';
import { useMemoryStore, MemoryType } from '../store/memoryStore';

const TABS: { key: MemoryType; label: string; icon: string }[] = [
  { key: 'working', label: '工作记忆', icon: 'flash-outline' },
  { key: 'episodic', label: '情景记忆', icon: 'film-outline' },
  { key: 'semantic', label: '语义记忆', icon: 'library-outline' },
  { key: 'fact', label: '事实库', icon: 'document-text-outline' },
];

const MemoryScreen: React.FC = () => {
  const { activeTab, setActiveTab, getFilteredMemories, getStats, clearMemories } =
    useMemoryStore();

  const stats = getStats();
  const filteredMemories = getFilteredMemories();

  // 清空记忆
  const handleClearMemories = () => {
    Alert.alert('清空记忆', '确定要清空所有记忆吗？此操作不可恢复。', [
      { text: '取消', style: 'cancel' },
      {
        text: '确定清空',
        style: 'destructive',
        onPress: () => {
          clearMemories();
          Alert.alert('成功', '记忆已清空');
        },
      },
    ]);
  };

  // 渲染记忆项
  const renderMemoryItem = (item: (typeof filteredMemories)[0]) => (
    <View key={item.id} style={styles.memoryItem}>
      <View style={styles.memoryHeader}>
        <View style={styles.importanceBadge}>
          <Text style={styles.importanceText}>
            {Math.round(item.importance * 100)}%
          </Text>
        </View>
        <Text style={styles.memoryTime}>
          {new Date(item.timestamp).toLocaleString()}
        </Text>
      </View>
      <Text style={styles.memoryContent}>{item.content}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* 头部 */}
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <Text style={styles.headerTitle}>记忆系统</Text>
          <TouchableOpacity style={styles.clearButton} onPress={handleClearMemories}>
            <Icon name="trash-outline" size={20} color={COLORS.gray} />
          </TouchableOpacity>
        </View>
        <View style={styles.statsContainer}>
          {TABS.map((tab) => (
            <View key={tab.key} style={styles.statItem}>
              <Text style={styles.statNumber}>{stats[tab.key]}</Text>
              <Text style={styles.statLabel}>{tab.label.replace('记忆', '').replace('库', '')}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 标签页 */}
      <View style={styles.tabBar}>
        {TABS.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.activeTab]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Icon
              name={tab.icon}
              size={18}
              color={activeTab === tab.key ? COLORS.primary : COLORS.gray}
            />
            <Text
              style={[
                styles.tabText,
                activeTab === tab.key && styles.activeTabText,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* 记忆列表 */}
      <ScrollView style={styles.content}>
        {filteredMemories.length > 0 ? (
          filteredMemories.map(renderMemoryItem)
        ) : (
          <View style={styles.emptyContainer}>
            <Icon name="folder-open-outline" size={48} color={COLORS.lightGray} />
            <Text style={styles.emptyText}>暂无记忆</Text>
            <Text style={styles.emptySubtext}>
              对话过程中产生的记忆将在这里显示
            </Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    backgroundColor: COLORS.white,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.text,
  },
  clearButton: {
    padding: 4,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 24,
    fontWeight: '700',
    color: COLORS.primary,
  },
  statLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 4,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: COLORS.white,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    gap: 4,
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: COLORS.primary,
  },
  tabText: {
    fontSize: 11,
    color: COLORS.gray,
  },
  activeTabText: {
    color: COLORS.primary,
    fontWeight: '600',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  memoryItem: {
    backgroundColor: COLORS.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  memoryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  importanceBadge: {
    backgroundColor: COLORS.primaryLight,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  importanceText: {
    fontSize: 12,
    color: COLORS.primary,
    fontWeight: '600',
  },
  memoryTime: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  memoryContent: {
    fontSize: 16,
    color: COLORS.text,
    lineHeight: 22,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 60,
  },
  emptyText: {
    fontSize: 16,
    color: COLORS.lightGray,
    marginTop: 12,
  },
  emptySubtext: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginTop: 8,
  },
});

export default MemoryScreen;
