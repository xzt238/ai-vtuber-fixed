"""
日志智能分析模块
接入LLM大模型自动分析日志，识别问题并提供建议
"""

import re
import logging
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: str
    module: str
    message: str
    raw: str


@dataclass
class LogAnalysisResult:
    """日志分析结果"""
    timestamp: datetime
    summary: str
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    severity: str  # low, medium, high, critical
    raw_logs: List[str]


class LogAnalyzer:
    """
    日志智能分析器
    
    功能：
    1. 收集日志条目
    2. 定期分析日志模式
    3. 识别异常和错误
    4. 调用LLM进行深度分析
    5. 生成分析报告
    """
    
    def __init__(self, max_logs: int = 1000, analysis_interval: float = 60.0) -> None:
        """初始化日志分析器"""
        self.max_logs = max_logs
        self.analysis_interval = analysis_interval
        
        # 日志缓冲区
        self._log_buffer: deque = deque(maxlen=max_logs)
        self._error_logs: deque = deque(maxlen=100)
        self._warning_logs: deque = deque(maxlen=200)
        
        # 分析结果
        self._analysis_results: deque = deque(maxlen=50)
        self._last_analysis_time: Optional[datetime] = None
        
        # 回调函数
        self._on_analysis_complete: List[Callable] = []
        self._on_issue_detected: List[Callable] = []
        
        # 线程和状态
        self._analysis_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._stop_event = threading.Event()
        
        # LLM配置
        self._llm_provider = None
        self._llm_model = None
        
        # 问题模式匹配
        self._error_patterns = [
            (r'error|Error|ERROR', 'error'),
            (r'exception|Exception|EXCEPTION', 'exception'),
            (r'fail|Fail|FAIL', 'failure'),
            (r'traceback|Traceback', 'traceback'),
            (r'critical|Critical|CRITICAL', 'critical'),
            (r'warning|Warning|WARNING', 'warning'),
            (r'OOM|out of memory|内存不足', 'memory'),
            (r'CUDA|GPU|cuda', 'gpu'),
            (r'timeout|Timeout|TIMEOUT', 'timeout'),
            (r'connection|Connection refused|连接', 'connection'),
        ]
        
        logger.info("[LogAnalyzer] 初始化完成")
    
    def add_log(self, record: logging.LogRecord) -> None:
        """添加日志条目"""
        try:
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                module=record.name,
                message=record.getMessage(),
                raw=self._format_record(record)
            )
            
            self._log_buffer.append(entry)
            
            # 收集错误和警告日志
            if record.levelno >= logging.ERROR:
                self._error_logs.append(entry)
                self._check_immediate_issue(entry)
            elif record.levelno >= logging.WARNING:
                self._warning_logs.append(entry)
                
        except Exception as e:
            logger.debug(f"[LogAnalyzer] 添加日志失败: {e}")
    
    def _format_record(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        return f"[{datetime.fromtimestamp(record.created).strftime('%H:%M:%S')}] [{record.levelname}] [{record.name}] {record.getMessage()}"
    
    def _check_immediate_issue(self, entry: LogEntry) -> None:
        """检查即时问题（严重错误立即通知）"""
        if entry.level in ('CRITICAL', 'FATAL'):
            for callback in self._on_issue_detected:
                try:
                    callback({
                        'type': 'critical_error',
                        'message': entry.message,
                        'module': entry.module,
                        'timestamp': entry.timestamp.isoformat()
                    })
                except Exception:
                    pass
    
    def start(self) -> None:
        """启动日志分析器"""
        if self._is_running:
            return
        
        self._is_running = True
        self._stop_event.clear()
        
        self._analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="LogAnalyzer"
        )
        self._analysis_thread.start()
        
        logger.info(f"[LogAnalyzer] 启动分析器 (间隔: {self.analysis_interval}秒)")
    
    def stop(self) -> None:
        """停止日志分析器"""
        self._is_running = False
        self._stop_event.set()
        
        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=5)
        
        logger.info("[LogAnalyzer] 分析器已停止")
    
    def _analysis_loop(self) -> None:
        """分析循环"""
        while self._is_running:
            try:
                # 等待分析间隔或停止信号
                if self._stop_event.wait(timeout=self.analysis_interval):
                    break
                
                # 执行分析
                self._analyze_logs()
                
            except Exception as e:
                logger.error(f"[LogAnalyzer] 分析循环异常: {e}")
    
    def _analyze_logs(self) -> None:
        """分析日志"""
        if len(self._log_buffer) < 10:
            return
        
        try:
            # 收集最近的日志
            recent_logs = list(self._log_buffer)[-100:]
            recent_errors = list(self._error_logs)[-20:]
            recent_warnings = list(self._warning_logs)[-30:]
            
            # 统计分析
            stats = self._compute_stats(recent_logs)
            
            # 模式识别
            patterns = self._identify_patterns(recent_logs)
            
            # 生成分析结果
            result = LogAnalysisResult(
                timestamp=datetime.now(),
                summary=self._generate_summary(stats, patterns),
                issues=self._identify_issues(stats, patterns, recent_errors),
                suggestions=self._generate_suggestions(stats, patterns),
                severity=self._determine_severity(stats, patterns),
                raw_logs=[log.raw for log in recent_errors[:5]]
            )
            
            self._analysis_results.append(result)
            self._last_analysis_time = datetime.now()
            
            # 通知回调
            for callback in self._on_analysis_complete:
                try:
                    callback(result)
                except Exception:
                    pass
            
            # 如果有严重问题，记录日志
            if result.severity in ('high', 'critical'):
                logger.warning(f"[LogAnalyzer] 检测到问题: {result.summary}")
                
        except Exception as e:
            logger.error(f"[LogAnalyzer] 分析失败: {e}")
    
    def _compute_stats(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """计算日志统计"""
        stats = {
            'total': len(logs),
            'by_level': {},
            'by_module': {},
            'error_rate': 0,
            'warning_rate': 0
        }
        
        for log in logs:
            # 按级别统计
            stats['by_level'][log.level] = stats['by_level'].get(log.level, 0) + 1
            # 按模块统计
            stats['by_module'][log.module] = stats['by_module'].get(log.module, 0) + 1
        
        if stats['total'] > 0:
            stats['error_rate'] = stats['by_level'].get('ERROR', 0) / stats['total']
            stats['warning_rate'] = stats['by_level'].get('WARNING', 0) / stats['total']
        
        return stats
    
    def _identify_patterns(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """识别日志模式"""
        patterns = []
        
        # 统计错误模式
        pattern_counts = {}
        for log in logs:
            for pattern, pattern_type in self._error_patterns:
                if re.search(pattern, log.message, re.IGNORECASE):
                    pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
        
        # 转换为列表
        for pattern_type, count in pattern_counts.items():
            if count > 0:
                patterns.append({
                    'type': pattern_type,
                    'count': count,
                    'frequency': count / len(logs) if logs else 0
                })
        
        return patterns
    
    def _generate_summary(self, stats: Dict, patterns: List[Dict]) -> str:
        """生成分析摘要"""
        total = stats['total']
        error_count = stats['by_level'].get('ERROR', 0)
        warning_count = stats['by_level'].get('WARNING', 0)
        
        if error_count > 0:
            return f"发现 {error_count} 个错误和 {warning_count} 个警告"
        elif warning_count > 5:
            return f"发现 {warning_count} 个警告，需要关注"
        else:
            return "系统运行正常"
    
    def _identify_issues(self, stats: Dict, patterns: List[Dict], errors: List[LogEntry]) -> List[Dict[str, Any]]:
        """识别具体问题"""
        issues = []
        
        # 检查错误率
        if stats['error_rate'] > 0.1:
            issues.append({
                'type': 'high_error_rate',
                'severity': 'high',
                'message': f"错误率过高: {stats['error_rate']:.1%}",
                'count': stats['by_level'].get('ERROR', 0)
            })
        
        # 检查特定模式
        for pattern in patterns:
            if pattern['type'] == 'memory' and pattern['count'] > 3:
                issues.append({
                    'type': 'memory_issue',
                    'severity': 'high',
                    'message': f"检测到 {pattern['count']} 次内存相关问题",
                    'suggestion': "检查内存使用情况，可能存在内存泄漏"
                })
            elif pattern['type'] == 'gpu' and pattern['count'] > 3:
                issues.append({
                    'type': 'gpu_issue',
                    'severity': 'medium',
                    'message': f"检测到 {pattern['count']} 次GPU相关问题",
                    'suggestion': "检查CUDA和GPU驱动状态"
                })
            elif pattern['type'] == 'timeout' and pattern['count'] > 2:
                issues.append({
                    'type': 'timeout_issue',
                    'severity': 'medium',
                    'message': f"检测到 {pattern['count']} 次超时问题",
                    'suggestion': "检查网络连接或增加超时时间"
                })
        
        # 检查重复错误
        if errors:
            error_messages = [e.message for e in errors]
            from collections import Counter
            common_errors = Counter(error_messages).most_common(3)
            for msg, count in common_errors:
                if count > 2:
                    issues.append({
                        'type': 'repeated_error',
                        'severity': 'medium',
                        'message': f"重复错误 ({count}次): {msg[:50]}...",
                        'suggestion': "需要修复根本原因"
                    })
        
        return issues
    
    def _generate_suggestions(self, stats: Dict, patterns: List[Dict]) -> List[str]:
        """生成建议"""
        suggestions = []
        
        if stats['error_rate'] > 0.05:
            suggestions.append("错误率较高，建议检查日志中的ERROR级别消息")
        
        for pattern in patterns:
            if pattern['type'] == 'memory':
                suggestions.append("存在内存问题，建议监控内存使用并检查是否有内存泄漏")
            elif pattern['type'] == 'gpu':
                suggestions.append("GPU相关问题，建议检查CUDA环境和GPU驱动")
            elif pattern['type'] == 'connection':
                suggestions.append("连接问题，建议检查网络和服务状态")
        
        if not suggestions:
            suggestions.append("系统运行正常，无需特别处理")
        
        return suggestions
    
    def _determine_severity(self, stats: Dict, patterns: List[Dict]) -> str:
        """确定严重程度"""
        # 检查是否有严重错误
        if stats['by_level'].get('CRITICAL', 0) > 0:
            return 'critical'
        
        # 检查错误率
        if stats['error_rate'] > 0.2:
            return 'critical'
        elif stats['error_rate'] > 0.1:
            return 'high'
        elif stats['error_rate'] > 0.05:
            return 'medium'
        
        # 检查模式
        for pattern in patterns:
            if pattern['type'] in ('memory', 'critical') and pattern['count'] > 5:
                return 'high'
            elif pattern['count'] > 10:
                return 'medium'
        
        return 'low'
    
    def analyze_with_llm(self, logs: List[str] = None) -> Optional[str]:
        """使用LLM分析日志（需要配置LLM）"""
        try:
            # 尝试导入LLM模块
            from llm import get_llm
            
            if logs is None:
                logs = [log.raw for log in list(self._error_logs)[-10:]]
            
            if not logs:
                return "没有错误日志需要分析"
            
            # 构建提示词
            prompt = f"""请分析以下系统日志，识别问题并提供解决方案：

日志内容：
{chr(10).join(logs[:10])}

请提供：
1. 问题总结
2. 根本原因分析
3. 解决方案建议
4. 预防措施"""

            # 调用LLM（这里需要根据实际的LLM接口调整）
            # response = get_llm().chat(prompt)
            # return response
            
            return "LLM分析功能需要配置LLM接口后使用"
            
        except Exception as e:
            logger.error(f"[LogAnalyzer] LLM分析失败: {e}")
            return f"LLM分析失败: {e}"
    
    def get_latest_analysis(self) -> Optional[LogAnalysisResult]:
        """获取最新的分析结果"""
        if self._analysis_results:
            return self._analysis_results[-1]
        return None
    
    def get_analysis_history(self, count: int = 10) -> List[LogAnalysisResult]:
        """获取分析历史"""
        return list(self._analysis_results)[-count:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        return {
            'total_errors': len(self._error_logs),
            'total_warnings': len(self._warning_logs),
            'recent_errors': [
                {
                    'time': log.timestamp.strftime('%H:%M:%S'),
                    'module': log.module,
                    'message': log.message[:100]
                }
                for log in list(self._error_logs)[-5:]
            ]
        }
    
    def on_analysis_complete(self, callback: Callable) -> None:
        """注册分析完成回调"""
        self._on_analysis_complete.append(callback)
    
    def on_issue_detected(self, callback: Callable) -> None:
        """注册问题检测回调"""
        self._on_issue_detected.append(callback)
    
    def clear(self) -> None:
        """清空日志缓冲"""
        self._log_buffer.clear()
        self._error_logs.clear()
        self._warning_logs.clear()
        self._analysis_results.clear()
        logger.info("[LogAnalyzer] 已清空日志缓冲")


class LogAnalyzerHandler(logging.Handler):
    """日志分析器处理器"""
    
    def __init__(self, analyzer: LogAnalyzer) -> None:
        """初始化"""
        super().__init__()
        self.analyzer = analyzer
    
    def emit(self, record: logging.LogRecord) -> None:
        """发送日志到分析器"""
        try:
            self.analyzer.add_log(record)
        except Exception:
            self.handleError(record)


# 全局实例
_log_analyzer: Optional[LogAnalyzer] = None


def get_log_analyzer() -> LogAnalyzer:
    """获取日志分析器实例"""
    global _log_analyzer
    if _log_analyzer is None:
        _log_analyzer = LogAnalyzer()
    return _log_analyzer


def init_log_analyzer(analysis_interval: float = 60.0, auto_start: bool = True) -> LogAnalyzer:
    """
    初始化并启动日志分析器
    
    Args:
        analysis_interval: 分析间隔（秒）
        auto_start: 是否自动启动
    
    Returns:
        LogAnalyzer 实例
    """
    global _log_analyzer
    
    # 创建实例
    _log_analyzer = LogAnalyzer(analysis_interval=analysis_interval)
    
    # 注册到根日志器
    handler = LogAnalyzerHandler(_log_analyzer)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(handler)
    
    # 自动启动
    if auto_start:
        _log_analyzer.start()
    
    logger.info(f"[LogAnalyzer] 初始化完成 (间隔: {analysis_interval}秒, 自动启动: {auto_start})")
    return _log_analyzer
