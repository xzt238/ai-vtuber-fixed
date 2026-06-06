/**
 * 设置页面
 *
 * 服务器配置、主题切换、语言选择、LLM 配置
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  TextInput,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/Ionicons';
import { COLORS, THEMES, LANGUAGES } from '../utils/constants';
import { useAppStore } from '../store/appStore';
import { useSettingsStore } from '../store/settingsStore';

const SettingsScreen: React.FC = () => {
  const {
    serverUrl,
    isConnected,
    setServerUrl,
    checkConnection,
  } = useAppStore();

  const {
    theme,
    language,
    notifications,
    autoSync,
    llmProvider,
    llmApiKey,
    llmBaseUrl,
    llmModel,
    setTheme,
    setLanguage,
    setNotifications,
    setAutoSync,
    setLLMConfig,
  } = useSettingsStore();

  const [editServerUrl, setEditServerUrl] = useState(serverUrl);
  const [isEditingServer, setIsEditingServer] = useState(false);
  const [isEditingLLM, setIsEditingLLM] = useState(false);
  const [editProvider, setEditProvider] = useState(llmProvider);
  const [editApiKey, setEditApiKey] = useState(llmApiKey);
  const [editBaseUrl, setEditBaseUrl] = useState(llmBaseUrl);
  const [editModel, setEditModel] = useState(llmModel);

  // 保存服务器地址
  const saveServerUrl = async () => {
    if (!editServerUrl.trim()) {
      Alert.alert('错误', '请输入服务器地址');
      return;
    }
    try {
      await setServerUrl(editServerUrl.trim());
      setIsEditingServer(false);
      Alert.alert('成功', '服务器地址已更新');
    } catch {
      Alert.alert('错误', '无法连接到服务器');
    }
  };

  // 测试连接
  const testConnection = async () => {
    const connected = await checkConnection();
    Alert.alert(
      connected ? '成功' : '失败',
      connected ? '连接成功！' : '无法连接到服务器'
    );
  };

  // 保存 LLM 配置
  const saveLLMConfig = () => {
    setLLMConfig({
      provider: editProvider,
      apiKey: editApiKey,
      baseUrl: editBaseUrl,
      model: editModel,
    });
    setIsEditingLLM(false);
    Alert.alert('成功', 'LLM 配置已保存');
  };

  // 渲染设置项
  const renderSettingItem = (
    icon: string,
    title: string,
    subtitle?: string,
    right?: React.ReactNode,
    onPress?: () => void
  ) => (
    <TouchableOpacity
      style={styles.settingItem}
      onPress={onPress}
      disabled={!onPress}
    >
      <View style={styles.settingLeft}>
        <Icon name={icon} size={24} color={COLORS.primary} />
        <View style={styles.settingText}>
          <Text style={styles.settingTitle}>{title}</Text>
          {subtitle && <Text style={styles.settingSubtitle}>{subtitle}</Text>}
        </View>
      </View>
      {right && <View style={styles.settingRight}>{right}</View>}
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>设置</Text>
      </View>

      <ScrollView style={styles.content}>
        {/* 服务器设置 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>服务器连接</Text>
          {renderSettingItem(
            'server-outline',
            '服务器地址',
            isEditingServer ? undefined : serverUrl,
            isEditingServer ? (
              <View style={styles.editContainer}>
                <TextInput
                  style={styles.editInput}
                  value={editServerUrl}
                  onChangeText={setEditServerUrl}
                  placeholder="输入服务器地址"
                  placeholderTextColor={COLORS.lightGray}
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                <TouchableOpacity style={styles.saveButton} onPress={saveServerUrl}>
                  <Text style={styles.saveButtonText}>保存</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <TouchableOpacity
                style={styles.editButton}
                onPress={() => setIsEditingServer(true)}
              >
                <Icon name="create-outline" size={20} color={COLORS.primary} />
              </TouchableOpacity>
            )
          )}
          {renderSettingItem(
            'wifi-outline',
            '连接状态',
            isConnected ? '已连接' : '未连接',
            <View
              style={[
                styles.statusDot,
                { backgroundColor: isConnected ? COLORS.success : COLORS.error },
              ]}
            />,
            testConnection
          )}
        </View>

        {/* LLM 配置 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>云端 LLM 配置</Text>
          {isEditingLLM ? (
            <>
              <View style={styles.llmInputGroup}>
                <Text style={styles.llmLabel}>供应商</Text>
                <View style={styles.providerRow}>
                  {['openai', 'anthropic', 'custom'].map((p) => (
                    <TouchableOpacity
                      key={p}
                      style={[
                        styles.providerChip,
                        editProvider === p && styles.providerChipActive,
                      ]}
                      onPress={() => setEditProvider(p)}
                    >
                      <Text
                        style={[
                          styles.providerChipText,
                          editProvider === p && styles.providerChipTextActive,
                        ]}
                      >
                        {p === 'openai' ? 'OpenAI' : p === 'anthropic' ? 'Anthropic' : '自定义'}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
              <View style={styles.llmInputGroup}>
                <Text style={styles.llmLabel}>API Key</Text>
                <TextInput
                  style={styles.llmInput}
                  value={editApiKey}
                  onChangeText={setEditApiKey}
                  placeholder="输入 API Key"
                  placeholderTextColor={COLORS.lightGray}
                  secureTextEntry
                  autoCapitalize="none"
                />
              </View>
              <View style={styles.llmInputGroup}>
                <Text style={styles.llmLabel}>Base URL</Text>
                <TextInput
                  style={styles.llmInput}
                  value={editBaseUrl}
                  onChangeText={setEditBaseUrl}
                  placeholder="可选，自定义 API 地址"
                  placeholderTextColor={COLORS.lightGray}
                  autoCapitalize="none"
                />
              </View>
              <View style={styles.llmInputGroup}>
                <Text style={styles.llmLabel}>模型</Text>
                <TextInput
                  style={styles.llmInput}
                  value={editModel}
                  onChangeText={setEditModel}
                  placeholder="例如: gpt-3.5-turbo"
                  placeholderTextColor={COLORS.lightGray}
                  autoCapitalize="none"
                />
              </View>
              <View style={styles.llmButtonRow}>
                <TouchableOpacity
                  style={styles.cancelButton}
                  onPress={() => setIsEditingLLM(false)}
                >
                  <Text style={styles.cancelButtonText}>取消</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.saveButton} onPress={saveLLMConfig}>
                  <Text style={styles.saveButtonText}>保存</Text>
                </TouchableOpacity>
              </View>
            </>
          ) : (
            <>
              {renderSettingItem(
                'cloud-outline',
                'LLM 供应商',
                llmProvider === 'openai'
                  ? 'OpenAI'
                  : llmProvider === 'anthropic'
                  ? 'Anthropic'
                  : '自定义',
                <Icon name="chevron-forward" size={20} color={COLORS.gray} />,
                () => setIsEditingLLM(true)
              )}
              {renderSettingItem(
                'key-outline',
                'API Key',
                llmApiKey ? '已配置' : '未配置'
              )}
              {renderSettingItem(
                'cube-outline',
                '模型',
                llmModel
              )}
            </>
          )}
        </View>

        {/* 外观设置 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>外观</Text>
          {renderSettingItem(
            'color-palette-outline',
            '主题',
            theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '跟随系统',
            <Icon name="chevron-forward" size={20} color={COLORS.gray} />,
            () => {
              Alert.alert('选择主题', '', [
                { text: '浅色', onPress: () => setTheme('light') },
                { text: '深色', onPress: () => setTheme('dark') },
                { text: '跟随系统', onPress: () => setTheme('auto') },
                { text: '取消', style: 'cancel' },
              ]);
            }
          )}
        </View>

        {/* 语言设置 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>语言</Text>
          {renderSettingItem(
            'language-outline',
            '界面语言',
            language === 'zh-CN'
              ? '简体中文'
              : language === 'en-US'
              ? 'English'
              : '日本語',
            <Icon name="chevron-forward" size={20} color={COLORS.gray} />,
            () => {
              Alert.alert('选择语言', '', [
                { text: '简体中文', onPress: () => setLanguage('zh-CN') },
                { text: 'English', onPress: () => setLanguage('en-US') },
                { text: '日本語', onPress: () => setLanguage('ja-JP') },
                { text: '取消', style: 'cancel' },
              ]);
            }
          )}
        </View>

        {/* 通知设置 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>通知</Text>
          {renderSettingItem(
            'notifications-outline',
            '推送通知',
            '接收AI消息通知',
            <Switch
              value={notifications}
              onValueChange={setNotifications}
              trackColor={{ false: COLORS.lightGray, true: COLORS.primaryLight }}
              thumbColor={notifications ? COLORS.primary : COLORS.gray}
            />
          )}
        </View>

        {/* 同步设置 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>同步</Text>
          {renderSettingItem(
            'sync-outline',
            '自动同步',
            '自动同步聊天记录',
            <Switch
              value={autoSync}
              onValueChange={setAutoSync}
              trackColor={{ false: COLORS.lightGray, true: COLORS.primaryLight }}
              thumbColor={autoSync ? COLORS.primary : COLORS.gray}
            />
          )}
        </View>

        {/* 关于 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>关于</Text>
          {renderSettingItem('information-circle-outline', '版本', 'v1.0.0')}
        </View>

        <View style={{ height: 40 }} />
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
  content: {
    flex: 1,
  },
  section: {
    marginTop: 16,
    backgroundColor: COLORS.white,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: COLORS.lightGray,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.textSecondary,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: COLORS.lightGray,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  settingText: {
    marginLeft: 12,
    flex: 1,
  },
  settingTitle: {
    fontSize: 16,
    color: COLORS.text,
  },
  settingSubtitle: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  settingRight: {
    marginLeft: 12,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  editContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  editInput: {
    flex: 1,
    height: 36,
    backgroundColor: COLORS.background,
    borderRadius: 8,
    paddingHorizontal: 12,
    marginRight: 8,
    fontSize: 14,
    color: COLORS.text,
  },
  editButton: {
    padding: 4,
  },
  saveButton: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  saveButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '600',
  },
  cancelButton: {
    backgroundColor: COLORS.background,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cancelButtonText: {
    color: COLORS.textSecondary,
    fontSize: 14,
    fontWeight: '600',
  },
  llmInputGroup: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: COLORS.lightGray,
  },
  llmLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 8,
  },
  llmInput: {
    height: 40,
    backgroundColor: COLORS.background,
    borderRadius: 8,
    paddingHorizontal: 12,
    fontSize: 14,
    color: COLORS.text,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  providerRow: {
    flexDirection: 'row',
    gap: 8,
  },
  providerChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: COLORS.background,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  providerChipActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  providerChipText: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  providerChipTextActive: {
    color: COLORS.white,
    fontWeight: '600',
  },
  llmButtonRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: COLORS.lightGray,
  },
});

export default SettingsScreen;
