// ============================================
// 数据备份恢复服务
// ============================================
import * as FileSystem from 'expo-file-system';
import { MMKV } from 'react-native-mmkv';
import type { Character, Conversation, AppSettings } from '../types';

const storage = new MMKV({ id: 'data-backup' });

// 备份数据格式
export interface BackupData {
  version: string;
  createdAt: string;
  appVersion: string;
  data: {
    characters: Character[];
    conversations: Conversation[];
    settings: AppSettings | null;
  };
  metadata: {
    characterCount: number;
    conversationCount: number;
    messageCount: number;
  };
}

// 备份历史
interface BackupHistoryEntry {
  id: string;
  filename: string;
  createdAt: string;
  size: number;
  metadata: BackupData['metadata'];
}

class DataBackupService {
  private static instance: DataBackupService;
  private backupDir: string;
  
  private constructor() {
    this.backupDir = `${FileSystem.documentDirectory}backups/`;
    this.ensureBackupDir();
  }
  
  static getInstance(): DataBackupService {
    if (!DataBackupService.instance) {
      DataBackupService.instance = new DataBackupService();
    }
    return DataBackupService.instance;
  }
  
  // 确保备份目录存在
  private async ensureBackupDir(): Promise<void> {
    try {
      const info = await FileSystem.getInfoAsync(this.backupDir);
      if (!info.exists) {
        await FileSystem.makeDirectoryAsync(this.backupDir, { intermediates: true });
      }
    } catch (e) {
      console.error('Ensure backup dir error:', e);
    }
  }
  
  // 创建备份
  async createBackup(
    characters: Character[],
    conversations: Conversation[],
    settings: AppSettings | null
  ): Promise<string | null> {
    try {
      await this.ensureBackupDir();
      
      // 计算统计信息
      const messageCount = conversations.reduce(
        (sum, conv) => sum + conv.messages.length, 
        0
      );
      
      // 创建备份数据
      const backupData: BackupData = {
        version: '1.0.0',
        createdAt: new Date().toISOString(),
        appVersion: '1.6.0',
        data: {
          characters,
          conversations,
          settings,
        },
        metadata: {
          characterCount: characters.length,
          conversationCount: conversations.length,
          messageCount,
        },
      };
      
      // 生成文件名
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `backup_${timestamp}.json`;
      const filePath = `${this.backupDir}${filename}`;
      
      // 写入文件
      const jsonStr = JSON.stringify(backupData, null, 2);
      await FileSystem.writeAsStringAsync(filePath, jsonStr, {
        encoding: FileSystem.EncodingType.UTF8,
      });
      
      // 获取文件大小
      const fileInfo = await FileSystem.getInfoAsync(filePath);
      const size = fileInfo.exists ? fileInfo.size || 0 : 0;
      
      // 保存到历史
      this.addBackupHistory({
        id: `backup_${Date.now()}`,
        filename,
        createdAt: backupData.createdAt,
        size,
        metadata: backupData.metadata,
      });
      
      return filePath;
    } catch (error) {
      console.error('Create backup error:', error);
      return null;
    }
  }
  
  // 恢复备份
  async restoreBackup(filePath: string): Promise<BackupData | null> {
    try {
      // 读取文件
      const jsonStr = await FileSystem.readAsStringAsync(filePath, {
        encoding: FileSystem.EncodingType.UTF8,
      });
      
      // 解析数据
      const backupData: BackupData = JSON.parse(jsonStr);
      
      // 验证数据
      if (!this.validateBackupData(backupData)) {
        throw new Error('Invalid backup data');
      }
      
      return backupData;
    } catch (error) {
      console.error('Restore backup error:', error);
      return null;
    }
  }
  
  // 验证备份数据
  private validateBackupData(data: any): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }
    
    if (!data.version || !data.data) {
      return false;
    }
    
    if (!Array.isArray(data.data.characters) || !Array.isArray(data.data.conversations)) {
      return false;
    }
    
    return true;
  }
  
  // 获取备份历史
  getBackupHistory(): BackupHistoryEntry[] {
    try {
      const saved = storage.getString('backup_history');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.error('Get backup history error:', e);
    }
    return [];
  }
  
  // 添加备份历史
  private addBackupHistory(entry: BackupHistoryEntry): void {
    try {
      const history = this.getBackupHistory();
      history.unshift(entry);
      
      // 只保留最近 20 条
      if (history.length > 20) {
        history.splice(20);
      }
      
      storage.set('backup_history', JSON.stringify(history));
    } catch (e) {
      console.error('Add backup history error:', e);
    }
  }
  
  // 删除备份
  async deleteBackup(filename: string): Promise<boolean> {
    try {
      const filePath = `${this.backupDir}${filename}`;
      await FileSystem.deleteAsync(filePath, { idempotent: true });
      
      // 从历史中移除
      const history = this.getBackupHistory().filter(h => h.filename !== filename);
      storage.set('backup_history', JSON.stringify(history));
      
      return true;
    } catch (error) {
      console.error('Delete backup error:', error);
      return false;
    }
  }
  
  // 清除所有备份
  async clearAllBackups(): Promise<void> {
    try {
      await FileSystem.deleteAsync(this.backupDir, { idempotent: true });
      await this.ensureBackupDir();
      storage.delete('backup_history');
    } catch (error) {
      console.error('Clear backups error:', error);
    }
  }
  
  // 获取备份文件路径
  getBackupPath(filename: string): string {
    return `${this.backupDir}${filename}`;
  }
  
  // 格式化文件大小
  formatSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    } else if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    } else if (bytes < 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    } else {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }
  }
  
  // 格式化日期
  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  }
  
  // 获取备份统计
  getBackupStats(): {
    totalBackups: number;
    totalSize: number;
    lastBackupDate: string | null;
  } {
    const history = this.getBackupHistory();
    const totalSize = history.reduce((sum, h) => sum + h.size, 0);
    const lastBackupDate = history.length > 0 ? history[0].createdAt : null;
    
    return {
      totalBackups: history.length,
      totalSize,
      lastBackupDate,
    };
  }
  
  // 自动备份（定期调用）
  async autoBackup(
    characters: Character[],
    conversations: Conversation[],
    settings: AppSettings | null
  ): Promise<boolean> {
    try {
      const lastBackup = storage.getString('last_auto_backup');
      const now = Date.now();
      
      // 检查是否需要备份（每天一次）
      if (lastBackup) {
        const lastTime = parseInt(lastBackup);
        const daysSinceLastBackup = (now - lastTime) / (1000 * 60 * 60 * 24);
        
        if (daysSinceLastBackup < 1) {
          return false; // 不需要备份
        }
      }
      
      // 执行备份
      const result = await this.createBackup(characters, conversations, settings);
      
      if (result) {
        storage.set('last_auto_backup', now.toString());
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Auto backup error:', error);
      return false;
    }
  }
}

// 单例
export const dataBackupService = DataBackupService.getInstance();

export default dataBackupService;
