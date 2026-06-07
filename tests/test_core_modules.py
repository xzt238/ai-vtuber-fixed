"""
核心模块单元测试
"""

import asyncio
import sys
import os
import logging

logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_framework import (
    get_test_runner, assert_equal, assert_not_none, assert_true
)

async def test_version_module():
    """测试版本模块"""
    from app.version import __version__, VERSION
    
    assert_not_none(__version__, "版本号不应为None")
    assert_not_none(VERSION, "VERSION不应为None")
    assert_equal(__version__, VERSION, "版本号应一致")
    assert_true(__version__.startswith("1."), "版本号应以1.开头")

async def test_vad_config():
    """测试VAD配置"""
    from app.vad import VADConfig, VADState
    
    # 测试默认配置
    config = VADConfig()
    assert_equal(config.prob_threshold, 0.4, "默认概率阈值应为0.4")
    assert_equal(config.db_threshold, 60, "默认音量阈值应为60")
    assert_equal(config.required_hits, 3, "默认激活帧数应为3")
    assert_equal(config.required_misses, 24, "默认停止帧数应为24")
    
    # 测试状态枚举
    assert_equal(VADState.IDLE.value, "idle", "IDLE状态值应为idle")
    assert_equal(VADState.ACTIVE.value, "active", "ACTIVE状态值应为active")
    assert_equal(VADState.INACTIVE.value, "inactive", "INACTIVE状态值应为inactive")

async def test_interrupt_reason():
    """测试打断原因枚举"""
    from app.interrupt import InterruptReason
    
    assert_equal(InterruptReason.USER_SPEECH.value, "user_speech")
    assert_equal(InterruptReason.MANUAL.value, "manual")
    assert_equal(InterruptReason.TIMEOUT.value, "timeout")
    assert_equal(InterruptReason.ERROR.value, "error")

async def test_speed_controller():
    """测试语速控制器"""
    from app.tts.speed_control import SpeedController, SpeedMode, SpeedConfig
    
    # 测试默认配置
    config = SpeedConfig()
    assert_equal(config.mode, SpeedMode.NORMAL, "默认模式应为NORMAL")
    assert_equal(config.speed_factor, 1.0, "默认语速因子应为1.0")
    
    # 测试控制器
    controller = SpeedController(config)
    speed = controller.get_speed_factor()
    assert_equal(speed, 1.0, "正常模式语速应为1.0")

async def test_emotion_voice():
    """测试情感语音控制"""
    from app.emotion.voice_emotion import (
        EmotionVoiceMapper, VoiceEmotion, VoiceEmotionParams
    )
    
    mapper = EmotionVoiceMapper()
    
    # 测试情感参数
    happy_params = mapper.get_params(VoiceEmotion.HAPPY)
    assert_not_none(happy_params, "开心情感参数不应为None")
    assert_true(happy_params.speed_factor > 1.0, "开心时语速应加快")
    assert_true(happy_params.pitch_shift > 0, "开心时音高应提高")
    
    sad_params = mapper.get_params(VoiceEmotion.SAD)
    assert_true(sad_params.speed_factor < 1.0, "悲伤时语速应减慢")
    assert_true(sad_params.pitch_shift < 0, "悲伤时音高应降低")

async def test_audio_preprocessor_config():
    """测试音频预处理器配置"""
    from app.asr.audio_preprocessor import AudioPreprocessorConfig
    
    config = AudioPreprocessorConfig()
    assert_equal(config.noise_reduce_strength, 0.5, "默认降噪强度应为0.5")
    assert_equal(config.target_db, -20.0, "默认目标音量应为-20dB")
    assert_equal(config.highpass_freq, 80, "默认高通频率应为80Hz")
    assert_equal(config.lowpass_freq, 8000, "默认低通频率应为8000Hz")

async def test_screen_region():
    """测试屏幕区域"""
    from app.game.screen_recognition import ScreenRegion
    
    region = ScreenRegion(x=100, y=200, width=800, height=600, name="test")
    assert_equal(region.x, 100, "x坐标应为100")
    assert_equal(region.y, 200, "y坐标应为200")
    assert_equal(region.width, 800, "宽度应为800")
    assert_equal(region.height, 600, "高度应为600")
    assert_equal(region.name, "test", "名称应为test")

async def test_plugin_category():
    """测试插件类别"""
    from app.plugin.marketplace import PluginCategory
    
    assert_equal(PluginCategory.TOOL.value, "tool")
    assert_equal(PluginCategory.TTS.value, "tts")
    assert_equal(PluginCategory.ASR.value, "asr")
    assert_equal(PluginCategory.LLM.value, "llm")

async def test_platform_type():
    """测试平台类型"""
    from app.live.platforms import PlatformType
    
    assert_equal(PlatformType.BILIBILI.value, "bilibili")
    assert_equal(PlatformType.DOUYIN.value, "douyin")
    assert_equal(PlatformType.KUAISHOU.value, "kuaishou")
    assert_equal(PlatformType.YOUTUBE.value, "youtube")
    assert_equal(PlatformType.TWITCH.value, "twitch")

async def test_document_version():
    """测试文档版本"""
    from app.rag.incremental_updater import DocumentVersion, ChangeType
    
    version = DocumentVersion(
        doc_id="test_doc",
        content_hash="abc123",
        version=1,
        timestamp=None,
        change_type=ChangeType.ADDED
    )
    
    assert_equal(version.doc_id, "test_doc")
    assert_equal(version.content_hash, "abc123")
    assert_equal(version.version, 1)
    assert_equal(version.change_type, ChangeType.ADDED)

async def run_all_tests():
    """运行所有测试"""
    runner = get_test_runner()
    
    # 创建测试套件
    suite = runner.create_suite("核心模块测试")
    
    # 定义测试列表
    tests = [
        ("版本模块测试", test_version_module),
        ("VAD配置测试", test_vad_config),
        ("打断原因测试", test_interrupt_reason),
        ("语速控制器测试", test_speed_controller),
        ("情感语音测试", test_emotion_voice),
        ("音频预处理器配置测试", test_audio_preprocessor_config),
        ("屏幕区域测试", test_screen_region),
        ("插件类别测试", test_plugin_category),
        ("平台类型测试", test_platform_type),
        ("文档版本测试", test_document_version),
    ]
    
    # 运行测试
    logger.info("\n" + "="*60)
    logger.info("运行核心模块单元测试")
    logger.info("="*60 + "\n")
    
    for test_name, test_func in tests:
        await runner.run_test(test_name, test_func, "核心模块测试")
    
    # 生成报告
    report = runner.generate_report()
    logger.info("\n" + report)
    
    # 保存报告
    runner.save_report("tests/test_report.md")
    
    return suite

if __name__ == "__main__":
    asyncio.run(run_all_tests())
