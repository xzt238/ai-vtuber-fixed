// ============================================
// GuguGaga AI VTuber Mobile - 服务统一导出
// ============================================

export { localAI } from './localAI';
export { apiService } from './api';
export { APIFactory, OpenAIClient, ClaudeClient, GenericLLMClient } from './api';

// TTS 语音合成
export { ttsService, VOICE_PRESETS } from './tts';

// ASR 语音识别
export { asrService } from './asr';

// RAG 知识库
export { ragService } from './rag';

// 情感分析
export { emotionService, EMOTION_EMOJI, EMOTION_COLOR } from './emotion';
export type { Emotion } from './emotion';

// 文生图
export { imageGenService } from './imageGen';
