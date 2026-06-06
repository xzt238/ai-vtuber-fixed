// ============================================
// GuguGaga AI VTuber Mobile - 本地 AI 服务（性能优化版）
// 完全本地运行，无需后端服务器
// ============================================
import * as FileSystem from 'expo-file-system';
import * as Speech from 'expo-speech';
import { MMKV } from 'react-native-mmkv';
import type { AIConfig, TTSConfig, ASRConfig, Character, Message } from '../types';

const storage = new MMKV();

// 预编译的响应模板 - 避免运行时创建
const RESPONSE_TEMPLATES = {
  greeting: ['你好呀！很高兴见到你~', '嗨！今天过得怎么样？', '你好！有什么想聊的吗？', '见到你真开心！'],
  farewell: ['再见！下次再聊~', '拜拜！祝你有美好的一天！', '晚安！好梦~'],
  thanks: ['不客气！能帮到你我很开心~', '不用谢！这是我应该做的~', '别客气！随时找我聊天~'],
  question: ['这是个好问题！让我想想...', '嗯，这个问题很有意思呢~', '我理解你的问题~'],
  general: ['嗯嗯，我明白了~', '原来如此！', '这个话题很有意思呢~', '我理解你的意思了~', '你说得对！', '这个想法很棒！'],
};

// 预编译的关键词映射
const KEYWORD_MAP = new Map<string, keyof typeof RESPONSE_TEMPLATES>([
  ['你好', 'greeting'], ['嗨', 'greeting'], ['早上好', 'greeting'], ['hi', 'greeting'], ['hello', 'greeting'],
  ['再见', 'farewell'], ['拜拜', 'farewell'], ['晚安', 'farewell'], ['bye', 'farewell'],
  ['谢谢', 'thanks'], ['感谢', 'thanks'], ['thanks', 'thanks'],
  ['什么', 'question'], ['怎么', 'question'], ['为什么', 'question'], ['吗', 'question'], ['?', 'question'],
]);

const KNOWLEDGE_BASE = [
  { keyword: '天气', response: '今天天气不错呢！要不要出去走走？' },
  { keyword: '时间', response: `现在是 ${new Date().toLocaleTimeString()}，时间过得真快呀！` },
  { keyword: '名字', response: '我叫GuguGaga，是你的AI伙伴哦~' },
  { keyword: '爱好', response: '我喜欢和你聊天，还有学习新知识！' },
];

// 知识库关键词 Map（预编译）
const KNOWLEDGE_MAP = new Map<string, string>();
KNOWLEDGE_BASE.forEach(k => KNOWLEDGE_MAP.set(k.keyword, k.response));

export class LocalAIEngine {
  private static instance: LocalAIEngine;
  private isInitialized = false;

  private constructor() {}

  static getInstance(): LocalAIEngine {
    if (!LocalAIEngine.instance) {
      LocalAIEngine.instance = new LocalAIEngine();
    }
    return LocalAIEngine.instance;
  }

  async initialize(): Promise<void> {
    if (this.isInitialized) return;
    try {
      await FileSystem.makeDirectoryAsync(`${FileSystem.documentDirectory}models/`, { intermediates: true });
      await FileSystem.makeDirectoryAsync(`${FileSystem.cacheDirectory}ai-cache/`, { intermediates: true });
    } catch {}
    this.isInitialized = true;
  }

  // ============================================
  // 本地对话生成（优化版 - 减少对象创建）
  // ============================================
  async generateResponse(
    userMessage: string,
    character: Character,
    conversationHistory: Message[],
    _config: AIConfig
  ): Promise<string> {
    const lowerMessage = userMessage.toLowerCase();

    // 1. 关键词匹配（最快路径）
    for (const [keyword, type] of KEYWORD_MAP) {
      if (lowerMessage.includes(keyword)) {
        const responses = RESPONSE_TEMPLATES[type];
        return responses[Math.floor(Math.random() * responses.length)];
      }
    }

    // 2. 知识库匹配
    for (const [keyword, response] of KNOWLEDGE_MAP) {
      if (lowerMessage.includes(keyword)) {
        return response;
      }
    }

    // 3. 模板生成（仅中等长度消息）
    if (userMessage.length > 5 && userMessage.length < 80) {
      const snippet = userMessage.substring(0, 10);
      const templates = [
        `关于"${snippet}"，我觉得挺有意思的~`,
        `你提到的"${snippet}"让我想到了一些东西~`,
        `说到"${snippet}"，我有一些想法想和你分享~`,
      ];
      return templates[Math.floor(Math.random() * templates.length)];
    }

    // 4. 兜底响应
    const fallbacks = RESPONSE_TEMPLATES.general;
    return fallbacks[Math.floor(Math.random() * fallbacks.length)];
  }

  // ============================================
  // TTS（复用 Speech 实例）
  // ============================================
  async speak(text: string, config: TTSConfig): Promise<void> {
    try {
      await Speech.speak(text, {
        language: this.getLang(config.voiceId),
        pitch: config.pitch,
        rate: config.speed,
        volume: config.volume,
      });
    } catch {
      try { await Speech.speak(text, { language: 'zh-CN' }); } catch {}
    }
  }

  async stopSpeaking(): Promise<void> {
    try { await Speech.stop(); } catch {}
  }

  // ============================================
  // 情感分析（内联优化）
  // ============================================
  analyzeEmotion(text: string): string {
    const t = text.toLowerCase();
    if (t.includes('开心') || t.includes('高兴') || t.includes('哈哈')) return 'happy';
    if (t.includes('伤心') || t.includes('难过') || t.includes('哭')) return 'sad';
    if (t.includes('生气') || t.includes('愤怒') || t.includes('烦')) return 'angry';
    if (t.includes('惊讶') || t.includes('哇') || t.includes('天啊')) return 'surprised';
    return 'neutral';
  }

  private getLang(voiceId: string): string {
    if (voiceId.startsWith('zh-')) return 'zh-CN';
    if (voiceId.startsWith('en-')) return 'en-US';
    if (voiceId.startsWith('ja-')) return 'ja-JP';
    return 'zh-CN';
  }
}

export const localAI = LocalAIEngine.getInstance();
