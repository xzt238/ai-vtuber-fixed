# -*- coding: utf-8 -*-
"""
GPT-SoVITS 轻量化封装
支持音色克隆的 TTS 引擎

已知问题（待解决）：
- GPT-SoVITS CNHuBERT 在 pipeline 重置时可能报告张量维度错误
  （Expected [4,33] got [4,28]），但 TTS 仍可正常工作
  原因：FunASR paraformer ASR 模型内部 CNHuBERT checkpoint 维度不匹配
  解决：v1.4.64 在 app/web/__init__.py 中增加了 faster-whisper fallback
        当 FunASR 返回空/失败时自动切换到 faster-whisper
"""
import os
import sys
import time
import json
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
from contextlib import redirect_stdout, redirect_stderr, contextmanager
import io as _io

# 添加 GPT-SoVITS 到路径
GPT_SOVITS_DIR = Path(__file__).parent.parent.parent / "GPT-SoVITS"
sys.path.insert(0, str(GPT_SOVITS_DIR))
sys.path.insert(0, str(GPT_SOVITS_DIR / "GPT_SoVITS"))
# 添加 eres2net 路径（sv.py 需要）
sys.path.insert(0, str(GPT_SOVITS_DIR / "GPT_SoVITS" / "eres2net"))

# 设置 BERT 模型路径（通过环境变量传递给 chinese2.py）
BERT_MODEL_PATH = str(GPT_SOVITS_DIR / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large")
os.environ["GPT_SOVITS_BERT_PATH"] = BERT_MODEL_PATH

# 设置工作目录（必须是 GPT-SoVITS/ 根目录，因为 TTS.py 会用 now_dir + "GPT_SoVITS/..." 构建路径）
os.chdir(str(GPT_SOVITS_DIR))

# 项目配置目录
PROJECTS_DIR = GPT_SOVITS_DIR / "data" / "web_projects"

# 上次使用的音色持久化文件（用于启动时只预热上次音色）
LAST_PROJECT_FILE = Path(__file__).parent.parent.parent / "app" / "cache" / "last_tts_project.json"


class _SuppressVerboseOutput:
    """
    上下文管理器：临时抑制 stdout/stderr 的冗余输出
    
    GPT-SoVITS 的 TTS() 初始化会通过 load_state_dict(strict=False) 打印
    大量 _IncompatibleKeys 信息（missing/unexpected keys），这些对用户无意义。
    用此上下文管理器在模型加载期间静默，加载完成后输出精简摘要。
    
    注意：异常信息仍会正常抛出（因为异常走 stderr 且不被 except 捕获）。
    """

    def __enter__(self):
        self._stdout = _io.StringIO()
        self._stderr = _io.StringIO()
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr
        # 如果有异常，把捕获的输出刷出来方便调试
        if exc_type is not None:
            captured_out = self._stdout.getvalue()
            captured_err = self._stderr.getvalue()
            if captured_out:
                self._orig_stdout.write(captured_out)
            if captured_err:
                self._orig_stderr.write(captured_err)
        return False  # 不吞异常


class GPTSoVITSEngine:
    """
    【核心类】GPT-SoVITS 轻量化推理引擎

    实现文本转语音（TTS）功能，支持音色克隆。
    基于 GPT-SoVITS v3/v4 模型，通过参考音频实现个性化音色合成。

    【单例模式】
    使用 __new__ 实现单例模式，确保全局只有一个引擎实例，
    避免多次初始化导致的重复模型加载和显存浪费。

    【延迟初始化】
    模型加载发生在首次 speak() 调用时（_lazy_init），而非构造时。
    这样可以加速系统启动，并确保配置已完全就绪。

    【多项目支持】
    支持同时管理多个训练项目（project），每个项目有独立的：
    - 参考音频（ref_audio）
    - 参考文本（ref_text）
    - 已训练模型路径（trained_gpt、trained_sovits）

    通过 set_project() 切换当前活跃项目。

    【版本兼容性】
    - v1/v2/v3/v4 模型格式各有不同，引擎会自动检测并应用对应配置
    - LoRA 模型使用特殊 ZIP 格式，需要 process_ckpt 模块辅助加载
    - fallback 机制：在版本不匹配时尝试降级到预训练底模

    【静音处理】
    当合成失败或音频过短时，生成 1 秒静音（24000 采样点）作为兜底，
    避免下游处理（WebSocket 播放）因空音频而报错。

    【输入/输出】
    - 输入：要合成的文本（str） + 可选的参考音频/项目配置
    - 输出：WAV 音频文件路径（str）
    """

    _instance = None

    def __new__(cls, config: dict = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: dict = None):
        import traceback as tb
        try:
            print(f"[GPT-SoVITS] __init__ called with config={config}")
            if self._initialized:
                if config:
                    self.config.update(config)
                    # 如果传入了新的 project 且与当前不同，需要切换项目
                    new_project = config.get('project')
                    if new_project and new_project != self.current_project:
                        self.set_project(new_project)
                print("[GPT-SoVITS] Already initialized, returning")
                return

            self.config = config or {}
            self.device = self.config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
            self.is_half = self.config.get('is_half', self.device == 'cuda')

            # 模型路径配置
            self.root_dir = GPT_SOVITS_DIR
            self.gpt_path = self.config.get('gpt_path',
                str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/s1v3.ckpt"))
            self.sovits_path = self.config.get('sovits_path',
                str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/s2Gv3.pth"))
            self.cnhubert_path = self.config.get('cnhubert_path',
                str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/chinese-hubert-base"))
            self.bert_path = self.config.get('bert_path',
                str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"))

            # 推理参数
            self.top_k = self.config.get('top_k', 15)
            self.top_p = self.config.get('top_p', 1.0)
            self.temperature = self.config.get('temperature', 1.0)
            self.speed = self.config.get('speed', 1.0)
            self.version = self.config.get('version', 'v3')
            self.parallel_infer = self.config.get('parallel_infer', False)

            # 项目配置（支持多音色）
            self.current_project = self.config.get('project', 'default')
            self._project_config = self._load_project_config(self.current_project)

            # 从项目配置更新模型路径（与 set_project 逻辑一致）
            config_version = self._project_config.get("version")
            if config_version in ("v1", "v2", "v3", "v4"):
                self.version = config_version

            trained_gpt = self._project_config.get("trained_gpt")
            trained_sovits = self._project_config.get("trained_sovits")
            if trained_sovits:
                self.sovits_path = trained_sovits
            if trained_gpt:
                self.gpt_path = trained_gpt

            self.tts_pipeline = None
            self._initialized = True
            print("[GPT-SoVITS] __init__ completed successfully")
        except Exception as e:
            print(f"[GPT-SoVITS] __init__ error: {e}")
            tb.print_exc()
            raise

    # ========== 项目配置管理 ==========

    def _get_project_dir(self, project_name: str) -> Path:
        """
        【功能说明】获取指定项目的工作目录路径

        【参数说明】
            project_name (str): 项目名称

        【返回值】
            Path: 项目目录的 Path 对象，格式为 {PROJECTS_DIR}/{project_name}
        """
        return PROJECTS_DIR / project_name

    def _get_project_config_path(self, project_name: str) -> Path:
        """
        【功能说明】获取指定项目的配置文件（config.json）路径

        【参数说明】
            project_name (str): 项目名称

        【返回值】
            Path: 配置文件路径，格式为 {PROJECTS_DIR}/{project_name}/config.json
        """
        return self._get_project_dir(project_name) / "config.json"

    def _check_sovits_config(self, sovits_path: str) -> bool:
        """检查 SoVITS 模型是否可以加载（兼容 LoRA 格式和标准格式）

        Args:
            sovits_path: SoVITS 模型文件路径

        Returns:
            True 表示文件有效可用，False 表示文件不存在或读取失败

        注意：GPT-SoVITS 的 LoRA 文件使用特殊格式（前2字节是版本标识而非标准pickle头），
              必须使用官方的 load_sovits_new / get_sovits_version_from_path_fast 来读取，
              不能用普通 torch.load。
        """
        try:
            from pathlib import Path

            sovits_file = Path(sovits_path)
            if not sovits_file.exists():
                print(f"[GPT-SoVITS] SoVITS 文件不存在: {sovits_path}")
                return False

            # 使用官方函数检测版本（读取前2字节的版本标识）
            import sys
            gptsovits_subdir = str(GPT_SOVITS_DIR / "GPT_SoVITS")
            if gptsovits_subdir not in sys.path:
                sys.path.insert(0, gptsovits_subdir)

            from process_ckpt import get_sovits_version_from_path_fast
            ver_info = get_sovits_version_from_path_fast(sovits_path)
            # ver_info: [version, model_version, if_lora_v3]
            version, model_version, if_lora_v3 = ver_info

            # ZIP 文件（b"PK" 头）= v3/v4 LoRA 格式，process_ckpt 错误返回 v2
            # 此时 if_lora_v3=False，但文件名含 l8 = lora_rank=8 → 实际是 v3
            if version == "v2" and not if_lora_v3:
                with open(sovits_path, "rb") as f:
                    header = f.read(2)
                if header == b"PK":  # ZIP 头 → v3/v4
                    filename_lower = os.path.basename(sovits_path).lower()
                    if "_l8" in filename_lower or "_l16" in filename_lower:
                        version = "v3"
                        if_lora_v3 = True
                        print(f"[GPT-SoVITS] SoVITS 文件版本: v3 (ZIP+LoRA, {os.path.basename(sovits_path)})")
                    else:
                        version = "v3"
                        print(f"[GPT-SoVITS] SoVITS 文件版本: v3 (ZIP, {os.path.basename(sovits_path)})")
                else:
                    print(f"[GPT-SoVITS] SoVITS 文件版本: {model_version}, LoRA={if_lora_v3}")
            else:
                print(f"[GPT-SoVITS] SoVITS 文件版本: {model_version}, LoRA={if_lora_v3}")
            return True
        except Exception as e:
            print(f"[GPT-SoVITS] 检查 SoVITS 配置失败: {e}")
            return False

    def _resolve_project_path(self, path: str, project_name: str) -> str:
        """
        【功能说明】将配置文件中的路径解析为绝对路径

        支持三种格式：
        - 绝对路径（兼容旧配置）：直接使用，文件不存在则回退到项目目录搜索
        - 相对路径（推荐）：相对于项目目录解析
        - 空值/None：原样返回

        【参数说明】
            path (str): 配置文件中存储的路径
            project_name (str): 项目名称，用于定位项目目录

        【返回值】
            str: 解析后的绝对路径（正斜杠格式），或原始值（空值时）
        """
        if not path:
            return path

        project_dir = str(self._get_project_dir(project_name))

        # 已经是绝对路径
        if os.path.isabs(path):
            if os.path.isfile(path):
                return path.replace('\\', '/')
            # 绝对路径但文件不存在（项目移动过），回退到项目目录搜索同名文件
            basename = os.path.basename(path)
            for subdir in ['', '32k', 'ckpt', 's2_ckpt']:
                candidate = os.path.join(project_dir, subdir, basename)
                if os.path.isfile(candidate):
                    print(f"[GPT-SoVITS] 路径修正: {os.path.basename(path)} → {candidate.replace(chr(92), '/')}")
                    return candidate.replace('\\', '/')
            # 搜索不到也返回原路径（后续 _check_sovits_config 会处理）
            return path.replace('\\', '/')

        # 相对路径：相对于项目目录解析
        abs_path = os.path.normpath(os.path.join(project_dir, path))
        return abs_path.replace('\\', '/')

    def _make_relative_path(self, abs_path: str, project_name: str) -> str:
        """
        【功能说明】将绝对路径转换为相对于项目目录的相对路径

        如果路径在项目目录下，返回相对路径（如 "32k/ref.wav"、"SV_mansui.pth"）。
        如果路径不在项目目录下，返回原始绝对路径（跨目录的文件保持绝对路径）。

        【参数说明】
            abs_path (str): 绝对路径
            project_name (str): 项目名称

        【返回值】
            str: 相对路径或原始绝对路径
        """
        if not abs_path:
            return abs_path

        project_dir = str(self._get_project_dir(project_name))
        try:
            rel = os.path.relpath(abs_path, project_dir).replace('\\', '/')
            # 如果相对路径没有 .. （即文件在项目目录内），使用相对路径
            if not rel.startswith('..'):
                return rel
        except ValueError:
            pass  # 不同盘符，无法计算相对路径

        return abs_path.replace('\\', '/')

    def _load_project_config(self, project_name: str) -> dict:
        """
        【功能说明】从磁盘加载指定项目的配置文件

        【参数说明】
            project_name (str): 项目名称

        【返回值】
            dict: 项目配置字典，路径字段已解析为绝对路径。
                  如果配置文件不存在，返回包含默认值的字典。

        【路径处理】
            config.json 中存储相对路径（推荐）或绝对路径（兼容旧配置）。
            加载时统一转换为绝对路径供代码使用。
            保存时通过 _save_project_config 自动转回相对路径。

            旧版绝对路径如果文件不存在，会自动在项目目录搜索同名文件并修正。
        """
        config_path = self._get_project_config_path(project_name)
        if config_path.exists():
            try:
                config = json.load(open(config_path, 'r', encoding='utf-8'))

                # 将路径字段从存储格式（相对/旧绝对）解析为运行时绝对路径
                path_keys = ['ref_audio', 'trained_gpt', 'trained_sovits']
                config_changed = False
                for key in path_keys:
                    raw_path = config.get(key)
                    if raw_path:
                        resolved = self._resolve_project_path(raw_path, project_name)
                        if resolved != raw_path:
                            config[key] = resolved
                            config_changed = True

                # 旧配置修正后，保存为新的相对路径格式
                if config_changed:
                    self._save_project_config(project_name, config)
                
                # 如果 ref_text 为空，自动识别
                ref_text = config.get("ref_text", "").strip()
                if not ref_text:
                    ref_audio = config.get("ref_audio", "")
                    if ref_audio:
                        ref_text = self._recognize_ref_audio(ref_audio)
                    if ref_text:
                        config["ref_text"] = ref_text
                        # 保存识别结果
                        self._save_project_config(project_name, config)
                        print(f"[GPT-SoVITS] 已识别参考音频文本: {ref_text[:30]}...")
                    else:
                        # 识别失败，使用默认文本
                        config["ref_text"] = "你好欢迎使用"
                        print(f"[GPT-SoVITS] 参考音频文本识别失败，使用默认文本")
                return config
            except Exception as e:
                print(f"[GPT-SoVITS] 加载项目配置失败: {e}")
        
        # 返回默认配置（空配置，需要项目先上传音频）
        return {
            "ref_audio": None,
            "ref_text": "你好欢迎使用",  # v1.6.7: 避免空 ref_text 导致 SoVITS V3 报错
            "trained_gpt": None,
            "trained_sovits": None,
        }

    def _recognize_ref_audio(self, audio_path: str) -> str:
        """
        【功能说明】使用 ASR 引擎识别参考音频文件中的文字内容

        【参数说明】
            audio_path (str): 参考音频文件路径

        【返回值】
            str: 识别出的文本（已去除空格）；识别失败时返回空字符串

        【实现细节】
            - 使用 faster-whisper ASR 引擎进行语音识别
            - 采用懒加载模式（首次调用时才初始化 ASR 引擎）
            - 识别结果自动去除空格，避免 GPT-SoVITS 处理时出现异常
        """
        try:
            # 懒加载 ASR 引擎
            if not hasattr(self, '_asr_engine') or self._asr_engine is None:
                try:
                    import sys
                    # 添加 app 目录到路径
                    app_dir = str(Path(__file__).parent.parent)
                    if app_dir not in sys.path:
                        sys.path.insert(0, app_dir)
                    
                    from asr import ASRFactory
                    self._asr_engine = ASRFactory.create({
                        "provider": "faster_whisper",
                        "faster_whisper": {
                            "model_size": "base",
                            "device": self.device,
                            "compute_type": "float16" if self.is_half else "float32"
                        }
                    })
                    print(f"[GPT-SoVITS] ASR 引擎创建成功: {type(self._asr_engine).__name__}")
                except Exception as e:
                    print(f"[GPT-SoVITS] ASR 引擎创建失败: {e}")
                    return ""

            if self._asr_engine and self._asr_engine.is_available():
                text = self._asr_engine.recognize(audio_path)
                if text:
                    # 清理空格
                    return text.replace(" ", "").strip()
        except Exception as e:
            print(f"[GPT-SoVITS] 识别参考音频失败: {e}")
        return ""

    def _save_project_config(self, project_name: str, config: dict):
        """
        【功能说明】将项目配置字典序列化并保存到磁盘的 config.json 文件

        【参数说明】
            project_name (str): 项目名称
            config (dict): 要保存的配置字典

        【副作用】
            - 自动创建项目目录（如果不存在）
            - 使用 UTF-8 编码和 JSON 格式化（indent=2）写入文件

        【路径处理】
            保存前将绝对路径转换为相对路径（相对于项目目录），
            确保项目移动后路径仍然有效。
        """
        # 深拷贝，避免修改传入的 config 对象（运行时仍需要绝对路径）
        save_config = dict(config)
        path_keys = ['ref_audio', 'trained_gpt', 'trained_sovits']
        for key in path_keys:
            abs_path = save_config.get(key)
            if abs_path and os.path.isabs(abs_path):
                save_config[key] = self._make_relative_path(abs_path, project_name)

        config_path = self._get_project_config_path(project_name)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(save_config, f, ensure_ascii=False, indent=2)
        print(f"[GPT-SoVITS] 项目配置已保存: {project_name}")

    def _save_last_project(self, project_name: str):
        """持久化上次使用的音色名称，供下次启动预热使用"""
        try:
            LAST_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LAST_PROJECT_FILE, 'w', encoding='utf-8') as f:
                json.dump({"last_project": project_name, "ts": time.time()}, f, ensure_ascii=False)
        except Exception:
            pass  # 非关键功能，失败不影响使用

    def _load_last_project(self) -> Optional[str]:
        """读取上次使用的音色名称，不存在则返回 None"""
        try:
            if LAST_PROJECT_FILE.exists():
                data = json.load(open(LAST_PROJECT_FILE, 'r', encoding='utf-8'))
                return data.get("last_project")
        except Exception:
            pass
        return None

    def set_project(self, project_name: str):
        """
        【功能说明】切换当前活跃项目，加载该项目的参考音频、配置和训练模型

        【参数说明】
            project_name (str): 要切换到的项目名称

        【执行流程】
            1. 如果项目未变化且 pipeline 已初始化，直接返回（避免重复加载）
            2. 加载新项目的配置文件
            3. 优先使用训练好的模型路径；无训练模型时回退到预训练底模
            4. 如果 ref_text 为空，尝试 ASR 自动识别
            5. 重置 tts_pipeline（下次 speak 时触发重新初始化）

        【版本兼容性】
            不同版本（v1/v2/v3/v4）使用不同的预训练 GPT 模型文件名，
            根据 self.version 自动选择对应的预训练文件。
        """
        # 如果已经是当前项目，跳过切换（避免重复重载模型）
        if self.current_project == project_name and self.tts_pipeline is not None:
            print(f"[GPT-SoVITS] 项目 {project_name} 已加载，跳过切换")
            return

        self.current_project = project_name
        self._project_config = self._load_project_config(project_name)

        # v1.9.1: 从项目配置读取模型版本（v1/v2/v3/v4），影响预训练底模选择
        config_version = self._project_config.get("version")
        if config_version in ("v1", "v2", "v3", "v4"):
            self.version = config_version
            print(f"[GPT-SoVITS] 项目模型版本: {config_version}")

        # 更新模型路径为训练好的模型
        trained_gpt = self._project_config.get("trained_gpt")
        trained_sovits = self._project_config.get("trained_sovits")
        
        # SoVITS 模型：优先使用训练的模型，否则使用预训练模型
        if trained_sovits:
            self.sovits_path = trained_sovits
            print(f"[GPT-SoVITS] 使用训练的 SoVITS 模型: {os.path.basename(trained_sovits)}")
        else:
            pretrained_sovits = str(GPT_SOVITS_DIR / "GPT_SoVITS" / "pretrained_models" / "s2Gv3.pth")
            self.sovits_path = pretrained_sovits
            print(f"[GPT-SoVITS] 使用预训练 SoVITS 模型: {os.path.basename(pretrained_sovits)}")
        
        # GPT 模型：优先使用训练的模型，否则使用预训练模型
        if trained_gpt:
            self.gpt_path = trained_gpt
            print(f"[GPT-SoVITS] 使用训练的 GPT 模型: {os.path.basename(trained_gpt)}")
        else:
            # 根据版本选择正确的预训练 GPT 模型（s1bert.pth 不存在，v3 用 s1v3.ckpt）
            version_pretrained_gpt = {
                "v1": "s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
                "v2": "gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
                "v3": "s1v3.ckpt",
                "v4": "s1v3.ckpt",
            }
            gpt_filename = version_pretrained_gpt.get(self.version, "s1v3.ckpt")
            pretrained_gpt = str(GPT_SOVITS_DIR / "GPT_SoVITS" / "pretrained_models" / gpt_filename)
            self.gpt_path = pretrained_gpt
            print(f"[GPT-SoVITS] 使用预训练 GPT 模型 ({self.version}): {os.path.basename(pretrained_gpt)}")

        # 如果 ref_text 为空，尝试识别
        if not self._project_config.get("ref_text", "").strip():
            ref_audio = self._project_config.get("ref_audio", "")
            if ref_audio:
                ref_text = self._recognize_ref_audio(ref_audio)
                if ref_text:
                    self._project_config["ref_text"] = ref_text
                    self._save_project_config(project_name, self._project_config)
                    print(f"[GPT-SoVITS] 已识别参考音频文本: {ref_text[:30]}...")
                else:
                    self._project_config["ref_text"] = "你好欢迎使用"
                    print(f"[GPT-SoVITS] 参考音频文本识别失败，使用默认文本")

        print(f"[GPT-SoVITS] 已切换到项目: {project_name}")
        print(f"[GPT-SoVITS] 参考音频: {self._project_config.get('ref_audio', '无')}")
        print(f"[GPT-SoVITS] 参考文本: {self._project_config.get('ref_text', '无')[:50]}...")

        # 持久化"上次使用的音色"，供启动预热使用
        self._save_last_project(project_name)

        # 重置 pipeline 以应用新模型（如果已初始化）
        if self.tts_pipeline is not None:
            print(f"[GPT-SoVITS] 重置 pipeline 以加载新模型")
            # C1修复: 释放旧模型占用的GPU显存
            try:
                del self.tts_pipeline
            except Exception:
                pass
            self.tts_pipeline = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("[GPT-SoVITS] 已释放GPU缓存")

    def cleanup(self):
        """C2修复: 关停时释放GPU资源，防止显存泄漏"""
        try:
            if self.tts_pipeline is not None:
                print("[GPT-SoVITS] 正在释放GPU资源...")
                try:
                    del self.tts_pipeline
                except Exception:
                    pass
                self.tts_pipeline = None
            # 释放模型权重占用的显存
            for attr_name in ['_gpt_model', '_sovits_model', '_bert_model', '_cnhubert']:
                model = getattr(self, attr_name, None)
                if model is not None:
                    try:
                        del model
                    except Exception:
                        pass
                    setattr(self, attr_name, None)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("[GPT-SoVITS] GPU缓存已清理")
        except Exception as e:
            print(f"[GPT-SoVITS] 清理GPU资源时出错: {e}")

    def get_available_projects(self) -> List[dict]:
        """
        获取所有可用项目

        【返回值】
            List[dict]: 项目列表，每个 dict 包含:
                - name (str): 项目名称
                - ref_audio (str): 参考音频路径
                - ref_text (str): 参考文本
                - has_trained (bool): 是否已完成训练
        """
        projects = []
        if not PROJECTS_DIR.exists():
            return projects
        
        for p in PROJECTS_DIR.iterdir():
            if p.is_dir():
                config_path = p / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            cfg = json.load(f)
                        projects.append({
                            "name": p.name,
                            "ref_audio": self._resolve_project_path(cfg.get("ref_audio", ""), p.name),
                            "ref_text": cfg.get("ref_text", ""),
                            "has_trained": cfg.get("trained_gpt") is not None or cfg.get("trained_sovits") is not None,
                        })
                    except:
                        pass
        
        return projects

    def save_trained_models(self, project_name: str, gpt_path: str, sovits_path: str):
        """
        保存训练后的模型路径到项目配置

        【参数说明】
            project_name (str): 项目名称
            gpt_path (str): 训练好的 GPT 模型文件路径
            sovits_path (str): 训练好的 SoVITS 模型文件路径
        """
        config = self._load_project_config(project_name)
        config["trained_gpt"] = gpt_path
        config["trained_sovits"] = sovits_path
        self._save_project_config(project_name, config)
        
        # 如果是当前项目，更新加载的模型
        if project_name == self.current_project:
            self.gpt_path = gpt_path
            self.sovits_path = sovits_path
            # 重置 TTS pipeline 以应用新模型
            self.tts_pipeline = None

    def _lazy_init(self):
        """
        延迟初始化 - 首次推理时才加载模型

        【执行流程】
            1. double-check 防止重复初始化
            2. 设置工作目录和 Python 路径
            3. 检测 SoVITS 模型版本（v1/v2/v3/v4）
            4. 配置 TTS_Config（设备、半精度、模型路径）
            5. 创建 TTS pipeline 实例
            6. 记录 GPU 显存占用

        【线程安全】
            使用 threading.Lock 实现 double-checked locking pattern，
            防止多个线程同时触发初始化。
        """
        if self.tts_pipeline is not None:
            return

        # 防止并发初始化（多个线程同时调用 speak 时）
        if not hasattr(self, '_init_lock'):
            import threading
            self._init_lock = threading.Lock()
        
        with self._init_lock:
            # double-check：拿到锁后可能另一个线程已经初始化了
            if self.tts_pipeline is not None:
                return

            print("[GPT-SoVITS] Loading models...")

            # 确保工作目录正确（训练可能改变了目录）
            # 需要 chdir 到 GPT_SoVITS 子目录，因为 GPT-SoVITS 代码中使用相对路径
            gptsovits_subdir = str(GPT_SOVITS_DIR / "GPT_SoVITS")
            os.chdir(gptsovits_subdir)

            # 添加必要的路径到 sys.path
            import sys
            if gptsovits_subdir not in sys.path:
                sys.path.insert(0, gptsovits_subdir)

            print(f"[GPT-SoVITS] Working directory: {os.getcwd()}")

            from TTS_infer_pack.TTS import TTS, TTS_Config

            # ============================================================
            # 修复版本检测问题：
            # v3/v4 LoRA 模型全部以 ZIP 格式存储（前2字节 = b"PK"），
            # process_ckpt.get_sovits_version_from_path_fast 对 ZIP 返回 ["v2","v2",False]
            # 导致系统错误地使用 v2 配置加载 v3/v4 模型，完全绕过训练的音色。
            # 正确做法：检测到 ZIP 头时，根据文件名判断版本（有 l8/lora_rank=8 → v3）
            # ============================================================
            sovits_version = None
            if os.path.exists(self.sovits_path):
                try:
                    from process_ckpt import get_sovits_version_from_path_fast
                    ver_info = get_sovits_version_from_path_fast(self.sovits_path)
                    sovits_version, _, _ = ver_info
                    print(f"[GPT-SoVITS] 检测 SoVITS 版本(原始): {sovits_version}")

                    # ZIP 文件 = v3/v4 LoRA 格式，process_ckpt 会错误返回 v2
                    if sovits_version == "v2":
                        with open(self.sovits_path, "rb") as f:
                            header = f.read(2)
                        if header == b"PK":  # ZIP 头 = v3/v4 LoRA
                            filename_lower = os.path.basename(self.sovits_path).lower()
                            if "_l8" in filename_lower or "_l16" in filename_lower:
                                sovits_version = "v3"
                                print(f"[GPT-SoVITS] ZIP 头检测 → v3/v4 LoRA，文件名含 l8/l16 → 强制 v3")
                            else:
                                sovits_version = "v3"
                                print(f"[GPT-SoVITS] ZIP 头检测 → 强制使用 v3")
                except Exception:
                    pass

            # v1 SoVITS 必须搭配 v1 预训练 GPT
            if sovits_version == "v1":
                pretrained_gpt = str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt")
                if os.path.exists(pretrained_gpt):
                    self.gpt_path = pretrained_gpt
                    print(f"[GPT-SoVITS] v1 SoVITS 检测 → 使用 v1 兼容预训练 GPT: {os.path.basename(pretrained_gpt)}")

            tts_config = TTS_Config(str(GPT_SOVITS_DIR / "GPT_SoVITS/configs/tts_infer.yaml"))
            tts_config.device = self.device
            tts_config.is_half = self.is_half
            tts_version = sovits_version if sovits_version in ("v1", "v2", "v3", "v4") else self.version
            tts_config.update_version(tts_version)
            tts_config.t2s_weights_path = self.gpt_path
            tts_config.vits_weights_path = self.sovits_path
            tts_config.cnhuhbert_base_path = self.cnhubert_path
            tts_config.bert_base_path = self.bert_path

            print(f"[GPT-SoVITS] Device: {self.device}, Half: {self.is_half}")
            print(f"[GPT-SoVITS] GPT: {os.path.basename(self.gpt_path)}")
            print(f"[GPT-SoVITS] SoVITS: {os.path.basename(self.sovits_path)}")

            # 验证 SoVITS 文件可读（兼容 LoRA 和标准格式）
            if not self._check_sovits_config(self.sovits_path):
                print(f"[GPT-SoVITS] ⚠️ SoVITS 文件无效，回退到预训练底模 s2Gv3.pth")
                self.sovits_path = str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/s2Gv3.pth")
                tts_config.vits_weights_path = self.sovits_path

            try:
                print(f"[GPT-SoVITS] 正在加载 TTS 模型（输出已静默）...")
                with _SuppressVerboseOutput():
                    self.tts_pipeline = TTS(tts_config)
                print("[GPT-SoVITS] ✓ TTS 模型加载完成!")
            except TypeError as e:
                # v1/v3 版本不匹配导致加载失败 → 尝试回退到 v1 底模
                if sovits_version == "v1" and "list indices" in str(e):
                    print(f"[GPT-SoVITS] ⚠️ v1/v3 版本不匹配: {e}")
                    print(f"[GPT-SoVITS] 强制使用 v1 预训练底模...")
                    fallback_gpt = str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt")
                    fallback_vits = str(GPT_SOVITS_DIR / "GPT_SoVITS/pretrained_models/s2Gv3.pth")
                    tts_config.t2s_weights_path = fallback_gpt
                    tts_config.vits_weights_path = fallback_vits
                    tts_config.update_version("v1")
                    print(f"[GPT-SoVITS] 正在加载 v1 回退底模（输出已静默）...")
                    with _SuppressVerboseOutput():
                        self.tts_pipeline = TTS(tts_config)
                    print(f"[GPT-SoVITS] ✓ v1 回退底模加载成功!")
                else:
                    raise

            # 记录显存占用
            if torch.cuda.is_available():
                mem_gb = torch.cuda.memory_allocated() / 1024**3
                print(f"[GPT-SoVITS] GPU Memory: {mem_gb:.2f} GB")

    def speak(self, text: str, ref_audio_path: str = None, ref_text: str = None,
              text_lang: str = "all_zh", prompt_lang: str = "all_zh",
              output_path: str = None, project: str = None) -> str:
        """
        使用参考音频进行语音合成（音色克隆）

        【参数说明】
            text (str): 要合成的文本，支持中文和少量英文
            ref_audio_path (str, optional): 参考音频路径（3-10秒）；
                                           默认使用当前项目的参考音频
            ref_text (str, optional): 参考音频对应的文本；默认使用当前项目配置
            text_lang (str): 合成文本的语言，默认 "all_zh"
            prompt_lang (str): 参考音频的语言，默认 "all_zh"
            output_path (str, optional): 输出 WAV 文件路径；
                                        默认保存到 app/cache/gptsovits_{timestamp}.wav
            project (str, optional): 指定项目名称；会切换到该项目并加载对应模型

        【返回值】
            str: 生成的音频文件路径（WAV 格式，24kHz 单声道）

        【处理流程】
            1. 延迟初始化模型（首次调用时）
            2. 切换到指定项目（如果提供）
            3. 文本清洗（去 emoji、换行、markdown 符号）
            4. 智能分句（按标点分，每句≤80字）
            5. 逐句合成（避免长文本 EOS 过早触发）
            6. 合并音频片段并保存

        【已知问题】
            - CNHuBERT 在 pipeline 重置时可能报告张量维度错误，但 TTS 仍可正常工作
              原因：FunASR paraformer ASR 模型内部 checkpoint 维度不匹配
              解决：v1.4.64 在 web/__init__.py 中增加了 faster-whisper fallback
        """
        self._lazy_init()

        # ===== v1.8.5: 空文本守卫 =====
        if not text or not text.strip():
            print(f"[GPT-SoVITS] speak: 收到空文本，跳过")
            return ""
        # ===== 守卫结束 =====

        # v1.5.2 修复: 无效 voice 参数处理
        # 'default' 不是有效项目名，跳过 set_project，保持当前已加载的项目
        effective_project = project if project and project != 'default' else None
        if effective_project is not None and effective_project != self.current_project:
            self.set_project(effective_project)

        # 使用当前项目的参考音频
        # ⚠️ 注意：ref_text 必须和参考音频内容一致，语言必须和目标文本相同
        if ref_audio_path is None:
            ref_audio_path = self._project_config.get('ref_audio', '')
        if ref_text is None:
            ref_text = self._project_config.get('ref_text', '')

        # 确保 prompt_text 以标点符号结尾（参考官方处理）
        if ref_text and ref_text[-1] not in '。！？.!?':
            ref_text += "."

        if output_path is None:
            output_path = str(Path(__file__).parent.parent / "cache" / f"gptsovits_{int(time.time() * 1000)}.wav")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 确保 text 以标点结尾
        if text:
            # v1.5.3 清理 emoji（GPT-SoVITS 无法处理 emoji）
            import re as _re
            text = _re.sub(r'[\U00010000-\U0010FFFF]', '', text)  # 4字节 emoji
            text = _re.sub(r'[\u2000-\u2BFF]', '', text)  # 符号区
            # v1.5.4 修复：替换换行符，防止 GPT-SoVITS 内部 pre_seg_text() 按 \n 切分
            text = text.replace('\n', '，').replace('\r', '')
            # v1.7.5 清理 markdown 格式符号（LLM 输出常包含 markdown，TTS 无法处理）
            text = _re.sub(r'-{2,}', '，', text)                # --- 横线 → 逗号（避免前后文字粘连）
            text = _re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)  # **bold** / *italic* → 纯文字
            text = _re.sub(r'#{1,6}\s*', '', text)            # ## heading → 删除标记
            text = _re.sub(r'(?<=[，,。.！!？?；;：:])\s*[-*+]\s*', '', text)  # 标点后 - list → 删除标记（含无空格情况）
            text = _re.sub(r'^\s*[-*+]\s*', '', text)                                # 行首 - list → 删除标记
            text = _re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [link](url) → link text
            # v1.7.5b 额外清理：反引号 code、括号说明
            text = _re.sub(r'`([^`]+)`', r'\1', text)           # `code` → code（去除反引号，保留内容）
            text = _re.sub(r'\([^)]*\)', '', text)              # (说明性文字) → 删除（如 (Terminal/Log)）
            # v1.9.21: 彻底清理所有横杠/减号（GPT-SoVITS 内部把 - 当标点，会读成"减"）
            # 策略：先把所有 - 替换为逗号，再恢复英文复合词中的连字符
            # 这样确保没有任何横杠到达 GPT-SoVITS，同时保留 GPT-SoVITS、v1.9-beta、5-10 等
            text = text.replace('-', '，')
            text = _re.sub(r'([a-zA-Z0-9])，([a-zA-Z0-9])', r'\1-\2', text)  # 恢复英文复合词连字符
            text = text.strip()

        # v1.6.7 修复: 清理 LLM 异常输出的连续标点（如 。，，。。等）
        # 在分句前做预处理，避免连续标点被切成空句
        if text:
            import re as _re
            # 合并连续的同类标点：。。。→。，，，→，
            # 但保留交替模式如 ？！（不要合成 ?!）
            for punct_group in [
                r'([。\.]{2,})', r'([！!]{2,})', r'([？?]{2,})',
                r'([，,]{2,})', r'([、]{2,})', r'([；;]{2,})', r'([：:]{2,})'
            ]:
                text = _re.sub(punct_group, lambda m: m.group(1)[0], text)
            # 清理标点+空格混合（如 "。  " → "。"）
            text = _re.sub(r'([。！？.!?])\s+([。！？.!?])', r'\1\2', text)
            # 清理句首标点（如 "。你好" → "你好"）
            text = _re.sub(r'^[，,、；：。！？.!?]+', '', text)
            text = text.strip()
            if not text:
                return output_path  # 清理后为空，直接返回

        if text and text[-1] not in '。！？.!?':
            text += "。"

        # v1.6 优化: 智能语义分句，减少连贯语句被切断
        # 提高单句长度上限，减少不必要的切分
        MAX_CHARS = 80  # v1.6: 从 40 提高到 80，减少强制切分
        # 主要分句点：句号、感叹号、问号
        major_punct = set('。！？.!?')
        # 次要分句点：逗号、顿号（用于超长句的语义断点）
        minor_punct = set('，,、；：')
        # 连接词断点：和、而、但、所以、因为、虽然、如果、虽然、不过、然后
        connectives = {'和', '而', '但', '所以', '因为', '虽然', '如果', '不过', '然后', '于是', '可是', '不过', '然而', '并且', '或者', '还是'}
        
        def find_best_break(text, max_len):
            """在 max_len 附近找最佳语义断点"""
            # 优先在标点处断开
            for i in range(max_len - 1, max(10, max_len - 20), -1):
                if text[i] in '。，,、；：':
                    return text[:i + 1]
            # 在连接词处断开
            for i in range(max_len - 1, max(10, max_len - 15), -1):
                if text[i:i+2] in connectives or text[i] in '但如果因为虽然':
                    return text[:i + 1]
            # 硬切
            return text[:max_len]
        
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in major_punct:
                if current.strip():
                    sentences.append(current.strip())
                current = ""
            elif char in minor_punct:
                # 逗号等次要标点：如果当前句子太长（>80字），在这里切分
                if len(current) > 80:
                    if current.strip():
                        sentences.append(current.strip())
                    current = ""
        if current.strip():
            sentences.append(current.strip())

        # v1.6 优化: 智能分句，在语义断点处断开而非硬切
        final_sentences = []
        for sent in sentences:
            # v1.6.7 修复: 过滤空句和纯标点句（LLM 异常输出如 "." "，，" 等）
            sent_stripped = sent.strip()
            if not sent_stripped:
                continue
            import re as _re2
            if _re2.fullmatch(r'[，,、；：。！？.!?！？\s]+', sent_stripped):
                print(f"  [TTS] 跳过纯标点句: {sent_stripped[:20]}")
                continue
            if len(sent_stripped) <= MAX_CHARS:
                final_sentences.append(sent_stripped)
            else:
                # 递归切分，每段最多 MAX_CHARS 字符
                remaining = sent
                while len(remaining) > MAX_CHARS:
                    # 找到最佳断点
                    chunk = find_best_break(remaining, MAX_CHARS)
                    final_sentences.append(chunk.strip())
                    remaining = remaining[len(chunk):].lstrip('，。、；：')
                if remaining.strip():
                    final_sentences.append(remaining.strip())

        print(f"[GPT-SoVITS] Split into {len(final_sentences)} sentences")
        for i, s in enumerate(final_sentences):
            print(f"  [{i}] ({len(s)}字) {s[:40]}")

        # v1.6.7: 如果所有句子都被过滤（纯标点/空句），返回静音
        if not final_sentences:
            print("[GPT-SoVITS] 所有句子被过滤（空/纯标点），生成静音")
            silence = np.zeros(24000).astype(np.float32)
            import soundfile as sf
            sf.write(output_path, silence, 24000)
            return output_path

        print(f"[GPT-SoVITS] Synthesizing: {text[:50]}...")

        # 逐句推理，避免长文本 EOS 过早触发
        audio_chunks = []
        sr = 24000

        for idx, sent in enumerate(final_sentences):
            inputs = {
                "text": sent,
                "text_lang": text_lang,
                "ref_audio_path": ref_audio_path,
                "aux_ref_audio_paths": [],
                "prompt_text": ref_text,
                "prompt_lang": prompt_lang,
                "top_k": self.top_k,
                "top_p": self.top_p,
                "temperature": self.temperature,
                "text_split_method": "cut0",  # 单句不需要切分
                "batch_size": 1,
                "speed_factor": self.speed,
                "split_bucket": True,
                "return_fragment": False,
                "fragment_interval": 0.3,
                "seed": 42,  # 固定种子保证音色一致性
                "parallel_infer": self.parallel_infer,
                "repetition_penalty": 1.35,
                "sample_steps": 32 if self.version in ['v3', 'v4'] else None,
                "super_sampling": False,
            }

            try:
                print(f"[GPT-SoVITS] Calling TTS.run() with text: {sent[:50]}")
                for result in self.tts_pipeline.run(inputs):
                    if result is None:
                        continue
                    chunk_sr, audio_data = result
                    sr = chunk_sr

                    # audio_data 类型：np.ndarray (int16) 或 torch.Tensor (float)
                    if isinstance(audio_data, np.ndarray):
                        if audio_data.dtype in (np.int16, np.int32):
                            audio_float = audio_data.astype(np.float32) / 32768.0
                        else:
                            audio_float = audio_data.astype(np.float32)
                    elif hasattr(audio_data, 'cpu'):
                        arr = audio_data.cpu().numpy()
                        if arr.dtype in (np.int16, np.int32):
                            audio_float = arr.astype(np.float32) / 32768.0
                        else:
                            audio_float = arr.astype(np.float32)
                    else:
                        audio_float = np.array(audio_data, dtype=np.float32)

                    # 展平为一维
                    audio_float = audio_float.flatten()

                    # 跳过过短片段
                    if len(audio_float) > sr * 0.05:
                        audio_chunks.append(audio_float)
                        print(f"  [{idx}] {len(audio_float)/sr:.2f}s, max={np.abs(audio_float).max():.4f}")
            except Exception as e:
                print(f"  [{idx}] Error: {e}")
                continue

        if audio_chunks:
            # 合并所有音频片段
            audio_float = np.concatenate(audio_chunks)

            # 振幅检查
            max_amp = np.abs(audio_float).max()
            if max_amp < 0.01 and max_amp > 0:
                audio_float = audio_float / max_amp * 0.9
                print(f"[GPT-SoVITS] 振幅归一化: {max_amp:.6f} -> 0.9")

            # 保存为 WAV
            import soundfile as sf
            sf.write(output_path, audio_float, sr)
            duration = len(audio_float) / sr
            print(f"[GPT-SoVITS] Saved: {output_path} ({duration:.2f}s, {len(audio_chunks)} chunks)")
            return output_path
        else:
            print("[GPT-SoVITS] No audio generated, creating silence")
            silence = np.zeros(24000).astype(np.float32)
            import soundfile as sf
            sf.write(output_path, silence, 24000)
            return output_path

    def speak_streaming(self, sentence: str, ref_audio_path: str = None, ref_text: str = None,
                         text_lang: str = "all_zh", prompt_lang: str = "all_zh",
                         project: str = None, on_chunk=None) -> str:
        """
        流式语音合成：每出一个 chunk 就写入临时 WAV 文件

        【参数说明】
            sentence (str): 要合成的文本（单个句子，不应过长）
            ref_audio_path (str, optional): 参考音频路径
            ref_text (str, optional): 参考文本
            text_lang (str): 文本语言，默认 "all_zh"
            prompt_lang (str): 参考音频语言，默认 "all_zh"
            project (str, optional): 指定项目
            on_chunk (Callable, optional): 每产出 chunk 时的回调函数，签名:
                                           on_chunk(chunk_sr, audio_float, chunk_idx)

        【返回值】
            str: 生成的音频文件路径（文件逐步增长，完整后返回路径）

        【与 speak() 的区别】
            - speak(): 等所有句子全部合完成后一次性返回文件
            - speak_streaming(): 每合成一个 chunk 就写入文件，可实时播放
            - 适合实时对话场景，边合成边播放降低延迟感知

        【实现细节】
            - 每个 chunk 追加写入同一 WAV 文件（更新 header）
            - 回调函数 on_chunk 可用于实时通知（如 WebSocket 推送）
        """
        self._lazy_init()

        # ===== v1.8.5: 空文本守卫 —— 清理前先判空，防止推理卡死 =====
        if not sentence or not sentence.strip():
            print(f"[GPT-SoVITS] speak_streaming: 收到空文本，跳过")
            return ""
        # ===== 守卫结束 =====

        # ===== v1.5.1 修复: 无效 voice 参数处理 =====
        # 'default' 不是有效项目名，跳过 set_project，保持当前已加载的项目
        # 这样 WebSocket 客户端默认 voice='default' 时不会触发项目切换失败
        effective_project = project if project and project != 'default' else None
        if effective_project is not None and effective_project != self.current_project:
            self.set_project(effective_project)
        # ===== v1.5.1 修复结束 =====

        if ref_audio_path is None:
            ref_audio_path = self._project_config.get('ref_audio', '')
        if ref_text is None:
            ref_text = self._project_config.get('ref_text', '')

        if ref_text and ref_text[-1] not in '。！？.!?':
            ref_text += "."

        # v1.5.3 优化: 避免 GPT-SoVITS 内部按换行符/逗号切分
        # TextPreprocessor.pre_seg_text() 中 text.split("\n") 会把文本切碎
        # GPT-SoVITS 可能还按逗号切分，所以把逗号也替换成空格
        # 空格不会触发切分，保持文本连贯
        if sentence:
            # 清理 emoji（GPT-SoVITS 无法处理 emoji，会导致截断）
            import re as _re
            sentence = _re.sub(r'[\U00010000-\U0010FFFF]', '', sentence)  # 4字节 emoji（\U 大写 = 8位十六进制）
            # v1.9.20 修复：缩窄符号清理范围，避免删除英文字母和数字
            # 旧代码 [\u1F300-\u1F9FF] 是严重 Bug！\u 只支持4位十六进制，
            # Python 把 \u1F300 解析为 \u1F30 + '0'，字符范围恰好覆盖全部英文字母！
            # 正确的 emoji 清理已由 \U00010000-\U0010FFFF 覆盖
            sentence = _re.sub(r'[\u2000-\u2BFF]', '', sentence)  # 通用符号区（不含英文字母/数字）
            # 清理 markdown 格式符号（与 speak() 方法对齐）
            sentence = _re.sub(r'-{2,}', '，', sentence)                # --- 横线 → 逗号
            sentence = _re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', sentence)  # **bold** → 纯文字
            sentence = _re.sub(r'#{1,6}\s*', '', sentence)            # ## heading → 删除标记
            sentence = _re.sub(r'(?<=[，,。.！!？?；;：:])\s*[-*+]\s*', '', sentence)  # 标点后 - list → 删除
            sentence = _re.sub(r'^\s*[-*+]\s*', '', sentence)         # 行首 - list → 删除
            sentence = _re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', sentence)  # [link](url) → link
            sentence = _re.sub(r'`([^`]+)`', r'\1', sentence)         # `code` → code
            sentence = _re.sub(r'\([^)]*\)', '', sentence)            # (说明性文字) → 删除
            # v1.9.21: 彻底清理所有横杠/减号（GPT-SoVITS 内部把 - 当标点，会读成"减"）
            # 策略：先把所有 - 替换为逗号，再恢复英文复合词中的连字符
            # 这样确保没有任何横杠到达 GPT-SoVITS，同时保留 GPT-SoVITS、v1.9-beta、5-10 等
            sentence = sentence.replace('-', '，')
            sentence = _re.sub(r'([a-zA-Z0-9])，([a-zA-Z0-9])', r'\1-\2', sentence)  # 恢复英文复合词连字符
            sentence = sentence.replace('\n', ' ').replace('\r', '').replace('，', ' ').replace(',', ' ')
            # 清理多余空格
            sentence = ' '.join(sentence.split())
            if sentence and sentence[-1] not in '。！？.!?':
                sentence += "。"

        # ===== v1.8.5: 清理后再次判空 =====
        if not sentence or not sentence.strip():
            print(f"[GPT-SoVITS] speak_streaming: 清理后文本为空，跳过")
            return ""
        # ===== 再次判空结束 =====

        import uuid
        tmp_path = str(Path(__file__).parent.parent / "cache" / f"stream_{uuid.uuid4().hex}.wav")
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)

        sr = 24000
        all_samples = []
        chunk_idx = 0

        # v1.8.5: 短句禁用 split_bucket
        # split_bucket=True 在短句末尾会产生空分桶条目，导致 tts_pipeline.run() 推理空文本卡死
        # 短句(≤50字)不需要分桶，直接关闭
        use_split_bucket = len(sentence) > 50

        try:
            inputs = {
                "text": sentence,
                "text_lang": text_lang,
                "ref_audio_path": ref_audio_path,
                "aux_ref_audio_paths": [],
                "prompt_text": ref_text,
                "prompt_lang": prompt_lang,
                "top_k": self.top_k,
                "top_p": self.top_p,
                "temperature": self.temperature,
                "text_split_method": "cut0",
                "batch_size": 1,
                "speed_factor": self.speed,
                "split_bucket": use_split_bucket,
                "return_fragment": False,
                "fragment_interval": 0.3,
                "seed": 42,
                "parallel_infer": self.parallel_infer,
                "repetition_penalty": 1.35,
                "sample_steps": 32 if self.version in ['v3', 'v4'] else None,
                "super_sampling": False,
            }

            for result in self.tts_pipeline.run(inputs):
                if result is None:
                    continue
                chunk_sr, audio_data = result
                sr = chunk_sr

                if isinstance(audio_data, np.ndarray):
                    if audio_data.dtype in (np.int16, np.int32):
                        audio_float = audio_data.astype(np.float32) / 32768.0
                    else:
                        audio_float = audio_data.astype(np.float32)
                elif hasattr(audio_data, 'cpu'):
                    arr = audio_data.cpu().numpy()
                    if arr.dtype in (np.int16, np.int32):
                        audio_float = arr.astype(np.float32) / 32768.0
                    else:
                        audio_float = arr.astype(np.float32)
                else:
                    audio_float = np.array(audio_data, dtype=np.float32)

                audio_float = audio_float.flatten()

                # 跳过过短片段
                if len(audio_float) < sr * 0.05:
                    continue

                all_samples.append(audio_float)

                # 追加写入临时 WAV 文件（更新 header）
                self._append_wav_samples(tmp_path, np.concatenate(all_samples) if all_samples else audio_float, sr)

                if on_chunk:
                    on_chunk(sr, audio_float, chunk_idx)
                chunk_idx += 1

            if not all_samples:
                import soundfile as sf
                silence = np.zeros(sr, dtype=np.float32)
                sf.write(tmp_path, silence, sr)
            else:
                import soundfile as sf
                audio_float = np.concatenate(all_samples)
                max_amp = np.abs(audio_float).max()
                if max_amp < 0.01 and max_amp > 0:
                    audio_float = audio_float / max_amp * 0.9
                sf.write(tmp_path, audio_float, sr)

            return tmp_path
        except Exception as e:
            print(f"[GPT-SoVITS] speak_streaming error: {e}")
            import soundfile as sf
            silence = np.zeros(24000, dtype=np.float32)
            sf.write(tmp_path, silence, 24000)
            return tmp_path

    def _append_wav_samples(self, path: str, samples: np.ndarray, sr: int):
        """追加音频样本到已有 WAV 文件（每次重写完整文件，包含更新后的 header）"""
        import soundfile as sf
        sf.write(path, samples, sr)

    def speak_zero_shot(self, text: str, text_lang: str = "all_zh") -> str:
        """
        零样本合成（需要微调模型）

        【参数说明】
            text (str): 要合成的文本
            text_lang (str): 文本语言

        【返回值】
            str: 输出文件路径（当前返回空路径占位，需微调模型支持）

        【当前状态】
            这是预留接口，当前实现只返回空路径。
            需要在项目完成微调训练后，才能真正实现零样本合成。
        """
        output_path = str(Path(__file__).parent.parent / "cache" / f"gptsovits_zero_{int(time.time() * 1000)}.wav")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        print("[GPT-SoVITS] Zero-shot requires fine-tuned model")
        return output_path

    def is_available(self) -> bool:
        """
        检查 GPT-SoVITS 是否可用

        【返回值】
            bool: True 表示模型文件存在且可加载

        【检查内容】
            - gpt_path (GPT 模型权重文件)
            - sovits_path (SoVITS 模型权重文件)
            - cnhubert_path (CNHuBERT 模型目录)
            - bert_path (BERT 模型目录)

        【注意】
            此方法只检查文件是否存在，不验证文件内容是否有效。
            有效性问题会在 _lazy_init() 或 speak() 时报告。
        """
        try:
            # 检查模型文件是否存在
            if not os.path.exists(self.gpt_path):
                print(f"[GPT-SoVITS] GPT模型不存在: {self.gpt_path}")
                return False
            if not os.path.exists(self.sovits_path):
                print(f"[GPT-SoVITS] SoVITS模型不存在: {self.sovits_path}")
                return False
            if not os.path.exists(self.cnhubert_path):
                print(f"[GPT-SoVITS] CNHuBERT模型不存在: {self.cnhubert_path}")
                return False
            if not os.path.exists(self.bert_path):
                print(f"[GPT-SoVITS] BERT模型不存在: {self.bert_path}")
                return False
            return True
        except Exception as e:
            print(f"[GPT-SoVITS] 可用性检查失败: {e}")
            return False

    def get_voices(self) -> list:
        """
        获取可用音色列表（基于项目）

        【返回值】
            list: 音色列表，每个 dict 包含:
                - value (str): 项目名称（用于 API 调用）
                - label (str): 显示名称（已训练的项目会标注）
                - project (str): 项目名称

        【生成规则】
            - 遍历所有项目，有 trained 模型的在 label 后加 "(已训练)"
            - 如果没有项目，返回默认音色 {"value": "default", "label": "默认音色"}
        """
        projects = self.get_available_projects()
        voices = []
        for p in projects:
            label = p['name']
            if p.get('has_trained'):
                label += " (已训练)"
            voices.append({
                "value": p['name'],
                "label": label,
                "project": p['name'],
            })
        
        # 如果没有项目，返回默认音色
        if not voices:
            voices = [{"value": "default", "label": "默认音色"}]
        
        return voices


def get_engine(config: dict = None) -> GPTSoVITSEngine:
    """
    【功能说明】获取 GPT-SoVITS 引擎的全局单例实例

    【参数说明】
        config (dict, optional): 引擎配置字典，可包含 device、version、project 等参数。
                                为 None 时使用默认配置。

    【返回值】
        GPTSoVITSEngine: 全局唯一的引擎实例

    【设计模式】
        单例模式：通过 GPTSoVITSEngine.__new__ 实现，确保全局只有一个引擎实例。
        多次调用 get_engine() 返回相同的实例，不会重复初始化模型。

    【使用示例】
        engine = get_engine({"project": "my_voice", "version": "v3"})
        audio_path = engine.speak("你好世界")
    """
    return GPTSoVITSEngine(config)
