// ============================================
// 消息搜索服务
// ============================================
import { MMKV } from 'react-native-mmkv';
import type { Message, Conversation, Character } from '../types';

const storage = new MMKV({ id: 'message-search' });

// 搜索结果
export interface SearchResult {
  message: Message;
  conversation: Conversation;
  character: Character;
  matchContext: string; // 匹配的上下文
  matchScore: number; // 匹配分数
}

// 搜索过滤器
export interface SearchFilter {
  query: string;
  characterId?: string;
  dateFrom?: Date;
  dateTo?: Date;
  role?: 'user' | 'assistant' | 'system';
  limit?: number;
}

// 搜索历史
interface SearchHistoryEntry {
  query: string;
  timestamp: number;
  resultCount: number;
}

class MessageSearchService {
  private static instance: MessageSearchService;
  private searchHistory: SearchHistoryEntry[] = [];
  
  private constructor() {
    this.loadSearchHistory();
  }
  
  static getInstance(): MessageSearchService {
    if (!MessageSearchService.instance) {
      MessageSearchService.instance = new MessageSearchService();
    }
    return MessageSearchService.instance;
  }
  
  // 加载搜索历史
  private loadSearchHistory(): void {
    try {
      const saved = storage.getString('search_history');
      if (saved) {
        this.searchHistory = JSON.parse(saved);
      }
    } catch (e) {
      console.error('Load search history error:', e);
    }
  }
  
  // 保存搜索历史
  private saveSearchHistory(): void {
    try {
      storage.set('search_history', JSON.stringify(this.searchHistory));
    } catch (e) {
      console.error('Save search history error:', e);
    }
  }
  
  // 搜索消息
  async search(
    filter: SearchFilter,
    conversations: Conversation[],
    characters: Character[]
  ): Promise<SearchResult[]> {
    const results: SearchResult[] = [];
    const query = filter.query.toLowerCase().trim();
    
    if (!query) {
      return results;
    }
    
    // 遍历所有对话
    for (const conversation of conversations) {
      // 过滤角色
      if (filter.characterId && conversation.characterId !== filter.characterId) {
        continue;
      }
      
      // 查找角色
      const character = characters.find(c => c.id === conversation.characterId);
      if (!character) {
        continue;
      }
      
      // 遍历消息
      for (const message of conversation.messages) {
        // 过滤角色类型
        if (filter.role && message.role !== filter.role) {
          continue;
        }
        
        // 过滤日期
        const messageDate = new Date(message.timestamp);
        if (filter.dateFrom && messageDate < filter.dateFrom) {
          continue;
        }
        if (filter.dateTo && messageDate > filter.dateTo) {
          continue;
        }
        
        // 搜索匹配
        const content = message.content.toLowerCase();
        if (content.includes(query)) {
          // 计算匹配分数
          const matchScore = this.calculateMatchScore(content, query);
          
          // 提取匹配上下文
          const matchContext = this.extractContext(message.content, query);
          
          results.push({
            message,
            conversation,
            character,
            matchContext,
            matchScore,
          });
        }
      }
    }
    
    // 按匹配分数排序
    results.sort((a, b) => b.matchScore - a.matchScore);
    
    // 限制结果数量
    const limit = filter.limit || 50;
    const limitedResults = results.slice(0, limit);
    
    // 保存搜索历史
    this.addSearchHistory(query, limitedResults.length);
    
    return limitedResults;
  }
  
  // 计算匹配分数
  private calculateMatchScore(content: string, query: string): number {
    let score = 0;
    
    // 完全匹配
    if (content === query) {
      score += 100;
    }
    
    // 开头匹配
    if (content.startsWith(query)) {
      score += 50;
    }
    
    // 包含匹配
    const index = content.indexOf(query);
    if (index !== -1) {
      score += 30;
      
      // 越靠前分数越高
      score += Math.max(0, 20 - index);
    }
    
    // 关键词数量
    const words = query.split(/\s+/);
    for (const word of words) {
      if (content.includes(word)) {
        score += 10;
      }
    }
    
    return score;
  }
  
  // 提取匹配上下文
  private extractContext(content: string, query: string, contextLength: number = 50): string {
    const lowerContent = content.toLowerCase();
    const lowerQuery = query.toLowerCase();
    const index = lowerContent.indexOf(lowerQuery);
    
    if (index === -1) {
      return content.substring(0, contextLength * 2) + '...';
    }
    
    const start = Math.max(0, index - contextLength);
    const end = Math.min(content.length, index + query.length + contextLength);
    
    let context = '';
    if (start > 0) {
      context += '...';
    }
    context += content.substring(start, end);
    if (end < content.length) {
      context += '...';
    }
    
    return context;
  }
  
  // 添加搜索历史
  private addSearchHistory(query: string, resultCount: number): void {
    const entry: SearchHistoryEntry = {
      query,
      timestamp: Date.now(),
      resultCount,
    };
    
    // 移除重复
    this.searchHistory = this.searchHistory.filter(h => h.query !== query);
    
    // 添加到开头
    this.searchHistory.unshift(entry);
    
    // 只保留最近 20 条
    if (this.searchHistory.length > 20) {
      this.searchHistory.splice(20);
    }
    
    this.saveSearchHistory();
  }
  
  // 获取搜索历史
  getSearchHistory(): SearchHistoryEntry[] {
    return [...this.searchHistory];
  }
  
  // 清除搜索历史
  clearSearchHistory(): void {
    this.searchHistory = [];
    this.saveSearchHistory();
  }
  
  // 高亮匹配文本
  highlightMatch(text: string, query: string): Array<{ text: string; highlight: boolean }> {
    const result: Array<{ text: string; highlight: boolean }> = [];
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    
    let lastIndex = 0;
    let index = lowerText.indexOf(lowerQuery);
    
    while (index !== -1) {
      // 添加未匹配部分
      if (index > lastIndex) {
        result.push({
          text: text.substring(lastIndex, index),
          highlight: false,
        });
      }
      
      // 添加匹配部分
      result.push({
        text: text.substring(index, index + query.length),
        highlight: true,
      });
      
      lastIndex = index + query.length;
      index = lowerText.indexOf(lowerQuery, lastIndex);
    }
    
    // 添加剩余部分
    if (lastIndex < text.length) {
      result.push({
        text: text.substring(lastIndex),
        highlight: false,
      });
    }
    
    return result;
  }
  
  // 获取热门搜索
  getPopularSearches(limit: number = 5): string[] {
    const queryCount = new Map<string, number>();
    
    for (const entry of this.searchHistory) {
      const count = queryCount.get(entry.query) || 0;
      queryCount.set(entry.query, count + 1);
    }
    
    return [...queryCount.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit)
      .map(([query]) => query);
  }
  
  // 获取搜索统计
  getSearchStats(): {
    totalSearches: number;
    uniqueQueries: number;
    averageResults: number;
  } {
    const totalSearches = this.searchHistory.length;
    const uniqueQueries = new Set(this.searchHistory.map(h => h.query)).size;
    const totalResults = this.searchHistory.reduce((sum, h) => sum + h.resultCount, 0);
    const averageResults = totalSearches > 0 ? totalResults / totalSearches : 0;
    
    return {
      totalSearches,
      uniqueQueries,
      averageResults,
    };
  }
}

// 单例
export const messageSearchService = MessageSearchService.getInstance();

export default messageSearchService;
