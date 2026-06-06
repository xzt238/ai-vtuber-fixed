/**
 * API 服务层类型定义
 */

import { AxiosRequestConfig, AxiosResponse } from 'axios';

// 请求配置扩展
export interface ApiRequestConfig extends AxiosRequestConfig {
  skipAuth?: boolean;
  retryCount?: number;
}

// API 错误
export interface ApiError {
  code: string;
  message: string;
  status: number;
  details?: any;
}

// 请求拦截器
export type RequestInterceptor = (config: ApiRequestConfig) => ApiRequestConfig | Promise<ApiRequestConfig>;

// 响应拦截器
export type ResponseInterceptor = (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>;
