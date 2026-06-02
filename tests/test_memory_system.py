"""
记忆系统单元测试

测试 MemorySystem 的核心功能：
- 工作记忆 CRUD
- 语义搜索
- 事实提取
- 持久化
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestMemorySystem:
    """MemorySystem 核心功能测试"""

    @pytest.fixture
    def memory_system(self, tmp_path):
        """创建临时记忆系统实例"""
        # 延迟导入避免 PyTorch 依赖
        sys_path_backup = sys.path.copy()
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
            from memory import MemorySystem
            config = {
                "storage_dir": str(tmp_path / "memory"),
                "max_working_memory": 10,
                "summarize_threshold": 5,
            }
            return MemorySystem(config)
        finally:
            sys.path = sys_path_backup

    def test_add_interaction(self, memory_system):
        """测试添加对话记录"""
        memory_system.add_interaction("user", "你好")
        memory_system.add_interaction("assistant", "你好！有什么可以帮你的？")

        assert len(memory_system.working_memory) == 2
        assert memory_system.working_memory[0].role == "user"
        assert memory_system.working_memory[0].content == "你好"
        assert memory_system.working_memory[1].role == "assistant"

    def test_working_memory_limit(self, memory_system):
        """测试工作记忆容量限制"""
        for i in range(20):
            memory_system.add_interaction("user", f"消息 {i}")

        # 应该不超过 max_working_memory
        assert len(memory_system.working_memory) <= memory_system.working_memory_limit

    def test_search_returns_results(self, memory_system):
        """测试语义搜索返回结果"""
        # 添加一些记忆
        memory_system.add_interaction("user", "我喜欢吃苹果")
        memory_system.add_interaction("assistant", "苹果很好吃！")
        memory_system.add_interaction("user", "今天天气真好")
        memory_system.add_interaction("assistant", "是的，适合出去走走")

        # 搜索
        results = memory_system.search("水果", top_k=2)
        assert isinstance(results, list)

    def test_get_stats(self, memory_system):
        """测试获取统计信息"""
        memory_system.add_interaction("user", "测试消息")
        stats = memory_system.get_stats()

        assert "working" in stats
        assert "episodic" in stats
        assert "semantic" in stats
        assert "facts" in stats
        assert stats["working"] >= 1

    def test_persistence(self, memory_system, tmp_path):
        """测试持久化保存和加载"""
        memory_system.add_interaction("user", "持久化测试")
        memory_system.add_interaction("assistant", "已保存")

        # 保存
        memory_system._save_memory_state()

        # 验证文件存在
        state_file = tmp_path / "memory" / "memory_state.json"
        assert state_file.exists()

        # 读取验证
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data.get("working_memory", [])) == 2


class TestMemoryItem:
    """MemoryItem 数据结构测试"""

    def test_memory_item_creation(self):
        """测试 MemoryItem 创建"""
        from datetime import datetime
        # 延迟导入
        sys_path_backup = sys.path.copy()
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
            from memory import MemoryItem
            item = MemoryItem(
                role="user",
                content="测试内容",
                timestamp=datetime.now().timestamp(),
                importance=3
            )
            assert item.role == "user"
            assert item.content == "测试内容"
            assert item.importance == 3
        finally:
            sys.path = sys_path_backup


class TestRetentionScorer:
    """RetentionScorer 记忆评分测试"""

    def test_score_calculation(self):
        """测试记忆评分计算"""
        sys_path_backup = sys.path.copy()
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "app"))
            from memory import RetentionScorer
            from datetime import datetime

            score = RetentionScorer.calculate_score(
                content="这是一条重要的消息",
                role="user",
                importance=4,
                timestamp=datetime.now().timestamp(),
                access_count=3
            )
            assert 0 <= score <= 1
            assert score > 0.5  # 高重要性应该有高分
        finally:
            sys.path = sys_path_backup


# 导入 sys 用于 path 操作
import sys
