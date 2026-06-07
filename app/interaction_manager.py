"""
交互模式管理器

负责管理 AIVTuber 的交互模式（命令行交互、Web 模式等）。

设计意图:
    - 将 AIVTuber 类中的交互模式逻辑提取到独立模块
    - 保持原有功能不变
    - 提高代码可维护性
"""

import logging
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


class InteractionManager:
    """
    交互模式管理器

    管理 AIVTuber 的各种交互模式，包括命令行交互、Web 模式等。
    """

    def __init__(self, aivtuber_instance: Any) -> None:
        """
        初始化交互模式管理器

        Args:
            aivtuber_instance: AIVTuber 实例，用于访问其方法和属性
        """
        self.aivtuber = aivtuber_instance
        self.logger = aivtuber_instance.logger

    def run_interactive(self) -> None:
        """
        交互模式 - 命令行文字/语音对话

        设计意图:
            用于开发和调试，支持:
            1. 文字输入: 直接在终端输入文字对话
            2. 语音输入: 输入 "voice" 切换到语音模式（3秒录音 → ASR → 回复 → TTS）
            3. Ctrl+C 退出

        执行流程:
            循环:
            - 语音模式: select 检测 stdin 输入停止 → 录音3秒 → process_audio → 播放
            - 文字模式: input() 读取 → process_message → speak() → 播放
        """
        logger.info("\n 咕咕嘎嘎 - 交互模式")
        logger.info("输入文字对话，按 Ctrl+C 退出")
        logger.info("输入 'voice' 开启语音输入模式\n")

        voice_mode = False
        _voice = None  # 延迟获取 voice 模块（避免启动时就加载 sounddevice）

        try:
            while True:
                if voice_mode:
                    logger.info("\n 语音输入模式已开启，按任意键停止...")
                    import select
                    # 非阻塞检测 stdin 是否有输入（超时 0 秒立即返回）
                    if select.select([sys.stdin], [], [], 0)[0]:
                        input()  # 消耗掉按键输入
                        voice_mode = False
                        logger.info(" 语音输入模式已关闭")
                        continue

                    # 懒加载 voice 模块（仅在首次进入语音模式时加载）
                    if _voice is None:
                        _voice = self.aivtuber.voice

                    # 录音: start() 开始 → 等待3秒 → stop() 结束并返回音频文件路径
                    if _voice.start():
                        time.sleep(3)  # 录音3秒
                        audio_file = _voice.stop()

                        if audio_file:
                            logger.info(f" 录音文件: {audio_file}")
                            result = self.aivtuber.process_audio(audio_file)
                            logger.info(f" 咕咕嘎嘎: {result['text']}")

                            # 播放 TTS 生成的回复音频
                            if result.get("audio"):
                                self.aivtuber._play_audio(result["audio"])
                else:
                    # 文字输入模式
                    user_input = input(" 你: ").strip()
                    if not user_input:
                        continue

                    # 特殊命令: 切换到语音模式
                    if user_input == "voice":
                        # 懒加载 voice 模块
                        if _voice is None:
                            _voice = self.aivtuber.voice
                        if _voice.is_available():
                            voice_mode = True
                            logger.info(" 进入语音输入模式...")
                        else:
                            logger.info("️ 语音输入不可用，请安装sounddevice")
                            continue

                    # 特殊命令: 退出
                    if user_input.lower() in ["exit", "quit", "bye"]:
                        logger.info(" 再见！")
                        break

                    # 处理文字消息
                    result = self.aivtuber.process_message(user_input)
                    logger.info(f" 咕咕嘎嘎: {result['text']}")

                    # 播放 TTS 生成的回复音频
                    if result.get("audio"):
                        self.aivtuber._play_audio(result["audio"])

        except KeyboardInterrupt:
            logger.info("\n 再见！")
        except Exception as e:
            logger.error(f"交互模式错误: {e}")
            raise

    def run_web(self, desktop_mode: bool = False) -> None:
        """
        Web 模式 - 启动 HTTP + WebSocket 服务

        Args:
            desktop_mode: 是否为桌面模式（用于桌面应用）
        """
        try:
            logger.info(" 启动 Web 服务...")

            # 启动 HTTP 服务器
            web_server = self.aivtuber.web_server
            web_server.start()

            # 启动 WebSocket 服务器
            ws_server = self.aivtuber.ws_server
            ws_server.start()

            logger.info(f" Web 服务已启动")
            logger.info(f"   HTTP: http://localhost:{web_server.port}")
            logger.info(f"   WebSocket: ws://localhost:{ws_server.port}")

            if desktop_mode:
                logger.info("️ 桌面模式已启用")
                # 这里可以添加桌面特定的初始化逻辑

            # 保持服务运行
            logger.info("按 Ctrl+C 停止服务...")
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n 服务已停止")
            self.aivtuber.stop()
        except Exception as e:
            logger.error(f"Web 服务启动失败: {e}")
            raise

    def run_live(self, platform: str = "bilibili") -> None:
        """
        直播模式 - 启动直播平台集成

        Args:
            platform: 直播平台名称（bilibili, douyin, etc.）
        """
        try:
            logger.info(f" 启动直播模式: {platform}")

            # 获取直播模块
            live_manager = self.aivtuber.live
            if not live_manager:
                logger.error("直播模块未初始化")
                return

            # 启动直播
            live_manager.start(platform)

            logger.info(f" 直播模式已启动: {platform}")
            logger.info("按 Ctrl+C 停止直播...")

            # 保持直播运行
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n 直播已停止")
            if live_manager:
                live_manager.stop()
        except Exception as e:
            logger.error(f"直播模式启动失败: {e}")
            raise

    def run_bot(self, platform: str = "telegram") -> None:
        """
        机器人模式 - 启动聊天机器人

        Args:
            platform: 机器人平台名称（telegram, discord, etc.）
        """
        try:
            logger.info(f" 启动机器人模式: {platform}")

            # 获取机器人模块
            bot_manager = self.aivtuber.bot
            if not bot_manager:
                logger.error("机器人模块未初始化")
                return

            # 启动机器人
            bot_manager.start(platform)

            logger.info(f" 机器人模式已启动: {platform}")
            logger.info("按 Ctrl+C 停止机器人...")

            # 保持机器人运行
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n 机器人已停止")
            if bot_manager:
                bot_manager.stop()
        except Exception as e:
            logger.error(f"机器人模式启动失败: {e}")
            raise

    def run_game(self, game_name: str = "minecraft") -> None:
        """
        游戏模式 - 启动游戏集成

        Args:
            game_name: 游戏名称（minecraft, stardew_valley, etc.）
        """
        try:
            logger.info(f" 启动游戏模式: {game_name}")

            # 获取游戏模块
            game_manager = self.aivtuber.game
            if not game_manager:
                logger.error("游戏模块未初始化")
                return

            # 启动游戏
            game_manager.start(game_name)

            logger.info(f" 游戏模式已启动: {game_name}")
            logger.info("按 Ctrl+C 停止游戏...")

            # 保持游戏运行
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n 游戏已停止")
            if game_manager:
                game_manager.stop()
        except Exception as e:
            logger.error(f"游戏模式启动失败: {e}")
            raise

    def run_multi_mode(self, modes: list) -> None:
        """
        多模式运行 - 同时启动多个服务

        Args:
            modes: 要启动的模式列表，如 ["web", "live:bilibili", "bot:telegram"]
        """
        try:
            logger.info(f" 启动多模式: {', '.join(modes)}")

            started_services = []

            for mode in modes:
                if mode == "web":
                    self.run_web()
                    started_services.append("web")
                elif mode.startswith("live:"):
                    platform = mode.split(":")[1]
                    self.run_live(platform)
                    started_services.append(f"live:{platform}")
                elif mode.startswith("bot:"):
                    platform = mode.split(":")[1]
                    self.run_bot(platform)
                    started_services.append(f"bot:{platform}")
                elif mode.startswith("game:"):
                    game_name = mode.split(":")[1]
                    self.run_game(game_name)
                    started_services.append(f"game:{game_name}")
                else:
                    logger.warning(f"未知模式: {mode}")

            logger.info(f" 多模式已启动: {', '.join(started_services)}")
            logger.info("按 Ctrl+C 停止所有服务...")

            # 保持所有服务运行
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("\n 所有服务已停止")
            self.aivtuber.stop()
        except Exception as e:
            logger.error(f"多模式启动失败: {e}")
            raise
