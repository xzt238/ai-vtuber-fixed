"""
设备管理器 — 跨平台 GPU/CPU 自动选择

统一管理 PyTorch 设备的检测与选择，消除硬编码 "cuda"。
"""

import logging
import torch

_logger = logging.getLogger("DeviceManager")


class DeviceManager:
    """跨平台 GPU 设备自动检测与选择"""

    @staticmethod
    def get_best_device() -> str:
        """返回当前平台最优设备字符串

        优先级: CUDA → MPS (Apple Silicon) → CPU
        """
        if torch.cuda.is_available():
            _logger.info("Device: CUDA")
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            _logger.info("Device: MPS (Apple Silicon)")
            return "mps"
        _logger.info("Device: CPU")
        return "cpu"

    @staticmethod
    def get_best_device_with_fallback(fallback: str = "cpu") -> str:
        """同 get_best_device，允许指定 fallback"""
        device = DeviceManager.get_best_device()
        if device == "cpu" and fallback != "cpu":
            return fallback
        return device

    @staticmethod
    def to_device(model_or_tensor, device: str = None) -> None:
        """将模型/张量移动到最优设备

        示例: model = DeviceManager.to_device(model)
        """
        if device is None:
            device = DeviceManager.get_best_device()
        return model_or_tensor.to(device)

    @staticmethod
    def get_device_info() -> dict:
        """获取设备信息（调试用）"""
        info = {
            "best_device": DeviceManager.get_best_device(),
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "mps_available": hasattr(torch.backends, "mps") and torch.backends.mps.is_available(),
        }
        if torch.cuda.is_available():
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
            info["cuda_memory_total"] = torch.cuda.get_device_properties(0).total_memory
        return info
