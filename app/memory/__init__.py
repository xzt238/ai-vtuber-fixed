#!/usr/bin/env python3
"""
=====================================
RAG 记忆系统模块 - v3.0 全面重构
=====================================

v3.0 改进点 (对标 Mem0/Letta/Zep):
- 重要性评分: 多维梯度评分(长度/问题/个人信息/情感/知识深度), 不再只有0/4/5
- 摘要压缩: LLM 语义摘要替代硬截断, 降级到规则摘要
- 事实提取: 规则+LLM 双模式, 独立保存用户偏好/事实
- 向量库: 降低入库阈值(>=3), 添加去重, 确保数据落盘
- 遗忘衰减: 降低衰减速度, 新记忆保护期, 重要性时间衰减保护
- 记忆去重: 向量相似度去重
- 自动标签: 基于关键词的领域分类
- 记忆重整: 跨层整合优化

作者: 咕咕嘎嘎
日期: 2026-04-28
"""

import os
import json
import time
import math
import re
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
from dataclasses import dataclass, asdict, field


# ==================== 数据结构 ====================

@dataclass
class MemoryItem:
    """记忆条目(增强版:支持遗忘机制 + 事实提取)"""
    role: str  # user/assistant/system
    content: str
    timestamp: float
    importance: int = 0  # 0-5, 5最重要
    tags: List[str] = field(default_factory=list)
    
    # 遗忘机制字段
    access_count: int = 1      # 被检索命中的次数
    connectivity: int = 0      # 与其他记忆的共现次数(关联度)
    is_forgotten: bool = False  # 软删除标记
    is_summary: bool = False    # 是否为摘要压缩后的记忆
    
    # v3.0 新增字段
    facts: List[str] = field(default_factory=list)  # 从此条提取的事实
    summary_text: str = ""  # LLM 生成的摘要文本
    
    def __post_init__(self):
        """数据类初始化后处理(确保字段不为 None)"""
        if self.tags is None:
            self.tags = []
        if self.facts is None:
            self.facts = []
    
    def get_retention_score(self) -> float:
        """计算当前保留分数"""
        hours_old = (time.time() - self.timestamp) / 3600
        return RetentionScorer.compute_retention_score(
            importance=self.importance,
            hours_old=hours_old,
            access_count=self.access_count,
            connectivity=self.connectivity
        )
    
    def should_forget(self) -> bool:
        """判断是否应该遗忘"""
        if self.is_forgotten:
            return True
        return RetentionScorer.should_forget(self.get_retention_score())
    
    def touch(self):
        """记忆被访问时调用,增加访问计数"""
        self.access_count += 1
    
    def link(self, other_mem_id: str):
        """与其他记忆建立关联,增加关联计数"""
        self.connectivity += 1


@dataclass
class FactItem:
    """独立事实条目(从对话中提取的用户偏好/个人信息/关键事实)"""
    content: str       # 事实内容
    source: str        # 来源(user_preference / user_info / key_fact)
    confidence: float  # 置信度 0-1
    timestamp: float   # 提取时间
    access_count: int = 1
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# ==================== 遗忘机制 ====================

class RetentionScorer:
    """
    智能遗忘机制 v2
    保留分数 = 重要性 × 时效衰减 × 访问频率 × 关联度
    
    v3.0 改进:
    - 降低衰减速度 (lambda 0.01→0.005, 记忆存续更久)
    - 新记忆保护期 (12小时内不参与遗忘扫描)
    - 重要性时间衰减保护 (importance>=3 的记忆衰减减半)
    """
    
    # 时效衰减系数 — v3.0: 0.005 (原来0.01太快,7天前importance=3的记忆就衰减到0.08)
    DECAY_LAMBDA = 0.005
    
    # 软删除阈值
    RETENTION_THRESHOLD = 0.15  # v3.0: 从0.3降到0.15, 更宽容
    
    # 新记忆保护期(小时) — 保护期内不参与遗忘扫描
    GRACE_PERIOD_HOURS = 12.0
    
    # 关联度计算用的共现窗口
    COOCCUR_WINDOW = 5
    
    @classmethod
    def compute_recency_decay(cls, hours_old: float) -> float:
        """计算时效衰减系数 e^(-lambda * hours)"""
        return math.exp(-cls.DECAY_LAMBDA * hours_old)
    
    @classmethod
    def compute_retention_score(
        cls,
        importance: float,      # 0-5 原始重要性评分
        hours_old: float,       # 距现在的小时数
        access_count: int = 1,  # 访问次数
        connectivity: int = 0   # 关联度
    ) -> float:
        """
        计算保留分数 0.0 ~ 1.0
        
        公式: importance_norm × recency_decay × access_boost × connectivity_boost
        v3.0: importance>=3 的记忆使用减半衰减
        """
        importance_norm = importance / 5.0
        
        # v3.0: 重要性保护 — importance>=3 使用减半衰减系数
        if importance >= 3:
            recency = math.exp(-cls.DECAY_LAMBDA * 0.5 * hours_old)
        else:
            recency = cls.compute_recency_decay(hours_old)
        
        # 访问频率加成(对数曲线)
        access_boost = 1.0 + 0.2 * math.log1p(access_count)
        
        # 关联度加成
        connectivity_boost = 1.0 + 0.1 * connectivity
        
        score = importance_norm * recency * access_boost * connectivity_boost
        return min(score, 1.0)
    
    @classmethod
    def should_forget(cls, retention_score: float) -> bool:
        """判断是否应该遗忘"""
        return retention_score < cls.RETENTION_THRESHOLD
    
    @classmethod
    def is_in_grace_period(cls, hours_old: float) -> bool:
        """是否在新记忆保护期内"""
        return hours_old < cls.GRACE_PERIOD_HOURS
    
    @classmethod
    def get_decay_stats(cls, hours_old: float) -> Dict[str, float]:
        """获取衰减统计(用于调试)"""
        return {
            "hours_old": hours_old,
            "recency_decay": cls.compute_recency_decay(hours_old),
            "score_at_importance_5": cls.compute_retention_score(5, hours_old),
            "score_at_importance_3": cls.compute_retention_score(3, hours_old),
            "score_at_importance_1": cls.compute_retention_score(1, hours_old),
            "score_at_importance_0": cls.compute_retention_score(0, hours_old),
        }


# ==================== 重要性评分 v2 ====================

class ImportanceScorer:
    """
    重要性评分器 v2 — 多维梯度评分
    
    评分维度:
    1. 内容长度: 短闲聊→0, 中等→1, 长→2
    2. 问题检测: 疑问句+1
    3. 关键词匹配: 根据类别梯度加分
    4. 个人信息: 名字/偏好/身份 → 3-5
    5. 情感强度: 感叹/表情 → +1
    6. 知识深度: 专业术语/概念 → +2
    7. 明确记忆指令: "记住" → 5
    
    结果: 0-5的连续梯度, 不再只有0/4/5三个值
    """
    
    # ===== 关键词分类 (从低到高梯度) =====
    
    # 信息交换词 (score=2) — 包含实质信息但不关键
    INFO_WORDS = [
        "因为", "所以", "原因", "结果", "方法", "方式",
        "认为", "觉得", "想法", "观点", "看法",
        "工作", "学习", "项目", "计划", "目标",
        "问题", "解决", "方案", "建议",
    ]
    
    # 个人偏好词 (score=3) — 用户个人喜好/习惯
    PREFERENCE_WORDS = [
        "喜欢", "讨厌", "偏好", "习惯", "不想", "不愿意",
        "最爱", "最讨厌", "受不了", "受不了",
        "喜欢用", "习惯了", "更倾向于", "更偏爱",
        "不要", "拒绝", "禁止", "别用", "避免",
    ]
    
    # 个人信息词 (score=4) — 身份/联系方式等
    IDENTITY_WORDS = [
        "名字", "叫", "我是", "电话", "地址", "账号",
        "邮箱", "email", "生日", "年龄", "职业",
        "住", "来自", "家乡", "学校", "公司",
    ]
    
    # 明确记忆指令 (score=5) — 用户要求记住
    MEMORY_COMMAND_WORDS = [
        "记住", "记住这个", "不要忘记", "下次记住",
        "记住我", "别忘了", "一定要记住", "帮我记",
        "remember", "keep in mind", "don't forget",
    ]
    
    # 忽略词 (极短闲聊)
    IGNORE_WORDS = [
        "你好", "hi", "hello", "在吗", "嗯", "哦", "好", "啊",
        "哈", "呵", "嗯嗯", "好的", "ok", "OK", "嗯呢",
    ]
    
    # 情感强度标记
    EMOTION_MARKERS = ["！", "！","？", "？", "...", "……", "😂", "😭", "🤔", "👍", "❤"]
    
    # 知识深度标记 (专业术语/概念性内容)
    KNOWLEDGE_PATTERNS = [
        r'(?:矩阵|向量|维度|映射|函数|算法|模型|架构|协议|接口|模块|组件)',
        r'(?:系统|框架|原理|机制|逻辑|策略|优化|参数|配置|部署)',
        r'(?:分析|设计|实现|集成|测试|验证|评估|监控)',
        r'(?:数据|信息|知识|理论|概念|定义|分类|结构)',
    ]
    
    @classmethod
    def score(cls, role: str, content: str) -> int:
        """
        多维梯度评分 0-5
        
        评分维度:
        1. 内容长度: 基础分
        2. 问题检测: 疑问句加分
        3. 关键词匹配: 梯度加分
        4. 情感强度: 感叹号/表情加分
        5. 知识深度: 专业术语加分
        """
        content_lower = content.lower()
        s = 0  # 当前分数
        
        # ===== 维度1: 内容长度 (基础分) =====
        content_len = len(content)
        if content_len < 5:
            # 极短: 检查是否闲聊
            for word in cls.IGNORE_WORDS:
                if word in content_lower:
                    return 0
            s = 0  # 极短但不是闲聊, 保留
        elif content_len < 20:
            s = 0  # 短句
        elif content_len < 50:
            s = 1  # 中短
        elif content_len < 100:
            s = 1  # 中等
        else:
            s = 2  # 长内容有信息量
        
        # ===== 维度2: 问题检测 =====
        if '？' in content or '?' in content or content.endswith('吗') or content.endswith('呢'):
            s += 1
        
        # ===== 维度3: 关键词匹配 (梯度) =====
        # 信息交换 → +0 (已在基础分中)
        for word in cls.INFO_WORDS:
            if word in content_lower:
                s = max(s, 2)
                break
        
        # 个人偏好 → 至少3
        for word in cls.PREFERENCE_WORDS:
            if word in content_lower:
                s = max(s, 3)
                break
        
        # 个人信息 → 至少4
        for word in cls.IDENTITY_WORDS:
            if word in content_lower:
                s = max(s, 4)
                break
        
        # 明确记忆指令 → 5
        for word in cls.MEMORY_COMMAND_WORDS:
            if word in content_lower:
                s = 5
                break
        
        # ===== 维度4: 情感强度 =====
        emotion_count = sum(1 for m in cls.EMOTION_MARKERS if m in content)
        if emotion_count >= 2:
            s += 1
        
        # ===== 维度5: 知识深度 =====
        for pattern in cls.KNOWLEDGE_PATTERNS:
            if re.search(pattern, content):
                s += 1
                break
        
        # ===== 用户消息额外加分 =====
        if role == "user" and s >= 2:
            s = min(s + 1, 5)  # 用户说的有价值的话多加1分
        
        return min(s, 5)
    
    @classmethod
    def is_important(cls, score: int) -> bool:
        """判断是否重要(>=3分视为重要)"""
        return score >= 3
    
    @classmethod
    def is_critical(cls, score: int) -> bool:
        """判断是否关键记忆(>=4分)"""
        return score >= 4


# ==================== 事实提取器 ====================

class FactExtractor:
    """
    事实提取器 v1 — 规则优先 + LLM 降级
    
    从对话中提取独立事实:
    - 用户偏好: "我喜欢...", "我讨厌..."
    - 用户信息: "我叫...", "我在..."
    - 关键事实: 被标记为重要的知识
    """
    
    # 偏好提取模式
    PREFERENCE_PATTERNS = [
        (r'我(喜欢|爱|偏好|最爱|更倾向)(.+?)(?:[，。！？,.]|$)', 'user_preference'),
        (r'我(讨厌|不喜欢|反感|最讨厌|受不了)(.+?)(?:[，。！？,.]|$)', 'user_preference'),
        (r'我(不要|不想|拒绝|别用)(.+?)(?:[，。！？,.]|$)', 'user_preference'),
        (r'我习惯(.+?)(?:[，。！？,.]|$)', 'user_preference'),
    ]
    
    # 个人信息提取模式
    INFO_PATTERNS = [
        (r'我(?:叫|名字是?)(.{1,10}?)(?:[，。！？,.]|$)', 'user_info'),
        (r'我(?:是|在)(.{1,20}?)(?:工作|上学|住|来自)', 'user_info'),
        (r'我(?:的?)(?:电话|邮箱|地址|微信|QQ)(?:是|:|：)?(.{1,30}?)(?:[，。！？,.]|$)', 'user_info'),
        (r'我(?:的)?生日(?:是|在)?(.{1,15}?)(?:[，。！？,.]|$)', 'user_info'),
    ]
    
    @classmethod
    def extract_facts(cls, role: str, content: str, importance: int) -> List[FactItem]:
        """从对话中提取事实(纯规则,快速)"""
        if role != "user":
            return []
        
        facts = []
        now = time.time()
        
        # 偏好提取
        for pattern, source in cls.PREFERENCE_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    fact_text = f"用户{match[0]}{match[1]}"
                else:
                    fact_text = f"用户{match}"
                if len(fact_text) > 4:  # 过滤太短的
                    facts.append(FactItem(
                        content=fact_text,
                        source=source,
                        confidence=0.8,
                        timestamp=now,
                        tags=["偏好"],
                    ))
        
        # 个人信息提取
        for pattern, source in cls.INFO_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    fact_text = match[0] if match[0] else str(match)
                else:
                    fact_text = match
                if len(fact_text) > 1:
                    facts.append(FactItem(
                        content=fact_text,
                        source=source,
                        confidence=0.9,
                        timestamp=now,
                        tags=["个人信息"],
                    ))
        
        # 重要内容自动提取为事实
        if importance >= 4 and len(content) > 20:
            # 对长内容提取关键信息
            fact_text = content[:100]
            facts.append(FactItem(
                content=fact_text,
                source="key_fact",
                confidence=0.7,
                timestamp=now,
                tags=["重要事实"],
            ))
        
        return facts
    
    @classmethod
    def extract_with_llm(cls, content: str, llm_chat_func) -> List[FactItem]:
        """
        LLM 事实提取(降级方案: 规则提取为空时调用)
        
        llm_chat_func: callable(message) -> {"text": ...}
        """
        if not llm_chat_func:
            return []
        
        try:
            prompt = f"""从以下对话中提取独立事实。只返回事实列表,每行一条,格式: 事实内容

要求:
1. 只提取客观事实和用户偏好,不要提取对话本身
2. 每条事实独立完整,不依赖上下文
3. 如果没有可提取的事实,返回空

对话内容:
{content}

事实列表:"""
            
            result = llm_chat_func(message=prompt)
            text = result.get("text", "").strip()
            
            if not text:
                return []
            
            facts = []
            now = time.time()
            for line in text.split("\n"):
                line = line.strip().lstrip("-•*0-9. ")
                if len(line) > 5:
                    # 简单判断类型
                    source = "user_preference" if any(w in line for w in ["喜欢", "讨厌", "偏好", "习惯"]) else "key_fact"
                    facts.append(FactItem(
                        content=line,
                        source=source,
                        confidence=0.7,
                        timestamp=now,
                    ))
            return facts
        except Exception as e:
            print(f" [记忆] LLM事实提取失败: {e}")
            return []


# ==================== 自动标签系统 ====================

class AutoTagger:
    """
    自动标签系统 — 基于关键词的领域分类
    
    自动为记忆条目打上领域标签,辅助检索和浏览
    """
    
    TAG_KEYWORDS = {
        "编程": ["代码", "python", "javascript", "函数", "API", "bug", "调试", "编程", "开发", "部署", "git", "编译"],
        "AI/ML": ["模型", "训练", "推理", "神经网络", "深度学习", "机器学习", "AI", "LLM", "GPT", "embedding", "向量"],
        "声音/TTS": ["声音", "语音", "TTS", "音色", "克隆", "GPT-SoVITS", "推理", "参考音频", "训练模型"],
        "记忆系统": ["记忆", "遗忘", "摘要", "向量", "检索", "工作记忆", "情景记忆"],
        "情感": ["开心", "难过", "生气", "焦虑", "喜欢", "讨厌", "感动", "失望", "担心"],
        "日常": ["天气", "吃饭", "睡觉", "运动", "旅行", "电影", "音乐", "游戏"],
        "工作": ["项目", "任务", "会议", "deadline", "截止", "进度", "需求", "上线"],
        "学习": ["学习", "考试", "课程", "论文", "研究", "知识", "理解", "概念"],
        "个人": ["名字", "年龄", "生日", "电话", "地址", "家乡", "职业", "爱好"],
    }
    
    @classmethod
    def tag(cls, content: str) -> List[str]:
        """为内容自动打标签"""
        tags = []
        content_lower = content.lower()
        for tag, keywords in cls.TAG_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    tags.append(tag)
                    break
        return tags


# ==================== LRU 缓存 ====================

class LRUCache:
    """LRU 缓存"""
    
    def __init__(self, capacity: int = 100):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


# ==================== 向量存储 ====================

class VectorStore:
    """
    向量存储 v2 — 增加去重
    
    v3.0 改进:
    - 降低入库阈值 (不再只存 importance>=4, 所有记忆都入库)
    - 添加向量去重 (cosine > 0.95 视为重复)
    - 确保 flush 逻辑完善
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.storage_dir = self.config.get("storage_dir", "./memory/vectors")
        # 立即解析为绝对路径，防止 os.chdir() 导致路径漂移
        if not os.path.isabs(self.storage_dir):
            self.storage_dir = str(Path(self.storage_dir).resolve())
        self.embedding_dim = self.config.get("embedding_dim", 768)
        
        self.vectors = {}
        self.texts = {}
        self.metadatas = {}
        self._norms = {}
        
        self._embedding_cache = LRUCache(200)
        self._search_cache = LRUCache(50)
        self.embedding_model = None
        self._model_loaded = False
        self._pending_save = False
        
        # 去重阈值
        self._dedup_threshold = self.config.get("dedup_threshold", 0.95)
        
        self._persist_file = Path(self.storage_dir) / "vector_store.json"
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        self._retrieval_weights = (config or {}).get("retrieval_weights", {"vector": 0.5, "keyword": 0.3, "recency": 0.2})
        self._embed_device = (config or {}).get("embedding_device", "cpu")
        self._embed_model_name = (config or {}).get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self._load_from_disk()
    
    def _get_norm(self, doc_id: str) -> float:
        if doc_id not in self._norms:
            emb = self.vectors[doc_id]
            self._norms[doc_id] = sum(x * x for x in emb) ** 0.5
        return self._norms[doc_id]
    
    def _load_from_disk(self):
        if not self._persist_file.exists():
            return
        try:
            print(" 加载持久化记忆...")
            with open(self._persist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.vectors = data.get("vectors", {})
            self.texts = data.get("texts", {})
            self.metadatas = data.get("metadatas", {})
            self._norms.clear()  # 重建范数缓存
            print(f" 已加载 {len(self.texts)} 条语义记忆")
        except Exception as e:
            print(f"️ 加载记忆失败: {e}")
    
    def _save_to_disk(self):
        try:
            data = {
                "vectors": self.vectors,
                "texts": self.texts,
                "metadatas": self.metadatas,
                "updated_at": datetime.now().isoformat(),
            }
            tmp_file = self._persist_file.with_suffix('.tmp')
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self._persist_file)
        except Exception as e:
            print(f"️ 保存记忆失败: {e}")
    
    def _get_local_model_path(self) -> str:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_name = self._embed_model_name
        hf_style = model_name.replace("/", "--")
        model_basename = model_name.split("/")[-1]
        ms_escaped = model_basename.replace(".", "___")
        ms_org = model_name.split("/")[0] if "/" in model_name else ""
        
        search_paths = [
            os.path.join(project_root, '.cache', 'modelscope', ms_org, ms_escaped) if ms_org else "",
            os.path.join(project_root, '.cache', 'modelscope', 'hub', 'hub', 'sentence-transformers', model_basename),
            os.path.join(project_root, '.cache', 'huggingface', 'hub', f"models--{hf_style}"),
            os.path.join(project_root, 'models', 'modelscope', 'hub', 'hub', 'sentence-transformers', model_basename),
        ]
        
        for path in search_paths:
            if not path:
                continue
            if os.path.isfile(os.path.join(path, 'model.safetensors')) or \
               os.path.isfile(os.path.join(path, 'pytorch_model.bin')):
                return path
            if os.path.isdir(os.path.join(path, 'snapshots')):
                snapshots_dir = os.path.join(path, 'snapshots')
                snapshots = os.listdir(snapshots_dir) if os.path.isdir(snapshots_dir) else []
                if snapshots:
                    snap_path = os.path.join(snapshots_dir, snapshots[0])
                    if os.path.isfile(os.path.join(snap_path, 'model.safetensors')) or \
                       os.path.isfile(os.path.join(snap_path, 'pytorch_model.bin')):
                        return snap_path
        
        ms_cache = os.path.join(project_root, '.cache', 'modelscope')
        if os.path.isdir(ms_cache):
            for org_dir in os.listdir(ms_cache):
                org_path = os.path.join(ms_cache, org_dir)
                if not os.path.isdir(org_path):
                    continue
                for model_dir in os.listdir(org_path):
                    clean_dir = model_dir.replace("___", ".").replace("--", "/")
                    if model_basename in clean_dir or clean_dir.endswith(model_basename):
                        full_path = os.path.join(org_path, model_dir)
                        if os.path.isfile(os.path.join(full_path, 'model.safetensors')) or \
                           os.path.isfile(os.path.join(full_path, 'pytorch_model.bin')):
                            return full_path
        return ""
    
    def _load_embedding_model(self):
        if self._model_loaded:
            return
        self._model_loaded = True
        try:
            from sentence_transformers import SentenceTransformer
            device = self._embed_device
            model_name = self._embed_model_name
            local_path = self._get_local_model_path()
            if local_path:
                print(f" [记忆系统] 加载本地嵌入模型: {local_path} | device={device}")
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                self.embedding_model = SentenceTransformer(local_path, device=device)
            else:
                print(f" [记忆系统] 未找到本地缓存,尝试在线加载: {model_name} | device={device}")
                self.embedding_model = SentenceTransformer(model_name, device=device)
            actual_dim = self.embedding_model.get_sentence_embedding_dimension()
            if actual_dim != self.embedding_dim:
                print(f" [记忆系统] 维度自动修正: {self.embedding_dim} -> {actual_dim}")
                self.embedding_dim = actual_dim
            print(" [记忆系统] 嵌入模型加载成功!")
        except ImportError:
            print(" [记忆系统] sentence-transformers 未安装,使用简单嵌入")
            self.embedding_model = "simple"
        except Exception as e:
            print(f" [记忆系统] 嵌入模型加载失败({type(e).__name__}): {e},使用简单嵌入")
            self.embedding_model = "simple"
    
    def get_embedding(self, text: str) -> List[float]:
        cached = self._embedding_cache.get(text)
        if cached is not None:
            return cached
        if not self._model_loaded:
            self._load_embedding_model()
        if self.embedding_model == "simple":
            embedding = self._simple_embedding(text)
        elif self.embedding_model:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True).tolist()
        else:
            import random
            embedding = [random.random() for _ in range(self.embedding_dim)]
        self._embedding_cache.put(text, embedding)
        return embedding
    
    def _simple_embedding(self, text: str) -> List[float]:
        words = text.lower().split()
        vector = [0.0] * self.embedding_dim
        for i, word in enumerate(words[:self.embedding_dim]):
            vector[i % self.embedding_dim] += hash(word) % 1000 / 1000.0
        total = sum(vector) or 1
        return [v / total for v in vector]
    
    def _is_duplicate(self, text: str, embedding: List[float]) -> bool:
        """检查是否与已有向量重复(cosine > threshold)"""
        if not self.vectors:
            return False
        norm_a = sum(x * x for x in embedding) ** 0.5
        if norm_a == 0:
            return False
        for doc_id, existing_emb in self.vectors.items():
            sim = self._cosine_similarity(embedding, norm_a, existing_emb)
            if sim > self._dedup_threshold:
                return True
        return False
    
    def add(self, text: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """添加文本到向量存储(带去重)"""
        import uuid
        
        embedding = self.get_embedding(text)
        
        # v3.0: 去重检查
        if self._is_duplicate(text, embedding):
            return None
        
        doc_id = str(uuid.uuid4())
        self.vectors[doc_id] = embedding
        self.texts[doc_id] = text
        self.metadatas[doc_id] = metadata or {}
        self._norms[doc_id] = sum(x * x for x in embedding) ** 0.5
        
        # 持久化策略: 每5条写一次磁盘
        if len(self.texts) % 5 == 0:
            self._save_to_disk()
            self._pending_save = False
        else:
            self._pending_save = True
        return doc_id
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """混合检索:向量相似度 + 关键词 + 时间权重"""
        cache_key = f"{query}:{top_k}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self.texts:
            return []
        query_embedding = self.get_embedding(query)
        norm_a = sum(x * x for x in query_embedding) ** 0.5
        
        results = []
        for doc_id, embedding in self.vectors.items():
            vector_score = self._cosine_similarity(query_embedding, norm_a, embedding)
            keyword_score = self._bm25_keyword_score(query, self.texts[doc_id])
            metadata = self.metadatas.get(doc_id, {})
            timestamp = metadata.get("timestamp", time.time())
            hours_old = (time.time() - timestamp) / 3600
            time_weight = RetentionScorer.compute_recency_decay(hours_old)
            
            weights = getattr(self, '_retrieval_weights', None) or {"vector": 0.5, "keyword": 0.3, "recency": 0.2}
            final_score = (weights.get("vector", 0.5) * vector_score +
                           weights.get("keyword", 0.3) * keyword_score +
                           weights.get("recency", 0.2) * time_weight)
            
            results.append({
                "id": doc_id,
                "vector_score": vector_score,
                "keyword_score": keyword_score,
                "time_weight": time_weight,
                "score": final_score,
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
        final_results = []
        for item in results[:top_k]:
            doc_id = item["id"]
            final_results.append({
                "id": doc_id,
                "text": self.texts[doc_id],
                "score": item["score"],
                "vector_score": item["vector_score"],
                "keyword_score": item["keyword_score"],
                "time_weight": item["time_weight"],
                "metadata": self.metadatas.get(doc_id, {}),
            })
        
        self._search_cache.put(cache_key, final_results)
        return final_results
    
    def delete(self, doc_id: str) -> bool:
        """删除指定向量"""
        if doc_id not in self.vectors:
            return False
        del self.vectors[doc_id]
        del self.texts[doc_id]
        del self.metadatas[doc_id]
        self._norms.pop(doc_id, None)
        self._pending_save = True
        return True
    
    def _bm25_keyword_score(self, query: str, text: str) -> float:
        if not query or not text:
            return 0.0
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.0
        matches = len(query_words & text_words)
        return matches / len(query_words)
    
    def _cosine_similarity(self, a: List[float], norm_a: float, b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def get_stats(self) -> Dict[str, Any]:
        return {"total_docs": len(self.texts), "embedding_dim": self.embedding_dim}
    
    def flush(self):
        if self._pending_save and self.texts:
            self._save_to_disk()
            self._pending_save = False
            print(f"[Memory] 向量存储已 flush ({len(self.texts)} 条)")
        elif self.texts:
            # 即使没有 pending 也要确保磁盘最新
            self._save_to_disk()
    
    def clear(self):
        self.flush()
        self.vectors.clear()
        self.texts.clear()
        self.metadatas.clear()
        self._norms.clear()
        self._embedding_cache = LRUCache(200)
        self._search_cache = LRUCache(50)
        if self._persist_file.exists():
            self._persist_file.unlink()


# ==================== 文件存储 ====================

class FileStorage:
    """文件系统存储"""
    
    def __init__(self, base_dir: str = "./memory"):
        if not os.path.isabs(base_dir):
            base_dir = str(Path(base_dir).resolve())
        self.base_dir = Path(base_dir)
        self.daily_dir = self.base_dir / "daily"
        self.long_term_file = self.base_dir / "long_term.md"
        self.index_file = self.base_dir / "index.md"
        self.config_file = self.base_dir / "config.json"
        
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.index_file.exists():
            self._init_index()
    
    def _init_index(self):
        content = """# 记忆系统入口

## 结构
- `daily/` - 每日对话记录
- `long_term.md` - 长期记忆
- `config.json` - 配置

## 功能
- 自动保存对话
- 重要性评分
- 搜索历史
"""
        self.index_file.write_text(content, encoding='utf-8')
    
    def get_daily_file(self, date: str = None) -> Path:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.daily_dir / f"{date}.md"
    
    def append_interaction(self, role: str, content: str, importance: int = 0, tags: List[str] = None):
        """追加对话记录到当日记忆文件"""
        daily_file = self.get_daily_file()
        timestamp = datetime.now().strftime("%H:%M")
        star = "⭐" * importance if importance > 0 else ""
        tag_str = f" [{','.join(tags)}]" if tags else ""
        line = f"- **{timestamp}** [{role}]{star}{tag_str}: {content}\n"
        with open(daily_file, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def read_daily(self, date: str = None) -> str:
        daily_file = self.get_daily_file(date)
        if not daily_file.exists():
            return ""
        return daily_file.read_text(encoding='utf-8')
    
    def list_daily_files(self) -> List[str]:
        if not self.daily_dir.exists():
            return []
        files = sorted(self.daily_dir.glob("*.md"), reverse=True)
        return [f.stem for f in files]
    
    def append_long_term(self, content: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"\n## {timestamp}\n\n{content}\n"
        with open(self.long_term_file, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def read_long_term(self) -> str:
        if not self.long_term_file.exists():
            return ""
        return self.long_term_file.read_text(encoding='utf-8')
    
    def search_in_files(self, query: str, days: int = 7) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_file = self.daily_dir / f"{date}.md"
            if not daily_file.exists():
                continue
            content = daily_file.read_text(encoding='utf-8')
            if query_lower in content.lower():
                lines = content.split('\n')
                matched = [l for l in lines if query_lower in l.lower()]
                if matched:
                    results.append({"date": date, "matches": matched[:5]})
        return results
    
    def export_all(self) -> str:
        output = f"# 记忆导出 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        long_term = self.read_long_term()
        if long_term:
            output += "## 长期记忆\n\n" + long_term + "\n\n"
        for date in self.list_daily_files()[:30]:
            content = self.read_daily(date)
            if content:
                output += f"## {date}\n\n" + content + "\n\n"
        return output
    
    def import_backup(self, content: str):
        self.append_long_term("\n[导入备份]\n" + content)
    
    def clear(self):
        if self.daily_dir.exists():
            for f in self.daily_dir.glob("*.md"):
                f.unlink()
        if self.long_term_file.exists():
            self.long_term_file.unlink()


# ==================== 摘要生成器 ====================

class SummaryGenerator:
    """
    摘要生成器 v2 — LLM 语义摘要 + 规则降级
    
    v3.0: 不再硬截断前80字, 而是真正理解对话内容生成摘要
    """
    
    @classmethod
    def generate_summary(cls, batch: List[MemoryItem], llm_chat_func=None) -> str:
        """
        为一批记忆生成摘要
        
        优先使用 LLM 生成语义摘要, 降级到规则摘要
        """
        if not batch:
            return ""
        
        # 构建对话文本
        conversation = "\n".join([
            f"[{item.role}](imp={item.importance}): {item.content}"
            for item in batch
        ])
        
        # ===== 优先: LLM 摘要 =====
        if llm_chat_func:
            try:
                summary = cls._llm_summarize(conversation, llm_chat_func)
                if summary:
                    return summary
            except Exception as e:
                print(f" [记忆] LLM摘要失败,降级到规则摘要: {e}")
        
        # ===== 降级: 规则摘要 =====
        return cls._rule_summarize(batch)
    
    @classmethod
    def _llm_summarize(cls, conversation: str, llm_chat_func) -> Optional[str]:
        """LLM 语义摘要"""
        prompt = f"""请将以下对话压缩为一段简洁的摘要。要求:
1. 保留所有重要信息(用户偏好、个人信息、关键决策)
2. 丢弃闲聊和问候
3. 用第三人称客观描述
4. 100字以内

对话内容:
{conversation[:2000]}

摘要:"""
        
        result = llm_chat_func(message=prompt)
        text = result.get("text", "").strip()
        if text and len(text) > 5:
            return text
        return None
    
    @classmethod
    def _rule_summarize(cls, batch: List[MemoryItem]) -> str:
        """规则摘要(降级方案) — v3.0改进: 按重要性分层处理"""
        important_parts = []
        normal_parts = []
        
        for item in batch:
            if item.importance >= 3:
                # 重要内容: 保留更多(前150字)
                important_parts.append(f"[{item.role}]: {item.content[:150]}")
            elif item.importance >= 1:
                # 一般内容: 保留前80字
                normal_parts.append(f"[{item.role}]: {item.content[:80]}")
            # importance=0 的闲聊直接丢弃
        
        if important_parts:
            return "[重要对话] " + " | ".join(important_parts)
        elif normal_parts:
            return "[对话摘要] " + " | ".join(normal_parts[:5])
        else:
            return "[闲聊记录] (已压缩)"


# ==================== 主记忆系统 ====================

class MemorySystem:
    """
    记忆系统 v3.0 — 全面重构
    
    改进点:
    - 多维梯度评分 (不再只有0/4/5)
    - LLM 语义摘要 (替代硬截断)
    - 事实提取 (独立保存用户偏好/信息)
    - 向量库去重 + 降低入库阈值
    - 遗忘衰减调优 (更慢衰减 + 保护期)
    - 自动标签
    - 记忆重整 (跨层整合)
    - 记忆管理 (删除/编辑/标重要)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化记忆系统"""
        self.config = config or {}
        # 存储目录（立即解析为绝对路径，防止 os.chdir() 导致路径漂移）
        self.storage_dir = self.config.get("storage_dir", "./memory")
        if not os.path.isabs(self.storage_dir):
            self.storage_dir = str(Path(self.storage_dir).resolve())
        
        # 从配置读取参数
        self.working_memory_limit = self.config.get("working_memory_limit", 30)  # v3.0: 20→30
        self.summarize_threshold = self.config.get("summarize_threshold", 20)    # v3.0: 15→20
        self.summarize_batch = self.config.get("summarize_batch", 5)
        
        # LLM 回调 (由外部通过 set_llm_callback 设置)
        self._llm_chat_func = None
        
        # 遗忘机制参数
        RetentionScorer.DECAY_LAMBDA = self.config.get("decay_lambda", 0.005)  # v3.0: 0.01→0.005
        RetentionScorer.RETENTION_THRESHOLD = self.config.get("forgetting_threshold", 0.15)  # v3.0: 0.3→0.15
        RetentionScorer.GRACE_PERIOD_HOURS = self.config.get("grace_period_hours", 12.0)
        
        # 向量存储
        vs_config = dict(self.config)
        vs_config["storage_dir"] = os.path.join(self.storage_dir, "vectors")
        vs_config["dedup_threshold"] = self.config.get("dedup_threshold", 0.95)
        self.vector_store = VectorStore(vs_config)
        
        # 文件存储
        self.file_storage = FileStorage(self.storage_dir)
        
        # ===== 四层记忆 =====
        self.working_memory: List[MemoryItem] = []
        self.episodic_memory: List[MemoryItem] = []
        
        # ===== v3.0: 事实库 =====
        self.facts: List[FactItem] = []
        
        # 过期记忆计数
        self.forgotten_count = 0
        
        # 自动存储
        self.auto_store = self.config.get("auto_store", True)
        
        # ===== 持久化文件路径 =====
        self._persist_dir = Path(self.storage_dir) / "state"
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._working_memory_file = self._persist_dir / "working_memory.json"
        self._episodic_memory_file = self._persist_dir / "episodic_memory.json"
        self._forgotten_count_file = self._persist_dir / "forgotten_count.json"
        self._facts_file = self._persist_dir / "facts.json"
        
        # ===== 从磁盘恢复 =====
        self._load_memory_state()
        
        print(f" 记忆系统 v3.0 初始化完成")
        print(f" 存储目录: {self.storage_dir}")
        print(f" 工作记忆: {len(self.working_memory)}条, 情景记忆: {len(self.episodic_memory)}条, "
              f"语义记忆: {self.vector_store.get_stats()['total_docs']}条, 事实: {len(self.facts)}条")
        print(f" 工作记忆上限: {self.working_memory_limit}, 摘要阈值: {self.summarize_threshold}, "
              f"遗忘阈值: {RetentionScorer.RETENTION_THRESHOLD}")
        
        # 定时flush
        self._flush_timer = None
        self._start_flush_timer()
    
    # ==================== LLM 回调 ====================
    
    def set_llm_callback(self, chat_func):
        """
        设置 LLM 回调函数, 用于摘要生成和事实提取
        
        chat_func: callable(message: str) -> {"text": str, "action": ...}
        """
        self._llm_chat_func = chat_func
        print(f" [记忆系统] LLM 回调已设置")
    
    # ==================== 定时持久化 ====================
    
    def _start_flush_timer(self):
        import threading
        def _flush_worker():
            try:
                self._save_memory_state()
            except Exception:
                pass
            finally:
                if self._flush_timer is not None:
                    self._flush_timer = threading.Timer(30.0, _flush_worker)
                    self._flush_timer.daemon = True
                    self._flush_timer.start()
        
        self._flush_timer = threading.Timer(30.0, _flush_worker)
        self._flush_timer.daemon = True
        self._flush_timer.start()
    
    # ==================== 持久化方法 ====================
    
    def _load_memory_state(self):
        """从磁盘恢复"""
        # 恢复工作记忆
        if self._working_memory_file.exists():
            try:
                with open(self._working_memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.working_memory = [self._dict_to_memory_item(item) for item in data]
                print(f" [记忆] 恢复工作记忆: {len(self.working_memory)}条")
            except Exception as e:
                print(f" [记忆] 恢复工作记忆失败: {e}")
        
        # 恢复情景记忆
        if self._episodic_memory_file.exists():
            try:
                with open(self._episodic_memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.episodic_memory = [self._dict_to_memory_item(item) for item in data]
                print(f" [记忆] 恢复情景记忆: {len(self.episodic_memory)}条")
            except Exception as e:
                print(f" [记忆] 恢复情景记忆失败: {e}")
        
        # 恢复遗忘计数
        if self._forgotten_count_file.exists():
            try:
                with open(self._forgotten_count_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.forgotten_count = data.get("count", 0)
            except Exception:
                pass
        
        # v3.0: 恢复事实库
        if self._facts_file.exists():
            try:
                with open(self._facts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.facts = [self._dict_to_fact_item(item) for item in data]
                print(f" [记忆] 恢复事实库: {len(self.facts)}条")
            except Exception as e:
                print(f" [记忆] 恢复事实库失败: {e}")
    
    @staticmethod
    def _dict_to_memory_item(d: Dict[str, Any]) -> MemoryItem:
        """将字典转为 MemoryItem，兼容旧版本缺失字段"""
        return MemoryItem(
            role=d.get("role", "unknown"),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", time.time()),
            importance=d.get("importance", 0),
            tags=d.get("tags", []),
            access_count=d.get("access_count", 1),
            connectivity=d.get("connectivity", 0),
            is_forgotten=d.get("is_forgotten", False),
            is_summary=d.get("is_summary", False),
            facts=d.get("facts", []),
            summary_text=d.get("summary_text", ""),
        )
    
    @staticmethod
    def _dict_to_fact_item(d: Dict[str, Any]) -> FactItem:
        """将字典转为 FactItem"""
        return FactItem(
            content=d.get("content", ""),
            source=d.get("source", "key_fact"),
            confidence=d.get("confidence", 0.5),
            timestamp=d.get("timestamp", time.time()),
            access_count=d.get("access_count", 1),
            tags=d.get("tags", []),
        )
    
    def _save_memory_state(self):
        """保存到磁盘（原子写入）"""
        try:
            self._atomic_write_json(
                self._working_memory_file,
                [asdict(item) for item in self.working_memory]
            )
            self._atomic_write_json(
                self._episodic_memory_file,
                [asdict(item) for item in self.episodic_memory]
            )
            self._atomic_write_json(
                self._forgotten_count_file,
                {"count": self.forgotten_count}
            )
            # v3.0: 保存事实库
            self._atomic_write_json(
                self._facts_file,
                [asdict(item) for item in self.facts]
            )
        except Exception as e:
            print(f" [记忆] 保存状态失败: {e}")
    
    def _atomic_write_json(self, target_path: Path, data: Any):
        tmp_path = target_path.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, target_path)
    
    def flush(self):
        """强制将所有未持久化的记忆数据写入磁盘"""
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None
        self._save_memory_state()
        self.vector_store.flush()
        print(f"[Memory] 全部记忆已 flush (工作:{len(self.working_memory)} 情景:{len(self.episodic_memory)} "
              f"语义:{self.vector_store.get_stats()['total_docs']} 事实:{len(self.facts)})")
    
    # ==================== 核心方法 ====================
    
    def add_interaction(self, role: str, content: str, importance: int = None):
        """
        添加对话记录
        
        流程:
        1. 多维梯度评分 → 创建 MemoryItem
        2. 自动标签
        3. 事实提取
        4. 加入工作记忆
        5. 超过阈值时触发 LLM/规则 摘要压缩
        6. 重要记忆存入向量库(降低阈值到>=3)
        7. 遗忘扫描(跳过保护期内的新记忆)
        8. 文件持久化
        """
        # 1. 多维梯度评分
        if importance is None:
            importance = ImportanceScorer.score(role, content)
        
        # 2. 自动标签
        tags = AutoTagger.tag(content)
        
        # 3. 事实提取(仅用户消息)
        extracted_facts = []
        if role == "user":
            extracted_facts = FactExtractor.extract_facts(role, content, importance)
            # v3.0: 如果规则提取为空且内容较长, 尝试LLM提取
            if not extracted_facts and len(content) > 50 and importance >= 2 and self._llm_chat_func:
                extracted_facts = FactExtractor.extract_with_llm(content, self._llm_chat_func)
            
            # 去重合并事实
            for fact in extracted_facts:
                self._merge_fact(fact)
        
        # 创建记忆条目
        item = MemoryItem(
            role=role,
            content=content,
            timestamp=time.time(),
            importance=importance,
            tags=tags,
            facts=[f.content for f in extracted_facts],
        )
        
        # 4. 加入工作记忆
        self.working_memory.append(item)
        
        # 5. 滑动窗口 + LLM/规则 摘要压缩
        if len(self.working_memory) > self.summarize_threshold:
            self._compress_early_memory()
        
        # 6. 重要记忆存入向量库 (v3.0: 阈值从>=4降到>=3)
        if ImportanceScorer.is_important(importance):  # >=3
            doc_id = self.vector_store.add(
                f"{role}: {content}",
                {
                    "timestamp": item.timestamp,
                    "importance": importance,
                    "role": role,
                    "is_summary": False,
                    "tags": tags,
                }
            )
            # 关键记忆同步写入 long_term.md
            if ImportanceScorer.is_critical(importance):  # >=4
                self.file_storage.append_long_term(
                    f"[{role}] 重要性:{importance} {tags} - {content}"
                )
        
        # 7. 遗忘扫描(v3.0: 跳过保护期内的新记忆)
        self._forgetting_sweep()
        
        # 8. 文件持久化
        if self.auto_store:
            self.file_storage.append_interaction(role, content, importance, tags)
        
        # 状态持久化(每5条保存一次)
        if len(self.working_memory) % 5 == 0:
            self._save_memory_state()
    
    def _compress_early_memory(self):
        """
        摘要压缩 v2 — LLM 语义摘要 + 规则降级
        
        不再硬截断前80字, 而是真正理解对话内容生成摘要
        """
        if len(self.working_memory) <= self.summarize_threshold:
            return
        
        batch = self.working_memory[:self.summarize_batch]
        self.working_memory = self.working_memory[self.summarize_batch:]
        
        # v3.0: 使用 SummaryGenerator 生成摘要
        summary_text = SummaryGenerator.generate_summary(batch, self._llm_chat_func)
        
        # 合并提取的事实
        all_facts = []
        for item in batch:
            all_facts.extend(item.facts)
            if item.facts:
                # facts可能在规则提取时已经保存到 self.facts, 这里跳过
                pass
        
        # 创建摘要记忆条目
        summary_item = MemoryItem(
            role="system",
            content=summary_text,
            timestamp=batch[-1].timestamp,
            importance=max(item.importance for item in batch),
            is_summary=True,
            summary_text=summary_text,
            facts=list(set(all_facts)),  # 去重
            tags=AutoTagger.tag(summary_text),
        )
        
        # 加入情景记忆
        self.episodic_memory.append(summary_item)
        
        # 重要摘要存入向量库
        if summary_item.importance >= 3:
            self.vector_store.add(
                f"[摘要] {summary_text}",
                {
                    "timestamp": summary_item.timestamp,
                    "importance": summary_item.importance,
                    "is_summary": True,
                    "role": "system",
                    "tags": summary_item.tags,
                }
            )
        
        print(f" 记忆压缩: {len(batch)}条 → 1条摘要 (剩余工作记忆: {len(self.working_memory)})")
        
        # 压缩后立即持久化
        self._save_memory_state()
    
    def _forgetting_sweep(self):
        """
        遗忘扫描 v2 — 跳过保护期内的新记忆
        """
        forgotten = 0
        now = time.time()
        
        survivors = []
        for item in self.episodic_memory:
            hours_old = (now - item.timestamp) / 3600
            
            # v3.0: 新记忆保护期, 不参与遗忘
            if RetentionScorer.is_in_grace_period(hours_old):
                survivors.append(item)
                continue
            
            if item.should_forget():
                forgotten += 1
            else:
                survivors.append(item)
        self.episodic_memory = survivors
        
        if forgotten > 0:
            self.forgotten_count += forgotten
            print(f" 遗忘扫描: 清理了 {forgotten} 条过期情景记忆 (累计: {self.forgotten_count})")
        return forgotten
    
    def _merge_fact(self, new_fact: FactItem):
        """
        合并事实(去重 + 更新)
        
        如果新事实与已有事实相似, 合并为置信度更高的版本
        """
        # 简单去重: 内容相似度过高则更新而非新增
        for existing in self.facts:
            # 简单字符串相似度
            if self._text_similarity(existing.content, new_fact.content) > 0.7:
                # 合并: 更新置信度取高值, 更新时间
                existing.confidence = max(existing.confidence, new_fact.confidence)
                existing.timestamp = new_fact.timestamp
                existing.access_count += 1
                # 合并标签
                for tag in new_fact.tags:
                    if tag not in existing.tags:
                        existing.tags.append(tag)
                return
        
        # 新事实
        self.facts.append(new_fact)
    
    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """简单文本相似度(字符级 Jaccard)"""
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
    
    # ==================== 检索 ====================
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        混合检索 v2: 工作记忆 + 情景记忆 + 向量库 + 事实库
        
        v3.0: 增加事实库检索, top_k 默认5
        """
        results = []
        query_lower = query.lower()
        
        # 1. 工作记忆搜索(最优先)
        for i, item in enumerate(self.working_memory):
            if query_lower in item.content.lower():
                item.touch()
                results.append({
                    "layer": "working",
                    "index": i,
                    "text": item.content,
                    "role": item.role,
                    "importance": item.importance,
                    "score": 1.0,
                    "is_summary": item.is_summary,
                    "tags": item.tags,
                })
        
        # 2. 事实库搜索
        for i, fact in enumerate(self.facts):
            if query_lower in fact.content.lower():
                fact.access_count += 1
                results.append({
                    "layer": "fact",
                    "index": i,
                    "text": fact.content,
                    "role": "fact",
                    "importance": 4,  # 事实默认高分
                    "score": 0.9,
                    "source": fact.source,
                    "tags": fact.tags,
                })
        
        # 3. 情景记忆搜索
        for i, item in enumerate(self.episodic_memory):
            if item.is_forgotten:
                continue
            if query_lower in item.content.lower():
                item.touch()
                retention = item.get_retention_score()
                results.append({
                    "layer": "episodic",
                    "index": i,
                    "text": item.content,
                    "role": item.role,
                    "importance": item.importance,
                    "retention_score": retention,
                    "score": 0.7 * retention,
                    "is_summary": item.is_summary,
                    "tags": item.tags,
                })
        
        # 4. 向量库混合检索
        vector_results = self.vector_store.search(query, top_k)
        for vr in vector_results:
            results.append({
                "layer": "semantic",
                "text": vr["text"],
                "score": vr["score"] * 0.8,  # 向量库结果略微降权
                "vector_score": vr.get("vector_score", 0),
                "keyword_score": vr.get("keyword_score", 0),
                "time_weight": vr.get("time_weight", 0),
                "is_summary": vr["metadata"].get("is_summary", False),
                "tags": vr["metadata"].get("tags", []),
            })
        
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]
    
    # ==================== 记忆管理 ====================
    
    def delete_memory(self, index: int, layer: str = "working") -> bool:
        """删除指定记忆"""
        try:
            if layer == "working" and 0 <= index < len(self.working_memory):
                self.working_memory.pop(index)
                self._save_memory_state()
                return True
            elif layer == "episodic" and 0 <= index < len(self.episodic_memory):
                self.episodic_memory.pop(index)
                self._save_memory_state()
                return True
            elif layer == "fact" and 0 <= index < len(self.facts):
                self.facts.pop(index)
                self._save_memory_state()
                return True
        except Exception as e:
            print(f" [记忆] 删除失败: {e}")
        return False
    
    def edit_memory(self, index: int, content: str, layer: str = "working") -> bool:
        """编辑指定记忆内容"""
        try:
            if layer == "working" and 0 <= index < len(self.working_memory):
                self.working_memory[index].content = content
                self.working_memory[index].tags = AutoTagger.tag(content)
                self._save_memory_state()
                return True
            elif layer == "episodic" and 0 <= index < len(self.episodic_memory):
                self.episodic_memory[index].content = content
                self.episodic_memory[index].tags = AutoTagger.tag(content)
                self._save_memory_state()
                return True
        except Exception as e:
            print(f" [记忆] 编辑失败: {e}")
        return False
    
    def set_importance(self, index: int, importance: int, layer: str = "working") -> bool:
        """手动设置重要性"""
        try:
            if layer == "working" and 0 <= index < len(self.working_memory):
                self.working_memory[index].importance = importance
                if ImportanceScorer.is_important(importance):  # >=3
                    item = self.working_memory[index]
                    self.vector_store.add(
                        f"{item.role}: {item.content}",
                        {"timestamp": item.timestamp, "importance": importance, "role": item.role}
                    )
                self._save_memory_state()
                return True
            elif layer == "episodic" and 0 <= index < len(self.episodic_memory):
                self.episodic_memory[index].importance = importance
                self._save_memory_state()
                return True
        except Exception as e:
            print(f" [记忆] 设置重要性失败: {e}")
        return False
    
    def delete_fact(self, index: int) -> bool:
        """删除指定事实"""
        if 0 <= index < len(self.facts):
            self.facts.pop(index)
            self._save_memory_state()
            return True
        return False
    
    # ==================== 记忆重整 ====================
    
    def consolidate(self) -> Dict[str, Any]:
        """
        记忆重整 — 跨层整合优化
        
        1. 合并情景记忆中的重复摘要
        2. 将高保留分数的情景记忆提升到长期存储
        3. 清理低价值的已遗忘记忆
        """
        merged_count = 0
        promoted_count = 0
        
        # 1. 合并重复情景记忆
        i = 0
        while i < len(self.episodic_memory) - 1:
            item_a = self.episodic_memory[i]
            j = i + 1
            while j < len(self.episodic_memory):
                item_b = self.episodic_memory[j]
                # 如果两条情景记忆相似度很高且都是摘要
                if (item_a.is_summary and item_b.is_summary and
                    self._text_similarity(item_a.content, item_b.content) > 0.6):
                    # 合并: 保留重要性更高的一条, 扩展内容
                    if item_a.importance >= item_b.importance:
                        item_a.importance = max(item_a.importance, item_b.importance)
                        item_a.connectivity += item_b.connectivity + 1
                        self.episodic_memory.pop(j)
                        merged_count += 1
                    else:
                        item_b.importance = max(item_a.importance, item_b.importance)
                        item_b.connectivity += item_a.connectivity + 1
                        self.episodic_memory.pop(i)
                        merged_count += 1
                        break  # i 被删除了, 重新开始
                else:
                    j += 1
            i += 1
        
        # 2. 高保留分数的情景记忆提升到长期存储
        for item in self.episodic_memory:
            if item.importance >= 4 and not item.is_forgotten:
                retention = item.get_retention_score()
                if retention > 0.5:
                    # 写入长期记忆文件
                    self.file_storage.append_long_term(
                        f"[情景提升] {item.content[:200]}"
                    )
                    promoted_count += 1
        
        # 3. 清理已遗忘记忆
        before = len(self.episodic_memory)
        self.episodic_memory = [m for m in self.episodic_memory if not m.is_forgotten]
        cleaned = before - len(self.episodic_memory)
        
        # 保存
        self._save_memory_state()
        self.vector_store.flush()
        
        result = {
            "merged": merged_count,
            "promoted": promoted_count,
            "cleaned": cleaned,
            "working": len(self.working_memory),
            "episodic": len(self.episodic_memory),
            "semantic": self.vector_store.get_stats()["total_docs"],
            "facts": len(self.facts),
        }
        print(f" [记忆重整] 合并:{merged_count} 提升:{promoted_count} 清理:{cleaned}")
        return result
    
    # ==================== 预加载 ====================
    
    def prefetch(self, context: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        预加载相关记忆 — 在对话开始前调用
        
        基于当前上下文预加载相关记忆, 注入到 prompt 中
        """
        return self.search(context, top_k)
    
    # ==================== 查询方法 ====================
    
    def get_working_memory(self) -> List[Dict[str, Any]]:
        return [asdict(item) for item in self.working_memory]
    
    def get_episodic_memory(self) -> List[Dict[str, Any]]:
        return [asdict(item) for item in self.episodic_memory]
    
    def get_facts(self, source: str = None) -> List[Dict[str, Any]]:
        """获取事实列表, 可按来源过滤"""
        if source:
            return [asdict(f) for f in self.facts if f.source == source]
        return [asdict(f) for f in self.facts]
    
    def search_by_time(self, days: int = 7) -> List[Dict[str, Any]]:
        return self.file_storage.search_in_files("", days)
    
    def search_by_role(self, role: str) -> List[Dict[str, Any]]:
        results = []
        for item in self.working_memory:
            if item.role == role:
                results.append(asdict(item))
        return results
    
    def summarize(self) -> str:
        """生成对话摘要"""
        if not self.working_memory:
            return ""
        
        recent = self.working_memory[-10:]
        summary = "[对话摘要]\n"
        for item in recent:
            content = item.content[:60] + "..." if len(item.content) > 60 else item.content
            star = "⭐" * item.importance if item.importance else ""
            tag = "[摘要]" if item.is_summary else ""
            tags_str = f" [{','.join(item.tags)}]" if item.tags else ""
            summary += f"- {tag}[{item.role}]{star}{tags_str}: {content}\n"
        
        if self.episodic_memory:
            summary += "\n[情景记忆摘要]\n"
            for item in self.episodic_memory[-5:]:
                if item.is_summary:
                    summary += f"- {item.content[:80]}\n"
        
        if self.facts:
            summary += "\n[已知事实]\n"
            for fact in self.facts[-10:]:
                summary += f"- [{fact.source}] {fact.content}\n"
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        retention_scores = [m.get_retention_score() for m in self.episodic_memory]
        avg_retention = sum(retention_scores) / len(retention_scores) if retention_scores else 0
        
        # 重要性分布
        importance_dist = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for m in self.working_memory:
            if m.importance in importance_dist:
                importance_dist[m.importance] += 1
        
        return {
            "working_memory": len(self.working_memory),
            "episodic_memory": len(self.episodic_memory),
            "semantic_memory": self.vector_store.get_stats()["total_docs"],
            "forgotten_count": self.forgotten_count,
            "avg_retention_score": round(avg_retention, 3),
            "facts_count": len(self.facts),
            "importance_distribution": importance_dist,
            "storage_dir": self.storage_dir,
            "version": "v3.0",
            "persistent": True,
        }
    
    def export(self) -> str:
        return self.file_storage.export_all()
    
    def import_backup(self, content: str):
        return self.file_storage.import_backup(content)
    
    def clear_all(self):
        self.working_memory.clear()
        self.episodic_memory.clear()
        self.facts.clear()
        self.vector_store.flush()
        self.vector_store.clear()
        self.file_storage.clear()
        self.forgotten_count = 0
        for f in [self._working_memory_file, self._episodic_memory_file, 
                  self._forgotten_count_file, self._facts_file]:
            if f.exists():
                f.unlink()
        print(" 所有记忆已清空")
    
    def get_decay_preview(self) -> Dict[str, Any]:
        return {
            "now": RetentionScorer.get_decay_stats(0),
            "1day": RetentionScorer.get_decay_stats(24),
            "7days": RetentionScorer.get_decay_stats(24 * 7),
            "30days": RetentionScorer.get_decay_stats(24 * 30),
            "grace_period_hours": RetentionScorer.GRACE_PERIOD_HOURS,
        }


# 示例
if __name__ == "__main__":
    config = {"storage_dir": "./memory/test"}
    memory = MemorySystem(config)
    
    print("=== 记忆系统 v3.0 测试 ===\n")
    
    # 测试多维梯度评分
    test_cases = [
        ("user", "你好"),                           # 闲聊 → 0
        ("user", "今天天气怎么样"),                    # 问题 → 1-2
        ("user", "我喜欢简洁的回复风格"),               # 偏好 → 3
        ("user", "我叫小明，来自北京"),                # 个人信息 → 4
        ("user", "记住我下周三有个会议"),               # 记忆指令 → 5
        ("user", "矩阵是高维空间到低维空间的线性映射"),   # 知识深度 → 2-3
        ("assistant", "好的，我了解了你的偏好"),        # 一般回复 → 1
    ]
    
    for role, content in test_cases:
        score = ImportanceScorer.score(role, content)
        tags = AutoTagger.tag(content)
        print(f"  [{role}] \"{content}\" → 评分:{score} 标签:{tags}")
    
    # 测试事实提取
    print("\n事实提取测试:")
    for role, content in test_cases:
        facts = FactExtractor.extract_facts(role, content, ImportanceScorer.score(role, content))
        for fact in facts:
            print(f"  [{fact.source}] {fact.content} (置信度:{fact.confidence})")
    
    print(f"\n统计: {memory.get_stats()}")
