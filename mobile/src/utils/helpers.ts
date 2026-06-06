// ============================================
// GuguGaga AI VTuber Mobile - 工具函数
// ============================================
import * as FileSystem from 'expo-file-system';
import * as Haptics from 'expo-haptics';
import { Alert, Platform } from 'react-native';

// 生成唯一 ID
export const generateId = (): string => {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// 格式化日期
export const formatDate = (date: Date | string, format: 'short' | 'medium' | 'long' | 'time' | 'dateTime' = 'medium'): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');
  
  switch (format) {
    case 'short':
      return `${month}/${day}`;
    case 'medium':
      return `${year}-${month}-${day}`;
    case 'long':
      return `${year}年${month}月${day}日`;
    case 'time':
      return `${hours}:${minutes}`;
    case 'dateTime':
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    default:
      return `${year}-${month}-${day}`;
  }
};

// 相对时间
export const getRelativeTime = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (seconds < 60) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  if (days < 365) return `${Math.floor(days / 30)}个月前`;
  return `${Math.floor(days / 365)}年前`;
};

// 截断文本
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
};

// 防抖函数
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// 节流函数
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

// 深拷贝
export const deepClone = <T>(obj: T): T => {
  return JSON.parse(JSON.stringify(obj));
};

// 延迟函数
export const sleep = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

// 触觉反馈
export const hapticFeedback = async (type: 'light' | 'medium' | 'heavy' = 'light'): Promise<void> => {
  try {
    switch (type) {
      case 'light':
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        break;
      case 'medium':
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        break;
      case 'heavy':
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
        break;
    }
  } catch (error) {
    // 忽略触觉反馈错误
  }
};

// 显示提示框
export const showAlert = (
  title: string,
  message?: string,
  buttons?: Array<{ text: string; onPress?: () => void; style?: 'default' | 'cancel' | 'destructive' }>
): void => {
  Alert.alert(title, message, buttons);
};

// 显示确认框
export const showConfirm = (
  title: string,
  message: string,
  onConfirm: () => void,
  onCancel?: () => void
): void => {
  Alert.alert(title, message, [
    { text: '取消', style: 'cancel', onPress: onCancel },
    { text: '确定', onPress: onConfirm },
  ]);
};

// 显示删除确认框
export const showDeleteConfirm = (
  title: string,
  message: string,
  onDelete: () => void
): void => {
  Alert.alert(title, message, [
    { text: '取消', style: 'cancel' },
    { text: '删除', style: 'destructive', onPress: onDelete },
  ]);
};

// 检查文件是否存在
export const fileExists = async (uri: string): Promise<boolean> => {
  try {
    const info = await FileSystem.getInfoAsync(uri);
    return info.exists;
  } catch {
    return false;
  }
};

// 读取文件
export const readFile = async (uri: string): Promise<string | null> => {
  try {
    return await FileSystem.readAsStringAsync(uri);
  } catch {
    return null;
  }
};

// 写入文件
export const writeFile = async (uri: string, content: string): Promise<boolean> => {
  try {
    await FileSystem.writeAsStringAsync(uri, content);
    return true;
  } catch {
    return false;
  }
};

// 删除文件
export const deleteFile = async (uri: string): Promise<boolean> => {
  try {
    await FileSystem.deleteAsync(uri);
    return true;
  } catch {
    return false;
  }
};

// 获取文件大小
export const getFileSize = async (uri: string): Promise<number> => {
  try {
    const info = await FileSystem.getInfoAsync(uri);
    return info.exists ? info.size || 0 : 0;
  } catch {
    return 0;
  }
};

// 格式化文件大小
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化数字
export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

// 验证邮箱
export const isValidEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

// 验证手机号
export const isValidPhone = (phone: string): boolean => {
  return /^1[3-9]\d{9}$/.test(phone);
};

// 验证 API Key
export const isValidApiKey = (apiKey: string): boolean => {
  return apiKey.length >= 20;
};

// 获取平台
export const getPlatform = (): 'ios' | 'android' | 'web' => {
  return Platform.OS as 'ios' | 'android' | 'web';
};

// 是否是 iOS
export const isIOS = (): boolean => {
  return Platform.OS === 'ios';
};

// 是否是 Android
export const isAndroid = (): boolean => {
  return Platform.OS === 'android';
};

// 获取设备信息
export const getDeviceInfo = () => {
  return {
    platform: Platform.OS,
    version: Platform.Version,
    isTV: Platform.isTV,
  };
};

// 安全的 JSON 解析
export const safeJsonParse = <T>(json: string, fallback: T): T => {
  try {
    return JSON.parse(json);
  } catch {
    return fallback;
  }
};

// 安全的 JSON 字符串化
export const safeJsonStringify = (obj: any): string => {
  try {
    return JSON.stringify(obj);
  } catch {
    return '';
  }
};

// 数组分块
export const chunkArray = <T>(array: T[], size: number): T[][] => {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
};

// 数组去重
export const uniqueArray = <T>(array: T[], key?: keyof T): T[] => {
  if (key) {
    const seen = new Set();
    return array.filter(item => {
      const val = item[key];
      if (seen.has(val)) {
        return false;
      }
      seen.add(val);
      return true;
    });
  }
  return [...new Set(array)];
};

// 对象转查询字符串
export const objectToQueryString = (obj: Record<string, any>): string => {
  return Object.entries(obj)
    .filter(([_, value]) => value !== undefined && value !== null)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&');
};

// 查询字符串转对象
export const queryStringToObject = (queryString: string): Record<string, string> => {
  const params: Record<string, string> = {};
  const searchParams = new URLSearchParams(queryString);
  searchParams.forEach((value, key) => {
    params[key] = value;
  });
  return params;
};
