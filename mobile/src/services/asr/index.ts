// ============================================
// GuguGaga AI VTuber Mobile - ASR 语音识别服务
// ============================================
// expo-av removed for build compatibility - ASR uses Whisper API with pre-recorded audio
import * as FileSystem from 'expo-file-system';
import axios from 'axios';

interface ASRConfig {
  provider: 'whisper' | 'baidu' | 'aliyun' | 'local';
  apiKey?: string;
  language?: string;
}

export class ASRService {
  private static instance: ASRService;
  private recording: any = null;
  private isRecording = false;

  private constructor() {}

  static getInstance(): ASRService {
    if (!ASRService.instance) {
      ASRService.instance = new ASRService();
    }
    return ASRService.instance;
  }

  // ============================================
  // 录音控制
  // ============================================
  async startRecording(): Promise<void> {
    // 占位实现 - 需要 expo-av 模块支持
    this.isRecording = true;
    console.log('Recording started (placeholder)');
  }

  async stopRecording(): Promise<string | null> {
    this.isRecording = false;
    return null;
  }

  async cancelRecording(): Promise<void> {
    this.isRecording = false;
  }

  getIsRecording(): boolean {
    return this.isRecording;
  }

  // ============================================
  // 语音识别
  // ============================================
  async recognize(audioUri: string, config: ASRConfig): Promise<string> {
    switch (config.provider) {
      case 'whisper':
        return this.recognizeWithWhisper(audioUri, config);
      case 'baidu':
        return this.recognizeWithBaidu(audioUri, config);
      case 'local':
        return this.recognizeLocally(audioUri);
      default:
        return this.recognizeWithWhisper(audioUri, config);
    }
  }

  // ============================================
  // Whisper API 识别
  // ============================================
  private async recognizeWithWhisper(audioUri: string, config: ASRConfig): Promise<string> {
    if (!config.apiKey) {
      throw new Error('Whisper API Key 未配置');
    }

    try {
      // 读取音频文件
      const fileInfo = await FileSystem.getInfoAsync(audioUri);
      if (!fileInfo.exists) {
        throw new Error('音频文件不存在');
      }

      // 创建 FormData
      const formData = new FormData();
      formData.append('file', {
        uri: audioUri,
        type: 'audio/m4a',
        name: 'audio.m4a',
      } as any);
      formData.append('model', 'whisper-1');
      formData.append('language', config.language || 'zh');
      formData.append('response_format', 'json');

      const response = await axios.post(
        'https://api.openai.com/v1/audio/transcriptions',
        formData,
        {
          headers: {
            'Authorization': `Bearer ${config.apiKey}`,
            'Content-Type': 'multipart/form-data',
          },
          timeout: 30000,
        }
      );

      return response.data.text || '';
    } catch (error) {
      console.error('Whisper recognition error:', error);
      throw error;
    }
  }

  // ============================================
  // 百度语音识别
  // ============================================
  private async recognizeWithBaidu(audioUri: string, config: ASRConfig): Promise<string> {
    // 占位实现
    return '[百度语音识别需要配置 API Key]';
  }

  // ============================================
  // 本地语音识别（简化版）
  // ============================================
  private async recognizeLocally(audioUri: string): Promise<string> {
    // 本地语音识别需要较大的模型，这里返回提示
    return '[本地语音识别功能需要下载语音模型]';
  }

  // ============================================
  // 实时识别（录音+识别）
  // ============================================
  async recordAndRecognize(
    config: ASRConfig,
    onResult: (text: string) => void,
    onError: (error: Error) => void,
    maxDuration: number = 10000
  ): Promise<void> {
    try {
      await this.startRecording();

      // 设置最大录音时长
      setTimeout(async () => {
        if (this.isRecording) {
          const uri = await this.stopRecording();
          if (uri) {
            try {
              const text = await this.recognize(uri, config);
              onResult(text);
            } catch (error) {
              onError(error as Error);
            }
          }
        }
      }, maxDuration);
    } catch (error) {
      onError(error as Error);
    }
  }
}

export const asrService = ASRService.getInstance();
