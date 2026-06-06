// ============================================
// GuguGaga AI VTuber Mobile - RAG 知识库服务
// ============================================
import { MMKV } from 'react-native-mmkv';
import * as FileSystem from 'expo-file-system';

const storage = new MMKV();

interface Document {
  id: string;
  title: string;
  content: string;
  chunks: TextChunk[];
  createdAt: Date;
  updatedAt: Date;
}

interface TextChunk {
  id: string;
  content: string;
  embedding: number[];
  metadata: {
    documentId: string;
    position: number;
    keywords: string[];
  };
}

interface SearchResult {
  chunk: TextChunk;
  score: number;
}

export class RAGService {
  private static instance: RAGService;
  private documents: Map<string, Document> = new Map();
  private chunks: TextChunk[] = [];

  private constructor() {
    this.loadFromStorage();
  }

  static getInstance(): RAGService {
    if (!RAGService.instance) {
      RAGService.instance = new RAGService();
    }
    return RAGService.instance;
  }

  // ============================================
  // 文档管理
  // ============================================
  async addDocument(title: string, content: string): Promise<Document> {
    const id = `doc_${Date.now()}`;
    const chunks = this.splitIntoChunks(content, id);

    const document: Document = {
      id,
      title,
      content,
      chunks,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.documents.set(id, document);
    this.chunks.push(...chunks);
    this.saveToStorage();

    return document;
  }

  async removeDocument(id: string): Promise<void> {
    const doc = this.documents.get(id);
    if (doc) {
      // 移除关联的 chunks
      this.chunks = this.chunks.filter(c => c.metadata.documentId !== id);
      this.documents.delete(id);
      this.saveToStorage();
    }
  }

  async updateDocument(id: string, content: string): Promise<void> {
    const doc = this.documents.get(id);
    if (doc) {
      // 移除旧 chunks
      this.chunks = this.chunks.filter(c => c.metadata.documentId !== id);
      // 生成新 chunks
      const newChunks = this.splitIntoChunks(content, id);
      doc.content = content;
      doc.chunks = newChunks;
      doc.updatedAt = new Date();
      this.chunks.push(...newChunks);
      this.saveToStorage();
    }
  }

  getDocuments(): Document[] {
    return Array.from(this.documents.values());
  }

  // ============================================
  // 文本分块
  // ============================================
  private splitIntoChunks(content: string, documentId: string): TextChunk[] {
    const chunks: TextChunk[] = [];
    const maxChunkSize = 500;
    const overlap = 50;

    // 按段落分割
    const paragraphs = content.split(/\n\n+/);
    let position = 0;

    for (const paragraph of paragraphs) {
      if (paragraph.trim().length === 0) continue;

      // 如果段落太长，按句子分割
      if (paragraph.length > maxChunkSize) {
        const sentences = paragraph.split(/[。！？；\n]/);
        let currentChunk = '';

        for (const sentence of sentences) {
          if (currentChunk.length + sentence.length > maxChunkSize && currentChunk.length > 0) {
            chunks.push(this.createChunk(currentChunk, documentId, position));
            position++;
            currentChunk = sentence;
          } else {
            currentChunk += (currentChunk ? '。' : '') + sentence;
          }
        }

        if (currentChunk.trim()) {
          chunks.push(this.createChunk(currentChunk, documentId, position));
          position++;
        }
      } else {
        chunks.push(this.createChunk(paragraph, documentId, position));
        position++;
      }
    }

    return chunks;
  }

  private createChunk(content: string, documentId: string, position: number): TextChunk {
    return {
      id: `chunk_${documentId}_${position}`,
      content: content.trim(),
      embedding: this.simpleEmbedding(content),
      metadata: {
        documentId,
        position,
        keywords: this.extractKeywords(content),
      },
    };
  }

  // ============================================
  // 简化的向量嵌入（基于关键词）
  // ============================================
  private simpleEmbedding(text: string): number[] {
    // 简化的嵌入：基于字符频率的 128 维向量
    const embedding = new Array(128).fill(0);
    const chars = text.split('');

    for (let i = 0; i < chars.length; i++) {
      const code = chars[i].charCodeAt(0);
      embedding[code % 128] += 1;
    }

    // 归一化
    const sum = embedding.reduce((a, b) => a + b * b, 0);
    const norm = Math.sqrt(sum);
    return norm > 0 ? embedding.map(v => v / norm) : embedding;
  }

  // ============================================
  // 关键词提取
  // ============================================
  private extractKeywords(text: string): string[] {
    // 简化的关键词提取
    const stopWords = new Set(['的', '了', '是', '在', '我', '你', '他', '她', '它', '这', '那', '有', '和', '与', '或', '但', '而', '也', '都', '就', '不']);
    const words = text.split(/[\s,，。！？；：、\n]+/).filter(w => w.length > 1 && !stopWords.has(w));
    const wordCount = new Map<string, number>();

    for (const word of words) {
      wordCount.set(word, (wordCount.get(word) || 0) + 1);
    }

    return Array.from(wordCount.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([word]) => word);
  }

  // ============================================
  // 检索
  // ============================================
  async search(query: string, topK: number = 3): Promise<SearchResult[]> {
    const queryEmbedding = this.simpleEmbedding(query);
    const queryKeywords = this.extractKeywords(query);

    const results: SearchResult[] = [];

    for (const chunk of this.chunks) {
      // 向量相似度
      const vectorScore = this.cosineSimilarity(queryEmbedding, chunk.embedding);

      // 关键词匹配
      const keywordScore = queryKeywords.filter(k => chunk.metadata.keywords.includes(k)).length / Math.max(queryKeywords.length, 1);

      // 内容匹配
      const contentScore = query.split('').filter(c => chunk.content.includes(c)).length / query.length;

      // 综合分数
      const totalScore = vectorScore * 0.4 + keywordScore * 0.4 + contentScore * 0.2;

      if (totalScore > 0.1) {
        results.push({ chunk, score: totalScore });
      }
    }

    return results
      .sort((a, b) => b.score - a.score)
      .slice(0, topK);
  }

  // ============================================
  // 构建 RAG 上下文
  // ============================================
  async buildContext(query: string): Promise<string> {
    const results = await this.search(query, 3);

    if (results.length === 0) {
      return '';
    }

    const context = results
      .map((r, i) => `[参考${i + 1}] ${r.chunk.content}`)
      .join('\n\n');

    return `以下是一些相关的参考资料，请基于这些信息回答用户的问题：\n\n${context}\n\n用户问题：${query}`;
  }

  // ============================================
  // 工具方法
  // ============================================
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
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB) || 1);
  }

  private saveToStorage(): void {
    try {
      const data = {
        documents: Array.from(this.documents.entries()),
        chunks: this.chunks,
      };
      storage.set('rag_data', JSON.stringify(data));
    } catch (error) {
      console.error('RAG save error:', error);
    }
  }

  private loadFromStorage(): void {
    try {
      const data = storage.getString('rag_data');
      if (data) {
        const parsed = JSON.parse(data);
        this.documents = new Map(parsed.documents);
        this.chunks = parsed.chunks || [];
      }
    } catch (error) {
      console.error('RAG load error:', error);
    }
  }

  // 从文件导入
  async importFromFile(uri: string, title?: string): Promise<Document> {
    try {
      const content = await FileSystem.readAsStringAsync(uri);
      const fileName = uri.split('/').pop() || 'document';
      return await this.addDocument(title || fileName, content);
    } catch (error) {
      console.error('Import file error:', error);
      throw error;
    }
  }

  // 获取统计信息
  getStats(): { documentCount: number; chunkCount: number } {
    return {
      documentCount: this.documents.size,
      chunkCount: this.chunks.length,
    };
  }
}

export const ragService = RAGService.getInstance();
