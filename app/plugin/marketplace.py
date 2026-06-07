"""
插件市场模块
支持插件发布、搜索、评分、下载
"""

import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class PluginCategory(Enum):
    """插件类别"""
    TOOL = "tool"           # 工具插件
    TTS = "tts"             # TTS插件
    ASR = "asr"             # ASR插件
    LLM = "llm"             # LLM插件
    VISION = "vision"       # 视觉插件
    GAME = "game"           # 游戏插件
    LIVE = "live"           # 直播插件
    THEME = "theme"         # 主题插件
    OTHER = "other"         # 其他

@dataclass
class PluginReview:
    """插件评论"""
    user_id: str
    username: str
    rating: int  # 1-5
    comment: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PluginEntry:
    """插件条目"""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    category: PluginCategory
    download_url: str
    icon_url: str = ""
    homepage: str = ""
    repository: str = ""
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # 统计信息
    downloads: int = 0
    rating: float = 0.0
    reviews: List[PluginReview] = field(default_factory=list)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class PluginMarketplace:
    """插件市场"""
    
    def __init__(self, storage_dir: str = "./plugins/marketplace") -> None:
        self.storage_dir = Path(storage_dir)
        self.index_file = self.storage_dir / "index.json"
        self.reviews_dir = self.storage_dir / "reviews"
        
        # 插件索引
        self.plugins: Dict[str, PluginEntry] = {}
        
        # 加载索引
        self._load_index()
        
        logger.info("[PluginMarketplace] 初始化完成")
    
    def _load_index(self) -> None:
        """加载插件索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for plugin_id, plugin_data in data.items():
                        self.plugins[plugin_id] = PluginEntry(
                            plugin_id=plugin_data["plugin_id"],
                            name=plugin_data["name"],
                            version=plugin_data["version"],
                            description=plugin_data["description"],
                            author=plugin_data["author"],
                            category=PluginCategory(plugin_data["category"]),
                            download_url=plugin_data["download_url"],
                            icon_url=plugin_data.get("icon_url", ""),
                            homepage=plugin_data.get("homepage", ""),
                            repository=plugin_data.get("repository", ""),
                            license=plugin_data.get("license", "MIT"),
                            tags=plugin_data.get("tags", []),
                            dependencies=plugin_data.get("dependencies", []),
                            downloads=plugin_data.get("downloads", 0),
                            rating=plugin_data.get("rating", 0.0),
                            created_at=datetime.fromisoformat(plugin_data.get("created_at", datetime.now().isoformat())),
                            updated_at=datetime.fromisoformat(plugin_data.get("updated_at", datetime.now().isoformat()))
                        )
                logger.info(f"[PluginMarketplace] 加载了 {len(self.plugins)} 个插件")
        except Exception as e:
            logger.info(f"[PluginMarketplace] 加载索引失败: {e}")
    
    def _save_index(self) -> None:
        """保存插件索引"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for plugin_id, plugin in self.plugins.items():
                data[plugin_id] = {
                    "plugin_id": plugin.plugin_id,
                    "name": plugin.name,
                    "version": plugin.version,
                    "description": plugin.description,
                    "author": plugin.author,
                    "category": plugin.category.value,
                    "download_url": plugin.download_url,
                    "icon_url": plugin.icon_url,
                    "homepage": plugin.homepage,
                    "repository": plugin.repository,
                    "license": plugin.license,
                    "tags": plugin.tags,
                    "dependencies": plugin.dependencies,
                    "downloads": plugin.downloads,
                    "rating": plugin.rating,
                    "created_at": plugin.created_at.isoformat(),
                    "updated_at": plugin.updated_at.isoformat()
                }
            
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.info(f"[PluginMarketplace] 保存索引失败: {e}")
    
    def publish_plugin(self, plugin: PluginEntry) -> bool:
        """发布插件"""
        try:
            # 检查是否已存在
            if plugin.plugin_id in self.plugins:
                # 更新版本
                old_plugin = self.plugins[plugin.plugin_id]
                plugin.downloads = old_plugin.downloads
                plugin.reviews = old_plugin.reviews
                plugin.created_at = old_plugin.created_at
            
            # 更新时间戳
            plugin.updated_at = datetime.now()
            
            # 保存
            self.plugins[plugin.plugin_id] = plugin
            self._save_index()
            
            logger.info(f"[PluginMarketplace] 插件已发布: {plugin.name} v{plugin.version}")
            return True
            
        except Exception as e:
            logger.info(f"[PluginMarketplace] 发布失败: {e}")
            return False
    
    def search_plugins(self, query: str = None, category: PluginCategory = None,
                      tags: List[str] = None, min_rating: float = 0.0,
                      sort_by: str = "downloads") -> List[PluginEntry]:
        """搜索插件"""
        results = []
        
        for plugin in self.plugins.values():
            # 类别过滤
            if category and plugin.category != category:
                continue
            
            # 评分过滤
            if plugin.rating < min_rating:
                continue
            
            # 标签过滤
            if tags and not any(tag in plugin.tags for tag in tags):
                continue
            
            # 关键词搜索
            if query:
                query_lower = query.lower()
                if (query_lower not in plugin.name.lower() and
                    query_lower not in plugin.description.lower() and
                    query_lower not in plugin.author.lower()):
                    continue
            
            results.append(plugin)
        
        # 排序
        if sort_by == "downloads":
            results.sort(key=lambda p: p.downloads, reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda p: p.rating, reverse=True)
        elif sort_by == "updated":
            results.sort(key=lambda p: p.updated_at, reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda p: p.name)
        
        return results
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginEntry]:
        """获取插件详情"""
        return self.plugins.get(plugin_id)
    
    def add_review(self, plugin_id: str, user_id: str, username: str,
                  rating: int, comment: str) -> bool:
        """添加评论"""
        if plugin_id not in self.plugins:
            return False
        
        try:
            plugin = self.plugins[plugin_id]
            
            # 创建评论
            review = PluginReview(
                user_id=user_id,
                username=username,
                rating=rating,
                comment=comment
            )
            
            # 添加到评论列表
            plugin.reviews.append(review)
            
            # 更新平均评分
            total_rating = sum(r.rating for r in plugin.reviews)
            plugin.rating = total_rating / len(plugin.reviews)
            
            # 保存
            self._save_index()
            
            logger.info(f"[PluginMarketplace] 评论已添加: {plugin.name}")
            return True
            
        except Exception as e:
            logger.info(f"[PluginMarketplace] 添加评论失败: {e}")
            return False
    
    def record_download(self, plugin_id: str) -> bool:
        """记录下载"""
        if plugin_id not in self.plugins:
            return False
        
        try:
            self.plugins[plugin_id].downloads += 1
            self._save_index()
            return True
        except Exception as e:
            return False
    
    def get_categories(self) -> Dict[str, int]:
        """获取类别统计"""
        categories = {}
        for plugin in self.plugins.values():
            category = plugin.category.value
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def get_top_plugins(self, count: int = 10, sort_by: str = "downloads") -> List[PluginEntry]:
        """获取热门插件"""
        return self.search_plugins(sort_by=sort_by)[:count]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_downloads = sum(p.downloads for p in self.plugins.values())
        avg_rating = sum(p.rating for p in self.plugins.values()) / max(1, len(self.plugins))
        
        return {
            "total_plugins": len(self.plugins),
            "total_downloads": total_downloads,
            "average_rating": avg_rating,
            "categories": self.get_categories()
        }

# 全局实例
_marketplace: Optional[PluginMarketplace] = None

def get_plugin_marketplace(storage_dir: str = None) -> PluginMarketplace:
    """获取插件市场实例"""
    global _marketplace
    if _marketplace is None:
        _marketplace = PluginMarketplace(storage_dir or "./plugins/marketplace")
    return _marketplace
