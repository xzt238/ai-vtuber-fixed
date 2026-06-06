// ============================================
// GuguGaga AI VTuber Mobile - API 服务
// 支持云端和本地两种模式
// ============================================
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { MMKV } from 'react-native-mmkv';
import type { AIConfig, LLMProvider, Character, Message } from '../types';

const storage = new MMKV();

// ============================================
// API 客户端基类
// ============================================
class BaseAPIClient {
  protected client: AxiosInstance;
  protected config: AIConfig;

  constructor(config: AIConfig) {
    this.config = config;
    this.client = axios.create({
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  protected getHeaders(): Record<string, string> {
    return {
      'Authorization': `Bearer ${this.config.apiKey}`,
      'Content-Type': 'application/json',
    };
  }
}

// ============================================
// OpenAI API 客户端
// ============================================
export class OpenAIClient extends BaseAPIClient {
  async chat(
    messages: Array<{ role: string; content: string }>,
    character: Character
  ): Promise<string> {
    try {
      const response = await this.client.post(
        `${this.config.baseUrl || 'https://api.openai.com/v1'}/chat/completions`,
        {
          model: this.config.model,
          messages: [
            { role: 'system', content: character.systemPrompt },
            ...messages,
          ],
          temperature: this.config.temperature,
          max_tokens: this.config.maxTokens,
          top_p: this.config.topP,
          frequency_penalty: this.config.frequencyPenalty,
          presence_penalty: this.config.presencePenalty,
        },
        { headers: this.getHeaders() }
      );

      return response.data.choices[0].message.content;
    } catch (error) {
      console.error('OpenAI API Error:', error);
      throw error;
    }
  }

  async streamChat(
    messages: Array<{ role: string; content: string }>,
    character: Character,
    onChunk: (chunk: string) => void,
    onDone: () => void,
    onError: (error: Error) => void
  ): Promise<void> {
    try {
      const response = await this.client.post(
        `${this.config.baseUrl || 'https://api.openai.com/v1'}/chat/completions`,
        {
          model: this.config.model,
          messages: [
            { role: 'system', content: character.systemPrompt },
            ...messages,
          ],
          temperature: this.config.temperature,
          max_tokens: this.config.maxTokens,
          stream: true,
        },
        {
          headers: this.getHeaders(),
          responseType: 'stream',
        }
      );

      // 处理流式响应
      response.data.on('data', (chunk: Buffer) => {
        const lines = chunk.toString().split('\n').filter(line => line.trim() !== '');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              onDone();
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              const content = parsed.choices[0]?.delta?.content;
              if (content) {
                onChunk(content);
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      });

      response.data.on('end', onDone);
      response.data.on('error', onError);
    } catch (error) {
      onError(error as Error);
    }
  }
}

// ============================================
// Claude API 客户端
// ============================================
export class ClaudeClient extends BaseAPIClient {
  async chat(
    messages: Array<{ role: string; content: string }>,
    character: Character
  ): Promise<string> {
    try {
      const response = await this.client.post(
        `${this.config.baseUrl || 'https://api.anthropic.com/v1'}/messages`,
        {
          model: this.config.model,
          max_tokens: this.config.maxTokens,
          system: character.systemPrompt,
          messages: messages.map(msg => ({
            role: msg.role === 'system' ? 'assistant' : msg.role,
            content: msg.content,
          })),
        },
        {
          headers: {
            'x-api-key': this.config.apiKey,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json',
          },
        }
      );

      return response.data.content[0].text;
    } catch (error) {
      console.error('Claude API Error:', error);
      throw error;
    }
  }
}

// ============================================
// 通用 LLM API 客户端（支持国产模型）
// ============================================
export class GenericLLMClient extends BaseAPIClient {
  private provider: LLMProvider;

  constructor(config: AIConfig) {
    super(config);
    this.provider = config.provider;
  }

  async chat(
    messages: Array<{ role: string; content: string }>,
    character: Character
  ): Promise<string> {
    const baseUrl = this.getBaseUrl();
    const headers = this.getProviderHeaders();
    
    try {
      const response = await this.client.post(
        `${baseUrl}/chat/completions`,
        {
          model: this.config.model,
          messages: [
            { role: 'system', content: character.systemPrompt },
            ...messages,
          ],
          temperature: this.config.temperature,
          max_tokens: this.config.maxTokens,
        },
        { headers }
      );

      return response.data.choices[0].message.content;
    } catch (error) {
      console.error(`${this.provider} API Error:`, error);
      throw error;
    }
  }

  private getBaseUrl(): string {
    if (this.config.baseUrl) return this.config.baseUrl;

    const baseUrls: Record<LLMProvider, string> = {
      openai: 'https://api.openai.com/v1',
      claude: 'https://api.anthropic.com/v1',
      gemini: 'https://generativelanguage.googleapis.com/v1beta',
      qwen: 'https://dashscope.aliyuncs.com/api/v1',
      deepseek: 'https://api.deepseek.com/v1',
      zhipu: 'https://open.bigmodel.cn/api/paas/v4',
      baichuan: 'https://api.baichuan-ai.com/v1',
      minimax: 'https://api.minimax.chat/v1',
      moonshot: 'https://api.moonshot.cn/v1',
      spark: 'https://spark-api-open.xf-yun.com/v1',
      hunyuan: 'https://hunyuan.tencentcloudapi.com/v1',
      local: 'http://localhost:11434/v1',
    };

    return baseUrls[this.provider] || baseUrls.openai;
  }

  private getProviderHeaders(): Record<string, string> {
    const baseHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    switch (this.provider) {
      case 'qwen':
        return { ...baseHeaders, 'Authorization': `Bearer ${this.config.apiKey}` };
      case 'deepseek':
        return { ...baseHeaders, 'Authorization': `Bearer ${this.config.apiKey}` };
      case 'zhipu':
        return { ...baseHeaders, 'Authorization': `Bearer ${this.config.apiKey}` };
      case 'spark':
        return { ...baseHeaders, 'Authorization': `Bearer ${this.config.apiKey}` };
      default:
        return { ...baseHeaders, 'Authorization': `Bearer ${this.config.apiKey}` };
    }
  }
}

// ============================================
// API 工厂
// ============================================
export class APIFactory {
  static createClient(config: AIConfig): BaseAPIClient {
    switch (config.provider) {
      case 'openai':
        return new OpenAIClient(config);
      case 'claude':
        return new ClaudeClient(config);
      default:
        return new GenericLLMClient(config);
    }
  }
}

// ============================================
// 统一 API 服务
// ============================================
export class APIService {
  private static instance: APIService;
  private client: BaseAPIClient | null = null;
  private config: AIConfig | null = null;

  private constructor() {}

  static getInstance(): APIService {
    if (!APIService.instance) {
      APIService.instance = new APIService();
    }
    return APIService.instance;
  }

  initialize(config: AIConfig): void {
    this.config = config;
    this.client = APIFactory.createClient(config);
  }

  async chat(
    messages: Array<{ role: string; content: string }>,
    character: Character
  ): Promise<string> {
    if (!this.client) {
      throw new Error('API not initialized');
    }
    return (this.client as any).chat(messages, character);
  }

  async streamChat(
    messages: Array<{ role: string; content: string }>,
    character: Character,
    onChunk: (chunk: string) => void,
    onDone: () => void,
    onError: (error: Error) => void
  ): Promise<void> {
    if (!this.client || !(this.client instanceof OpenAIClient)) {
      throw new Error('Streaming not supported for this provider');
    }
    return this.client.streamChat(messages, character, onChunk, onDone, onError);
  }

  isInitialized(): boolean {
    return this.client !== null;
  }

  getConfig(): AIConfig | null {
    return this.config;
  }
}

// 导出单例
export const apiService = APIService.getInstance();
