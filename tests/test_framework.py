"""
测试框架模块
提供单元测试、集成测试、性能测试支持
"""

import asyncio
import time
import traceback
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

class TestStatus(Enum):
    """测试状态"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    error: Optional[Exception] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class TestSuite:
    """测试套件"""
    name: str
    tests: List[TestResult] = field(default_factory=list)
    
    @property
    def passed(self) -> int:
        return len([t for t in self.tests if t.status == TestStatus.PASSED])
    
    @property
    def failed(self) -> int:
        return len([t for t in self.tests if t.status == TestStatus.FAILED])
    
    @property
    def skipped(self) -> int:
        return len([t for t in self.tests if t.status == TestStatus.SKIPPED])
    
    @property
    def total(self) -> int:
        return len(self.tests)
    
    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.suites: Dict[str, TestSuite] = {}
        self.setup_hooks: List[Callable] = []
        self.teardown_hooks: List[Callable] = []
        
        print("[TestRunner] 初始化完成")
    
    def create_suite(self, name: str) -> TestSuite:
        """创建测试套件"""
        suite = TestSuite(name=name)
        self.suites[name] = suite
        return suite
    
    def add_setup(self, hook: Callable):
        """添加setup钩子"""
        self.setup_hooks.append(hook)
    
    def add_teardown(self, hook: Callable):
        """添加teardown钩子"""
        self.teardown_hooks.append(hook)
    
    async def run_test(self, test_name: str, test_func: Callable, 
                      suite_name: str = "default") -> TestResult:
        """运行单个测试"""
        # 确保套件存在
        if suite_name not in self.suites:
            self.create_suite(suite_name)
        
        suite = self.suites[suite_name]
        
        # 执行setup
        for hook in self.setup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                print(f"[TestRunner] Setup失败: {e}")
        
        # 运行测试
        start_time = time.time()
        status = TestStatus.PASSED
        message = ""
        error = None
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            message = "测试通过"
        except AssertionError as e:
            status = TestStatus.FAILED
            message = str(e)
            error = e
        except Exception as e:
            status = TestStatus.ERROR
            message = f"测试错误: {str(e)}"
            error = e
        
        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000
        
        # 创建结果
        result = TestResult(
            test_name=test_name,
            status=status,
            duration_ms=duration_ms,
            message=message,
            error=error
        )
        
        # 添加到套件
        suite.tests.append(result)
        
        # 执行teardown
        for hook in self.teardown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                print(f"[TestRunner] Teardown失败: {e}")
        
        # 打印结果
        status_icon = "✅" if status == TestStatus.PASSED else "❌"
        print(f"{status_icon} {test_name} ({duration_ms:.1f}ms) - {message}")
        
        return result
    
    async def run_suite(self, suite_name: str) -> TestSuite:
        """运行整个测试套件"""
        if suite_name not in self.suites:
            print(f"[TestRunner] 测试套件不存在: {suite_name}")
            return None
        
        suite = self.suites[suite_name]
        print(f"\n{'='*50}")
        print(f"运行测试套件: {suite_name}")
        print(f"{'='*50}")
        
        return suite
    
    def generate_report(self) -> str:
        """生成测试报告"""
        report_lines = []
        report_lines.append("# 测试报告")
        report_lines.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("\n## 测试套件汇总\n")
        
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_tests = 0
        
        for suite_name, suite in self.suites.items():
            report_lines.append(f"### {suite_name}")
            report_lines.append(f"- 总测试数: {suite.total}")
            report_lines.append(f"- 通过: {suite.passed}")
            report_lines.append(f"- 失败: {suite.failed}")
            report_lines.append(f"- 跳过: {suite.skipped}")
            report_lines.append(f"- 通过率: {suite.pass_rate:.1f}%")
            report_lines.append("")
            
            total_passed += suite.passed
            total_failed += suite.failed
            total_skipped += suite.skipped
            total_tests += suite.total
        
        report_lines.append("## 总计")
        report_lines.append(f"- 总测试数: {total_tests}")
        report_lines.append(f"- 通过: {total_passed}")
        report_lines.append(f"- 失败: {total_failed}")
        report_lines.append(f"- 跳过: {total_skipped}")
        
        if total_tests > 0:
            pass_rate = total_passed / total_tests * 100
            report_lines.append(f"- 通过率: {pass_rate:.1f}%")
        
        # 添加失败详情
        failed_tests = []
        for suite_name, suite in self.suites.items():
            for test in suite.tests:
                if test.status in [TestStatus.FAILED, TestStatus.ERROR]:
                    failed_tests.append((suite_name, test))
        
        if failed_tests:
            report_lines.append("\n## 失败详情\n")
            for suite_name, test in failed_tests:
                report_lines.append(f"### {suite_name} - {test.test_name}")
                report_lines.append(f"- 状态: {test.status.value}")
                report_lines.append(f"- 消息: {test.message}")
                if test.error:
                    report_lines.append(f"- 错误: {str(test.error)}")
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_report(self, filepath: str):
        """保存测试报告"""
        report = self.generate_report()
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"[TestRunner] 测试报告已保存: {filepath}")

# 全局实例
_test_runner: Optional[TestRunner] = None

def get_test_runner() -> TestRunner:
    """获取测试运行器实例"""
    global _test_runner
    if _test_runner is None:
        _test_runner = TestRunner()
    return _test_runner

# 断言辅助函数
def assert_equal(actual, expected, message: str = ""):
    """断言相等"""
    if actual != expected:
        msg = f"期望 {expected}，实际 {actual}"
        if message:
            msg = f"{message}: {msg}"
        raise AssertionError(msg)

def assert_not_none(value, message: str = ""):
    """断言非空"""
    if value is None:
        msg = "值不应为None"
        if message:
            msg = f"{message}: {msg}"
        raise AssertionError(msg)

def assert_true(value, message: str = ""):
    """断言为真"""
    if not value:
        msg = "值应为True"
        if message:
            msg = f"{message}: {msg}"
        raise AssertionError(msg)

def assert_false(value, message: str = ""):
    """断言为假"""
    if value:
        msg = "值应为False"
        if message:
            msg = f"{message}: {msg}"
        raise AssertionError(msg)

def assert_raises(exception_type, func, *args, **kwargs):
    """断言抛出异常"""
    try:
        func(*args, **kwargs)
        raise AssertionError(f"期望抛出 {exception_type.__name__}，但未抛出")
    except exception_type:
        pass
    except Exception as e:
        raise AssertionError(f"期望抛出 {exception_type.__name__}，但抛出了 {type(e).__name__}")
