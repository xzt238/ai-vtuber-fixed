// ============================================
// 视觉分析页面
// ============================================
import React, { useState, useCallback, useMemo, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
  FlatList,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { 
  visionService, 
  VisionAnalysisType, 
  VisionResult,
  DetectedObject,
  DetectedEmotion,
  ColorInfo 
} from '../src/services/vision';

// 分析类型配置
const ANALYSIS_TYPES: Array<{
  type: VisionAnalysisType;
  icon: string;
  label: string;
  description: string;
  color: string;
}> = [
  {
    type: 'general',
    icon: 'scan',
    label: '全面分析',
    description: '物体、场景、情感综合分析',
    color: '#6366f1',
  },
  {
    type: 'object_detection',
    icon: 'cube',
    label: '物体识别',
    description: '识别图像中的物体',
    color: '#10b981',
  },
  {
    type: 'scene_description',
    icon: 'landscape',
    label: '场景描述',
    description: '描述图像场景和环境',
    color: '#f59e0b',
  },
  {
    type: 'text_recognition',
    icon: 'text',
    label: '文字识别',
    description: '识别图像中的文字',
    color: '#3b82f6',
  },
  {
    type: 'emotion_recognition',
    icon: 'happy',
    label: '情感分析',
    description: '分析人物情感状态',
    color: '#ec4899',
  },
  {
    type: 'color_analysis',
    icon: 'color-palette',
    label: '颜色分析',
    description: '分析主要颜色组成',
    color: '#8b5cf6',
  },
];

// 分析类型按钮组件
const AnalysisTypeButton = React.memo(({ 
  config, 
  isSelected, 
  onSelect 
}: { 
  config: typeof ANALYSIS_TYPES[0]; 
  isSelected: boolean;
  onSelect: () => void;
}) => (
  <TouchableOpacity
    style={[styles.typeButton, isSelected && { backgroundColor: config.color + '20', borderColor: config.color }]}
    onPress={onSelect}
    activeOpacity={0.7}
  >
    <Ionicons 
      name={config.icon as any} 
      size={24} 
      color={isSelected ? config.color : '#6b7280'} 
    />
    <Text style={[styles.typeLabel, isSelected && { color: config.color }]}>
      {config.label}
    </Text>
  </TouchableOpacity>
));

// 分析结果组件
const AnalysisResultView = React.memo(({ result }: { result: VisionResult }) => {
  const typeConfig = ANALYSIS_TYPES.find(t => t.type === result.type);
  
  return (
    <View style={styles.resultContainer}>
      {/* 头部 */}
      <View style={styles.resultHeader}>
        <View style={[styles.resultTypeBadge, { backgroundColor: typeConfig?.color + '20' }]}>
          <Ionicons name={typeConfig?.icon as any} size={16} color={typeConfig?.color} />
          <Text style={[styles.resultTypeText, { color: typeConfig?.color }]}>
            {typeConfig?.label}
          </Text>
        </View>
        <Text style={styles.resultTime}>
          {new Date(result.timestamp).toLocaleTimeString()}
        </Text>
      </View>
      
      {/* 描述 */}
      <Text style={styles.resultDescription}>{result.description}</Text>
      
      {/* 物体列表 */}
      {result.objects.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>识别到的物体</Text>
          <View style={styles.objectList}>
            {result.objects.map((obj, index) => (
              <View key={index} style={styles.objectTag}>
                <Text style={styles.objectText}>{obj.name}</Text>
                <Text style={styles.objectConfidence}>
                  {Math.round(obj.confidence * 100)}%
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}
      
      {/* 情感分析 */}
      {result.emotions.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>情感分析</Text>
          <View style={styles.emotionList}>
            {result.emotions.map((emotion, index) => (
              <View key={index} style={styles.emotionItem}>
                <Text style={styles.emotionName}>{emotion.emotion}</Text>
                <View style={styles.emotionBar}>
                  <View 
                    style={[
                      styles.emotionProgress, 
                      { width: `${emotion.confidence * 100}%` }
                    ]} 
                  />
                </View>
                <Text style={styles.emotionConfidence}>
                  {Math.round(emotion.confidence * 100)}%
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}
      
      {/* 颜色分析 */}
      {result.colors.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>颜色分析</Text>
          <View style={styles.colorList}>
            {result.colors.map((color, index) => (
              <View key={index} style={styles.colorItem}>
                <View style={[styles.colorSwatch, { backgroundColor: color.hex }]} />
                <Text style={styles.colorName}>{color.color}</Text>
                <Text style={styles.colorPercentage}>{color.percentage}%</Text>
              </View>
            ))}
          </View>
        </View>
      )}
      
      {/* 识别文字 */}
      {result.text && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>识别到的文字</Text>
          <View style={styles.textContainer}>
            <Text style={styles.recognizedText}>{result.text}</Text>
          </View>
        </View>
      )}
      
      {/* 置信度 */}
      <View style={styles.confidenceContainer}>
        <Text style={styles.confidenceLabel}>分析置信度</Text>
        <View style={styles.confidenceBar}>
          <View 
            style={[
              styles.confidenceProgress, 
              { width: `${result.confidence * 100}%` }
            ]} 
          />
        </View>
        <Text style={styles.confidenceValue}>
          {Math.round(result.confidence * 100)}%
        </Text>
      </View>
    </View>
  );
});

export default function VisionAnalyzerScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const scrollViewRef = useRef<ScrollView>(null);
  
  const [selectedType, setSelectedType] = useState<VisionAnalysisType>('general');
  const [imageDescription, setImageDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentResult, setCurrentResult] = useState<VisionResult | null>(null);
  const [analysisHistory, setAnalysisHistory] = useState<VisionResult[]>([]);
  
  // 获取历史记录
  useMemo(() => {
    setAnalysisHistory(visionService.getHistory());
  }, []);
  
  // 执行分析
  const handleAnalyze = useCallback(async () => {
    if (!imageDescription.trim()) {
      Alert.alert('提示', '请输入图像描述');
      return;
    }
    
    setIsAnalyzing(true);
    
    try {
      const result = await visionService.analyzeImage(imageDescription, selectedType);
      setCurrentResult(result);
      setAnalysisHistory(prev => [result, ...prev.slice(0, 19)]);
      
      // 滚动到结果
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error) {
      console.error('Analysis error:', error);
      Alert.alert('错误', '分析失败，请重试');
    } finally {
      setIsAnalyzing(false);
    }
  }, [imageDescription, selectedType]);
  
  // 使用示例描述
  const handleUseExample = useCallback((example: string) => {
    setImageDescription(example);
  }, []);
  
  // 清除历史
  const handleClearHistory = useCallback(() => {
    Alert.alert(
      '清除历史',
      '确定要清除所有分析历史吗？',
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '清除', 
          style: 'destructive',
          onPress: () => {
            visionService.clearHistory();
            setAnalysisHistory([]);
            setCurrentResult(null);
          }
        },
      ]
    );
  }, []);
  
  // 示例描述
  const exampleDescriptions = [
    '一个年轻女孩坐在咖啡馆里，手里拿着一本书，面带微笑',
    '城市夜景，高楼大厦灯火通明，天空中有星星',
    '一只橘色猫咪躺在沙发上睡觉，旁边有一个毛线球',
    '厨房台面上有各种蔬菜和水果，包括西红柿、胡萝卜和苹果',
  ];
  
  return (
    <>
      <Stack.Screen options={{ title: '视觉分析', headerShown: false }} />
      <KeyboardAvoidingView 
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {/* 头部 */}
        <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle}>视觉分析</Text>
            <Text style={styles.headerSubtitle}>AI图像识别与分析</Text>
          </View>
          <TouchableOpacity onPress={handleClearHistory} style={styles.clearButton}>
            <Ionicons name="trash-outline" size={20} color="#6b7280" />
          </TouchableOpacity>
        </View>
        
        <ScrollView 
          ref={scrollViewRef}
          style={styles.content}
          contentContainerStyle={styles.contentContainer}
          keyboardShouldPersistTaps="handled"
        >
          {/* 分析类型选择 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>选择分析类型</Text>
            <ScrollView 
              horizontal 
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.typeList}
            >
              {ANALYSIS_TYPES.map((config) => (
                <AnalysisTypeButton
                  key={config.type}
                  config={config}
                  isSelected={selectedType === config.type}
                  onSelect={() => setSelectedType(config.type)}
                />
              ))}
            </ScrollView>
          </View>
          
          {/* 图像描述输入 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>图像描述</Text>
            <TextInput
              style={styles.textInput}
              value={imageDescription}
              onChangeText={setImageDescription}
              placeholder="描述你看到的图像内容，例如：一个女孩在公园里跑步..."
              placeholderTextColor="#9ca3af"
              multiline
              maxLength={1000}
            />
            
            {/* 示例描述 */}
            <View style={styles.examplesContainer}>
              <Text style={styles.examplesTitle}>示例描述：</Text>
              {exampleDescriptions.map((example, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.exampleButton}
                  onPress={() => handleUseExample(example)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.exampleText} numberOfLines={1}>
                    {example}
                  </Text>
                  <Ionicons name="copy-outline" size={14} color="#6366f1" />
                </TouchableOpacity>
              ))}
            </View>
          </View>
          
          {/* 分析按钮 */}
          <TouchableOpacity
            style={[styles.analyzeButton, isAnalyzing && styles.analyzeButtonDisabled]}
            onPress={handleAnalyze}
            disabled={isAnalyzing || !imageDescription.trim()}
            activeOpacity={0.7}
          >
            {isAnalyzing ? (
              <>
                <Ionicons name="hourglass" size={20} color="#fff" />
                <Text style={styles.analyzeButtonText}>分析中...</Text>
              </>
            ) : (
              <>
                <Ionicons name="scan" size={20} color="#fff" />
                <Text style={styles.analyzeButtonText}>开始分析</Text>
              </>
            )}
          </TouchableOpacity>
          
          {/* 当前结果 */}
          {currentResult && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>分析结果</Text>
              <AnalysisResultView result={currentResult} />
            </View>
          )}
          
          {/* 历史记录 */}
          {analysisHistory.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>分析历史</Text>
              {analysisHistory.slice(0, 5).map((result, index) => (
                <TouchableOpacity
                  key={result.id}
                  style={styles.historyItem}
                  onPress={() => setCurrentResult(result)}
                  activeOpacity={0.7}
                >
                  <View style={styles.historyHeader}>
                    <Text style={styles.historyType}>
                      {ANALYSIS_TYPES.find(t => t.type === result.type)?.label}
                    </Text>
                    <Text style={styles.historyTime}>
                      {new Date(result.timestamp).toLocaleTimeString()}
                    </Text>
                  </View>
                  <Text style={styles.historyDescription} numberOfLines={2}>
                    {result.description}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
          
          {/* 统计信息 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>使用统计</Text>
            <View style={styles.statsContainer}>
              <View style={styles.statItem}>
                <Text style={styles.statValue}>{analysisHistory.length}</Text>
                <Text style={styles.statLabel}>总分析次数</Text>
              </View>
              <View style={styles.statItem}>
                <Text style={styles.statValue}>
                  {analysisHistory.length > 0 
                    ? Math.round(analysisHistory.reduce((sum, r) => sum + r.confidence, 0) / analysisHistory.length * 100)
                    : 0}%
                </Text>
                <Text style={styles.statLabel}>平均置信度</Text>
              </View>
              <View style={styles.statItem}>
                <Text style={styles.statValue}>
                  {new Set(analysisHistory.map(r => r.type)).size}
                </Text>
                <Text style={styles.statLabel}>使用类型数</Text>
              </View>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
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
    paddingBottom: 12,
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
  clearButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f3f4f6',
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
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 12,
  },
  typeList: {
    gap: 8,
  },
  typeButton: {
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    minWidth: 80,
  },
  typeLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  textInput: {
    backgroundColor: '#fff',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 15,
    color: '#1f2937',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    minHeight: 100,
    textAlignVertical: 'top',
  },
  examplesContainer: {
    marginTop: 12,
  },
  examplesTitle: {
    fontSize: 13,
    color: '#6b7280',
    marginBottom: 8,
  },
  exampleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  exampleText: {
    fontSize: 13,
    color: '#374151',
    flex: 1,
    marginRight: 8,
  },
  analyzeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#6366f1',
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
    marginBottom: 20,
  },
  analyzeButtonDisabled: {
    backgroundColor: '#d1d5db',
  },
  analyzeButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  resultContainer: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  resultTypeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  resultTypeText: {
    fontSize: 12,
    fontWeight: '500',
  },
  resultTime: {
    fontSize: 12,
    color: '#9ca3af',
  },
  resultDescription: {
    fontSize: 15,
    color: '#374151',
    lineHeight: 22,
    marginBottom: 16,
  },
  objectList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  objectTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 4,
  },
  objectText: {
    fontSize: 13,
    color: '#374151',
  },
  objectConfidence: {
    fontSize: 11,
    color: '#6b7280',
  },
  emotionList: {
    gap: 8,
  },
  emotionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  emotionName: {
    fontSize: 13,
    color: '#374151',
    width: 60,
  },
  emotionBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#e5e7eb',
    borderRadius: 3,
    overflow: 'hidden',
  },
  emotionProgress: {
    height: '100%',
    backgroundColor: '#6366f1',
    borderRadius: 3,
  },
  emotionConfidence: {
    fontSize: 12,
    color: '#6b7280',
    width: 40,
    textAlign: 'right',
  },
  colorList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  colorItem: {
    alignItems: 'center',
    gap: 4,
  },
  colorSwatch: {
    width: 40,
    height: 40,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  colorName: {
    fontSize: 12,
    color: '#374151',
  },
  colorPercentage: {
    fontSize: 11,
    color: '#6b7280',
  },
  textContainer: {
    backgroundColor: '#f9fafb',
    padding: 12,
    borderRadius: 8,
  },
  recognizedText: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
  },
  confidenceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    gap: 8,
  },
  confidenceLabel: {
    fontSize: 13,
    color: '#6b7280',
  },
  confidenceBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#e5e7eb',
    borderRadius: 3,
    overflow: 'hidden',
  },
  confidenceProgress: {
    height: '100%',
    backgroundColor: '#10b981',
    borderRadius: 3,
  },
  confidenceValue: {
    fontSize: 13,
    color: '#374151',
    fontWeight: '500',
  },
  historyItem: {
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  historyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  historyType: {
    fontSize: 13,
    fontWeight: '500',
    color: '#6366f1',
  },
  historyTime: {
    fontSize: 12,
    color: '#9ca3af',
  },
  historyDescription: {
    fontSize: 13,
    color: '#6b7280',
    lineHeight: 18,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#6366f1',
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
});