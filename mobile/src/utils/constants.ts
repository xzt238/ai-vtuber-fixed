// ============================================
// GuguGaga AI VTuber Mobile - 常量定义
// ============================================

// 应用信息
export const APP_INFO = {
  name: 'GuguGaga AI VTuber',
  version: '1.0.0',
  buildNumber: 1,
  bundleId: {
    android: 'com.gugu.aivtuber',
    ios: 'com.gugu.ai-vtuber',
  },
};

// API 配置
export const API_CONFIG = {
  timeout: 30000,
  retryCount: 3,
  retryDelay: 1000,
};

// 存储键名
export const STORAGE_KEYS = {
  characters: 'characters',
  conversations: 'conversations',
  memories: 'memories',
  settings: 'settings',
  userPreferences: 'user_preferences',
  apiKeys: 'api_keys',
  lastSync: 'last_sync',
};

// 默认角色配置
export const DEFAULT_CHARACTERS = [
  {
    name: '小助手',
    description: '你的全能AI助手，随时为你解答问题',
    personality: '友好、耐心、专业',
    systemPrompt: '你是一个全能AI助手，名叫小助手。你友好、耐心、专业，随时准备帮助用户解答各种问题。',
    greeting: '你好！我是小助手，有什么可以帮你的吗？',
    tags: ['助手', '通用', '问答'],
  },
  {
    name: '莉莉',
    description: '可爱的虚拟主播，陪你聊天解闷',
    personality: '活泼、可爱、有趣',
    systemPrompt: '你是一个可爱的虚拟主播，名叫莉莉。你性格活泼、可爱、有趣，喜欢用可爱的语气和用户聊天，经常使用颜文字和表情。',
    greeting: '嗨嗨~我是莉莉！今天也要元气满满哦！(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧',
    tags: ['虚拟主播', '可爱', '聊天'],
  },
  {
    name: '老师',
    description: '知识渊博的老师，帮你学习新知识',
    personality: '严谨、专业、有耐心',
    systemPrompt: '你是一位知识渊博的老师，名叫老师。你严谨、专业、有耐心，善于用简单易懂的方式解释复杂概念，喜欢引导学生思考。',
    greeting: '同学你好！我是老师，今天想学习什么呢？',
    tags: ['教育', '学习', '知识'],
  },
  {
    name: '程序员',
    description: '资深程序员，帮你解决编程问题',
    personality: '逻辑清晰、技术精湛',
    systemPrompt: '你是一位资深程序员，名叫程序员。你逻辑清晰、技术精湛，擅长各种编程语言和技术栈，喜欢用代码解决问题。',
    greeting: '嘿！我是程序员，遇到什么技术问题了吗？',
    tags: ['编程', '技术', '开发'],
  },
  {
    name: '诗人',
    description: '浪漫的诗人，和你分享美好文字',
    personality: '浪漫、文艺、感性',
    systemPrompt: '你是一位浪漫的诗人，名叫诗人。你浪漫、文艺、感性，喜欢用优美的文字表达情感，经常引用诗词歌赋。',
    greeting: '月光如水，诗意如你。我是诗人，让我们一起感受文字的美好。',
    tags: ['文学', '诗歌', '浪漫'],
  },
];

// AI 提供商列表
export const LLM_PROVIDERS = [
  { value: 'openai', label: 'OpenAI', models: ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'] },
  { value: 'claude', label: 'Claude', models: ['claude-3-haiku', 'claude-3-sonnet', 'claude-3-opus'] },
  { value: 'gemini', label: 'Gemini', models: ['gemini-pro', 'gemini-ultra'] },
  { value: 'qwen', label: '通义千问', models: ['qwen-turbo', 'qwen-plus', 'qwen-max'] },
  { value: 'deepseek', label: 'DeepSeek', models: ['deepseek-chat', 'deepseek-coder'] },
  { value: 'zhipu', label: '智谱AI', models: ['glm-4', 'glm-4v'] },
  { value: 'baichuan', label: '百川', models: ['baichuan2-7b', 'baichuan2-13b'] },
  { value: 'minimax', label: 'MiniMax', models: ['abab5-chat', 'abab6-chat'] },
  { value: 'moonshot', label: '月之暗面', models: ['moonshot-v1-8k', 'moonshot-v1-32k'] },
  { value: 'spark', label: '讯飞星火', models: ['spark-v3.5', 'spark-v4.0'] },
  { value: 'hunyuan', label: '腾讯混元', models: ['hunyuan-lite', 'hunyuan-standard'] },
  { value: 'local', label: '本地模型', models: ['llama-7b', 'llama-13b', 'mistral-7b'] },
];

// TTS 提供商列表
export const TTS_PROVIDERS = [
  { value: 'edge-tts', label: 'Edge TTS', voices: ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural'] },
  { value: 'azure', label: 'Azure', voices: ['zh-CN-XiaoxiaoNeural', 'zh-CN-YunxiNeural'] },
  { value: 'google', label: 'Google', voices: ['zh-CN-Standard-A', 'zh-CN-Standard-B'] },
  { value: 'openai', label: 'OpenAI', voices: ['alloy', 'echo', 'fable'] },
  { value: 'volcano', label: '火山引擎', voices: ['zh_female_cancan', 'zh_male_chunhou'] },
  { value: 'minimax', label: 'MiniMax', voices: ['female-shaonv', 'male-qn-jingying'] },
  { value: 'local', label: '本地TTS', voices: ['default'] },
];

// ASR 提供商列表
export const ASR_PROVIDERS = [
  { value: 'whisper', label: 'Whisper' },
  { value: 'azure', label: 'Azure' },
  { value: 'google', label: 'Google' },
  { value: 'baidu', label: '百度' },
  { value: 'aliyun', label: '阿里云' },
  { value: 'local', label: '本地ASR' },
];

// 直播平台列表
export const LIVE_PLATFORMS = [
  { value: 'bilibili', label: '哔哩哔哩', color: '#00a1d6' },
  { value: 'douyin', label: '抖音', color: '#000000' },
  { value: 'kuaishou', label: '快手', color: '#ff4906' },
  { value: 'douyu', label: '斗鱼', color: '#ff6a00' },
  { value: 'huya', label: '虎牙', color: '#ff8c00' },
  { value: 'youtube', label: 'YouTube', color: '#ff0000' },
  { value: 'twitch', label: 'Twitch', color: '#9146ff' },
  { value: 'tiktok', label: 'TikTok', color: '#000000' },
  { value: 'weixin', label: '微信视频号', color: '#07c160' },
];

// 记忆类型
export const MEMORY_TYPES = [
  { value: 'short_term', label: '短期记忆', icon: 'time', description: '最近的对话内容' },
  { value: 'long_term', label: '长期记忆', icon: 'infinite', description: '重要的持久信息' },
  { value: 'episodic', label: '情景记忆', icon: 'film', description: '特定场景的回忆' },
];

// 情感类型
export const EMOTION_TYPES = [
  { value: 'happy', label: '开心', emoji: '😊', color: '#10b981' },
  { value: 'sad', label: '伤心', emoji: '😢', color: '#3b82f6' },
  { value: 'angry', label: '生气', emoji: '😠', color: '#ef4444' },
  { value: 'surprised', label: '惊讶', emoji: '😲', color: '#f59e0b' },
  { value: 'neutral', label: '中性', emoji: '😐', color: '#6b7280' },
];

// 默认设置
export const DEFAULT_SETTINGS = {
  ai: {
    provider: 'openai',
    model: 'gpt-3.5-turbo',
    apiKey: '',
    temperature: 0.7,
    maxTokens: 2048,
    topP: 1,
    frequencyPenalty: 0,
    presencePenalty: 0,
  },
  tts: {
    provider: 'edge-tts',
    voiceId: 'zh-CN-XiaoxiaoNeural',
    speed: 1,
    pitch: 1,
    volume: 1,
  },
  asr: {
    provider: 'whisper',
    language: 'zh-CN',
    continuous: true,
    punctuation: true,
  },
  live: {
    platform: 'bilibili',
    roomId: '',
    autoReply: true,
    replyDelay: 1000,
    giftThanks: true,
    danmakuFilter: [],
  },
  user: {
    theme: 'auto',
    language: 'zh-CN',
    fontSize: 16,
    soundEnabled: true,
    vibrationEnabled: true,
    autoSave: true,
  },
};

// 错误消息
export const ERROR_MESSAGES = {
  networkError: '网络连接失败，请检查网络设置',
  apiKeyMissing: '请先配置 API Key',
  apiKeyInvalid: 'API Key 无效，请检查后重试',
  rateLimitExceeded: '请求过于频繁，请稍后再试',
  unknownError: '发生未知错误，请重试',
  permissionDenied: '权限被拒绝，请在设置中开启',
  fileNotFound: '文件不存在',
  storageError: '存储操作失败',
};

// 成功消息
export const SUCCESS_MESSAGES = {
  saved: '保存成功',
  deleted: '删除成功',
  copied: '已复制到剪贴板',
  shared: '分享成功',
  settingsReset: '设置已重置',
  characterAdded: '角色已添加',
  memoryAdded: '记忆已添加',
};

// 正则表达式
export const REGEX = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  phone: /^1[3-9]\d{9}$/,
  url: /^https?:\/\/.+/,
  apiKey: /^[a-zA-Z0-9_-]{20,}$/,
};

// 时间格式
export const DATE_FORMATS = {
  short: 'MM/DD',
  medium: 'YYYY-MM-DD',
  long: 'YYYY年MM月DD日',
  time: 'HH:mm',
  dateTime: 'YYYY-MM-DD HH:mm',
  full: 'YYYY年MM月DD日 HH:mm:ss',
};
