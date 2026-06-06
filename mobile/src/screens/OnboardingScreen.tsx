/**
 * 引导页面
 *
 * 3步引导流程: 欢迎 → 服务器配置 → 完成
 */

import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Dimensions,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/Ionicons';
import { COLORS, SERVER_CONFIG } from '../utils/constants';
import { useAppStore } from '../store/appStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const STEPS = [
  {
    id: 'welcome',
    title: '欢迎使用咕咕嘎嘎',
    subtitle: '你的 AI VTuber 伙伴',
    icon: 'sparkles',
  },
  {
    id: 'server',
    title: '连接服务器',
    subtitle: '输入桌面端 IP 地址',
    icon: 'server-outline',
  },
  {
    id: 'complete',
    title: '准备就绪',
    subtitle: '开始你的 AI 之旅',
    icon: 'checkmark-circle',
  },
];

const OnboardingScreen: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [serverIp, setServerIp] = useState(SERVER_CONFIG.DEFAULT_HOST);
  const [serverPort, setServerPort] = useState(String(SERVER_CONFIG.DEFAULT_PORT));
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionResult, setConnectionResult] = useState<'success' | 'fail' | null>(null);
  const scrollViewRef = useRef<ScrollView>(null);

  const { setServerUrl, checkConnection, completeOnboarding } = useAppStore();

  // 下一步
  const goNext = () => {
    if (currentStep < STEPS.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      scrollViewRef.current?.scrollTo({
        x: nextStep * SCREEN_WIDTH,
        animated: true,
      });
    }
  };

  // 上一步
  const goPrev = () => {
    if (currentStep > 0) {
      const prevStep = currentStep - 1;
      setCurrentStep(prevStep);
      scrollViewRef.current?.scrollTo({
        x: prevStep * SCREEN_WIDTH,
        animated: true,
      });
    }
  };

  // 测试连接
  const testConnection = async () => {
    if (!serverIp.trim()) {
      Alert.alert('错误', '请输入服务器 IP 地址');
      return;
    }

    setIsConnecting(true);
    setConnectionResult(null);

    try {
      const url = `http://${serverIp.trim()}:${serverPort.trim()}`;
      await setServerUrl(url);
      const connected = await checkConnection();
      setConnectionResult(connected ? 'success' : 'fail');
    } catch {
      setConnectionResult('fail');
    } finally {
      setIsConnecting(false);
    }
  };

  // 跳过服务器配置
  const skipServerConfig = () => {
    setConnectionResult(null);
    goNext();
  };

  // 完成引导
  const finishOnboarding = async () => {
    await completeOnboarding();
    onComplete();
  };

  // 渲染欢迎步骤
  const renderWelcomeStep = () => (
    <View style={styles.stepContainer}>
      <View style={styles.iconContainer}>
        <Icon name="sparkles" size={80} color={COLORS.primary} />
      </View>
      <Text style={styles.stepTitle}>欢迎使用咕咕嘎嘎</Text>
      <Text style={styles.stepSubtitle}>
        你的 AI VTuber 伙伴{'\n'}随时随地与 AI 畅聊
      </Text>
      <View style={styles.featureList}>
        <View style={styles.featureItem}>
          <Icon name="chatbubbles-outline" size={24} color={COLORS.primary} />
          <Text style={styles.featureText}>智能对话</Text>
        </View>
        <View style={styles.featureItem}>
          <Icon name="person-outline" size={24} color={COLORS.primary} />
          <Text style={styles.featureText}>多角色切换</Text>
        </View>
        <View style={styles.featureItem}>
          <Icon name="cloud-outline" size={24} color={COLORS.primary} />
          <Text style={styles.featureText}>云端 LLM 支持</Text>
        </View>
      </View>
      <TouchableOpacity style={styles.primaryButton} onPress={goNext}>
        <Text style={styles.primaryButtonText}>开始设置</Text>
        <Icon name="arrow-forward" size={20} color={COLORS.white} />
      </TouchableOpacity>
    </View>
  );

  // 渲染服务器配置步骤
  const renderServerStep = () => (
    <View style={styles.stepContainer}>
      <View style={styles.iconContainer}>
        <Icon name="server-outline" size={80} color={COLORS.primary} />
      </View>
      <Text style={styles.stepTitle}>连接服务器</Text>
      <Text style={styles.stepSubtitle}>
        输入桌面端的 IP 地址以连接到后端服务
      </Text>

      <View style={styles.inputGroup}>
        <Text style={styles.inputLabel}>服务器 IP</Text>
        <TextInput
          style={styles.textInput}
          value={serverIp}
          onChangeText={setServerIp}
          placeholder="例如: 192.168.1.100"
          placeholderTextColor={COLORS.lightGray}
          keyboardType="numeric"
          autoCapitalize="none"
          autoCorrect={false}
        />
      </View>

      <View style={styles.inputGroup}>
        <Text style={styles.inputLabel}>端口号</Text>
        <TextInput
          style={styles.textInput}
          value={serverPort}
          onChangeText={setServerPort}
          placeholder="默认: 8080"
          placeholderTextColor={COLORS.lightGray}
          keyboardType="numeric"
        />
      </View>

      {/* 连接状态 */}
      {connectionResult && (
        <View
          style={[
            styles.statusBox,
            {
              backgroundColor:
                connectionResult === 'success'
                  ? COLORS.success + '20'
                  : COLORS.error + '20',
            },
          ]}
        >
          <Icon
            name={
              connectionResult === 'success'
                ? 'checkmark-circle'
                : 'close-circle'
            }
            size={20}
            color={connectionResult === 'success' ? COLORS.success : COLORS.error}
          />
          <Text
            style={[
              styles.statusText,
              {
                color:
                  connectionResult === 'success' ? COLORS.success : COLORS.error,
              },
            ]}
          >
            {connectionResult === 'success' ? '连接成功！' : '连接失败，请检查 IP 地址'}
          </Text>
        </View>
      )}

      <View style={styles.buttonRow}>
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={testConnection}
          disabled={isConnecting}
        >
          {isConnecting ? (
            <ActivityIndicator size="small" color={COLORS.primary} />
          ) : (
            <>
              <Icon name="wifi-outline" size={18} color={COLORS.primary} />
              <Text style={styles.secondaryButtonText}>测试连接</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      <View style={styles.bottomButtons}>
        <TouchableOpacity style={styles.textButton} onPress={skipServerConfig}>
          <Text style={styles.textButtonText}>跳过，稍后设置</Text>
        </TouchableOpacity>
        {connectionResult === 'success' && (
          <TouchableOpacity style={styles.primaryButton} onPress={goNext}>
            <Text style={styles.primaryButtonText}>下一步</Text>
            <Icon name="arrow-forward" size={20} color={COLORS.white} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  // 渲染完成步骤
  const renderCompleteStep = () => (
    <View style={styles.stepContainer}>
      <View style={styles.iconContainer}>
        <Icon name="checkmark-circle" size={80} color={COLORS.success} />
      </View>
      <Text style={styles.stepTitle}>准备就绪！</Text>
      <Text style={styles.stepSubtitle}>
        一切就绪，开始和你的 AI 伙伴聊天吧
      </Text>

      <View style={styles.summaryBox}>
        <View style={styles.summaryItem}>
          <Icon name="server-outline" size={20} color={COLORS.primary} />
          <Text style={styles.summaryText}>
            服务器: {serverIp}:{serverPort}
          </Text>
        </View>
        <View style={styles.summaryItem}>
          <Icon name="person-outline" size={20} color={COLORS.primary} />
          <Text style={styles.summaryText}>默认角色: 小助手</Text>
        </View>
      </View>

      <TouchableOpacity
        style={[styles.primaryButton, styles.finishButton]}
        onPress={finishOnboarding}
      >
        <Text style={styles.primaryButtonText}>开始使用</Text>
        <Icon name="rocket-outline" size={20} color={COLORS.white} />
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* 步骤指示器 */}
      <View style={styles.stepIndicator}>
        {STEPS.map((step, index) => (
          <View key={step.id} style={styles.stepDotContainer}>
            <View
              style={[
                styles.stepDot,
                index <= currentStep && styles.stepDotActive,
              ]}
            >
              {index < currentStep ? (
                <Icon name="checkmark" size={14} color={COLORS.white} />
              ) : (
                <Text
                  style={[
                    styles.stepDotText,
                    index <= currentStep && styles.stepDotTextActive,
                  ]}
                >
                  {index + 1}
                </Text>
              )}
            </View>
            {index < STEPS.length - 1 && (
              <View
                style={[
                  styles.stepLine,
                  index < currentStep && styles.stepLineActive,
                ]}
              />
            )}
          </View>
        ))}
      </View>

      {/* 内容区域 */}
      <ScrollView
        ref={scrollViewRef}
        horizontal
        pagingEnabled
        scrollEnabled={false}
        showsHorizontalScrollIndicator={false}
        style={styles.scrollView}
      >
        {renderWelcomeStep()}
        {renderServerStep()}
        {renderCompleteStep()}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.white,
  },
  stepIndicator: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 20,
    paddingHorizontal: 40,
  },
  stepDotContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: COLORS.lightGray,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stepDotActive: {
    backgroundColor: COLORS.primary,
  },
  stepDotText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.gray,
  },
  stepDotTextActive: {
    color: COLORS.white,
  },
  stepLine: {
    width: 60,
    height: 2,
    backgroundColor: COLORS.lightGray,
    marginHorizontal: 8,
  },
  stepLineActive: {
    backgroundColor: COLORS.primary,
  },
  scrollView: {
    flex: 1,
  },
  stepContainer: {
    width: SCREEN_WIDTH,
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  iconContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: COLORS.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  stepTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: 8,
    textAlign: 'center',
  },
  stepSubtitle: {
    fontSize: 16,
    color: COLORS.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
  },
  featureList: {
    width: '100%',
    marginBottom: 40,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: COLORS.background,
    borderRadius: 12,
    marginBottom: 8,
  },
  featureText: {
    fontSize: 16,
    color: COLORS.text,
    marginLeft: 12,
  },
  inputGroup: {
    width: '100%',
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: 8,
  },
  textInput: {
    width: '100%',
    height: 48,
    backgroundColor: COLORS.background,
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 16,
    color: COLORS.text,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  statusBox: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 12,
    width: '100%',
    marginBottom: 16,
  },
  statusText: {
    fontSize: 14,
    marginLeft: 8,
  },
  buttonRow: {
    width: '100%',
    marginBottom: 16,
  },
  bottomButtons: {
    width: '100%',
    alignItems: 'center',
    gap: 12,
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.primary,
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 12,
    gap: 8,
    width: '100%',
  },
  primaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.white,
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.white,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.primary,
    gap: 8,
  },
  secondaryButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
  },
  textButton: {
    paddingVertical: 8,
  },
  textButtonText: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  finishButton: {
    marginTop: 16,
  },
  summaryBox: {
    width: '100%',
    backgroundColor: COLORS.background,
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  summaryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  summaryText: {
    fontSize: 14,
    color: COLORS.text,
    marginLeft: 12,
  },
});

export default OnboardingScreen;
