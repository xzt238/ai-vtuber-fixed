/**
 * 统一 API 客户端
 *
 * 基于 axios 封装，包含请求/响应拦截器、错误处理、重试机制
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_CONFIG, STORAGE_KEYS } from '../../utils/constants';
import { ApiResponse } from '../../types/api';
import { ApiRequestConfig, ApiError } from './types';

class ApiClient {
  private instance: AxiosInstance;
  private deviceId: string | null = null;
  private serverUrl: string = API_CONFIG.BASE_URL;

  constructor() {
    this.instance = axios.create({
      baseURL: this.serverUrl + API_CONFIG.API_PREFIX,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  // 设置拦截器
  private setupInterceptors(): void {
    // 请求拦截器
    this.instance.interceptors.request.use(
      async (config) => {
        // 添加设备 ID
        if (!this.deviceId) {
          this.deviceId = await AsyncStorage.getItem(STORAGE_KEYS.DEVICE_ID);
        }
        if (this.deviceId) {
          config.headers['X-Device-ID'] = this.deviceId;
        }

        // 添加时间戳（防缓存）
        if (config.method === 'get') {
          config.params = {
            ...config.params,
            _t: Date.now(),
          };
        }

        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response) => {
        return response;
      },
      async (error: AxiosError) => {
        const apiError: ApiError = {
          code: error.code || 'UNKNOWN',
          message: error.message || '请求失败',
          status: error.response?.status || 0,
          details: error.response?.data,
        };

        console.error('[API] 请求失败:', apiError);

        // 401 未授权 - 清理凭证
        if (error.response?.status === 401) {
          await AsyncStorage.multiRemove([
            STORAGE_KEYS.DEVICE_ID,
            STORAGE_KEYS.USER_ID,
          ]);
          this.deviceId = null;
        }

        return Promise.reject(apiError);
      }
    );
  }

  // 设置服务器地址
  async setServerUrl(url: string): Promise<void> {
    this.serverUrl = url;
    this.instance.defaults.baseURL = url + API_CONFIG.API_PREFIX;
    await AsyncStorage.setItem(STORAGE_KEYS.SERVER_URL, url);
  }

  // 获取服务器地址
  getServerUrl(): string {
    return this.serverUrl;
  }

  // 设置设备 ID
  setDeviceId(deviceId: string): void {
    this.deviceId = deviceId;
  }

  // GET 请求
  async get<T = any>(url: string, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.instance.get<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // POST 请求
  async post<T = any>(url: string, data?: any, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.instance.post<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // PUT 请求
  async put<T = any>(url: string, data?: any, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.instance.put<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // DELETE 请求
  async delete<T = any>(url: string, config?: ApiRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.instance.delete<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // 检查连接
  async checkConnection(): Promise<boolean> {
    try {
      const response = await this.instance.get('/status', {
        timeout: 5000,
      });
      return response.status === 200;
    } catch {
      return false;
    }
  }

  // 上传文件
  async upload<T = any>(url: string, formData: FormData): Promise<ApiResponse<T>> {
    try {
      const response = await this.instance.post<ApiResponse<T>>(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }
}

// 导出单例
export const apiClient = new ApiClient();
