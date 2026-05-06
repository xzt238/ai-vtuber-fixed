"""
模型下载页面 — 首次使用模型下载管理

从 settings_page.py 拆分出来，放在主导航栏与对话/训练/记忆同级。

支持:
- FunASR (语音识别)
- Faster-Whisper (多语言 ASR)
- BGE-Base (语义向量)
- RapidOCR (文字识别)
- Silero VAD (语音活动检测)
- 下载状态检测 + 进度显示 + 重新下载
"""

import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread

from qfluentwidgets import (
    PushButton, TitleLabel, BodyLabel, CaptionLabel,
    CardWidget, FluentIcon, InfoBar, InfoBarPosition,
    HeaderCardWidget, ScrollArea, ProgressRing
)

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gugu_native.theme import get_colors


# ===== 模型下载列表配置 =====
MODEL_DOWNLOADS = [
    {
        "id": "funasr",
        "name": "FunASR (语音识别)",
        "desc": "Paraformer-ZH 中文语音识别模型，约 900MB",
        "type": "huggingface",
        "repo_id": "funasr/paraformer-zh",
    },
    {
        "id": "faster_whisper",
        "name": "Faster-Whisper (多语言ASR)",
        "desc": "Whisper-large-v3 多语言识别模型，约 1.5GB",
        "type": "huggingface",
        "repo_id": "Systran/faster-whisper-large-v3",
    },
    {
        "id": "bge_base",
        "name": "BGE-Base (语义向量)",
        "desc": "记忆系统语义检索模型，约 400MB",
        "type": "huggingface",
        "repo_id": "BAAI/bge-base-zh-v1.5",
    },
    {
        "id": "rapidocr",
        "name": "RapidOCR (文字识别)",
        "desc": "本地OCR模型，约 50MB",
        "type": "pip",
        "package": "rapidocr_onnxruntime",
    },
    {
        "id": "silero_vad",
        "name": "Silero VAD (语音活动检测)",
        "desc": "实时语音端点检测模型，约 2MB",
        "type": "torch_hub",
    },
]


def _check_model_downloaded(mdl: dict) -> bool:
    """检测模型是否已下载 — 多策略检测

    v1.9.81 修复: huggingface 模型缓存格式不统一，
    FunASR/Faster-Whisper 等通过自身库下载不走 snapshot_download，
    所以统一用 import 检测（最可靠）+ 目录检测（兜底）
    """
    mdl_type = mdl["type"]
    mdl_id = mdl["id"]

    if mdl_type == "huggingface":
        repo_id = mdl.get("repo_id", "")

        # 策略1 (最可靠): import 检测 — 对应的 Python 库能导入就说明模型已下载
        import_map = {
            "funasr": "funasr",
            "faster_whisper": "faster_whisper",
            "bge_base": "sentence_transformers",
        }
        import_name = import_map.get(mdl_id)
        if import_name:
            try:
                __import__(import_name)
                return True
            except ImportError:
                pass

        # 策略2: 检查 huggingface_hub 标准缓存 (models--xxx 格式)
        if repo_id:
            # 项目级缓存 (HF_HOME=.cache/huggingface)
            cache_dir = os.path.join(PROJECT_DIR, ".cache", "huggingface", "hub")
            cache_model_dir = os.path.join(cache_dir, f"models--{repo_id.replace('/', '--')}")
            if os.path.exists(cache_model_dir) and os.listdir(cache_model_dir):
                return True

            # 用户目录缓存 (~/.cache/huggingface/hub)
            user_cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
            user_cache_model_dir = os.path.join(user_cache_dir, f"models--{repo_id.replace('/', '--')}")
            if os.path.exists(user_cache_model_dir) and os.listdir(user_cache_model_dir):
                return True

        # 策略3: 检查 modelscope 缓存 (BGE 等可能走 modelscope 下载)
        modelscope_patterns = {
            "bge_base": "bge-base-zh",
        }
        pattern = modelscope_patterns.get(mdl_id)
        if pattern:
            ms_dir = os.path.join(PROJECT_DIR, ".cache", "modelscope")
            if os.path.exists(ms_dir):
                for root, dirs, files in os.walk(ms_dir):
                    for d in dirs:
                        if pattern in d.lower():
                            return True

        # 策略4: 检查项目本地目录 (旧版下载路径)
        local_paths = [
            os.path.join(PROJECT_DIR, "app", "cache", f"{mdl_id}_models"),
            os.path.join(PROJECT_DIR, "app", "cache", mdl_id.replace("_", "")),
        ]
        for p in local_paths:
            if os.path.exists(p) and os.path.isdir(p) and os.listdir(p):
                return True

    elif mdl_type == "pip":
        # 策略: 尝试 import 检测
        package_map = {
            "rapidocr": "rapidocr_onnxruntime",
        }
        import_name = package_map.get(mdl_id, mdl.get("package", mdl_id))
        try:
            __import__(import_name.replace("-", "_"))
            return True
        except ImportError:
            pass

    elif mdl_type == "torch_hub":
        # 策略1: 检查 torch hub 缓存 (snakers4_silero-vad_master 格式)
        hub_dir = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub")
        if os.path.exists(hub_dir):
            for d in os.listdir(hub_dir):
                d_lower = d.lower()
                if "silero" in d_lower and "vad" in d_lower:
                    return True

        # 策略2: import 检测 (如果 torch.hub.load 过就会缓存)
        try:
            import torch
            hub_dir = torch.hub.get_dir()
            if os.path.exists(os.path.join(hub_dir, "snakers4_silero-vad_master")):
                return True
        except Exception:
            pass

    return False


class _DownloadWorker(QThread):
    """模型下载线程"""
    progress = Signal(str, int)          # model_id, percent
    finished = Signal(str, bool, str)    # model_id, success, message

    def __init__(self, model_info):
        super().__init__()
        self.model_info = model_info

    def run(self):
        mdl = self.model_info
        mdl_type = mdl["type"]
        mdl_id = mdl["id"]

        try:
            if mdl_type == "huggingface":
                from huggingface_hub import snapshot_download
                # 下载到项目本地目录
                local_dir = os.path.join(PROJECT_DIR, "app", "cache", f"{mdl_id}_models")
                os.makedirs(local_dir, exist_ok=True)

                self.progress.emit(mdl_id, 10)

                snapshot_download(
                    repo_id=mdl["repo_id"],
                    local_dir=local_dir,
                )
                self.finished.emit(mdl_id, True, "下载完成")

            elif mdl_type == "pip":
                import subprocess
                self.progress.emit(mdl_id, 10)
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", mdl["package"]],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    self.finished.emit(mdl_id, True, "安装完成")
                else:
                    self.finished.emit(mdl_id, False, result.stderr[:200] if result.stderr else "安装失败")

            elif mdl_type == "torch_hub":
                import torch
                self.progress.emit(mdl_id, 10)
                model, _ = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    trust_repo=True
                )
                self.finished.emit(mdl_id, True, "下载完成")

            else:
                self.finished.emit(mdl_id, False, f"不支持的类型: {mdl_type}")

        except Exception as e:
            self.finished.emit(mdl_id, False, str(e)[:300])


class ModelDownloadPage(ScrollArea):
    """模型下载页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modelDownloadPage")
        self._download_worker = None
        self._model_items = {}
        self._init_ui()

    def _init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.setWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # 标题
        title = TitleLabel("模型下载")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        main_layout.addWidget(title)

        hint = CaptionLabel("首次使用需要下载以下模型，点击「下载」按钮自动下载到本地")
        main_layout.addWidget(hint)

        # 模型卡片
        for mdl in MODEL_DOWNLOADS:
            card = self._create_model_card(mdl)
            main_layout.addWidget(card)

        main_layout.addStretch(1)

    def _create_model_card(self, mdl: dict) -> CardWidget:
        """创建单个模型下载卡片"""
        c = get_colors()
        is_downloaded = _check_model_downloaded(mdl)

        card = CardWidget()
        card.setStyleSheet(f"""
            CardWidget {{
                background-color: {c.card_bg};
                border: 1px solid {c.card_border};
                border-radius: 12px;
                padding: 16px;
            }}
            CardWidget:hover {{
                background-color: {c.card_bg_hover};
                border: 1px solid {c.card_border_hover};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # 第一行: 模型名称 + 状态标签 + 下载按钮
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        # 模型图标
        type_icons = {
            "huggingface": FluentIcon.GLOBE,
            "pip": FluentIcon.DOWNLOAD,
            "torch_hub": FluentIcon.SETTING,
        }
        icon_label = QLabel()
        # 简化: 用文字代替图标

        name_label = BodyLabel(mdl["name"])
        name_label.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {c.text_primary};")
        row1.addWidget(name_label)

        row1.addStretch()

        # 状态标签
        status_label = CaptionLabel("已下载" if is_downloaded else "未下载")
        status_label.setStyleSheet(f"""
            color: {'#37b24d' if is_downloaded else '#f03e3e'};
            font-weight: 500;
            padding: 3px 12px;
            background-color: {'#1a3a2a' if is_downloaded else '#3a1a1a'};
            border-radius: 10px;
        """)
        row1.addWidget(status_label)

        # 下载按钮
        if is_downloaded:
            dl_btn = PushButton("已就绪")
            dl_btn.setEnabled(False)
            dl_btn.setFixedWidth(90)
        else:
            dl_btn = PushButton("下载")
            dl_btn.setFixedWidth(90)
            dl_btn.setStyleSheet(f"""
                PushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #37b24d, stop:1 #2f9e44);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 500;
                }}
                PushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2f9e44, stop:1 #2b8a3e);
                }}
            """)
        dl_btn.clicked.connect(lambda checked, m=mdl: self._on_download_model(m))
        row1.addWidget(dl_btn)

        layout.addLayout(row1)

        # 第二行: 描述
        desc_label = CaptionLabel(mdl["desc"])
        desc_label.setStyleSheet(f"color: {c.text_muted};")
        layout.addWidget(desc_label)

        # 第三行: 进度条（默认隐藏）
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setVisible(False)
        progress_bar.setFixedHeight(4)
        layout.addWidget(progress_bar)

        self._model_items[mdl["id"]] = {
            "card": card,
            "status_label": status_label,
            "download_btn": dl_btn,
            "progress_bar": progress_bar,
            "info": mdl,
        }

        return card

    def _on_download_model(self, mdl: dict):
        """开始下载模型"""
        model_id = mdl["id"]
        item_info = self._model_items.get(model_id)
        if not item_info:
            return

        btn = item_info["download_btn"]
        status = item_info["status_label"]
        progress = item_info["progress_bar"]

        # 更新 UI 状态
        btn.setEnabled(False)
        btn.setText("下载中...")
        status.setText("下载中...")
        c = get_colors()
        status.setStyleSheet(f"""
            color: #f59f00;
            font-weight: 500;
            padding: 3px 12px;
            background-color: {c.warning_bg};
            border-radius: 10px;
        """)
        progress.setVisible(True)
        progress.setValue(0)

        # 启动下载线程
        worker = _DownloadWorker(mdl)
        worker.progress.connect(self._on_download_progress)
        worker.finished.connect(self._on_download_finished)
        worker.start()
        self._download_worker = worker

    def _on_download_progress(self, model_id: str, percent: int):
        """下载进度更新"""
        item_info = self._model_items.get(model_id)
        if item_info:
            item_info["progress_bar"].setValue(percent)

    def _on_download_finished(self, model_id: str, success: bool, message: str):
        """下载完成回调"""
        item_info = self._model_items.get(model_id)
        if not item_info:
            return

        btn = item_info["download_btn"]
        status = item_info["status_label"]
        progress = item_info["progress_bar"]
        c = get_colors()

        progress.setVisible(False)

        if success:
            status.setText("已下载")
            status.setStyleSheet(f"""
                color: #37b24d;
                font-weight: 500;
                padding: 3px 12px;
                background-color: #1a3a2a;
                border-radius: 10px;
            """)
            btn.setText("已就绪")
            btn.setEnabled(False)
            btn.setStyleSheet("")  # 清除自定义样式，使用默认禁用样式
            InfoBar.success(
                title="下载完成",
                content=f"{item_info['info']['name']} {message}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
        else:
            status.setText("下载失败")
            status.setStyleSheet(f"""
                color: #f03e3e;
                font-weight: 500;
                padding: 3px 12px;
                background-color: #3a1a1a;
                border-radius: 10px;
            """)
            btn.setText("重试")
            btn.setEnabled(True)
            btn.setStyleSheet(f"""
                PushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #f03e3e, stop:1 #e03131);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 500;
                }}
                PushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e03131, stop:1 #c92a2a);
                }}
            """)
            InfoBar.error(
                title="下载失败",
                content=message,
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def refresh_statuses(self):
        """刷新所有模型的下载状态"""
        for mdl_id, item_info in self._model_items.items():
            mdl = item_info["info"]
            is_downloaded = _check_model_downloaded(mdl)

            btn = item_info["download_btn"]
            status = item_info["status_label"]
            c = get_colors()

            if is_downloaded:
                status.setText("已下载")
                status.setStyleSheet(f"""
                    color: #37b24d;
                    font-weight: 500;
                    padding: 3px 12px;
                    background-color: #1a3a2a;
                    border-radius: 10px;
                """)
                btn.setText("已就绪")
                btn.setEnabled(False)
                btn.setStyleSheet("")
            else:
                status.setText("未下载")
                status.setStyleSheet(f"""
                    color: #f03e3e;
                    font-weight: 500;
                    padding: 3px 12px;
                    background-color: #3a1a1a;
                    border-radius: 10px;
                """)
                btn.setText("下载")
                btn.setEnabled(True)
                btn.setStyleSheet(f"""
                    PushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #37b24d, stop:1 #2f9e44);
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 16px;
                        font-weight: 500;
                    }}
                    PushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #2f9e44, stop:1 #2b8a3e);
                    }}
                """)

    # ========== 主题刷新（v1.9.80）==========

    def refresh_theme(self):
        """主题切换时刷新卡片样式"""
        c = get_colors()
        for mdl_id, item_info in self._model_items.items():
            card = item_info["card"]
            card.setStyleSheet(f"""
                CardWidget {{
                    background-color: {c.card_bg};
                    border: 1px solid {c.card_border};
                    border-radius: 12px;
                    padding: 16px;
                }}
                CardWidget:hover {{
                    background-color: {c.card_bg_hover};
                    border: 1px solid {c.card_border_hover};
                }}
            """)
            # 刷新名称标签颜色
            for child in card.findChildren(BodyLabel):
                child.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {c.text_primary};")
            for child in card.findChildren(CaptionLabel):
                child.setStyleSheet(f"color: {c.text_muted};")
