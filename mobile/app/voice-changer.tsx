// ============================================
// 变声页面
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Switch,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Slider from '@react-native-community/slider';
import { 
  voiceChangerService, 
  VoiceEffect, 
  VoiceEffectConfig,
  VoiceParams 
} from '../src/services/voiceChanger';

// 音效卡片组件
const EffectCard = React.memo(({ 
  config, 
  isSelected, 
  onSelect 
}: { 
  config: VoiceEffectConfig; 
  isSelected: boolean;
  onSelect: () => void;
}) => (
  <TouchableOpacity
    style={[styles.effectCard, isSelected && styles.effectCardSelected]}
    onPress={onSelect}
    activeOpacity={0.7}
  >
    <Text style={styles.effectIcon}>{config.icon}</Text>
    <Text style={[styles.effectName, isSelected && styles.effectNameSelected]}>
      {config.name}
    </Text>
    <Text style={[styles.effectDesc, isSelected && styles.effectDescSelected]} numberOfLines={1}>
      {config.description}
    </Text>
  </TouchableOpacity>
));

// 参数滑块组件
const ParamSlider = React.memo(({ 
  label, 
  value, 
  min, 
  max, 
  step, 
  onChange,
  icon,
}: { 
  label: string; 
  value: number; 
  min: number; 
  max: number; 
  step: number; 
  onChange: (value: number) => void;
  icon: string;
}) => (
  <View style={styles.paramContainer}>
    <View style={styles.paramHeader}>
      <Ionicons name={icon as any} size={16} color="#6366f1" />
      <Text style={styles.paramLabel}>{label}</Text>
      <Text style={styles.paramValue}>{value.toFixed(2)}</Text>
    </View>
    <Slider
      style={styles.slider}
      minimumValue={min}
      maximumValue={max}
      step={step}
      value={value}
      onValueChange={onChange}
      minimumTrackTintColor="#6366f1"
      maximumTrackTintColor="#e5e7eb"
      thumbTintColor="#6366f1"
    />
    <View style={styles.paramRange}>
      <Text style={styles.rangeText}>{min}</Text>
      <Text style={styles.rangeText}>{max}</Text>
    </View>
  </View>
));

export default function VoiceChangerScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  
  const [currentEffect, setCurrentEffect] = useState<VoiceEffect>(voiceChangerService.getCurrentEffect());
  const [params, setParams] = useState<VoiceParams>(voiceChangerService.getCurrentParams());
  const [isEnabled, setIsEnabled] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // 获取所有音效
  const allEffects = useMemo(() => voiceChangerService.getAllEffects(), []);
  const presetEffects = useMemo(() => voiceChangerService.getPresetEffects(), []);
  const customEffects = useMemo(() => voiceChangerService.getCustomEffects(), []);
  
  // 选择音效
  const handleSelectEffect = useCallback((effect: VoiceEffect) => {
    setCurrentEffect(effect);
    voiceChangerService.setEffect(effect);
    setParams(voiceChangerService.getCurrentParams());
  }, []);
  
  // 更新参数
  const handleParamChange = useCallback((key: keyof VoiceParams, value: number) => {
    const newParams = { ...params, [key]: value };
    setParams(newParams);
    voiceChangerService.updateParams({ [key]: value });
  }, [params]);
  
  // 重置参数
  const handleResetParams = useCallback(() => {
    voiceChangerService.resetParams();
    setParams(voiceChangerService.getCurrentParams());
  }, []);
  
  // 创建自定义音效
  const handleCreateCustom = useCallback(() => {
    Alert.prompt(
      '创建自定义音效',
      '输入音效名称',
      (name) => {
        if (name) {
          Alert.prompt(
            '音效描述',
            '输入音效描述',
            (description) => {
              if (description) {
                voiceChangerService.createCustomEffect(name, description, params);
                Alert.alert('成功', '自定义音效已创建');
              }
            }
          );
        }
      }
    );
  }, [params]);
  
  // 测试变声效果
  const handleTestVoice = useCallback(() => {
    Alert.alert(
      '测试变声',
      '请对着麦克风说话，测试变声效果',
      [
        { text: '取消', style: 'cancel' },
        { text: '开始测试', onPress: () => {
          // 这里可以启动录音并应用变声效果
          Alert.alert('提示', '变声测试功能需要在聊天页面中使用');
        }},
      ]
    );
  }, []);
  
  return (
    <>
      <Stack.Screen options={{ title: '变声器', headerShown: false }} />
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {/* 头部 */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle}>变声器</Text>
            <Text style={styles.headerSubtitle}>实时语音变换</Text>
          </View>
          <Switch
            value={isEnabled}
            onValueChange={setIsEnabled}
            trackColor={{ false: '#d1d5db', true: '#a5b4fc' }}
            thumbColor={isEnabled ? '#6366f1' : '#f4f3f4'}
          />
        </View>
        
        <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
          {/* 当前音效预览 */}
          <View style={styles.previewSection}>
            <View style={styles.previewCard}>
              <Text style={styles.previewIcon}>
                {allEffects.find(e => e.id === currentEffect)?.icon || '🎤'}
              </Text>
              <Text style={styles.previewName}>
                {allEffects.find(e => e.id === currentEffect)?.name || '正常'}
              </Text>
              <Text style={styles.previewDesc}>
                {allEffects.find(e => e.id === currentEffect)?.description || ''}
              </Text>
              <View style={styles.previewFeatures}>
                {params.pitch !== 0 && (
                  <View style={styles.featureTag}>
                    <Text style={styles.featureText}>
                      {params.pitch > 0 ? '高音' : '低音'}
                    </Text>
                  </View>
                )}
                {params.reverb > 0.3 && (
                  <View style={styles.featureTag}>
                    <Text style={styles.featureText}>混响</Text>
                  </View>
                )}
                {params.echo > 0.3 && (
                  <View style={styles.featureTag}>
                    <Text style={styles.featureText}>回声</Text>
                  </View>
                )}
              </View>
            </View>
            
            <TouchableOpacity style={styles.testButton} onPress={handleTestVoice}>
              <Ionicons name="mic" size={20} color="#fff" />
              <Text style={styles.testButtonText}>测试变声</Text>
            </TouchableOpacity>
          </View>
          
          {/* 预设音效 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>预设音效</Text>
            <ScrollView 
              horizontal 
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.effectList}
            >
              {presetEffects.map((config) => (
                <EffectCard
                  key={config.id}
                  config={config}
                  isSelected={currentEffect === config.id}
                  onSelect={() => handleSelectEffect(config.id)}
                />
              ))}
            </ScrollView>
          </View>
          
          {/* 自定义音效 */}
          {customEffects.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>自定义音效</Text>
              <ScrollView 
                horizontal 
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.effectList}
              >
                {customEffects.map((config) => (
                  <EffectCard
                    key={config.id}
                    config={config}
                    isSelected={currentEffect === config.id}
                    onSelect={() => handleSelectEffect(config.id)}
                  />
                ))}
              </ScrollView>
            </View>
          )}
          
          {/* 参数调整 */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>参数调整</Text>
              <TouchableOpacity onPress={handleResetParams}>
                <Text style={styles.resetText}>重置</Text>
              </TouchableOpacity>
            </View>
            
            {/* 基础参数 */}
            <View style={styles.paramGroup}>
              <ParamSlider
                label="音高"
                icon="musical-notes"
                value={params.pitch}
                min={-12}
                max={12}
                step={1}
                onChange={(v) => handleParamChange('pitch', v)}
              />
              
              <ParamSlider
                label="共振峰"
                icon="voice"
                value={params.formant}
                min={0.5}
                max={2.0}
                step={0.05}
                onChange={(v) => handleParamChange('formant', v)}
              />
              
              <ParamSlider
                label="语速"
                icon="speedometer"
                value={params.rate}
                min={0.5}
                max={2.0}
                step={0.05}
                onChange={(v) => handleParamChange('rate', v)}
              />
              
              <ParamSlider
                label="音量"
                icon="volume-high"
                value={params.volume}
                min={0}
                max={1.5}
                step={0.05}
                onChange={(v) => handleParamChange('volume', v)}
              />
            </View>
            
            {/* 高级参数 */}
            <TouchableOpacity 
              style={styles.advancedToggle}
              onPress={() => setShowAdvanced(!showAdvanced)}
            >
              <Text style={styles.advancedText}>高级参数</Text>
              <Ionicons 
                name={showAdvanced ? 'chevron-up' : 'chevron-down'} 
                size={16} 
                color="#6b7280" 
              />
            </TouchableOpacity>
            
            {showAdvanced && (
              <View style={styles.paramGroup}>
                <ParamSlider
                  label="混响"
                  icon="water"
                  value={params.reverb}
                  min={0}
                  max={1}
                  step={0.05}
                  onChange={(v) => handleParamChange('reverb', v)}
                />
                
                <ParamSlider
                  label="回声"
                  icon="repeat"
                  value={params.echo}
                  min={0}
                  max={1}
                  step={0.05}
                  onChange={(v) => handleParamChange('echo', v)}
                />
                
                <ParamSlider
                  label="失真"
                  icon="flash"
                  value={params.distortion}
                  min={0}
                  max={1}
                  step={0.05}
                  onChange={(v) => handleParamChange('distortion', v)}
                />
                
                <ParamSlider
                  label="合唱"
                  icon="people"
                  value={params.chorus}
                  min={0}
                  max={1}
                  step={0.05}
                  onChange={(v) => handleParamChange('chorus', v)}
                />
              </View>
            )}
          </View>
          
          {/* 创建自定义音效 */}
          <TouchableOpacity style={styles.createButton} onPress={handleCreateCustom}>
            <Ionicons name="add-circle" size={20} color="#6366f1" />
            <Text style={styles.createButtonText}>保存为自定义音效</Text>
          </TouchableOpacity>
          
          {/* 使用说明 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>使用说明</Text>
            <View style={styles.helpCard}>
              <View style={styles.helpItem}>
                <Ionicons name="information-circle" size={16} color="#6366f1" />
                <Text style={styles.helpText}>选择音效后，在聊天页面发送语音消息会自动应用变声效果</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="settings" size={16} color="#6366f1" />
                <Text style={styles.helpText}>调整参数可以微调声音效果，创造独特的音色</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="save" size={16} color="#6366f1" />
                <Text style={styles.helpText}>满意的参数可以保存为自定义音效，方便下次使用</Text>
              </View>
            </View>
          </View>
        </ScrollView>
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
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 40,
  },
  previewSection: {
    marginBottom: 20,
  },
  previewCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
    marginBottom: 12,
  },
  previewIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  previewName: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 4,
  },
  previewDesc: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 12,
  },
  previewFeatures: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  featureTag: {
    backgroundColor: '#eef2ff',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  featureText: {
    fontSize: 12,
    color: '#6366f1',
  },
  testButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#6366f1',
    paddingVertical: 12,
    borderRadius: 12,
    gap: 8,
  },
  testButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  section: {
    marginBottom: 20,
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
    color: '#1f2937',
    marginBottom: 12,
  },
  resetText: {
    fontSize: 14,
    color: '#6366f1',
  },
  effectList: {
    gap: 12,
  },
  effectCard: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    minWidth: 80,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  effectCardSelected: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  effectIcon: {
    fontSize: 28,
    marginBottom: 8,
  },
  effectName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 2,
  },
  effectNameSelected: {
    color: '#fff',
  },
  effectDesc: {
    fontSize: 10,
    color: '#6b7280',
  },
  effectDescSelected: {
    color: '#e0e7ff',
  },
  paramGroup: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  paramContainer: {
    marginBottom: 16,
  },
  paramHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  paramLabel: {
    fontSize: 14,
    color: '#374151',
    flex: 1,
  },
  paramValue: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '500',
  },
  slider: {
    width: '100%',
    height: 40,
  },
  paramRange: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  rangeText: {
    fontSize: 11,
    color: '#9ca3af',
  },
  advancedToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    gap: 4,
  },
  advancedText: {
    fontSize: 14,
    color: '#6b7280',
  },
  createButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#6366f1',
    borderStyle: 'dashed',
    marginBottom: 20,
    gap: 8,
  },
  createButtonText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '500',
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
});