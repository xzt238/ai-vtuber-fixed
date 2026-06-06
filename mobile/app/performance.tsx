// ============================================
// 性能监控页面
// ============================================
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { 
  performanceMonitor, 
  PerformanceMetrics,
  PerformanceWarning,
  MonitorConfig 
} from '../src/services/performanceMonitor';

// 指标卡片组件
const MetricCard = React.memo(({ 
  icon, 
  label, 
  value, 
  unit, 
  color, 
  status 
}: { 
  icon: string;
  label: string;
  value: number;
  unit: string;
  color: string;
  status: 'good' | 'warning' | 'critical';
}) => {
  const statusColors = {
    good: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
  };
  
  return (
    <View style={[styles.metricCard, { borderLeftColor: statusColors[status] }]}>
      <View style={[styles.metricIcon, { backgroundColor: color + '15' }]}>
        <Ionicons name={icon as any} size={20} color={color} />
      </View>
      <View style={styles.metricInfo}>
        <Text style={styles.metricLabel}>{label}</Text>
        <Text style={styles.metricValue}>
          {typeof value === 'number' ? Math.round(value) : value}
          <Text style={styles.metricUnit}>{unit}</Text>
        </Text>
      </View>
    </View>
  );
});

// 警告项组件
const WarningItem = React.memo(({ warning }: { warning: PerformanceWarning }) => {
  const severityColors = {
    low: '#6b7280',
    medium: '#f59e0b',
    high: '#f97316',
    critical: '#ef4444',
  };
  
  const typeIcons = {
    fps: 'speedometer',
    memory: 'hardware-chip',
    cpu: 'cpu',
    network: 'wifi',
    battery: 'battery-dead',
  };
  
  return (
    <View style={[styles.warningItem, { borderLeftColor: severityColors[warning.severity] }]}>
      <Ionicons 
        name={typeIcons[warning.type] as any} 
        size={16} 
        color={severityColors[warning.severity]} 
      />
      <View style={styles.warningInfo}>
        <Text style={styles.warningMessage}>{warning.message}</Text>
        <Text style={styles.warningTime}>
          {new Date(warning.timestamp).toLocaleTimeString()}
        </Text>
      </View>
    </View>
  );
});

// 统计行组件
const StatRow = React.memo(({ label, value, unit }: { label: string; value: number; unit: string }) => (
  <View style={styles.statRow}>
    <Text style={styles.statLabel}>{label}</Text>
    <Text style={styles.statValue}>
      {typeof value === 'number' ? Math.round(value) : value}
      <Text style={styles.statUnit}>{unit}</Text>
    </Text>
  </View>
));

export default function PerformanceScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [warnings, setWarnings] = useState<PerformanceWarning[]>([]);
  const [config, setConfig] = useState<MonitorConfig>(performanceMonitor.getConfig());
  const [isRunning, setIsRunning] = useState(performanceMonitor.getIsRunning());
  
  // 监听指标更新
  useEffect(() => {
    const unsubscribe = performanceMonitor.onMetrics((newMetrics) => {
      setMetrics(newMetrics);
    });
    
    const unsubscribeWarning = performanceMonitor.onWarning((warning) => {
      setWarnings(prev => [warning, ...prev.slice(0, 49)]);
    });
    
    // 初始化
    setMetrics(performanceMonitor.getCurrentMetrics());
    setWarnings(performanceMonitor.getWarnings());
    
    return () => {
      unsubscribe();
      unsubscribeWarning();
    };
  }, []);
  
  // 获取统计
  const stats = useMemo(() => performanceMonitor.getStats(), [metrics]);
  const grade = useMemo(() => performanceMonitor.getPerformanceGrade(), [metrics]);
  const score = useMemo(() => performanceMonitor.getPerformanceScore(), [metrics]);
  
  // 切换监控
  const handleToggleMonitor = useCallback((value: boolean) => {
    performanceMonitor.updateConfig({ enabled: value });
    setConfig(performanceMonitor.getConfig());
    setIsRunning(value);
  }, []);
  
  // 切换悬浮窗
  const handleToggleOverlay = useCallback((value: boolean) => {
    performanceMonitor.updateConfig({ showOverlay: value });
    setConfig(performanceMonitor.getConfig());
  }, []);
  
  // 清除数据
  const handleClearData = useCallback(() => {
    Alert.alert(
      '清除数据',
      '确定要清除所有性能数据吗？',
      [
        { text: '取消', style: 'cancel' },
        { 
          text: '清除', 
          style: 'destructive',
          onPress: () => {
            performanceMonitor.clearData();
            performanceMonitor.clearWarnings();
            setMetrics(null);
            setWarnings([]);
          }
        },
      ]
    );
  }, []);
  
  // 获取指标状态
  const getMetricStatus = (type: string, value: number): 'good' | 'warning' | 'critical' => {
    switch (type) {
      case 'fps':
        if (value < 30) return 'critical';
        if (value < 45) return 'warning';
        return 'good';
      case 'memory':
        if (value > 800) return 'critical';
        if (value > 500) return 'warning';
        return 'good';
      case 'cpu':
        if (value > 90) return 'critical';
        if (value > 70) return 'warning';
        return 'good';
      default:
        return 'good';
    }
  };
  
  return (
    <>
      <Stack.Screen options={{ title: '性能监控', headerShown: false }} />
      <View style={[styles.container, { paddingTop: insets.top }]}>
        {/* 头部 */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1f2937" />
          </TouchableOpacity>
          <View style={styles.headerInfo}>
            <Text style={styles.headerTitle}>性能监控</Text>
            <Text style={styles.headerSubtitle}>
              {isRunning ? '监控中...' : '已停止'}
            </Text>
          </View>
          <TouchableOpacity 
            style={styles.clearButton}
            onPress={handleClearData}
          >
            <Ionicons name="trash-outline" size={20} color="#6b7280" />
          </TouchableOpacity>
        </View>
        
        <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
          {/* 性能评分 */}
          <View style={[styles.scoreCard, { borderColor: grade.color }]}>
            <View style={styles.scoreHeader}>
              <Text style={[styles.scoreGrade, { color: grade.color }]}>{grade.grade}</Text>
              <View style={styles.scoreInfo}>
                <Text style={styles.scoreValue}>{score}</Text>
                <Text style={styles.scoreLabel}>性能评分</Text>
              </View>
            </View>
            <Text style={[styles.scoreDesc, { color: grade.color }]}>{grade.description}</Text>
            
            {/* 评分条 */}
            <View style={styles.scoreBar}>
              <View 
                style={[
                  styles.scoreFill, 
                  { 
                    width: `${score}%`, 
                    backgroundColor: grade.color 
                  }
                ]} 
              />
            </View>
          </View>
          
          {/* 实时指标 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>实时指标</Text>
            <View style={styles.metricsGrid}>
              <MetricCard
                icon="speedometer"
                label="FPS"
                value={metrics?.fps || 0}
                unit=" fps"
                color="#6366f1"
                status={getMetricStatus('fps', metrics?.fps || 0)}
              />
              <MetricCard
                icon="hardware-chip"
                label="内存"
                value={metrics?.memoryUsed || 0}
                unit=" MB"
                color="#10b981"
                status={getMetricStatus('memory', metrics?.memoryUsed || 0)}
              />
              <MetricCard
                icon="cpu"
                label="CPU"
                value={metrics?.cpuUsage || 0}
                unit="%"
                color="#f59e0b"
                status={getMetricStatus('cpu', metrics?.cpuUsage || 0)}
              />
              <MetricCard
                icon="battery-full"
                label="电量"
                value={metrics?.batteryLevel || 0}
                unit="%"
                color="#ef4444"
                status="good"
              />
            </View>
          </View>
          
          {/* 网络信息 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>网络状态</Text>
            <View style={styles.networkCard}>
              <View style={styles.networkItem}>
                <Ionicons name="wifi" size={20} color="#6366f1" />
                <Text style={styles.networkLabel}>网络类型</Text>
                <Text style={styles.networkValue}>{metrics?.networkType || '未知'}</Text>
              </View>
              <View style={styles.networkDivider} />
              <View style={styles.networkItem}>
                <Ionicons name="speedometer" size={20} color="#10b981" />
                <Text style={styles.networkLabel}>网络速度</Text>
                <Text style={styles.networkValue}>
                  {metrics?.networkSpeed ? `${Math.round(metrics.networkSpeed)} KB/s` : '未知'}
                </Text>
              </View>
            </View>
          </View>
          
          {/* 渲染性能 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>渲染性能</Text>
            <View style={styles.renderCard}>
              <View style={styles.renderItem}>
                <Text style={styles.renderLabel}>渲染时间</Text>
                <Text style={styles.renderValue}>
                  {metrics?.renderTime ? `${metrics.renderTime.toFixed(1)} ms` : '-'}
                </Text>
              </View>
              <View style={styles.renderDivider} />
              <View style={styles.renderItem}>
                <Text style={styles.renderLabel}>JS 线程</Text>
                <Text style={styles.renderValue}>
                  {metrics?.jsThreadTime ? `${metrics.jsThreadTime.toFixed(1)} ms` : '-'}
                </Text>
              </View>
            </View>
          </View>
          
          {/* 统计信息 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>统计信息</Text>
            <View style={styles.statsCard}>
              <StatRow label="平均 FPS" value={stats.avgFps} unit=" fps" />
              <StatRow label="最低 FPS" value={stats.minFps} unit=" fps" />
              <StatRow label="最高 FPS" value={stats.maxFps} unit=" fps" />
              <View style={styles.statsDivider} />
              <StatRow label="平均内存" value={stats.avgMemory} unit=" MB" />
              <StatRow label="最大内存" value={stats.maxMemory} unit=" MB" />
              <View style={styles.statsDivider} />
              <StatRow label="平均 CPU" value={stats.avgCpu} unit="%" />
              <StatRow label="最大 CPU" value={stats.maxCpu} unit="%" />
              <View style={styles.statsDivider} />
              <StatRow label="总警告数" value={stats.totalWarnings} unit="" />
              <StatRow label="严重警告" value={stats.criticalWarnings} unit="" />
            </View>
          </View>
          
          {/* 设置 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>设置</Text>
            <View style={styles.settingsCard}>
              <View style={styles.settingItem}>
                <View style={styles.settingInfo}>
                  <Ionicons name="pulse" size={20} color="#6366f1" />
                  <Text style={styles.settingLabel}>启用监控</Text>
                </View>
                <Switch
                  value={config.enabled}
                  onValueChange={handleToggleMonitor}
                  trackColor={{ false: '#d1d5db', true: '#a5b4fc' }}
                  thumbColor={config.enabled ? '#6366f1' : '#f4f3f4'}
                />
              </View>
              <View style={styles.settingDivider} />
              <View style={styles.settingItem}>
                <View style={styles.settingInfo}>
                  <Ionicons name="phone-portrait" size={20} color="#10b981" />
                  <Text style={styles.settingLabel}>显示悬浮窗</Text>
                </View>
                <Switch
                  value={config.showOverlay}
                  onValueChange={handleToggleOverlay}
                  trackColor={{ false: '#d1d5db', true: '#a5b4fc' }}
                  thumbColor={config.showOverlay ? '#6366f1' : '#f4f3f4'}
                />
              </View>
            </View>
          </View>
          
          {/* 警告列表 */}
          {warnings.length > 0 && (
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>警告记录</Text>
                <TouchableOpacity onPress={() => performanceMonitor.clearWarnings()}>
                  <Text style={styles.clearText}>清除</Text>
                </TouchableOpacity>
              </View>
              {warnings.slice(0, 10).map((warning) => (
                <WarningItem key={warning.id} warning={warning} />
              ))}
            </View>
          )}
          
          {/* 使用说明 */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>使用说明</Text>
            <View style={styles.helpCard}>
              <View style={styles.helpItem}>
                <Ionicons name="information-circle" size={16} color="#6366f1" />
                <Text style={styles.helpText}>FPS 低于 30 会影响流畅度</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="warning" size={16} color="#f59e0b" />
                <Text style={styles.helpText}>内存超过 500MB 可能导致卡顿</Text>
              </View>
              <View style={styles.helpItem}>
                <Ionicons name="battery-dead" size={16} color="#ef4444" />
                <Text style={styles.helpText}>低电量时性能可能下降</Text>
              </View>
            </View>
          </View>
        </ScrollView>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#6b7280',
  },
  clearButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f3f4f6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 40,
  },
  scoreCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    borderWidth: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  scoreHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  scoreGrade: {
    fontSize: 48,
    fontWeight: '700',
    marginRight: 16,
  },
  scoreInfo: {
    flex: 1,
  },
  scoreValue: {
    fontSize: 32,
    fontWeight: '600',
    color: '#1f2937',
  },
  scoreLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  scoreDesc: {
    fontSize: 14,
    marginBottom: 12,
  },
  scoreBar: {
    height: 8,
    backgroundColor: '#e5e7eb',
    borderRadius: 4,
    overflow: 'hidden',
  },
  scoreFill: {
    height: '100%',
    borderRadius: 4,
  },
  section: {
    marginBottom: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 12,
  },
  clearText: {
    fontSize: 14,
    color: '#6366f1',
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  metricCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    width: '47%',
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  metricIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  metricInfo: {
    flex: 1,
  },
  metricLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1f2937',
  },
  metricUnit: {
    fontSize: 12,
    color: '#6b7280',
  },
  networkCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  networkItem: {
    flex: 1,
    alignItems: 'center',
  },
  networkDivider: {
    width: 1,
    backgroundColor: '#e5e7eb',
    marginVertical: 4,
  },
  networkLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 8,
    marginBottom: 4,
  },
  networkValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
  },
  renderCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  renderItem: {
    flex: 1,
    alignItems: 'center',
  },
  renderDivider: {
    width: 1,
    backgroundColor: '#e5e7eb',
    marginVertical: 4,
  },
  renderLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginBottom: 4,
  },
  renderValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
  },
  statsCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  statLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  statValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1f2937',
  },
  statUnit: {
    fontSize: 12,
    color: '#6b7280',
  },
  statsDivider: {
    height: 1,
    backgroundColor: '#e5e7eb',
    marginVertical: 8,
  },
  settingsCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  settingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  settingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  settingLabel: {
    fontSize: 15,
    color: '#1f2937',
  },
  settingDivider: {
    height: 1,
    backgroundColor: '#e5e7eb',
    marginVertical: 8,
  },
  warningItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderLeftWidth: 3,
    gap: 10,
  },
  warningInfo: {
    flex: 1,
  },
  warningMessage: {
    fontSize: 13,
    color: '#1f2937',
    marginBottom: 4,
  },
  warningTime: {
    fontSize: 11,
    color: '#9ca3af',
  },
  helpCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
  },
  helpItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 8,
  },
  helpText: {
    fontSize: 13,
    color: '#6b7280',
    flex: 1,
    lineHeight: 20,
  },
});