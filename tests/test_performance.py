"""
性能测试模块
测试各模块的性能指标
"""

import asyncio
import time
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_framework import (
    get_test_runner, assert_equal, assert_not_none, assert_true
)

async def test_vad_performance():
    """测试VAD性能"""
    from app.vad import VADConfig, SileroVAD
    import numpy as np
    
    # 创建VAD实例
    config = VADConfig()
    vad = SileroVAD(config)
    
    # 创建测试音频
    test_audio = np.random.randn(512).astype(np.float32) * 0.1
    
    # 性能测试
    start_time = time.time()
    iterations = 100
    
    for _ in range(iterations):
        await vad.process_audio(test_audio)
    
    elapsed = (time.time() - start_time) * 1000
    avg_time = elapsed / iterations
    
    print(f"VAD处理延迟: {avg_time:.2f}ms/帧")
    assert_true(avg_time < 10, "VAD处理延迟应小于10ms")

async def test_cache_performance():
    """测试缓存性能"""
    from app.cache_optimizer import LRUCache
    
    # 创建缓存
    cache = LRUCache(max_size=1000)
    
    # 写入性能测试
    start_time = time.time()
    iterations = 1000
    
    for i in range(iterations):
        cache.set(f"key_{i}", f"value_{i}")
    
    write_elapsed = (time.time() - start_time) * 1000
    write_avg = write_elapsed / iterations
    
    # 读取性能测试
    start_time = time.time()
    
    for i in range(iterations):
        cache.get(f"key_{i}")
    
    read_elapsed = (time.time() - start_time) * 1000
    read_avg = read_elapsed / iterations
    
    print(f"缓存写入延迟: {write_avg:.3f}ms/次")
    print(f"缓存读取延迟: {read_avg:.3f}ms/次")
    
    assert_true(write_avg < 1, "缓存写入延迟应小于1ms")
    assert_true(read_avg < 0.5, "缓存读取延迟应小于0.5ms")

async def test_interaction_optimizer_performance():
    """测试交互优化器性能"""
    from app.interaction_optimizer import Debouncer, Throttler
    
    # 防抖器性能测试
    debouncer = Debouncer(delay_ms=100)
    
    start_time = time.time()
    iterations = 100
    
    for i in range(iterations):
        debouncer.should_execute = lambda: True
    
    elapsed = (time.time() - start_time) * 1000
    print(f"防抖器检查延迟: {elapsed/iterations:.3f}ms/次")
    
    # 节流器性能测试
    throttler = Throttler(interval_ms=100)
    
    start_time = time.time()
    
    for i in range(iterations):
        throttler.should_execute(f"key_{i % 10}")
    
    elapsed = (time.time() - start_time) * 1000
    print(f"节流器检查延迟: {elapsed/iterations:.3f}ms/次")

async def test_audio_preprocessor_performance():
    """测试音频预处理器性能"""
    from app.asr.audio_preprocessor import get_audio_preprocessor
    import numpy as np
    
    # 创建预处理器
    preprocessor = get_audio_preprocessor()
    
    # 创建测试音频（1秒）
    test_audio = np.random.randn(16000).astype(np.float32) * 0.1
    
    # 性能测试
    start_time = time.time()
    iterations = 10
    
    for _ in range(iterations):
        preprocessor.process(test_audio)
    
    elapsed = (time.time() - start_time) * 1000
    avg_time = elapsed / iterations
    
    print(f"音频预处理延迟: {avg_time:.2f}ms/秒音频")
    assert_true(avg_time < 100, "音频预处理延迟应小于100ms")

async def test_speed_controller_performance():
    """测试语速控制器性能"""
    from app.tts.speed_control import get_speed_controller
    
    # 获取控制器
    controller = get_speed_controller()
    
    # 性能测试
    start_time = time.time()
    iterations = 1000
    
    for _ in range(iterations):
        controller.get_speed_factor(emotion="happy")
    
    elapsed = (time.time() - start_time) * 1000
    avg_time = elapsed / iterations
    
    print(f"语速计算延迟: {avg_time:.3f}ms/次")
    assert_true(avg_time < 1, "语速计算延迟应小于1ms")

async def test_emotion_voice_performance():
    """测试情感语音性能"""
    from app.emotion.voice_emotion import get_emotion_voice_controller, VoiceEmotion
    
    # 获取控制器
    controller = get_emotion_voice_controller()
    
    # 性能测试
    start_time = time.time()
    iterations = 1000
    
    for _ in range(iterations):
        controller.set_emotion(VoiceEmotion.HAPPY)
        controller.get_tts_params("测试文本")
    
    elapsed = (time.time() - start_time) * 1000
    avg_time = elapsed / iterations
    
    print(f"情感语音计算延迟: {avg_time:.3f}ms/次")
    assert_true(avg_time < 1, "情感语音计算延迟应小于1ms")

async def test_memory_usage():
    """测试内存使用"""
    import psutil
    import gc
    
    # 获取当前进程
    process = psutil.Process()
    
    # 记录初始内存
    gc.collect()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 创建大量对象
    from app.cache_optimizer import LRUCache
    cache = LRUCache(max_size=10000)
    
    for i in range(10000):
        cache.set(f"key_{i}", f"value_{i}" * 100)
    
    # 记录峰值内存
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 清理
    cache.clear()
    gc.collect()
    
    # 记录清理后内存
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"初始内存: {initial_memory:.1f}MB")
    print(f"峰值内存: {peak_memory:.1f}MB")
    print(f"最终内存: {final_memory:.1f}MB")
    print(f"内存增长: {peak_memory - initial_memory:.1f}MB")
    
    # 内存增长应该在合理范围内
    assert_true(peak_memory - initial_memory < 100, "内存增长应小于100MB")

async def test_concurrent_performance():
    """测试并发性能"""
    from app.cache_optimizer import LRUCache
    
    # 创建缓存
    cache = LRUCache(max_size=1000)
    
    # 并发写入测试
    async def write_task(task_id):
        for i in range(100):
            cache.set(f"task_{task_id}_key_{i}", f"value_{i}")
    
    start_time = time.time()
    
    # 并发执行
    tasks = [write_task(i) for i in range(10)]
    await asyncio.gather(*tasks)
    
    elapsed = (time.time() - start_time) * 1000
    
    print(f"并发写入延迟: {elapsed:.2f}ms (10任务 x 100次写入)")
    assert_true(elapsed < 1000, "并发写入应在1秒内完成")

async def test_startup_optimizer_performance():
    """测试启动优化器性能"""
    from app.startup_optimizer import StartupOptimizer, LoadPriority
    
    # 创建优化器
    optimizer = StartupOptimizer()
    
    # 注册模块
    loaded_count = 0
    
    def make_loader(loader_id):
        def loader():
            nonlocal loaded_count
            loaded_count += 1
            time.sleep(0.01)  # 模拟加载时间
        return loader
    
    for i in range(10):
        optimizer.register_module(
            f"module_{i}",
            make_loader(i),
            priority=LoadPriority.HIGH
        )
    
    # 性能测试
    start_time = time.time()
    await optimizer.load_all_modules()
    elapsed = (time.time() - start_time) * 1000
    
    print(f"启动优化加载延迟: {elapsed:.2f}ms (10个模块)")
    assert_equal(loaded_count, 10, "所有模块应该被加载")

async def run_all_tests():
    """运行所有测试"""
    runner = get_test_runner()
    
    # 创建测试套件
    suite = runner.create_suite("性能测试")
    
    # 定义测试列表
    tests = [
        ("VAD性能测试", test_vad_performance),
        ("缓存性能测试", test_cache_performance),
        ("交互优化器性能测试", test_interaction_optimizer_performance),
        ("音频预处理器性能测试", test_audio_preprocessor_performance),
        ("语速控制器性能测试", test_speed_controller_performance),
        ("情感语音性能测试", test_emotion_voice_performance),
        ("内存使用测试", test_memory_usage),
        ("并发性能测试", test_concurrent_performance),
        ("启动优化器性能测试", test_startup_optimizer_performance),
    ]
    
    # 运行测试
    print("\n" + "="*60)
    print("运行性能测试")
    print("="*60 + "\n")
    
    for test_name, test_func in tests:
        await runner.run_test(test_name, test_func, "性能测试")
    
    # 生成报告
    report = runner.generate_report()
    print("\n" + report)
    
    # 保存报告
    runner.save_report("tests/performance_test_report.md")
    
    return suite

if __name__ == "__main__":
    asyncio.run(run_all_tests())
