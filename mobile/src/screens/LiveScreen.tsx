/**
 * 直播页面
 * 
 * 主要功能：
 * - 查看直播状态
 * - 连接直播平台
 * - 查看弹幕
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/Ionicons';
import { COLORS } from '../utils/constants';

interface Platform {
  id: string;
  name: string;
  icon: string;
  connected: boolean;
  roomId: string;
}

interface Danmaku {
  id: string;
  username: string;
  content: string;
  timestamp: Date;
}

const LiveScreen: React.FC = () => {
  const [platforms] = useState<Platform[]>([
    { id: 'bilibili', name: 'Bilibili', icon: 'tv-outline', connected: false, roomId: '' },
    { id: 'douyin', name: '抖音', icon: 'musical-notes-outline', connected: false, roomId: '' },
    { id: 'kuaishou', name: '快手', icon: 'videocam-outline', connected: false, roomId: '' },
    { id: 'douyu', name: '斗鱼', icon: 'fish-outline', connected: false, roomId: '' },
    { id: 'huya', name: '虎牙', icon: 'paw-outline', connected: false, roomId: '' },
    { id: 'youtube', name: 'YouTube', icon: 'logo-youtube', connected: false, roomId: '' },
    { id: 'twitch', name: 'Twitch', icon: 'logo-twitch', connected: false, roomId: '' },
  ]);

  const [danmakuList] = useState<Danmaku[]>([
    {
      id: '1',
      username: '用户A',
      content: '你好！',
      timestamp: new Date(),
    },
    {
      id: '2',
      username: '用户B',
      content: '主播好厉害',
      timestamp: new Date(Date.now() - 5000),
    },
  ]);

  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);

  // 连接平台
  const connectPlatform = (platformId: string) => {
    Alert.alert(
      '连接平台',
      `确定要连接到 ${platforms.find(p => p.id === platformId)?.name} 吗？`,
      [
        { text: '取消', style: 'cancel' },
        {
          text: '确定',
          onPress: () => {
            // TODO: 实现连接逻辑
            Alert.alert('提示', '连接功能开发中');
          },
        },
      ]
    );
  };

  const renderPlatform = ({ item }: { item: Platform }) => (
    <TouchableOpacity
      style={[
        styles.platformCard,
        selectedPlatform === item.id && styles.selectedCard,
      ]}
      onPress={() => setSelectedPlatform(item.id)}
    >
      <Icon name={item.icon} size={32} color={COLORS.primary} />
      <Text style={styles.platformName}>{item.name}</Text>
      <View
        style={[
          styles.statusDot,
          { backgroundColor: item.connected ? COLORS.success : COLORS.gray },
        ]}
      />
    </TouchableOpacity>
  );

  const renderDanmaku = ({ item }: { item: Danmaku }) => (
    <View style={styles.danmakuItem}>
      <Text style={styles.danmakuUser}>{item.username}:</Text>
      <Text style={styles.danmakuContent}>{item.content}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* 头部 */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>直播设置</Text>
      </View>

      {/* 平台选择 */}
      <View style={styles.platformSection}>
        <Text style={styles.sectionTitle}>选择平台</Text>
        <FlatList
          data={platforms}
          renderItem={renderPlatform}
          keyExtractor={item => item.id}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.platformList}
        />
      </View>

      {/* 连接状态 */}
      {selectedPlatform && (
        <View style={styles.connectionSection}>
          <Text style={styles.sectionTitle}>连接状态</Text>
          <View style={styles.connectionCard}>
            <View style={styles.connectionInfo}>
              <Text style={styles.connectionPlatform}>
                {platforms.find(p => p.id === selectedPlatform)?.name}
              </Text>
              <Text style={styles.connectionStatus}>
                {platforms.find(p => p.id === selectedPlatform)?.connected
                  ? '已连接'
                  : '未连接'}
              </Text>
            </View>
            <TouchableOpacity
              style={styles.connectButton}
              onPress={() => connectPlatform(selectedPlatform)}
            >
              <Text style={styles.connectButtonText}>连接</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* 弹幕预览 */}
      <View style={styles.danmakuSection}>
        <Text style={styles.sectionTitle}>弹幕预览</Text>
        <FlatList
          data={danmakuList}
          renderItem={renderDanmaku}
          keyExtractor={item => item.id}
          style={styles.danmakuList}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>暂无弹幕</Text>
            </View>
          }
        />
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: COLORS.white,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.text,
  },
  platformSection: {
    backgroundColor: COLORS.white,
    marginTop: 16,
    paddingVertical: 12,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  platformList: {
    paddingHorizontal: 12,
  },
  platformCard: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 80,
    height: 80,
    marginHorizontal: 4,
    backgroundColor: COLORS.background,
    borderRadius: 12,
  },
  selectedCard: {
    backgroundColor: COLORS.primaryLight,
    borderWidth: 2,
    borderColor: COLORS.primary,
  },
  platformName: {
    fontSize: 12,
    color: COLORS.text,
    marginTop: 4,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 4,
  },
  connectionSection: {
    backgroundColor: COLORS.white,
    marginTop: 16,
    padding: 16,
  },
  connectionCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: COLORS.background,
    borderRadius: 12,
    padding: 16,
  },
  connectionInfo: {
    flex: 1,
  },
  connectionPlatform: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.text,
  },
  connectionStatus: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginTop: 4,
  },
  connectButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  connectButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '600',
  },
  danmakuSection: {
    flex: 1,
    backgroundColor: COLORS.white,
    marginTop: 16,
  },
  danmakuList: {
    flex: 1,
    paddingHorizontal: 16,
  },
  danmakuItem: {
    flexDirection: 'row',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  danmakuUser: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
    marginRight: 8,
  },
  danmakuContent: {
    fontSize: 14,
    color: COLORS.text,
    flex: 1,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: 40,
  },
  emptyText: {
    fontSize: 14,
    color: COLORS.lightGray,
  },
});

export default LiveScreen;
