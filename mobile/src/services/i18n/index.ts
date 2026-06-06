// ============================================
// 国际化服务 - 移动端版本
// ============================================
import { MMKV } from 'react-native-mmkv';
import { I18nManager as RNI18nManager } from 'react-native';

const storage = new MMKV();

// 支持的语言
export type Language = 
  | 'zh-CN'    // 简体中文
  | 'zh-TW'    // 繁体中文
  | 'en-US'    // 美式英语
  | 'en-GB'    // 英式英语
  | 'ja-JP'    // 日语
  | 'ko-KR'    // 韩语
  | 'fr-FR'    // 法语
  | 'de-DE'    // 德语
  | 'es-ES'    // 西班牙语
  | 'pt-BR'    // 葡萄牙语
  | 'ru-RU'    // 俄语
  | 'ar-SA';   // 阿拉伯语

// 语言信息
export interface LanguageInfo {
  code: Language;
  name: string;
  nativeName: string;
  flag: string;
  rtl: boolean;
}

// 支持的语言列表
export const SUPPORTED_LANGUAGES: LanguageInfo[] = [
  { code: 'zh-CN', name: 'Chinese (Simplified)', nativeName: '简体中文', flag: '🇨🇳', rtl: false },
  { code: 'zh-TW', name: 'Chinese (Traditional)', nativeName: '繁體中文', flag: '🇹🇼', rtl: false },
  { code: 'en-US', name: 'English (US)', nativeName: 'English', flag: '🇺🇸', rtl: false },
  { code: 'en-GB', name: 'English (UK)', nativeName: 'English', flag: '🇬🇧', rtl: false },
  { code: 'ja-JP', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵', rtl: false },
  { code: 'ko-KR', name: 'Korean', nativeName: '한국어', flag: '🇰🇷', rtl: false },
  { code: 'fr-FR', name: 'French', nativeName: 'Français', flag: '🇫🇷', rtl: false },
  { code: 'de-DE', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪', rtl: false },
  { code: 'es-ES', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸', rtl: false },
  { code: 'pt-BR', name: 'Portuguese (Brazil)', nativeName: 'Português', flag: '🇧🇷', rtl: false },
  { code: 'ru-RU', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺', rtl: false },
  { code: 'ar-SA', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦', rtl: true },
];

// 翻译字典类型
type TranslationDictionary = Record<string, string | Record<string, string>>;

// 预设翻译
const TRANSLATIONS: Record<Language, TranslationDictionary> = {
  'zh-CN': {
    // 通用
    'common.ok': '确定',
    'common.cancel': '取消',
    'common.save': '保存',
    'common.delete': '删除',
    'common.edit': '编辑',
    'common.add': '添加',
    'common.search': '搜索',
    'common.loading': '加载中...',
    'common.error': '错误',
    'common.success': '成功',
    'common.confirm': '确认',
    'common.back': '返回',
    'common.next': '下一步',
    'common.done': '完成',
    'common.close': '关闭',
    'common.retry': '重试',
    'common.yes': '是',
    'common.no': '否',
    
    // 导航
    'nav.chat': '对话',
    'nav.characters': '角色',
    'nav.live': '直播',
    'nav.memory': '记忆',
    'nav.settings': '设置',
    
    // 聊天
    'chat.placeholder': '输入消息...',
    'chat.send': '发送',
    'chat.thinking': '思考中...',
    'chat.speaking': '说话中...',
    'chat.online': '在线',
    'chat.empty': '暂无对话',
    'chat.new': '新建对话',
    'chat.delete': '删除对话',
    'chat.clear': '清除聊天',
    
    // 角色
    'character.list': '角色列表',
    'character.add': '添加角色',
    'character.market': '角色市场',
    'character.editor': '角色编辑器',
    'character.name': '名称',
    'character.description': '描述',
    'character.personality': '性格',
    'character.greeting': '开场白',
    'character.tags': '标签',
    
    // 设置
    'settings.title': '设置',
    'settings.ai': 'AI 配置',
    'settings.tts': '语音合成',
    'settings.general': '通用',
    'settings.about': '关于',
    'settings.backup': '数据备份',
    'settings.language': '语言',
    'settings.theme': '主题',
    'settings.darkMode': '深色模式',
    
    // 游戏助手
    'game.title': '游戏助手',
    'game.select': '选择游戏',
    'game.ask': '问我任何游戏问题...',
    'game.guide': '攻略',
    'game.tips': '提示',
    
    // 视觉分析
    'vision.title': '视觉分析',
    'vision.analyze': '开始分析',
    'vision.description': '图像描述',
    'vision.result': '分析结果',
    'vision.history': '分析历史',
    
    // 多Agent
    'multiAgent.title': '多角色讨论',
    'multiAgent.start': '开始讨论',
    'multiAgent.mode': '讨论模式',
    
    // 语音通话
    'voiceCall.title': '语音通话',
    'voiceCall.start': '开始通话',
    'voiceCall.end': '结束通话',
    'voiceCall.mute': '静音',
    
    // 消息搜索
    'search.title': '搜索消息',
    'search.placeholder': '搜索对话历史...',
    'search.history': '搜索历史',
    'search.popular': '热门搜索',
    
    // 群聊
    'groupChat.title': '多角色群聊',
    'groupChat.scenario': '选择场景',
    'groupChat.custom': '自定义群聊',
    
    // 模型选择
    'model.title': '模型选择',
    'model.download': '下载',
    'model.select': '选择',
    'model.downloading': '下载中...',
  },
  
  'en-US': {
    // Common
    'common.ok': 'OK',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.add': 'Add',
    'common.search': 'Search',
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.success': 'Success',
    'common.confirm': 'Confirm',
    'common.back': 'Back',
    'common.next': 'Next',
    'common.done': 'Done',
    'common.close': 'Close',
    'common.retry': 'Retry',
    'common.yes': 'Yes',
    'common.no': 'No',
    
    // Navigation
    'nav.chat': 'Chat',
    'nav.characters': 'Characters',
    'nav.live': 'Live',
    'nav.memory': 'Memory',
    'nav.settings': 'Settings',
    
    // Chat
    'chat.placeholder': 'Type a message...',
    'chat.send': 'Send',
    'chat.thinking': 'Thinking...',
    'chat.speaking': 'Speaking...',
    'chat.online': 'Online',
    'chat.empty': 'No conversations yet',
    'chat.new': 'New Chat',
    'chat.delete': 'Delete Chat',
    'chat.clear': 'Clear Chat',
    
    // Character
    'character.list': 'Character List',
    'character.add': 'Add Character',
    'character.market': 'Character Market',
    'character.editor': 'Character Editor',
    'character.name': 'Name',
    'character.description': 'Description',
    'character.personality': 'Personality',
    'character.greeting': 'Greeting',
    'character.tags': 'Tags',
    
    // Settings
    'settings.title': 'Settings',
    'settings.ai': 'AI Configuration',
    'settings.tts': 'Text to Speech',
    'settings.general': 'General',
    'settings.about': 'About',
    'settings.backup': 'Data Backup',
    'settings.language': 'Language',
    'settings.theme': 'Theme',
    'settings.darkMode': 'Dark Mode',
    
    // Game Assistant
    'game.title': 'Game Assistant',
    'game.select': 'Select Game',
    'game.ask': 'Ask me any game question...',
    'game.guide': 'Guide',
    'game.tips': 'Tips',
    
    // Vision
    'vision.title': 'Vision Analysis',
    'vision.analyze': 'Start Analysis',
    'vision.description': 'Image Description',
    'vision.result': 'Analysis Result',
    'vision.history': 'Analysis History',
    
    // Multi-Agent
    'multiAgent.title': 'Multi-Agent Discussion',
    'multiAgent.start': 'Start Discussion',
    'multiAgent.mode': 'Discussion Mode',
    
    // Voice Call
    'voiceCall.title': 'Voice Call',
    'voiceCall.start': 'Start Call',
    'voiceCall.end': 'End Call',
    'voiceCall.mute': 'Mute',
    
    // Search
    'search.title': 'Search Messages',
    'search.placeholder': 'Search conversation history...',
    'search.history': 'Search History',
    'search.popular': 'Popular Searches',
    
    // Group Chat
    'groupChat.title': 'Group Chat',
    'groupChat.scenario': 'Select Scenario',
    'groupChat.custom': 'Custom Group',
    
    // Model Selection
    'model.title': 'Model Selection',
    'model.download': 'Download',
    'model.select': 'Select',
    'model.downloading': 'Downloading...',
  },
  
  'ja-JP': {
    // 共通
    'common.ok': 'OK',
    'common.cancel': 'キャンセル',
    'common.save': '保存',
    'common.delete': '削除',
    'common.edit': '編集',
    'common.add': '追加',
    'common.search': '検索',
    'common.loading': '読み込み中...',
    'common.error': 'エラー',
    'common.success': '成功',
    'common.confirm': '確認',
    'common.back': '戻る',
    'common.next': '次へ',
    'common.done': '完了',
    'common.close': '閉じる',
    'common.retry': '再試行',
    'common.yes': 'はい',
    'common.no': 'いいえ',
    
    // ナビゲーション
    'nav.chat': 'チャット',
    'nav.characters': 'キャラクター',
    'nav.live': 'ライブ',
    'nav.memory': 'メモリ',
    'nav.settings': '設定',
    
    // チャット
    'chat.placeholder': 'メッセージを入力...',
    'chat.send': '送信',
    'chat.thinking': '考え中...',
    'chat.speaking': '話中...',
    'chat.online': 'オンライン',
    'chat.empty': '会話がありません',
    'chat.new': '新しいチャット',
    'chat.delete': 'チャットを削除',
    'chat.clear': 'チャットをクリア',
    
    // キャラクター
    'character.list': 'キャラクターリスト',
    'character.add': 'キャラクター追加',
    'character.market': 'キャラクターマーケット',
    'character.editor': 'キャラクターエディター',
    'character.name': '名前',
    'character.description': '説明',
    'character.personality': '性格',
    'character.greeting': '挨拶',
    'character.tags': 'タグ',
    
    // 設定
    'settings.title': '設定',
    'settings.ai': 'AI設定',
    'settings.tts': '音声合成',
    'settings.general': '一般',
    'settings.about': 'アプリについて',
    'settings.backup': 'データバックアップ',
    'settings.language': '言語',
    'settings.theme': 'テーマ',
    'settings.darkMode': 'ダークモード',
  },
  
  'ko-KR': {
    // 공통
    'common.ok': '확인',
    'common.cancel': '취소',
    'common.save': '저장',
    'common.delete': '삭제',
    'common.edit': '편집',
    'common.add': '추가',
    'common.search': '검색',
    'common.loading': '로딩 중...',
    'common.error': '오류',
    'common.success': '성공',
    'common.confirm': '확인',
    'common.back': '뒤로',
    'common.next': '다음',
    'common.done': '완료',
    'common.close': '닫기',
    'common.retry': '재시도',
    'common.yes': '예',
    'common.no': '아니요',
    
    // 네비게이션
    'nav.chat': '채팅',
    'nav.characters': '캐릭터',
    'nav.live': '라이브',
    'nav.memory': '메모리',
    'nav.settings': '설정',
    
    // 채팅
    'chat.placeholder': '메시지를 입력하세요...',
    'chat.send': '보내기',
    'chat.thinking': '생각 중...',
    'chat.speaking': '말하는 중...',
    'chat.online': '온라인',
    'chat.empty': '대화가 없습니다',
    'chat.new': '새 채팅',
    'chat.delete': '채팅 삭제',
    'chat.clear': '채팅 지우기',
    
    // 캐릭터
    'character.list': '캐릭터 목록',
    'character.add': '캐릭터 추가',
    'character.market': '캐릭터 마켓',
    'character.editor': '캐릭터 편집기',
    'character.name': '이름',
    'character.description': '설명',
    'character.personality': '성격',
    'character.greeting': '인사',
    'character.tags': '태그',
    
    // 설정
    'settings.title': '설정',
    'settings.ai': 'AI 설정',
    'settings.tts': '음성 합성',
    'settings.general': '일반',
    'settings.about': '정보',
    'settings.backup': '데이터 백업',
    'settings.language': '언어',
    'settings.theme': '테마',
    'settings.darkMode': '다크 모드',
  },
  
  // 其他语言使用英文作为回退
  'zh-TW': {}, // 繁体中文 - 后续补充
  'en-GB': {}, // 英式英语 - 使用美式英语
  'fr-FR': {}, // 法语 - 后续补充
  'de-DE': {}, // 德语 - 后续补充
  'es-ES': {}, // 西班牙语 - 后续补充
  'pt-BR': {}, // 葡萄牙语 - 后续补充
  'ru-RU': {}, // 俄语 - 后续补充
  'ar-SA': {}, // 阿拉伯语 - 后续补充
};

// 国际化管理器类
class I18nManager {
  private currentLanguage: Language = 'zh-CN';
  private translations: Record<Language, TranslationDictionary> = TRANSLATIONS;
  private callbacks: Array<(language: Language) => void> = [];
  
  constructor() {
    this.loadSavedLanguage();
  }
  
  // 加载保存的语言
  private loadSavedLanguage(): void {
    try {
      const saved = storage.getString('app_language');
      if (saved && this.isValidLanguage(saved)) {
        this.currentLanguage = saved as Language;
      } else {
        // 尝试获取系统语言
        const systemLanguage = this.getSystemLanguage();
        if (systemLanguage) {
          this.currentLanguage = systemLanguage;
        }
      }
    } catch (e) {
      console.error('Load language error:', e);
    }
  }
  
  // 获取系统语言
  private getSystemLanguage(): Language | null {
    try {
      // React Native I18nManager 没有 localeIdentifier 属性
      // 使用其他方式获取系统语言，或者默认返回中文
      return 'zh-CN';
    } catch (e) {
      console.error('Get system language error:', e);
    }
    return null;
  }
  
  // 验证语言代码是否有效
  private isValidLanguage(code: string): boolean {
    return SUPPORTED_LANGUAGES.some(l => l.code === code);
  }
  
  // 设置语言
  setLanguage(language: Language): void {
    this.currentLanguage = language;
    storage.set('app_language', language);
    
    // 通知回调
    this.callbacks.forEach(cb => {
      try {
        cb(language);
      } catch (e) {
        console.error('Language callback error:', e);
      }
    });
  }
  
  // 获取当前语言
  getCurrentLanguage(): Language {
    return this.currentLanguage;
  }
  
  // 获取当前语言信息
  getCurrentLanguageInfo(): LanguageInfo {
    return SUPPORTED_LANGUAGES.find(l => l.code === this.currentLanguage) || SUPPORTED_LANGUAGES[0];
  }
  
  // 添加语言变更回调
  onLanguageChange(callback: (language: Language) => void): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }
  
  // 获取翻译文本
  t(key: string, params?: Record<string, string | number>): string {
    const langCode = this.currentLanguage;
    
    // 尝试获取当前语言的翻译
    let text = this.getTranslation(langCode, key);
    
    // 如果没有，回退到英文
    if (!text && langCode !== 'en-US') {
      text = this.getTranslation('en-US', key);
    }
    
    // 如果还没有，回退到简体中文
    if (!text && langCode !== 'zh-CN') {
      text = this.getTranslation('zh-CN', key);
    }
    
    // 如果还是没有，返回key
    if (!text) {
      return key;
    }
    
    // 替换参数
    if (params) {
      Object.entries(params).forEach(([paramKey, paramValue]) => {
        text = text!.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramValue));
      });
    }
    
    return text;
  }
  
  // 获取翻译
  private getTranslation(langCode: Language, key: string): string | null {
    const translations = this.translations[langCode];
    if (!translations) {
      return null;
    }
    
    // 支持嵌套key，如 'chat.placeholder'
    const keys = key.split('.');
    let value: any = translations;
    
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return null;
      }
    }
    
    return typeof value === 'string' ? value : null;
  }
  
  // 获取支持的语言列表
  getSupportedLanguages(): LanguageInfo[] {
    return [...SUPPORTED_LANGUAGES];
  }
  
  // 检查是否是RTL语言
  isRTL(): boolean {
    const langInfo = this.getCurrentLanguageInfo();
    return langInfo.rtl;
  }
  
  // 添加翻译
  addTranslation(language: Language, key: string, value: string): void {
    if (!this.translations[language]) {
      this.translations[language] = {};
    }
    
    // 支持嵌套key
    const keys = key.split('.');
    let current: any = this.translations[language];
    
    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i];
      if (!current[k] || typeof current[k] !== 'object') {
        current[k] = {};
      }
      current = current[k];
    }
    
    current[keys[keys.length - 1]] = value;
  }
  
  // 批量添加翻译
  addTranslations(language: Language, translations: Record<string, string>): void {
    Object.entries(translations).forEach(([key, value]) => {
      this.addTranslation(language, key, value);
    });
  }
}

// 导出单例
export const i18n = new I18nManager();