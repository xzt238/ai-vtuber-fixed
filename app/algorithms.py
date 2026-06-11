"""
高级算法模块

提供优化的数据结构和算法：
1. AhoCorasick - 多模式字符串匹配（用于日志模式识别）
2. BM25 - 信息检索算法（用于记忆系统关键词搜索）
3. TDigest - 流式百分位数计算（用于性能监控）
4. HNSW - 近似最近邻搜索（用于向量检索）

作者: 咕咕嘎嘎
日期: 2026-06-10
"""

import math
import heapq
import random
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)


# ==================== Aho-Corasick 多模式匹配 ====================

class AhoCorasickNode:
    """Aho-Corasick 自动机节点"""
    __slots__ = ['children', 'fail', 'output', 'pattern_ids']

    def __init__(self):
        self.children: Dict[str, 'AhoCorasickNode'] = {}
        self.fail: Optional['AhoCorasickNode'] = None
        self.output: List[str] = []
        self.pattern_ids: List[int] = []


class AhoCorasick:
    """
    Aho-Corasick 多模式字符串匹配算法

    时间复杂度：
    - 构建: O(m) 其中 m 是所有模式的总长度
    - 匹配: O(n + z) 其中 n 是文本长度，z 是匹配数量

    适用于：日志模式识别、关键词过滤、敏感词检测
    """

    def __init__(self):
        self.root = AhoCorasickNode()
        self.patterns: List[str] = []
        self._built = False

    def add_pattern(self, pattern: str, pattern_id: Optional[int] = None) -> None:
        """添加模式串"""
        if pattern_id is None:
            pattern_id = len(self.patterns)

        node = self.root
        for char in pattern:
            if char not in node.children:
                node.children[char] = AhoCorasickNode()
            node = node.children[char]

        node.output.append(pattern)
        node.pattern_ids.append(pattern_id)
        self.patterns.append(pattern)
        self._built = False

    def build(self) -> None:
        """构建失败指针（BFS）"""
        if self._built:
            return

        queue = deque()

        # 第一层节点的失败指针指向根节点
        for child in self.root.children.values():
            child.fail = self.root
            queue.append(child)

        # BFS 构建失败指针
        while queue:
            current = queue.popleft()

            for char, child in current.children.items():
                queue.append(child)

                # 查找失败指针
                fail_node = current.fail
                while fail_node and char not in fail_node.children:
                    fail_node = fail_node.fail

                child.fail = fail_node.children.get(char) if fail_node else self.root

                if child.fail == child:
                    child.fail = self.root

                # 合并输出
                child.output.extend(child.fail.output)
                child.pattern_ids.extend(child.fail.pattern_ids)

        self._built = True

    def search(self, text: str) -> List[Tuple[int, str]]:
        """
        搜索文本中的所有模式

        Returns:
            List of (position, pattern) tuples
        """
        if not self._built:
            self.build()

        results = []
        node = self.root

        for i, char in enumerate(text):
            while node and char not in node.children:
                node = node.fail

            if node is None:
                node = self.root
                continue

            node = node.children[char]

            for pattern in node.output:
                results.append((i, pattern))

        return results

    def search_first(self, text: str) -> Optional[Tuple[int, str]]:
        """搜索第一个匹配"""
        if not self._built:
            self.build()

        node = self.root

        for i, char in enumerate(text):
            while node and char not in node.children:
                node = node.fail

            if node is None:
                node = self.root
                continue

            node = node.children[char]

            if node.output:
                return (i, node.output[0])

        return None


# ==================== BM25 信息检索算法 ====================

class BM25:
    """
    BM25 (Best Matching 25) 信息检索算法

    用于文档排序和关键词搜索，比简单的 TF-IDF 更准确。

    参数：
    - k1: 词频饱和参数（1.2-2.0）
    - b: 文档长度归一化参数（0.75）
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[List[str]] = []
        self.doc_ids: List[str] = []
        self.doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_freqs: Dict[str, int] = defaultdict(int)  # 包含词的文档数
        self.doc_lengths: List[int] = []
        self._idf_cache: Dict[str, float] = {}
        self._lock = threading.Lock()

    def add_document(self, doc_id: str, text: str) -> None:
        """添加文档"""
        with self._lock:
            words = self._tokenize(text)
            self.documents.append(words)
            self.doc_ids.append(doc_id)
            self.doc_lengths.append(len(words))
            self.doc_count += 1

            # 更新文档频率
            unique_words = set(words)
            for word in unique_words:
                self.doc_freqs[word] += 1

            # 更新平均文档长度
            self.avg_doc_len = sum(self.doc_lengths) / self.doc_count

            # 清除 IDF 缓存
            self._idf_cache.clear()

    def _tokenize(self, text: str) -> List[str]:
        """分词（简单实现，可替换为 jieba 等）"""
        # 简单的中英文分词
        import re
        # 英文单词
        words = re.findall(r'[a-zA-Z]+', text.lower())
        # 中文字符（单字）
        chinese = re.findall(r'[\u4e00-\u9fff]', text)
        return words + chinese

    def _idf(self, word: str) -> float:
        """计算 IDF (Inverse Document Frequency)"""
        if word in self._idf_cache:
            return self._idf_cache[word]

        n = self.doc_freqs.get(word, 0)
        # BM25 IDF 公式
        idf = math.log((self.doc_count - n + 0.5) / (n + 0.5) + 1)
        self._idf_cache[word] = idf
        return idf

    def _score_document(self, query_words: List[str], doc_index: int) -> float:
        """计算单个文档的 BM25 分数"""
        doc_words = self.documents[doc_index]
        doc_len = self.doc_lengths[doc_index]
        score = 0.0

        # 词频统计
        word_freq = defaultdict(int)
        for word in doc_words:
            word_freq[word] += 1

        for word in query_words:
            if word not in word_freq:
                continue

            tf = word_freq[word]
            idf = self._idf(word)

            # BM25 TF 公式
            tf_normalized = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            )

            score += idf * tf_normalized

        return score

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        搜索文档

        Returns:
            List of {doc_id, score} sorted by score descending
        """
        query_words = self._tokenize(query)
        if not query_words:
            return []

        scores = []
        for i in range(self.doc_count):
            score = self._score_document(query_words, i)
            if score > 0:
                scores.append({
                    "doc_id": self.doc_ids[i],
                    "score": score,
                    "index": i
                })

        # 按分数排序
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def remove_document(self, doc_id: str) -> bool:
        """删除文档"""
        with self._lock:
            try:
                idx = self.doc_ids.index(doc_id)
                self.doc_ids.pop(idx)
                self.documents.pop(idx)
                self.doc_lengths.pop(idx)
                self.doc_count -= 1

                # 重建文档频率
                self.doc_freqs.clear()
                for doc in self.documents:
                    for word in set(doc):
                        self.doc_freqs[word] += 1

                self.avg_doc_len = sum(self.doc_lengths) / max(self.doc_count, 1)
                self._idf_cache.clear()
                return True
            except ValueError:
                return False


# ==================== T-Digest 流式百分位数 ====================

@dataclass
class Centroid:
    """质心"""
    mean: float
    count: int

    def __lt__(self, other: 'Centroid') -> bool:
        return self.mean < other.mean


class TDigest:
    """
    T-Digest 流式百分位数算法

    优势：
    - 流式处理，无需存储所有数据
    - 内存占用固定
    - 极端百分位数（p99, p99.9）精度高

    适用于：性能监控、延迟统计、实时分析
    """

    def __init__(self, compression: float = 100.0):
        self.compression = compression
        self.centroids: List[Centroid] = []
        self.count = 0
        self._min = float('inf')
        self._max = float('-inf')
        self._lock = threading.Lock()

    def update(self, value: float, weight: int = 1) -> None:
        """添加数据点"""
        with self._lock:
            self.count += weight
            self._min = min(self._min, value)
            self._max = max(self._max, value)

            if not self.centroids:
                self.centroids.append(Centroid(value, weight))
                return

            # 找到插入位置
            idx = self._find_centroid_index(value)

            # 检查是否可以合并
            if idx < len(self.centroids) and abs(self.centroids[idx].mean - value) < 1e-10:
                self.centroids[idx].count += weight
            else:
                self.centroids.insert(idx, Centroid(value, weight))

            # 压缩
            if len(self.centroids) > self.compression * 2:
                self._compress()

    def _find_centroid_index(self, value: float) -> int:
        """二分查找插入位置"""
        lo, hi = 0, len(self.centroids) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.centroids[mid].mean < value:
                lo = mid + 1
            else:
                hi = mid - 1
        return lo

    def _compress(self) -> None:
        """压缩质心列表"""
        if len(self.centroids) <= 1:
            return

        # 计算每个质心的允许范围
        new_centroids = [self.centroids[0]]
        total = self.centroids[0].count

        for i in range(1, len(self.centroids)):
            centroid = self.centroids[i]
            last = new_centroids[-1]

            # 计算合并条件
            q = total / self.count
            k = 4 * self.count * q * (1 - q) / self.compression

            if last.count + centroid.count <= k:
                # 合并
                new_mean = (last.mean * last.count + centroid.mean * centroid.count) / (last.count + centroid.count)
                new_centroids[-1] = Centroid(new_mean, last.count + centroid.count)
            else:
                new_centroids.append(centroid)

            total += centroid.count

        self.centroids = new_centroids

    def percentile(self, p: float) -> float:
        """计算百分位数 (0-100)"""
        if not self.centroids:
            return 0.0

        if p <= 0:
            return self._min
        if p >= 100:
            return self._max

        target = p / 100.0 * self.count
        cumulative = 0.0

        for i, centroid in enumerate(self.centroids):
            if cumulative + centroid.count >= target:
                # 线性插值
                if i == 0:
                    return centroid.mean
                prev = self.centroids[i - 1]
                ratio = (target - cumulative) / centroid.count
                return prev.mean + ratio * (centroid.mean - prev.mean)
            cumulative += centroid.count

        return self._max

    def median(self) -> float:
        """计算中位数"""
        return self.percentile(50)

    def p95(self) -> float:
        """计算 P95"""
        return self.percentile(95)

    def p99(self) -> float:
        """计算 P99"""
        return self.percentile(99)

    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        return {
            "count": self.count,
            "min": self._min if self._min != float('inf') else 0,
            "max": self._max if self._max != float('-inf') else 0,
            "median": self.median(),
            "p95": self.p95(),
            "p99": self.p99(),
            "centroids": len(self.centroids)
        }


# ==================== HNSW 近似最近邻 ====================

class HNSWNode:
    """HNSW 图节点"""
    __slots__ = ['id', 'vector', 'neighbors', 'level']

    def __init__(self, id: str, vector: List[float], level: int = 0):
        self.id = id
        self.vector = vector
        self.neighbors: Dict[int, List[str]] = {}  # level -> [neighbor_ids]
        self.level = level


class HNSW:
    """
    Hierarchical Navigable Small World (HNSW) 近似最近邻搜索

    优势：
    - 查询时间 O(log n)
    - 支持动态插入删除
    - 内存效率高

    适用于：向量检索、语义搜索、推荐系统
    """

    def __init__(
        self,
        dim: int = 768,
        m: int = 16,
        ef_construction: int = 200,
        max_level: int = 16
    ):
        self.dim = dim
        self.m = m  # 每层最大邻居数
        self.ef_construction = ef_construction
        self.max_level = max_level
        self.nodes: Dict[str, HNSWNode] = {}
        self.entry_point: Optional[str] = None
        self.max_layer = 0
        self._lock = threading.Lock()

        # 概率参数
        self.ml = 1.0 / math.log(m)

    def _random_level(self) -> int:
        """随机生成节点层级"""
        level = 0
        while random.random() < self.ml and level < self.max_level:
            level += 1
        return level

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _distance(self, a: List[float], b: List[float]) -> float:
        """计算距离（1 - 相似度）"""
        return 1.0 - self._cosine_similarity(a, b)

    def insert(self, id: str, vector: List[float]) -> None:
        """插入节点"""
        with self._lock:
            if id in self.nodes:
                return

            level = self._random_level()
            node = HNSWNode(id, vector, level)
            self.nodes[id] = node

            if self.entry_point is None:
                self.entry_point = id
                self.max_layer = level
                return

            # 从顶层搜索到 level+1 层
            current = self.entry_point
            for l in range(self.max_layer, level, -1):
                current = self._search_layer(vector, current, 1, l)[0]

            # 从 level 层到底层，每层插入并连接邻居
            for l in range(min(level, self.max_layer), -1, -1):
                candidates = self._search_layer(vector, current, self.ef_construction, l)
                neighbors = self._select_neighbors(vector, candidates, self.m)

                node.neighbors[l] = neighbors
                for neighbor_id in neighbors:
                    neighbor = self.nodes[neighbor_id]
                    if l not in neighbor.neighbors:
                        neighbor.neighbors[l] = []
                    neighbor.neighbors[l].append(id)

                    # 保持邻居数限制
                    if len(neighbor.neighbors[l]) > self.m:
                        neighbor.neighbors[l] = self._select_neighbors(
                            neighbor.vector,
                            neighbor.neighbors[l],
                            self.m
                        )

                current = candidates[0] if candidates else current

            if level > self.max_layer:
                self.max_layer = level
                self.entry_point = id

    def _search_layer(
        self,
        query: List[float],
        entry: str,
        ef: int,
        layer: int
    ) -> List[str]:
        """在指定层搜索最近邻"""
        visited = {entry}
        candidates = [(self._distance(query, self.nodes[entry].vector), entry)]
        results = [(self._distance(query, self.nodes[entry].vector), entry)]

        while candidates:
            _, current = heapq.heappop(candidates)

            # 检查是否需要继续
            if results and results[0][0] < self._distance(query, self.nodes[current].vector):
                break

            # 遍历邻居
            neighbors = self.nodes[current].neighbors.get(layer, [])
            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)
                dist = self._distance(query, self.nodes[neighbor_id].vector)

                if len(results) < ef or dist < results[-1][0]:
                    heapq.heappush(candidates, (dist, neighbor_id))
                    heapq.heappush(results, (dist, neighbor_id))

                    if len(results) > ef:
                        heapq.heappop(results)

        return [node_id for _, node_id in sorted(results)]

    def _select_neighbors(
        self,
        query: List[float],
        candidates: List[str],
        m: int
    ) -> List[str]:
        """选择最近的 m 个邻居"""
        distances = [(self._distance(query, self.nodes[c].vector), c) for c in candidates]
        distances.sort()
        return [node_id for _, node_id in distances[:m]]

    def search(self, query: List[float], top_k: int = 10, ef: int = 50) -> List[Dict[str, Any]]:
        """搜索最近邻"""
        if not self.nodes:
            return []

        if self.entry_point is None:
            return []

        # 从顶层搜索到第 1 层
        current = self.entry_point
        for l in range(self.max_layer, 0, -1):
            current = self._search_layer(query, current, 1, l)[0]

        # 在第 0 层搜索 top_k
        results = self._search_layer(query, current, max(ef, top_k), 0)

        # 计算相似度并排序
        scored_results = []
        for node_id in results[:top_k]:
            similarity = self._cosine_similarity(query, self.nodes[node_id].vector)
            scored_results.append({
                "id": node_id,
                "similarity": similarity,
                "vector": self.nodes[node_id].vector
            })

        scored_results.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_results

    def delete(self, id: str) -> bool:
        """删除节点"""
        with self._lock:
            if id not in self.nodes:
                return False

            node = self.nodes[id]

            # 从所有邻居的邻居列表中移除
            for l, neighbors in node.neighbors.items():
                for neighbor_id in neighbors:
                    if neighbor_id in self.nodes:
                        neighbor = self.nodes[neighbor_id]
                        if l in neighbor.neighbors and id in neighbor.neighbors[l]:
                            neighbor.neighbors[l].remove(id)

            del self.nodes[id]

            # 更新入口点
            if id == self.entry_point:
                if self.nodes:
                    self.entry_point = next(iter(self.nodes))
                else:
                    self.entry_point = None

            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_nodes": len(self.nodes),
            "max_layer": self.max_layer,
            "entry_point": self.entry_point,
            "m": self.m,
            "ef_construction": self.ef_construction
        }


# ==================== 工厂函数 ====================

def create_aho_corasick(patterns: List[str]) -> AhoCorasick:
    """创建 Aho-Corasick 实例"""
    ac = AhoCorasick()
    for i, pattern in enumerate(patterns):
        ac.add_pattern(pattern, i)
    ac.build()
    return ac


def create_bm25() -> BM25:
    """创建 BM25 实例"""
    return BM25()


def create_tdigest(compression: float = 100.0) -> TDigest:
    """创建 T-Digest 实例"""
    return TDigest(compression)


def create_hnsw(dim: int = 768, m: int = 16) -> HNSW:
    """创建 HNSW 实例"""
    return HNSW(dim=dim, m=m)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试 Aho-Corasick
    print("=== 测试 Aho-Corasick ===")
    ac = AhoCorasick()
    patterns = ["error", "warning", "timeout", "memory"]
    for p in patterns:
        ac.add_pattern(p)
    ac.build()

    text = "This is an error message with a timeout warning"
    results = ac.search(text)
    print(f"文本: {text}")
    print(f"匹配: {results}")

    # 测试 BM25
    print("\n=== 测试 BM25 ===")
    bm25 = BM25()
    bm25.add_document("doc1", "Python is a great programming language")
    bm25.add_document("doc2", "Java is also a popular language")
    bm25.add_document("doc3", "Python and Java are both object-oriented")

    results = bm25.search("Python programming")
    print(f"搜索 'Python programming': {results}")

    # 测试 T-Digest
    print("\n=== 测试 T-Digest ===")
    td = TDigest()
    import random
    for _ in range(10000):
        td.update(random.gauss(100, 15))

    stats = td.get_stats()
    print(f"统计: {stats}")

    # 测试 HNSW
    print("\n=== 测试 HNSW ===")
    hnsw = HNSW(dim=3)
    vectors = [
        ("doc1", [1.0, 0.0, 0.0]),
        ("doc2", [0.0, 1.0, 0.0]),
        ("doc3", [0.0, 0.0, 1.0]),
        ("doc4", [0.7, 0.7, 0.0]),
    ]
    for id, vec in vectors:
        hnsw.insert(id, vec)

    results = hnsw.search([0.9, 0.1, 0.0], top_k=2)
    print(f"搜索 [0.9, 0.1, 0.0]: {results}")
