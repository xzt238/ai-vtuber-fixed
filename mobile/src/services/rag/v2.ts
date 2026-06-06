// ============================================
// RAG 知识库 V2 - 向量检索增强版
// ============================================
import { MMKV } from 'react-native-mmkv';
import * as FileSystem from 'expo-file-system';

const storage = new MMKV({ id: 'rag-v2' });

// 文档接口
export interface RAGDocument {
  id: string;
  title: string;
  content: string;
  metadata: Record<string, any>;
  embedding?: number[];
  createdAt: Date;
  updatedAt: Date;
}

// 检索结果
export interface RAGResult {
  document: RAGDocument;
  score: number;
  snippet: string;
}

// RAG 配置
export interface RAGConfig {
  // 向量维度
  embeddingDimension: number;
  
  // 检索数量
  topK: number;
  
  // 相似度阈值
  similarityThreshold: number;
  
  // 是否启用
  enabled: boolean;
}

// 默认配置
const DEFAULT_CONFIG: RAGConfig = {
  embeddingDimension: 384,
  topK: 5,
  similarityThreshold: 0.6,
  enabled: true,
};

// 简化的向量存储
interface VectorEntry {
  id: string;
  vector: number[];
  documentId: string;
}

class RAGServiceV2 {
  private static instance: RAGServiceV2;
  private config: RAGConfig;
  private documents: Map<string, RAGDocument> = new Map();
  private vectors: VectorEntry[] = [];
  
  private constructor() {
    this.config = this.loadConfig();
    this.loadDocuments();
  }
  
  static getInstance(): RAGServiceV2 {
    if (!RAGServiceV2.instance) {
      RAGServiceV2.instance = new RAGServiceV2();
    }
    return RAGServiceV2.instance;
  }
  
  // 加载配置
  private loadConfig(): RAGConfig {
    try {
      const saved = storage.getString('rag_v2_config');
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error('Load RAG config error:', e);
    }
    return { ...DEFAULT_CONFIG };
  }
  
  // 保存配置
  private saveConfig(): void {
    try {
      storage.set('rag_v2_config', JSON.stringify(this.config));
    } catch (e) {
      console.error('Save RAG config error:', e);
    }
  }
  
  // 加载文档
  private loadDocuments(): void {
    try {
      const saved = storage.getString('rag_documents');
      if (saved) {
        const parsed = JSON.parse(saved);
        parsed.forEach((doc: RAGDocument) => {
          this.documents.set(doc.id, {
            ...doc,
            createdAt: new Date(doc.createdAt),
            updatedAt: new Date(doc.updatedAt),
          });
        });
      }
    } catch (e) {
      console.error('Load documents error:', e);
    }
  }
  
  // 保存文档
  private saveDocuments(): void {
    try {
      const docs = Array.from(this.documents.values());
      storage.set('rag_documents', JSON.stringify(docs));
    } catch (e) {
      console.error('Save documents error:', e);
    }
  }
  
  // 添加文档
  async addDocument(title: string, content: string, metadata: Record<string, any> = {}): Promise<RAGDocument> {
    const id = `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const document: RAGDocument = {
      id,
      title,
      content,
      metadata,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    // 生成嵌入向量（简化版）
    document.embedding = this.generateEmbedding(content);
    
    // 存储文档
    this.documents.set(id, document);
    
    // 存储向量
    this.vectors.push({
      id: `vec_${id}`,
      vector: document.embedding,
      documentId: id,
    });
    
    this.saveDocuments();
    
    return document;
  }
  
  // 删除文档
  async deleteDocument(id: string): Promise<boolean> {
    if (!this.documents.has(id)) {
      return false;
    }
    
    this.documents.delete(id);
    this.vectors = this.vectors.filter(v => v.documentId !== id);
    
    this.saveDocuments();
    
    return true;
  }
  
  // 更新文档
  async updateDocument(id: string, updates: Partial<RAGDocument>): Promise<RAGDocument | null> {
    const document = this.documents.get(id);
    if (!document) {
      return null;
    }
    
    const updated: RAGDocument = {
      ...document,
      ...updates,
      updatedAt: new Date(),
    };
    
    // 如果内容更新，重新生成嵌入
    if (updates.content && updates.content !== document.content) {
      updated.embedding = this.generateEmbedding(updates.content);
      
      // 更新向量
      const vecIndex = this.vectors.findIndex(v => v.documentId === id);
      if (vecIndex !== -1) {
        this.vectors[vecIndex].vector = updated.embedding;
      }
    }
    
    this.documents.set(id, updated);
    this.saveDocuments();
    
    return updated;
  }
  
  // 获取文档
  getDocument(id: string): RAGDocument | null {
    return this.documents.get(id) || null;
  }
  
  // 获取所有文档
  getAllDocuments(): RAGDocument[] {
    return Array.from(this.documents.values());
  }
  
  // 检索文档
  async search(query: string, topK?: number): Promise<RAGResult[]> {
    if (!this.config.enabled) {
      return [];
    }
    
    const k = topK || this.config.topK;
    const queryEmbedding = this.generateEmbedding(query);
    
    // 计算相似度
    const results: RAGResult[] = [];
    
    for (const vector of this.vectors) {
      const similarity = this.cosineSimilarity(queryEmbedding, vector.vector);
      
      if (similarity >= this.config.similarityThreshold) {
        const document = this.documents.get(vector.documentId);
        if (document) {
          // 提取相关片段
          const snippet = this.extractSnippet(document.content, query);
          
          results.push({
            document,
            score: similarity,
            snippet,
          });
        }
      }
    }
    
    // 排序并返回 top K
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, k);
  }
  
  // 生成嵌入向量（简化版 - 基于词频）
  private generateEmbedding(text: string): number[] {
    const words = text.toLowerCase().split(/\s+/);
    const embedding: number[] = new Array(this.config.embeddingDimension).fill(0);
    
    // 简化的词频向量
    words.forEach((word, index) => {
      const hash = this.simpleHash(word);
      embedding[hash % this.config.embeddingDimension] += 1;
    });
    
    // 归一化
    const magnitude = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
    if (magnitude > 0) {
      return embedding.map(val => val / magnitude);
    }
    
    return embedding;
  }
  
  // 简单哈希函数
  private simpleHash(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // 转换为 32 位整数
    }
    return Math.abs(hash);
  }
  
  // 余弦相似度
  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;
    
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    
    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    
    if (normA === 0 || normB === 0) return 0;
    
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }
  
  // 提取相关片段
  private extractSnippet(content: string, query: string, maxLength: number = 200): string {
    const queryWords = query.toLowerCase().split(/\s+/);
    const sentences = content.split(/[。！？.!?]/);
    
    // 找到包含查询词最多的句子
    let bestSentence = '';
    let bestScore = 0;
    
    for (const sentence of sentences) {
      const lowerSentence = sentence.toLowerCase();
      let score = 0;
      
      for (const word of queryWords) {
        if (lowerSentence.includes(word)) {
          score++;
        }
      }
      
      if (score > bestScore) {
        bestScore = score;
        bestSentence = sentence;
      }
    }
    
    // 截断到最大长度
    if (bestSentence.length > maxLength) {
      return bestSentence.substring(0, maxLength) + '...';
    }
    
    return bestSentence || content.substring(0, maxLength) + '...';
  }
  
  // 获取统计信息
  getStats() {
    return {
      documentCount: this.documents.size,
      vectorCount: this.vectors.length,
      config: this.config,
    };
  }
  
  // 清空所有数据
  async clearAll(): Promise<void> {
    this.documents.clear();
    this.vectors = [];
    this.saveDocuments();
  }
  
  // 导出数据
  async exportData(): Promise<string> {
    const data = {
      documents: Array.from(this.documents.values()),
      vectors: this.vectors,
      config: this.config,
    };
    return JSON.stringify(data, null, 2);
  }
  
  // 导入数据
  async importData(jsonStr: string): Promise<boolean> {
    try {
      const data = JSON.parse(jsonStr);
      
      if (data.documents) {
        data.documents.forEach((doc: RAGDocument) => {
          this.documents.set(doc.id, doc);
        });
      }
      
      if (data.vectors) {
        this.vectors = data.vectors;
      }
      
      this.saveDocuments();
      return true;
    } catch (e) {
      console.error('Import data error:', e);
      return false;
    }
  }
  
  // 获取配置
  getConfig(): RAGConfig {
    return { ...this.config };
  }
  
  // 更新配置
  updateConfig(partial: Partial<RAGConfig>): void {
    this.config = { ...this.config, ...partial };
    this.saveConfig();
  }
}

// 单例
export const ragServiceV2 = RAGServiceV2.getInstance();

export default ragServiceV2;
