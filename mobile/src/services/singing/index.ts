// ============================================
// AI 唱歌服务 - 移动端版本
// ============================================
import { MMKV } from 'react-native-mmkv';
import { ttsService } from '../tts';
import { voiceChangerService } from '../voiceChanger';

const storage = new MMKV();

// 唱法类型
export type SingingStyle = 
  | 'pop'         // 流行
  | 'folk'        // 民谣
  | 'rock'        // 摇滚
  | 'jazz'        // 爵士
  | 'classical'   // 古典
  | 'rnb'         // R&B
  | 'rap'         // 说唱
  | 'children'    // 儿歌
  | 'opera'       // 歌剧
  | 'country'     // 乡村
  | 'electronic'  // 电子
  | 'custom';     // 自定义

// 音高类型
export type NotePitch = 
  | 'C3' | 'D3' | 'E3' | 'F3' | 'G3' | 'A3' | 'B3'
  | 'C4' | 'D4' | 'E4' | 'F4' | 'G4' | 'A4' | 'B4'
  | 'C5' | 'D5' | 'E5' | 'F5' | 'G5' | 'A5' | 'B5';

// 歌词行
export interface LyricLine {
  text: string;
  startTime: number; // 秒
  duration: number;  // 秒
  pitch?: NotePitch;
  notes?: NoteInfo[];
}

// 音符信息
export interface NoteInfo {
  pitch: NotePitch;
  duration: number; // 秒
  lyric: string;
}

// 歌曲配置
export interface SongConfig {
  title: string;
  artist?: string;
  style: SingingStyle;
  tempo: number;       // BPM
  key: string;         // 调性
  lyrics: LyricLine[];
  voiceId?: string;
  effects?: SongEffects;
}

// 歌曲效果
export interface SongEffects {
  reverb: number;      // 混响 (0-1)
  echo: number;        // 回声 (0-1)
  chorus: number;      // 合唱 (0-1)
  pitch_correction: boolean; // 音高修正
  vibrato: number;     // 颤音 (0-1)
}

// 歌曲模板
export interface SongTemplate {
  id: string;
  title: string;
  style: SingingStyle;
  description: string;
  lyrics: string;
  tempo: number;
  key: string;
}

// 预设歌曲模板
const SONG_TEMPLATES: SongTemplate[] = [
  {
    id: 'twinkle_star',
    title: '小星星',
    style: 'children',
    description: '经典儿歌，适合入门',
    lyrics: '一闪一闪亮晶晶\n满天都是小星星\n挂在天空放光明\n好像许多小眼睛',
    tempo: 100,
    key: 'C',
  },
  {
    id: 'happy_birthday',
    title: '生日快乐',
    style: 'pop',
    description: '生日祝福歌曲',
    lyrics: '祝你生日快乐\n祝你生日快乐\n祝你生日快乐\n祝你生日快乐',
    tempo: 120,
    key: 'G',
  },
  {
    id: 'little_rabbit',
    title: '小兔子乖乖',
    style: 'children',
    description: '经典儿歌',
    lyrics: '小兔子乖乖\n把门儿开开\n快点儿开开\n我要进来',
    tempo: 110,
    key: 'D',
  },
  {
    id: 'spring',
    title: '春天在哪里',
    style: 'folk',
    description: '民谣风格',
    lyrics: '春天在哪里呀\n春天在哪里\n春天在那青翠的山林里',
    tempo: 108,
    key: 'F',
  },
  {
    id: 'ode_to_joy',
    title: '欢乐颂',
    style: 'classical',
    description: '贝多芬经典',
    lyrics: '欢乐女神圣洁美丽\n灿烂光芒照大地\n我们心中充满热情\n来到你的圣殿里',
    tempo: 108,
    key: 'C',
  },
];

// 唱法配置
const STYLE_CONFIGS: Record<SingingStyle, {
  name: string;
  description: string;
  icon: string;
  params: {
    vibrato: number;
    breathiness: number;
    brightness: number;
    warmth: number;
  };
}> = {
  pop: {
    name: '流行',
    description: '现代流行唱法',
    icon: '🎵',
    params: { vibrato: 0.3, breathiness: 0.2, brightness: 0.6, warmth: 0.5 },
  },
  folk: {
    name: '民谣',
    description: '自然质朴的唱法',
    icon: '🎸',
    params: { vibrato: 0.2, breathiness: 0.3, brightness: 0.4, warmth: 0.7 },
  },
  rock: {
    name: '摇滚',
    description: '有力的摇滚唱法',
    icon: '🤘',
    params: { vibrato: 0.1, breathiness: 0.1, brightness: 0.8, warmth: 0.3 },
  },
  jazz: {
    name: '爵士',
    description: '慵懒的爵士唱法',
    icon: '🎷',
    params: { vibrato: 0.4, breathiness: 0.3, brightness: 0.5, warmth: 0.6 },
  },
  classical: {
    name: '古典',
    description: '古典美声唱法',
    icon: '🎻',
    params: { vibrato: 0.5, breathiness: 0.1, brightness: 0.7, warmth: 0.4 },
  },
  rnb: {
    name: 'R&B',
    description: '节奏布鲁斯唱法',
    icon: '🎤',
    params: { vibrato: 0.3, breathiness: 0.2, brightness: 0.5, warmth: 0.6 },
  },
  rap: {
    name: '说唱',
    description: '节奏说唱',
    icon: '🎧',
    params: { vibrato: 0.0, breathiness: 0.1, brightness: 0.7, warmth: 0.3 },
  },
  children: {
    name: '儿歌',
    description: '可爱的童声唱法',
    icon: '👶',
    params: { vibrato: 0.1, breathiness: 0.2, brightness: 0.8, warmth: 0.7 },
  },
  opera: {
    name: '歌剧',
    description: '歌剧美声唱法',
    icon: '🎭',
    params: { vibrato: 0.6, breathiness: 0.0, brightness: 0.8, warmth: 0.3 },
  },
  country: {
    name: '乡村',
    description: '乡村音乐唱法',
    icon: '🤠',
    params: { vibrato: 0.3, breathiness: 0.2, brightness: 0.5, warmth: 0.6 },
  },
  electronic: {
    name: '电子',
    description: '电子音乐唱法',
    icon: '🎹',
    params: { vibrato: 0.1, breathiness: 0.1, brightness: 0.7, warmth: 0.2 },
  },
  custom: {
    name: '自定义',
    description: '自定义唱法参数',
    icon: '⚙️',
    params: { vibrato: 0.3, breathiness: 0.2, brightness: 0.5, warmth: 0.5 },
  },
};

// AI 唱歌服务类
class SingingService {
  private templates: SongTemplate[] = SONG_TEMPLATES;
  private savedSongs: SongConfig[] = [];
  private currentSong: SongConfig | null = null;
  private isPlaying = false;
  private callbacks: Array<(event: string, data: any) => void> = [];
  
  constructor() {
    this.loadSavedSongs();
  }
  
  // 加载保存的歌曲
  private loadSavedSongs(): void {
    try {
      const saved = storage.getString('saved_songs');
      if (saved) {
        this.savedSongs = JSON.parse(saved);
      }
    } catch (e) {
      console.error('Load saved songs error:', e);
    }
  }
  
  // 保存歌曲
  private saveSongs(): void {
    try {
      storage.set('saved_songs', JSON.stringify(this.savedSongs.slice(-20)));
    } catch (e) {
      console.error('Save songs error:', e);
    }
  }
  
  // 获取所有模板
  getTemplates(): SongTemplate[] {
    return [...this.templates];
  }
  
  // 获取指定模板
  getTemplate(id: string): SongTemplate | undefined {
    return this.templates.find(t => t.id === id);
  }
  
  // 获取所有唱法
  getStyles(): Array<{ style: SingingStyle; config: typeof STYLE_CONFIGS[SingingStyle] }> {
    return Object.entries(STYLE_CONFIGS).map(([style, config]) => ({
      style: style as SingingStyle,
      config,
    }));
  }
  
  // 获取唱法配置
  getStyleConfig(style: SingingStyle): typeof STYLE_CONFIGS[SingingStyle] {
    return STYLE_CONFIGS[style];
  }
  
  // 解析歌词
  parseLyrics(lyrics: string, tempo: number): LyricLine[] {
    const lines = lyrics.split('\n').filter(line => line.trim());
    const beatDuration = 60 / tempo; // 每拍时长（秒）
    
    return lines.map((text, index) => ({
      text: text.trim(),
      startTime: index * beatDuration * 4, // 每行4拍
      duration: beatDuration * 4,
      notes: this.generateNotes(text, tempo),
    }));
  }
  
  // 生成音符序列（简化版）
  private generateNotes(text: string, tempo: number): NoteInfo[] {
    const beatDuration = 60 / tempo;
    const chars = text.split('');
    const notes: NoteInfo[] = [];
    
    // 简化版：为每个字分配一个音符
    const pitches: NotePitch[] = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4'];
    
    chars.forEach((char, index) => {
      if (char.trim()) {
        notes.push({
          pitch: pitches[index % pitches.length],
          duration: beatDuration,
          lyric: char,
        });
      }
    });
    
    return notes;
  }
  
  // 创建歌曲配置
  createSong(config: Partial<SongConfig>): SongConfig {
    const defaultConfig: SongConfig = {
      title: '未命名歌曲',
      style: 'pop',
      tempo: 120,
      key: 'C',
      lyrics: [],
      effects: {
        reverb: 0.3,
        echo: 0.1,
        chorus: 0.1,
        pitch_correction: true,
        vibrato: 0.3,
      },
    };
    
    const song: SongConfig = { ...defaultConfig, ...config };
    
    // 如果提供了歌词文本，解析它
    if (config.lyrics && config.lyrics.length > 0 && typeof config.lyrics[0] === 'string') {
      song.lyrics = this.parseLyrics(config.lyrics as any, song.tempo);
    }
    
    return song;
  }
  
  // 从模板创建歌曲
  createSongFromTemplate(templateId: string, customizations?: Partial<SongConfig>): SongConfig | null {
    const template = this.getTemplate(templateId);
    if (!template) return null;
    
    const lyrics = this.parseLyrics(template.lyrics, template.tempo);
    
    return this.createSong({
      title: template.title,
      style: template.style,
      tempo: template.tempo,
      key: template.key,
      lyrics,
      ...customizations,
    });
  }
  
  // 保存歌曲
  saveSong(song: SongConfig): void {
    const existingIndex = this.savedSongs.findIndex(s => s.title === song.title);
    
    if (existingIndex >= 0) {
      this.savedSongs[existingIndex] = song;
    } else {
      this.savedSongs.push(song);
    }
    
    this.saveSongs();
  }
  
  // 获取保存的歌曲
  getSavedSongs(): SongConfig[] {
    return [...this.savedSongs];
  }
  
  // 删除歌曲
  deleteSong(title: string): boolean {
    const index = this.savedSongs.findIndex(s => s.title === title);
    if (index === -1) return false;
    
    this.savedSongs.splice(index, 1);
    this.saveSongs();
    return true;
  }
  
  // 开始播放歌曲
  async startSinging(song: SongConfig): Promise<void> {
    this.currentSong = song;
    this.isPlaying = true;
    
    this.notify('start', { song });
    
    // 模拟唱歌过程
    // 在实际实现中，这里会调用TTS服务，应用变声效果
    try {
      for (const line of song.lyrics) {
        if (!this.isPlaying) break;
        
        this.notify('line', { line });
        
        // 使用TTS朗读歌词
        await ttsService.speak(line.text, {
          rate: 0.8, // 唱歌时语速稍慢
          pitch: 1.2, // 音调稍高
        });
        
        // 等待该行时长
        await new Promise(resolve => setTimeout(resolve, line.duration * 1000));
      }
    } catch (error) {
      console.error('Singing error:', error);
    }
    
    this.stopSinging();
  }
  
  // 停止唱歌
  stopSinging(): void {
    this.isPlaying = false;
    this.currentSong = null;
    this.notify('stop', {});
  }
  
  // 检查是否正在播放
  getIsPlaying(): boolean {
    return this.isPlaying;
  }
  
  // 获取当前歌曲
  getCurrentSong(): SongConfig | null {
    return this.currentSong;
  }
  
  // 添加回调
  onEvent(callback: (event: string, data: any) => void): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }
  
  // 通知回调
  private notify(event: string, data: any): void {
    this.callbacks.forEach(cb => {
      try {
        cb(event, data);
      } catch (e) {
        console.error('Singing callback error:', e);
      }
    });
  }
  
  // 获取歌曲统计
  getSongStats(): {
    totalSongs: number;
    byStyle: Record<SingingStyle, number>;
  } {
    const byStyle: Record<SingingStyle, number> = {
      pop: 0, folk: 0, rock: 0, jazz: 0, classical: 0,
      rnb: 0, rap: 0, children: 0, opera: 0, country: 0,
      electronic: 0, custom: 0,
    };
    
    this.savedSongs.forEach(song => {
      byStyle[song.style]++;
    });
    
    return {
      totalSongs: this.savedSongs.length,
      byStyle,
    };
  }
  
  // 生成歌词（使用AI）
  async generateLyrics(theme: string, style: SingingStyle): Promise<string> {
    // 简化版：返回示例歌词
    const examples: Record<SingingStyle, string> = {
      pop: `关于${theme}的歌\n在心中回荡\n像阳光一样温暖\n照亮每个角落`,
      folk: `${theme}的故事\n在风中传唱\n简单的旋律\n深深的感动`,
      rock: `燃烧的${theme}\n激情四射\n让我们一起\n摇滚到底`,
      jazz: `${theme}的夜晚\n慵懒的旋律\n在月光下\n轻轻摇摆`,
      classical: `赞美${theme}\n神圣而美丽\n在永恒中\n回响不息`,
      rnb: `${theme}的感觉\n如此甜蜜\n在节奏中\n慢慢沉醉`,
      rap: `${theme}说唱\n节奏不停\n跟着节拍\n一起摇摆`,
      children: `小${theme}\n真可爱\n蹦蹦跳跳\n乐开怀`,
      opera: `啊~${theme}\n伟大的存在\n在舞台上\n永远闪耀`,
      country: `${theme}的乡村\n宁静而美好\n在田野间\n自由歌唱`,
      electronic: `${theme}电子\n节奏强烈\n在夜空中\n闪耀光芒`,
      custom: `${theme}自定义\n由你创造\n独特的旋律\n只属于你`,
    };
    
    return examples[style] || examples.pop;
  }
}

// 导出单例
export const singingService = new SingingService();