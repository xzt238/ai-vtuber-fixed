# -*- coding: utf-8 -*-
"""
=====================================
GPT-SoVITS 训练管理器
=====================================

【模块功能概述】
本模块是 GPT-SoVITS 训练的前端管理模块，负责：
1. 处理 Web 端的训练请求（音频上传、配置更新、训练触发）
2. 管理训练任务队列和并发
3. 跟踪训练进度并提供状态查询
4. 提供 Web API（HTTP 轮询）供前端获取训练状态

【核心类】
- TrainingManager: 训练任务管理器，单例模式

【训练流程】
1. 用户上传参考音频（raw/*.wav）
2. 自动清洗文本（去除特殊字符、处理省略号等）
3. 调用 GPT-SoVITS 训练脚本（ preprocess → train → extract）
4. 完成后更新项目配置（trained_gpt、trained_sovits 路径）

【配置文件】
每个项目在 GPT-SoVITS/data/web_projects/{project}/config.json 存储：
- ref_audio: 参考音频路径
- ref_text: 参考音频对应的文本
- trained_gpt: 已训练的 GPT 模型路径
- trained_sovits: 已训练的 SoVITS 模型路径

【与其他模块的关系】
- 被 web/__init__.py 通过 HTTP API 调用
- 被 tts/gptsovits.py 读取项目配置加载已训练模型
- 训练脚本输出通过 subprocess 实时捕获

【输入/输出】
- 输入：project_name、音频文件路径、训练参数（epochs、batch_size 等）
- 输出：训练进度（百分比）、已完成模型路径、错误信息

作者: 咕咕嘎嘎
日期: 2026-04-01
"""
import os
import sys
import json
import time
import threading
import subprocess
import tempfile
import shutil
import yaml
from pathlib import Path
from datetime import datetime

# 路径配置 - 从 trainer/manager.py 计算项目根目录
_PROJECT_ROOT = Path(__file__).parent.parent.parent
GPT_SOVITS_ROOT = _PROJECT_ROOT / "GPT-SoVITS"
TRAIN_DATA_ROOT = GPT_SOVITS_ROOT / "data"

# 模型缓存目录
_MODELS_CACHE = _PROJECT_ROOT / "models"
_MODELS_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["MODELSCOPE_CACHE"] = str(_MODELS_CACHE)
os.environ["HF_HOME"] = str(_MODELS_CACHE / "hf")

# Python 解释器
PYTHON = r"C:\Users\x\AppData\Local\Programs\Python\Python311\python.exe"

# 支持的音频格式
SUPPORTED_AUDIO_EXTS = ("*.wav", "*.mp3", "*.flac", "*.m4a", "*.ogg")

import re

def _get_audio_files(directory: Path) -> list:
    """获取目录下所有支持的音频文件"""
    if not directory.exists():
        return []
    files = []
    for ext in SUPPORTED_AUDIO_EXTS:
        files.extend(directory.glob(ext))
        files.extend(directory.glob(ext.upper()))  # 大写扩展名
    return sorted(files)


def _clean_text_for_g2p(text: str) -> str:
    """清洗文本，去除 G2P 无法处理的特殊字符"""
    # 先处理省略号：三个点转成一个省略号字符
    text = re.sub(r'\.{3,}', '…', text)  # ... 或更多 → …
    text = re.sub(r'…{2,}', '…', text)   # 多余的省略号合并
    
    # 处理"嗯"字：pypinyin 会把嗯转成 ng+ng，导致声母韵母相同触发 assert
    # 类似的还有"呃"(e的轻声)等问题字符
    text = text.replace("嗯", "恩").replace("呣", "母").replace("呃", "呢")
    
    # 常见中文标点（GPT-SoVITS 支持的）
    allowed_punctuation = '!?…,.。！？、，；：""''（）【】《》- '
    
    # 保留中文、英文、数字、标点、空格
    cleaned = []
    for char in text:
        if (char.isalnum() or  # 英文、数字
            '\u4e00' <= char <= '\u9fff' or  # 中文
            '\u3400' <= char <= '\u4dbf' or  # 扩展中文
            char in allowed_punctuation):
            cleaned.append(char)
    
    result = ''.join(cleaned)
    # 压缩连续空格，去除首尾空白
    result = re.sub(r'\s+', ' ', result).strip()
    return result





class TrainingManager:
    """训练管理器 - 处理训练请求、队列和进度"""
    
    def __init__(self):
        """
        【功能说明】初始化训练管理器

        【返回值】
            无
        """
        self.current_task = None
        self.task_queue = []
        self.is_training = False
        self.progress_callback = None
        self._lock = threading.Lock()
        self._asr_engine = None
        # C3修复: 跟踪活跃训练子进程，关停时清理
        self._active_processes = []  # List[subprocess.Popen]
        
        self.projects_dir = TRAIN_DATA_ROOT / "web_projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        
        # 注册atexit清理，防止主进程崩溃时子进程成为孤儿
        import atexit
        atexit.register(self._cleanup_processes)
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def _report_progress(self, task_id, step, message, progress=0, total=100, action=""):
        """报告训练进度
        
        Args:
            task_id: 任务ID
            step: 进度阶段 (preparing/training/complete/error/saving/cleaning/running)
            message: 进度消息
            progress: 当前进度百分比
            total: 总进度百分比
            action: 动作类型 (start_training/extract_features/preprocess/prepare_s2_data/start_s2_training)
                    前端需要此字段区分 S1/S2 完成逻辑
        """
        if self.progress_callback:
            self.progress_callback({
                "task_id": task_id,
                "step": step,
                "action": action,
                "message": message,
                "progress": progress,
                "total": total,
                "timestamp": datetime.now().isoformat()
            })
    
    def create_project(self, project_name: str) -> dict:
        """创建新训练项目"""
        project_dir = self.projects_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        
        (project_dir / "raw").mkdir(exist_ok=True)
        (project_dir / "32k").mkdir(exist_ok=True)
        (project_dir / "3-bert").mkdir(exist_ok=True)
        (project_dir / "4-cnhubert").mkdir(exist_ok=True)
        (project_dir / "5-wav32k").mkdir(exist_ok=True)
        (project_dir / "ckpt").mkdir(exist_ok=True)
        
        config_file = project_dir / "config.json"
        default_config = {
            "ref_audio": "",
            "ref_text": "",
            "trained_gpt": None,
            "trained_sovits": None,
            "trained_audios": [],  # 已训练的音频列表
            "created_at": datetime.now().isoformat()
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "project": project_name,
            "path": str(project_dir)
        }
    
    def update_project_config(self, project_name: str, key: str, value):
        """更新项目配置"""
        project_dir = self.projects_dir / project_name
        config_file = project_dir / "config.json"
        
        config = {}
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        
        config[key] = value
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return {"success": True}
    
    def get_project_config(self, project_name: str) -> dict:
        """获取项目配置"""
        project_dir = self.projects_dir / project_name
        config_file = project_dir / "config.json"
        
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def save_train_defaults(self, project_name: str, s1_config: dict = None, s2_config: dict = None) -> dict:
        """保存训练参数默认值到项目 config.json
        
        Args:
            project_name: 项目名称
            s1_config: S1 训练参数（可选，部分更新）
            s2_config: S2 训练参数（可选，部分更新）
        """
        config = self.get_project_config(project_name)
        
        if "train_defaults" not in config:
            config["train_defaults"] = {"s1": {}, "s2": {}}
        
        if s1_config:
            config["train_defaults"]["s1"].update(s1_config)
        if s2_config:
            config["train_defaults"]["s2"].update(s2_config)
        
        project_dir = self.projects_dir / project_name
        config_file = project_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "train_defaults": config["train_defaults"]}
    
    def get_train_defaults(self, project_name: str) -> dict:
        """获取项目的训练参数默认值
        
        Returns:
            dict: {success, s1_defaults, s2_defaults}
        """
        config = self.get_project_config(project_name)
        defaults = config.get("train_defaults", {})
        return {
            "success": True,
            "s1_defaults": defaults.get("s1", {}),
            "s2_defaults": defaults.get("s2", {})
        }
    
    def list_projects(self) -> list:
        """列出所有训练项目"""
        projects = []
        for p in self.projects_dir.iterdir():
            if p.is_dir():
                audio_count = len(_get_audio_files(p / "raw"))
                config = self.get_project_config(p.name)
                projects.append({
                    "name": p.name,
                    "audio_count": audio_count,
                    "path": str(p),
                    "has_checkpoint": (p / "ckpt").exists() and any((p / "ckpt").glob("*.ckpt")),
                    "ref_audio": config.get("ref_audio", ""),
                    "ref_text": config.get("ref_text", ""),
                    "has_trained": config.get("trained_gpt") is not None,
                })
        return projects
    
    def save_audio(self, project_name: str, filename: str, audio_data: bytes) -> dict:
        """保存上传的音频文件"""
        raw_dir = self.projects_dir / project_name / "raw"
        audio_path = raw_dir / filename
        
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        
        config = self.get_project_config(project_name)
        if not config.get("ref_audio"):
            config["ref_audio"] = str(raw_dir / filename)
            self.update_project_config(project_name, "ref_audio", config["ref_audio"])
        
        return {
            "success": True,
            "filename": filename,
            "path": str(audio_path),
            "size": len(audio_data),
            "is_ref": config.get("ref_audio") == str(raw_dir / filename)
        }
    
    def save_text(self, project_name: str, audio_filename: str, text: str) -> dict:
        """保存音频对应的文本"""
        project_dir = self.projects_dir / project_name
        texts_file = project_dir / "texts.json"
        config = self.get_project_config(project_name)

        texts = {}
        if texts_file.exists():
            with open(texts_file, "r", encoding="utf-8") as f:
                texts = json.load(f)

        base_name = audio_filename.rsplit(".", 1)[0]
        # 去除空格和空白
        clean_text = text.replace(" ", "").strip()
        texts[base_name] = clean_text

        # 如果保存的是参考音频的文本，自动更新 config.json 的 ref_text
        ref_audio = config.get("ref_audio", "")
        ref_audio_base = Path(ref_audio).stem if ref_audio else ""
        if base_name == ref_audio_base and clean_text:
            config["ref_text"] = clean_text
            self.update_project_config(project_name, "ref_text", clean_text)
            print(f"[TRAIN] 已更新参考音频文本: {clean_text}")

        with open(texts_file, "w", encoding="utf-8") as f:
            json.dump(texts, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "audio": audio_filename,
            "text_length": len(text)
        }
    
    def _get_asr_engine(self):
        """获取 ASR 引擎（延迟加载）"""
        if self._asr_engine is None:
            try:
                if str(_PROJECT_ROOT) not in sys.path:
                    sys.path.insert(0, str(_PROJECT_ROOT))
                
                from app.asr import ASRFactory
                
                config = {
                    "provider": "funasr",
                    "funasr": {
                        "model": "paraformer-zh",
                        "device": "cuda"
                    }
                }
                self._asr_engine = ASRFactory.create(config)
                
                if self._asr_engine.is_available():
                    print("[TRAIN] FunASR 引擎加载成功")
                else:
                    raise Exception("FunASR 不可用")
                    
            except Exception as e:
                print(f"[TRAIN] FunASR 加载失败: {e}，尝试 Faster-Whisper...")
                try:
                    config = {
                        "provider": "faster_whisper",
                        "faster_whisper": {
                            "model_size": "base",
                            "device": "auto",
                            "compute_type": "float16",
                            "language": "zh"
                        }
                    }
                    self._asr_engine = ASRFactory.create(config)
                    if self._asr_engine.is_available():
                        print("[TRAIN] Faster-Whisper 引擎加载成功")
                except Exception as e2:
                    print(f"[TRAIN] ASR 引擎全部加载失败: {e2}")
                    self._asr_engine = None
        return self._asr_engine
    
    def recognize_audio_text(self, project_name: str, audio_filename: str) -> dict:
        """使用 STT 识别音频文本"""
        project_dir = self.projects_dir / project_name
        
        audio_32k = project_dir / "32k" / audio_filename
        audio_raw = project_dir / "raw" / audio_filename
        
        if audio_32k.exists():
            audio_path = str(audio_32k)
        elif audio_raw.exists():
            audio_path = str(audio_raw)
        else:
            return {"success": False, "error": "音频文件不存在"}
        
        asr = self._get_asr_engine()
        if asr is None:
            return {"success": False, "error": "ASR 引擎不可用"}
        
        if not asr.is_available():
            return {"success": False, "error": "ASR 模型未加载"}
        
        try:
            print(f"[TRAIN] 正在识别: {audio_filename}")
            text = asr.recognize(audio_path)
            
            if text:
                # 去除空格
                clean_text = text.replace(" ", "").strip()
                self.save_text(project_name, audio_filename, clean_text)
                return {
                    "success": True,
                    "filename": audio_filename,
                    "text": clean_text,
                    "auto_saved": True
                }
            else:
                return {"success": False, "error": "未能识别出文本"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_project_info(self, project_name: str) -> dict:
        """获取项目详细信息"""
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return {"success": False, "error": "项目不存在"}
        
        # 优先从 32k 目录获取（原始音频可能已被删除）
        processed_dir = project_dir / "32k"
        raw_dir = project_dir / "raw"
        texts_file = project_dir / "texts.json"
        config = self.get_project_config(project_name)
        
        texts = {}
        if texts_file.exists():
            with open(texts_file, "r", encoding="utf-8") as f:
                texts = json.load(f)
        
        trained_audios = set(config.get("trained_audios", []))
        
        audio_files = []
        # 从 32k 目录获取（优先），同时也扫描 raw 目录（防止遗漏）
        seen_names = set()
        for audio_dir in [processed_dir, raw_dir]:
            if not audio_dir.exists():
                continue
            for f in _get_audio_files(audio_dir):
                if f.stem in seen_names:
                    continue  # 避免重复
                seen_names.add(f.stem)
                base_name = f.stem
                raw_text = texts.get(base_name, "")
                clean_text = raw_text.replace(" ", "").strip() if raw_text else ""
                audio_files.append({
                    "filename": f.name,
                    "has_text": bool(clean_text),
                    "text": clean_text,
                    "size": f.stat().st_size,
                    "is_trained": base_name in trained_audios
                })
        
        ckpt_dir = project_dir / "ckpt"
        ckpt_files = list(ckpt_dir.glob("*.ckpt"))
        
        # 同时扫描 S2 模型文件（s2_ckpt/*.pth）
        s2_ckpt_dir = project_dir / "s2_ckpt"
        sovits_files = list(s2_ckpt_dir.glob("*.pth")) if s2_ckpt_dir.exists() else []
        
        # 获取配置的模型路径（最新训练的）
        config = self.get_project_config(project_name)
        active_gpt = config.get("trained_gpt", "")
        active_sovits = config.get("trained_sovits", "")
        # 提取文件名用于比较
        active_gpt_name = Path(active_gpt).name if active_gpt else ""
        active_sovits_name = Path(active_sovits).name if active_sovits else ""
        
        checkpoints = []
        for c in ckpt_files:
            is_active = (c.name == active_gpt_name)
            checkpoints.append({
                "name": c.name,
                "path": str(c).replace("\\", "/"),
                "is_active": is_active,
                "size": c.stat().st_size,
                "epoch": int(c.stem.split("-e")[-1]) if "-e" in c.stem else 0,
                "type": "gpt"
            })
        
        for c in sovits_files:
            is_active = (c.name == active_sovits_name)
            checkpoints.append({
                "name": c.name,
                "path": str(c).replace("\\", "/"),
                "is_active": is_active,
                "size": c.stat().st_size,
                "epoch": int(c.stem.split("_e")[-1].split("_")[0]) if "_e" in c.stem else 0,
                "type": "sovits"
            })
        
        # 排序：GPT 在前，SoVITS 在后，各自按 epoch 降序
        checkpoints.sort(key=lambda x: (0 if x["type"] == "gpt" else 1, -x["epoch"]))
        
        # 计算待训练数量（有文本但未训练的）
        pending_count = len([f for f in audio_files if f["has_text"] and not f["is_trained"]])
        
        # 检查预处理状态（32k音频）
        preprocessed_count = 0
        if processed_dir.exists():
            preprocessed_count = len(list(processed_dir.glob("*.wav")))
        
        # 检查特征提取状态（4-cnhubert目录）
        extracted_count = 0
        cnhubert_dir = project_dir / "4-cnhubert"
        if cnhubert_dir.exists():
            extracted_count = len(list(cnhubert_dir.glob("*.pt")))
        
        # 检查S2训练数据（2-name2text.txt）
        has_s2_data = (project_dir / "2-name2text.txt").exists()
        
        # 检查S2训练结果
        has_s2_trained = False
        s2_dir = project_dir / "s2_ckpt"
        if s2_dir.exists():
            s2_files = list(s2_dir.glob("*.pth"))
            has_s2_trained = len(s2_files) > 0

        # 调试日志
        print(f"[DEBUG] 项目 {project_name}:")
        print(f"  - audio_files 数量: {len(audio_files)}")
        print(f"  - trained_audios: {sorted(trained_audios)}")
        print(f"  - trained_count: {len(trained_audios)}")
        print(f"  - pending_count: {pending_count}")
        for f in audio_files:
            print(f"    {f['filename']}: has_text={f['has_text']}, is_trained={f['is_trained']}")
        
        return {
            "success": True,
            "name": project_name,
            "path": str(project_dir),
            "audio_files": audio_files,
            "texts_count": len(texts),
            "checkpoints": checkpoints,
            "trained_audios": list(trained_audios),
            "trained_count": len(trained_audios),
            "pending_count": pending_count,
            # 流程状态
            "preprocessed_count": preprocessed_count,
            "extracted_count": extracted_count,
            "has_s2_data": has_s2_data,
            "has_s2_trained": has_s2_trained
        }
    
    def delete_audio(self, project_name: str, filename: str) -> dict:
        """删除单个音频文件及其相关数据
        
        Args:
            project_name: 项目名称
            filename: 音频文件名
            
        Returns:
            删除结果
        """
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return {"success": False, "error": "项目不存在"}
        
        deleted_items = []
        base_name = Path(filename).stem  # 去掉扩展名
        
        # 1. 删除原始音频 (raw/)
        raw_file = project_dir / "raw" / filename
        if raw_file.exists():
            raw_file.unlink()
            deleted_items.append(f"raw/{filename}")
        
        # 2. 删除 32k 音频
        file_32k = project_dir / "32k" / filename
        if file_32k.exists():
            file_32k.unlink()
            deleted_items.append(f"32k/{filename}")
        
        # 3. 删除特征文件（.pt 和 .npy 格式，含 .wav 后缀的官方命名）
        wav_name = base_name + ".wav"
        for feature_dir in ["3-bert", "4-cnhubert", "5-wav32k"]:
            for ext in [f"{wav_name}.pt", f"{base_name}.pt", f"{base_name}.npy", wav_name, f"{base_name}.txt"]:
                feature_file = project_dir / feature_dir / ext
                if feature_file.exists():
                    feature_file.unlink()
                    deleted_items.append(f"{feature_dir}/{ext}")
        
        # 4. 从 texts.json 中删除文本
        texts_file = project_dir / "texts.json"
        if texts_file.exists():
            with open(texts_file, "r", encoding="utf-8") as f:
                texts = json.load(f)
            if base_name in texts:
                del texts[base_name]
                with open(texts_file, "w", encoding="utf-8") as f:
                    json.dump(texts, f, ensure_ascii=False, indent=2)
                deleted_items.append("texts.json 中的文本")
        
        # 5. 从 trained_audios 中移除
        config = self.get_project_config(project_name)
        if base_name in config.get("trained_audios", []):
            config["trained_audios"] = [x for x in config.get("trained_audios", []) if x != base_name]
            self.save_project_config(project_name, config)
            deleted_items.append("trained_audios 记录")
        
        print(f"[DELETE] 已删除 {project_name}/{filename}: {deleted_items}")
        
        return {
            "success": True,
            "deleted": deleted_items,
            "message": f"已删除 {filename}"
        }
    
    def save_project_config(self, project_name: str, config: dict):
        """保存项目完整配置"""
        project_dir = self.projects_dir / project_name
        config_file = project_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def delete_s1_training(self, project_name: str) -> dict:
        """单独删除 S1 训练产物（保留音频、特征、S2 模型）
        
        删除内容：
        - S1 checkpoint 模型 (ckpt/*.ckpt)
        - S1 训练输出目录 (GPT-SoVITS/data/web_{name}/)
        - S1 YAML 配置
        - S1 训练数据文件 (2-name2text-0.txt, 6-name2semantic-0.tsv, filelist_for_semantic.txt)
        - config.json 中的 trained_gpt / trained_audios / trained_at
        
        不删除：原始音频、32k音频、特征文件(3-bert/4-cnhubert)、S2 模型(s2_ckpt)、ref_audio/ref_text
        """
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return {"success": False, "error": "项目不存在"}
        
        deleted_items = []
        try:
            # 1. 删除 S1 checkpoint
            ckpt_dir = project_dir / "ckpt"
            if ckpt_dir.exists():
                for f in ckpt_dir.glob("*.ckpt"):
                    f.unlink()
                    deleted_items.append(f"模型: {f.name}")
            
            # 2. 删除 S1 训练输出目录
            gpt_data_dir = TRAIN_DATA_ROOT / f"web_{project_name}"
            if gpt_data_dir.exists():
                shutil.rmtree(gpt_data_dir)
                deleted_items.append(f"训练目录: {gpt_data_dir.name}/")
            
            # 3. 删除 S1 YAML 配置
            yaml_file = GPT_SOVITS_ROOT / "GPT_SoVITS" / "configs" / f"s1_web_{project_name}.yaml"
            if yaml_file.exists():
                yaml_file.unlink()
                deleted_items.append(f"配置: {yaml_file.name}")
            
            # 4. 删除 S1 训练数据文件
            for data_file in ["2-name2text-0.txt", "6-name2semantic-0.tsv", "filelist_for_semantic.txt"]:
                data_path = project_dir / data_file
                if data_path.exists():
                    data_path.unlink()
                    deleted_items.append(f"数据: {data_file}")
            
            # 5. 重置 config.json 中的 S1 相关字段（保留 S2 和 ref_audio/ref_text）
            config = self.get_project_config(project_name)
            config["trained_gpt"] = None
            config["trained_audios"] = []
            config["trained_at"] = None
            self.save_project_config(project_name, config)
            deleted_items.append("配置: trained_gpt/trained_audios 已重置")
            
            print(f"[DELETE_S1] {project_name}: 删除了 {len(deleted_items)} 项")
            return {"success": True, "deleted": deleted_items}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_s2_training(self, project_name: str) -> dict:
        """单独删除 S2 训练产物（保留音频、特征、S1 模型）
        
        删除内容：
        - S2 checkpoint (project_dir/s2_ckpt/*.pth)
        - S2 训练日志目录 (GPT-SoVITS/logs/web_{name}/)
        - S2 导出权重 (GPT-SoVITS/SoVITS_weights_v3/web_{name}*.pth)
        - S2 训练数据文件 (2-name2text.txt, 用于S2的)
        - config.json 中的 trained_sovits
        
        不删除：S1 模型(ckpt/)、原始音频、特征文件、ref_audio/ref_text
        """
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return {"success": False, "error": "项目不存在"}
        
        deleted_items = []
        try:
            s2_exp_name = f"web_{project_name}"
            
            # 1. 删除 S2 checkpoint (项目目录下)
            s2_ckpt_dir = project_dir / "s2_ckpt"
            if s2_ckpt_dir.exists():
                for f in s2_ckpt_dir.glob("*.pth"):
                    f.unlink()
                    deleted_items.append(f"S2模型: {f.name}")
            
            # 2. 删除 S2 训练日志目录 (GPT-SoVITS/logs/web_{name}/)
            s2_log_dir = GPT_SOVITS_ROOT / "logs" / s2_exp_name
            if s2_log_dir.exists():
                shutil.rmtree(s2_log_dir)
                deleted_items.append(f"S2日志: logs/{s2_exp_name}/")
            
            # 3. 删除 S2 导出权重 (SoVITS_weights_v3/web_{name}*.pth)
            sovits_weights_dir = GPT_SOVITS_ROOT / "SoVITS_weights_v3"
            if sovits_weights_dir.exists():
                for f in sovits_weights_dir.glob(f"{s2_exp_name}*.pth"):
                    f.unlink()
                    deleted_items.append(f"S2权重: {f.name}")
            
            # 4. 删除 S2 训练数据文件
            for data_file in ["2-name2text.txt"]:
                data_path = project_dir / data_file
                if data_path.exists():
                    data_path.unlink()
                    deleted_items.append(f"数据: {data_file}")
            
            # 5. 重置 config.json 中的 S2 相关字段
            config = self.get_project_config(project_name)
            config["trained_sovits"] = None
            self.save_project_config(project_name, config)
            deleted_items.append("配置: trained_sovits 已重置")
            
            print(f"[DELETE_S2] {project_name}: 删除了 {len(deleted_items)} 项")
            return {"success": True, "deleted": deleted_items}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def reset_project(self, project_name: str, delete_all: bool = False) -> dict:
        """重置项目 - 删除训练模型和已训练记录
        
        Args:
            project_name: 项目名称
            delete_all: 是否删除所有数据（包括原始音频），默认 False 只删除训练相关
        """
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return {"success": False, "error": "项目不存在"}
        
        try:
            deleted_items = []
            
            # 1. 删除训练模型（projects_dir 下的 ckpt 目录）
            ckpt_dir = project_dir / "ckpt"
            if ckpt_dir.exists():
                ckpt_count = len(list(ckpt_dir.glob("*.ckpt")))
                for ckpt_file in ckpt_dir.glob("*.ckpt"):
                    ckpt_file.unlink()
                    deleted_items.append(f"模型: {ckpt_file.name}")
                print(f"[RESET] 已删除 {ckpt_count} 个训练模型")
            
            # 2. 删除训练输出目录（web_{project}/）
            gpt_data_dir = TRAIN_DATA_ROOT / f"web_{project_name}"
            if gpt_data_dir.exists():
                import shutil
                shutil.rmtree(gpt_data_dir)
                deleted_items.append(f"训练目录: {gpt_data_dir.name}/")
                print(f"[RESET] 已删除训练目录: {gpt_data_dir}")
            
            # 3. 删除 YAML 配置文件
            gpt_root = GPT_SOVITS_ROOT / "GPT_SoVITS"
            yaml_file = gpt_root / "configs" / f"s1_web_{project_name}.yaml"
            if yaml_file.exists():
                yaml_file.unlink()
                deleted_items.append(f"配置: {yaml_file.name}")
                print(f"[RESET] 已删除 YAML 配置: {yaml_file}")
            
            # 3.5 删除 logs 下的训练输出目录（残留数据会导致数据复制被跳过）
            logs_data_dir = GPT_SOVITS_ROOT / "logs" / f"web_{project_name}"
            if logs_data_dir.exists():
                import shutil
                shutil.rmtree(logs_data_dir)
                deleted_items.append(f"日志目录: logs/{logs_data_dir.name}/")
                print(f"[RESET] 已删除日志目录: {logs_data_dir}")
            
            # 4. 删除训练数据文件
            train_data_files = [
                "2-name2text-0.txt",
                "6-name2semantic-0.tsv",
                "filelist_for_semantic.txt",
            ]
            for data_file in train_data_files:
                data_path = project_dir / data_file
                if data_path.exists():
                    data_path.unlink()
                    deleted_items.append(f"训练数据: {data_file}")
                    print(f"[RESET] 已删除: {data_path}")
            
            # 5. 删除训练生成的特征文件
            for feature_dir in ["3-bert", "4-cnhubert", "5-wav32k"]:
                feature_path = project_dir / feature_dir
                if feature_path.exists():
                    feature_count = len(list(feature_path.glob("*")))
                    for f in feature_path.glob("*"):
                        f.unlink()
                    deleted_items.append(f"特征: {feature_dir}/ ({feature_count}个文件)")
            
            # 6. 重置 config.json 中的训练相关字段
            config = self.get_project_config(project_name)
            config["trained_gpt"] = None
            config["trained_sovits"] = None
            config["trained_audios"] = []
            config["trained_at"] = None
            self.save_project_config(project_name, config)
            deleted_items.append("配置: trained_* 重置")
            
            # 7. 如果 delete_all=True，删除所有数据
            if delete_all:
                # 删除原始音频
                raw_dir = project_dir / "raw"
                if raw_dir.exists():
                    raw_files = _get_audio_files(raw_dir)
                    raw_count = len(raw_files)
                    for wav in raw_files:
                        wav.unlink()
                    deleted_items.append(f"原始音频: {raw_count} 个")
                
                # 删除 32k 音频
                audio_32k_dir = project_dir / "32k"
                if audio_32k_dir.exists():
                    audio_32k_files = _get_audio_files(audio_32k_dir)
                    audio_count = len(audio_32k_files)
                    for wav in audio_32k_files:
                        wav.unlink()
                    deleted_items.append(f"32k音频: {audio_count} 个")
                
                # 删除 texts.json
                texts_file = project_dir / "texts.json"
                if texts_file.exists():
                    texts_file.unlink()
                    deleted_items.append("文本: texts.json")
                
                # 重置 ref_audio 和 ref_text
                config["ref_audio"] = ""
                config["ref_text"] = ""
                self.save_project_config(project_name, config)
                deleted_items.append("配置: ref_* 重置")
                
                print(f"[RESET] 已删除项目所有数据: {project_name}")
            else:
                print(f"[RESET] 已重置训练数据（保留音频）: {project_name}")
            
            return {
                "success": True,
                "message": "项目已重置",
                "deleted_items": deleted_items,
                "delete_all": delete_all
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def switch_checkpoint(self, project_name: str, checkpoint_name: str) -> dict:
        """切换项目使用的模型
        
        根据文件扩展名自动判断类型：
        - .ckpt → GPT 模型（S1 AR Transformer），存放在 ckpt/ 目录
        - .pth  → SoVITS 模型（S2 Diffusion），存放在 s2_ckpt/ 目录
        """
        project_dir = self.projects_dir / project_name
        ckpt_dir = project_dir / "ckpt"
        s2_ckpt_dir = project_dir / "s2_ckpt"

        # 根据扩展名确定查找目录
        suffix = Path(checkpoint_name).suffix.lower()
        if suffix == ".ckpt":
            checkpoint_path = ckpt_dir / checkpoint_name
        elif suffix == ".pth":
            checkpoint_path = s2_ckpt_dir / checkpoint_name
        else:
            checkpoint_path = ckpt_dir / checkpoint_name
            if not checkpoint_path.exists():
                checkpoint_path = s2_ckpt_dir / checkpoint_name

        if not checkpoint_path.exists():
            return {"success": False, "error": f"模型文件不存在: {checkpoint_name}"}
        
        # 更新 config.json（根据文件类型区分 GPT/S2）
        config = self.get_project_config(project_name)
        ckpt_str = str(checkpoint_path).replace("\\", "/")
        if checkpoint_name.endswith(".ckpt"):
            # .ckpt 是 GPT 权重
            config["trained_gpt"] = ckpt_str
        elif checkpoint_name.endswith(".pth"):
            # .pth 是 SoVITS 权重
            config["trained_sovits"] = ckpt_str
        else:
            # 无法判断类型，默认只更新 GPT
            config["trained_gpt"] = ckpt_str
        self.save_project_config(project_name, config)
        
        return {"success": True, "checkpoint": checkpoint_name}
    
    def preprocess_audio(self, project_name: str, audio_filename: str = None) -> dict:
        """预处理音频 - 转换为32kHz单声道"""
        project_dir = self.projects_dir / project_name
        raw_dir = project_dir / "raw"
        out_dir = project_dir / "32k"
        
        if audio_filename:
            # 如果指定了文件名，检查 raw 和 32k 目录
            raw_file = raw_dir / audio_filename
            if raw_file.exists():
                files_to_process = [raw_file]
            elif (out_dir / audio_filename).exists():
                return {"success": True, "message": f"音频 {audio_filename} 已预处理"}  # 已处理
            else:
                return {"success": False, "error": f"没有找到音频文件: {audio_filename}"}
        else:
            # 获取所有支持的音频文件
            raw_files = _get_audio_files(raw_dir) if raw_dir.exists() else []
            if not raw_files:
                # raw 目录为空，检查 32k 目录是否有文件
                out_files = _get_audio_files(out_dir) if out_dir.exists() else []
                if out_files:
                    return {"success": True, "message": f"已有 {len(out_files)} 个预处理音频"}  # 全部已处理
                return {"success": False, "error": "没有找到音频文件"}
            files_to_process = raw_files
        
        if not files_to_process:
            return {"success": False, "error": "没有找到音频文件"}
        
        try:
            import soundfile as sf
            import numpy as np
            from scipy import signal
            
            os.makedirs(out_dir, exist_ok=True)
            
            for audio_file in files_to_process:
                try:
                    audio, sr = sf.read(audio_file)
                    print(f"处理 {audio_file.name}: sr={sr}, shape={audio.shape}")
                    
                    if audio.ndim > 1:
                        audio = audio.mean(axis=1)
                    
                    if sr != 32000:
                        num_samples = int(len(audio) * 32000 / sr)
                        audio = signal.resample(audio, num_samples)
                    
                    dst_path = out_dir / audio_file.name
                    sf.write(dst_path, audio.astype(np.float32), 32000)
                    print(f"已保存: {dst_path}")
                except Exception as e:
                    print(f"处理失败 {audio_file.name}: {e}")
                    return {"success": False, "error": f"处理 {audio_file.name} 失败: {e}"}
            
            config = self.get_project_config(project_name)
            if config.get("ref_audio"):
                old_ref = Path(config["ref_audio"])
                new_ref = out_dir / old_ref.name
                if new_ref.exists():
                    self.update_project_config(project_name, "ref_audio", str(new_ref))
                    print(f"已更新参考音频路径: {new_ref}")
            
            return {"success": True, "message": f"预处理完成，共处理 {len(files_to_process)} 个文件"}
        except ImportError as e:
            return {"success": False, "error": f"缺少依赖: {e}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def extract_features(self, project_name: str) -> dict:
        """提取BERT和HuBERT特征（严格遵循官方 1-get-text.py + 2-get-hubert-wav32k.py 流程）
        
        官方流程:
        1. 1-get-text.py: clean_text() → 音素 + word2ph + BERT特征(.pt)
        2. 2-get-hubert-wav32k.py: load_audio(32kHz) → 音量归一化 → 重采样16kHz → HuBERT → .pt [1,768,T]
                                     同时保存 5-wav32k/ 音频（int16 PCM）
        
        关键规范:
        - 3-bert/{name}.pt: BERT 特征 [1024, num_phones]（S1 dataset.py 必需）
        - 4-cnhubert/{name}.pt: HuBERT 特征 [1, 768, T]（S1 + S2 必需）
        - 5-wav32k/{name}: 32kHz int16 PCM 音频（S2 训练必需）
        - name 格式：原始文件名（含 .wav 后缀，如 "录音.wav"）
        """
        project_dir = self.projects_dir / project_name
        wav32k_dir = project_dir / "32k"
        bert_dir_path = project_dir / "3-bert"
        hubert_dir = project_dir / "4-cnhubert"
        wav32k_out_dir = project_dir / "5-wav32k"
        texts_file = project_dir / "texts.json"
        
        if not texts_file.exists():
            return {"success": False, "error": "没有找到训练文本"}
        
        if not _get_audio_files(wav32k_dir):
            return {"success": False, "error": "没有找到 32kHz 音频文件"}
        
        try:
            import torch
            import numpy as np
            
            # 添加路径
            gpt_root = str(GPT_SOVITS_ROOT).replace("\\", "/")
            if gpt_root not in sys.path:
                sys.path.insert(0, gpt_root)
            gptsovits_text = gpt_root + "/GPT_SoVITS/text"
            if gptsovits_text not in sys.path:
                sys.path.insert(0, gptsovits_text)
            
            for d in [bert_dir_path, hubert_dir, wav32k_out_dir]:
                d.mkdir(parents=True, exist_ok=True)
            
            with open(texts_file, "r", encoding="utf-8") as f:
                texts = json.load(f)
            
            is_half = torch.cuda.is_available()
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            
            print(f"[FEATURE] 开始提取特征，项目: {project_name}")
            print(f"[FEATURE] 设备: {device}, half: {is_half}")
            print(f"[FEATURE] 文本数量: {len(texts)}")
            
            # === 初始化 BERT 模型（官方 1-get-text.py）===
            print(f"[FEATURE] 加载 BERT 模型...")
            from transformers import AutoModelForMaskedLM, AutoTokenizer
            bert_pretrained_dir = str(GPT_SOVITS_ROOT / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large")
            tokenizer = AutoTokenizer.from_pretrained(bert_pretrained_dir)
            bert_model = AutoModelForMaskedLM.from_pretrained(bert_pretrained_dir)
            if is_half:
                bert_model = bert_model.half().to(device)
            else:
                bert_model = bert_model.to(device)
            
            def get_bert_feature(text, word2ph):
                """官方 1-get-text.py 中的 BERT 特征提取方法"""
                with torch.no_grad():
                    inputs = tokenizer(text, return_tensors="pt")
                    for i in inputs:
                        inputs[i] = inputs[i].to(device)
                    res = bert_model(**inputs, output_hidden_states=True)
                    res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()[1:-1]
                
                assert len(word2ph) == len(text), f"word2ph长度{len(word2ph)}!=文本长度{len(text)}"
                phone_level_feature = []
                for i in range(len(word2ph)):
                    repeat_feature = res[i].repeat(word2ph[i], 1)
                    phone_level_feature.append(repeat_feature)
                
                phone_level_feature = torch.cat(phone_level_feature, dim=0)
                return phone_level_feature.T  # [1024, num_phones]
            
            # === 初始化 HuBERT 模型（官方 2-get-hubert-wav32k.py）===
            print(f"[FEATURE] 加载 HuBERT 模型...")
            from feature_extractor import cnhubert
            cnhubert.cnhubert_base_path = str(GPT_SOVITS_ROOT / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base")
            hubert_model = cnhubert.get_model()
            if is_half:
                hubert_model = hubert_model.half().to(device)
            else:
                hubert_model = hubert_model.to(device)
            
            # === 使用官方 clean_text 提取音素（而非 g2p）===
            from text.cleaner import clean_text
            
            # 官方音量归一化参数
            maxx = 0.95
            alpha = 0.5
            
            processed = 0
            skipped_bert = 0
            skipped_hubert = 0
            
            for audio_file in _get_audio_files(wav32k_dir):
                name = audio_file.stem  # 不含扩展名
                if name not in texts:
                    print(f"[FEATURE] 跳过 {name}: 没有对应文本")
                    continue
                
                raw_text = texts[name].strip()
                if not raw_text:
                    print(f"[FEATURE] 跳过 {name}: 文本为空")
                    continue
                
                # name 带 .wav 后缀（官方规范）
                wav_name = name + ".wav"
                
                print(f"[FEATURE] 处理: {wav_name}")
                
                # ========== 步骤1: 音素提取 + BERT 特征（官方 1-get-text.py）==========
                try:
                    # 官方使用 clean_text() 而非 g2p()
                    # clean_text 返回 (phones, word2ph, norm_text)
                    phones, word2ph, norm_text = clean_text(
                        raw_text.replace("%", "-").replace("￥", ","), 
                        "zh",  # 语言
                        "v3"  # 版本（v2/v2Pro/v3 使用相同的音素符号表）
                    )
                except Exception as e:
                    print(f"[FEATURE] clean_text 失败 {name}: {e}")
                    # 回退到 g2p
                    try:
                        from text.chinese import g2p
                        cleaned = _clean_text_for_g2p(raw_text)
                        phones_str, word2ph = g2p(cleaned)
                        phones = phones_str
                        norm_text = cleaned
                    except Exception as e2:
                        print(f"[FEATURE] g2p 也失败 {name}: {e2}")
                        continue
                
                # 保存 BERT 特征到 3-bert/{name}.pt（官方 1-get-text.py 格式）
                bert_pt_path = bert_dir_path / f"{wav_name}.pt"
                if not bert_pt_path.exists():
                    try:
                        bert_feature = get_bert_feature(norm_text, word2ph)
                        assert bert_feature.shape[-1] == len(phones), \
                            f"BERT特征长度{bert_feature.shape[-1]}!=音素数量{len(phones)}"
                        # 官方使用 my_save 避免中文路径问题，我们直接 torch.save
                        torch.save(bert_feature, str(bert_pt_path))
                        print(f"[FEATURE]   BERT: {bert_feature.shape}")
                    except Exception as e:
                        print(f"[FEATURE]   BERT提取失败: {e}")
                        skipped_bert += 1
                
                # 同时保存音素文本（供 S2 name2text 使用）
                bert_txt_path = bert_dir_path / f"{name}.txt"
                if not bert_txt_path.exists():
                    with open(bert_txt_path, "w", encoding="utf-8") as f:
                        f.write(" ".join(phones))
                
                # ========== 步骤2: HuBERT 特征 + 32k音频保存（官方 2-get-hubert-wav32k.py）==========
                hubert_pt_path = hubert_dir / f"{wav_name}.pt"
                
                if not hubert_pt_path.exists():
                    try:
                        # 官方 2-get-hubert-wav32k.py: load_audio → 音量归一化 → 重采样16kHz → HuBERT
                        from tools.my_utils import load_audio
                        tmp_audio = load_audio(str(audio_file), 32000)  # 加载为 32kHz float32
                        tmp_max = np.abs(tmp_audio).max()
                        
                        if tmp_max > 2.2:
                            print(f"[FEATURE]   音频振幅过大 {tmp_max:.2f}，跳过HuBERT")
                            skipped_hubert += 1
                            continue
                        
                        # 官方音量归一化
                        tmp_audio32 = (tmp_audio / tmp_max * (maxx * alpha * 32768)) + ((1 - alpha) * 32768) * tmp_audio
                        tmp_audio32b = (tmp_audio / tmp_max * (maxx * alpha * 1145.14)) + ((1 - alpha) * 1145.14) * tmp_audio
                        
                        # 保存 5-wav32k/ 音频（int16 PCM，官方格式）
                        wav32k_out_path = wav32k_out_dir / wav_name
                        if not wav32k_out_path.exists():
                            from scipy.io import wavfile
                            wavfile.write(str(wav32k_out_path), 32000, tmp_audio32.astype("int16"))
                        
                        # 重采样到 16kHz 给 HuBERT（官方明确 16kHz 输入）
                        import librosa
                        tmp_audio_16k = librosa.resample(tmp_audio32b, orig_sr=32000, target_sr=16000)
                        
                        # HuBERT 推理
                        tensor_wav16 = torch.from_numpy(tmp_audio_16k)
                        if is_half:
                            tensor_wav16 = tensor_wav16.half().to(device)
                        else:
                            tensor_wav16 = tensor_wav16.to(device)
                        
                        with torch.no_grad():
                            # 官方: model.model(tensor_wav16.unsqueeze(0))["last_hidden_state"].transpose(1, 2).cpu()
                            ssl = hubert_model.model(tensor_wav16.unsqueeze(0))["last_hidden_state"].transpose(1, 2).cpu()
                            # ssl: [1, 768, T] — 官方格式，直接保存
                        
                        # 检查 NaN
                        if np.isnan(ssl.detach().numpy()).sum() != 0:
                            print(f"[FEATURE]   HuBERT 输出含 NaN，跳过")
                            skipped_hubert += 1
                            continue
                        
                        # 保存 HuBERT 特征（官方格式 [1, 768, T]）
                        torch.save(ssl, str(hubert_pt_path))
                        print(f"[FEATURE]   HuBERT: {ssl.shape} (官方格式 [1,768,T])")
                        
                        # 同时保存旧 .npy 格式（兼容旧逻辑回退）
                        npy_path = hubert_dir / f"{name}.npy"
                        if not npy_path.exists():
                            np.save(npy_path, ssl.squeeze(0).transpose(0, 1).numpy())  # [T, 768]
                        
                    except Exception as e:
                        print(f"[FEATURE]   HuBERT提取失败: {e}")
                        import traceback
                        traceback.print_exc()
                        skipped_hubert += 1
                else:
                    print(f"[FEATURE]   HuBERT已存在: {hubert_pt_path.name}")
                
                processed += 1
            
            # 释放 GPU 显存
            del bert_model
            del hubert_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            msg = f"特征提取完成! 处理了 {processed} 个文件"
            if skipped_bert > 0:
                msg += f" (BERT跳过: {skipped_bert})"
            if skipped_hubert > 0:
                msg += f" (HuBERT跳过: {skipped_hubert})"
            print(f"[FEATURE] {msg}")
            return {"success": True, "message": msg}
            
        except ImportError as e:
            return {"success": False, "error": f"缺少依赖: {e}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def start_training(self, project_name: str, config: dict = None) -> dict:
        """启动训练"""
        with self._lock:
            if self.is_training:
                return {"success": False, "error": "已有训练任务正在进行"}
            self.is_training = True
        
        task_id = f"{project_name}_{int(time.time())}"
        self.current_task = {
            "task_id": task_id,
            "project_name": project_name,
            "status": "running"
        }
        
        thread = threading.Thread(
            target=self._run_training,
            args=(task_id, project_name, config)
        )
        thread.daemon = True
        thread.start()
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "训练已启动"
        }
    
    def _run_training(self, task_id: str, project_name: str, config: dict = None):
        """执行真正的 GPT-SoVITS 训练（后台线程）
        
        严格遵循官方 webui.py open1Bb() 的流程：
        1. 读取 s1longer-v2.yaml 模板
        2. 填充配置字段
        3. 使用 subprocess 调用 s1_train.py（与官方一致）
        """
        import shutil
        import yaml
        
        project_dir = self.projects_dir / project_name
        gpt_dir = GPT_SOVITS_ROOT
        
        # 【关键】训练版本：用户只有 s2Gv3.pth，使用 v3
        train_version = "v3"
        
        train_config = {
            # S1 基础参数
            "epochs": 100,
            "batch_size": 8,
            "learning_rate": 0.0001,
            # S1 高级参数
            "dropout": 0.0,
            "grad_clip": 1.0,
            "warmup_steps": 1000,
            "save_freq": 5,
            # DPO（官方默认关闭）
            "if_dpo": False,
        }
        if config:
            train_config.update(config)
        
        try:
            # ============ 阶段1: 检查已有特征 ============
            self._report_progress(task_id, "preparing", "📁 准备训练数据...", 5, 100)
            
            audio_32k_dir = project_dir / "32k"
            bert_dir = project_dir / "3-bert"
            hubert_dir = project_dir / "4-cnhubert"
            raw_dir = project_dir / "raw"
            
            if not audio_32k_dir.exists() or not _get_audio_files(audio_32k_dir):
                self._report_progress(task_id, "error", "请先预处理音频（转32kHz）", 0, 100)
                return
            
            if not bert_dir.exists() or not list(bert_dir.glob("*.pt")):
                self._report_progress(task_id, "error", "请先执行特征提取步骤（生成BERT .pt特征）", 0, 100)
                return
            
            if not hubert_dir.exists() or not list(hubert_dir.glob("*.pt")):
                self._report_progress(task_id, "error", "请先执行特征提取步骤（生成HuBERT .pt特征）", 0, 100)
                return
            
            texts_file = project_dir / "texts.json"
            if not texts_file.exists():
                self._report_progress(task_id, "error", "没有找到训练文本，请先进行语音识别", 0, 100)
                return
            
            with open(texts_file, "r", encoding="utf-8") as f:
                texts = json.load(f)
            
            # 获取已训练的音频列表
            config_path = project_dir / "config.json"
            with open(config_path, "r", encoding="utf-8") as f:
                project_config = json.load(f)
            trained_audios = set(project_config.get("trained_audios", []))
            
            # retrain 模式：忽略已训练标记，使用全部音频
            is_retrain = train_config.get("retrain", False)
            if is_retrain:
                print(f"[TRAIN] 重训模式: 忽略已训练标记，使用全部音频")
            
            # 收集有效音频（排除已训练的，除非 retrain=True）
            valid_audios = []
            skipped_count = 0
            for audio_file in _get_audio_files(audio_32k_dir):
                name = audio_file.stem
                
                # 跳过已训练的音频（retrain 模式下跳过此检查）
                if not is_retrain and name in trained_audios:
                    skipped_count += 1
                    continue
                
                if name not in texts or not texts[name].strip():
                    continue
                # 官方格式：BERT .pt = {name}.wav.pt，HuBERT .pt = {name}.wav.pt
                wav_name = name + ".wav"
                bert_pt = bert_dir / f"{wav_name}.pt"
                hubert_pt = hubert_dir / f"{wav_name}.pt"
                # 回退兼容：也可能存在无 .wav 后缀的旧格式
                if not bert_pt.exists():
                    bert_pt = bert_dir / f"{name}.pt"
                if not hubert_pt.exists():
                    hubert_pt = hubert_dir / f"{name}.pt"
                if bert_pt.exists() and hubert_pt.exists():
                    valid_audios.append({
                        "name": name,
                        "text": texts[name].strip().replace(" ", ""),
                        "audio_path": str(audio_file),
                        "bert_path": str(bert_pt),
                        "hubert_path": str(hubert_pt)
                    })
            
            if skipped_count > 0:
                print(f"[TRAIN] 跳过 {skipped_count} 个已训练的音频")
            
            if len(valid_audios) < 1:
                self._report_progress(task_id, "error", "没有新音频需要训练（所有音频已训练过）", 0, 100)
                return
            
            # ============ 阶段1.5: 自动设置参考音频（如果没有） ============
            if not project_config.get("ref_audio") or not project_config.get("ref_text"):
                # 使用第一个有效音频作为参考
                first_audio = valid_audios[0]
                ref_audio_path = first_audio["audio_path"]
                ref_text = first_audio["text"]
                
                # 转换为 32k 音频作为参考音频
                ref_32k_path = Path(ref_audio_path)  # 已经是 32k 目录下的
                
                project_config["ref_audio"] = str(ref_32k_path).replace("\\", "/")
                project_config["ref_text"] = ref_text
                
                # 立即保存到 config.json
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(project_config, f, indent=2, ensure_ascii=False)
                
                print(f"[TRAIN] 自动设置参考音频: {ref_32k_path.name}")
                print(f"[TRAIN] 参考文本: {ref_text}")
            
            self._report_progress(task_id, "preparing", f"✅ 找到 {len(valid_audios)} 个新音频（跳过 {skipped_count} 个已训练的）", 10, 100)
            
            # ============ 阶段2: 复制数据 ============
            self._report_progress(task_id, "preparing", "📂 复制训练数据...", 15, 100)
            
            gpt_data_dir = gpt_dir / "data" / f"web_{project_name}"
            wav_dir = gpt_data_dir / "5-wav32k"
            bert_feature_dir = gpt_data_dir / "3-bert"
            hubert_feature_dir = gpt_data_dir / "4-cnhubert"
            
            for d in [wav_dir, bert_feature_dir, hubert_feature_dir]:
                d.mkdir(parents=True, exist_ok=True)
            
            for audio in valid_audios:
                src = Path(audio['audio_path'])
                dst = wav_dir / src.name
                if not dst.exists():
                    shutil.copy2(src, dst)
                
                src_bert = Path(audio['bert_path'])
                dst_bert = bert_feature_dir / src_bert.name
                if not dst_bert.exists():
                    shutil.copy2(src_bert, dst_bert)
                
                src_hubert = Path(audio['hubert_path'])
                dst_hubert = hubert_feature_dir / src_hubert.name
                if not dst_hubert.exists():
                    shutil.copy2(src_hubert, dst_hubert)
            
            filelist_path = gpt_data_dir / "filelist_for_semantic.txt"
            
            # 增量训练：保留之前的 filelist 内容，追加新音频（避免重复）
            existing_entries = []
            existing_names = set()
            if filelist_path.exists():
                with open(filelist_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            existing_entries.append(line)
                            # 提取文件名
                            name = line.split("|")[0].replace(".wav", "")
                            existing_names.add(name)
                print(f"[TRAIN] 保留 {len(existing_entries)} 条已有训练记录（增量训练）")
            
            # 只追加不重复的新音频
            new_entries = []
            for audio in valid_audios:
                if audio['name'] not in existing_names:
                    new_entries.append(f"{audio['name']}.wav|{project_name}|ZH|{audio['text']}")
            
            if new_entries:
                print(f"[TRAIN] 追加 {len(new_entries)} 个新音频")
            
            # 合并并写入
            all_entries = existing_entries + new_entries
            with open(filelist_path, "w", encoding="utf-8") as f:
                for entry in all_entries:
                    f.write(entry + "\n")
            
            self._report_progress(task_id, "preparing", "✅ 训练数据已准备", 20, 100)
            
            # ============ 阶段3: 生成音素文件 ============
            self._report_progress(task_id, "preparing", "🔤 生成音素文件...", 25, 100)
            
            gptsovits_root = str(gpt_dir).replace("\\", "/")
            if gptsovits_root not in sys.path:
                sys.path.insert(0, gptsovits_root)
            text_path = f"{gptsovits_root}/GPT_SoVITS/text"
            if text_path not in sys.path:
                sys.path.insert(0, text_path)
            
            # 使用官方 clean_text（而非 g2p），与 1-get-text.py 一致
            from text.cleaner import clean_text
            
            # GPT-SoVITS 期望的格式: 文件名\t音素\tword2ph\t文本
            # 【关键】name 必须带 .wav 后缀（官方规范：3-get-semantic.py 和 dataset.py 中 key 一致性）
            name2text_path = gpt_data_dir / "2-name2text-0.txt"
            
            # 增量训练：保留已有内容，避免重复
            existing_texts = {}
            if name2text_path.exists():
                with open(name2text_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 4:
                            existing_texts[parts[0]] = line.strip()
                print(f"[TRAIN] 保留 {len(existing_texts)} 条已有音素记录")
            
            # 只处理新的音频
            new_texts = {}
            for audio in valid_audios:
                # name 带 .wav 后缀（官方规范）
                wav_name = audio['name'] + ".wav"
                if wav_name in existing_texts:
                    continue
                # 使用官方 clean_text() 提取音素
                try:
                    cleaned_input = audio['text'].replace("%", "-").replace("￥", ",")
                    phones, word2ph, norm_text = clean_text(cleaned_input, "zh", "v3")
                except Exception as e:
                    # 回退到 g2p
                    print(f"[TRAIN] clean_text 失败 {wav_name}: {e}，回退到 g2p")
                    from text.chinese import g2p
                    cleaned_text = _clean_text_for_g2p(audio['text'])
                    if not cleaned_text:
                        print(f"[TRAIN] 跳过 {wav_name}: 文本无效")
                        continue
                    phones_str, word2ph = g2p(cleaned_text)
                    phones = phones_str
                    norm_text = audio['text']
                
                phone_text = " ".join(phones)
                word2ph_str = " ".join(map(str, word2ph))
                # 格式: 文件名(带.wav) \t 音素 \t word2ph \t 原文
                new_texts[wav_name] = f"{wav_name}\t{phone_text}\t{word2ph_str}\t{audio['text']}"
            
            # 合并并写入
            all_texts = list(existing_texts.values()) + list(new_texts.values())
            with open(name2text_path, "w", encoding="utf-8") as f:
                for content in all_texts:
                    f.write(content + "\n")
            
            if new_texts:
                print(f"[TRAIN] 追加 {len(new_texts)} 条新音素记录")
            
            print(f"[TRAIN] 音素文件已生成: {name2text_path}")
            self._report_progress(task_id, "preparing", "✅ 音素文件已生成", 30, 100)
            
            # ============ 阶段4: 生成语义特征 ============
            self._report_progress(task_id, "preparing", "🔮 生成语义特征...", 35, 100)
            
            # 语义特征文件：每行 文件名 \t 语义ID列表（用空格分隔的数字）
            name2semantic_path = gpt_data_dir / "6-name2semantic-0.tsv"
            
            # 检查现有文件是否包含有效语义 token（全 512 则重新提取）
            existing_semantics = {}
            if name2semantic_path.exists():
                has_fake_tokens = False
                with open(name2semantic_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 2:
                            tokens = parts[1].split()
                            # 如果所有 token 都是 512，说明是假 token
                            if all(t == "512" for t in tokens):
                                has_fake_tokens = True
                                break
                            existing_semantics[parts[0]] = line.strip()
                
                if has_fake_tokens:
                    print(f"[TRAIN] 检测到假语义 token（全512），强制重新提取真实语义特征")
                    existing_semantics = {}
                    name2semantic_path.unlink(missing_ok=True)
                    # 同时删除验证集文件
                    dev_semantic = gpt_data_dir / "6-name2semantic-dev-0.tsv"
                    dev_semantic.unlink(missing_ok=True)
                else:
                    print(f"[TRAIN] 保留 {len(existing_semantics)} 条已有真实语义记录")
            
            # 只处理新的音频
            new_semantics = {}
            
            # 使用预训练 SoVITS VQ encoder 提取真实语义 token
            # 参考官方 3-get-semantic.py 的方法
            import torch
            vq_model = None
            is_half_flag = torch.cuda.is_available()
            try:
                sys.path.insert(0, str(GPT_SOVITS_ROOT / "GPT_SoVITS"))
                from module.models import SynthesizerTrnV3 as SynthesizerTrn
                
                vq_device = "cuda" if torch.cuda.is_available() else "cpu"
                pretrained_s2G = str(GPT_SOVITS_ROOT / "GPT_SoVITS/pretrained_models/s2Gv3.pth")
                print(f"[TRAIN] 加载预训练 SoVITS VQ encoder: {pretrained_s2G}")
                
                # 使用官方 s2.json 配置构建模型（而非手动构造 Hps）
                s2_config_path = GPT_SOVITS_ROOT / "GPT_SoVITS" / "configs" / "s2.json"
                if s2_config_path.exists():
                    # 必须用 importlib 强制加载 GPT_SoVITS 的 utils.py
                    # 直接 import utils 可能拿到其他已缓存的同名模块
                    import importlib
                    import importlib.util
                    utils_spec = importlib.util.spec_from_file_location(
                        "s2_utils", str(GPT_SOVITS_ROOT / "GPT_SoVITS" / "utils.py")
                    )
                    s2_utils = importlib.util.module_from_spec(utils_spec)
                    utils_spec.loader.exec_module(s2_utils)
                    hps = s2_utils.get_hparams_from_file(str(s2_config_path))
                    vq_model = SynthesizerTrn(
                        hps.data.filter_length // 2 + 1,
                        hps.train.segment_size // hps.data.hop_length,
                        n_speakers=hps.data.n_speakers,
                        version="v3",
                        **hps.model,
                    )
                else:
                    # 回退到手动构造
                    class Hps:
                        data = type('Hps', (), {'filter_length': 2048, 'hop_length': 640, 'n_speakers': 300, 'segment_size': 20480})()
                        model = {
                            'inter_channels': 192, 'hidden_channels': 192, 'filter_channels': 768,
                            'n_heads': 2, 'n_layers': 6, 'kernel_size': 3, 'p_dropout': 0.1,
                            'gin_channels': 512, 'semantic_frame_rate': '25hz',
                            'version': 'v3'
                        }
                    hps_mini = Hps()
                    vq_model = SynthesizerTrn(
                        hps_mini.data.filter_length // 2 + 1,
                        hps_mini.data.segment_size // hps_mini.data.hop_length,
                        n_speakers=hps_mini.data.n_speakers,
                        version='v3',
                        **hps_mini.model
                    )
                
                # 官方 3-get-semantic.py: load_state_dict(torch.load(pretrained_s2G)["weight"], strict=False)
                dict_s2 = torch.load(pretrained_s2G, map_location="cpu", weights_only=False)
                vq_model.load_state_dict(dict_s2["weight"], strict=False)
                vq_model = vq_model.eval().to(vq_device)
                if is_half_flag:
                    vq_model = vq_model.half()
                print(f"[TRAIN] SoVITS VQ encoder 加载成功")
            except Exception as e:
                print(f"[TRAIN] 加载 SoVITS VQ encoder 失败: {e}，使用备用方法")
                vq_model = None
            
            for audio in valid_audios:
                # name 带 .wav 后缀（官方规范）
                wav_name = audio['name'] + ".wav"
                if wav_name in existing_semantics:
                    continue
                
                # 尝试用 VQ encoder 提取真实语义 token
                semantic_ids = None
                # HuBERT 特征路径：优先查找带 .wav 后缀的官方格式
                # 官方 3-get-semantic.py: hubert_path = "%s/%s.pt" % (hubert_dir, wav_name)
                # 其中 wav_name = "录音.wav"，所以文件名是 "录音.wav.pt"
                hubert_wav_pt_path = gpt_data_dir / "4-cnhubert" / f"{wav_name}.pt"
                hubert_npy_path = gpt_data_dir / "4-cnhubert" / f"{audio['name']}.npy"
                hubert_plain_pt_path = gpt_data_dir / "4-cnhubert" / f"{audio['name']}.pt"
                
                # 按优先级查找 HuBERT 特征文件
                hubert_path = None
                for candidate in [hubert_wav_pt_path, hubert_plain_pt_path, hubert_npy_path]:
                    if candidate.exists():
                        hubert_path = candidate
                        break

                if vq_model is not None and hubert_path is not None and hubert_path.exists():
                    try:
                        if hubert_path.suffix == ".npy":
                            # .npy 格式：numpy 数组，形状 [T, 768]
                            import numpy as np
                            ssl_np = np.load(hubert_path)
                            # 转置为 [768, T]，然后添加batch维 [1, 768, T]
                            if ssl_np.ndim == 2 and ssl_np.shape[1] == 768:
                                ssl_np = ssl_np.T  # [T, 768] -> [768, T]
                            ssl_content = torch.from_numpy(ssl_np).float().unsqueeze(0)  # [1, 768, T]
                        else:
                            # .pt 格式：PyTorch 张量，官方格式 [1, 768, T]
                            ssl_content = torch.load(hubert_path, map_location="cpu", weights_only=False)

                        # 移动到设备
                        if is_half_flag:
                            ssl_content = ssl_content.half().to(vq_device)
                        else:
                            ssl_content = ssl_content.to(vq_device)

                        # 提取语义 token（官方 3-get-semantic.py 完全一致）
                        with torch.no_grad():
                            codes = vq_model.extract_latent(ssl_content)
                        # codes: (1, 1, T) → 取 [0,0,:] 转为 list
                        semantic_ids_list = codes[0, 0, :].tolist()
                        semantic_ids = " ".join(str(int(i)) for i in semantic_ids_list)
                        print(f"[TRAIN] 提取语义 token: {wav_name} ({len(semantic_ids_list)} tokens)")
                    except Exception as e:
                        print(f"[TRAIN] 提取语义失败 {wav_name}: {e}")
                
                # 备用：如果 VQ encoder 失败，报错而非使用假 token
                if semantic_ids is None:
                    print(f"[TRAIN] ⚠️ 无法提取真实语义 token: {wav_name}，跳过此音频")
                    continue
                
                # name 带 .wav 后缀（官方规范）
                new_semantics[wav_name] = f"{wav_name}\t{semantic_ids}"
            
            # 合并并写入
            all_semantics = list(existing_semantics.values()) + list(new_semantics.values())
            with open(name2semantic_path, "w", encoding="utf-8") as f:
                for content in all_semantics:
                    f.write(content + "\n")
            
            if new_semantics:
                print(f"[TRAIN] 追加 {len(new_semantics)} 条新语义记录")
            
            print(f"[TRAIN] 语义特征文件已生成: {name2semantic_path}")
            self._report_progress(task_id, "preparing", "✅ 语义特征已生成", 40, 100)
            
            # ============ 阶段4.5: 验证集处理 ============
            # 【关键】官方 webui.py open1Bb() 不设 dev_semantic_path / dev_phoneme_path
            # 官方 data_module.py 在不提供 dev 路径时，复用训练集作为验证集
            # 我们遵循官方做法：不生成独立的验证集文件
            dev_semantic_path = None
            dev_phoneme_path = None
            print(f"[TRAIN] 遵循官方规范：S1 训练不使用独立验证集（复用训练集）")
            
            self._report_progress(task_id, "preparing", "✅ 训练数据准备完成", 44, 100)
            
            # ============ 阶段5: 生成训练配置（严格遵循官方 open1Bb）============
            self._report_progress(task_id, "preparing", "⚙️ 生成训练配置...", 45, 100)
            
            # 增量训练：计算累计轮数
            import re
            max_prev_epoch = 0
            ckpt_dir = gpt_data_dir / "ckpt"
            if ckpt_dir.exists():
                for ckpt_file in ckpt_dir.glob("*.ckpt"):
                    # 匹配 epoch=N 格式
                    match = re.search(r'epoch=(\d+)', ckpt_file.name)
                    if match:
                        epoch_num = int(match.group(1))
                        max_prev_epoch = max(max_prev_epoch, epoch_num)
            
            if max_prev_epoch > 0:
                print(f"[TRAIN] 检测到已有训练记录 (epoch={max_prev_epoch})，将进行增量训练")
                total_epochs = train_config["epochs"] + max_prev_epoch
            else:
                total_epochs = train_config["epochs"]
            
            # 【关键】官方 open1Bb() 流程：
            # 1. 读取 s1longer-v2.yaml 模板（v2/v2Pro/v3 通用）
            # 2. exp_root = "logs"，s1_dir = "logs/{exp_name}"
            # 3. output_dir = "{s1_dir}/logs_s1_{version}"
            # 4. half_weights_save_dir = GPT_weight_version2root[version]（v3="GPT_weights_v3"）
            # 5. train_semantic_path = "{s1_dir}/6-name2semantic.tsv"（无 -0 后缀！）
            # 6. train_phoneme_path = "{s1_dir}/2-name2text.txt"（无 -0 后缀！）
            
            # 官方 exp_root = "logs"，数据目录 = "logs/{exp_name}"
            s1_dir = str(GPT_SOVITS_ROOT / "logs" / f"web_{project_name}")
            # 确保目录存在
            os.makedirs(s1_dir, exist_ok=True)
            os.makedirs(f"{s1_dir}/logs_s1_{train_version}", exist_ok=True)
            
            # 读取官方 YAML 模板
            yaml_template = GPT_SOVITS_ROOT / "GPT_SoVITS" / "configs" / "s1longer-v2.yaml"
            if yaml_template.exists():
                with open(yaml_template, "r", encoding="utf-8") as f:
                    yaml_config = yaml.load(f.read(), Loader=yaml.FullLoader)
            else:
                # 回退：手动构造
                # 动态获取音素词表大小，避免硬编码 512 导致推理时越界
                try:
                    import sys as _sys
                    _gptsovits_subdir = str(GPT_SOVITS_ROOT / "GPT_SoVITS")
                    if _gptsovits_subdir not in _sys.path:
                        _sys.path.insert(0, _gptsovits_subdir)
                    from text.symbols2 import symbols as _symbols2
                    _phoneme_vocab_size = len(_symbols2)
                except Exception:
                    _phoneme_vocab_size = 512
                print(f"[TRAIN] S1 phoneme_vocab_size = {_phoneme_vocab_size}")
                yaml_config = {
                    "optimizer": {
                        "name": "AdamW",
                        "lr_init": 0.0001,
                        "lr": 0.0005,
                        "lr_end": 0.00001,
                        "warmup_steps": 1000,
                        "decay_steps": 100000,
                    },
                    "lr_scheduler": {"name": "ExponentialLR", "gamma": 0.999875},
                    "data": {"max_eval_sample": 8, "max_sec": 54, "num_workers": 4, "pad_val": 1024},
                    "train": {
                        "seed": 1234, "epochs": 20, "batch_size": 8,
                        "save_every_n_epoch": 1, "precision": "16-mixed",
                        "gradient_clip": 1.0, "if_save_latest": True,
                        "if_save_every_weights": False,
                    },
                    "model": {
                        "vocab_size": 1025, "phoneme_vocab_size": _phoneme_vocab_size,
                        "embedding_dim": 512, "hidden_dim": 512,
                        "head": 16, "linear_units": 2048, "n_layer": 24,
                        "dropout": 0, "EOS": 1024,
                    },
                }
            
            # 按官方 open1Bb() 填充字段
            import torch as _torch
            _is_half = _torch.cuda.is_available()
            if not _is_half:
                yaml_config["train"]["precision"] = "32"
                train_config["batch_size"] = max(1, train_config["batch_size"] // 2)
            
            yaml_config["train"]["batch_size"] = train_config["batch_size"]
            yaml_config["train"]["epochs"] = total_epochs
            yaml_config["pretrained_s1"] = str(GPT_SOVITS_ROOT / "GPT_SoVITS" / "pretrained_models" / "s1v3.ckpt")
            yaml_config["train"]["save_every_n_epoch"] = train_config.get("save_freq", 5)
            yaml_config["train"]["if_save_every_weights"] = True  # 官方默认 False，但我们的场景需要
            yaml_config["train"]["if_save_latest"] = True
            yaml_config["train"]["if_dpo"] = train_config.get("if_dpo", False)
            # 【关键】官方 GPT_weight_version2root["v3"] = "GPT_weights_v3"
            yaml_config["train"]["half_weights_save_dir"] = f"GPT_weights_{train_version}"
            yaml_config["train"]["exp_name"] = f"web_{project_name}"
            # 【关键】官方 train_semantic_path / train_phoneme_path 无 -0 后缀
            yaml_config["train_semantic_path"] = f"{s1_dir}/6-name2semantic.tsv"
            yaml_config["train_phoneme_path"] = f"{s1_dir}/2-name2text.txt"
            yaml_config["output_dir"] = f"{s1_dir}/logs_s1_{train_version}"
            
            # 【关键】强制将 phoneme_vocab_size 设置为当前词表实际大小
            # 不能依赖模板或 ckpt 里的旧值（扩展词典后必须重新配置）
            try:
                import sys as _sys
                _gptsovits_subdir = str(GPT_SOVITS_ROOT / "GPT_SoVITS")
                if _gptsovits_subdir not in _sys.path:
                    _sys.path.insert(0, _gptsovits_subdir)
                from text.symbols2 import symbols as _symbols2
                _phoneme_vocab_size = len(_symbols2)
            except Exception:
                _phoneme_vocab_size = 512
            if "model" not in yaml_config:
                yaml_config["model"] = {}
            yaml_config["model"]["phoneme_vocab_size"] = _phoneme_vocab_size
            print(f"[TRAIN] S1 phoneme_vocab_size 强制设置为: {_phoneme_vocab_size}")
            
            # 写入 tmp_s1.yaml（与官方 tmp_config_path 一致）
            tmp_dir = GPT_SOVITS_ROOT / "TEMP"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            yaml_path = tmp_dir / f"tmp_s1_web_{project_name}.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_config, f, default_flow_style=False)
            
            self._report_progress(task_id, "preparing", "✅ 训练配置已生成", 50, 100)
            
            # ============ 阶段6: 复制数据到官方目录结构 ============
            # 官方目录结构：GPT-SoVITS/logs/{exp_name}/
            # 而非之前的 GPT-SoVITS/data/web_{project_name}/
            self._report_progress(task_id, "preparing", "📂 复制数据到官方目录...", 47, 100)
            
            s1_data_dir = GPT_SOVITS_ROOT / "logs" / f"web_{project_name}"
            s1_data_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制 3-bert, 4-cnhubert, 5-wav32k 到 s1_data_dir
            for subdir in ["3-bert", "4-cnhubert", "5-wav32k"]:
                src_dir = gpt_data_dir / subdir
                dst_dir = s1_data_dir / subdir
                if src_dir.exists():
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    for f in src_dir.glob("*"):
                        dst = dst_dir / f.name
                        if not dst.exists():
                            shutil.copy2(f, dst)
            
            # 2-name2text.txt（始终覆盖，与 semantic 保持一致）
            s1_name2text = s1_data_dir / "2-name2text.txt"
            if name2text_path.exists():
                shutil.copy2(name2text_path, s1_name2text)
            
            # 6-name2semantic.tsv（始终覆盖，避免上次训练残留空文件导致跳过）
            s1_semantic_path = s1_data_dir / "6-name2semantic.tsv"
            if name2semantic_path.exists():
                # 官方 open1c 合并时添加标题行 "item_name\tsemantic_audio"
                with open(name2semantic_path, "r", encoding="utf-8") as f:
                    semantic_content = f.read().strip()
                with open(s1_semantic_path, "w", encoding="utf-8") as f:
                    f.write("item_name\tsemantic_audio\n")
                    if semantic_content:
                        f.write(semantic_content + "\n")
            
            print(f"[TRAIN] S1 数据目录: {s1_data_dir}")
            print(f"[TRAIN] train_semantic_path: {yaml_config['train_semantic_path']}")
            print(f"[TRAIN] train_phoneme_path: {yaml_config['train_phoneme_path']}")
            
            # ============ 阶段7: 运行 S1 训练（官方 subprocess 方式）============
            self._report_progress(task_id, "training", "🚀 开始训练 S1 模型...", 50, 100)
            
            # 官方 open1Bb(): Popen(cmd, shell=True)
            # cmd = '"{python}" -s GPT_SoVITS/s1_train.py --config_file "{tmp_s1.yaml}"'
            python_exe = sys.executable
            cmd = f'"{python_exe}" -s GPT_SoVITS/s1_train.py --config_file "{yaml_path}"'
            
            env = os.environ.copy()
            env["_CUDA_VISIBLE_DEVICES"] = "0"
            env["CUDA_VISIBLE_DEVICES"] = "0"
            env["hz"] = "25hz"
            env["version"] = train_version  # v3（而非 v2Pro）
            env["PYTHONPATH"] = str(GPT_SOVITS_ROOT) + os.pathsep + str(GPT_SOVITS_ROOT / "GPT_SoVITS")
            
            print(f"[TRAIN] 工作目录: {GPT_SOVITS_ROOT}")
            print(f"[TRAIN] 命令: {cmd}")
            print(f"[TRAIN] version={train_version}")
            
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(GPT_SOVITS_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    shell=True,
                )
                self._active_processes.append(proc)  # C3修复: 跟踪子进程
                for line in proc.stdout:
                    print(line, end="")
                proc.wait()
                return_code = proc.returncode
                print(f"[TRAIN] S1 训练进程退出，返回码: {return_code}")
                
                if return_code != 0:
                    self._report_progress(task_id, "error", f"❌ S1 训练失败，返回码: {return_code}", 0, 100, action="start_training")
                    return
                
                print("[TRAIN] S1 训练完成!")
                self._report_progress(task_id, "complete", "✅ S1 训练完成!", 100, 100, action="start_training")
            except Exception as train_err:
                print(f"[TRAIN] 训练过程出错: {train_err}")
                import traceback
                traceback.print_exc()
                self._report_progress(task_id, "error", f"训练错误: {train_err}", 0, 100, action="start_training")
                return
            
            # ============ 阶段8: 保存模型 ============
            self._report_progress(task_id, "saving", "💾 保存模型...", 95, 100)
            
            # 官方 S1 模型保存到 half_weights_save_dir = "GPT_weights_v3/"
            # s1_train.py 的 my_model_ckpt 保存到 {output_dir}/ckpt/ 和 half_weights_save_dir/
            gpt_weights_dir = GPT_SOVITS_ROOT / f"GPT_weights_{train_version}"
            gpt_weights_dir.mkdir(parents=True, exist_ok=True)
            
            # 查找 half_weights_save_dir 中的 .ckpt 文件
            ckpts = list(gpt_weights_dir.glob(f"web_{project_name}*.ckpt"))
            
            # 同时检查 output_dir/ckpt/ 目录
            s1_ckpt_dir = s1_data_dir / f"logs_s1_{train_version}" / "ckpt"
            if s1_ckpt_dir.exists():
                ckpts.extend(list(s1_ckpt_dir.glob("*.ckpt")))
            
            if ckpts:
                latest_ckpt = max(ckpts, key=lambda p: p.stat().st_mtime)
                
                # 复制模型到项目文件夹（统一管理）
                project_ckpt_dir = project_dir / "ckpt"
                project_ckpt_dir.mkdir(parents=True, exist_ok=True)
                project_ckpt_path = project_ckpt_dir / latest_ckpt.name
                shutil.copy2(latest_ckpt, project_ckpt_path)
                print(f"✅ 模型已复制到: {project_ckpt_path}")
                
                # 更新项目配置（指向项目文件夹内的模型）
                with open(config_path, "r", encoding="utf-8") as f:
                    project_config = json.load(f)

                # 确保 ref_text 已设置（从 texts.json 获取参考音频的文本）
                if not project_config.get("ref_text"):
                    ref_audio = project_config.get("ref_audio", "")
                    if ref_audio:
                        ref_audio_base = Path(ref_audio).stem
                        texts_file = project_dir / "texts.json"
                        if texts_file.exists():
                            with open(texts_file, "r", encoding="utf-8") as f:
                                texts = json.load(f)
                            ref_text = texts.get(ref_audio_base, "")
                            if ref_text:
                                project_config["ref_text"] = ref_text
                                print(f"[TRAIN] 已设置参考音频文本: {ref_text}")

                # 【关键】S1 只更新 trained_gpt，不覆盖 trained_sovits！
                # 之前 bug：trained_sovits 也被写成了 S1 的 .ckpt 文件，
                # 导致 TTS 引擎加载时拿到错误格式（.ckpt 非 SoVITS 权重），
                # S2 训练的模型因此"找不到"。
                project_config["trained_gpt"] = str(project_ckpt_path).replace("\\", "/")
                if not project_config.get("trained_sovits"):
                    # 仅在 trained_sovits 为空时使用预训练底模，而非 S1 的 ckpt
                    project_config["trained_sovits"] = str(GPT_SOVITS_ROOT / "GPT_SoVITS" / "pretrained_models" / "s2Gv3.pth").replace("\\", "/")
                project_config["trained_at"] = datetime.now().isoformat()
                
                # 标记已训练的音频
                trained_names = [a["name"] for a in valid_audios]
                old_trained = set(project_config.get("trained_audios", []))
                new_trained = set(trained_names)
                project_config["trained_audios"] = sorted(old_trained | new_trained)

                print(f"[DEBUG] 训练完成，更新 trained_audios:")
                print(f"  - 旧列表 ({len(old_trained)}): {sorted(old_trained)}")
                print(f"  - 新增 ({len(new_trained)}): {sorted(new_trained)}")
                print(f"  - 合并后 ({len(project_config['trained_audios'])}): {project_config['trained_audios']}")
                
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(project_config, f, indent=2, ensure_ascii=False)
                
                print(f"✅ 模型已保存: {project_ckpt_path}")
                print(f"✅ 已标记 {len(trained_names)} 个音频为已训练")
                
                # ============ 阶段8: 清理原始音频 ============
                self._report_progress(task_id, "cleaning", "🗑️ 清理原始音频...", 98, 100)
                
                cleaned_count = 0
                for audio in valid_audios:
                    raw_audio = Path(audio['audio_path']).parent.parent / "raw" / Path(audio['audio_path']).name
                    if raw_audio.exists():
                        raw_audio.unlink()
                        cleaned_count += 1
                
                print(f"✅ 已清理 {cleaned_count} 个原始音频文件")
                self._report_progress(task_id, "complete", f"✅ 训练完成! 模型: {project_ckpt_path.name}，已清理 {cleaned_count} 个原始音频", 100, 100, action="start_training")
            else:
                print("⚠️ 未找到 checkpoint 文件")
                self._report_progress(task_id, "complete", "⚠️ 训练完成，但未找到 checkpoint", 100, 100, action="start_training")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._report_progress(task_id, "error", f"训练错误: {str(e)}", 0, 100, action="start_training")
        
        finally:
            with self._lock:
                self.is_training = False
                self.current_task = None
    
    def get_training_status(self) -> dict:
        """获取当前训练状态"""
        if self.current_task:
            return {
                "is_training": self.is_training,
                "task": self.current_task
            }
        return {
            "is_training": False,
            "task": None
        }
    
    def stop_training(self) -> dict:
        """停止当前训练"""
        if not self.is_training:
            return {"success": False, "error": "没有正在进行的训练"}
        
        with self._lock:
            self.is_training = False
            self.current_task = None
        
        # C3修复: 终止所有活跃训练子进程
        self._cleanup_processes()
        
        return {"success": True, "message": "训练已停止"}
    
    def _cleanup_processes(self):
        """C3修复: 清理所有活跃训练子进程，防止孤儿进程"""
        for proc in self._active_processes[:]:
            try:
                if proc.poll() is None:  # 进程仍在运行
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    print(f"[TRAIN] 已终止训练子进程 PID={proc.pid}")
            except Exception as e:
                print(f"[TRAIN] 清理子进程失败: {e}")
        self._active_processes.clear()

    def prepare_s2_data(self, project_name: str) -> dict:
        """准备 S2 训练所需的数据格式
        
        【官方 key 命名规则】（参考 2-get-hubert-wav32k.py）
        官方流程中 wav_name 是原始文件名（含扩展名，如 "录音 (2).wav"），
        因此三个数据源的 key 全部带 .wav 后缀：
          - 2-name2text.txt  第一列 = "录音 (2).wav"
          - 4-cnhubert/      文件名 = "录音 (2).wav.pt"  (去.pt后 = "录音 (2).wav")
          - 5-wav32k/        文件名 = "录音 (2).wav"
        只有三者 key 完全一致，TextAudioSpeakerLoader 的三方交集才不为空。
        """
        project_dir = self.projects_dir / project_name
        
        # S2 数据目录：GPT-SoVITS/logs/web_{project_name}/
        # 与官方 webui.py open1Ba() 完全一致（exp_root="logs" 在 GPT-SoVITS/ 目录）
        s2_exp_name = f"web_{project_name}"
        s2_data_dir = GPT_SOVITS_ROOT / "logs" / s2_exp_name
        
        try:
            bert_dir = project_dir / "3-bert"
            hubert_dir = project_dir / "4-cnhubert"
            wav32k_dir = project_dir / "32k"
            raw_dir = project_dir / "raw"
            
            if not bert_dir.exists() or not list(bert_dir.glob("*.pt")):
                return {"success": False, "error": "请先执行特征提取步骤（需要 BERT .pt 文件）"}
            
            if not hubert_dir.exists() or not list(hubert_dir.glob("*.pt")):
                return {"success": False, "error": "请先执行特征提取步骤（需要 HuBERT .pt 文件）"}
            
            # 收集音频文件（优先 32k，否则 raw）
            audio_files = _get_audio_files(wav32k_dir)
            if not audio_files:
                audio_files = _get_audio_files(raw_dir)
            if not audio_files:
                return {"success": False, "error": "没有找到 32kHz 音频文件"}
            
            # 创建目标目录
            s2_hubert_dir = s2_data_dir / "4-cnhubert"
            s2_wav_dir = s2_data_dir / "5-wav32k"
            for d in [s2_data_dir, s2_hubert_dir, s2_wav_dir]:
                d.mkdir(parents=True, exist_ok=True)
            
            import shutil
            import soundfile as sf
            import torch
            import numpy as np
            
            # 先清理 5-wav32k 中遗留的 .flac 文件（官方只用 .wav）
            for f in s2_wav_dir.glob("*.flac"):
                f.unlink()
            
            # === 1. 5-wav32k：key = "录音 (2).wav"（统一 .wav 后缀）===
            audio_count = 0
            audio_stems = []   # 记录无扩展名的 stem（用于查找 HuBERT）
            for audio_file in audio_files:
                stem = audio_file.stem          # 例：录音 (2)
                wav_key = stem + ".wav"         # 官方 key
                dst = s2_wav_dir / wav_key
                if not dst.exists():
                    if audio_file.suffix.lower() == ".wav":
                        shutil.copy2(audio_file, dst)
                    else:
                        # .flac → .wav 转换（保持 32k 采样率）
                        audio_data, sr = sf.read(audio_file)
                        sf.write(dst, audio_data, sr, subtype='PCM_16')
                audio_count += 1
                audio_stems.append(stem)
            
            print(f"[S2 PREP] 5-wav32k: {audio_count} 个文件, key 格式: {audio_stems[0]}.wav")
            
            # === 2. 4-cnhubert：文件名 = "录音 (2).wav.pt"（key 去.pt = "录音 (2).wav"）===
            pt_count = 0
            
            # 查找项目 hubert_dir 里的特征文件（可能叫 "录音 (2).npy" 或 "录音 (2).pt"）
            npy_files = list(hubert_dir.glob("*.npy"))
            pt_files_src = list(hubert_dir.glob("*.pt"))
            
            for src_file in npy_files + pt_files_src:
                stem = src_file.stem             # 例：.npy → "录音 (2)", .pt → "录音 (2).wav"
                # 如果 stem 已经以 .wav 结尾（官方格式 .pt），则直接用作 wav_key
                if stem.endswith(".wav"):
                    wav_key = stem               # 例："录音 (2).wav"
                else:
                    wav_key = stem + ".wav"      # 例："录音 (2)" → "录音 (2).wav"
                dst_name = wav_key + ".pt"       # 例："录音 (2).wav.pt"
                dst = s2_hubert_dir / dst_name
                if not dst.exists():
                    if src_file.suffix == ".npy":
                        npy_data = np.load(src_file)
                        tensor = torch.from_numpy(npy_data).float()
                        # 官方格式必须是 [1, 768, T]（data_utils.py TextAudioSpeakerLoaderV3 期望）
                        # .npy 文件保存的是 [T, 768]，需要转置并添加 batch 维
                        if tensor.dim() == 2 and tensor.shape[1] == 768:
                            # [T, 768] -> [768, T] -> [1, 768, T]（官方格式）
                            tensor = tensor.T.unsqueeze(0)
                        elif tensor.dim() == 2 and tensor.shape[0] == 768:
                            # [768, T] -> [1, 768, T]（已经是转置后的）
                            tensor = tensor.unsqueeze(0)
                        elif tensor.dim() == 1:
                            # 1D 不应该出现，但做保护
                            tensor = tensor.unsqueeze(0).unsqueeze(0)
                        # 如果已经是 [1, 768, T] 则不变
                        torch.save(tensor, dst)
                        pt_count += 1
                        print(f"[S2 PREP] npy→pt: {src_file.name} -> {dst_name}, shape={tensor.shape}")
                    else:
                        # .pt 文件：检查格式并确保是 [1, 768, T]
                        loaded = torch.load(src_file, map_location="cpu", weights_only=False)
                        if loaded.dim() == 2 and loaded.shape[1] == 768:
                            loaded = loaded.T.unsqueeze(0)  # [T, 768] -> [1, 768, T]
                        elif loaded.dim() == 2 and loaded.shape[0] == 768:
                            loaded = loaded.unsqueeze(0)  # [768, T] -> [1, 768, T]
                        torch.save(loaded, dst)
                        pt_count += 1
                        print(f"[S2 PREP] pt复制: {src_file.name} -> {dst_name}, shape={loaded.shape}")
            
            print(f"[S2 PREP] 4-cnhubert: {pt_count} 个特征文件, key 格式: {audio_stems[0]}.wav.pt")
            
            # 同时清理旧的（无 .wav 的）特征文件，避免混淆
            for old_pt in s2_hubert_dir.glob("*.pt"):
                # 如果文件名形如 "录音 (2).pt"（stem 不含 .wav），删掉
                if not old_pt.stem.endswith(".wav"):
                    old_pt.unlink()
                    print(f"[S2 PREP] 删除旧格式特征: {old_pt.name}")
            
            # === 4. 3-bert：复制 BERT .pt 特征文件（S2 训练 TextAudioSpeakerLoaderV3 必需）===
            s2_bert_dir = s2_data_dir / "3-bert"
            s2_bert_dir.mkdir(parents=True, exist_ok=True)
            bert_pt_count = 0
            for src_file in list(bert_dir.glob("*.pt")):
                dst = s2_bert_dir / src_file.name
                if not dst.exists():
                    shutil.copy2(src_file, dst)
                    bert_pt_count += 1
            print(f"[S2 PREP] 3-bert: 复制 {bert_pt_count} 个 .pt 特征文件")
            
            # === 5. 2-name2text.txt：第一列 = "录音 (2).wav"（带 .wav 后缀）===
            # 【关键】word2ph 必须从 clean_text() 获取，不能硬编码
            # 官方 1-get-text.py 中 clean_text() 返回 (phones, word2ph, norm_text)
            # word2ph 描述每个字符对应的音素数量，对 BERT 特征对齐至关重要
            s2_name2text_path = s2_data_dir / "2-name2text.txt"
            
            texts_file = project_dir / "texts.json"
            name2text_written = 0
            
            # 添加路径（供 clean_text 使用）
            gptsovits_root = str(GPT_SOVITS_ROOT).replace("\\", "/")
            if gptsovits_root not in sys.path:
                sys.path.insert(0, gptsovits_root)
            text_path = f"{gptsovits_root}/GPT_SoVITS/text"
            if text_path not in sys.path:
                sys.path.insert(0, text_path)
            from text.cleaner import clean_text
            
            if texts_file.exists():
                with open(texts_file, "r", encoding="utf-8") as f:
                    texts = json.load(f)
                
                with open(s2_name2text_path, "w", encoding="utf-8") as out:
                    for stem in audio_stems:
                        wav_key = stem + ".wav"
                        text = texts.get(stem, "")
                        if not text:
                            continue
                        # 官方做法：从 clean_text() 获取音素和 word2ph
                        try:
                            cleaned_input = text.replace("%", "-").replace("￥", ",")
                            phones, word2ph_list, norm_text = clean_text(cleaned_input, "zh", "v3")
                            phones_str = " ".join(phones)
                            word2ph = " ".join(map(str, word2ph_list))
                        except Exception as e:
                            print(f"[S2 PREP] clean_text 失败 {wav_key}: {e}，跳过")
                            continue
                        out.write(f"{wav_key}\t{phones_str}\t{word2ph}\t{text}\n")
                        name2text_written += 1
            else:
                return {"success": False, "error": "找不到 texts.json，无法生成 name2text"}
            
            print(f"[S2 PREP] 2-name2text.txt: {name2text_written} 条, key 格式: {audio_stems[0]}.wav")
            
            # === 最终验证：三方交集是否不为空 ===
            names4 = set([f.stem for f in s2_hubert_dir.glob("*.pt")])  # 去 .pt -> "录音 (2).wav"
            names5 = set([f.name for f in s2_wav_dir.glob("*.wav")])    # "录音 (2).wav"
            phoneme_keys = set()
            with open(s2_name2text_path, "r", encoding="utf-8") as f:
                for line in f:
                    tmp = line.strip().split("\t")
                    if len(tmp) >= 4:
                        phoneme_keys.add(tmp[0])
            
            intersection = phoneme_keys & names4 & names5
            print(f"[S2 PREP] 验证交集: phoneme={len(phoneme_keys)}, hubert={len(names4)}, wav={len(names5)}, 交集={len(intersection)}")
            
            if len(intersection) == 0:
                return {"success": False, "error": f"三方交集为空！phoneme={len(phoneme_keys)}, hubert={len(names4)}, wav={len(names5)}"}
            
            actual_wav_count = len(list(s2_wav_dir.glob("*.wav")))
            actual_pt_count = len(list(s2_hubert_dir.glob("*.pt")))
            print(f"[S2] 数据准备完成: {actual_wav_count} 音频, {actual_pt_count} HuBERT特征, {len(intersection)} 有效样本")
            return {
                "success": True,
                "message": f"S2 数据准备完成: {actual_wav_count} 音频, {actual_pt_count} HuBERT特征, {len(intersection)} 有效样本",
                "data_dir": str(s2_data_dir)
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def start_s2_training(self, project_name: str, config: dict = None) -> dict:
        """启动 S2 训练（SoVITS 声码器训练）"""
        with self._lock:
            if self.is_training:
                return {"success": False, "error": "已有训练任务正在进行"}
            self.is_training = True
        
        task_id = f"{project_name}_s2_{int(time.time())}"
        self.current_task = {
            "task_id": task_id,
            "project_name": project_name,
            "status": "running",
            "phase": "s2"
        }
        
        thread = threading.Thread(
            target=self._run_s2_training,
            args=(task_id, project_name, config)
        )
        thread.daemon = True
        thread.start()
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "S2 训练已启动"
        }
    
    def _run_s2_training(self, task_id: str, project_name: str, config: dict = None):
        """执行 S2 训练（后台线程）

        严格遵循官方 webui.py open1Ba() 的流程：
        1. 数据准备 → GPT_SoVITS/logs/web_{project_name}/
        2. 读取 s2.json 模板（v3 版本用 s2.json，非 s2v2Pro.json）
        3. Config 写入 TEMP/tmp_s2.json
        4. 启动官方 s2_train_v3_lora.py subprocess
        5. 模型导出到 SoVITS_weights_v3/
        """
        project_dir = self.projects_dir / project_name
        s2_exp_name = f"web_{project_name}"
        # S2 数据目录：GPT-SoVITS/logs/web_{project_name}/
        s2_data_dir = GPT_SOVITS_ROOT / "logs" / s2_exp_name
        
        # 【关键】训练版本：用户只有 s2Gv3.pth，使用 v3
        train_version = "v3"
        
        train_config = {
            # S2 基础参数
            "epochs": 100,
            "batch_size": 4,
            "learning_rate": 0.0001,
            "grad_ckpt": True,
            "lora_rank": 8,  # LoRA 模式（官方 webui.py 默认 v3 用 LoRA）
            "pretrain_s2g": str(GPT_SOVITS_ROOT / "GPT_SoVITS" / "pretrained_models" / "s2Gv3.pth"),
            "pretrain_s2d": "",  # v3 LoRA 训练不需要 s2D
            # S2 高级参数
            "betas1": 0.8,
            "betas2": 0.99,
            "eps": 1e-9,
            "lr_decay": 0.999875,
            "segment_size": 20480,
            "log_interval": 100,
            "save_freq": 1,
            "c_mel": 45,
            "text_low_lr_rate": 0.4,  # 官方默认 0.4
        }
        if config:
            train_config.update(config)
        
        try:
            # ============ 阶段1: 准备数据 ============
            self._report_progress(task_id, "preparing", "📁 准备 S2 训练数据...", 5, 100, action="prepare_s2_data")
            
            prep_result = self.prepare_s2_data(project_name)
            if not prep_result["success"]:
                self._report_progress(task_id, "error", prep_result["error"], 0, 100, action="prepare_s2_data")
                return
            
            # 验证数据完整性
            s2_name2text = s2_data_dir / "2-name2text.txt"
            s2_hubert_dir = s2_data_dir / "4-cnhubert"
            s2_wav_dir = s2_data_dir / "5-wav32k"
            
            print(f"[S2] s2_data_dir: {s2_data_dir}")
            print(f"[S2] s2_wav_dir: {s2_wav_dir}")
            print(f"[S2] s2_wav_dir exists: {s2_wav_dir.exists()}")
            if s2_wav_dir.exists():
                print(f"[S2] wav files: {list(s2_wav_dir.glob('*.wav'))}")
            
            if not s2_name2text.exists():
                self._report_progress(task_id, "error", "缺少 2-name2text.txt 文件", 0, 100, action="prepare_s2_data")
                return
            if not s2_hubert_dir.exists() or not list(s2_hubert_dir.glob("*.pt")):
                self._report_progress(task_id, "error", "缺少 HuBERT .pt 特征文件", 0, 100, action="prepare_s2_data")
                return
            if not s2_wav_dir.exists() or not list(s2_wav_dir.glob("*.wav")):
                self._report_progress(task_id, "error", "缺少 32kHz 音频文件", 0, 100, action="prepare_s2_data")
                return
            
            wav_files = list(s2_wav_dir.glob("*.wav"))
            self._report_progress(task_id, "preparing", f"✅ 找到 {len(wav_files)} 个训练样本", 10, 100)
            
            # ============ 阶段2: 生成 S2 Config（严格遵循官方 open1Ba）============
            self._report_progress(task_id, "preparing", "⚙️ 生成 S2 训练配置...", 15, 100)
            
            # 【关键】官方 open1Ba(): 
            # version not in {"v2Pro", "v2ProPlus"} → 使用 "GPT_SoVITS/configs/s2.json"
            # version in {"v2Pro", "v2ProPlus"} → 使用 "GPT_SoVITS/configs/s2{version}.json"
            # 我们使用 v3，所以用 s2.json
            config_file = GPT_SOVITS_ROOT / "GPT_SoVITS" / "configs" / "s2.json"
            with open(config_file, "r", encoding="utf-8") as f:
                s2_config = json.load(f)
            
            s2_dir = f"{GPT_SOVITS_ROOT / 'logs' / s2_exp_name}"
            os.makedirs(f"{s2_dir}/logs_s2_{train_version}", exist_ok=True)
            
            # === 关键：与 webui.py open1Ba() 完全一致的配置 ===
            import torch
            is_half = True if torch.cuda.is_available() else False
            if not is_half:
                s2_config["train"]["fp16_run"] = False
                batch_size = max(1, train_config["batch_size"] // 2)
            else:
                batch_size = train_config["batch_size"]
            s2_config["train"]["batch_size"] = batch_size
            s2_config["train"]["epochs"] = train_config["epochs"]
            s2_config["train"]["text_low_lr_rate"] = train_config.get("text_low_lr_rate", 0.4)
            s2_config["train"]["pretrained_s2G"] = train_config["pretrain_s2g"]
            s2_config["train"]["pretrained_s2D"] = train_config.get("pretrain_s2d", "")
            s2_config["train"]["gpu_numbers"] = "0"
            s2_config["train"]["if_save_latest"] = True
            s2_config["train"]["if_save_every_weights"] = True
            s2_config["train"]["save_every_epoch"] = train_config.get("save_freq", 1)
            s2_config["train"]["log_interval"] = train_config.get("log_interval", 100)
            s2_config["train"]["grad_ckpt"] = train_config.get("grad_ckpt", True)
            s2_config["train"]["lora_rank"] = train_config.get("lora_rank", 8)
            s2_config["train"]["learning_rate"] = train_config["learning_rate"]
            s2_config["train"]["betas"] = [train_config.get("betas1", 0.8), train_config.get("betas2", 0.99)]
            s2_config["train"]["eps"] = train_config.get("eps", 1e-9)
            s2_config["train"]["lr_decay"] = train_config.get("lr_decay", 0.999875)
            s2_config["train"]["segment_size"] = train_config.get("segment_size", 20480)
            s2_config["train"]["c_mel"] = train_config.get("c_mel", 45)
            s2_config["model"]["version"] = train_version
            s2_config["data"]["exp_dir"] = s2_dir
            s2_config["s2_ckpt_dir"] = s2_dir
            # 【关键】官方 save_weight_dir = SoVITS_weight_version2root[version]
            # v3 → "SoVITS_weights_v3"
            s2_config["save_weight_dir"] = f"SoVITS_weights_{train_version}"
            s2_config["name"] = s2_exp_name
            s2_config["version"] = train_version
            
            # === 写入 TEMP/tmp_s2.json（与 webui.py 完全一致）===
            temp_dir = GPT_SOVITS_ROOT / "TEMP"
            temp_dir.mkdir(parents=True, exist_ok=True)
            tmp_config_path = temp_dir / "tmp_s2.json"
            with open(tmp_config_path, "w", encoding="utf-8") as f:
                json.dump(s2_config, f, ensure_ascii=False, indent=2)
            
            print(f"[S2] Config 已写入: {tmp_config_path}")
            print(f"[S2] data.exp_dir={s2_config['data']['exp_dir']}")
            print(f"[S2] save_weight_dir={s2_config['save_weight_dir']}")
            print(f"[S2] lora_rank={s2_config['train']['lora_rank']}")
            self._report_progress(task_id, "preparing", "✅ S2 配置已生成", 20, 100)
            
            # ============ 阶段3: 启动官方 s2_train_v3_lora.py subprocess ============
            self._report_progress(task_id, "training", "🚀 开始训练 S2 模型 (LoRA)...", 25, 100)
            
            # 官方训练脚本（已 patch Windows DataLoader worker 修复）
            train_script = GPT_SOVITS_ROOT / "GPT_SoVITS" / "s2_train_v3_lora.py"
            python_exe = sys.executable
            
            # 与 webui.py open1Ba() 完全一致的命令格式：
            # python -s GPT_SoVITS/s2_train_v3_lora.py --config "TEMP/tmp_s2.json"
            cmd = f'"{python_exe}" -s GPT_SoVITS/s2_train_v3_lora.py --config "{tmp_config_path}"'
            
            print(f"[S2] 工作目录: {GPT_SOVITS_ROOT}")
            print(f"[S2] 命令: {cmd}")
            
            # 设置环境变量
            env = os.environ.copy()
            env["_CUDA_VISIBLE_DEVICES"] = "0"
            env["CUDA_VISIBLE_DEVICES"] = "0"
            # 官方 s2_train_v3_lora.py 已内置 init_method="env://?use_libuv=False"
            # 但也设置环境变量确保一致
            env["USE_LIBUV"] = "0"
            # 关键！data_utils.py 和 dataset.py 读取 os.environ["version"]
            # 官方 webui.py 全局设为 "v2Pro"，但 v3 训练环境变量也设为 v3
            # 因为 data_utils.py 中 TextAudioSpeakerLoaderV3 不检查 is_v2Pro
            env["version"] = train_version  # v3
            env["hz"] = "25hz"
            # 关键！webui.py 在启动时做了 sys.path.insert(0, os.getcwd())，
            # 但 sys.path 不会被子进程继承。需要通过 PYTHONPATH 环境变量传递
            env["PYTHONPATH"] = str(GPT_SOVITS_ROOT) + os.pathsep + str(GPT_SOVITS_ROOT / "GPT_SoVITS")
            
            proc = subprocess.Popen(
                cmd,
                cwd=str(GPT_SOVITS_ROOT),   # 工作目录: GPT-SoVITS/（TEMP/ 在这里）
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                shell=True,
            )
            self._active_processes.append(proc)  # C3修复: 跟踪子进程
            
            # 实时打印训练输出
            for line in proc.stdout:
                print(line, end="")
            
            proc.wait()
            return_code = proc.returncode
            print(f"[S2] 训练进程退出，返回码: {return_code}")
            
            if return_code != 0:
                self._report_progress(task_id, "error", f"❌ S2 训练失败，返回码: {return_code}", 0, 100, action="start_s2_training")
                return
            
            # ============ 阶段4: 从 SoVITS_weights_v3/ 收集导出的模型 ============
            self._report_progress(task_id, "saving", "💾 收集 S2 模型...", 95, 100, action="start_s2_training")
            
            # savee() 导出的路径：{save_weight_dir}/{name}_e{epoch}_s{step}_l{rank}.pth
            # save_weight_dir = "SoVITS_weights_v3"（相对路径，相对于 GPT_SOVITS_ROOT）
            sovits_weights_dir = GPT_SOVITS_ROOT / f"SoVITS_weights_{train_version}"
            sovits_weights_dir.mkdir(parents=True, exist_ok=True)
            
            # 查找所有导出的 LoRA 权重
            exported_weights = list(sovits_weights_dir.glob(f"{s2_exp_name}*.pth"))
            print(f"[S2] 导出目录: {sovits_weights_dir}")
            print(f"[S2] 找到 {len(exported_weights)} 个导出权重: {[w.name for w in exported_weights]}")
            
            if exported_weights:
                # 取最新（按修改时间）
                latest = max(exported_weights, key=lambda p: p.stat().st_mtime)
                print(f"[S2] 最新权重: {latest.name}")
                
                # 复制到项目 s2_ckpt 目录
                project_s2_ckpt_dir = project_dir / "s2_ckpt"
                project_s2_ckpt_dir.mkdir(parents=True, exist_ok=True)
                project_sovits_path = project_s2_ckpt_dir / latest.name
                shutil.copy2(latest, project_sovits_path)
                
                # 更新项目配置
                config_path = project_dir / "config.json"
                with open(config_path, "r", encoding="utf-8") as f:
                    project_config = json.load(f)
                project_config["trained_sovits"] = str(project_sovits_path).replace("\\", "/")
                project_config["s2_trained_at"] = datetime.now().isoformat()
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(project_config, f, indent=2, ensure_ascii=False)
                
                print(f"✅ S2 模型已保存: {project_sovits_path}")
                self._report_progress(task_id, "complete",
                    f"✅ S2 训练完成! 模型: {latest.name}", 100, 100, action="start_s2_training")
                return
            else:
                # 如果没有找到导出权重，检查 logs/ 子目录（中间 checkpoint）
                s2_logs_dir = s2_data_dir / f"logs_s2_{train_version}_lora_{train_config.get('lora_rank', 8)}"
                print(f"[S2] 未找到导出权重，检查中间目录: {s2_logs_dir}")
                if s2_logs_dir.exists():
                    g_ckpts = list(s2_logs_dir.glob("G_*.pth"))
                    if g_ckpts:
                        latest_ckpt = max(g_ckpts, key=lambda p: p.stat().st_mtime)
                        project_s2_ckpt_dir = project_dir / "s2_ckpt"
                        project_s2_ckpt_dir.mkdir(parents=True, exist_ok=True)
                        project_sovits_path = project_s2_ckpt_dir / f"sovits_{latest_ckpt.name}"
                        shutil.copy2(latest_ckpt, project_sovits_path)
                        
                        config_path = project_dir / "config.json"
                        with open(config_path, "r", encoding="utf-8") as f:
                            project_config = json.load(f)
                        project_config["trained_sovits"] = str(project_sovits_path).replace("\\", "/")
                        project_config["s2_trained_at"] = datetime.now().isoformat()
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(project_config, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ S2 模型(中间)已保存: {project_sovits_path}")
                        self._report_progress(task_id, "complete",
                            f"✅ S2 训练完成 (中间 checkpoint): {latest_ckpt.name}", 100, 100, action="start_s2_training")
                        return
            
            self._report_progress(task_id, "complete", "⚠️ S2 训练完成，但未找到权重文件", 100, 100, action="start_s2_training")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._report_progress(task_id, "error", f"S2 训练错误: {str(e)}", 0, 100, action="start_s2_training")
        
        finally:
            with self._lock:
                self.is_training = False
                self.current_task = None
    
    def _get_default_s2_config(self) -> dict:
        """获取默认 S2 配置"""
        return {
            "train": {
                "log_interval": 100,
                "eval_interval": 500,
                "seed": 1234,
                "epochs": 100,
                "learning_rate": 0.0001,
                "betas": [0.8, 0.99],
                "eps": 1e-09,
                "batch_size": 32,
                "fp16_run": True,
                "lr_decay": 0.999875,
                "segment_size": 20480,
                "init_lr_ratio": 1,
                "warmup_epochs": 0,
                "c_mel": 45,
                "c_kl": 1.0,
                "text_low_lr_rate": 0.4,
                "grad_ckpt": True,  # 默认开启，减少显存占用
                "pretrained_s2G": "",
                "if_save_latest": True,
                "if_save_every_weights": True,
                "save_every_epoch": 1
            },
            "data": {
                "max_wav_value": 32768.0,
                "sampling_rate": 32000,
                "filter_length": 2048,
                "hop_length": 640,
                "win_length": 2048,
                "n_mel_channels": 128,
                "mel_fmin": 0.0,
                "mel_fmax": None,
                "add_blank": True,
                "n_speakers": 300,
                "cleaned_text": True,
                "exp_dir": ""
            },
            "model": {
                "inter_channels": 192,
                "hidden_channels": 192,
                "filter_channels": 768,
                "n_heads": 2,
                "n_layers": 6,
                "kernel_size": 3,
                "p_dropout": 0.1,
                "resblock": "1",
                "resblock_kernel_sizes": [3, 7, 11],
                "resblock_dilation_sizes": [[1, 3, 5], [1, 3, 5], [1, 3, 5]],
                "upsample_rates": [10, 8, 2, 2, 2],
                "upsample_initial_channel": 512,
                "upsample_kernel_sizes": [16, 16, 8, 2, 2],
                "n_layers_q": 3,
                "use_spectral_norm": False,
                "gin_channels": 512,
                "semantic_frame_rate": "25hz",
                "freeze_quantizer": True,
                "version": "v3"
            },
            "s2_ckpt_dir": "",
            "content_module": "cnhubert"
        }


# 全局训练管理器实例
_training_manager = None

def get_training_manager() -> TrainingManager:
    """获取训练管理器单例"""
    global _training_manager
    if _training_manager is None:
        _training_manager = TrainingManager()
    return _training_manager
