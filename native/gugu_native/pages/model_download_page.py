"""
模型下载页面 — 首次使用模型下载管理

从 settings_page.py 拆分出来，放在主导航栏与对话/训练/记忆同级。

支持下载类型:
  huggingface  — HuggingFace Hub snapshot_download（支持 local_dir 自定义路径）
  pip          — pip install 安装 Python 包
  torch_hub    — torch.hub.load 自动下载
  direct_url   — 直接 URL 下载单文件（带实时进度）
  zip_url      — 下载 zip 并解压（带实时进度）

模型分类:
  语音识别 — FunASR, Faster-Whisper
  语音合成 — GPT-SoVITS 系列、BigVGAN v2 声码器、ERes2NetV2 说话人验证
  语义检索 & 工具 — BGE-Base, RapidOCR, Silero VAD, fast-langdetect
"""

import os
import sys
import time
import shutil
import zipfile
import tempfile
import urllib.request
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

# 国内 HuggingFace 镜像
HF_MIRROR = 'https://hf-mirror.com'

from gugu_native.theme import get_colors


# ===== 模型下载列表配置 =====
MODEL_DOWNLOADS = [
    # ── 语音识别 (ASR) ──────────────────────────────────────
    {
        "id": "funasr",
        "name": "FunASR (语音识别)",
        "desc": "Paraformer-ZH 中文语音识别模型，约 900MB",
        "type": "huggingface",
        "repo_id": "funasr/paraformer-zh",
        "category": "语音识别",
    },
    {
        "id": "faster_whisper",
        "name": "Faster-Whisper (多语言ASR)",
        "desc": "Whisper-large-v3 多语言识别模型，约 1.5GB",
        "type": "huggingface",
        "repo_id": "Systran/faster-whisper-large-v3",
        "category": "语音识别",
    },

    # ── 语音合成 (TTS) ──────────────────────────────────────
    {
        "id": "gpt_sovits_s2g",
        "name": "GPT-SoVITS 语义解码器 (s2Gv3)",
        "desc": "SoVITS v3 语义解码器，语音合成核心模型，约 733MB",
        "type": "direct_url",
        "url": "https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s2Gv3.pth",
        "dest": "GPT-SoVITS/GPT_SoVITS/pretrained_models/s2Gv3.pth",
        "min_size": 100_000_000,
        "category": "语音合成",
    },
    {
        "id": "gpt_sovits_s1v",
        "name": "GPT-SoVITS GPT模型 (s1v3)",
        "desc": "GPT v3 预训练模型，语音合成核心模型，约 155MB",
        "type": "direct_url",
        "url": "https://hf-mirror.com/kevinwang676/GPT-SoVITS-v3/resolve/main/GPT_SoVITS/pretrained_models/s1v3.ckpt",
        "dest": "GPT-SoVITS/GPT_SoVITS/pretrained_models/s1v3.ckpt",
        "min_size": 100_000_000,
        "category": "语音合成",
    },
    {
        "id": "chinese_hubert",
        "name": "Chinese HuBERT (特征提取)",
        "desc": "中文语音特征提取模型，GPT-SoVITS 依赖，约 189MB",
        "type": "direct_url",
        "url": "https://hf-mirror.com/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin",
        "dest": "GPT-SoVITS/GPT_SoVITS/pretrained_models/chinese-hubert-base/pytorch_model.bin",
        "min_size": 100_000_000,
        "category": "语音合成",
    },
    {
        "id": "chinese_roberta",
        "name": "Chinese RoBERTa (BERT语义)",
        "desc": "中文语义模型，GPT-SoVITS 依赖，约 651MB",
        "type": "huggingface",
        "repo_id": "uer/chinese-roberta-wwm-ext-large",
        "local_dir": "GPT-SoVITS/GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large",
        "category": "语音合成",
    },
    {
        "id": "g2pw",
        "name": "G2PW (字音转换)",
        "desc": "中文多音字消歧模型，GPT-SoVITS 依赖，约 635MB",
        "type": "zip_url",
        "url": "https://www.modelscope.cn/models/kamiorinn/g2pw/resolve/master/G2PWModel_1.1.zip",
        "dest": "GPT-SoVITS/GPT_SoVITS/text/G2PWModel",
        "rename_from": "G2PWModel_1.1",
        "rename_to": "G2PWModel",
        "check_file": "GPT-SoVITS/GPT_SoVITS/text/G2PWModel/g2pW.onnx",
        "min_size": 1_000_000,
        "category": "语音合成",
    },
    {
        "id": "bigvgan_v2",
        "name": "BigVGAN v2 (声码器)",
        "desc": "GPT-SoVITS v3 声码器模型，v3 语音合成必需，约 450MB",
        "type": "huggingface",
        "repo_id": "nvidia/bigvgan_v2_24khz_100band_256x",
        "local_dir": "GPT-SoVITS/GPT_SoVITS/pretrained_models/models--nvidia--bigvgan_v2_24khz_100band_256x",
        "allow_patterns": ["config.json", "bigvgan_generator.pt"],
        "category": "语音合成",
    },
    {
        "id": "sv_eres2net",
        "name": "ERes2NetV2 (说话人验证)",
        "desc": "参考音频说话人验证模型，GPT-SoVITS 参考音频质量检测依赖，约 103MB",
        "type": "direct_url",
        "url": "https://hf-mirror.com/lj1995/GPT-SoVITS/resolve/main/sv/pretrained_eres2netv2w24s4ep4.ckpt",
        "dest": "GPT-SoVITS/GPT_SoVITS/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt",
        "min_size": 100_000_000,
        "category": "语音合成",
    },

    # ── 语义检索 & 工具 ─────────────────────────────────────
    {
        "id": "bge_base",
        "name": "BGE-Base (语义向量)",
        "desc": "记忆系统语义检索模型，约 400MB",
        "type": "huggingface",
        "repo_id": "BAAI/bge-base-zh-v1.5",
        "category": "语义检索 & 工具",
    },
    {
        "id": "rapidocr",
        "name": "RapidOCR (文字识别)",
        "desc": "本地OCR模型，约 50MB",
        "type": "pip",
        "package": "rapidocr_onnxruntime",
        "category": "语义检索 & 工具",
    },
    {
        "id": "silero_vad",
        "name": "Silero VAD (语音活动检测)",
        "desc": "实时语音端点检测模型，约 2MB",
        "type": "torch_hub",
        "category": "语义检索 & 工具",
    },
    {
        "id": "fast_langdetect",
        "name": "fast-langdetect (语种检测)",
        "desc": "多语言语种检测工具，GPT-SoVITS 多语言推理依赖，首次使用时自动下载模型",
        "type": "pip",
        "package": "fast-langdetect>=0.3.1",
        "category": "语义检索 & 工具",
    },
]


def _check_model_downloaded(mdl: dict) -> bool:
    """检测模型是否已下载 — 多策略检测

    支持类型: huggingface / pip / torch_hub / direct_url / zip_url / chattts
    """
    mdl_type = mdl["type"]
    mdl_id = mdl["id"]

    if mdl_type == "huggingface":
        repo_id = mdl.get("repo_id", "")
        local_dir = mdl.get("local_dir")

        # 优先检查 local_dir（自定义路径模型如 chinese-roberta）
        if local_dir:
            full_path = os.path.join(PROJECT_DIR, local_dir)
            if os.path.isdir(full_path) and os.listdir(full_path):
                # 目录非空，但还需要确认有实际模型文件（排除只有 .git 的情况）
                has_model = False
                for f in os.listdir(full_path):
                    if f.endswith(('.bin', '.safetensors', '.onnx', '.pth', '.ckpt')):
                        has_model = True
                        break
                    # 包含 config.json 也算（完整 repo 下载）
                    if f == 'config.json':
                        has_model = True
                        break
                if has_model:
                    return True

        # 策略1 (最可靠): import 检测 — 对应的 Python 库能导入就说明模型已下载
        import_map = {
            "funasr": "funasr",
            "faster_whisper": "faster_whisper",
            "bge_base": "sentence_transformers",
        }
        import_name = import_map.get(mdl_id)
        if import_name and not local_dir:
            # 有 local_dir 的模型不能用 import 检测（import 成功不代表本地文件在正确位置）
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

    elif mdl_type == "direct_url":
        # 检查目标文件是否存在且大于最小尺寸
        dest = os.path.join(PROJECT_DIR, mdl["dest"])
        min_size = mdl.get("min_size", 0)
        if os.path.exists(dest):
            try:
                return os.path.getsize(dest) > min_size
            except OSError:
                pass
        return False

    elif mdl_type == "zip_url":
        # 检查解压后的关键文件是否存在
        check_file = mdl.get("check_file")
        if check_file:
            full_path = os.path.join(PROJECT_DIR, check_file)
            min_size = mdl.get("min_size", 0)
            if os.path.exists(full_path):
                try:
                    return os.path.getsize(full_path) > min_size
                except OSError:
                    pass
        return False

    elif mdl_type == "pip":
        # 策略: 尝试 import 检测
        package_map = {
            "rapidocr": "rapidocr_onnxruntime",
            "fast_langdetect": "fast_langdetect",
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
    """模型下载线程

    支持: huggingface / pip / torch_hub / direct_url / zip_url / chattts
    direct_url 和 zip_url 类型支持实时下载进度。
    """
    progress = Signal(str, int)          # model_id, percent
    finished = Signal(str, bool, str)    # model_id, success, message

    def __init__(self, model_info):
        super().__init__()
        self.model_info = model_info

    @staticmethod
    def _apply_hf_mirror(url):
        """对 HuggingFace 官方 URL 替换为国内镜像"""
        if "huggingface.co" in url and "hf-mirror.com" not in url:
            return url.replace("huggingface.co", "hf-mirror.com")
        return url

    def _download_file_with_progress(self, url, dest, mdl_id):
        """下载单个文件，实时报告进度。"""
        url = self._apply_hf_mirror(url)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            done = 0
            with open(dest, 'wb') as f:
                while True:
                    chunk = resp.read(65536)  # 64KB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total > 0:
                        # 最多报 95%，留 5% 给后续处理
                        self.progress.emit(mdl_id, min(int(done / total * 95), 95))

            # 验证下载完整性
            if total > 0 and done < total:
                raise IOError(f"下载不完整: {done}/{total} bytes")

        self.progress.emit(mdl_id, 98)

    def _set_env(self, key, value):
        """临时设置环境变量，返回旧值（None 表示之前不存在）"""
        old = os.environ.get(key)
        os.environ[key] = value
        return old

    def _restore_env(self, key, old_value):
        """恢复环境变量"""
        if old_value is not None:
            os.environ[key] = old_value
        elif key in os.environ:
            del os.environ[key]

    def run(self):
        mdl = self.model_info
        mdl_type = mdl["type"]
        mdl_id = mdl["id"]

        try:
            if mdl_type == "huggingface":
                from huggingface_hub import snapshot_download

                # 确定下载目标目录
                local_dir_cfg = mdl.get("local_dir")
                if local_dir_cfg:
                    local_dir = os.path.join(PROJECT_DIR, local_dir_cfg)
                else:
                    local_dir = os.path.join(PROJECT_DIR, "app", "cache", f"{mdl_id}_models")
                os.makedirs(local_dir, exist_ok=True)

                self.progress.emit(mdl_id, 10)

                # 设置 HF 镜像（国内加速）
                old_endpoint = self._set_env('HF_ENDPOINT', HF_MIRROR)
                try:
                    kwargs = dict(
                        repo_id=mdl["repo_id"],
                        local_dir=local_dir,
                    )
                    # 支持仅下载指定文件（避免下载整个 repo 中不需要的大文件）
                    allow_patterns = mdl.get("allow_patterns")
                    if allow_patterns:
                        kwargs["allow_patterns"] = allow_patterns
                    snapshot_download(**kwargs)
                finally:
                    self._restore_env('HF_ENDPOINT', old_endpoint)

                self.finished.emit(mdl_id, True, "下载完成")

            elif mdl_type == "direct_url":
                dest = os.path.join(PROJECT_DIR, mdl["dest"])
                self._download_file_with_progress(mdl["url"], dest, mdl_id)
                self.finished.emit(mdl_id, True, "下载完成")

            elif mdl_type == "zip_url":
                # 先下载 zip 到临时目录
                zip_path = os.path.join(tempfile.gettempdir(), f'_gugu_dl_{mdl_id}.zip')
                self._download_file_with_progress(mdl["url"], zip_path, mdl_id)

                # 解压
                dest = os.path.join(PROJECT_DIR, mdl["dest"])
                parent = os.path.dirname(os.path.abspath(dest))
                os.makedirs(parent, exist_ok=True)

                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(parent)

                # 重命名（如需要）
                rename_from = mdl.get("rename_from")
                rename_to = mdl.get("rename_to")
                if rename_from and rename_to:
                    src = os.path.join(parent, rename_from)
                    dst = os.path.join(parent, rename_to)
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    os.rename(src, dst)

                # 清理 zip
                try:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                except OSError:
                    pass

                self.progress.emit(mdl_id, 100)
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
        main_layout.setSpacing(8)

        # 标题
        title = TitleLabel("模型下载")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        main_layout.addWidget(title)

        hint = CaptionLabel("首次使用需要下载以下模型，点击「下载」按钮自动下载到本地。所有 HuggingFace 下载均使用国内镜像源。")
        main_layout.addWidget(hint)

        main_layout.addSpacing(8)

        # 按分类渲染模型卡片
        current_category = None
        for mdl in MODEL_DOWNLOADS:
            cat = mdl.get("category", "")
            if cat != current_category:
                current_category = cat
                # 分类标题
                c = get_colors()
                cat_label = BodyLabel(f"  {cat}")
                cat_label.setStyleSheet(f"""
                    color: {c.text_secondary};
                    font-size: 14px;
                    font-weight: 600;
                    padding: 12px 0 4px 0;
                """)
                main_layout.addWidget(cat_label)

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
