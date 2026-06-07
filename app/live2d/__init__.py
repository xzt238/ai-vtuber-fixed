#!/usr/bin/env python3
"""
=====================================
Live2D 虚拟形象模块
=====================================

【模块功能概述】
本模块负责 Live2D 虚拟形象的管理和显示，包括：
1. Live2D 模型的加载和配置
2. 通过 Web 页面渲染和展示 Live2D 模型
3. 表情切换、动作播放、口型同步等交互功能

【Live2D 简介】
Live2D 是一种将 2D 插画"活起来"的技术，可以让平面角色呈现类似 3D 的立体效果。
本模块使用 pixi.js + pixi-live2d 在浏览器中渲染 Live2D Cubism 模型。

【核心技术栈】
- 后端：Python http.server（静态文件服务）
- 前端：pixi.js v7（WebGL 渲染）+ pixi-live2d（Live2D Cubism 渲染器）
- 交互：鼠标跟踪、点击响应、窗口自适应

【功能特性】
- 模型自动检测：在多个可能的路径中搜索 Live2D 模型文件
- 表情切换：支持开心/难过/惊讶/待机等预设表情
- 口型同步：通过 startSpeaking()/stopSpeaking() 控制说话动画
- 响应式布局：根据窗口大小自动缩放模型

【与其他模块的关系】
- 被 main.py 初始化，提供虚拟形象的 HTML 和控制接口
- 表情和口型控制被 web 模块调用，实现 AI 表情联动
- 模型文件存储在 web/assets/model/shizuku/ 目录下

【输入/输出】
- 输入：配置字典（启用状态、模型路径、端口等）
- 输出：HTTP 服务（提供 Live2D 渲染页面）和 JS 控制接口

支持:
- 本地模型加载
- 表情切换
- 口型同步
- 动作播放

作者: 咕咕嘎嘎
日期: 2026-03-27
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class Live2DModel:
    """
    【核心类】Live2D 虚拟形象管理器

    负责 Live2D 模型的检测、加载和 Web 服务。

    【模型检测策略】
        在多个可能的路径中搜索包含 .json 文件的目录：
        - 开发模式：搜索 app/web/static/assets/model/shizuku/ 等多个路径
        - 打包模式：搜索 sys._MEIPASS 下的多个路径（PyInstaller 打包后）

    【配置参数】
        enabled (bool): 是否启用 Live2D，默认 False
        model_path (str): 模型目录路径
        port (int): Web 服务端口，默认 8765
        auto_motion (bool): 是否启用自动动作，默认 True
        expressions (dict): 自定义表情映射
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【构造函数】初始化 Live2D 模型管理器

        【参数说明】
            config (Dict[str, Any]): 配置字典
        """
        self.config = config
        self.enabled = config.get("enabled", False)       # 是否启用
        self.model_path = config.get("model_path", "./app/web/assets/model/shizuku")  # 模型路径
        self.port = config.get("port", 8765)              # Web 服务端口
        self.auto_motion = config.get("auto_motion", True) # 自动动作
        self.expressions = config.get("expressions", {})   # 自定义表情
        self.model_loaded = False                          # 模型是否已加载
        self.current_expression = "idle"                   # 当前表情状态
    
    def is_available(self) -> bool:
        """
        【检测方法】检查 Live2D 模型是否可用

        【返回值】
            bool: True 表示模型文件存在且可用

        【检测逻辑】
            1. 检查 enabled 是否为 True
            2. 根据运行环境（开发/打包）确定可能的模型路径列表
            3. 在每个路径中搜索 .json 文件（Live2D 模型配置文件）
            4. 找到第一个有效路径后更新 self.model_path 并返回 True

        【路径搜索优先级】
            打包模式（sys.frozen=True）：
                _MEIPASS/web/assets/model/shizuku → _MEIPASS/app/web/... → exe同目录/web/...

            开发模式：
                base/app/web/static/assets/model/shizuku → base/app/web/assets/... →
                base/web/assets/... → ./web/assets/... → ./app/web/assets/...
        """
        if not self.enabled:
            return False
        
        import sys
        from pathlib import Path
        
        possible_paths = []
        
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后的环境
            meipass = Path(sys._MEIPASS)
            possible_paths = [
                meipass / "web" / "assets" / "model" / "shizuku",
                meipass / "app" / "web" / "assets" / "model" / "shizuku",
                meipass.parent / "web" / "assets" / "model" / "shizuku",
            ]
        else:
            # 开发环境
            # __file__ = app/live2d/__init__.py → .parent = app/live2d/ → .parent.parent = app/
            # 所以路径从 app/ 开始，不需要再加 app/ 前缀
            base = Path(__file__).parent.parent  # = app/
            project_root = base.parent           # = ai-vtuber-fixed/
            possible_paths = [
                base / "web" / "static" / "assets" / "model" / "shizuku",
                base / "web" / "assets" / "model" / "shizuku",
                project_root / "app" / "web" / "static" / "assets" / "model" / "shizuku",
                project_root / "app" / "web" / "assets" / "model" / "shizuku",
                project_root / "web" / "assets" / "model" / "shizuku",
            ]
        
        # 调试信息：打印所有搜索路径及其存在状态
        print(f"[Live2D] 检查目录:")
        for d in possible_paths:
            print(f"  {d} -> {d.exists()}")
        
        # 遍历路径，找到第一个包含 .json 文件的目录
        for p in possible_paths:
            if p.exists() and p.is_dir():
                if list(p.glob("*.json")):  # 检查目录下是否有 JSON 文件
                    self.model_path = str(p)
                    print(f"✅ 找到模型: {p}")
                    return True
        
        print(f"⚠️ 模型目录不存在")
        return False
    
    def load(self) -> bool:
        """
        【加载方法】加载 Live2D 模型

        【返回值】
            bool: True 表示加载成功

        【执行流程】
            1. 检查是否启用
            2. 调用 is_available() 确认模型文件存在
            3. 标记 model_loaded = True
        """
        if not self.enabled:
            print("Live2D 未启用")
            return False
        
        if self.is_available():
            print(f"✅ Live2D模型已就绪: {self.model_path}")
            self.model_loaded = True
            return True
        
        print(f"⚠️ 请放置Live2D模型到: {self.model_path}")
        return False
    
    def get_html(self) -> str:
        """
        【生成 HTML】获取 Live2D Web 渲染页面的完整 HTML 代码

        【返回值】
            str: 完整的 HTML 页面，包含：
                - pixi.js 和 pixi-live2d 的 CDN 引用
                - CSS 样式（渐变背景、控制按钮、说话指示器）
                - JavaScript 逻辑（模型加载、表情切换、口型动画、窗口自适应）

        【JavaScript 控制接口】
            window.setExpression(name)  —— 切换表情（"happy"/"sad"/"surprise"/"idle"）
            window.startSpeaking()      —— 开始说话动画
            window.stopSpeaking()       —— 停止说话动画

        【表情映射】
            happy → F00_00, sad → F00_03, surprise → F00_06, idle → F00_00
            （具体文件名取决于使用的 Live2D 模型）

        【模型加载策略】
            依次尝试 model.json、shizuku.model3.json、model.model3.json 三个文件名，
            第一个成功加载的即被使用。全部失败则显示占位提示。
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>咕咕嘎嘎 - Live2D</title>
    <!-- 引入 pixi.js（WebGL 渲染引擎）和 pixi-live2d（Live2D 渲染插件） -->
    <script src="https://cdn.jsdelivr.net/npm/pixi.js@7.3.2/dist/pixi.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/pixi-live2d@3.0.1/dist/pixi-live2d.min.js"></script>
    <style>
        * { margin: 0; padding: 0; }
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            overflow: hidden;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
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
            font-size: 24px;
            font-family: sans-serif;
        }
        /* 控制按钮区域（页面底部居中） */
        #controls {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
            z-index: 100;
        }
        .btn {
            padding: 10px 20px;
            background: rgba(255,255,255,0.9);
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        /* 说话状态指示器（右上角） */
        #speaking {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: rgba(255,107,157,0.9);
            color: white;
            border-radius: 20px;
            font-size: 14px;
            display: none;
        }
        #speaking.active { display: block; }
    </style>
</head>
<body>
    <div id="loading">加载模型中...</div>
    <div id="canvas-container"></div>
    <div id="speaking">🎤 说话中...</div>
    <!-- 表情切换按钮 -->
    <div id="controls">
        <button class="btn" onclick="setExpression('happy')">开心</button>
        <button class="btn" onclick="setExpression('sad')">难过</button>
        <button class="btn" onclick="setExpression('surprise')">惊讶</button>
        <button class="btn" onclick="setExpression('idle')">待机</button>
    </div>
    
    <script>
        let model = null;
        // 表情名称 → Live2D 表情文件名的映射
        const expressions = {
            happy: "F00_00",
            sad: "F00_03", 
            surprise: "F00_06",
            idle: "F00_00"
        };
        
        // 初始化 Pixi.js 应用（WebGL 渲染上下文）
        const app = new PIXI.Application({
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundColor: 0x664ba2,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true,
        });
        document.getElementById('canvas-container').appendChild(app.view);
        
        // 异步加载 Live2D 模型
        async function loadModel() {
            try {
                const modelUrl = './assets/model/';
                
                // 依次尝试多种模型文件名（不同 Live2D 模型的命名不同）
                const files = ['model.json', 'shizuku.model3.json', 'model.model3.json'];
                let loaded = false;
                
                for (const file of files) {
                    try {
                        model = await PIXI.live2d.Live2DModel.from(modelUrl + file, {
                            autoInteract: true  // 启用鼠标交互
                        });
                        loaded = true;
                        break;
                    } catch(e) {
                        console.log('尝试:', file, e.message);
                    }
                }
                
                if (!loaded) {
                    showPlaceholder();
                    return;
                }
                
                // 设置模型位置和缩放
                model.anchor.set(0.5, 0.5);  // 锚点设为中心
                model.position.set(window.innerWidth / 2, window.innerHeight / 2);
                
                // 根据窗口大小自适应缩放（基于最小边长/500 的比例）
                const scale = Math.min(window.innerWidth, window.innerHeight) / 500;
                model.scale.set(scale);
                
                app.stage.addChild(model);  // 添加到渲染舞台
                
                document.getElementById('loading').style.display = 'none';
                console.log('✅ Live2D模型加载成功');
                
                // 启用鼠标交互（点击模型触发事件）
                model.interactive = true;
                model.on('pointertap', () => {
                    console.log('点击模型');
                });
                
            } catch(e) {
                console.error('模型加载失败:', e);
                showPlaceholder();
            }
        }
        
        // 模型加载失败时显示占位提示
        function showPlaceholder() {
            document.getElementById('loading').innerHTML = '🐱<br><small>请放置Live2D模型到 assets/model/ 目录</small>';
        }
        
        // 【全局接口】切换表情 —— 可被外部 JS 调用
        window.setExpression = function(name) {
            if (!model) return;
            
            const exp = expressions[name];
            if (exp && model.internalModel) {
                try {
                    model.internalModel.motionManager.expressionManager?.setExpression(exp);
                } catch(e) {
                    console.log('切换表情:', name);
                }
            }
        };
        
        // 【全局接口】开始说话 —— 播放说话动作并显示指示器
        window.startSpeaking = function() {
            document.getElementById('speaking').classList.add('active');
            if (model && model.internalModel) {
                try {
                    model.internalModel.motionManager.startRandomMotion('TapBody');
                } catch(e) {}
            }
        };
        
        // 【全局接口】停止说话 —— 隐藏指示器
        window.stopSpeaking = function() {
            document.getElementById('speaking').classList.remove('active');
        };
        
        // 窗口大小改变时重新计算模型位置和缩放
        window.addEventListener('resize', () => {
            app.renderer.resize(window.innerWidth, window.innerHeight);
            if (model) {
                model.position.set(window.innerWidth / 2, window.innerHeight / 2);
                const scale = Math.min(window.innerWidth, window.innerHeight) / 500;
                model.scale.set(scale);
            }
        });
        
        // 页面加载完成后启动模型加载
        loadModel();
    </script>
</body>
</html>
"""
    
    def start_server(self):
        """
        【服务启动】启动 Live2D Web 服务

        【执行流程】
            1. 创建 web/live2d/ 目录和 assets/model/ 子目录
            2. 将 HTML 页面写入 index.html
            3. 写入 README.md（模型放置说明）
            4. 启动 Python HTTP 服务器（默认端口 8765）

        【服务访问】
            启动后可通过 http://localhost:8765 访问 Live2D 渲染页面。

        【注意】
            此方法会阻塞当前线程（serve_forever），适合独立启动。
            在主程序中应在线程中调用。
        """
        if not self.enabled:
            print("Live2D 未启用")
            return
        
        import http.server
        import socketserver
        
        # 创建目录结构
        web_dir = Path(__file__).parent / "web" / "live2d"
        web_dir.mkdir(parents=True, exist_ok=True)
        
        assets_dir = web_dir / "assets" / "model"
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入 HTML 页面
        html_path = web_dir / "index.html"
        html_path.write_text(self.get_html(), encoding="utf-8")
        
        # 写入模型放置说明
        readme = """# Live2D模型放置说明

将你的Live2D模型文件放入此目录：

```
assets/model/
├── model.json          # 或 model.model3.json
├── model.1024/
│   └── texture_00.png
└── expressions/
    └── ...
```

推荐模型来源：
- https://www.live2d.com/ (官方)
- https://hub.vroid.com/ (免费)

或者使用示例模型：
- https://github.com/guansss/pixi-live2d-demo
"""
        (web_dir / "README.md").write_text(readme)

        # 使用 SimpleHTTPRequestHandler 的 directory 参数指定服务目录
        # 不再使用 os.chdir()，避免影响整个进程的相对路径解析
        _web_dir = str(web_dir)  # 闭包捕获

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=_web_dir, **kwargs)

            def log_message(self, format, *args):
                pass  # 抑制每条请求的日志输出

        # 启动 TCP 服务器（allow_reuse_address 避免端口占用重启失败）
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", self.port), Handler) as httpd:
            print(f"\n🎭 Live2D服务: http://localhost:{self.port}")
            print(f"📁 模型目录: {assets_dir}")
            httpd.serve_forever()


# =====================================================================
# 模块测试
# =====================================================================

if __name__ == "__main__":
    config = {
        "enabled": True,
        "model_path": "./assets/model",
        "port": 8765
    }
    
    live2d = Live2DModel(config)
    live2d.start_server()
