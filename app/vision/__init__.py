#!/usr/bin/env python3
"""
=====================================
视觉理解模块 v2.1 - 多 Provider 架构
=====================================

支持多种视觉理解 Provider：
- RapidOCR: 纯文字 OCR（本地，依赖 rapidocr-onnxruntime）
- MiniMax VL: MiniMax 视觉理解 API（需要 API Key）
- MiniCPM: 本地视觉模型（对齐官方MiniCPM-V-2实现）

使用方式：
    from app.vision import VisionManager

    vm = VisionManager()
    vm.set_provider("minimax_vl")
    result = vm.understand("screenshot.png", "描述这张图")

作者: 咕咕嘎嘎
日期: 2026-04-20 (v2.1修复版)
"""

import os
import base64
import json
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union, Iterator
from enum import Enum
from threading import Thread
from copy import deepcopy


# ==================== Provider 类型 ====================

class VisionProviderType(Enum):
    """支持的视觉 Provider"""
    RAPIDOCR = "rapidocr"      # OCR 文字识别
    MINIMAX_VL = "minimax_vl"  # MiniMax 视觉理解
    MINICPM = "minicpm"        # MiniCPM 本地
    AUTO = "auto"              # 自动选择


# ==================== 视觉 Provider 基类 ====================

class VisionProvider(ABC):
    """视觉理解 Provider 基类"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        【功能说明】初始化视觉 Provider 基类

        【参数说明】
            config (Dict[str, Any], optional): 提供者配置字典

        【返回值】
            无
        """
        self.config = config or {}
        self.name = "base"

    @property
    def provider_type(self) -> VisionProviderType:
        """
        【属性】获取 Provider 类型

        【返回值】
            VisionProviderType: Provider 类型枚举值
        """
        return VisionProviderType.RAPIDOCR

    @property
    def supports_understanding(self) -> bool:
        """
        【属性】是否支持图像理解（而非仅 OCR）

        【返回值】
            bool: 返回 False，基础 Provider 不支持图像理解
        """
        return False

    @property
    def description(self) -> str:
        """
        【属性】获取 Provider 描述信息

        【返回值】
            str: Provider 的描述字符串
        """
        return "基础 Provider"

    @abstractmethod
    def recognize_text(self, image_path: str) -> Optional[str]:
        """OCR 文字识别"""
        pass

    def understand(self, image_path: str, prompt: str = None) -> Optional[str]:
        """
        图像理解（如果支持）

        Args:
            image_path: 图片路径
            prompt: 理解提示

        Returns:
            str: 理解结果
        """
        # 默认实现：先 OCR 再描述
        text = self.recognize_text(image_path)
        if text:
            return f"[OCR识别]\n{text}"
        return None

    def understand_stream(self, image_path: str, prompt: str = None) -> Iterator[str]:
        """
        流式图像理解（子类可覆盖）

        Args:
            image_path: 图片路径
            prompt: 理解提示

        Yields:
            str: 理解结果片段
        """
        result = self.understand(image_path, prompt)
        if result:
            yield result

    def _encode_image_base64(self, image_path: str) -> Optional[str]:
        """图片转 base64"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"[VisionProvider] 图片编码失败: {e}")
            return None

    def cleanup(self):
        """清理资源（子类可覆盖）"""
        pass


# ==================== RapidOCR Provider ====================

class RapidOCRProvider(VisionProvider):
    """RapidOCR - 本地文字识别"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        【功能说明】初始化 RapidOCR Provider

        【参数说明】
            config (Dict[str, Any], optional): 提供者配置字典

        【返回值】
            无
        """
        super().__init__(config)
        self.name = "rapidocr"
        self._engine = None

    @property
    def provider_type(self) -> VisionProviderType:
        """
        【属性】获取 Provider 类型

        【返回值】
            VisionProviderType: Provider 类型枚举值
        """
        return VisionProviderType.RAPIDOCR

    @property
    def supports_understanding(self) -> bool:
        """
        【属性】RapidOCR 是否支持图像理解

        【返回值】
            bool: 返回 False，RapidOCR 仅支持 OCR 文字识别
        """
        return False  # RapidOCR 只支持 OCR

    @property
    def description(self) -> str:
        """
        【属性】获取 Provider 描述信息

        【返回值】
            str: Provider 的描述字符串
        """
        return "RapidOCR（本地 OCR，仅识别文字）"

    def _get_engine(self):
        """懒加载引擎"""
        if self._engine is None:
            try:
                from rapidocr import RapidOCR
                self._engine = RapidOCR()
                print("[Vision] RapidOCR 引擎已加载")
            except ImportError:
                print("[Vision] ⚠️ RapidOCR 未安装: pip install rapidocr-onnxruntime")
                return None
        return self._engine

    def recognize_text(self, image_path: str) -> Optional[str]:
        """RapidOCR 文字识别"""
        engine = self._get_engine()
        if not engine:
            return None

        try:
            result, elapse = engine(image_path)
            if not result:
                return ""

            # 合并所有识别结果
            lines = []
            for item in result:
                if len(item) >= 2:
                    text = item[1]
                    if text:
                        lines.append(text)

            return "\n".join(lines)

        except Exception as e:
            print(f"[Vision] RapidOCR 识别失败: {e}")
            return None


# ==================== MiniMax VL Provider ====================

class MiniMaxVLProvider(VisionProvider):
    """
    MiniMax 视觉理解 - 使用 /v1/coding_plan/vlm 端点

    v2.2 修复：原 Anthropic 兼容端点不支持图片（静默降级为 M2.7 纯文本模型），
    改用 MiniMax VLM 专用端点 /v1/coding_plan/vlm（与 MCP understand_image 同源）。

    请求格式：
        POST {api_host}/v1/coding_plan/vlm
        {
            "prompt": "描述这张图片",
            "image_url": "data:image/jpeg;base64,..."
        }

    注意：
    - image_url 只支持 data URI 格式（data:image/xxx;base64,...），不支持 HTTP URL
    - 大图片建议先压缩为 JPEG（quality=30~50），否则请求超时
    - 超时建议 120s（大图 base64 上传较慢）
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        【功能说明】初始化 MiniMax VL Provider

        【参数说明】
            config (Dict[str, Any], optional): 提供者配置字典，包含 api_key、api_host、model 等

        【返回值】
            无
        """
        super().__init__(config)
        self.name = "minimax_vl"
        self.api_key = config.get("api_key", "") or os.getenv("MINIMAX_API_KEY", "")
        self.api_host = config.get("api_host", "https://api.minimaxi.com")
        self.model = config.get("model", "MiniMax-VL-01")
        # JPEG 压缩质量（降低 base64 体积，加快上传速度）
        self.jpeg_quality = config.get("jpeg_quality", 40)
        # 请求超时（秒，大图需要更长时间）
        self.timeout = config.get("timeout", 120)

        if not self.api_key:
            # 尝试从 config.yaml 读取
            try:
                import yaml
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    llm_cfg = cfg.get("llm", {}).get("minimax", {})
                    self.api_key = llm_cfg.get("api_key", "")
            except:
                pass

    @property
    def provider_type(self) -> VisionProviderType:
        """
        【属性】获取 Provider 类型

        【返回值】
            VisionProviderType: Provider 类型枚举值
        """
        return VisionProviderType.MINIMAX_VL

    @property
    def supports_understanding(self) -> bool:
        """
        【属性】MiniMax VL 是否支持图像理解

        【返回值】
            bool: 返回 True，MiniMax VL 支持完整图像理解
        """
        return True

    @property
    def description(self) -> str:
        """
        【属性】获取 Provider 描述信息

        【返回值】
            str: Provider 的描述字符串
        """
        return f"MiniMax VL（{self.model}，VLM API）"

    def _encode_image_data_uri(self, image_path: str) -> Optional[str]:
        """
        将图片编码为 data URI 格式（data:image/xxx;base64,...）
        自动压缩为 JPEG 以减小体积
        """
        try:
            from PIL import Image as PILImage
            from io import BytesIO

            img = PILImage.open(image_path)
            # 如果是 RGBA/PALETTE 等模式，转为 RGB
            if img.mode != "RGB":
                img = img.convert("RGB")

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=self.jpeg_quality)
            img_bytes = buffer.getvalue()
            b64 = base64.b64encode(img_bytes).decode("utf-8")

            media_type = "image/jpeg"
            data_uri = f"data:{media_type};base64,{b64}"

            print(f"[Vision] MiniMax VL 图片编码: {os.path.getsize(image_path)} -> {len(img_bytes)} bytes (JPEG q={self.jpeg_quality})")
            return data_uri
        except ImportError:
            # 没有 Pillow，回退到原始 base64
            print("[Vision] MiniMax VL Pillow 未安装，使用原始 base64")
            b64 = self._encode_image_base64(image_path)
            if b64:
                # 检测格式
                ext = os.path.splitext(image_path)[1].lower()
                media_type = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                }.get(ext, "image/png")
                return f"data:{media_type};base64,{b64}"
            return None
        except Exception as e:
            print(f"[Vision] MiniMax VL 图片编码失败: {e}")
            return None

    def recognize_text(self, image_path: str) -> Optional[str]:
        """MiniMax VL 文字识别"""
        return self.understand(image_path, "请仔细识别图中所有文字，原文输出，不要总结。")

    def understand(self, image_path: str, prompt: str = None) -> Optional[str]:
        """MiniMax VL 图像理解（v2.2 VLM API）"""
        if not self.api_key:
            print("[Vision] 请配置 MiniMax API Key")
            return None

        data_uri = self._encode_image_data_uri(image_path)
        if not data_uri:
            return None

        default_prompt = "请描述这张图片的内容，包括所有可见的物体、场景、文字等。"
        full_prompt = prompt or default_prompt

        # 清理 prompt 中可能残留的 <image> 标签（旧格式不需要了）
        full_prompt = full_prompt.replace("<image>", "").strip()

        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "prompt": full_prompt,
                "image_url": data_uri
            }

            url = f"{self.api_host}/v1/coding_plan/vlm"
            print(f"[Vision] MiniMax VL 调用: {url} (prompt: {full_prompt[:30]}...)")

            response = requests.post(url, headers=headers, json=data, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                base_resp = result.get("base_resp", {})
                status_code = base_resp.get("status_code", -1)

                if status_code != 0:
                    print(f"[Vision] MiniMax VL API 错误: {base_resp.get('status_msg', 'unknown')}")
                    return None

                content = result.get("content", "")
                if content:
                    print(f"[Vision] MiniMax VL 结果: {content[:80]}...")
                return content if content else None
            else:
                print(f"[Vision] MiniMax VL HTTP 错误: {response.status_code} - {response.text[:200]}")
                return None

        except Exception as e:
            print(f"[Vision] MiniMax VL 理解失败: {e}")
            return None


# ==================== MiniCPM Provider (本地视觉) ====================

class MiniCPMProvider(VisionProvider):
    """
    MiniCPM-V 2 本地视觉模型 - 对齐官方实现

    支持:
    - BF16/FP16: ~4-5GB 显存
    - 4bit量化: ~4-5GB 显存
    - 8bit量化: ~6-7GB 显存

    模型来源: OpenBMB/MiniCPM-V-2
    官方参考: https://huggingface.co/openbmb/MiniCPM-V-2
    """

    DEFAULT_MODEL_ID = "OpenBMB/MiniCPM-V-2"

    def __init__(self, config: Dict[str, Any] = None):
        """
        【功能说明】初始化 MiniCPM Provider

        【参数说明】
            config (Dict[str, Any], optional): 提供者配置字典，包含 model_id、量化配置等

        【返回值】
            无
        """
        super().__init__(config)
        self.name = "minicpm"
        self.model_id = config.get("model_id", self.DEFAULT_MODEL_ID)
        self.model_path = config.get("model_path", "")
        
        # V2官方默认值
        self.max_new_tokens = config.get("max_new_tokens", 1024)
        self.max_inp_length = config.get("max_inp_length", 2048)
        self.temperature = config.get("temperature", 0.7)
        self.do_sample = config.get("do_sample", True)
        
        # 量化配置
        self.use_int4 = config.get("use_int4", False)
        self.use_int8 = config.get("use_int8", False)
        self.quantization_enabled = self.use_int4 or self.use_int8
        
        self._model = None
        self._tokenizer = None

        # 设置缓存目录（与 go.bat 中 HF_HOME 一致，项目根目录）
        # __file__ = app/vision/__init__.py, 往上1层=app/vision, 2层=app, 3层=项目根
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        cache_dir = os.path.join(project_root, ".cache", "huggingface")
        os.environ.setdefault("HF_HOME", cache_dir)
        # ModelScope 缓存单独设置
        modelscope_cache = os.path.join(project_root, ".cache", "modelscope")
        os.environ.setdefault("MODELSCOPE_CACHE", modelscope_cache)
        # 使用清华镜像加速下载
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    @property
    def provider_type(self) -> VisionProviderType:
        """
        【属性】获取 Provider 类型

        【返回值】
            VisionProviderType: Provider 类型枚举值
        """
        return VisionProviderType.MINICPM

    @property
    def supports_understanding(self) -> bool:
        """
        【属性】MiniCPM 是否支持图像理解

        【返回值】
            bool: 返回 True，MiniCPM 支持完整图像理解
        """
        return True

    @property
    def description(self) -> str:
        """
        【属性】获取 Provider 描述信息（含量化配置）

        【返回值】
            str: Provider 的描述字符串
        """
        q_str = ""
        if self.use_int4:
            q_str = " [int4量化]"
        elif self.use_int8:
            q_str = " [int8量化]"
        return f"MiniCPM-V2（本地 GPU, max_new={self.max_new_tokens}, max_inp={self.max_inp_length}）{q_str}"

    def _check_dependencies(self) -> bool:
        """
        【功能说明】检查 MiniCPM 依赖是否满足（torch, transformers）

        【返回值】
            bool: 依赖满足返回 True，否则返回 False
        """
        try:
            import torch
            import transformers
            return True
        except ImportError as e:
            print(f"[Vision] MiniCPM 依赖缺失: {e}")
            print("[Vision] 请运行: pip install torch transformers")
            return False


    def _load_model(self):
        """
        【功能说明】懒加载 MiniCPM-V 2 模型

        【返回值】
            bool: 加载成功返回 True，失败返回 False

        【说明】
            - 自动检测可用显存并选择合适的量化等级
            - INT4: ~4-5GB 显存, INT8: ~6-7GB 显存, BF16: ~3.5GB 显存
            - 量化后自动反量化 VPM 和 Resampler（去除量化）
        """
        if self._model is not None:
            return True

        if not self._check_dependencies():
            return False

        try:
            import torch

            print(f"[Vision] 加载 MiniCPM-V 2...")
            print(f"[Vision] 模型: {self.model_id}")

            # 获取本地模型路径
            model_local_path = self._get_model_path()
            if not model_local_path:
                print("[Vision] 模型未找到")
                return False

            # 检查可用显存（不是总显存，而是实际剩余的）
            free_mem_gb = 0.0
            if torch.cuda.is_available():
                total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
                allocated_gb = torch.cuda.memory_allocated(0) / 1024**3
                reserved_gb = torch.cuda.memory_reserved(0) / 1024**3
                # 使用 reserved 作为已占用显存（更保守准确）
                free_mem_gb = (total_gb - reserved_gb) if reserved_gb > allocated_gb else (total_gb - allocated_gb)
                print(f"[Vision] GPU 总显存: {total_gb:.1f} GB, 已占用: ~{max(allocated_gb, reserved_gb):.1f} GB, 可用: ~{free_mem_gb:.1f} GB")

            # 加载模型 - 对齐官方V2实现
            print("[Vision] 加载 MiniCPM-V2...")
            from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

            # V2不使用AutoProcessor

            # 选择dtype - 与官方一致
            if torch.cuda.is_bf16_supported():
                torch_dtype = torch.bfloat16
                print("[Vision] 使用 BF16")
            else:
                torch_dtype = torch.float16
                print("[Vision] 使用 FP16")

            # 量化配置 - 对齐官方
            # 显存需求估算：BF16 ~2.8GB, INT4 ~3.5GB, INT8 ~5GB
            # 如果可用显存不足，自动降级量化等级
            quantization_config = None
            MIN_MEM_INT4 = 4.0   # INT4 最少需要 ~4GB
            MIN_MEM_INT8 = 6.0   # INT8 最少需要 ~6GB
            MIN_MEM_BF16 = 3.5  # BF16 最少需要 ~3.5GB

            if self.use_int4:
                if free_mem_gb >= MIN_MEM_INT4:
                    print("[Vision] 使用 INT4 量化")
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch_dtype,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                else:
                    print(f"[Vision] ⚠️ 可用显存 {free_mem_gb:.1f}GB < INT4 最低 {MIN_MEM_INT4}GB，降级为 BF16 非量化")
            elif self.use_int8:
                if free_mem_gb >= MIN_MEM_INT8:
                    print("[Vision] 使用 INT8 量化")
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        bnb_8bit_compute_dtype=torch_dtype
                    )
                elif free_mem_gb >= MIN_MEM_INT4:
                    print(f"[Vision] ⚠️ 可用显存 {free_mem_gb:.1f}GB < INT8 最低 {MIN_MEM_INT8}GB，降级为 INT4 量化")
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch_dtype,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                else:
                    print(f"[Vision] ⚠️ 可用显存 {free_mem_gb:.1f}GB < INT4 最低 {MIN_MEM_INT4}GB，降级为 BF16 非量化")
            elif free_mem_gb < MIN_MEM_BF16:
                print(f"[Vision] ⚠️ 可用显存仅 {free_mem_gb:.1f}GB，可能不足以加载模型")

            # 加载模型
            load_kwargs = {
                "torch_dtype": torch_dtype,
                "trust_remote_code": True
            }

            if quantization_config:
                load_kwargs["quantization_config"] = quantization_config
                # 使用 {"": "cuda"} 而不是 "auto"，避免 accelerate 将部分层分配到 CPU
                # 导致 validate_environment 报错
                load_kwargs["device_map"] = {"": "cuda"}

                # ========== 关键兼容性修复 ==========
                # transformers 4.44.2 的 PreTrainedModel.to() 无条件禁止
                # bitsandbytes 量化模型的 .to() 调用，但 accelerate 1.13.0 的
                # dispatch_model 在 device_map 只有一个设备时仍会调用 model.to()。
                # 这是一个已知的兼容性 bug，需要临时 monkey-patch .to() 来绕过。
                from transformers import PreTrainedModel
                _original_to = PreTrainedModel.to
                _is_loading_quantized = True  # 闭包标志

                def _patched_to(self_model, *args, **kwargs):
                    """
                    【内部函数】绕过 bitsandbytes 量化模型的 .to() 调用兼容性 bug

                    【参数说明】
                        self_model: 模型实例
                        *args, **kwargs: 传递给原始 .to() 的参数

                    【返回值】
                        返回模型本身（跳过 .to() 调用）
                    """
                    if _is_loading_quantized and getattr(self_model, "quantization_method", None) is not None:
                        return self_model
                    return _original_to(self_model, *args, **kwargs)

                PreTrainedModel.to = _patched_to

                try:
                    # 清理 GPU 缓存，释放被其他模块(如GPT-SoVITS)reserved的显存
                    torch.cuda.empty_cache()
                    self._model = AutoModel.from_pretrained(model_local_path, **load_kwargs)
                finally:
                    # 恢复原始 .to()
                    _is_loading_quantized = False
                    PreTrainedModel.to = _original_to
            else:
                # 非量化模式：直接加载并移到 GPU
                self._model = AutoModel.from_pretrained(model_local_path, **load_kwargs)
                self._model = self._model.to("cuda")

            self._model.eval()

            # ========== INT4 量化后处理 ==========
            # BitsAndBytes quantization_config 会被 apply 到整个模型（包括 VPM 和 Resampler），
            # 但 vision 组件不应该被量化。需要将 VPM 和 Resampler 恢复为 bfloat16。
            if quantization_config is not None:
                import torch.nn as nn
                import bitsandbytes as bnb
                target_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                
                def _dequantize_module(module):
                    """递归替换模块中所有 Linear4bit/Linear8bitLt 为标准 nn.Linear"""
                    for name, child in module.named_children():
                        if isinstance(child, (bnb.nn.Linear4bit, bnb.nn.Linear8bitLt)):
                            # 使用 bitsandbytes 正确反量化权重
                            if isinstance(child, bnb.nn.Linear4bit):
                                dequant_weight = bnb.functional.dequantize_4bit(
                                    child.weight.data, child.weight.quant_state
                                ).to(target_dtype)
                            else:
                                dequant_weight = child.weight.data.to(target_dtype)
                            
                            # 用标准 nn.Linear 替换
                            new_linear = nn.Linear(
                                child.in_features, child.out_features,
                                bias=child.bias is not None
                            )
                            new_linear.weight = nn.Parameter(dequant_weight)
                            if child.bias is not None:
                                new_linear.bias = nn.Parameter(child.bias.to(target_dtype))
                            setattr(module, name, new_linear)
                        else:
                            _dequantize_module(child)
                
                # 恢复 VPM（Vision Transformer）
                print("[Vision] 正在反量化 VPM...")
                _dequantize_module(self._model.vpm)
                self._model.vpm = self._model.vpm.to(target_dtype).cuda()
                
                # 恢复 Resampler
                print("[Vision] 正在反量化 Resampler...")
                _dequantize_module(self._model.resampler)
                self._model.resampler = self._model.resampler.to(target_dtype).cuda()
                
                print(f"[Vision] VPM + Resampler 已恢复为 {target_dtype}（去除量化）")

            # 加载 tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_local_path,
                trust_remote_code=True
            )

            print("[Vision] MiniCPM-V2 加载完成")
            return True

        except Exception as e:
            print(f"[Vision] MiniCPM 加载失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_model_path(self) -> Optional[str]:
        """
        【功能说明】获取模型本地路径（优先本地，其次 ModelScope 下载）

        【返回值】
            Optional[str]: 本地模型路径，下载失败返回 None
        """
        # 项目根目录 (与 go.bat HF_HOME 一致)
        # __file__ = app/vision/__init__.py, 往上3层=项目根
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        # 首先检查本地是否存在
        local_path = os.path.join(
            project_root,
            ".cache", "huggingface", "OpenBMB",
            self.model_id.split("/")[-1]
        )

        if os.path.exists(local_path):
            print(f"[Vision] 使用本地模型: {local_path}")
            return local_path

        # 尝试从 ModelScope 下载
        try:
            from modelscope import snapshot_download
            model_path = snapshot_download(
                self.model_id,
                cache_dir=self.model_path or None
            )
            print(f"[Vision] ModelScope 模型路径: {model_path}")
            return model_path
        except Exception as e:
            print(f"[Vision] ModelScope 下载失败: {e}")

        return None

    def recognize_text(self, image_path: str) -> Optional[str]:
        """MiniCPM 文字识别 - 对齐官方实现"""
        return self.understand(
            image_path,
            "请仔细识别图中所有文字，原文输出，不要总结。"
        )

    def understand(self, image_path: str, prompt: str = None) -> Optional[str]:
        """
        MiniCPM-V2 图像理解 - 对齐官方 chat() 实现

        官方V2用法:
        - msgs content 是纯字符串，图片通过 image 参数单独传入
        - 不使用 processor
        - chat()参数: context, max_new_tokens=1024, max_inp_length=2048
        """
        if not self._load_model():
            return None

        if not os.path.exists(image_path):
            print(f"[Vision] 图片不存在: {image_path}")
            return None

        try:
            import torch
            import time as _time
            from PIL import Image

            # 构建 prompt
            if prompt is None:
                prompt = "请描述这张图片的内容，包括所有可见的物体、场景、文字等。"

            # 加载图片
            print(f"[Vision] MiniCPM-V2 推理开始: {os.path.basename(image_path)}")
            image = Image.open(image_path).convert("RGB")

            # 官方V2格式: content 是纯字符串，图片通过 image 参数传入
            msgs = [{"role": "user", "content": prompt}]

            # 对齐官方V2的 chat() 调用
            infer_start = _time.time()
            with torch.no_grad():
                res, context, _ = self._model.chat(
                    image=image,                  # 图片单独传
                    msgs=msgs,                    # content只有文字
                    context=None,
                    tokenizer=self._tokenizer,
                    max_new_tokens=self.max_new_tokens,
                    max_inp_length=self.max_inp_length,
                    sampling=True,
                    temperature=self.temperature,
                )
            infer_elapsed = _time.time() - infer_start
            print(f"[Vision] MiniCPM-V2 推理完成: {infer_elapsed:.1f}s, 结果({len(res)}字): {res[:80]}...")

            return res

        except Exception as e:
            # OOM 时尝试释放显存
            import torch as _torch
            err_str = str(e)
            if "out of memory" in err_str.lower() or "CUDA" in err_str:
                print(f"[Vision] MiniCPM-V2 CUDA 错误: {e}")
                print(f"[Vision] 尝试释放显存...")
                _torch.cuda.empty_cache()
                allocated = _torch.cuda.memory_allocated(0) / 1024**3
                reserved = _torch.cuda.memory_reserved(0) / 1024**3
                print(f"[Vision] GPU 显存: allocated={allocated:.2f}GB, reserved={reserved:.2f}GB")
            else:
                print(f"[Vision] MiniCPM-V2 理解失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def understand_stream(self, image_path: str, prompt: str = None) -> Iterator[str]:
        """
        V2 不支持流式输出，降级到普通 understand()
        """
        result = self.understand(image_path, prompt)
        if result:
            yield result

    def cleanup(self):
        """
        【功能说明】释放 MiniCPM 模型资源（显存和内存）

        【返回值】
            无
        """
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        try:
            import torch
            torch.cuda.empty_cache()
        except:
            pass
        print("[Vision] MiniCPM 资源已释放")


# ==================== Vision Manager ====================

class VisionManager:
    """
    视觉理解管理器

    统一管理多个 Provider，支持动态切换
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        【功能说明】初始化视觉理解管理器

        【参数说明】
            config (Dict[str, Any], optional): 配置字典

        【返回值】
            无
        """
        self.config = config or {}
        self._providers: Dict[VisionProviderType, VisionProvider] = {}
        self._current_provider_type = VisionProviderType.RAPIDOCR
        self._current_provider: VisionProvider = None

        # 初始化所有 Provider
        self._init_providers()

        # 设置默认 Provider
        default = self.config.get("default_provider", "minimax_vl")
        self.set_provider(default)

    def _init_providers(self):
        """
        【功能说明】初始化所有视觉理解 Provider

        【返回值】
            无
        """
        # RapidOCR（本地 OCR）
        self._providers[VisionProviderType.RAPIDOCR] = RapidOCRProvider(
            self.config.get("rapidocr", {})
        )

        # MiniMax VL（云端）
        self._providers[VisionProviderType.MINIMAX_VL] = MiniMaxVLProvider(
            self.config.get("minimax_vl", {})
        )

        # MiniCPM（本地视觉）
        self._providers[VisionProviderType.MINICPM] = MiniCPMProvider(
            self.config.get("minicpm", {})
        )

    def set_provider(self, provider: str):
        """
        切换 Provider

        Args:
            provider: Provider 名称 ("rapidocr", "minimax_vl", "minicpm", "auto")
        """
        if provider == "auto":
            # 自动选择：有 MiniMax API 用它，否则用 RapidOCR
            if self._providers[VisionProviderType.MINIMAX_VL].api_key:
                provider = "minimax_vl"
            else:
                provider = "rapidocr"

        provider_map = {
            "rapidocr": VisionProviderType.RAPIDOCR,
            "minimax_vl": VisionProviderType.MINIMAX_VL,
            "minicpm": VisionProviderType.MINICPM,
        }

        pt = provider_map.get(provider)
        if pt and pt in self._providers:
            self._current_provider_type = pt
            self._current_provider = self._providers[pt]
            print(f"[Vision] Provider 切换: {self._current_provider.description}")
        else:
            print(f"[Vision] ⚠️ 未知 Provider: {provider}")

    @property
    def current_provider_name(self) -> str:
        """当前 Provider 名称"""
        return self._current_provider_type.value

    @property
    def current_provider_description(self) -> str:
        """当前 Provider 描述"""
        return self._current_provider.description if self._current_provider else ""

    def recognize_text(self, image_path: str) -> Optional[str]:
        """OCR 文字识别"""
        if not self._current_provider:
            return None
        return self._current_provider.recognize_text(image_path)

    def understand(self, image_path: str, prompt: str = None) -> Optional[str]:
        """图像理解"""
        if not self._current_provider:
            return None
        return self._current_provider.understand(image_path, prompt)

    def understand_stream(self, image_path: str, prompt: str = None):
        """流式图像理解"""
        if not self._current_provider:
            return None
        return self._current_provider.understand_stream(image_path, prompt)

    def get_available_providers(self) -> List[Dict[str, str]]:
        """获取可用 Provider 列表"""
        result = []
        for pt, provider in self._providers.items():
            result.append({
                "type": pt.value,
                "name": provider.description,
                "supports_understanding": provider.supports_understanding
            })
        return result

    def cleanup(self):
        """清理所有 Provider"""
        for provider in self._providers.values():
            provider.cleanup()


# ==================== 工厂函数 ====================

def create_vision_manager(config: Dict[str, Any] = None) -> VisionManager:
    """创建视觉管理器"""
    return VisionManager(config)


# ==================== 兼容旧接口 ====================

class VisionSystem(VisionManager):
    """兼容旧接口"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        【功能说明】初始化 VisionSystem（兼容旧接口）

        【参数说明】
            config (Dict[str, Any], optional): 配置字典

        【返回值】
            无
        """
        super().__init__(config)
        self.screen = None  # 简化，不复用旧代码
        self.camera = None

    def screenshot(self, save_path: str = None) -> Optional[str]:
        """截图（使用 OCR 模块的截图功能）"""
        try:
            import mss
            if save_path is None:
                save_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "cache", "vision_screenshot.png"
                )
            with mss.mss() as sct:
                sct.shot(output=save_path)
            return save_path
        except Exception as e:
            print(f"[Vision] 截图失败: {e}")
            return None

    def screenshot_and_read(self) -> Optional[str]:
        """截图并识别文字"""
        path = self.screenshot()
        if path:
            return self.recognize_text(path)
        return None

    def screenshot_and_understand(self, prompt: str = None) -> Optional[str]:
        """截图并理解"""
        path = self.screenshot()
        if path:
            return self.understand(path, prompt)
        return None


# ========== 测试 ==========

if __name__ == "__main__":
    print("=" * 50)
    print("Vision Module v2.1 - 多 Provider 架构")
    print("=" * 50)

    # 列出可用 Provider
    vm = VisionManager()
    print("\n可用 Provider:")
    for p in vm.get_available_providers():
        print(f"  [{p['type']}] {p['name']} (支持理解: {p['supports_understanding']})")

    # 测试 RapidOCR
    print(f"\n当前 Provider: {vm.current_provider_name}")
    vm.set_provider("rapidocr")
    print(f"切换到: {vm.current_provider_name} - {vm.current_provider_description}")
