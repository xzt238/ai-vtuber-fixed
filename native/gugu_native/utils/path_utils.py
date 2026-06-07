"""
路径工具模块

提供统一的路径操作函数，减少代码重复。
"""

import os
from pathlib import Path
from typing import Optional

# 项目根目录
PROJECT_DIR = None


def get_project_dir() -> str:
    """获取项目根目录"""
    global PROJECT_DIR
    if PROJECT_DIR is None:
        from app.shared_config import PROJECT_DIR as _PD
        PROJECT_DIR = _PD
    return PROJECT_DIR


def get_model_dir(model_type: str = "live2d") -> str:
    """获取模型目录
    
    Args:
        model_type: 模型类型 (live2d, vrm, etc.)
    
    Returns:
        模型目录路径
    """
    project_dir = get_project_dir()
    return os.path.join(project_dir, "app", "web", "static", "assets", "model")


def get_live2d_model_path(model_name: str) -> str:
    """获取 Live2D 模型路径
    
    Args:
        model_name: 模型名称
    
    Returns:
        模型文件路径
    """
    model_dir = get_model_dir("live2d")
    return os.path.join(model_dir, model_name, f"{model_name}.model3.json")


def get_vrm_model_path(model_name: str) -> str:
    """获取 VRM 模型路径
    
    Args:
        model_name: 模型名称
    
    Returns:
        模型文件路径
    """
    model_dir = get_model_dir("vrm")
    return os.path.join(model_dir, f"{model_name}.vrm")


def get_cache_dir() -> str:
    """获取缓存目录
    
    Returns:
        缓存目录路径
    """
    project_dir = get_project_dir()
    cache_dir = os.path.join(project_dir, "app", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def get_state_dir() -> str:
    """获取状态目录
    
    Returns:
        状态目录路径
    """
    project_dir = get_project_dir()
    state_dir = os.path.join(project_dir, "app", "state")
    os.makedirs(state_dir, exist_ok=True)
    return state_dir


def get_history_path(filename: str = "native_chat_history.json") -> str:
    """获取历史记录文件路径
    
    Args:
        filename: 文件名
    
    Returns:
        文件路径
    """
    state_dir = get_state_dir()
    return os.path.join(state_dir, filename)


def get_tts_prefs_path() -> str:
    """获取 TTS 偏好文件路径
    
    Returns:
        文件路径
    """
    cache_dir = get_cache_dir()
    return os.path.join(cache_dir, "tts_preferences.json")


def get_vrm_display_config_path() -> str:
    """获取 VRM 显示配置文件路径
    
    Returns:
        文件路径
    """
    cache_dir = get_cache_dir()
    return os.path.join(cache_dir, "vrm_display.json")


def ensure_dir(dir_path: str) -> str:
    """确保目录存在
    
    Args:
        dir_path: 目录路径
    
    Returns:
        目录路径
    """
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def path_exists(path: str) -> bool:
    """检查路径是否存在
    
    Args:
        path: 路径
    
    Returns:
        是否存在
    """
    return Path(path).exists()


def join_path(*args) -> str:
    """拼接路径
    
    Args:
        *args: 路径组件
    
    Returns:
        拼接后的路径
    """
    return os.path.join(*args)
