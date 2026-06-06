// ============================================
// 角色分享服务
// ============================================
import * as FileSystem from 'expo-file-system';
import { MMKV } from 'react-native-mmkv';
import type { Character } from '../types';

const storage = new MMKV({ id: 'character-share' });

// 分享的角色数据格式
export interface SharedCharacter {
  version: string;
  exportDate: string;
  character: Omit<Character, 'id' | 'createdAt' | 'updatedAt'>;
  metadata: {
    appVersion: string;
    platform: string;
  };
}

// 分享链接格式
export interface ShareLink {
  id: string;
  characterName: string;
  createdAt: string;
  expiresAt?: string;
}

class CharacterShareService {
  private static instance: CharacterShareService;
  
  private constructor() {}
  
  static getInstance(): CharacterShareService {
    if (!CharacterShareService.instance) {
      CharacterShareService.instance = new CharacterShareService();
    }
    return CharacterShareService.instance;
  }
  
  // 导出角色为 JSON
  exportCharacter(character: Character): SharedCharacter {
    return {
      version: '1.0.0',
      exportDate: new Date().toISOString(),
      character: {
        name: character.name,
        avatar: character.avatar,
        description: character.description,
        personality: character.personality,
        systemPrompt: character.systemPrompt,
        greeting: character.greeting,
        tags: character.tags,
        voiceId: character.voiceId,
      },
      metadata: {
        appVersion: '1.5.0',
        platform: 'mobile',
      },
    };
  }
  
  // 导入角色从 JSON
  importCharacter(data: SharedCharacter): Omit<Character, 'id' | 'createdAt' | 'updatedAt'> | null {
    try {
      // 验证版本
      if (!data.version || !data.character) {
        throw new Error('Invalid share data');
      }
      
      // 验证必填字段
      if (!data.character.name || !data.character.systemPrompt) {
        throw new Error('Missing required fields');
      }
      
      return {
        name: data.character.name,
        avatar: data.character.avatar || '',
        description: data.character.description || '',
        personality: data.character.personality || '',
        systemPrompt: data.character.systemPrompt,
        greeting: data.character.greeting || `你好！我是${data.character.name}。`,
        tags: data.character.tags || [],
        voiceId: data.character.voiceId || '',
      };
    } catch (error) {
      console.error('Import character error:', error);
      return null;
    }
  }
  
  // 分享角色文件
  async shareCharacterAsFile(character: Character): Promise<string | null> {
    try {
      const sharedData = this.exportCharacter(character);
      const jsonStr = JSON.stringify(sharedData, null, 2);
      
      // 写入临时文件
      const filePath = `${FileSystem.cacheDirectory}share_${character.name}_${Date.now()}.json`;
      await FileSystem.writeAsStringAsync(filePath, jsonStr, {
        encoding: FileSystem.EncodingType.UTF8,
      });
      
      return filePath;
    } catch (error) {
      console.error('Share character error:', error);
      return null;
    }
  }
  
  // 生成分享文本（用于复制粘贴）
  generateShareText(character: Character): string {
    const sharedData = this.exportCharacter(character);
    return JSON.stringify(sharedData);
  }
  
  // 从分享文本导入
  importFromText(text: string): Omit<Character, 'id' | 'createdAt' | 'updatedAt'> | null {
    try {
      const data = JSON.parse(text);
      return this.importCharacter(data);
    } catch (error) {
      console.error('Import from text error:', error);
      return null;
    }
  }
  
  // 保存分享历史
  saveShareHistory(character: Character): void {
    try {
      const history = this.getShareHistory();
      const entry: ShareLink = {
        id: `share_${Date.now()}`,
        characterName: character.name,
        createdAt: new Date().toISOString(),
      };
      
      history.unshift(entry);
      
      // 只保留最近 50 条
      if (history.length > 50) {
        history.splice(50);
      }
      
      storage.set('share_history', JSON.stringify(history));
    } catch (error) {
      console.error('Save share history error:', error);
    }
  }
  
  // 获取分享历史
  getShareHistory(): ShareLink[] {
    try {
      const saved = storage.getString('share_history');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (error) {
      console.error('Get share history error:', error);
    }
    return [];
  }
  
  // 清除分享历史
  clearShareHistory(): void {
    storage.delete('share_history');
  }
  
  // 验证分享数据
  validateShareData(data: any): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }
    
    if (!data.version || !data.character) {
      return false;
    }
    
    if (!data.character.name || !data.character.systemPrompt) {
      return false;
    }
    
    return true;
  }
  
  // 生成二维码数据（用于分享）
  generateQRData(character: Character): string {
    const sharedData = this.exportCharacter(character);
    // 压缩数据（移除空格）
    return JSON.stringify(sharedData);
  }
  
  // 从二维码数据解析
  parseQRData(data: string): Omit<Character, 'id' | 'createdAt' | 'updatedAt'> | null {
    try {
      const parsed = JSON.parse(data);
      return this.importCharacter(parsed);
    } catch (error) {
      console.error('Parse QR data error:', error);
      return null;
    }
  }
}

// 单例
export const characterShareService = CharacterShareService.getInstance();

export default characterShareService;
