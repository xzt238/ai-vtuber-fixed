/**
 * AI 引擎
 *
 * 统一的 AI 任务处理入口，支持多模型源切换
 */

import { AITask, AIResponse } from '../../types/ai';
import { ChatMessage } from '../../types/chat';
import { cloudModel } from './cloudModel';
import { taskRouter, ModelSource } from './taskRouter';
import { ApiService } from '../api';
import { localAI } from '../localAI';

class AIEngine {
  // 发送对话消息
  async chat(
    message: string,
    characterId: string,
    history: ChatMessage[] = [],
    systemPrompt?: string
  ): Promise<{ content: string; source: ModelSource }> {
    const task: AITask = {
      type: 'chat',
      input: message,
      characterId,
    };

    const source = taskRouter.resolve(task);

    switch (source) {
      case 'cloud':
        return this.cloudChat(message, history, systemPrompt);
      case 'server':
        return this.serverChat(message, characterId);
      case 'local':
        return this.localChat(message);
    }
  }

  // 云端 LLM 对话
  private async cloudChat(
    message: string,
    history: ChatMessage[],
    systemPrompt?: string
  ): Promise<{ content: string; source: ModelSource }> {
    const messages = [
      ...(systemPrompt
        ? [{ role: 'system' as const, content: systemPrompt }]
        : []),
      ...history.slice(-20).map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })),
      { role: 'user' as const, content: message },
    ];

    const response = await cloudModel.chat({ messages });
    return { content: response.content, source: 'cloud' };
  }

  // 服务器对话
  private async serverChat(
    message: string,
    characterId: string
  ): Promise<{ content: string; source: ModelSource }> {
    const response = await ApiService.sendMessage(message, characterId);
    return { content: response, source: 'server' };
  }

  // 本地对话
  private async localChat(
    message: string
  ): Promise<{ content: string; source: ModelSource }> {
    const response = await localAI.sendMessage(message);
    return { content: response, source: 'local' };
  }

  // 获取当前模型源
  getActiveSource(): string {
    return taskRouter.getActiveSource();
  }

  // 检查是否有可用模型
  hasAvailableModel(): boolean {
    return taskRouter.hasAvailableModel();
  }
}

// 导出单例
export const aiEngine = new AIEngine();
