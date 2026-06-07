"""
增强版插件市场模块
支持插件发布、搜索、评分、下载、版本管理
"""

import asyncio
import json
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

class PluginCategory(Enum):
    """插件类别"""
    VOICE = "voice"          # 语音相关
    VISION = "vision"        # 视觉相关
    GAME = "game"            # 游戏相关
    LIVE = "live"            # 直播相关
    SOCIAL = "social"        # 社交相关
    UTILITY = "utility"      # 工具类
    THEME = "theme"          # 主题类
    LANGUAGE = "language"    # 语言包
    AI = "ai"                # AI模型
    OTHER = "other"          # 其他

class PluginStatus(Enum):
    """插件状态"""
    DRAFT = "draft"              # 草稿
    PENDING = "pending"          # 待审核
    APPROVED = "approved"        # 已审核
    REJECTED = "rejected"        # 已拒绝
    DEPRECATED = "deprecated"    # 已弃用

@dataclass
class PluginVersion:
    """插件版本"""
    version: str
    release_date: datetime
    changelog: str
    download_url: str
    file_size: int = 0
    checksum: str = ""

@dataclass
class PluginReview:
    """插件评论"""
    user_id: str
    username: str
    rating: int  # 1-5
    comment: str
    timestamp: datetime = field(default_factory=datetime.now)
    helpful_count: int = 0

@dataclass
class PluginEntry:
    """插件条目"""
    plugin_id: str
    name: str
    description: str
    author: str
    category: PluginCategory
    status: PluginStatus = PluginStatus.DRAFT
    
    # 版本信息
    current_version: str = "1.0.0"
    versions: List[PluginVersion] = field(default_factory=list)
    
    # 元数据
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

class EnhancedPluginMarketplace:
    """增强版插件市场"""
    
    def __init__(self, storage_dir: str = "./plugins/marketplace"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 插件索引
        self.index_file = self.storage_dir / "index.json"
        self.plugins: Dict[str, PluginEntry] = {}
        
        # 下载统计
        self.download_stats: Dict[str, int] = {}
        
        # 加载索引
        self._load_index()
        
        print(f"[EnhancedMarketplace] 初始化完成，插件数量: {len(self.plugins)}")
    
    def _load_index(self):
        """加载插件索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    for plugin_id, plugin_data in data.items():
                        # 简化加载，实际应该完整反序列化
                        self.plugins[plugin_id] = PluginEntry(
                            plugin_id=plugin_id,
                            name=plugin_data.get("name", ""),
                            description=plugin_data.get("description", ""),
                            author=plugin_data.get("author", ""),
                            category=PluginCategory(plugin_data.get("category", "other")),
                            status=PluginStatus(plugin_data.get("status", "draft")),
                            current_version=plugin_data.get("current_version", "1.0.0"),
                            downloads=plugin_data.get("downloads", 0),
                            rating=plugin_data.get("rating", 0.0)
                        )
                
                print(f"[EnhancedMarketplace] 加载了 {len(self.plugins)} 个插件")
                
        except Exception as e:
            print(f"[EnhancedMarketplace] 加载索引失败: {e}")
    
    def _save_index(self):
        """保存插件索引"""
        try:
            data = {}
            for plugin_id, plugin in self.plugins.items():
                data[plugin_id] = {
                    "name": plugin.name,
                    "description": plugin.description,
                    "author": plugin.author,
                    "category": plugin.category.value,
                    "status": plugin.status.value,
                    "current_version": plugin.current_version,
                    "downloads": plugin.downloads,
                    "rating": plugin.rating
                }
            
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print("[EnhancedMarketplace] 索引已保存")
            
        except Exception as e:
            print(f"[EnhancedMarketplace] 保存索引失败: {e}")
    
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
            plugin.status = PluginStatus.APPROVED
            
            # 保存
            self.plugins[plugin.plugin_id] = plugin
            self._save_index()
            
            print(f"[EnhancedMarketplace] 插件已发布: {plugin.name} v{plugin.current_version}")
            return True
            
        except Exception as e:
            print(f"[EnhancedMarketplace] 发布失败: {e}")
            return False
    
    def search_plugins(self, query: str = None, category: PluginCategory = None,
                      tags: List[str] = None, min_rating: float = 0.0,
                      sort_by: str = "downloads") -> List[PluginEntry]:
        """搜索插件"""
        results = []
        
        for plugin in self.plugins.values():
            # 状态过滤
            if plugin.status != PluginStatus.APPROVED:
                continue
            
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
            
            print(f"[EnhancedMarketplace] 评论已添加: {plugin.name}")
            return True
            
        except Exception as e:
            print(f"[EnhancedMarketplace] 添加评论失败: {e}")
            return False
    
    def record_download(self, plugin_id: str) -> bool:
        """记录下载"""
        if plugin_id not in self.plugins:
            return False
        
        try:
            self.plugins[plugin_id].downloads += 1
            self.download_stats[plugin_id] = self.download_stats.get(plugin_id, 0) + 1
            self._save_index()
            return True
        except Exception:
            return False
    
    def get_categories(self) -> Dict[str, int]:
        """获取类别统计"""
        categories = {}
        for plugin in self.plugins.values():
            if plugin.status == PluginStatus.APPROVED:
                category = plugin.category.value
                categories[category] = categories.get(category, 0) + 1
        return categories
    
    def get_top_plugins(self, count: int = 10, sort_by: str = "downloads") -> List[PluginEntry]:
        """获取热门插件"""
        return self.search_plugins(sort_by=sort_by)[:count]
    
    def get_new_plugins(self, count: int = 10) -> List[PluginEntry]:
        """获取最新插件"""
        return self.search_plugins(sort_by="updated")[:count]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        approved_plugins = [p for p in self.plugins.values() if p.status == PluginStatus.APPROVED]
        
        total_downloads = sum(p.downloads for p in approved_plugins)
        avg_rating = sum(p.rating for p in approved_plugins) / max(1, len(approved_plugins))
        
        return {
            "total_plugins": len(self.plugins),
            "approved_plugins": len(approved_plugins),
            "total_downloads": total_downloads,
            "average_rating": avg_rating,
            "categories": self.get_categories()
        }

# 全局实例
_enhanced_marketplace: Optional[EnhancedPluginMarketplace] = None

def get_enhanced_marketplace(storage_dir: str = None) -> EnhancedPluginMarketplace:
    """获取增强版插件市场实例"""
    global _enhanced_marketplace
    if _enhanced_marketplace is None:
        _enhanced_marketplace = EnhancedPluginMarketplace(storage_dir or "./plugins/marketplace")
    return _enhanced_marketplace
