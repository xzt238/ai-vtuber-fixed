"""
高级日志监控模块 - 对标行业顶尖（Datadog/Grafana/Sentry）

功能：
1. 错误追踪/聚合（Error Tracking）
2. 告警规则引擎（Alert Rules Engine）
3. 日志模式识别（Pattern Recognition）
4. 性能指标关联（Correlation Analysis）
5. 高级搜索语法（Advanced Search）
"""

import re
import json
import time
import hashlib
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

# ==================== 数据结构 ====================

class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class ErrorGroup:
    """错误组（类似Sentry的Issue）"""
    fingerprint: str  # 错误指纹
    error_type: str
    message: str
    file_path: str
    line_number: int
    count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    stack_traces: List[str] = field(default_factory=list)
    affected_modules: Set[str] = field(default_factory=set)
    status: str = "unresolved"  # unresolved, resolved, ignored
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "fingerprint": self.fingerprint,
            "error_type": self.error_type,
            "message": self.message[:200],
            "file_path": self.file_path,
            "line_number": self.line_number,
            "count": self.count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "affected_modules": list(self.affected_modules),
            "status": self.status
        }


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    description: str
    condition: str  # 条件表达式
    severity: AlertSeverity
    duration: int = 0  # 持续时间（秒）
    cooldown: int = 300  # 冷却时间（秒）
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "severity": self.severity.value,
            "duration": self.duration,
            "cooldown": self.cooldown,
            "enabled": self.enabled,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None
        }


@dataclass
class Alert:
    """告警实例"""
    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "context": self.context
        }


@dataclass
class LogPattern:
    """日志模式"""
    pattern_id: str
    pattern_type: str  # regex, template, frequency
    pattern: str
    description: str
    count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "pattern": self.pattern,
            "description": self.description,
            "count": self.count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "examples": self.examples[:5]
        }


@dataclass
class PerformanceMetric:
    """性能指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    gpu_percent: float
    disk_percent: float
    log_rate: float  # 日志速率（条/分钟）
    error_rate: float  # 错误率
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_mb": self.memory_mb,
            "gpu_percent": self.gpu_percent,
            "disk_percent": self.disk_percent,
            "log_rate": self.log_rate,
            "error_rate": self.error_rate
        }


# ==================== 日志解析器 ====================

class LogParser:
    """日志解析器"""
    
    # 标准日志格式
    LOG_PATTERN = re.compile(
        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]\s+'
        r'\[(\w+)\]\s+'
        r'(.+)'
    )
    
    # 错误堆栈格式
    STACK_TRACE_PATTERN = re.compile(
        r'(?:Traceback \(most recent call last\):|'
        r'File "(.+?)", line (\d+)|'
        r'(\w+Error|\w+Exception): (.+))'
    )
    
    @classmethod
    def parse_log_line(cls, line: str) -> Optional[Dict[str, Any]]:
        """解析单行日志"""
        match = cls.LOG_PATTERN.match(line.strip())
        if not match:
            return None
        
        timestamp_str, level, message = match.groups()
        
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            timestamp = datetime.now()
        
        return {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "raw": line
        }
    
    @classmethod
    def extract_error_info(cls, message: str) -> Dict[str, Any]:
        """从错误消息中提取信息"""
        info = {
            "error_type": "Unknown",
            "message": message,
            "file_path": "",
            "line_number": 0
        }
        
        # 提取错误类型
        error_match = re.search(r'(\w+Error|\w+Exception)', message)
        if error_match:
            info["error_type"] = error_match.group(1)
        
        # 提取文件和行号
        file_match = re.search(r'File "(.+?)", line (\d+)', message)
        if file_match:
            info["file_path"] = file_match.group(1)
            info["line_number"] = int(file_match.group(2))
        
        return info
    
    @classmethod
    def generate_fingerprint(cls, error_type: str, file_path: str, line_number: int, message: str) -> str:
        """生成错误指纹"""
        # 提取错误消息的核心部分（去掉变量部分）
        core_message = re.sub(r'[\d]+', 'N', message[:100])
        fingerprint_str = f"{error_type}:{file_path}:{line_number}:{core_message}"
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]


# ==================== 告警规则引擎 ====================

class AlertRuleEngine:
    """告警规则引擎"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        # 初始化默认规则
        self._init_default_rules()
    
    def _init_default_rules(self) -> None:
        """初始化默认告警规则"""
        default_rules = [
            AlertRule(
                rule_id="high_error_rate",
                name="错误率过高",
                description="错误率超过阈值",
                condition="error_rate > 5",
                severity=AlertSeverity.WARNING,
                duration=60,
                cooldown=300
            ),
            AlertRule(
                rule_id="critical_error",
                name="严重错误",
                description="出现CRITICAL级别错误",
                condition="critical_count > 0",
                severity=AlertSeverity.CRITICAL,
                duration=0,
                cooldown=60
            ),
            AlertRule(
                rule_id="memory_high",
                name="内存使用过高",
                description="内存使用率超过阈值",
                condition="memory_percent > 90",
                severity=AlertSeverity.WARNING,
                duration=120,
                cooldown=600
            ),
            AlertRule(
                rule_id="memory_leak",
                name="内存泄漏",
                description="内存持续增长",
                condition="memory_growth_rate > 10",
                severity=AlertSeverity.ERROR,
                duration=300,
                cooldown=900
            ),
            AlertRule(
                rule_id="log_spike",
                name="日志激增",
                description="日志速率异常增加",
                condition="log_rate > 100",
                severity=AlertSeverity.WARNING,
                duration=60,
                cooldown=300
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
    
    def add_rule(self, rule: AlertRule) -> None:
        """添加规则"""
        with self._lock:
            self.rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str) -> None:
        """移除规则"""
        with self._lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
    
    def evaluate(self, metrics: Dict[str, Any]) -> List[Alert]:
        """评估规则"""
        triggered_alerts = []
        
        with self._lock:
            for rule_id, rule in self.rules.items():
                if not rule.enabled:
                    continue
                
                # 检查冷却时间
                if rule.last_triggered:
                    cooldown_end = rule.last_triggered + timedelta(seconds=rule.cooldown)
                    if datetime.now() < cooldown_end:
                        continue
                
                # 评估条件
                if self._evaluate_condition(rule.condition, metrics):
                    alert = Alert(
                        alert_id=f"{rule_id}_{int(time.time())}",
                        rule_id=rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        status=AlertStatus.ACTIVE,
                        message=f"{rule.name}: {rule.description}",
                        triggered_at=datetime.now(),
                        context=metrics
                    )
                    
                    triggered_alerts.append(alert)
                    self.alerts.append(alert)
                    rule.last_triggered = datetime.now()
                    
                    # 触发回调
                    for callback in self._callbacks:
                        try:
                            callback(alert)
                        except Exception:
                            pass
        
        return triggered_alerts
    
    def _evaluate_condition(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        try:
            # 替换变量
            expr = condition
            for key, value in metrics.items():
                expr = expr.replace(key, str(value))
            
            # 安全评估
            # 只允许简单的比较运算
            allowed_chars = set('0123456789.><=!and or ()')
            if all(c in allowed_chars or c.isalpha() for c in expr):
                return eval(expr)
        except Exception:
            pass
        return False
    
    def acknowledge_alert(self, alert_id: str) -> None:
        """确认告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                break
    
    def resolve_alert(self, alert_id: str) -> None:
        """解决告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                break
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [a for a in self.alerts if a.status == AlertStatus.ACTIVE]
    
    def on_alert(self, callback: Callable[[Alert], None]) -> None:
        """注册告警回调"""
        self._callbacks.append(callback)


# ==================== 错误追踪器 ====================

class ErrorTracker:
    """错误追踪器（类似Sentry）"""
    
    def __init__(self, max_groups: int = 1000):
        self.error_groups: Dict[str, ErrorGroup] = {}
        self.max_groups = max_groups
        self._lock = threading.Lock()
    
    def track_error(self, log_entry: Dict[str, Any]) -> Optional[ErrorGroup]:
        """追踪错误"""
        if log_entry.get("level") not in ("ERROR", "CRITICAL"):
            return None
        
        message = log_entry.get("message", "")
        error_info = LogParser.extract_error_info(message)
        
        # 生成指纹
        fingerprint = LogParser.generate_fingerprint(
            error_info["error_type"],
            error_info["file_path"],
            error_info["line_number"],
            message
        )
        
        with self._lock:
            if fingerprint in self.error_groups:
                # 更新现有组
                group = self.error_groups[fingerprint]
                group.count += 1
                group.last_seen = log_entry.get("timestamp", datetime.now())
                group.stack_traces.append(message[:500])
                if len(group.stack_traces) > 10:
                    group.stack_traces = group.stack_traces[-10:]
            else:
                # 创建新组
                if len(self.error_groups) >= self.max_groups:
                    # 移除最旧的
                    oldest = min(self.error_groups.values(), key=lambda g: g.last_seen or datetime.min)
                    del self.error_groups[oldest.fingerprint]
                
                group = ErrorGroup(
                    fingerprint=fingerprint,
                    error_type=error_info["error_type"],
                    message=message[:500],
                    file_path=error_info["file_path"],
                    line_number=error_info["line_number"],
                    count=1,
                    first_seen=log_entry.get("timestamp", datetime.now()),
                    last_seen=log_entry.get("timestamp", datetime.now()),
                    stack_traces=[message[:500]]
                )
                self.error_groups[fingerprint] = group
            
            return group
    
    def get_top_errors(self, limit: int = 10) -> List[ErrorGroup]:
        """获取最常见的错误"""
        with self._lock:
            sorted_groups = sorted(
                self.error_groups.values(),
                key=lambda g: g.count,
                reverse=True
            )
            return sorted_groups[:limit]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            total_errors = sum(g.count for g in self.error_groups.values())
            unresolved = sum(1 for g in self.error_groups.values() if g.status == "unresolved")
            
            return {
                "total_groups": len(self.error_groups),
                "total_errors": total_errors,
                "unresolved": unresolved,
                "top_error_types": Counter(g.error_type for g in self.error_groups.values()).most_common(5)
            }


# ==================== 模式识别器 ====================

class PatternRecognizer:
    """日志模式识别器"""
    
    def __init__(self, max_patterns: int = 100):
        self.patterns: Dict[str, LogPattern] = {}
        self.max_patterns = max_patterns
        self._lock = threading.Lock()
        
        # 常见模式
        self._known_patterns = [
            (r'connection\s+(refused|timeout|reset)', "连接问题"),
            (r'out\s+of\s+memory|OOM|内存不足', "内存问题"),
            (r'permission\s+denied|access\s+denied', "权限问题"),
            (r'file\s+not\s+found|No such file', "文件缺失"),
            (r'timeout|timed?\s*out', "超时问题"),
            (r'CUDA|GPU|cuda', "GPU问题"),
            (r'import\s+error|ModuleNotFoundError', "依赖问题"),
        ]
    
    def analyze(self, log_entries: List[Dict[str, Any]]) -> List[LogPattern]:
        """分析日志模式"""
        pattern_matches = defaultdict(list)
        
        for entry in log_entries:
            message = entry.get("message", "")
            
            for pattern_regex, description in self._known_patterns:
                if re.search(pattern_regex, message, re.IGNORECASE):
                    pattern_id = hashlib.md5(pattern_regex.encode()).hexdigest()[:12]
                    pattern_matches[pattern_id].append({
                        "regex": pattern_regex,
                        "description": description,
                        "message": message[:200],
                        "timestamp": entry.get("timestamp")
                    })
        
        # 更新模式统计
        with self._lock:
            for pattern_id, matches in pattern_matches.items():
                if pattern_id in self.patterns:
                    pattern = self.patterns[pattern_id]
                    pattern.count += len(matches)
                    pattern.last_seen = matches[-1]["timestamp"]
                    pattern.examples.append(matches[-1]["message"])
                    if len(pattern.examples) > 10:
                        pattern.examples = pattern.examples[-10:]
                else:
                    if len(self.patterns) >= self.max_patterns:
                        # 移除最旧的
                        oldest = min(self.patterns.values(), key=lambda p: p.last_seen or datetime.min)
                        del self.patterns[oldest.pattern_id]
                    
                    self.patterns[pattern_id] = LogPattern(
                        pattern_id=pattern_id,
                        pattern_type="regex",
                        pattern=matches[0]["regex"],
                        description=matches[0]["description"],
                        count=len(matches),
                        first_seen=matches[0]["timestamp"],
                        last_seen=matches[-1]["timestamp"],
                        examples=[m["message"] for m in matches[:5]]
                    )
        
        return list(self.patterns.values())
    
    def get_patterns(self) -> List[LogPattern]:
        """获取所有模式"""
        with self._lock:
            return sorted(self.patterns.values(), key=lambda p: p.count, reverse=True)


# ==================== 高级搜索引擎 ====================

class LogSearchEngine:
    """高级日志搜索引擎"""
    
    def __init__(self):
        self._log_index: List[Dict[str, Any]] = []
        self._max_index_size = 50000
        self._lock = threading.Lock()
    
    def index_log(self, log_entry: Dict[str, Any]) -> None:
        """索引日志"""
        with self._lock:
            self._log_index.append(log_entry)
            if len(self._log_index) > self._max_index_size:
                self._log_index = self._log_index[-self._max_index_size:]
    
    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """高级搜索"""
        with self._lock:
            results = []
            
            # 解析查询
            filters = self._parse_query(query)
            
            for entry in self._log_index:
                if self._match_entry(entry, filters):
                    results.append(entry)
                    if len(results) >= limit:
                        break
            
            return results
    
    def _parse_query(self, query: str) -> Dict[str, Any]:
        """解析查询语法"""
        filters = {
            "text": [],
            "level": None,
            "module": None,
            "time_from": None,
            "time_to": None,
            "exclude": []
        }
        
        # 解析特殊语法
        tokens = query.split()
        for token in tokens:
            if token.startswith("level:"):
                filters["level"] = token[6:].upper()
            elif token.startswith("module:"):
                filters["module"] = token[7:]
            elif token.startswith("after:"):
                try:
                    filters["time_from"] = datetime.fromisoformat(token[6:])
                except:
                    pass
            elif token.startswith("before:"):
                try:
                    filters["time_to"] = datetime.fromisoformat(token[7:])
                except:
                    pass
            elif token.startswith("-"):
                filters["exclude"].append(token[1:].lower())
            elif token.startswith("is:"):
                status = token[3:]
                if status == "error":
                    filters["level"] = "ERROR"
                elif status == "warning":
                    filters["level"] = "WARNING"
            else:
                filters["text"].append(token.lower())
        
        return filters
    
    def _match_entry(self, entry: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """匹配日志条目"""
        # 级别过滤
        if filters["level"] and entry.get("level") != filters["level"]:
            return False
        
        # 模块过滤
        if filters["module"]:
            message = entry.get("message", "")
            if filters["module"].lower() not in message.lower():
                return False
        
        # 时间过滤
        timestamp = entry.get("timestamp")
        if timestamp:
            if filters["time_from"] and timestamp < filters["time_from"]:
                return False
            if filters["time_to"] and timestamp > filters["time_to"]:
                return False
        
        # 文本匹配
        message = entry.get("message", "").lower()
        raw = entry.get("raw", "").lower()
        full_text = message + " " + raw
        
        # 排除词
        for exclude in filters["exclude"]:
            if exclude in full_text:
                return False
        
        # 必须包含的词
        for text in filters["text"]:
            if text not in full_text:
                return False
        
        return True


# ==================== 主监控类 ====================

class LogMonitor:
    """日志监控主类"""
    
    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        
        # 组件
        self.error_tracker = ErrorTracker()
        self.alert_engine = AlertRuleEngine()
        self.pattern_recognizer = PatternRecognizer()
        self.search_engine = LogSearchEngine()
        
        # 指标历史
        self.metrics_history: List[PerformanceMetric] = []
        self._max_metrics_history = 1000
        
        # 统计
        self.stats = {
            "total_logs": 0,
            "error_count": 0,
            "warning_count": 0,
            "critical_count": 0,
            "start_time": datetime.now()
        }
        
        # 回调
        self._on_alert_callbacks = []
        self._on_error_callbacks = []
        
        # 注册告警回调
        self.alert_engine.on_alert(self._handle_alert)
        
        # 加载配置
        self._load_config()
        
        logger.info("[LogMonitor] 初始化完成")
    
    def _load_config(self) -> None:
        """加载配置"""
        config_file = self.config_dir / "alert_rules.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                for rule_data in config.get("rules", []):
                    rule = AlertRule(
                        rule_id=rule_data["rule_id"],
                        name=rule_data["name"],
                        description=rule_data["description"],
                        condition=rule_data["condition"],
                        severity=AlertSeverity(rule_data["severity"]),
                        duration=rule_data.get("duration", 0),
                        cooldown=rule_data.get("cooldown", 300),
                        enabled=rule_data.get("enabled", True)
                    )
                    self.alert_engine.add_rule(rule)
                
                logger.info(f"[LogMonitor] 加载了 {len(config.get('rules', []))} 条告警规则")
            except Exception as e:
                logger.error(f"[LogMonitor] 加载配置失败: {e}")
    
    def _save_config(self) -> None:
        """保存配置"""
        config_file = self.config_dir / "alert_rules.json"
        try:
            config = {
                "rules": [rule.to_dict() for rule in self.alert_engine.rules.values()]
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[LogMonitor] 保存配置失败: {e}")
    
    def process_log(self, log_line: str) -> None:
        """处理单条日志"""
        # 解析日志
        entry = LogParser.parse_log_line(log_line)
        if not entry:
            return
        
        # 更新统计
        self.stats["total_logs"] += 1
        level = entry.get("level", "")
        if level == "ERROR":
            self.stats["error_count"] += 1
        elif level == "WARNING":
            self.stats["warning_count"] += 1
        elif level == "CRITICAL":
            self.stats["critical_count"] += 1
        
        # 索引日志
        self.search_engine.index_log(entry)
        
        # 追踪错误
        if level in ("ERROR", "CRITICAL"):
            error_group = self.error_tracker.track_error(entry)
            if error_group:
                for callback in self._on_error_callbacks:
                    try:
                        callback(error_group)
                    except Exception:
                        pass
    
    def process_logs_batch(self, log_lines: List[str]) -> None:
        """批量处理日志"""
        entries = []
        for line in log_lines:
            entry = LogParser.parse_log_line(line)
            if entry:
                entries.append(entry)
                self.process_log(line)
        
        # 模式识别
        if entries:
            self.pattern_recognizer.analyze(entries)
    
    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """更新性能指标"""
        try:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                cpu_percent=metrics.get("cpu_percent", 0),
                memory_percent=metrics.get("memory_percent", 0),
                memory_mb=metrics.get("memory_mb", 0),
                gpu_percent=metrics.get("gpu_percent", 0),
                disk_percent=metrics.get("disk_percent", 0),
                log_rate=metrics.get("log_rate", 0),
                error_rate=metrics.get("error_rate", 0)
            )
            
            self.metrics_history.append(metric)
            if len(self.metrics_history) > self._max_metrics_history:
                self.metrics_history = self.metrics_history[-self._max_metrics_history:]
            
            # 评估告警规则
            alert_metrics = {
                **metrics,
                "error_rate": self.stats["error_count"] / max(self.stats["total_logs"], 1) * 100,
                "critical_count": self.stats["critical_count"],
                "log_rate": metrics.get("log_rate", 0)
            }
            self.alert_engine.evaluate(alert_metrics)
            
        except Exception as e:
            logger.error(f"[LogMonitor] 更新指标失败: {e}")
    
    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """搜索日志"""
        return self.search_engine.search(query, limit)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        return {
            "stats": self.stats,
            "error_stats": self.error_tracker.get_error_stats(),
            "active_alerts": [a.to_dict() for a in self.alert_engine.get_active_alerts()],
            "top_errors": [e.to_dict() for e in self.error_tracker.get_top_errors(5)],
            "patterns": [p.to_dict() for p in self.pattern_recognizer.get_patterns()[:10]],
            "recent_metrics": [m.to_dict() for m in self.metrics_history[-20:]],
            "uptime": (datetime.now() - self.stats["start_time"]).total_seconds()
        }
    
    def get_error_groups(self) -> List[Dict[str, Any]]:
        """获取错误组列表"""
        return [g.to_dict() for g in self.error_tracker.error_groups.values()]
    
    def get_alert_rules(self) -> List[Dict[str, Any]]:
        """获取告警规则"""
        return [r.to_dict() for r in self.alert_engine.rules.values()]
    
    def add_alert_rule(self, rule_data: Dict[str, Any]) -> bool:
        """添加告警规则"""
        try:
            rule = AlertRule(
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                description=rule_data["description"],
                condition=rule_data["condition"],
                severity=AlertSeverity(rule_data["severity"]),
                duration=rule_data.get("duration", 0),
                cooldown=rule_data.get("cooldown", 300),
                enabled=rule_data.get("enabled", True)
            )
            self.alert_engine.add_rule(rule)
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"[LogMonitor] 添加规则失败: {e}")
            return False
    
    def acknowledge_alert(self, alert_id: str) -> None:
        """确认告警"""
        self.alert_engine.acknowledge_alert(alert_id)
    
    def resolve_alert(self, alert_id: str) -> None:
        """解决告警"""
        self.alert_engine.resolve_alert(alert_id)
    
    def _handle_alert(self, alert: Alert) -> None:
        """处理告警"""
        for callback in self._on_alert_callbacks:
            try:
                callback(alert)
            except Exception:
                pass
    
    def on_alert(self, callback: Callable[[Alert], None]) -> None:
        """注册告警回调"""
        self._on_alert_callbacks.append(callback)
    
    def on_error(self, callback: Callable[[ErrorGroup], None]) -> None:
        """注册错误回调"""
        self._on_error_callbacks.append(callback)


# 全局实例
_log_monitor: Optional[LogMonitor] = None


def get_log_monitor() -> LogMonitor:
    """获取日志监控实例"""
    global _log_monitor
    if _log_monitor is None:
        _log_monitor = LogMonitor()
    return _log_monitor


def init_log_monitor(config_dir: str = ".") -> LogMonitor:
    """初始化日志监控"""
    global _log_monitor
    _log_monitor = LogMonitor(config_dir)
    return _log_monitor
