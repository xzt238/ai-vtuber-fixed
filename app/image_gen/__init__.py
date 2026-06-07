"""
文生图模块

提供文生图API支持，包括：
- 通义万相
- 智谱CogView
- 可图
- DALL-E
- Flux

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# 版本信息
__version__ = "1.0.0"
__author__ = "咕咕嘎嘎"


class ImageProvider(Enum):
    """图像生成提供商枚举"""
    WANX = "wanx"           # 通义万相
    COGVIEW = "cogview"     # 智谱CogView
    KOLORS = "kolors"       # 可图
    DALL_E = "dall_e"       # DALL-E
    FLUX = "flux"           # Flux
    MIMO = "mimo"           # 小米MiMo


@dataclass
class ImageRequest:
    """图像生成请求"""
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    num_images: int = 1
    style: str = ""
    seed: int = -1


@dataclass
class ImageResponse:
    """图像生成响应"""
    images: List[str]  # 图片URL或base64
    prompt: str
    provider: ImageProvider
    model: str
    created_at: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ImageGenerator:
    """文生图生成器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 提供商配置
        self.provider = ImageProvider(self.config.get("provider", "wanx"))
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get("base_url", "")
        self.model = self.config.get("model", "")
        
        # 默认参数
        self.default_width = self.config.get("width", 1024)
        self.default_height = self.config.get("height", 1024)
        self.default_style = self.config.get("style", "")
        
        # HTTP会话
        self._session = None
        
        logger.info(f" 文生图模块初始化完成")
        logger.info(f" 提供商: {self.provider.value}")
        logger.info(f" 模型: {self.model}")
    
    async def generate(self, request: ImageRequest) -> ImageResponse:
        """生成图像"""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # 根据提供商调用不同的API
            if self.provider == ImageProvider.WANX:
                return await self._generate_wanx(request)
            elif self.provider == ImageProvider.COGVIEW:
                return await self._generate_cogview(request)
            elif self.provider == ImageProvider.KOLORS:
                return await self._generate_kolors(request)
            elif self.provider == ImageProvider.DALL_E:
                return await self._generate_dall_e(request)
            elif self.provider == ImageProvider.FLUX:
                return await self._generate_flux(request)
            elif self.provider == ImageProvider.MIMO:
                return await self._generate_mimo(request)
            else:
                raise ValueError(f"不支持的提供商: {self.provider}")
            
        except Exception as e:
            logger.info(f" 图像生成失败: {e}")
            raise
    
    async def _generate_wanx(self, request: ImageRequest) -> ImageResponse:
        """通义万相文生图"""
        try:
            # 构建请求
            url = f"{self.base_url or 'https://dashscope.aliyuncs.com'}/api/v1/services/aigc/text2image/image-synthesis"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable"
            }
            
            data = {
                "model": self.model or "wanx-v1",
                "input": {
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt
                },
                "parameters": {
                    "size": f"{request.width}*{request.height}",
                    "n": request.num_images,
                    "seed": request.seed if request.seed > 0 else None
                }
            }
            
            # 移除None值
            data["parameters"] = {k: v for k, v in data["parameters"].items() if v is not None}
            
            # 发送请求
            async with self._session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    # 异步任务，需要轮询获取结果
                    task_id = result.get("output", {}).get("task_id")
                    if task_id:
                        # 轮询等待结果
                        images = await self._poll_wanx_task(task_id)
                        return ImageResponse(
                            images=images,
                            prompt=request.prompt,
                            provider=ImageProvider.WANX,
                            model=self.model or "wanx-v1",
                            created_at=datetime.now(),
                            metadata={"task_id": task_id}
                        )
                    else:
                        raise Exception(f"通义万相请求失败: {result}")
                else:
                    raise Exception(f"通义万相请求失败: {result}")
            
        except Exception as e:
            logger.info(f" 通义万相生成失败: {e}")
            raise
    
    async def _poll_wanx_task(self, task_id: str, max_retries: int = 30) -> List[str]:
        """轮询通义万相任务"""
        url = f"{self.base_url or 'https://dashscope.aliyuncs.com'}/api/v1/tasks/{task_id}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        for i in range(max_retries):
            async with self._session.get(url, headers=headers) as response:
                result = await response.json()
                
                status = result.get("output", {}).get("task_status")
                
                if status == "SUCCEEDED":
                    # 获取图片URL
                    results = result.get("output", {}).get("results", [])
                    return [r.get("url") for r in results if r.get("url")]
                elif status == "FAILED":
                    raise Exception(f"任务失败: {result}")
                else:
                    # 等待后重试
                    await asyncio.sleep(2)
        
        raise Exception("任务超时")
    
    async def _generate_cogview(self, request: ImageRequest) -> ImageResponse:
        """智谱CogView文生图"""
        try:
            # 构建请求
            url = f"{self.base_url or 'https://open.bigmodel.cn'}/api/paas/v4/images/generations"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model or "cogview-4",
                "prompt": request.prompt,
                "size": f"{request.width}x{request.height}",
                "n": request.num_images
            }
            
            # 发送请求
            async with self._session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    # 获取图片URL
                    images = [item.get("url") for item in result.get("data", []) if item.get("url")]
                    return ImageResponse(
                        images=images,
                        prompt=request.prompt,
                        provider=ImageProvider.COGVIEW,
                        model=self.model or "cogview-4",
                        created_at=datetime.now()
                    )
                else:
                    raise Exception(f"智谱CogView请求失败: {result}")
            
        except Exception as e:
            logger.info(f" 智谱CogView生成失败: {e}")
            raise
    
    async def _generate_kolors(self, request: ImageRequest) -> ImageResponse:
        """可图文生图"""
        try:
            # 构建请求
            url = f"{self.base_url or 'https://api.kolors.com'}/v1/images/generations"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model or "kolors",
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "num_images": request.num_images
            }
            
            # 发送请求
            async with self._session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    # 获取图片URL
                    images = [item.get("url") for item in result.get("data", []) if item.get("url")]
                    return ImageResponse(
                        images=images,
                        prompt=request.prompt,
                        provider=ImageProvider.KOLORS,
                        model=self.model or "kolors",
                        created_at=datetime.now()
                    )
                else:
                    raise Exception(f"可图请求失败: {result}")
            
        except Exception as e:
            logger.info(f" 可图生成失败: {e}")
            raise
    
    async def _generate_dall_e(self, request: ImageRequest) -> ImageResponse:
        """DALL-E文生图"""
        try:
            # 构建请求
            url = f"{self.base_url or 'https://api.openai.com'}/v1/images/generations"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model or "dall-e-3",
                "prompt": request.prompt,
                "n": request.num_images,
                "size": f"{request.width}x{request.height}"
            }
            
            # 发送请求
            async with self._session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    # 获取图片URL
                    images = [item.get("url") for item in result.get("data", []) if item.get("url")]
                    return ImageResponse(
                        images=images,
                        prompt=request.prompt,
                        provider=ImageProvider.DALL_E,
                        model=self.model or "dall-e-3",
                        created_at=datetime.now()
                    )
                else:
                    raise Exception(f"DALL-E请求失败: {result}")
            
        except Exception as e:
            logger.info(f" DALL-E生成失败: {e}")
            raise
    
    async def _generate_flux(self, request: ImageRequest) -> ImageResponse:
        """Flux文生图"""
        try:
            # 构建请求
            url = f"{self.base_url or 'https://api.bfl.ml'}/v1/flux-pro-1.1"
            
            headers = {
                "X-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "prompt": request.prompt,
                "width": request.width,
                "height": request.height,
                "steps": 20,
                "guidance": 7.5
            }
            
            # 发送请求
            async with self._session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    # 获取图片URL
                    images = [result.get("sample")] if result.get("sample") else []
                    return ImageResponse(
                        images=images,
                        prompt=request.prompt,
                        provider=ImageProvider.FLUX,
                        model=self.model or "flux-pro-1.1",
                        created_at=datetime.now()
                    )
                else:
                    raise Exception(f"Flux请求失败: {result}")
            
        except Exception as e:
            logger.info(f" Flux生成失败: {e}")
            raise
    
    async def _generate_mimo(self, request: ImageRequest) -> ImageResponse:
        """小米MiMo文生图"""
        try:
            # MiMo目前主要是文本和多模态理解，文生图功能可能需要使用其他API
            # 这里提供一个通用的OpenAI兼容接口实现
            
            url = f"{self.base_url or 'https://api.xiaomimimo.com'}/v1/images/generations"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model or "mimo-v2.5",
                "prompt": request.prompt,
                "n": request.num_images,
                "size": f"{request.width}x{request.height}"
            }
            
            # 发送请求
            async with self._session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    # 获取图片URL
                    images = [item.get("url") for item in result.get("data", []) if item.get("url")]
                    return ImageResponse(
                        images=images,
                        prompt=request.prompt,
                        provider=ImageProvider.MIMO,
                        model=self.model or "mimo-v2.5",
                        created_at=datetime.now()
                    )
                else:
                    raise Exception(f"MiMo请求失败: {result}")
            
        except Exception as e:
            logger.info(f" MiMo生成失败: {e}")
            raise
    
    async def generate_simple(self, prompt: str, **kwargs) -> List[str]:
        """简单的图像生成"""
        request = ImageRequest(
            prompt=prompt,
            width=kwargs.get("width", self.default_width),
            height=kwargs.get("height", self.default_height),
            negative_prompt=kwargs.get("negative_prompt", ""),
            num_images=kwargs.get("num_images", 1),
            style=kwargs.get("style", self.default_style),
            seed=kwargs.get("seed", -1)
        )
        
        response = await self.generate(request)
        return response.images
    
    def get_supported_providers(self) -> List[Dict[str, str]]:
        """获取支持的提供商列表"""
        return [
            {"id": "wanx", "name": "通义万相", "description": "阿里云通义万相文生图"},
            {"id": "cogview", "name": "智谱CogView", "description": "智谱AI CogView文生图"},
            {"id": "kolors", "name": "可图", "description": "可图文生图"},
            {"id": "dall_e", "name": "DALL-E", "description": "OpenAI DALL-E文生图"},
            {"id": "flux", "name": "Flux", "description": "Flux文生图"},
            {"id": "mimo", "name": "小米MiMo", "description": "小米MiMo文生图"},
        ]
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session:
            await self._session.close()
            self._session = None


# 全局文生图生成器实例
_image_generator = None


def get_image_generator(config: Dict[str, Any] = None) -> ImageGenerator:
    """获取文生图生成器单例"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator(config)
    return _image_generator


async def generate_image(prompt: str, **kwargs) -> List[str]:
    """生成图像的便捷函数"""
    generator = get_image_generator()
    return await generator.generate_simple(prompt, **kwargs)


# 导出主要类
__all__ = [
    'ImageProvider',
    'ImageRequest',
    'ImageResponse',
    'ImageGenerator',
    'get_image_generator',
    'generate_image',
]