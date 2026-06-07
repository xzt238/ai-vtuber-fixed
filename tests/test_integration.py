"""
集成测试模块
测试模块之间的协作和数据流
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_framework import (
    get_test_runner, assert_equal, assert_not_none, assert_true
)

async def test_vad_interrupt_integration():
    """测试VAD和打断处理器的集成"""
    from app.vad import VADConfig, VADState
    from app.interrupt import get_interrupt_handler, InterruptReason
    
    # 获取打断处理器
    handler = get_interrupt_handler()
    
    # 测试打断处理
    result = await handler.handle_interrupt(
        heard_response="测试回复",
        reason=InterruptReason.USER_SPEECH
    )
    
    assert_true(result, "打断处理应该成功")
    assert_equal(handler.get_heard_response(), "测试回复", "应该保存已听到的回复")

async def test_speed_emotion_integration():
    """测试语速控制和情感系统的集成"""
    from app.tts.speed_control import get_speed_controller, SpeedMode
    from app.emotion.voice_emotion import get_emotion_voice_controller, VoiceEmotion
    
    # 获取控制器
    speed_controller = get_speed_controller()
    emotion_controller = get_emotion_voice_controller()
    
    # 设置情感
    emotion_controller.set_emotion(VoiceEmotion.HAPPY)
    
    # 获取语速
    speed = speed_controller.get_speed_factor(emotion="happy")
    
    assert_true(speed > 1.0, "开心时语速应该加快")

async def test_cache_performance_integration():
    """测试缓存和性能监控的集成"""
    from app.cache_optimizer import get_cache_optimizer
    from app.performance_monitor import get_performance_monitor
    
    # 获取实例
    cache = get_cache_optimizer()
    monitor = get_performance_monitor()
    
    # 测试缓存设置和获取
    cache.set("test_key", "test_value", memory_only=True)
    value = await cache.get("test_key")
    
    assert_equal(value, "test_value", "缓存值应该正确")

async def test_audio_preprocessor_flow():
    """测试音频预处理流程"""
    from app.asr.audio_preprocessor import get_audio_preprocessor, AudioPreprocessorConfig
    import numpy as np
    
    # 创建预处理器
    config = AudioPreprocessorConfig(
        noise_reduce_strength=0.5,
        target_db=-20.0,
        enable_normalization=True
    )
    preprocessor = get_audio_preprocessor(config)
    
    # 创建测试音频
    test_audio = np.random.randn(16000).astype(np.float32) * 0.1
    
    # 处理音频
    processed = preprocessor.process(test_audio)
    
    assert_not_none(processed, "处理后的音频不应为None")
    assert_equal(len(processed), len(test_audio), "处理后音频长度应相同")

async def test_interaction_optimizer_flow():
    """测试交互优化流程"""
    from app.interaction_optimizer import get_interaction_optimizer, UserAction
    
    # 获取优化器
    optimizer = get_interaction_optimizer()
    
    # 创建测试操作
    action = UserAction(
        action_id="test_action",
        action_type="click",
        params={"target": "button"}
    )
    
    # 测试操作处理
    async def handler(action):
        return "processed"
    
    result = await optimizer.process_action(action, handler)
    
    assert_equal(result, "processed", "操作应该被处理")

async def test_startup_optimizer_flow():
    """测试启动优化流程"""
    from app.startup_optimizer import get_startup_optimizer, LoadPriority
    
    # 获取优化器
    optimizer = get_startup_optimizer()
    
    # 注册测试模块
    loaded = False
    
    def test_loader():
        nonlocal loaded
        loaded = True
    
    optimizer.register_module(
        "test_module",
        test_loader,
        priority=LoadPriority.CRITICAL
    )
    
    # 加载关键模块
    await optimizer.load_critical_modules()
    
    assert_true(loaded, "模块应该被加载")

async def test_emotion_voice_flow():
    """测试情感语音流程"""
    from app.emotion.voice_emotion import (
        get_emotion_voice_controller, VoiceEmotion
    )
    
    # 获取控制器
    controller = get_emotion_voice_controller()
    
    # 设置情感
    controller.set_emotion(VoiceEmotion.SAD)
    
    # 获取TTS参数
    params = controller.get_tts_params("我很难过")
    
    assert_not_none(params, "TTS参数不应为None")
    assert_true(params["speed_factor"] < 1.0, "悲伤时语速应该减慢")
    assert_true(params["pitch_shift"] < 0, "悲伤时音高应该降低")

async def test_danmaku_enhancer_flow():
    """测试弹幕增强流程"""
    from app.live.danmaku_enhancer import get_danmaku_enhancer
    
    # 获取增强器
    enhancer = get_danmaku_enhancer()
    
    # 测试弹幕处理
    reply = await enhancer.process_danmaku(
        user_id="test_user",
        username="测试用户",
        content="你好",
        room_id="test_room"
    )
    
    # 问候语应该触发回复
    if reply:
        assert_true("你好" in reply.reply_content or "欢迎" in reply.reply_content, 
                    "回复应该包含问候")

async def test_incremental_updater_flow():
    """测试增量更新流程"""
    from app.rag.incremental_updater import get_incremental_updater
    
    # 获取更新器
    updater = get_incremental_updater()
    
    # 测试变更检测
    documents = {
        "doc1": "内容1",
        "doc2": "内容2"
    }
    
    changes = updater.detect_changes(documents)
    
    assert_not_none(changes, "变更检测结果不应为None")

async def test_config_hot_reload_flow():
    """测试配置热重载流程"""
    from app.config_hot_reload import get_config_hot_reload
    
    # 获取热重载器
    hot_reload = get_config_hot_reload()
    
    # 测试添加监听
    result = hot_reload.add_watch("test_file.txt")
    
    # 由于文件不存在，应该返回False
    assert_equal(result, False, "不存在的文件应该返回False")

async def run_all_tests():
    """运行所有测试"""
    runner = get_test_runner()
    
    # 创建测试套件
    suite = runner.create_suite("集成测试")
    
    # 定义测试列表
    tests = [
        ("VAD打断集成测试", test_vad_interrupt_integration),
        ("语速情感集成测试", test_speed_emotion_integration),
        ("缓存性能集成测试", test_cache_performance_integration),
        ("音频预处理流程测试", test_audio_preprocessor_flow),
        ("交互优化流程测试", test_interaction_optimizer_flow),
        ("启动优化流程测试", test_startup_optimizer_flow),
        ("情感语音流程测试", test_emotion_voice_flow),
        ("弹幕增强流程测试", test_danmaku_enhancer_flow),
        ("增量更新流程测试", test_incremental_updater_flow),
        ("配置热重载流程测试", test_config_hot_reload_flow),
    ]
    
    # 运行测试
    print("\n" + "="*60)
    print("运行集成测试")
    print("="*60 + "\n")
    
    for test_name, test_func in tests:
        await runner.run_test(test_name, test_func, "集成测试")
    
    # 生成报告
    report = runner.generate_report()
    print("\n" + report)
    
    # 保存报告
    runner.save_report("tests/integration_test_report.md")
    
    return suite

if __name__ == "__main__":
    asyncio.run(run_all_tests())
