// ============================================
// 角色编辑器页面
// ============================================
import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput,
  TouchableOpacity, Alert, Image, KeyboardAvoidingView, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useCharacterStore } from '../src/stores';
import type { Character } from '../src/types';

// 预设头像列表
const PRESET_AVATARS = [
  'https://img.icons8.com/color/96/user-male-circle.png',
  'https://img.icons8.com/color/96/user-female-circle.png',
  'https://img.icons8.com/color/96/cat.png',
  'https://img.icons8.com/color/96/dog.png',
  'https://img.icons8.com/color/96/rabbit.png',
  'https://img.icons8.com/color/96/fox.png',
  'https://img.icons8.com/color/96/panda.png',
  'https://img.icons8.com/color/96/unicorn.png',
  'https://img.icons8.com/color/96/robot.png',
  'https://img.icons8.com/color/96/angel.png',
  'https://img.icons8.com/color/96/devil.png',
  'https://img.icons8.com/color/96/witch.png',
];

// 预设性格标签
const PERSONALITY_TAGS = [
  '温柔', '活泼', '傲娇', '元气', '文静', '毒舌',
  '天然呆', '腹黑', '治愈', '高冷', '软萌', '知性',
  '中二', '病娇', '三无', '热血', '电波', '电波',
];

// 预设系统提示词模板
const PROMPT_TEMPLATES = [
  {
    name: '温柔治愈',
    prompt: '你是一个温柔治愈的AI伙伴。你说话温和，善于倾听，总是能给人温暖和安慰。你喜欢用柔和的语气，偶尔会用一些可爱的语气词。',
  },
  {
    name: '傲娇毒舌',
    prompt: '你是一个傲娇的AI伙伴。表面上你很冷淡，经常说反话，但内心其实很关心对方。你喜欢用"哼"开头说话，偶尔会露出柔软的一面。',
  },
  {
    name: '元气满满',
    prompt: '你是一个元气满满的AI伙伴！你对世界充满好奇，总是乐观向上。你说话充满活力，喜欢用感叹号，偶尔会有点冒失。',
  },
  {
    name: '知识渊博',
    prompt: '你是一个知识渊博的AI伙伴。你对各种话题都有深入了解，善于解释复杂概念。你说话条理清晰，偶尔会引用一些有趣的知识。',
  },
  {
    name: '神秘优雅',
    prompt: '你是一个神秘优雅的AI伙伴。你说话优雅但偶尔会有点腹黑。你喜欢用谜语般的方式表达，对神秘事物有着浓厚的兴趣。',
  },
];

interface CharacterFormData {
  name: string;
  avatar: string;
  description: string;
  personality: string;
  systemPrompt: string;
  greeting: string;
  tags: string[];
  voiceId: string;
}

export default function CharacterEditorPage() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { addCharacter } = useCharacterStore();
  
  const [form, setForm] = useState<CharacterFormData>({
    name: '',
    avatar: PRESET_AVATARS[0],
    description: '',
    personality: '',
    systemPrompt: '',
    greeting: '',
    tags: [],
    voiceId: '',
  });
  
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const [showPromptTemplates, setShowPromptTemplates] = useState(false);
  
  // 更新表单字段
  const updateField = useCallback((field: keyof CharacterFormData, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);
  
  // 切换标签
  const toggleTag = useCallback((tag: string) => {
    setForm(prev => ({
      ...prev,
      tags: prev.tags.includes(tag)
        ? prev.tags.filter(t => t !== tag)
        : [...prev.tags, tag],
    }));
  }, []);
  
  // 验证表单
  const validateForm = useCallback((): boolean => {
    if (!form.name.trim()) {
      Alert.alert('错误', '请输入角色名称');
      return false;
    }
    if (!form.description.trim()) {
      Alert.alert('错误', '请输入角色描述');
      return false;
    }
    if (!form.systemPrompt.trim()) {
      Alert.alert('错误', '请输入系统提示词');
      return false;
    }
    return true;
  }, [form]);
  
  // 保存角色
  const handleSave = useCallback(() => {
    if (!validateForm()) {
      return;
    }
    
    addCharacter({
      name: form.name.trim(),
      avatar: form.avatar,
      description: form.description.trim(),
      personality: form.personality.trim(),
      systemPrompt: form.systemPrompt.trim(),
      greeting: form.greeting.trim() || `你好！我是${form.name}。`,
      tags: form.tags,
      voiceId: form.voiceId,
    });
    
    Alert.alert('成功', `角色 "${form.name}" 已创建`, [
      { text: '确定', onPress: () => router.back() },
    ]);
  }, [form, validateForm, addCharacter, router]);
  
  // 使用提示词模板
  const usePromptTemplate = useCallback((template: typeof PROMPT_TEMPLATES[0]) => {
    updateField('systemPrompt', template.prompt);
    setShowPromptTemplates(false);
  }, [updateField]);
  
  return (
    <>
      <Stack.Screen options={{ title: '创建角色', headerShown: true }} />
      
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* 头像选择 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>头像</Text>
            <TouchableOpacity
              style={styles.avatarButton}
              onPress={() => setShowAvatarPicker(!showAvatarPicker)}
            >
              <Image source={{ uri: form.avatar }} style={styles.avatarPreview} />
              <Text style={styles.avatarButtonText}>选择头像</Text>
            </TouchableOpacity>
            
            {showAvatarPicker && (
              <View style={styles.avatarGrid}>
                {PRESET_AVATARS.map((avatar, index) => (
                  <TouchableOpacity
                    key={index}
                    style={[
                      styles.avatarOption,
                      form.avatar === avatar && styles.avatarOptionSelected,
                    ]}
                    onPress={() => {
                      updateField('avatar', avatar);
                      setShowAvatarPicker(false);
                    }}
                  >
                    <Image source={{ uri: avatar }} style={styles.avatarOptionImage} />
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </View>
          
          {/* 基本信息 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>基本信息</Text>
            
            <View style={styles.inputGroup}>
              <Text style={styles.label}>角色名称 *</Text>
              <TextInput
                style={styles.input}
                value={form.name}
                onChangeText={(text) => updateField('name', text)}
                placeholder="给你的角色起个名字"
                placeholderTextColor="#9ca3af"
                maxLength={20}
              />
            </View>
            
            <View style={styles.inputGroup}>
              <Text style={styles.label}>角色描述 *</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={form.description}
                onChangeText={(text) => updateField('description', text)}
                placeholder="简单描述一下你的角色"
                placeholderTextColor="#9ca3af"
                multiline
                numberOfLines={3}
                maxLength={200}
              />
            </View>
            
            <View style={styles.inputGroup}>
              <Text style={styles.label}>性格特点</Text>
              <TextInput
                style={styles.input}
                value={form.personality}
                onChangeText={(text) => updateField('personality', text)}
                placeholder="例：温柔、活泼、傲娇"
                placeholderTextColor="#9ca3af"
                maxLength={100}
              />
            </View>
            
            <View style={styles.inputGroup}>
              <Text style={styles.label}>开场白</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={form.greeting}
                onChangeText={(text) => updateField('greeting', text)}
                placeholder="角色的第一句话"
                placeholderTextColor="#9ca3af"
                multiline
                numberOfLines={2}
                maxLength={200}
              />
            </View>
          </View>
          
          {/* 性格标签 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>性格标签</Text>
            <View style={styles.tagsContainer}>
              {PERSONALITY_TAGS.map((tag) => (
                <TouchableOpacity
                  key={tag}
                  style={[
                    styles.tag,
                    form.tags.includes(tag) && styles.tagSelected,
                  ]}
                  onPress={() => toggleTag(tag)}
                >
                  <Text style={[
                    styles.tagText,
                    form.tags.includes(tag) && styles.tagTextSelected,
                  ]}>
                    {tag}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
          
          {/* 系统提示词 */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>系统提示词 *</Text>
              <TouchableOpacity
                style={styles.templateButton}
                onPress={() => setShowPromptTemplates(!showPromptTemplates)}
              >
                <Ionicons name="document-text" size={16} color="#6366f1" />
                <Text style={styles.templateButtonText}>使用模板</Text>
              </TouchableOpacity>
            </View>
            
            {showPromptTemplates && (
              <View style={styles.templateList}>
                {PROMPT_TEMPLATES.map((template, index) => (
                  <TouchableOpacity
                    key={index}
                    style={styles.templateItem}
                    onPress={() => usePromptTemplate(template)}
                  >
                    <Text style={styles.templateName}>{template.name}</Text>
                    <Text style={styles.templatePreview} numberOfLines={2}>
                      {template.prompt}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
            
            <TextInput
              style={[styles.input, styles.promptInput]}
              value={form.systemPrompt}
              onChangeText={(text) => updateField('systemPrompt', text)}
              placeholder="定义角色的行为和性格..."
              placeholderTextColor="#9ca3af"
              multiline
              numberOfLines={6}
              textAlignVertical="top"
            />
            <Text style={styles.hint}>
              提示词决定了角色如何回应你的对话。可以描述角色的性格、说话方式、知识背景等。
            </Text>
          </View>
        </ScrollView>
        
        {/* 底部按钮 */}
        <View style={[styles.footer, { paddingBottom: insets.bottom + 16 }]}>
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={() => router.back()}
          >
            <Text style={styles.cancelButtonText}>取消</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={styles.saveButton}
            onPress={handleSave}
          >
            <Ionicons name="checkmark" size={20} color="#fff" />
            <Text style={styles.saveButtonText}>创建角色</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 12,
  },
  
  // 头像
  avatarButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatarPreview: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#e2e8f0',
  },
  avatarButtonText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '500',
  },
  avatarGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 12,
    padding: 12,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
  avatarOption: {
    width: 48,
    height: 48,
    borderRadius: 24,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  avatarOptionSelected: {
    borderColor: '#6366f1',
  },
  avatarOptionImage: {
    width: '100%',
    height: '100%',
  },
  
  // 输入
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#374151',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    color: '#1e293b',
  },
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  promptInput: {
    minHeight: 150,
  },
  hint: {
    fontSize: 12,
    color: '#9ca3af',
    marginTop: 8,
    lineHeight: 16,
  },
  
  // 标签
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  tag: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  tagSelected: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  tagText: {
    fontSize: 13,
    color: '#64748b',
  },
  tagTextSelected: {
    color: '#fff',
    fontWeight: '500',
  },
  
  // 模板
  templateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#eef2ff',
    borderRadius: 8,
  },
  templateButtonText: {
    fontSize: 13,
    color: '#6366f1',
    fontWeight: '500',
  },
  templateList: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginBottom: 12,
    overflow: 'hidden',
  },
  templateItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  templateName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 4,
  },
  templatePreview: {
    fontSize: 12,
    color: '#64748b',
    lineHeight: 16,
  },
  
  // 底部
  footer: {
    flexDirection: 'row',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  cancelButton: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    backgroundColor: '#f1f5f9',
    borderRadius: 12,
  },
  cancelButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#64748b',
  },
  saveButton: {
    flex: 2,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    backgroundColor: '#6366f1',
    borderRadius: 12,
  },
  saveButtonText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
});
