// ============================================
// GuguGaga AI VTuber Mobile - 设置页面（完整版）
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Switch, Alert, TextInput, Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useSettingsStore } from '../../src/stores';
import { LLM_PROVIDERS, TTS_PROVIDERS, LIVE_PLATFORMS } from '../../src/utils/constants';
import { VOICE_PRESETS } from '../../src/services/tts';
import { ragService } from '../../src/services/rag';
import { dataBackupService } from '../../src/services/dataBackup';
import { useCharacterStore, useConversationStore } from '../../src/stores';
import { useI18n } from '../../src/hooks/useI18n';

// 设置项 memo
const SettingItem = React.memo(({ icon, iconColor, title, subtitle, value, onPress, showArrow = true, rightComponent, badge }: {
  icon: string; iconColor?: string; title: string; subtitle?: string; value?: string;
  onPress?: () => void; showArrow?: boolean; rightComponent?: React.ReactNode; badge?: string;
}) => (
  <TouchableOpacity style={styles.item} onPress={onPress} disabled={!onPress} activeOpacity={onPress ? 0.7 : 1}>
    <View style={[styles.icon, { backgroundColor: (iconColor || '#6366f1') + '15' }]}>
      <Ionicons name={icon as any} size={20} color={iconColor || '#6366f1'} />
    </View>
    <View style={styles.content}>
      <View style={styles.titleRow}>
        <Text style={styles.itemTitle}>{title}</Text>
        {badge && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{badge}</Text>
          </View>
        )}
      </View>
      {subtitle && <Text style={styles.itemSub}>{subtitle}</Text>}
    </View>
    {value && <Text style={styles.value} numberOfLines={1}>{value}</Text>}
    {rightComponent}
    {showArrow && onPress && <Ionicons name="chevron-forward" size={18} color="#9ca3af" />}
  </TouchableOpacity>
));

const Divider = React.memo(() => <View style={styles.divider} />);

export default function SettingsTab() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { settings, updateAIConfig, updateTTSConfig, updateLiveConfig, updateUserPreferences, resetSettings } = useSettingsStore();
  const { characters } = useCharacterStore();
  const { conversations } = useConversationStore();
  const { t, currentLanguage, languageInfo, supportedLanguages, setLanguage } = useI18n();
  const [apiKeyModal, setApiKeyModal] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState(settings.ai.apiKey);

  const showPicker = useCallback((title: string, options: { text: string; onPress: () => void }[]) => {
    Alert.alert(title, '', [...options.map(o => ({ text: o.text, onPress: o.onPress })), { text: '取消', style: 'cancel' as const }]);
  }, []);

  const ragStats = useMemo(() => ragService.getStats(), []);
  const currentProvider = useMemo(() => LLM_PROVIDERS.find(p => p.value === settings.ai.provider), [settings.ai.provider]);
  const currentVoice = useMemo(() => Object.entries(VOICE_PRESETS).find(([id]) => id === settings.tts.voiceId)?.[1], [settings.tts.voiceId]);
  const currentPlatform = useMemo(() => LIVE_PLATFORMS.find(p => p.value === settings.live.platform), [settings.live.platform]);
  
  // 备份统计
  const backupStats = useMemo(() => dataBackupService.getBackupStats(), []);
  
  // 计算消息总数
  const totalMessages = useMemo(() => 
    conversations.reduce((sum, conv) => sum + conv.messages.length, 0),
    [conversations]
  );

  // 创建备份
  const handleCreateBackup = useCallback(async () => {
    Alert.alert(
      '创建备份',
      `确定要备份所有数据吗？\n\n• ${characters.length} 个角色\n• ${conversations.length} 个对话\n• ${totalMessages} 条消息`,
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '备份', 
          onPress: async () => {
            try {
              const result = await dataBackupService.createBackup(
                characters,
                conversations,
                settings
              );
              
              if (result) {
                Alert.alert('成功', '数据已备份');
              } else {
                Alert.alert('错误', '备份失败');
              }
            } catch (error) {
              Alert.alert('错误', '备份失败');
            }
          }
        },
      ]
    );
  }, [characters, conversations, settings, totalMessages]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Text style={styles.title}>设置</Text>
        <TouchableOpacity onPress={() => router.push('/about')} style={styles.aboutBtn}>
          <Ionicons name="information-circle" size={22} color="#6366f1" />
        </TouchableOpacity>
      </View>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* 数据概览 */}
        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Ionicons name="people" size={20} color="#6366f1" />
            <Text style={styles.statValue}>{characters.length}</Text>
            <Text style={styles.statLabel}>角色</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Ionicons name="chatbubbles" size={20} color="#10b981" />
            <Text style={styles.statValue}>{conversations.length}</Text>
            <Text style={styles.statLabel}>对话</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Ionicons name="document-text" size={20} color="#f59e0b" />
            <Text style={styles.statValue}>{totalMessages}</Text>
            <Text style={styles.statLabel}>消息</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Ionicons name="save" size={20} color="#8b5cf6" />
            <Text style={styles.statValue}>{backupStats.totalBackups}</Text>
            <Text style={styles.statLabel}>备份</Text>
          </View>
        </View>

        <Text style={styles.sectionLabel}>AI 配置</Text>
        <View style={styles.section}>
          <SettingItem icon="hardware-chip" title="AI 提供商" value={currentProvider?.label}
            onPress={() => showPicker('AI 提供商', LLM_PROVIDERS.map(p => ({ text: p.label, onPress: () => updateAIConfig({ provider: p.value as any }) })))} />
          <Divider />
          <SettingItem icon="key" title="API Key"
            subtitle={settings.ai.apiKey ? `已配置` : '未配置'}
            value={settings.ai.apiKey ? '已设置' : '未设置'}
            onPress={() => { setApiKeyInput(settings.ai.apiKey); setApiKeyModal(true); }} />
          <Divider />
          <SettingItem icon="cube" title="模型" value={settings.ai.model}
            onPress={() => {
              if (currentProvider) showPicker('模型', currentProvider.models.map(m => ({ text: m, onPress: () => updateAIConfig({ model: m }) })));
            }} />
          <Divider />
          <SettingItem icon="thermometer" title="温度" value={settings.ai.temperature.toString()}
            onPress={() => showPicker('温度', [
              { text: '0.3 保守', onPress: () => updateAIConfig({ temperature: 0.3 }) },
              { text: '0.7 平衡', onPress: () => updateAIConfig({ temperature: 0.7 }) },
              { text: '1.0 创造', onPress: () => updateAIConfig({ temperature: 1.0 }) },
            ])} />
        </View>

        <Text style={styles.sectionLabel}>语音合成</Text>
        <View style={styles.section}>
          <SettingItem icon="volume-high" title="TTS 提供商" value={TTS_PROVIDERS.find(p => p.value === settings.tts.provider)?.label}
            onPress={() => showPicker('TTS', TTS_PROVIDERS.map(p => ({ text: p.label, onPress: () => updateTTSConfig({ provider: p.value as any }) })))} />
          <Divider />
          <SettingItem icon="mic" title="语音角色" subtitle={currentVoice?.style} value={currentVoice?.name}
            onPress={() => showPicker('语音', Object.entries(VOICE_PRESETS).map(([id, p]) => ({ text: `${p.name} (${p.style})`, onPress: () => updateTTSConfig({ voiceId: id }) })))} />
          <Divider />
          <SettingItem icon="speedometer" title="语速" value={`${settings.tts.speed}x`}
            onPress={() => showPicker('语速', [
              { text: '0.5x 慢', onPress: () => updateTTSConfig({ speed: 0.5 }) },
              { text: '1.0x 正常', onPress: () => updateTTSConfig({ speed: 1.0 }) },
              { text: '1.5x 快', onPress: () => updateTTSConfig({ speed: 1.5 }) },
            ])} />
          <Divider />
          <SettingItem 
            icon="mic" 
            iconColor="#ec4899"
            title="变声器" 
            subtitle="实时语音变换效果"
            onPress={() => router.push('/voice-changer')} 
          />
          <Divider />
          <SettingItem 
            icon="musical-notes" 
            iconColor="#f59e0b"
            title="AI 唱歌" 
            subtitle="创作和演唱歌曲"
            onPress={() => router.push('/singing')} 
          />
          <Divider />
          <SettingItem 
            icon="person" 
            iconColor="#8b5cf6"
            title="语音克隆" 
            subtitle="复制你的声音"
            onPress={() => router.push('/voice-clone')} 
          />
        </View>

        <Text style={styles.sectionLabel}>知识库</Text>
        <View style={styles.section}>
          <SettingItem icon="library" title="知识库状态" subtitle={`${ragStats.documentCount}文档 ${ragStats.chunkCount}片段`} showArrow={false} />
        </View>

        <Text style={styles.sectionLabel}>直播</Text>
        <View style={styles.section}>
          <SettingItem icon="videocam" title="直播平台" value={currentPlatform?.label}
            onPress={() => showPicker('平台', LIVE_PLATFORMS.map(p => ({ text: p.label, onPress: () => updateLiveConfig({ platform: p.value as any }) })))} />
          <Divider />
          <SettingItem icon="home" title="房间号" value={settings.live.roomId || '未设置'}
            onPress={() => Alert.prompt('房间号', '', (t) => updateLiveConfig({ roomId: t }))} />
          <Divider />
          <SettingItem icon="chatbubbles" title="自动回复" showArrow={false}
            rightComponent={<Switch value={settings.live.autoReply} onValueChange={(v) => updateLiveConfig({ autoReply: v })} trackColor={{ false: '#d1d5db', true: '#a5b4fc' }} thumbColor={settings.live.autoReply ? '#6366f1' : '#f4f3f4'} />} />
        </View>

        <Text style={styles.sectionLabel}>通用</Text>
        <View style={styles.section}>
          <SettingItem 
            icon="moon" 
            iconColor="#8b5cf6"
            title="深色模式" 
            subtitle="跟随系统或手动切换"
            showArrow={false}
            rightComponent={
              <Switch 
                value={settings.user.theme === 'dark'} 
                onValueChange={(v) => updateUserPreferences({ theme: v ? 'dark' : 'light' })} 
                trackColor={{ false: '#d1d5db', true: '#a5b4fc' }} 
                thumbColor={settings.user.theme === 'dark' ? '#8b5cf6' : '#f4f3f4'} 
              />
            } 
          />
          <Divider />
          <SettingItem icon="volume-off" title="语音播放" showArrow={false}
            rightComponent={<Switch value={settings.user.soundEnabled} onValueChange={(v) => updateUserPreferences({ soundEnabled: v })} trackColor={{ false: '#d1d5db', true: '#a5b4fc' }} thumbColor={settings.user.soundEnabled ? '#6366f1' : '#f4f3f4'} />} />
          <Divider />
          <SettingItem icon="phone-portrait" title="震动" showArrow={false}
            rightComponent={<Switch value={settings.user.vibrationEnabled} onValueChange={(v) => updateUserPreferences({ vibrationEnabled: v })} trackColor={{ false: '#d1d5db', true: '#a5b4fc' }} thumbColor={settings.user.vibrationEnabled ? '#6366f1' : '#f4f3f4'} />} />
          <Divider />
          <SettingItem 
            icon="language" 
            iconColor="#f59e0b"
            title="语言" 
            subtitle={languageInfo.nativeName}
            value={languageInfo.flag}
            onPress={() => {
              showPicker('选择语言', supportedLanguages.map((lang: any) => ({
                text: `${lang.flag} ${lang.nativeName}`,
                onPress: () => setLanguage(lang.code),
              })));
            }} 
          />
          <Divider />
          <SettingItem 
            icon="eye" 
            iconColor="#10b981"
            title="视觉分析" 
            subtitle="AI图像识别与分析"
            onPress={() => router.push('/vision-analyzer')} 
          />
          <Divider />
          <SettingItem 
            icon="pulse" 
            iconColor="#ef4444"
            title="性能监控" 
            subtitle="实时性能数据监控"
            onPress={() => router.push('/performance')} 
          />
        </View>

        <Text style={styles.sectionLabel}>数据管理</Text>
        <View style={styles.section}>
          <SettingItem 
            icon="cloud-upload" 
            iconColor="#10b981"
            title="创建备份" 
            subtitle={`已备份 ${backupStats.totalBackups} 次`}
            onPress={handleCreateBackup} 
          />
          <Divider />
          <SettingItem 
            icon="cloud-download" 
            iconColor="#3b82f6"
            title="恢复备份" 
            subtitle="从备份文件恢复数据"
            onPress={() => Alert.alert('提示', '请在文件管理器中选择备份文件')} 
          />
          <Divider />
          <SettingItem 
            icon="search" 
            iconColor="#8b5cf6"
            title="搜索消息" 
            subtitle="搜索所有对话历史"
            onPress={() => router.push('/search')} 
          />
        </View>

        <Text style={styles.sectionLabel}>关于</Text>
        <View style={styles.section}>
          <SettingItem icon="information-circle" title="关于 GuguGaga" subtitle="版本 1.7.0" onPress={() => router.push('/about')} />
          <Divider />
          <SettingItem icon="globe" title="官方网站" subtitle="gugugaga.ai" onPress={() => Alert.alert('提示', '即将开放')} />
          <Divider />
          <SettingItem icon="help-circle" title="帮助与反馈" subtitle="常见问题解答" onPress={() => Alert.alert('提示', '即将开放')} />
          <Divider />
          <SettingItem 
            icon="refresh" 
            iconColor="#ef4444"
            title="重置设置" 
            onPress={() => {
              Alert.alert('重置', '确定重置所有设置？', [
                { text: '取消', style: 'cancel' },
                { text: '重置', style: 'destructive', onPress: () => { resetSettings(); Alert.alert('已重置'); } },
              ]);
            }} 
          />
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>

      {/* API Key 弹窗 */}
      <Modal visible={apiKeyModal} transparent animationType="fade">
        <View style={styles.modalBg}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>输入 API Key</Text>
            <Text style={styles.modalSub}>{currentProvider?.label} API Key</Text>
            <TextInput style={styles.modalInput} value={apiKeyInput} onChangeText={setApiKeyInput}
              placeholder="sk-..." placeholderTextColor="#9ca3af" secureTextEntry autoCapitalize="none" />
            <View style={styles.modalBtns}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setApiKeyModal(false)}>
                <Text style={styles.cancelText}>取消</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmBtn} onPress={() => {
                updateAIConfig({ apiKey: apiKeyInput }); setApiKeyModal(false); Alert.alert('已保存');
              }}>
                <Text style={styles.confirmText}>保存</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  aboutBtn: { padding: 4 },
  scroll: { flex: 1 },
  
  // 数据概览
  statsCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    margin: 16,
    padding: 16,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
  },
  statValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1e293b',
  },
  statLabel: {
    fontSize: 11,
    color: '#64748b',
  },
  statDivider: {
    width: 1,
    backgroundColor: '#e5e7eb',
    marginVertical: 4,
  },
  
  sectionLabel: { fontSize: 13, fontWeight: '600', color: '#6b7280', marginHorizontal: 18, marginTop: 20, marginBottom: 8 },
  section: { backgroundColor: '#fff', marginHorizontal: 14, borderRadius: 14, overflow: 'hidden' },
  item: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 14,
  },
  icon: {
    width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center', marginRight: 12,
  },
  content: { flex: 1 },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  itemTitle: { fontSize: 15, color: '#1f2937', fontWeight: '500' },
  itemSub: { fontSize: 12, color: '#9ca3af', marginTop: 2 },
  value: { fontSize: 14, color: '#6b7280', marginRight: 6, maxWidth: 120 },
  badge: {
    backgroundColor: '#6366f1',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  badgeText: {
    fontSize: 10,
    color: '#fff',
    fontWeight: '600',
  },
  divider: { height: 1, backgroundColor: '#f3f4f6', marginLeft: 62 },
  modalBg: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'center', alignItems: 'center' },
  modalCard: { width: '85%', backgroundColor: '#fff', borderRadius: 18, padding: 24 },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#1f2937', textAlign: 'center' },
  modalSub: { fontSize: 13, color: '#6b7280', textAlign: 'center', marginTop: 4, marginBottom: 16 },
  modalInput: {
    backgroundColor: '#f3f4f6', borderRadius: 10, padding: 14, fontSize: 15, color: '#1f2937', marginBottom: 20,
  },
  modalBtns: { flexDirection: 'row', gap: 12 },
  cancelBtn: { flex: 1, paddingVertical: 14, borderRadius: 10, backgroundColor: '#f3f4f6', alignItems: 'center' },
  cancelText: { fontSize: 15, color: '#6b7280', fontWeight: '600' },
  confirmBtn: { flex: 1, paddingVertical: 14, borderRadius: 10, backgroundColor: '#6366f1', alignItems: 'center' },
  confirmText: { fontSize: 15, color: '#fff', fontWeight: '600' },
});
