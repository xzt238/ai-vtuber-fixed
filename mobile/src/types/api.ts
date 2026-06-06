/**
 * API 相关类型定义
 */

// 通用 API 响应
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 分页参数
export interface PaginationParams {
  page: number;
  pageSize: number;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// 服务器状态
export interface ServerStatus {
  connected: boolean;
  version: string;
  uptime: number;
  llmProviders: string[];
}

// 设备注册请求
export interface DeviceRegisterRequest {
  device_id: string;
  platform: 'mobile';
  device_type: string;
  screen_width: number;
  screen_height: number;
}

// 设备注册响应
export interface DeviceRegisterResponse {
  success: boolean;
  device_id?: string;
  error?: string;
}
