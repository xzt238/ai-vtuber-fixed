/**
 * 云端模型对接
 *
 * 支持 OpenAI、Anthropic 等多种 LLM 供应商
 */

import { AIProvider, CloudLLMConfig } from '../../types/ai';
import { useSettingsStore } from '../../store/settingsStore';

interface ChatCompletionMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatCompletionRequest {
  messages: ChatCompletionMessage[];
  model?: string;
  maxTokens?: number;
  temperature?: number;
  stream?: boolean;
}

interface ChatCompletionResponse {
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

class CloudModelService {
  // 获取当前 LLM 配置
  private getConfig(): CloudLLMConfig {
    const settings = useSettingsStore.getState();
    return {
      provider: settings.llmProvider as AIProvider,
      apiKey: settings.llmApiKey,
      baseUrl: settings.llmBaseUrl || this.getDefaultBaseUrl(settings.llmProvider),
      model: settings.llmModel,
      maxTokens: 2048,
      temperature: 0.7,
    };
  }

  // 获取默认 Base URL
  private getDefaultBaseUrl(provider: string): string {
    switch (provider) {
      case 'openai':
        return 'https://api.openai.com/v1';
      case 'anthropic':
        return 'https://api.anthropic.com/v1';
      default:
        return '';
    }
  }

  // 是否已配置
  isConfigured(): boolean {
    const config = this.getConfig();
    return !!(config.apiKey && config.baseUrl);
  }

  // 发送聊天请求
  async chat(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    const config = this.getConfig();

    if (!config.apiKey) {
      throw new Error('未配置 API Key，请在设置中配置');
    }

    const provider = config.provider;

    switch (provider) {
      case 'openai':
        return this.openaiChat(config, request);
      case 'anthropic':
        return this.anthropicChat(config, request);
      case 'custom':
        return this.customChat(config, request);
      default:
        throw new Error(`不支持的 AI 供应商: ${provider}`);
    }
  }

  // OpenAI API
  private async openaiChat(
    config: CloudLLMConfig,
    request: ChatCompletionRequest
  ): Promise<ChatCompletionResponse> {
    const url = `${config.baseUrl}/chat/completions`;

    const body = {
      model: request.model || config.model,
      messages: request.messages,
      max_tokens: request.maxTokens || config.maxTokens,
      temperature: request.temperature ?? config.temperature,
      stream: false,
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`OpenAI API 错误: ${response.status} - ${error}`);
    }

    const data = await response.json();
    return {
      content: data.choices?.[0]?.message?.content || '',
      usage: data.usage
        ? {
            promptTokens: data.usage.prompt_tokens,
            completionTokens: data.usage.completion_tokens,
            totalTokens: data.usage.total_tokens,
          }
        : undefined,
    };
  }

  // Anthropic API
  private async anthropicChat(
    config: CloudLLMConfig,
    request: ChatCompletionRequest
  ): Promise<ChatCompletionResponse> {
    const url = `${config.baseUrl}/messages`;

    // 提取 system 消息
    const systemMessage = request.messages.find((m) => m.role === 'system');
    const messages = request.messages
      .filter((m) => m.role !== 'system')
      .map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      }));

    const body: any = {
      model: request.model || config.model,
      messages,
      max_tokens: request.maxTokens || config.maxTokens,
    };

    if (systemMessage) {
      body.system = systemMessage.content;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': config.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Anthropic API 错误: ${response.status} - ${error}`);
    }

    const data = await response.json();
    return {
      content: data.content?.[0]?.text || '',
      usage: data.usage
        ? {
            promptTokens: data.usage.input_tokens,
            completionTokens: data.usage.output_tokens,
            totalTokens: data.usage.input_tokens + data.usage.output_tokens,
          }
        : undefined,
    };
  }

  // 自定义 API（兼容 OpenAI 格式）
  private async customChat(
    config: CloudLLMConfig,
    request: ChatCompletionRequest
  ): Promise<ChatCompletionResponse> {
    // 自定义 API 默认使用 OpenAI 兼容格式
    return this.openaiChat(config, request);
  }
}

// 导出单例
export const cloudModel = new CloudModelService();
