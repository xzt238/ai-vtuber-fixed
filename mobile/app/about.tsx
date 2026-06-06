// ============================================
// GuguGaga AI VTuber Mobile - 关于页面（完整版）
// ============================================
import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// 功能列表
const FEATURES = [
  { icon: 'chatbubbles', color: '#6366f1', title: '智能对话', desc: '支持 12 种 AI 模型，自然流畅的对话体验' },
  { icon: 'people', color: '#10b981', title: '角色扮演', desc: '自定义角色设定，沉浸式角色扮演体验' },
  { icon: 'volume-high', color: '#f59e0b', title: '语音交互', desc: '语音输入和语音合成，多模态交互' },
  { icon: 'cube', color: '#8b5cf6', title: 'Live2D/3D', desc: '支持 Live2D 和 VRM 3D 模型显示' },
  { icon: 'videocam', color: '#ef4444', title: '直播集成', desc: '支持 9 大直播平台，智能弹幕互动' },
  { icon: 'people-circle', color: '#ec4899', title: '多角色群聊', desc: '多个 AI 角色同时对话，互相回应' },
  { icon: 'call', color: '#06b6d4', title: '语音通话', desc: '实时语音对话，情感驱动交互' },
  { icon: 'library', color: '#84cc16', title: '知识库', desc: 'RAG 知识库系统，增强 AI 回答' },
  { icon: 'storefront', color: '#f97316', title: '角色市场', desc: '浏览和下载社区创建的角色' },
  { icon: 'search', color: '#6366f1', title: '消息搜索', desc: '全局搜索对话历史，快速查找' },
  { icon: 'cloud-upload', color: '#10b981', title: '数据备份', desc: '本地备份和恢复，保护你的数据' },
  { icon: 'phone-portrait', color: '#8b5cf6', title: '离线运行', desc: '本地 AI 引擎，无需联网也能聊天' },
];

// 版本历史
const VERSION_HISTORY = [
  { version: '1.7.0', date: '2026-06-05', features: ['消息搜索', '数据备份'] },
  { version: '1.6.0', date: '2026-06-05', features: ['语音通话', '角色分享'] },
  { version: '1.5.0', date: '2026-06-05', features: ['性能优化', '角色编辑器'] },
  { version: '1.4.0', date: '2026-06-05', features: ['多角色群聊'] },
  { version: '1.3.0', date: '2026-06-05', features: ['模型管理', '角色市场'] },
  { version: '1.2.0', date: '2026-06-05', features: ['Live2D V2', 'VRM 3D', 'TTS 增强'] },
];

export default function AboutScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={[styles.container, { paddingTop: insets.top }]}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <Text style={styles.title}>关于</Text>
          <View style={{ width: 40 }} />
        </View>

        <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
          {/* Logo 区域 */}
          <View style={styles.logoSection}>
            <View style={styles.logoContainer}>
              <Ionicons name="chatbubbles" size={48} color="#fff" />
            </View>
            <Text style={styles.appName}>GuguGaga AI VTuber</Text>
            <Text style={styles.version}>版本 1.7.0</Text>
            <Text style={styles.description}>你的专属 AI 虚拟主播伙伴</Text>
            
            {/* 统计 */}
            <View style={styles.statsRow}>
              <View style={styles.statItem}>
                <Text style={styles.statValue}>12</Text>
                <Text style={styles.statLabel}>AI 模型</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={styles.statValue}>9</Text>
                <Text style={styles.statLabel}>直播平台</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={styles.statValue}>15</Text>
                <Text style={styles.statLabel}>语音角色</Text>
              </View>
            </View>
          </View>

          {/* 功能列表 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>核心功能</Text>
            {FEATURES.map((f, i) => (
              <View key={i} style={styles.featureItem}>
                <View style={[styles.featureIcon, { backgroundColor: f.color + '15' }]}>
                  <Ionicons name={f.icon as any} size={20} color={f.color} />
                </View>
                <View style={styles.featureInfo}>
                  <Text style={styles.featureTitle}>{f.title}</Text>
                  <Text style={styles.featureDesc}>{f.desc}</Text>
                </View>
              </View>
            ))}
          </View>

          {/* 版本历史 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>版本历史</Text>
            {VERSION_HISTORY.map((v, i) => (
              <View key={i} style={styles.versionItem}>
                <View style={styles.versionHeader}>
                  <Text style={styles.versionNumber}>v{v.version}</Text>
                  <Text style={styles.versionDate}>{v.date}</Text>
                </View>
                <View style={styles.versionFeatures}>
                  {v.features.map((f, j) => (
                    <View key={j} style={styles.versionTag}>
                      <Text style={styles.versionTagText}>{f}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ))}
          </View>

          {/* 技术栈 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>技术栈</Text>
            <View style={styles.techList}>
              {['React Native', 'Expo', 'TypeScript', 'Live2D', 'Three.js', 'WebRTC'].map((tech, i) => (
                <View key={i} style={styles.techTag}>
                  <Text style={styles.techTagText}>{tech}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 链接 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>相关链接</Text>
            <TouchableOpacity style={styles.linkItem} onPress={() => Alert.alert('提示', '即将开放')}>
              <Ionicons name="globe" size={20} color="#6366f1" />
              <Text style={styles.linkText}>官方网站</Text>
              <Ionicons name="open" size={16} color="#9ca3af" />
            </TouchableOpacity>
            <View style={styles.linkDivider} />
            <TouchableOpacity style={styles.linkItem} onPress={() => Alert.alert('提示', '即将开放')}>
              <Ionicons name="logo-github" size={20} color="#1f2937" />
              <Text style={styles.linkText}>GitHub</Text>
              <Ionicons name="open" size={16} color="#9ca3af" />
            </TouchableOpacity>
            <View style={styles.linkDivider} />
            <TouchableOpacity style={styles.linkItem} onPress={() => Alert.alert('提示', '即将开放')}>
              <Ionicons name="help-circle" size={20} color="#10b981" />
              <Text style={styles.linkText}>帮助中心</Text>
              <Ionicons name="open" size={16} color="#9ca3af" />
            </TouchableOpacity>
          </View>

          {/* 页脚 */}
          <View style={styles.footer}>
            <Text style={styles.copyright}>© 2026 GuguGaga AI Team</Text>
            <Text style={styles.license}>MIT License</Text>
            <Text style={styles.slogan}>让 AI 陪伴你的每一天</Text>
          </View>

          <View style={{ height: 40 }} />
        </ScrollView>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: '#e5e7eb',
  },
  backBtn: { padding: 8 },
  title: { fontSize: 18, fontWeight: '600', color: '#1f2937' },
  scroll: { flex: 1 },
  
  // Logo
  logoSection: { alignItems: 'center', paddingVertical: 32, backgroundColor: '#fff', marginBottom: 16 },
  logoContainer: { width: 80, height: 80, borderRadius: 20, backgroundColor: '#6366f1', justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  appName: { fontSize: 24, fontWeight: '700', color: '#1f2937', marginBottom: 4 },
  version: { fontSize: 14, color: '#6b7280', marginBottom: 8 },
  description: { fontSize: 16, color: '#4b5563', textAlign: 'center', paddingHorizontal: 40, marginBottom: 20 },
  statsRow: {
    flexDirection: 'row',
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 24,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#6366f1',
  },
  statLabel: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    backgroundColor: '#e5e7eb',
  },
  
  // 功能
  section: { backgroundColor: '#fff', marginHorizontal: 16, marginBottom: 16, borderRadius: 12, padding: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 1 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#1f2937', marginBottom: 16 },
  featureItem: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 14 },
  featureIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  featureInfo: { flex: 1, marginLeft: 12 },
  featureTitle: { fontSize: 15, fontWeight: '600', color: '#1f2937', marginBottom: 2 },
  featureDesc: { fontSize: 13, color: '#6b7280', lineHeight: 18 },
  
  // 版本历史
  versionItem: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  versionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  versionNumber: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1e293b',
  },
  versionDate: {
    fontSize: 12,
    color: '#9ca3af',
  },
  versionFeatures: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  versionTag: {
    backgroundColor: '#eef2ff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  versionTagText: {
    fontSize: 12,
    color: '#6366f1',
  },
  
  // 技术栈
  techList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  techTag: {
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  techTagText: {
    fontSize: 13,
    color: '#475569',
  },
  
  // 链接
  linkItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 12,
  },
  linkText: {
    flex: 1,
    fontSize: 15,
    color: '#1e293b',
  },
  linkDivider: {
    height: 1,
    backgroundColor: '#f1f5f9',
    marginLeft: 32,
  },
  
  // 页脚
  footer: { alignItems: 'center', paddingVertical: 24 },
  copyright: { fontSize: 14, color: '#9ca3af', marginBottom: 4 },
  license: { fontSize: 13, color: '#d1d5db', marginBottom: 8 },
  slogan: { fontSize: 13, color: '#6366f1', fontStyle: 'italic' },
});
