// ============================================
// GuguGaga AI VTuber Mobile - 直播 Tab（性能优化版）
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Switch, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useSettingsStore } from '../../src/stores';
import { LIVE_PLATFORMS } from '../../src/utils/constants';

// 平台卡片 memo
const PlatformCard = React.memo(({ platform, isSelected, onPress }: {
  platform: typeof LIVE_PLATFORMS[0]; isSelected: boolean; onPress: () => void;
}) => (
  <TouchableOpacity
    style={[styles.platformCard, isSelected && styles.platformCardSelected]}
    onPress={onPress} activeOpacity={0.7}
  >
    <View style={[styles.platformIcon, { backgroundColor: platform.color }]}>
      <Ionicons name="videocam" size={16} color="#fff" />
    </View>
    <Text style={styles.platformName} numberOfLines={1}>{platform.label}</Text>
    {isSelected && <Ionicons name="checkmark-circle" size={14} color="#6366f1" />}
  </TouchableOpacity>
));

export default function LiveTab() {
  const insets = useSafeAreaInsets();
  const { settings, updateLiveConfig } = useSettingsStore();
  const [isLive, setIsLive] = useState(false);

  const currentPlatform = useMemo(() => LIVE_PLATFORMS.find(p => p.value === settings.live.platform), [settings.live.platform]);

  const handleToggle = useCallback(() => {
    if (!settings.live.roomId) {
      Alert.alert('提示', '请先在设置页面配置房间号');
      return;
    }
    if (isLive) {
      Alert.alert('停止直播', '确定停止？', [
        { text: '取消', style: 'cancel' },
        { text: '停止', style: 'destructive', onPress: () => setIsLive(false) },
      ]);
    } else {
      setIsLive(true);
    }
  }, [isLive, settings.live]);

  const renderPlatform = useCallback((platform: typeof LIVE_PLATFORMS[0]) => (
    <PlatformCard
      key={platform.value}
      platform={platform}
      isSelected={settings.live.platform === platform.value}
      onPress={() => updateLiveConfig({ platform: platform.value as any })}
    />
  ), [settings.live.platform, updateLiveConfig]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.title}>直播控制</Text>
        <View style={styles.indicator}>
          <View style={[styles.dot, isLive && styles.dotActive]} />
          <Text style={[styles.indicatorText, isLive && styles.indicatorTextActive]}>
            {isLive ? '直播中' : '未开播'}
          </Text>
        </View>
      </View>

      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* 控制按钮 */}
        <View style={styles.controlSection}>
          <TouchableOpacity style={[styles.liveBtn, isLive && styles.liveBtnActive]} onPress={handleToggle} activeOpacity={0.8}>
            <Ionicons name={isLive ? 'stop' : 'videocam'} size={28} color="#fff" />
            <Text style={styles.liveBtnText}>{isLive ? '停止' : '开播'}</Text>
          </TouchableOpacity>
        </View>

        {/* 平台选择 */}
        <Text style={styles.sectionLabel}>直播平台</Text>
        <View style={styles.platformGrid}>
          {LIVE_PLATFORMS.map(renderPlatform)}
        </View>

        {/* 设置 */}
        <Text style={styles.sectionLabel}>设置</Text>
        <View style={styles.settingsSection}>
          <View style={styles.settingRow}>
            <View style={styles.settingLeft}>
              <Ionicons name="home" size={18} color="#6366f1" />
              <Text style={styles.settingLabel}>房间号</Text>
            </View>
            <Text style={styles.settingValue}>{settings.live.roomId || '未设置'}</Text>
          </View>
          <View style={styles.settingRow}>
            <View style={styles.settingLeft}>
              <Ionicons name="chatbubbles" size={18} color="#6366f1" />
              <Text style={styles.settingLabel}>自动回复</Text>
            </View>
            <Switch
              value={settings.live.autoReply}
              onValueChange={(v) => updateLiveConfig({ autoReply: v })}
              trackColor={{ false: '#d1d5db', true: '#a5b4fc' }}
              thumbColor={settings.live.autoReply ? '#6366f1' : '#f4f3f4'}
            />
          </View>
          <View style={styles.settingRow}>
            <View style={styles.settingLeft}>
              <Ionicons name="gift" size={18} color="#6366f1" />
              <Text style={styles.settingLabel}>礼物感谢</Text>
            </View>
            <Switch
              value={settings.live.giftThanks}
              onValueChange={(v) => updateLiveConfig({ giftThanks: v })}
              trackColor={{ false: '#d1d5db', true: '#a5b4fc' }}
              thumbColor={settings.live.giftThanks ? '#6366f1' : '#f4f3f4'}
            />
          </View>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
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
  indicator: { flexDirection: 'row', alignItems: 'center' },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#9ca3af', marginRight: 6 },
  dotActive: { backgroundColor: '#ef4444' },
  indicatorText: { fontSize: 13, color: '#9ca3af' },
  indicatorTextActive: { color: '#ef4444', fontWeight: '600' },
  scroll: { flex: 1 },
  controlSection: { padding: 18, alignItems: 'center' },
  liveBtn: {
    width: 100, height: 100, borderRadius: 50, backgroundColor: '#6366f1',
    justifyContent: 'center', alignItems: 'center',
    shadowColor: '#6366f1', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.3, shadowRadius: 6, elevation: 5,
  },
  liveBtnActive: { backgroundColor: '#ef4444', shadowColor: '#ef4444' },
  liveBtnText: { color: '#fff', fontSize: 13, fontWeight: '600', marginTop: 4 },
  sectionLabel: { fontSize: 12, fontWeight: '600', color: '#6b7280', marginHorizontal: 18, marginTop: 18, marginBottom: 8, textTransform: 'uppercase' },
  platformGrid: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: 10 },
  platformCard: {
    width: '30%', margin: '1.66%', backgroundColor: '#fff', borderRadius: 10, padding: 10, alignItems: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 2, elevation: 1,
  },
  platformCardSelected: { borderWidth: 2, borderColor: '#6366f1', backgroundColor: '#f5f3ff' },
  platformIcon: { width: 30, height: 30, borderRadius: 15, justifyContent: 'center', alignItems: 'center', marginBottom: 6 },
  platformName: { fontSize: 11, fontWeight: '500', color: '#1f2937', textAlign: 'center' },
  settingsSection: { backgroundColor: '#fff', marginHorizontal: 14, borderRadius: 10, overflow: 'hidden' },
  settingRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 12, paddingHorizontal: 14, borderBottomWidth: 1, borderBottomColor: '#f3f4f6',
  },
  settingLeft: { flexDirection: 'row', alignItems: 'center' },
  settingLabel: { fontSize: 15, color: '#1f2937', marginLeft: 10 },
  settingValue: { fontSize: 13, color: '#6b7280' },
});
