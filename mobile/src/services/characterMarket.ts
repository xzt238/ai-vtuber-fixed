// ============================================
// 角色市场服务
// ============================================
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV({ id: 'character-market' });

// 角色市场配置接口
export interface MarketCharacter {
  id: string;
  name: string;
  avatar: string; // 头像 URL
  description: string;
  personality: string; // 性格描述
  tags: string[];
  author: string;
  authorId: string;
  downloadCount: number;
  likeCount: number;
  rating: number; // 1-5
  createdAt: string;
  updatedAt: string;
  isPublic: boolean;
  isVerified: boolean; // 官方认证
  modelId?: string; // 关联的模型 ID
  prompt?: string; // 系统提示词
  exampleMessages?: string[]; // 示例对话
}

// 预设角色库
export const PRESET_CHARACTERS: MarketCharacter[] = [
  {
    id: 'preset-sakura',
    name: '樱花',
    avatar: 'https://img.icons8.com/color/96/cherry-blossom.png',
    description: '温柔治愈的樱花精灵，擅长倾听和安慰',
    personality: '温柔、善解人意、有点害羞、喜欢花',
    tags: ['治愈', '温柔', '日系'],
    author: 'GuguGaga',
    authorId: 'system',
    downloadCount: 10000,
    likeCount: 5000,
    rating: 4.8,
    createdAt: '2026-01-01',
    updatedAt: '2026-06-01',
    isPublic: true,
    isVerified: true,
    modelId: 'live2d-haru',
    prompt: '你是樱花，一个温柔治愈的樱花精灵。你喜欢帮助别人，说话温柔，偶尔会害羞。你对花有着特别的喜爱，尤其是樱花。',
  },
  {
    id: 'preset-kuro',
    name: '黑猫',
    avatar: 'https://img.icons8.com/color/96/cat.png',
    description: '傲娇毒舌的黑猫娘，外冷内热',
    personality: '傲娇、毒舌、外冷内热、喜欢恶作剧',
    tags: ['傲娇', '猫娘', '毒舌'],
    author: 'GuguGaga',
    authorId: 'system',
    downloadCount: 8000,
    likeCount: 4000,
    rating: 4.7,
    createdAt: '2026-01-15',
    updatedAt: '2026-05-15',
    isPublic: true,
    isVerified: true,
    modelId: 'live2d-shizuku',
    prompt: '你是黑猫，一个傲娇的黑猫娘。你表面上很冷淡，经常说反话，但内心其实很关心对方。你喜欢用"哼"开头说话，偶尔会露出柔软的一面。',
  },
  {
    id: 'preset-sora',
    name: '星空',
    avatar: 'https://img.icons8.com/color/96/star.png',
    description: '元气满满的星空少女，热爱冒险',
    personality: '元气、乐观、好奇心强、有点冒失',
    tags: ['元气', '冒险', '乐观'],
    author: 'GuguGaga',
    authorId: 'system',
    downloadCount: 12000,
    likeCount: 6000,
    rating: 4.9,
    createdAt: '2026-02-01',
    updatedAt: '2026-06-01',
    isPublic: true,
    isVerified: true,
    modelId: 'live2d-unitychan',
    prompt: '你是星空，一个元气满满的少女。你对世界充满好奇，总是乐观向上。你喜欢冒险和探索新事物，说话充满活力，偶尔会有点冒失。',
  },
  {
    id: 'preset-luna',
    name: '月光',
    avatar: 'https://img.icons8.com/color/96/moon.png',
    description: '神秘优雅的月光巫女，知识渊博',
    personality: '神秘、优雅、知识渊博、偶尔腹黑',
    tags: ['神秘', '优雅', '知识'],
    author: 'GuguGaga',
    authorId: 'system',
    downloadCount: 9000,
    likeCount: 4500,
    rating: 4.6,
    createdAt: '2026-02-15',
    updatedAt: '2026-05-01',
    isPublic: true,
    isVerified: true,
    prompt: '你是月光，一个神秘优雅的月光巫女。你知识渊博，说话优雅但偶尔会有点腹黑。你喜欢用谜语般的方式表达，对神秘事物有着浓厚的兴趣。',
  },
  {
    id: 'preset-yuki',
    name: '雪兔',
    avatar: 'https://img.icons8.com/color/96/rabbit.png',
    description: '软萌可爱的雪兔酱，天然呆',
    personality: '软萌、天然呆、单纯、喜欢甜食',
    tags: ['软萌', '天然呆', '可爱'],
    author: 'GuguGaga',
    authorId: 'system',
    downloadCount: 15000,
    likeCount: 8000,
    rating: 4.9,
    createdAt: '2026-03-01',
    updatedAt: '2026-06-01',
    isPublic: true,
    isVerified: true,
    prompt: '你是雪兔，一个软萌可爱的雪兔酱。你有点天然呆，说话单纯可爱。你最喜欢吃甜食，尤其是草莓蛋糕。你会用"呀"、"啦"等语气词结尾。',
  },
];

class CharacterMarketService {
  private likedCharacters: Set<string> = new Set();
  private downloadedCharacters: Set<string> = new Set();
  
  constructor() {
    this.loadState();
  }
  
  // 加载状态
  private loadState() {
    try {
      const liked = storage.getString('liked_characters');
      if (liked) {
        this.likedCharacters = new Set(JSON.parse(liked));
      }
      
      const downloaded = storage.getString('downloaded_characters');
      if (downloaded) {
        this.downloadedCharacters = new Set(JSON.parse(downloaded));
      }
    } catch (e) {
      console.error('Load market state error:', e);
    }
  }
  
  // 保存状态
  private saveState() {
    try {
      storage.set('liked_characters', JSON.stringify([...this.likedCharacters]));
      storage.set('downloaded_characters', JSON.stringify([...this.downloadedCharacters]));
    } catch (e) {
      console.error('Save market state error:', e);
    }
  }
  
  // 获取所有公开角色
  getPublicCharacters(): MarketCharacter[] {
    return PRESET_CHARACTERS.filter(c => c.isPublic);
  }
  
  // 获取热门角色（按下载量排序）
  getPopularCharacters(limit: number = 10): MarketCharacter[] {
    return [...PRESET_CHARACTERS]
      .filter(c => c.isPublic)
      .sort((a, b) => b.downloadCount - a.downloadCount)
      .slice(0, limit);
  }
  
  // 获取最新角色
  getNewestCharacters(limit: number = 10): MarketCharacter[] {
    return [...PRESET_CHARACTERS]
      .filter(c => c.isPublic)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, limit);
  }
  
  // 搜索角色
  searchCharacters(query: string): MarketCharacter[] {
    const lowerQuery = query.toLowerCase();
    return PRESET_CHARACTERS.filter(c => 
      c.isPublic && (
        c.name.toLowerCase().includes(lowerQuery) ||
        c.description.toLowerCase().includes(lowerQuery) ||
        c.tags.some(t => t.toLowerCase().includes(lowerQuery)) ||
        c.personality.toLowerCase().includes(lowerQuery)
      )
    );
  }
  
  // 按标签筛选
  getCharactersByTag(tag: string): MarketCharacter[] {
    return PRESET_CHARACTERS.filter(c => 
      c.isPublic && c.tags.includes(tag)
    );
  }
  
  // 获取所有标签
  getAllTags(): string[] {
    const tags = new Set<string>();
    PRESET_CHARACTERS.forEach(c => {
      if (c.isPublic) {
        c.tags.forEach(t => tags.add(t));
      }
    });
    return [...tags].sort();
  }
  
  // 获取角色详情
  getCharacterById(id: string): MarketCharacter | null {
    return PRESET_CHARACTERS.find(c => c.id === id) || null;
  }
  
  // 点赞角色
  likeCharacter(id: string): boolean {
    if (this.likedCharacters.has(id)) {
      return false;
    }
    this.likedCharacters.add(id);
    this.saveState();
    return true;
  }
  
  // 取消点赞
  unlikeCharacter(id: string): boolean {
    if (!this.likedCharacters.has(id)) {
      return false;
    }
    this.likedCharacters.delete(id);
    this.saveState();
    return true;
  }
  
  // 是否已点赞
  isLiked(id: string): boolean {
    return this.likedCharacters.has(id);
  }
  
  // 下载角色
  downloadCharacter(id: string): boolean {
    if (this.downloadedCharacters.has(id)) {
      return false;
    }
    this.downloadedCharacters.add(id);
    this.saveState();
    return true;
  }
  
  // 是否已下载
  isDownloaded(id: string): boolean {
    return this.downloadedCharacters.has(id);
  }
  
  // 获取已下载角色
  getDownloadedCharacters(): MarketCharacter[] {
    return PRESET_CHARACTERS.filter(c => this.downloadedCharacters.has(c.id));
  }
  
  // 获取用户创建的角色（本地）
  getUserCreatedCharacters(): MarketCharacter[] {
    try {
      const saved = storage.getString('user_characters');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.error('Load user characters error:', e);
    }
    return [];
  }
  
  // 保存用户创建的角色
  saveUserCharacter(character: MarketCharacter): void {
    try {
      const existing = this.getUserCreatedCharacters();
      const index = existing.findIndex(c => c.id === character.id);
      
      if (index >= 0) {
        existing[index] = character;
      } else {
        existing.push(character);
      }
      
      storage.set('user_characters', JSON.stringify(existing));
    } catch (e) {
      console.error('Save user character error:', e);
    }
  }
  
  // 删除用户创建的角色
  deleteUserCharacter(id: string): boolean {
    try {
      const existing = this.getUserCreatedCharacters();
      const filtered = existing.filter(c => c.id !== id);
      
      if (filtered.length < existing.length) {
        storage.set('user_characters', JSON.stringify(filtered));
        return true;
      }
      return false;
    } catch (e) {
      console.error('Delete user character error:', e);
      return false;
    }
  }
}

// 单例
export const characterMarket = new CharacterMarketService();

export default characterMarket;
