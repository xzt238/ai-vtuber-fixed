#!/usr/bin/env python3
"""
=====================================
桌面宠物模式模块
=====================================

v1.9.52: 新增功能
将 Live2D 角色以桌面宠物的形式悬浮在桌面上。
无边框透明窗口，始终置顶，可拖拽移动，点击交互。

架构设计:
    使用 pywebview 创建无边框透明窗口，加载 Live2D 模型。
    窗口通过 pywebview 的 frameless + transparent 参数实现。
    右键菜单通过 JS → Python API 桥接实现。

交互设计:
    - 鼠标拖拽: 移动宠物位置
    - 左键点击: 触发打招呼/随机动作
    - 右键菜单: 切换模式/隐藏/退出
    - 双击: 打开完整 WebUI

配置来源: config.yaml → desktop_pet 节

作者: 咕咕嘎嘎
日期: 2026-05-01
"""

import os
import sys
import json
import threading
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import AIVTuber


# 桌面宠物 HTML 模板
PET_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>咕咕嘎嘎 - 桌面宠物</title>
    <script src="https://cdn.jsdelivr.net/npm/pixi.js@7.3.2/dist/pixi.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/pixi-live2d@3.0.1/dist/pixi-live2d.min.js"></script>
    <style>
        * { margin: 0; padding: 0; }
        html, body {
            background: transparent !important;
            overflow: hidden;
            height: 100vh;
            width: 100vw;
            /* pywebview transparent 需要 */
        }
        #canvas-container {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        #loading {
            position: absolute;
            color: white;
            font-size: 14px;
            font-family: sans-serif;
            text-shadow: 0 0 8px rgba(0,0,0,0.5);
        }
        /* 右键菜单 */
        .context-menu {
            display: none;
            position: fixed;
            background: rgba(30,30,40,0.95);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 4px 0;
            min-width: 160px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            z-index: 9999;
        }
        .context-menu.show { display: block; }
        .context-menu-item {
            padding: 8px 16px;
            color: #eee;
            font-size: 12px;
            cursor: pointer;
            font-family: -apple-system, sans-serif;
            transition: background 0.15s;
        }
        .context-menu-item:hover {
            background: rgba(255,255,255,0.1);
        }
        .context-menu-sep {
            height: 1px;
            background: rgba(255,255,255,0.1);
            margin: 4px 0;
        }
        /* 打招呼气泡 */
        .speech-bubble {
            position: fixed;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255,255,255,0.95);
            color: #333;
            padding: 8px 14px;
            border-radius: 12px;
            font-size: 13px;
            font-family: -apple-system, sans-serif;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
            max-width: 280px;
            text-align: center;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
            z-index: 9998;
        }
        .speech-bubble.show { opacity: 1; }
    </style>
</head>
<body>
    <div id="loading">🐱 加载中...</div>
    <div id="canvas-container"></div>
    <div class="speech-bubble" id="speech-bubble"></div>

    <!-- 右键菜单 -->
    <div class="context-menu" id="context-menu">
        <div class="context-menu-item" onclick="api.openWebUI()">🖥️ 打开主界面</div>
        <div class="context-menu-sep"></div>
        <div class="context-menu-item" onclick="api.triggerGreet()">👋 打招呼</div>
        <div class="context-menu-item" onclick="api.triggerRandomMotion()">🎲 随机动作</div>
        <div class="context-menu-sep"></div>
        <div class="context-menu-item" onclick="api.toggleAlwaysOnTop()">📌 窗口置顶</div>
        <div class="context-menu-item" onclick="api.hide()">🙈 隐藏宠物</div>
        <div class="context-menu-item" onclick="api.exit()">❌ 退出</div>
    </div>

    <script>
        let model = null;
        let pixiApp = null;

        // ===== 模型加载 =====
        async function loadModel() {
            try {
                const modelUrl = './assets/model/';
                const files = ['model.json', 'shizuku.model3.json', 'model.model3.json'];
                let loaded = false;

                for (const file of files) {
                    try {
                        model = await PIXI.live2d.Live2DModel.from(modelUrl + file, {
                            autoInteract: true
                        });
                        loaded = true;
                        break;
                    } catch(e) {
                        console.log('尝试:', file, e.message);
                    }
                }

                if (!loaded) {
                    document.getElementById('loading').innerHTML = '🐱<br><small>请放置Live2D模型</small>';
                    return;
                }

                // 设置模型位置和缩放
                model.anchor.set(0.5, 0.5);
                model.position.set(window.innerWidth / 2, window.innerHeight / 2);
                const scale = Math.min(window.innerWidth, window.innerHeight) / 400;
                model.scale.set(scale);

                pixiApp.stage.addChild(model);
                document.getElementById('loading').style.display = 'none';

                // 点击交互
                model.interactive = true;
                model.on('pointertap', () => {
                    if (typeof api !== 'undefined') {
                        api.onPetClick();
                    }
                });

                console.log('✅ 桌面宠物模型加载成功');

            } catch(e) {
                console.error('模型加载失败:', e);
                document.getElementById('loading').innerHTML = '🐱<br><small>模型加载失败</small>';
            }
        }

        // ===== Pixi.js 初始化 =====
        pixiApp = new PIXI.Application({
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundColor: 0x000000,
            backgroundAlpha: 0,  // 透明背景
            resolution: window.devicePixelRatio || 1,
            autoDensity: true,
            antialias: true,
        });
        document.getElementById('canvas-container').appendChild(pixiApp.view);

        // ===== 右键菜单 =====
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            const menu = document.getElementById('context-menu');
            menu.style.left = e.clientX + 'px';
            menu.style.top = e.clientY + 'px';
            menu.classList.add('show');
        });

        document.addEventListener('click', () => {
            document.getElementById('context-menu').classList.remove('show');
        });

        // ===== 气泡消息 =====
        let bubbleTimer = null;
        function showBubble(text) {
            const bubble = document.getElementById('speech-bubble');
            bubble.textContent = text;
            bubble.classList.add('show');
            if (bubbleTimer) clearTimeout(bubbleTimer);
            bubbleTimer = setTimeout(() => {
                bubble.classList.remove('show');
            }, 3000);
        }

        // ===== 窗口自适应 =====
        window.addEventListener('resize', () => {
            pixiApp.renderer.resize(window.innerWidth, window.innerHeight);
            if (model) {
                model.position.set(window.innerWidth / 2, window.innerHeight / 2);
                const scale = Math.min(window.innerWidth, window.innerHeight) / 400;
                model.scale.set(scale);
            }
        });

        // ===== 微动作定时器 =====
        let idleTimer = null;
        function startIdleMotion() {
            stopIdleMotion();
            function doIdle() {
                if (model && model.internalModel) {
                    try {
                        const motions = ['Idle', 'TapBody', 'Flick'];
                        const motion = motions[Math.floor(Math.random() * motions.length)];
                        model.internalModel.motionManager.startRandomMotion(motion);
                    } catch(e) {}
                }
                const nextDelay = 5000 + Math.random() * 10000; // 5-15秒
                idleTimer = setTimeout(doIdle, nextDelay);
            }
            idleTimer = setTimeout(doIdle, 5000);
        }

        function stopIdleMotion() {
            if (idleTimer) {
                clearTimeout(idleTimer);
                idleTimer = null;
            }
        }

        // ===== 表情和动作控制 =====
        window.setExpression = function(name) {
            if (!model || !model.internalModel) return;
            const expressions = {
                happy: "F00_00", sad: "F00_03",
                surprise: "F00_06", idle: "F00_00"
            };
            const exp = expressions[name];
            if (exp) {
                try {
                    model.internalModel.motionManager.expressionManager?.setExpression(exp);
                } catch(e) {}
            }
        };

        window.startSpeaking = function() {
            if (model && model.internalModel) {
                try {
                    model.internalModel.motionManager.startRandomMotion('TapBody');
                } catch(e) {}
            }
        };

        window.stopSpeaking = function() {};

        // ===== 启动 =====
        loadModel();
        startIdleMotion();

        // ===== pywebview API 桥接 =====
        // 这些函数通过 window.api 对象暴露给 Python
    </script>
</body>
</html>
"""


class PetAPI:
    """pywebview JS → Python API 桥接"""

    def __init__(self, pet_manager):
        self._pet = pet_manager

    def onPetClick(self):
        """宠物被点击"""
        click_action = self._pet._config.get("click_action", "greet")
        if click_action == "greet":
            self.triggerGreet()
        else:
            self.triggerRandomMotion()

    def triggerGreet(self):
        """触发打招呼"""
        greets = [
            "喵~", "你好呀！", "嗯？怎么了？", "嘻嘻~",
            "我在呢~", "想我了吗？", "嘿嘿~", "有什么事吗？"
        ]
        import random
        text = random.choice(greets)
        # 通过 WS 让 AI 说话
        self._pet._trigger_speech(text)
        return text

    def triggerRandomMotion(self):
        """触发随机动作"""
        if self._pet._window:
            try:
                self._pet._window.evaluate_js(
                    "if(model&&model.internalModel){try{model.internalModel.motionManager.startRandomMotion('TapBody');}catch(e){}}"
                )
            except Exception:
                pass

    def openWebUI(self):
        """打开完整 WebUI"""
        import webbrowser
        webbrowser.open(f"http://localhost:{self._pet._backend_port}")

    def toggleAlwaysOnTop(self):
        """切换窗口置顶"""
        if self._pet._window:
            try:
                self._pet._window.on_top = not getattr(self._pet._window, 'on_top', True)
            except Exception:
                pass

    def hide(self):
        """隐藏宠物窗口"""
        if self._pet._window:
            try:
                self._pet._window.hide()
            except Exception:
                pass

    def exit(self):
        """退出桌面宠物"""
        self._pet.stop()


class DesktopPetManager:
    """
    桌面宠物管理器

    管理桌面宠物窗口的创建、显示和交互。
    使用 pywebview 创建无边框透明窗口。
    """

    def __init__(self, app: "AIVTuber"):
        self.app = app
        self._config = app.config.config.get("desktop_pet", {})
        self.enabled = self._config.get("enabled", False)
        self._window = None
        self._thread = None
        self._running = False
        self._backend_port = app.config.config.get("web", {}).get("port", 12393)

    def start(self):
        """启动桌面宠物窗口"""
        if not self.enabled:
            print("[桌面宠物] 未启用 (config.yaml → desktop_pet.enabled)")
            return

        if self._running:
            return

        print("[桌面宠物] 启动中...")
        self._running = True
        self._thread = threading.Thread(target=self._run_window, daemon=True, name="desktop-pet")
        self._thread.start()

    def stop(self):
        """停止桌面宠物窗口"""
        self._running = False
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
        self._window = None
        print("[桌面宠物] 已停止")

    def _run_window(self):
        """在独立线程中运行 pywebview 窗口"""
        try:
            import webview
        except ImportError:
            print("[桌面宠物] pywebview 未安装，请运行: pip install pywebview")
            self._running = False
            return

        try:
            width = self._config.get("width", 400)
            height = self._config.get("height", 500)
            always_on_top = self._config.get("always_on_top", True)
            transparent = self._config.get("transparent", True)

            # 写入 HTML 文件
            html_path = Path(__file__).parent / "pet.html"
            html_path.write_text(PET_HTML_TEMPLATE, encoding="utf-8")

            api = PetAPI(self)

            self._window = webview.create_window(
                title="咕咕嘎嘎",
                url=str(html_path),
                width=width,
                height=height,
                frameless=True,
                transparent=transparent,
                always_on_top=always_on_top,
                resizable=False,
                min_size=(200, 300),
                js_api=api,
            )

            print(f"[桌面宠物] 窗口已创建 ({width}x{height})")
            webview.start(debug=False)

        except Exception as e:
            print(f"[桌面宠物] 窗口异常: {e}")
        finally:
            self._running = False

    def _trigger_speech(self, text: str):
        """通过 WebSocket 触发 AI 说话"""
        try:
            ws_server = getattr(self.app, '_lazy_modules', {}).get('ws')
            if not ws_server or not hasattr(ws_server, 'server'):
                return

            import json
            clients = getattr(ws_server.server, 'clients', {})
            for client_id, client in list(clients.items()):
                try:
                    ws_server.server.send_message(client, json.dumps({
                        "type": "text",
                        "text": text,
                        "proactive": True
                    }))
                except Exception:
                    pass
        except Exception as e:
            print(f"[桌面宠物] 触发说话失败: {e}")

    def show(self):
        """显示宠物窗口"""
        if self._window:
            try:
                self._window.show()
            except Exception:
                pass

    def show_bubble(self, text: str):
        """在宠物上方显示气泡"""
        if self._window:
            try:
                import json
                js_text = json.dumps(text)
                self._window.evaluate_js(f"showBubble({js_text})")
            except Exception:
                pass
