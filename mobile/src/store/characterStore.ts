/**
 * 角色状态管理
 */

import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Character } from '../types/character';
import { STORAGE_KEYS } from '../utils/constants';

// 内置默认角色
const DEFAULT_CHARACTERS: Character[] = [
  {
    id: 'default_assistant',
    name: '小助手',
    avatar: '',
    description: '友好、乐于助人的AI助手',
    personality: '友好',
    traits: [
      { name: '友好', description: '总是以积极的态度回应' },
      { name: '专业', description: '提供准确、有用的信息' },
    ],
    systemPrompt: '你是一个友好、专业的AI助手，名叫小助手。你会用亲切的语气和用户交流，帮助他们解决各种问题。',
    greeting: '你好！我是小助手，很高兴认识你！有什么我可以帮助你的吗？',
    isDefault: true,
  },
  {
    id: 'default_companion',
    name: '小陪伴',
    avatar: '',
    description: '可爱、温暖的AI陪伴者',
    personality: '可爱',
    traits: [
      { name: '可爱', description: '说话方式温暖可爱' },
      { name: '体贴', description: '善于倾听和安慰' },
    ],
    systemPrompt: '你是一个可爱、温暖的AI陪伴者，名叫小陪伴。你会用温柔可爱的语气和用户交流，善于倾听和陪伴。',
    greeting: '嗨~ 我是小陪伴，今天陪你聊天哦！有什么想说的吗？',
    isDefault: true,
  },
  {
    id: 'default_teacher',
    name: '小老师',
    avatar: '',
    description: '耐心、专业的AI老师',
    personality: '专业',
    traits: [
      { name: '耐心', description: '善于解释复杂概念' },
      { name: '专业', description: '知识渊博，讲解清晰' },
    ],
    systemPrompt: '你是一个耐心、专业的AI老师，名叫小老师。你善于用简单易懂的方式解释复杂概念，帮助用户学习和成长。',
    greeting: '你好！我是小老师，准备好学习新知识了吗？',
    isDefault: true,
  },
];

interface CharacterState {
  // 角色列表
  characters: Character[];
  // 当前选中角色
  activeCharacter: Character | null;
  // 加载状态
  isLoading: boolean;

  // 操作
  loadCharacters: () => Promise<void>;
  setActiveCharacter: (characterId: string) => void;
  getCharacterById: (id: string) => Character | undefined;
  addCharacter: (character: Character) => void;
}

export const useCharacterStore = create<CharacterState>((set, get) => ({
  characters: DEFAULT_CHARACTERS,
  activeCharacter: DEFAULT_CHARACTERS[0],
  isLoading: false,

  // 加载角色列表
  loadCharacters: async () => {
    try {
      set({ isLoading: true });

      // 从存储中获取上次选中的角色
      const activeCharacterId = await AsyncStorage.getItem(STORAGE_KEYS.ACTIVE_CHARACTER_ID);
      const characters = get().characters;

      let activeCharacter = characters[0];
      if (activeCharacterId) {
        const found = characters.find((c) => c.id === activeCharacterId);
        if (found) activeCharacter = found;
      }

      set({
        characters,
        activeCharacter,
        isLoading: false,
      });
    } catch (error) {
      console.error('[CharacterStore] 加载角色失败:', error);
      set({ isLoading: false });
    }
  },

  // 设置当前角色
  setActiveCharacter: (characterId) => {
    const character = get().characters.find((c) => c.id === characterId);
    if (character) {
      set({ activeCharacter: character });
      AsyncStorage.setItem(STORAGE_KEYS.ACTIVE_CHARACTER_ID, characterId);
    }
  },

  // 根据 ID 获取角色
  getCharacterById: (id) => {
    return get().characters.find((c) => c.id === id);
  },

  // 添加角色
  addCharacter: (character) => {
    set((state) => ({
      characters: [...state.characters, character],
    }));
  },
}));
