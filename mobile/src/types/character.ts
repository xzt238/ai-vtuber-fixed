/**
 * 角色相关类型定义
 */

// 角色个性标签
export interface CharacterTrait {
  name: string;
  description: string;
}

// 角色定义
export interface Character {
  id: string;
  name: string;
  avatar: string;
  description: string;
  personality: string;
  traits: CharacterTrait[];
  systemPrompt: string;
  greeting: string;
  voiceId?: string;
  modelId?: string;
  isDefault?: boolean;
}

// 角色列表响应
export interface CharacterListResponse {
  success: boolean;
  characters: Character[];
  error?: string;
}
