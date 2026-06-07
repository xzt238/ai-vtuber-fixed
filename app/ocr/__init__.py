#!/usr/bin/env python3
"""
=====================================
OCR 实时屏幕分析模块
=====================================

本模块提供实时屏幕截图 + OCR 文字识别 + LLM 分析功能。
底层使用 vision 模块的 RapidOCR 进行文字识别，
使用 mss 进行屏幕截图。

功能：
- start_monitor(interval): 启动定时屏幕截图 + OCR 监控
- stop_monitor(): 停止监控
- capture_and_ocr(): 单次截图 + OCR
- get_screenshot_base64(): 获取当前屏幕截图的 base64
- analyze_screen(prompt): 截图 + OCR + LLM 分析
- get_status(): 获取监控状态

作者: 咕咕嘎嘎
日期: 2026-04-25
"""

import os
import time
import base64
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass


@dataclass
class OCRResult:
    """OCR 识别结果"""
    text: str
    timestamp: float
    confidence: float = 0.0


class OCRSystem:
    """
    OCR 实时屏幕分析系统
    
    架构：
        mss (屏幕截图) → RapidOCR (文字识别) → LLM (语义分析)
        
    使用 vision 模块的 RapidOCRProvider 进行 OCR，
    使用 mss 进行屏幕截图。
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 OCR 系统
        
        Args:
            config: 配置字典，可包含：
                - interval: 默认监控间隔（秒）
                - analyzer: LLM 分析配置
        """
        self.config = config or {}
        self.interval = self.config.get("interval", 1.0)
        self._running = False
        self._monitor_thread = None
        self._event_callback = None
        self._last_ocr = None
        self._last_screenshot_b64 = None
        self._history = []
        self._max_history = 100
        self._lock = threading.Lock()
        
        # OCR 引擎（延迟初始化）
        self._ocr_engine = None
        
        # LLM 分析器（延迟初始化）
        self._analyzer_config = self.config.get("analyzer", {})
        
        # 截图临时文件
        self._screenshot_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "cache"
        )
        os.makedirs(self._screenshot_dir, exist_ok=True)
    
    def _get_ocr_engine(self):
        """延迟获取 OCR 引擎（使用 vision 模块的 RapidOCR）"""
        if self._ocr_engine is None:
            try:
                from vision import RapidOCRProvider
                self._ocr_engine = RapidOCRProvider()
                print("[OCR] RapidOCR 引擎已加载")
            except ImportError:
                print("[OCR] ⚠️ vision 模块不可用，OCR 功能受限")
                self._ocr_engine = None
        return self._ocr_engine

    def _take_screenshot(self, save_path: str = None) -> Optional[str]:
        """截取屏幕截图"""
        try:
            import mss
            if save_path is None:
                save_path = os.path.join(
                    self._screenshot_dir,
                    f"ocr_screenshot_{int(time.time()*1000)}.png"
                )
            with mss.mss() as sct:
                sct.shot(output=save_path)
            return save_path
        except ImportError:
            print("[OCR] ⚠️ mss 未安装，无法截图: pip install mss")
            return None
        except Exception as e:
            print(f"[OCR] 截图失败: {e}")
            return None

    def _recognize(self, image_path: str) -> Optional[str]:
        """OCR 识别图片中的文字"""
        engine = self._get_ocr_engine()
        if not engine:
            return None
        try:
            return engine.recognize_text(image_path)
        except Exception as e:
            print(f"[OCR] 识别失败: {e}")
            return None

    def set_event_callback(self, callback: Callable):
        """设置事件回调函数"""
        self._event_callback = callback

    def start_monitor(self, interval: float = 1.0):
        """
        启动定时 OCR 监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self._running:
            print("[OCR] 监控已在运行")
            return
        
        self.interval = max(0.5, interval)
        self._running = True
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ocr-monitor"
        )
        self._monitor_thread.start()
        print(f"[OCR] 监控已启动，间隔: {self.interval}s")

    def stop_monitor(self):
        """停止监控"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3)
        self._monitor_thread = None
        print("[OCR] 监控已停止")

    def _monitor_loop(self):
        """监控循环（后台线程）"""
        while self._running:
            try:
                result = self.capture_and_ocr()
                if result and self._event_callback:
                    self._event_callback("ocr_result", {
                        "text": result.text,
                        "timestamp": result.timestamp
                    })
            except Exception as e:
                print(f"[OCR] 监控循环错误: {e}")
            
            # 分段 sleep，方便及时响应 stop
            end_time = time.time() + self.interval
            while self._running and time.time() < end_time:
                time.sleep(0.1)

    def capture_and_ocr(self) -> Optional[OCRResult]:
        """截取屏幕并 OCR"""
        screenshot_path = self._take_screenshot()
        if not screenshot_path:
            return None
        
        try:
            # 保存 base64
            with open(screenshot_path, "rb") as f:
                self._last_screenshot_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            # OCR 识别
            text = self._recognize(screenshot_path)
            
            result = OCRResult(
                text=text or "",
                timestamp=time.time()
            )
            
            with self._lock:
                self._last_ocr = result
                self._history.append(result)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]
            
            return result
        finally:
            # 清理临时截图
            try:
                os.unlink(screenshot_path)
            except OSError:
                pass

    def get_screenshot_base64(self) -> Optional[str]:
        """获取当前屏幕截图的 base64"""
        # 先截一张新的
        screenshot_path = self._take_screenshot()
        if not screenshot_path:
            return self._last_screenshot_b64
        
        try:
            with open(screenshot_path, "rb") as f:
                self._last_screenshot_b64 = base64.b64encode(f.read()).decode("utf-8")
            return self._last_screenshot_b64
        except Exception as e:
            print(f"[OCR] 截图 base64 编码失败: {e}")
            return self._last_screenshot_b64
        finally:
            try:
                os.unlink(screenshot_path)
            except OSError:
                pass

    def get_last_ocr(self) -> Optional[OCRResult]:
        """获取最近一次 OCR 结果"""
        return self._last_ocr

    def get_history(self, limit: int = 10) -> list:
        """获取 OCR 历史"""
        with self._lock:
            return self._history[-limit:]

    def analyze_screen(self, prompt: str = None) -> Optional[str]:
        """截图 + OCR + LLM 分析"""
        result = self.capture_and_ocr()
        if not result or not result.text:
            return "未识别到屏幕文字"
        
        # 尝试使用 LLM 分析
        llm_config = self._analyzer_config.get("llm_config", {})
        if llm_config:
            try:
                from llm import LLMFactory
                llm = LLMFactory.create(llm_config)
                if llm and llm.is_available():
                    analysis_prompt = prompt or "请分析以下屏幕文字内容"
                    full_prompt = f"{analysis_prompt}\n\n屏幕文字:\n{result.text}"
                    response = llm.chat(full_prompt, [])
                    return response.get("text", "")
            except Exception as e:
                print(f"[OCR] LLM 分析失败: {e}")
        
        # fallback: 直接返回 OCR 文字
        return result.text[:500]

    def is_running(self) -> bool:
        """检查是否在运行"""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "running": self._running,
            "interval": self.interval,
            "history_count": len(self._history),
            "last_ocr_time": self._last_ocr.timestamp if self._last_ocr else None
        }

    def close(self):
        """关闭系统"""
        self.stop_monitor()
        self._ocr_engine = None


def get_ocr_system(config: Dict[str, Any] = None) -> OCRSystem:
    """
    创建 OCR 系统实例
    
    Args:
        config: 配置字典
    
    Returns:
        OCRSystem: OCR 系统实例
    """
    return OCRSystem(config)
