// ============================================
// GuguGaga AI VTuber Mobile - 文生图服务
// ============================================
import axios from 'axios';
import * as FileSystem from 'expo-file-system';

interface ImageGenConfig {
  provider: 'wanx' | 'cogview' | 'dalle' | 'flux' | 'kolors';
  apiKey: string;
  baseUrl?: string;
}

interface ImageGenResult {
  url: string;
  width: number;
  height: number;
}

export class ImageGenService {
  private static instance: ImageGenService;

  private constructor() {}

  static getInstance(): ImageGenService {
    if (!ImageGenService.instance) {
      ImageGenService.instance = new ImageGenService();
    }
    return ImageGenService.instance;
  }

  // ============================================
  // 生成图片
  // ============================================
  async generate(prompt: string, config: ImageGenConfig): Promise<ImageGenResult> {
    switch (config.provider) {
      case 'wanx':
        return this.generateWithWanx(prompt, config);
      case 'cogview':
        return this.generateWithCogView(prompt, config);
      case 'dalle':
        return this.generateWithDALLE(prompt, config);
      case 'flux':
        return this.generateWithFlux(prompt, config);
      case 'kolors':
        return this.generateWithKolors(prompt, config);
      default:
        return this.generateWithDALLE(prompt, config);
    }
  }

  // ============================================
  // 通义万相（阿里云）
  // ============================================
  private async generateWithWanx(prompt: string, config: ImageGenConfig): Promise<ImageGenResult> {
    try {
      const response = await axios.post(
        `${config.baseUrl || 'https://dashscope.aliyuncs.com'}/api/v1/services/aigc/text2image/image-synthesis`,
        {
          model: 'wanx-v1',
          input: { prompt },
          parameters: { n: 1, size: '1024*1024' },
        },
        {
          headers: {
            'Authorization': `Bearer ${config.apiKey}`,
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable',
          },
        }
      );

      // 轮询获取结果
      const taskId = response.data.output.task_id;
      return await this.pollWanxResult(taskId, config);
    } catch (error) {
      console.error('Wanx generation error:', error);
      throw error;
    }
  }

  private async pollWanxResult(taskId: string, config: ImageGenConfig): Promise<ImageGenResult> {
    for (let i = 0; i < 30; i++) {
      await new Promise(resolve => setTimeout(resolve, 2000));

      const response = await axios.get(
        `${config.baseUrl || 'https://dashscope.aliyuncs.com'}/api/v1/tasks/${taskId}`,
        { headers: { 'Authorization': `Bearer ${config.apiKey}` } }
      );

      if (response.data.output.task_status === 'SUCCEEDED') {
        return {
          url: response.data.output.results[0].url,
          width: 1024,
          height: 1024,
        };
      }
    }
    throw new Error('Wanx generation timeout');
  }

  // ============================================
  // CogView（智谱 AI）
  // ============================================
  private async generateWithCogView(prompt: string, config: ImageGenConfig): Promise<ImageGenResult> {
    try {
      const response = await axios.post(
        `${config.baseUrl || 'https://open.bigmodel.cn'}/api/paas/v4/images/generations`,
        {
          model: 'cogview-3',
          prompt,
          size: '1024x1024',
        },
        {
          headers: {
            'Authorization': `Bearer ${config.apiKey}`,
            'Content-Type': 'application/json',
          },
        }
      );

      return {
        url: response.data.data[0].url,
        width: 1024,
        height: 1024,
      };
    } catch (error) {
      console.error('CogView generation error:', error);
      throw error;
    }
  }

  // ============================================
  // DALL-E（OpenAI）
  // ============================================
  private async generateWithDALLE(prompt: string, config: ImageGenConfig): Promise<ImageGenResult> {
    try {
      const response = await axios.post(
        `${config.baseUrl || 'https://api.openai.com'}/v1/images/generations`,
        {
          model: 'dall-e-3',
          prompt,
          n: 1,
          size: '1024x1024',
        },
        {
          headers: {
            'Authorization': `Bearer ${config.apiKey}`,
            'Content-Type': 'application/json',
          },
        }
      );

      return {
        url: response.data.data[0].url,
        width: 1024,
        height: 1024,
      };
    } catch (error) {
      console.error('DALL-E generation error:', error);
      throw error;
    }
  }

  // ============================================
  // Flux
  // ============================================
  private async generateWithFlux(prompt: string, config: ImageGenConfig): Promise<ImageGenResult> {
    // Flux API 实现
    throw new Error('Flux provider not implemented yet');
  }

  // ============================================
  // Kolors（快手）
  // ============================================
  private async generateWithKolors(prompt: string, config: ImageGenConfig): Promise<ImageGenResult> {
    // Kolors API 实现
    throw new Error('Kolors provider not implemented yet');
  }

  // ============================================
  // 下载图片到本地
  // ============================================
  async downloadImage(url: string): Promise<string> {
    try {
      const fileName = `img_${Date.now()}.png`;
      const localUri = `${FileSystem.cacheDirectory}${fileName}`;

      const downloadResult = await FileSystem.downloadAsync(url, localUri);
      return downloadResult.uri;
    } catch (error) {
      console.error('Download image error:', error);
      throw error;
    }
  }

  // ============================================
  // 优化提示词
  // ============================================
  optimizePrompt(prompt: string, style?: string): string {
    const stylePrompts: Record<string, string> = {
      anime: 'anime style, high quality, detailed',
      realistic: 'photorealistic, high resolution, detailed',
      watercolor: 'watercolor painting style, artistic',
      oil: 'oil painting style, classical art',
      pixel: 'pixel art style, retro game',
      '3d': '3D render, cinema 4d, octane render',
    };

    const stylePrompt = style ? stylePrompts[style] || '' : '';
    return `${prompt}, ${stylePrompt}, masterpiece, best quality`.trim();
  }
}

export const imageGenService = ImageGenService.getInstance();
