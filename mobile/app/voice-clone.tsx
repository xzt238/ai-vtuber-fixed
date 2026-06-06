// ============================================
// 语音克隆页面
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  TextInput,
  Modal,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { 
  voiceCloneService, 
  VoiceCloneEngine, 
  CloneVoiceModel,
  CloneStatus 
} from '../src/services/voiceClone';

// 引擎卡片组件
const EngineCard = React.memo(({ 
  engine, 
  config, 
  isSelected, 
  onSelect 
}: { 
  engine: VoiceCloneEngine;
  config: any;
  isSelected: boolean;
  onSelect: () => void;
}) => (
  <TouchableOpacity
    style={[styles.engineCard, isSelected && styles.engineCardSelected]}
    onPress={onSelect}
    activeOpacity={0.7}
  >
    <Text style={styles.engineIcon}>{config.icon}</Text>
    <Text style={[styles.engineName, isSelected && styles.engineNameSelected]}>
      {config.name}
    </Text>
    <Text style={[styles.engineDesc, isSelected && styles.engineDescSelected]} numberOfLines={2}>
      {config.description}
    </Text>
    <View style={styles.engineMeta}>
      <Text style={[styles.engineMetaText, isSelected && styles.engineMetaTextSelected]}>
        {config.minSamples}-{config.maxSamples} 样本
      </Text>
    </View>
  </TouchableOpacity>
));

// 模型卡片组件
const ModelCard = React.memo(({ 
  model, 
  isSelected, 
  onSelect, 
  onTrain, 
  onDelete 
}: { 
  model: CloneVoiceModel;
  isSelected: boolean;
  onSelect: () => void;
  onTrain: () => void;
  onDelete: () => void;
}) => {
  const statusColor = voiceCloneService.getStatusColor(model.status);
  const statusText = voiceCloneService.getStatusDescription(model.status);
  
  return (
    <TouchableOpacity
      style={[styles.modelCard, isSelected && styles.modelCardSelected]}
      onPress={onSelect}
      activeOpacity={0.7}
    >
      <View style={styles.modelHeader}>
        <View style={styles.modelInfo}>
          <Text style={[styles.modelName, isSelected && styles.modelNameSelected]}>
            {model.name}
          </Text>
          <Text style={[styles.modelDesc, isSelected && styles.modelDescSelected]}>
            {model.description}
          </Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: statusColor + '20' }]}>
          <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
          <Text style={[styles.statusText, { color: statusColor }]}>{statusText}</Text>
        </View>
      </View>
      
      {/* 进度条 */}
      {(model.status === 'uploading' || model.status === 'processing' || model.status === 'training') && (
        <View style={styles.progressContainer}>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${model.progress}%` }]} />
          </View>
          <Text style={styles.progressText}>{model.progress}%</Text>
        </View>
      )}
      
      <View style={styles.modelFooter}>
        <Text style={styles.modelMeta}>
          {model.samples.length} 样本 · {model.engine}
        </Text>
        <View style={styles.modelActions}>
          {model.status === 'idle' && model.samples.length > 0 && (
            <TouchableOpacity style={styles.actionBtn} onPress={onTrain}>
              <Ionicons name="play" size={16} color="#6366f1" />
            </TouchableOpacity>
          )}
          {!model.id.startsWith('preset_') && (
            <TouchableOpacity style={styles.actionBtn} onPress={onDelete}>
              <Ionicons name="trash" size={16} color="#ef4444" />
            </TouchableOpacity>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
});

export default function VoiceCloneScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  
  const [selectedEngine, setSelectedEngine] = useState<VoiceCloneEngine>('gpt_sovits');
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newModelName, setNewModelName] = useState('');
  const [newModelDesc, setNewModelDesc] = useState('');
  
  // 获取数据
  const engineConfigs = useMemo(() => voiceCloneService.getEngineConfigs(), []);
  const allModels = useMemo(() => voiceCloneService.getModels(), []);
  const presetModels = useMemo(() => voiceCloneService.getPresetModels(), []);
  const userModels = useMemo(() => voiceCloneService.getUserModels(), []);
  const stats = useMemo(() => voiceCloneService.getStats(), []);
  
  // 创建新模型
  const handleCreateModel = useCallback(() => {
    if (!newModelName.trim()) {
      Alert.alert('提示', '请输入模型名称');
      return;
    }
    
    voiceCloneService.createModel(newModelName, newModelDesc, selectedEngine);
    setShowCreateModal(false);
    setNewModelName('');
    setNewModelDesc('');
    
    Alert.alert('成功', '模型已创建，请添加音频样本后开始训练');
  }, [newModelName, newModelDesc, selectedEngine]);
  
  // 开始训练
  const handleStartTraining = useCallback((modelId: string) => {
    const model = voiceCloneService.getModel(modelId);
    if (!model) return;
    
    Alert.alert(
      '开始训练',
      `使用 ${model.samples.length} 个样本训练 ${model.name}？`,
      [
        { text: '取消', style: 'cancel' },
        { text: '开始', onPress: () => voiceCloneService.startTraining(modelId) },
      ]
    );
  }, []);
  
  // 删除模型
  const handleDeleteModel = useCallback((modelId: string) => {
    Alert.alert(
      '删除模型',
      '确定要删除这个语音模型吗？',
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '删除', 
          style: 'destructive',
          onPress: () => {
            voiceCloneService.deleteModel(modelId);
            if (selectedModel === modelId) {
              setSelectedModel(null);
            }
          }
        },
      ]
    );
  }, [selectedModel]);
  
  // 选择模型
  const handleSelectModel = useCallback((modelId: string) => {
    const model = voiceCloneService.getModel(modelId);
    if (model && model.status === 'ready') {
      voiceCloneService.setCurrentModel(modelId);
      setSelectedModel(modelId);
      Alert.alert('已选择', `当前使用: ${model.name}`);
    }
  }, []);
  
  return (
    <>
      <Stack.Screen options={{ title: '语音克隆', headerShown: false }} />
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {/* 头部 */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle}>语音克隆</Text>
            <Text style={styles.headerSubtitle}>复制你的声音</Text>
          </View>
          <TouchableOpacity 
            style={styles.addButton}
            onPress={() => setShowCreateModal(true)}
          >
            <Ionicons name="add" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
        
        <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
          {/* 统计卡片 */}
          <View style={styles.statsCard}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.totalModels}</Text>
              <Text style={styles.statLabel}>总模型</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.readyModels}</Text>
              <Text style={styles.statLabel}>就绪</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.trainingModels}</Text>
              <Text style={styles.statLabel}>训练中</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.totalSamples}</Text>
              <Text style={styles.statLabel}>样本数</Text>
            </View>
          </View>
          
          {/* 预设语音 */}
          {presetModels.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>预设语音</Text>
              {presetModels.map((model) => (
                <ModelCard
                  key={model.id}
                  model={model}
                  isSelected={selectedModel === model.id}
                  onSelect={() => handleSelectModel(model.id)}
                  onTrain={() => handleStartTraining(model.id)}
                  onDelete={() => handleDeleteModel(model.id)}
                />
              ))}
            </View>
          )}
          
          {/* 我的语音模型 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>我的语音模型</Text>
            {userModels.length === 0 ? (
              <View style={styles.emptyCard}>
                <Ionicons name="mic-outline" size={48} color="#d1d5db" />
                <Text style={styles.emptyText}>还没有自定义语音模型</Text>
                <Text style={styles.emptySubtext}>点击右上角 + 创建新模型</Text>
              </View>
            ) : (
              userModels.map((model) => (
                <ModelCard
                  key={model.id}
                  model={model}
                  isSelected={selectedModel === model.id}
                  onSelect={() => handleSelectModel(model.id)}
                  onTrain={() => handleStartTraining(model.id)}
                  onDelete={() => handleDeleteModel(model.id)}
                />
              ))
            )}
          </View>
          
          {/* 克隆引擎 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>克隆引擎</Text>
            <ScrollView 
              horizontal 
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.engineList}
            >
              {Object.entries(engineConfigs).map(([engine, config]) => (
                <EngineCard
                  key={engine}
                  engine={engine as VoiceCloneEngine}
                  config={config}
                  isSelected={selectedEngine === engine}
                  onSelect={() => setSelectedEngine(engine as VoiceCloneEngine)}
                />
              ))}
            </ScrollView>
          </View>
          
          {/* 使用说明 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>使用说明</Text>
            <View style={styles.helpCard}>
              <View style={styles.helpItem}>
                <Ionicons name="mic" size={16} color="#6366f1" />
                <Text style={styles.helpText}>录制 3-10 分钟的清晰语音样本</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="cloud-upload" size={16} color="#6366f1" />
                <Text style={styles.helpText}>上传样本到云端进行训练</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="time" size={16} color="#6366f1" />
                <Text style={styles.helpText}>训练通常需要 10-30 分钟</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="checkmark-circle" size={16} color="#6366f1" />
                <Text style={styles.helpText}>训练完成后即可使用克隆语音</Text>
              </View>
            </View>
          </View>
        </ScrollView>
        
        {/* 创建模型弹窗 */}
        <Modal visible={showCreateModal} transparent animationType="fade">
          <View style={styles.modalBg}>
            <View style={styles.modalCard}>
              <Text style={styles.modalTitle}>创建语音模型</Text>
              
              <Text style={styles.inputLabel}>模型名称</Text>
              <TextInput
                style={styles.modalInput}
                value={newModelName}
                onChangeText={setNewModelName}
                placeholder="例如：我的声音"
                placeholderTextColor="#9ca3af"
              />
              
              <Text style={styles.inputLabel}>描述（可选）</Text>
              <TextInput
                style={styles.modalInput}
                value={newModelDesc}
                onChangeText={setNewModelDesc}
                placeholder="描述这个声音的特点"
                placeholderTextColor="#9ca3af"
              />
              
              <Text style={styles.inputLabel}>选择引擎</Text>
              <View style={styles.engineSelect}>
                {Object.entries(engineConfigs).slice(0, 3).map(([engine, config]) => (
                  <TouchableOpacity
                    key={engine}
                    style={[
                      styles.engineOption,
                      selectedEngine === engine && styles.engineOptionSelected
                    ]}
                    onPress={() => setSelectedEngine(engine as VoiceCloneEngine)}
                  >
                    <Text style={styles.engineOptionIcon}>{config.icon}</Text>
                    <Text style={[
                      styles.engineOptionText,
                      selectedEngine === engine && styles.engineOptionTextSelected
                    ]}>
                      {config.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
              
              <View style={styles.modalBtns}>
                <TouchableOpacity 
                  style={styles.cancelBtn} 
                  onPress={() => setShowCreateModal(false)}
                >
                  <Text style={styles.cancelText}>取消</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.confirmBtn} onPress={handleCreateModel}>
                  <Text style={styles.confirmText}>创建</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#6b7280',
  },
  addButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#6366f1',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 40,
  },
  statsCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#6366f1',
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  statDivider: {
    width: 1,
    backgroundColor: '#e5e7eb',
    marginVertical: 4,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 12,
  },
  engineList: {
    gap: 12,
  },
  engineCard: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    minWidth: 100,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  engineCardSelected: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  engineIcon: {
    fontSize: 28,
    marginBottom: 8,
  },
  engineName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 4,
  },
  engineNameSelected: {
    color: '#fff',
  },
  engineDesc: {
    fontSize: 10,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 8,
  },
  engineDescSelected: {
    color: '#e0e7ff',
  },
  engineMeta: {
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  engineMetaText: {
    fontSize: 10,
    color: '#6b7280',
  },
  engineMetaTextSelected: {
    color: '#e0e7ff',
  },
  modelCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  modelCardSelected: {
    borderColor: '#6366f1',
    borderWidth: 2,
  },
  modelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  modelInfo: {
    flex: 1,
    marginRight: 12,
  },
  modelName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 2,
  },
  modelNameSelected: {
    color: '#6366f1',
  },
  modelDesc: {
    fontSize: 13,
    color: '#6b7280',
  },
  modelDescSelected: {
    color: '#6366f1',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '500',
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  progressBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#e5e7eb',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#6366f1',
    borderRadius: 3,
  },
  progressText: {
    fontSize: 12,
    color: '#6b7280',
    width: 35,
    textAlign: 'right',
  },
  modelFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  modelMeta: {
    fontSize: 12,
    color: '#9ca3af',
  },
  modelActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 40,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderStyle: 'dashed',
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#6b7280',
    marginTop: 12,
  },
  emptySubtext: {
    fontSize: 13,
    color: '#9ca3af',
    marginTop: 4,
  },
  helpCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  helpItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 8,
  },
  helpText: {
    fontSize: 13,
    color: '#6b7280',
    flex: 1,
    lineHeight: 20,
  },
  // Modal styles
  modalBg: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 20,
    textAlign: 'center',
  },
  inputLabel: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 6,
  },
  modalInput: {
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 15,
    color: '#1f2937',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    marginBottom: 16,
  },
  engineSelect: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 20,
  },
  engineOption: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: '#f3f4f6',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  engineOptionSelected: {
    backgroundColor: '#eef2ff',
    borderColor: '#6366f1',
  },
  engineOptionIcon: {
    fontSize: 20,
    marginBottom: 4,
  },
  engineOptionText: {
    fontSize: 11,
    color: '#6b7280',
  },
  engineOptionTextSelected: {
    color: '#6366f1',
    fontWeight: '500',
  },
  modalBtns: {
    flexDirection: 'row',
    gap: 12,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
  },
  cancelText: {
    fontSize: 16,
    color: '#6b7280',
  },
  confirmBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: '#6366f1',
    alignItems: 'center',
  },
  confirmText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
  },
});