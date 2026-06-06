// ============================================
// GuguGaga AI VTuber Mobile - 情感分析服务
// ============================================

export type Emotion = 'happy' | 'sad' | 'angry' | 'surprised' | 'neutral' | 'fear' | 'disgust';

interface EmotionResult {
  emotion: Emotion;
  confidence: number;
  keywords: string[];
}

// 情感关键词库
const EMOTION_KEYWORDS: Record<Emotion, string[]> = {
  happy: ['开心', '高兴', '快乐', '太好了', '棒', '赞', '哈哈', '嘻嘻', '耶', '好开心', '幸福', '满意', '喜欢', '爱', '感谢', '谢谢', '好的', '没问题', '可以', '当然'],
  sad: ['伤心', '难过', '哭', '呜呜', '不开心', '失望', '遗憾', '可惜', '想念', '思念', '孤独', '寂寞', '心痛', '悲伤', '忧伤', '难过', '不好', '糟糕'],
  angry: ['生气', '愤怒', '烦', '讨厌', '气死', '恨', '恼火', '暴躁', '火大', '可恶', '混蛋', '白痴', '笨蛋', '垃圾', '废物', '恶心'],
  surprised: ['惊讶', '哇', '天啊', '不会吧', '真的吗', '不可思议', '难以置信', '震惊', '意外', '惊喜', '吓我', '吓死', '我的天', '妈呀'],
  fear: ['害怕', '恐惧', '担心', '焦虑', '紧张', '不安', '恐', '怕', '吓', '危险', '威胁', '可怕'],
  disgust: ['恶心', '讨厌', '厌恶', '反感', '呕', '吐', '受不了', '忍不了', '够了'],
  neutral: ['嗯', '好的', '知道了', '明白', '了解', '哦', '这样', '是吗', '好吧'],
};

// 情感表情符号映射
export const EMOTION_EMOJI: Record<Emotion, string> = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😲',
  fear: '😨',
  disgust: '🤢',
  neutral: '😐',
};

// 情感颜色映射
export const EMOTION_COLOR: Record<Emotion, string> = {
  happy: '#10b981',
  sad: '#3b82f6',
  angry: '#ef4444',
  surprised: '#f59e0b',
  fear: '#8b5cf6',
  disgust: '#6b7280',
  neutral: '#6b7280',
};

export class EmotionService {
  private static instance: EmotionService;
  private emotionHistory: Array<{ emotion: Emotion; timestamp: Date }> = [];

  private constructor() {}

  static getInstance(): EmotionService {
    if (!EmotionService.instance) {
      EmotionService.instance = new EmotionService();
    }
    return EmotionService.instance;
  }

  // ============================================
  // 文本情感分析
  // ============================================
  analyze(text: string): EmotionResult {
    const lowerText = text.toLowerCase();
    const scores: Record<Emotion, number> = {
      happy: 0, sad: 0, angry: 0, surprised: 0,
      fear: 0, disgust: 0, neutral: 0,
    };
    const matchedKeywords: string[] = [];

    // 计算每种情感的得分
    for (const [emotion, keywords] of Object.entries(EMOTION_KEYWORDS)) {
      for (const keyword of keywords) {
        if (lowerText.includes(keyword)) {
          scores[emotion as Emotion] += 1;
          matchedKeywords.push(keyword);
        }
      }
    }

    // 特殊规则
    if (text.includes('！') || text.includes('!')) {
      scores.surprised += 0.5;
    }
    if (text.includes('？') || text.includes('?')) {
      scores.neutral += 0.3;
    }
    if (text.length < 5) {
      scores.neutral += 1;
    }

    // 找出最高分的情感
    let maxEmotion: Emotion = 'neutral';
    let maxScore = scores.neutral;

    for (const [emotion, score] of Object.entries(scores)) {
      if (score > maxScore) {
        maxScore = score;
        maxEmotion = emotion as Emotion;
      }
    }

    // 计算置信度
    const totalScore = Object.values(scores).reduce((a, b) => a + b, 0);
    const confidence = totalScore > 0 ? maxScore / totalScore : 0.5;

    // 记录历史
    this.emotionHistory.push({ emotion: maxEmotion, timestamp: new Date() });
    if (this.emotionHistory.length > 100) {
      this.emotionHistory = this.emotionHistory.slice(-100);
    }

    return {
      emotion: maxEmotion,
      confidence: Math.min(confidence, 1),
      keywords: [...new Set(matchedKeywords)],
    };
  }

  // ============================================
  // 获取情感对应的语音参数
  // ============================================
  getVoiceParams(emotion: Emotion): { pitch: number; rate: number; volume: number } {
    const params: Record<Emotion, { pitch: number; rate: number; volume: number }> = {
      happy: { pitch: 1.2, rate: 1.1, volume: 1.0 },
      sad: { pitch: 0.8, rate: 0.85, volume: 0.8 },
      angry: { pitch: 1.3, rate: 1.2, volume: 1.1 },
      surprised: { pitch: 1.4, rate: 1.15, volume: 1.0 },
      fear: { pitch: 1.1, rate: 1.3, volume: 0.9 },
      disgust: { pitch: 0.9, rate: 0.95, volume: 0.85 },
      neutral: { pitch: 1.0, rate: 1.0, volume: 1.0 },
    };
    return params[emotion];
  }

  // ============================================
  // 获取情感统计
  // ============================================
  getEmotionStats(): Record<Emotion, number> {
    const stats: Record<Emotion, number> = {
      happy: 0, sad: 0, angry: 0, surprised: 0,
      fear: 0, disgust: 0, neutral: 0,
    };
    for (const item of this.emotionHistory) {
      stats[item.emotion]++;
    }
    return stats;
  }

  // 获取主要情感
  getDominantEmotion(): Emotion {
    const stats = this.getEmotionStats();
    let maxEmotion: Emotion = 'neutral';
    let maxCount = 0;
    for (const [emotion, count] of Object.entries(stats)) {
      if (count > maxCount) {
        maxCount = count;
        maxEmotion = emotion as Emotion;
      }
    }
    return maxEmotion;
  }

  // 清除历史
  clearHistory(): void {
    this.emotionHistory = [];
  }
}

export const emotionService = EmotionService.getInstance();
