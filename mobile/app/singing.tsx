// ============================================
// AI 唱歌页面
// ============================================
import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  FlatList,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { 
  singingService, 
  SingingStyle, 
  SongTemplate,
  SongConfig 
} from '../src/services/singing';

// 唱法卡片组件
const StyleCard = React.memo(({ 
  style, 
  name, 
  icon, 
  description,
  isSelected, 
  onSelect 
}: { 
  style: SingingStyle;
  name: string;
  icon: string;
  description: string;
  isSelected: boolean;
  onSelect: () => void;
}) => (
  <TouchableOpacity
    style={[styles.styleCard, isSelected && styles.styleCardSelected]}
    onPress={onSelect}
    activeOpacity={0.7}
  >
    <Text style={styles.styleIcon}>{icon}</Text>
    <Text style={[styles.styleName, isSelected && styles.styleNameSelected]}>
      {name}
    </Text>
    <Text style={[styles.styleDesc, isSelected && styles.styleDescSelected]} numberOfLines={1}>
      {description}
    </Text>
  </TouchableOpacity>
));

// 模板卡片组件
const TemplateCard = React.memo(({ 
  template, 
  onPress 
}: { 
  template: SongTemplate;
  onPress: () => void;
}) => {
  const styleConfig = singingService.getStyleConfig(template.style);
  
  return (
    <TouchableOpacity style={styles.templateCard} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.templateHeader}>
        <Text style={styles.templateIcon}>{styleConfig.icon}</Text>
        <View style={styles.templateInfo}>
          <Text style={styles.templateTitle}>{template.title}</Text>
          <Text style={styles.templateStyle}>{styleConfig.name}</Text>
        </View>
        <View style={styles.templateMeta}>
          <Text style={styles.templateTempo}>{template.tempo} BPM</Text>
          <Text style={styles.templateKey}>{template.key}调</Text>
        </View>
      </View>
      <Text style={styles.templateLyrics} numberOfLines={2}>
        {template.lyrics}
      </Text>
    </TouchableOpacity>
  );
});

export default function SingingScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  
  const [selectedStyle, setSelectedStyle] = useState<SingingStyle>('pop');
  const [customLyrics, setCustomLyrics] = useState('');
  const [songTitle, setSongTitle] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentSong, setCurrentSong] = useState<SongConfig | null>(null);
  
  // 获取模板和唱法
  const templates = useMemo(() => singingService.getTemplates(), []);
  const singingStyles = useMemo(() => singingService.getStyles(), []);
  const savedSongs = useMemo(() => singingService.getSavedSongs(), []);
  
  // 选择模板
  const handleSelectTemplate = useCallback((template: SongTemplate) => {
    const song = singingService.createSongFromTemplate(template.id);
    if (song) {
      setCurrentSong(song);
      setSongTitle(song.title);
      setCustomLyrics(template.lyrics);
      setSelectedStyle(template.style);
    }
  }, []);
  
  // 生成歌词
  const handleGenerateLyrics = useCallback(async () => {
    if (!songTitle.trim()) {
      Alert.alert('提示', '请输入歌曲主题');
      return;
    }
    
    setIsGenerating(true);
    
    try {
      const lyrics = await singingService.generateLyrics(songTitle, selectedStyle);
      setCustomLyrics(lyrics);
    } catch (error) {
      console.error('Generate lyrics error:', error);
      Alert.alert('错误', '生成歌词失败');
    } finally {
      setIsGenerating(false);
    }
  }, [songTitle, selectedStyle]);
  
  // 创建歌曲
  const handleCreateSong = useCallback(() => {
    if (!customLyrics.trim()) {
      Alert.alert('提示', '请输入歌词');
      return;
    }
    
    const song = singingService.createSong({
      title: songTitle || '未命名歌曲',
      style: selectedStyle,
      lyrics: singingService.parseLyrics(customLyrics, 120),
    });
    
    singingService.saveSong(song);
    setCurrentSong(song);
    
    Alert.alert('成功', '歌曲已保存');
  }, [songTitle, selectedStyle, customLyrics]);
  
  // 开始唱歌
  const handleStartSinging = useCallback(async () => {
    if (!currentSong) {
      Alert.alert('提示', '请先创建歌曲');
      return;
    }
    
    Alert.alert(
      '开始唱歌',
      `即将演唱: ${currentSong.title}`,
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '开始', 
          onPress: async () => {
            try {
              await singingService.startSinging(currentSong);
            } catch (error) {
              console.error('Singing error:', error);
            }
          }
        },
      ]
    );
  }, [currentSong]);
  
  // 停止唱歌
  const handleStopSinging = useCallback(() => {
    singingService.stopSinging();
  }, []);
  
  return (
    <>
      <Stack.Screen options={{ title: 'AI 唱歌', headerShown: false }} />
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {/* 头部 */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle}>AI 唱歌</Text>
            <Text style={styles.headerSubtitle}>创作你的歌曲</Text>
          </View>
          <TouchableOpacity 
            style={styles.singingButton}
            onPress={currentSong ? handleStopSinging : handleStartSinging}
          >
            <Ionicons 
              name={currentSong ? 'stop' : 'play'} 
              size={20} 
              color="#fff" 
            />
            <Text style={styles.singingButtonText}>
              {currentSong ? '停止' : '演唱'}
            </Text>
          </TouchableOpacity>
        </View>
        
        <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
          {/* 歌曲信息 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>歌曲信息</Text>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>歌曲标题</Text>
              <TextInput
                style={styles.textInput}
                value={songTitle}
                onChangeText={setSongTitle}
                placeholder="输入歌曲标题或主题"
                placeholderTextColor="#9ca3af"
              />
            </View>
          </View>
          
          {/* 唱法选择 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>选择唱法</Text>
            <ScrollView 
              horizontal 
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.styleList}
            >
              {singingStyles.map(({ style, config }) => (
                <StyleCard
                  key={style}
                  style={style}
                  name={config.name}
                  icon={config.icon}
                  description={config.description}
                  isSelected={selectedStyle === style}
                  onSelect={() => setSelectedStyle(style)}
                />
              ))}
            </ScrollView>
          </View>
          
          {/* 歌词编辑 */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>歌词</Text>
              <TouchableOpacity onPress={handleGenerateLyrics} disabled={isGenerating}>
                <Text style={[styles.generateText, isGenerating && styles.generateTextDisabled]}>
                  {isGenerating ? '生成中...' : 'AI 生成'}
                </Text>
              </TouchableOpacity>
            </View>
            <TextInput
              style={styles.lyricsInput}
              value={customLyrics}
              onChangeText={setCustomLyrics}
              placeholder="输入歌词，每行一句..."
              placeholderTextColor="#9ca3af"
              multiline
              textAlignVertical="top"
            />
          </View>
          
          {/* 保存按钮 */}
          <TouchableOpacity style={styles.saveButton} onPress={handleCreateSong}>
            <Ionicons name="save" size={20} color="#fff" />
            <Text style={styles.saveButtonText}>保存歌曲</Text>
          </TouchableOpacity>
          
          {/* 模板推荐 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>歌曲模板</Text>
            {templates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                onPress={() => handleSelectTemplate(template)}
              />
            ))}
          </View>
          
          {/* 已保存的歌曲 */}
          {savedSongs.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>我的歌曲</Text>
              {savedSongs.map((song, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.savedSongCard}
                  onPress={() => {
                    setCurrentSong(song);
                    setSongTitle(song.title);
                    setCustomLyrics(song.lyrics.map(l => l.text).join('\n'));
                    setSelectedStyle(song.style);
                  }}
                >
                  <View style={styles.savedSongHeader}>
                    <Text style={styles.savedSongTitle}>{song.title}</Text>
                    <Text style={styles.savedSongStyle}>
                      {singingService.getStyleConfig(song.style).name}
                    </Text>
                  </View>
                  <Text style={styles.savedSongLyrics} numberOfLines={1}>
                    {song.lyrics[0]?.text || '无歌词'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
          
          {/* 使用说明 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>使用说明</Text>
            <View style={styles.helpCard}>
              <View style={styles.helpItem}>
                <Ionicons name="musical-notes" size={16} color="#6366f1" />
                <Text style={styles.helpText}>选择唱法风格，影响声音效果和演唱方式</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="create" size={16} color="#6366f1" />
                <Text style={styles.helpText}>输入歌词或使用AI生成，每行一句</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="play" size={16} color="#6366f1" />
                <Text style={styles.helpText}>点击演唱按钮，AI会根据歌词和唱法进行演唱</Text>
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
  singingButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#6366f1',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 6,
  },
  singingButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
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
  generateText: {
    fontSize: 14,
    color: '#6366f1',
    fontWeight: '500',
  },
  generateTextDisabled: {
    color: '#9ca3af',
  },
  inputGroup: {
    marginBottom: 12,
  },
  inputLabel: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 6,
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
  },
  styleList: {
    gap: 12,
  },
  styleCard: {
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    minWidth: 80,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  styleCardSelected: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  styleIcon: {
    fontSize: 28,
    marginBottom: 8,
  },
  styleName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 2,
  },
  styleNameSelected: {
    color: '#fff',
  },
  styleDesc: {
    fontSize: 10,
    color: '#6b7280',
  },
  styleDescSelected: {
    color: '#e0e7ff',
  },
  lyricsInput: {
    backgroundColor: '#fff',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 15,
    color: '#1f2937',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    minHeight: 150,
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#10b981',
    paddingVertical: 14,
    borderRadius: 12,
    marginBottom: 20,
    gap: 8,
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  templateCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  templateHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  templateIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  templateInfo: {
    flex: 1,
  },
  templateTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
  },
  templateStyle: {
    fontSize: 12,
    color: '#6b7280',
  },
  templateMeta: {
    alignItems: 'flex-end',
  },
  templateTempo: {
    fontSize: 12,
    color: '#6366f1',
  },
  templateKey: {
    fontSize: 12,
    color: '#6b7280',
  },
  templateLyrics: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 20,
  },
  savedSongCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  savedSongHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  savedSongTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
  },
  savedSongStyle: {
    fontSize: 12,
    color: '#6366f1',
    backgroundColor: '#eef2ff',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  savedSongLyrics: {
    fontSize: 14,
    color: '#6b7280',
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