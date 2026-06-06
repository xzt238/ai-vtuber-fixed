/**
 * 对话相关类型定义
 */

// 消息角色
export type MessageRole = 'user' | 'assistant' | 'system';

// 消息类型
export type MessageType = 'text' | 'voice' | 'image' | 'system';

// 对话消息
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  type: MessageType;
  timestamp: number;
  characterId?: string;
  isStreaming?: boolean;
  error?: string;
}

// 对话会话
export interface ChatSession {
  id: string;
  characterId: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

// 对话请求参数
export interface ChatRequest {
  message: string;
  characterId: string;
  sessionId?: string;
  history?: ChatMessage[];
}

// 对话响应
export interface ChatResponse {
  success: boolean;
  message?: string;
  error?: string;
}
