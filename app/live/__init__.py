"""
=====================================
直播平台弹幕集成模块
=====================================

支持多平台弹幕 WebSocket 连接：
- B 站 (Bilibili)
- 抖音 (Douyin)
- YouTube
- Twitch

架构：
- LivePlatform (抽象基类) — 定义弹幕接收接口
- BilibiliPlatform / DouyinPlatform — 各平台实现
- LiveManager — 管理多个平台连接，统一弹幕处理

弹幕流水线：
弹幕 → 解析 → LLM 回复 → TTS 合成 → Live2D 口型

作者: 咕咕嘎嘎
日期: 2026-06-02
"""

import os
import json
import time
import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ==================== 数据结构 ====================

@dataclass
class DanmakuMessage:
    """弹幕消息"""
    platform: str           # 平台名称: bilibili, douyin, youtube, twitch
    user_name: str          # 用户名
    content: str            # 弹幕内容
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""       # 用户 ID
    room_id: str = ""       # 直播间 ID
    extra: Dict[str, Any] = field(default_factory=dict)  # 平台特有数据

    def __str__(self):
        return f"[{self.platform}] {self.user_name}: {self.content}"


@dataclass
class LiveConfig:
    """直播配置"""
    platform: str           # 平台名称
    room_id: str            # 直播间 ID
    enabled: bool = True
    # 平台特有配置
    extra: Dict[str, Any] = field(default_factory=dict)


# ==================== 抽象基类 ====================

class LivePlatform(ABC):
    """直播平台抽象基类

    所有平台实现必须继承此类，并实现 connect/disconnect/on_danmaku 方法。
    """

    def __init__(self, config: LiveConfig, on_danmaku: Callable[[DanmakuMessage], None]):
        """
        Args:
            config: 直播配置
            on_danmaku: 弹幕回调函数，收到弹幕时调用
        """
        self.config = config
        self.on_danmaku = on_danmaku
        self.is_connected = False
        self._thread = None
        self._stop_event = threading.Event()

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass

    @abstractmethod
    def connect(self):
        """连接到直播间"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    def start(self):
        """在后台线程中启动连接"""
        if self.is_connected:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"live-{self.platform_name}"
        )
        self._thread.start()

    def stop(self):
        """停止连接"""
        self._stop_event.set()
        self.disconnect()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self):
        """后台线程主循环"""
        try:
            self.connect()
            self.is_connected = True
            logger.info(f"[{self.platform_name}] 已连接到直播间 {self.config.room_id}")

            # 保持连接
            while not self._stop_event.is_set():
                self._poll_messages()
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"[{self.platform_name}] 连接失败: {e}")
        finally:
            self.is_connected = False
            self.disconnect()

    def _poll_messages(self):
        """轮询消息（子类可覆盖）"""
        pass

    def _emit_danmaku(self, msg: DanmakuMessage):
        """发送弹幕到回调"""
        if self.on_danmaku:
            try:
                self.on_danmaku(msg)
            except Exception as e:
                logger.error(f"[{self.platform_name}] 弹幕回调错误: {e}")


# ==================== B 站平台 ====================

class BilibiliPlatform(LivePlatform):
    """B 站直播弹幕平台

    使用 WebSocket 连接到 B 站弹幕服务器。
    需要提供 room_id（直播间号）。
    """

    @property
    def platform_name(self) -> str:
        return "bilibili"

    def connect(self):
        """连接到 B 站弹幕服务器"""
        try:
            import websocket
        except ImportError:
            logger.error("[bilibili] websocket-client 未安装: pip install websocket-client")
            return

        room_id = self.config.room_id
        uid = self.config.extra.get("uid", 0)
        token = self.config.extra.get("token", "")

        # B 站弹幕服务器地址
        ws_url = "wss://broadcastlv.chat.bilibili.com/sub"

        def on_message(ws, message):
            self._parse_message(message)

        def on_error(ws, error):
            logger.error(f"[bilibili] WebSocket 错误: {error}")

        def on_close(ws, close_status_code, close_msg):
            logger.info(f"[bilibili] WebSocket 关闭")
            self.is_connected = False

        def on_open(ws):
            # 发送认证包
            auth_data = {
                "uid": uid,
                "roomid": int(room_id),
                "protover": 3,
                "platform": "web",
                "type": 2,
                "key": token
            }
            self._send_packet(ws, 7, json.dumps(auth_data))
            logger.info(f"[bilibili] 已发送认证包")

        try:
            self._ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            self._ws.run_forever()
        except Exception as e:
            logger.error(f"[bilibili] 连接失败: {e}")

    def disconnect(self):
        """断开 B 站连接"""
        if hasattr(self, '_ws') and self._ws:
            self._ws.close()

    def _send_packet(self, ws, operation: int, body: str):
        """发送 B 站弹幕协议包"""
        import struct
        body_bytes = body.encode('utf-8')
        header = struct.pack('>IHHII', 16 + len(body_bytes), 16, 1, operation, 1)
        ws.send(header + body_bytes)

    def _parse_message(self, raw_data: bytes):
        """解析 B 站弹幕消息"""
        import struct
        try:
            # 解析包头
            if len(raw_data) < 16:
                return

            packet_len, header_len, proto_ver, operation, seq = struct.unpack(
                '>IHHII', raw_data[:16]
            )

            body = raw_data[16:packet_len]

            if operation == 5:  # 数据包
                if proto_ver == 3:
                    # zlib 压缩
                    import zlib
                    body = zlib.decompress(body)
                    self._parse_message(body)
                    return

                try:
                    data = json.loads(body)
                    cmd = data.get('cmd', '')

                    if cmd == 'DANMU_MSG':
                        # 弹幕消息
                        info = data.get('info', [])
                        if len(info) >= 2:
                            content = str(info[1])
                            user_name = str(info[0][15].get('user', {}).get('base', {}).get('name', ''))
                            if not user_name and len(info) >= 3:
                                user_name = str(info[2][1]) if isinstance(info[2], list) else str(info[2])

                            msg = DanmakuMessage(
                                platform="bilibili",
                                user_name=user_name or "匿名用户",
                                content=content,
                                room_id=self.config.room_id,
                                extra={"cmd": cmd}
                            )
                            self._emit_danmaku(msg)

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.error(f"[bilibili] 消息解析错误: {e}")


# ==================== YouTube 平台 ====================

class YouTubePlatform(LivePlatform):
    """YouTube 直播弹幕平台

    使用 YouTube Data API 获取直播聊天消息。
    需要 API Key 和直播视频 ID。
    """

    @property
    def platform_name(self) -> str:
        return "youtube"

    def connect(self):
        """连接到 YouTube 直播聊天"""
        api_key = self.config.extra.get("api_key", "")
        video_id = self.config.room_id

        if not api_key:
            logger.error("[youtube] 缺少 API Key")
            return

        self._api_key = api_key
        self._video_id = video_id
        self._next_page_token = None
        logger.info(f"[youtube] 已初始化，视频 ID: {video_id}")

    def disconnect(self):
        """断开 YouTube 连接"""
        pass

    def _poll_messages(self):
        """轮询 YouTube 直播聊天消息"""
        try:
            import urllib.request
            import urllib.parse

            # 获取直播聊天 ID
            if not hasattr(self, '_live_chat_id'):
                url = f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails&id={self._video_id}&key={self._api_key}"
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read())
                    items = data.get('items', [])
                    if items:
                        self._live_chat_id = items[0]['liveStreamingDetails']['activeLiveChatId']
                    else:
                        logger.error("[youtube] 未找到直播")
                        return

            # 获取聊天消息
            url = f"https://www.googleapis.com/youtube/v3/liveChat/messages?liveChatId={self._live_chat_id}&part=snippet,authorDetails&key={self._api_key}"
            if self._next_page_token:
                url += f"&pageToken={self._next_page_token}"

            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                self._next_page_token = data.get('nextPageToken')

                for item in data.get('items', []):
                    snippet = item.get('snippet', {})
                    author = item.get('authorDetails', {})

                    if snippet.get('type') == 'textMessageEvent':
                        msg = DanmakuMessage(
                            platform="youtube",
                            user_name=author.get('displayName', 'Anonymous'),
                            content=snippet.get('displayMessage', ''),
                            user_id=author.get('channelId', ''),
                            room_id=self._video_id
                        )
                        self._emit_danmaku(msg)

        except Exception as e:
            logger.error(f"[youtube] 消息获取错误: {e}")


# ==================== Twitch 平台 ====================

class TwitchPlatform(LivePlatform):
    """Twitch 直播弹幕平台

    使用 IRC 协议连接到 Twitch 聊天。
    需要 OAuth token 和频道名。
    """

    @property
    def platform_name(self) -> str:
        return "twitch"

    def connect(self):
        """连接到 Twitch IRC"""
        try:
            import socket
        except ImportError:
            logger.error("[tsocket] socket 模块不可用")
            return

        token = self.config.extra.get("oauth_token", "")
        nickname = self.config.extra.get("nickname", "justinfan12345")
        channel = self.config.extra.get("channel", self.config.room_id)

        self._sock = socket.socket()
        self._sock.connect(("irc.chat.twitch.tv", 6667))

        if token:
            self._sock.send(f"PASS {token}\r\n".encode())
        self._sock.send(f"NICK {nickname}\r\n".encode())
        self._sock.send(f"JOIN #{channel}\r\n".encode())

        logger.info(f"[twitch] 已连接到 #{channel}")

    def disconnect(self):
        """断开 Twitch 连接"""
        if hasattr(self, '_sock') and self._sock:
            self._sock.close()

    def _poll_messages(self):
        """轮询 Twitch IRC 消息"""
        if not hasattr(self, '_sock'):
            return

        try:
            self._sock.settimeout(0.1)
            data = self._sock.recv(4096).decode('utf-8', errors='ignore')

            for line in data.split('\r\n'):
                if line.startswith('PING'):
                    self._sock.send('PONG :tmi.twitch.tv\r\n'.encode())
                    continue

                if 'PRIVMSG' in line:
                    # 解析消息
                    parts = line.split('PRIVMSG')
                    if len(parts) >= 2:
                        user = parts[0].split('!')[0].lstrip(':')
                        content = parts[1].split(':', 1)[1] if ':' in parts[1] else ''

                        msg = DanmakuMessage(
                            platform="twitch",
                            user_name=user,
                            content=content.strip(),
                            room_id=self.config.room_id
                        )
                        self._emit_danmaku(msg)

        except (TimeoutError, OSError):
            pass
        except Exception as e:
            logger.error(f"[twitch] 消息接收错误: {e}")


# ==================== 直播管理器 ====================

class LiveManager:
    """直播平台管理器

    管理多个直播平台连接，统一处理弹幕消息。
    提供弹幕 → LLM → TTS 流水线接口。
    """

    def __init__(self):
        self.platforms: Dict[str, LivePlatform] = {}
        self._on_danmaku_callback = None
        self._message_queue = []  # 消息队列
        self._queue_lock = threading.Lock()

    def set_danmaku_callback(self, callback: Callable[[DanmakuMessage], None]):
        """设置弹幕回调"""
        self._on_danmaku_callback = callback

    def add_platform(self, config: LiveConfig) -> bool:
        """添加直播平台

        Args:
            config: 直播配置

        Returns:
            是否添加成功
        """
        platform_map = {
            "bilibili": BilibiliPlatform,
            "youtube": YouTubePlatform,
            "twitch": TwitchPlatform,
        }

        platform_class = platform_map.get(config.platform)
        if not platform_class:
            logger.error(f"不支持的平台: {config.platform}")
            return False

        platform = platform_class(config, self._handle_danmaku)
        self.platforms[config.platform] = platform
        logger.info(f"已添加平台: {config.platform} (房间: {config.room_id})")
        return True

    def start_all(self):
        """启动所有平台连接"""
        for name, platform in self.platforms.items():
            if platform.config.enabled:
                platform.start()
                logger.info(f"已启动平台: {name}")

    def stop_all(self):
        """停止所有平台连接"""
        for name, platform in self.platforms.items():
            platform.stop()
            logger.info(f"已停止平台: {name}")

    def get_status(self) -> Dict[str, Any]:
        """获取所有平台状态"""
        return {
            name: {
                "connected": platform.is_connected,
                "room_id": platform.config.room_id,
            }
            for name, platform in self.platforms.items()
        }

    def _handle_danmaku(self, msg: DanmakuMessage):
        """处理弹幕消息"""
        with self._queue_lock:
            self._message_queue.append(msg)

        # 调用回调
        if self._on_danmaku_callback:
            try:
                self._on_danmaku_callback(msg)
            except Exception as e:
                logger.error(f"弹幕回调错误: {e}")

    def get_pending_messages(self, max_count: int = 10) -> List[DanmakuMessage]:
        """获取待处理的弹幕消息"""
        with self._queue_lock:
            messages = self._message_queue[:max_count]
            self._message_queue = self._message_queue[max_count:]
        return messages


# ==================== 工厂函数 ====================

def create_live_manager(configs: List[Dict[str, Any]]) -> LiveManager:
    """创建直播管理器

    Args:
        configs: 平台配置列表，每个配置包含 platform, room_id, enabled 等字段

    Returns:
        LiveManager 实例
    """
    manager = LiveManager()

    for config_data in configs:
        config = LiveConfig(
            platform=config_data.get("platform", ""),
            room_id=config_data.get("room_id", ""),
            enabled=config_data.get("enabled", True),
            extra=config_data.get("extra", {})
        )
        manager.add_platform(config)

    return manager
