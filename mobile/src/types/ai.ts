/**
 * AI 相关类型定义
 */

// AI 供应商类型
export type AIProvider = 'openai' | 'anthropic' | 'local' | 'custom';

// AI 模型配置
export interface AIModelConfig {
  provider: AIProvider;
  modelId: string;
  apiKey?: string;
  baseUrl?: string;
  maxTokens: number;
  temperature: number;
}

// 任务类型
export type AITaskType = 'chat' | 'completion' | 'embedding' | 'tts' | 'stt';

// AI 任务
export interface AITask {
  type: AITaskType;
  input: string;
  config?: Partial<AIModelConfig>;
  characterId?: string;
}

// AI 响应
export interface AIResponse {
  success: boolean;
  output?: string;
  error?: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

// 云端 LLM 对接配置
export interface CloudLLMConfig {
  provider: AIProvider;
  apiKey: string;
  baseUrl: string;
  model: string;
  maxTokens: number;
  temperature: number;
}
