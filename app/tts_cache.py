#!/usr/bin/env python3
"""
=====================================
TTS 缓存系统 (TTS Cache System)
=====================================

功能概述:
- 缓存已生成的 TTS 语音文件到本地磁盘，避免对相同文本重复调用 TTS 接口合成语音
- 基于文本内容 + 语音名称 + TTS 提供商生成唯一缓存键（MD5 哈希）
- 提供两种自动清理策略：
  1. 惰性过期清理：首次读取缓存时触发，删除超过保留天数的缓存文件
  2. 容量限制清理：每次写入新缓存后（带 60 秒限频），删除最旧文件直到总大小降至上限的 80%

设计决策:
- 采用"惰性清理"而非"启动时立即清理"，是为了不阻塞应用的启动流程
- 容量清理使用 80% 水位线而非 100%，是为了减少频繁触发清理带来的 I/O 开销
- 容量检查设有 60 秒限频，防止高频写入时反复扫描磁盘

作者: 咕咕嘎嘎
日期: 2026-04-06
"""

import os          # 用于检查源音频文件是否存在
import hashlib     # 用于对缓存键进行 MD5 哈希，生成唯一文件名
import shutil      # 用于高效复制文件（copy2 保留元数据）和递归删除目录
import time        # 用于获取当前时间戳，计算文件年龄和实现限频机制
from pathlib import Path     # 面向对象的路径操作，比 os.path 更安全可读
from typing import Optional  # 类型提示：表示返回值可能为 None


class TTSCache:
    """
    TTS 缓存管理器

    本类实现了一个基于磁盘文件的 TTS（Text-To-Speech）语音缓存系统。
    核心思想：以 "provider:voice:text" 的组合作为唯一标识，通过 MD5 哈希
    映射为文件名，将合成后的 .wav 音频文件持久化到磁盘缓存目录中。

    生命周期：
    1. 初始化时创建缓存目录（如不存在）
    2. 每次调用 get() 查询缓存 —— 命中则直接返回文件路径，未命中则返回 None
    3. TTS 合成完成后调用 set() 将音频文件复制到缓存目录
    4. 自动在合适的时机执行过期清理和容量清理
    """

    def __init__(self, cache_dir: str = "cache/tts", max_age_days: int = 7, max_size_mb: int = 100):
        """
        初始化 TTS 缓存管理器

        设计意图:
        - 在构造时仅创建目录、设置参数，不执行任何清理操作（惰性清理策略）
        - 清理操作推迟到首次 get() 调用时触发，确保应用启动速度不受缓存规模影响

        Args:
            cache_dir: 缓存文件存放的目录路径，默认为 "cache/tts"
            max_age_days: 缓存文件的最大保留天数，超过此天数的文件将在惰性清理时被删除，默认 7 天
            max_size_mb: 缓存目录的总大小上限（MB），超出时将按 LRU 策略清理最旧文件，默认 100MB

        内部状态:
            - _cleanup_done: 标记过期清理是否已执行过（整个生命周期只执行一次）
            - _last_size_check: 上次容量检查的时间戳，用于实现 60 秒限频
        """
        # 将字符串路径转换为 Path 对象，便于后续的路径拼接和文件操作
        self.cache_dir = Path(cache_dir)
        # 创建缓存目录（含所有必要的父目录），如果已存在则不报错
        # parents=True 允许创建多级目录，exist_ok=True 避免目录已存在时抛异常
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 将天数转换为秒数，便于后续与文件修改时间戳直接比较
        self.max_age_seconds = max_age_days * 24 * 3600
        # 将 MB 转换为字节数，用于与磁盘文件大小直接比较
        self.max_size_bytes = max_size_mb * 1024 * 1024

        # 惰性过期清理标记：初始为 False，表示尚未执行过过期清理
        # 首次 get() 命中缓存时将其设为 True 并触发一次性清理
        # 设计原因：避免在 __init__ 中遍历大量缓存文件，拖慢启动速度
        self._cleanup_done = False
        # 上次容量检查的时间戳，初始为 0 表示从未检查过
        # 配合 60 秒限频窗口，防止高频写入场景下反复执行磁盘扫描
        self._last_size_check = 0

    def get_cache_key(self, text: str, voice: str, provider: str = "") -> str:
        """
        根据文本、语音名称和提供商生成缓存键（唯一标识符）

        设计意图:
        - 将 TTS 合成的三个核心参数拼接为字符串，再取 MD5 哈希作为文件名
        - 使用 MD5 而非 SHA256 是因为此处不需要密码学安全性，MD5 更快且缓存键冲突概率极低
        - 拼接格式为 "provider:voice:text"，冒号作为分隔符确保各字段不会歧义合并

        Args:
            text: 要合成语音的文本内容（如 "你好世界"）
            voice: TTS 语音的名称/ID（如 "zh-CN-XiaoxiaoNeural"）
            provider: TTS 服务提供商名称（如 "edge", "azure"），默认为空字符串

        Returns:
            str: 32 位十六进制 MD5 哈希字符串（如 "a1b2c3d4..."），用作缓存文件名
        """
        # 将三个参数用冒号拼接为唯一键字符串
        # 格式示例: "edge:zh-CN-XiaoxiaoNeural:你好世界"
        # 即使 text 中包含冒号也不会造成问题，因为 MD5 是对整个字符串做哈希
        key_str = f"{provider}:{voice}:{text}"
        # 对拼接后的字符串进行 UTF-8 编码，再计算 MD5 哈希，取十六进制摘要作为缓存键
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def get(self, text: str, voice: str, provider: str = "") -> Optional[str]:
        """
        查询缓存中是否已存在对应的音频文件

        设计意图:
        - 本方法是缓存查询的入口，调用方在调用 TTS 合成接口前先调用此方法
        - 如果命中缓存，直接返回文件路径，跳过耗时的网络合成请求
        - 副作用：首次命中时会触发一次性过期清理（惰性清理策略）

        Args:
            text: 要查询的文本内容
            voice: 语音名称
            provider: TTS 提供商

        Returns:
            Optional[str]:
            - 命中缓存时返回缓存文件的绝对路径字符串（如 "cache/tts/a1b2c3d4.wav"）
            - 未命中时返回 None，表示需要重新合成
        """
        # 根据参数组合生成唯一的缓存键（MD5 哈希）
        key = self.get_cache_key(text, voice, provider)
        # 拼接缓存文件的完整路径: 缓存目录 / MD5哈希.wav
        cache_file = self.cache_dir / f"{key}.wav"

        if cache_file.exists():
            # ===== 惰性过期清理触发 =====
            # 如果这是首次命中缓存，且尚未执行过过期清理，则立即执行一次
            # 设计原因：将清理推迟到"首次需要用到缓存"的时刻，避免阻塞启动
            if not self._cleanup_done:
                self._cleanup_done = True  # 标记为已执行，后续不再触发
                self._cleanup_expired()    # 执行过期缓存清理
            return str(cache_file)  # 命中缓存，返回文件路径

        return None  # 未命中，返回 None 表示需要重新合成

    def set(self, text: str, voice: str, audio_path: str, provider: str = ""):
        """
        保存音频到缓存

        功能: 将 TTS 合成生成的音频文件复制到缓存目录中，以备后续相同请求直接复用。
        保存后会检查缓存总大小，如果超出限制则触发容量清理。

        Args:
            text: 文本内容（用于生成缓存键）
            voice: 语音名称（用于生成缓存键）
            audio_path: 源音频文件的路径（TTS 合成输出的临时文件）
            provider: TTS 提供商（用于生成缓存键）
        """
        # 防御性检查：如果源音频文件不存在，跳过缓存保存
        if not os.path.exists(audio_path):
            return

        # 生成缓存键和目标缓存文件路径
        key = self.get_cache_key(text, voice, provider)
        cache_file = self.cache_dir / f"{key}.wav"

        try:
            # 使用 copy2 而非 copy: copy2 会保留源文件的元数据（修改时间等）
            # 这对于后续基于 st_mtime 的过期清理是必要的
            shutil.copy2(audio_path, cache_file)

            # 保存后检查缓存总大小，必要时触发容量清理
            # 设计原因：每次写入都可能使缓存超出上限，需及时检查
            self._check_size_limit()
        except Exception as e:
            print(f"️ 缓存保存失败: {e}")

    def clear(self):
        """
        清空所有缓存

        功能: 删除整个缓存目录，然后重新创建一个空的缓存目录。
        用于用户主动清理缓存或调试时重置状态。
        """
        try:
            shutil.rmtree(self.cache_dir)  # 递归删除整个缓存目录及其内容
            self.cache_dir.mkdir(parents=True, exist_ok=True)  # 重新创建空目录
            print(" 缓存已清空")
        except Exception as e:
            print(f"️ 清空缓存失败: {e}")

    def _cleanup_expired(self):
        """
        清理过期缓存（内部方法）

        功能: 遍历缓存目录中的所有 .wav 文件，删除修改时间超过 max_age_seconds 的文件。
        由 get() 方法在首次命中缓存时触发，整个生命周期只执行一次。

        设计原因: "惰性清理"策略 —— 不在 __init__ 中阻塞启动，而是在首次实际使用缓存时执行。
        """
        now = time.time()  # 获取当前时间戳（Unix 纪元秒数）
        removed_count = 0  # 已删除的文件计数

        # 遍历缓存目录下所有 .wav 文件
        for cache_file in self.cache_dir.glob("*.wav"):
            try:
                # 计算文件年龄: 当前时间 - 文件最后修改时间
                age = now - cache_file.stat().st_mtime
                if age > self.max_age_seconds:
                    cache_file.unlink()  # 删除过期文件
                    removed_count += 1
            except Exception as e:
                print(f"️ 清理缓存失败: {e}")

        # 如果有文件被清理，输出日志
        if removed_count > 0:
            print(f" [TTSCache] 惰性清理: {removed_count} 个过期缓存")

    def _check_size_limit(self):
        """
        检查缓存大小限制并按需清理（内部方法）

        功能: 计算缓存目录的总大小，如果超出 max_size_bytes 上限，
        则按访问时间从旧到新依次删除文件，直到总大小降至上限的 80%。

        设计细节:
        - 限频机制: 每 60 秒最多执行一次容量检查，防止高频写入时反复扫描磁盘
        - 80% 水位线: 不清理到 100%，而是 80%，减少频繁触发清理的 I/O 开销
        - 删除策略: 按访问时间（st_atime）排序，优先删除最久未访问的文件（类 LRU）
        """
        now = time.time()
        # 限频检查: 距离上次检查不足 60 秒则跳过
        if (now - self._last_size_check) < 60:
            return
        self._last_size_check = now  # 更新上次检查时间

        # 计算缓存目录中所有 .wav 文件的总大小
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.wav"))

        if total_size > self.max_size_bytes:
            # 按访问时间升序排序（最旧的在前面），优先删除最久未访问的文件
            files = sorted(
                self.cache_dir.glob("*.wav"),
                key=lambda f: f.stat().st_atime  # st_atime: 最后访问时间
            )

            removed_count = 0
            for f in files:
                try:
                    file_size = f.stat().st_size
                    f.unlink()  # 删除文件
                    removed_count += 1
                    total_size -= file_size  # 从总计中减去已删除文件的大小

                    # 清理到 80% 水位线即停止，避免过度清理
                    if total_size <= self.max_size_bytes * 0.8:
                        break
                except Exception as e:
                    print(f"️ 删除缓存失败: {e}")

            if removed_count > 0:
                print(f"️ 清理了 {removed_count} 个旧缓存（大小限制）")

    def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            dict: 包含以下字段:
                - count (int): 缓存文件数量
                - size_mb (float): 缓存总大小（MB）
                - size_bytes (int): 缓存总大小（字节）
        """
        files = list(self.cache_dir.glob("*.wav"))  # 获取所有 .wav 文件
        total_size = sum(f.stat().st_size for f in files)  # 计算总大小

        return {
            "count": len(files),                              # 文件数量
            "size_mb": total_size / (1024 * 1024),            # 转换为 MB
            "size_bytes": total_size,                         # 原始字节数
        }


if __name__ == "__main__":
    # ===== 模块自测入口 =====
    print(" 测试 TTS 缓存...")

    cache = TTSCache()

    # 测试缓存键生成
    key = cache.get_cache_key("你好", "zh-CN-XiaoxiaoNeural", "edge")
    print(f" 缓存键: {key}")

    # 测试统计
    stats = cache.get_stats()
    print(f" 缓存统计: {stats['count']} 个文件, {stats['size_mb']:.2f} MB")

    print(" 测试完成")
