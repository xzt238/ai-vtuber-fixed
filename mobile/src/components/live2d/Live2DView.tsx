import React, { useRef, useCallback, useEffect, useState, memo } from 'react';
import { View, StyleSheet, TouchableOpacity, Text, Platform } from 'react-native';
import { WebView } from 'react-native-webview';

interface Live2DViewProps {
  emotion?: string;
  isSpeaking?: boolean;
  isTalking?: boolean; // 兼容旧接口
  message?: string; // 显示消息
  audioLevel?: number; // 0-1 音频音量
  onTouch?: (area: string) => void;
  onTapHead?: () => void; // 点击头部回调
  style?: any;
  visible?: boolean;
  onToggleVisibility?: () => void;
}

const Live2DView: React.FC<Live2DViewProps> = ({
  emotion = 'neutral',
  isSpeaking = false,
  isTalking = false,
  message,
  audioLevel = 0,
  onTouch,
  onTapHead,
  style,
  visible = true,
  onToggleVisibility,
}) => {
  // 合并 isSpeaking 和 isTalking
  const speaking = isSpeaking || isTalking;
  const webViewRef = useRef<WebView>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState(emotion);
  const lipSyncInterval = useRef<NodeJS.Timeout | null>(null);
  
  // 更新口型同步
  useEffect(() => {
    if (!isLoaded || !webViewRef.current) return;
    
    if (speaking) {
      // 模拟口型同步 - 基于音频音量或随机
      lipSyncInterval.current = setInterval(() => {
        const lipValue = audioLevel > 0 
          ? audioLevel 
          : 0.3 + Math.random() * 0.5; // 随机模拟
        
        webViewRef.current?.injectJavaScript(`
          window.setLipSync(${lipValue});
          true;
        `);
      }, 50);
    } else {
      // 停止说话
      if (lipSyncInterval.current) {
        clearInterval(lipSyncInterval.current);
        lipSyncInterval.current = null;
      }
      webViewRef.current?.injectJavaScript(`
        window.setLipSync(0);
        true;
      `);
    }
    
    return () => {
      if (lipSyncInterval.current) {
        clearInterval(lipSyncInterval.current);
      }
    };
  }, [isLoaded, speaking, audioLevel]);
  
  // 更新情感
  useEffect(() => {
    if (!isLoaded || !webViewRef.current) return;
    
    setCurrentEmotion(emotion);
    webViewRef.current?.injectJavaScript(`
      window.setEmotion('${emotion}', 0);
      true;
    `);
  }, [isLoaded, emotion]);
  
  // WebView 消息处理
  const handleMessage = useCallback((event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      
      switch (data.type) {
        case 'ready':
          setIsLoaded(true);
          break;
        case 'touch':
          onTouch?.(data.area);
          // 如果点击头部，触发 onTapHead 回调
          if (data.area === 'head' && onTapHead) {
            onTapHead();
          }
          break;
      }
    } catch (e) {}
  }, [onTouch, onTapHead]);
  
  // 注入的 JavaScript
  const injectedJavaScript = `
    // 禁止缩放
    document.addEventListener('gesturestart', function(e) { e.preventDefault(); });
    true;
  `;
  
  if (!visible) {
    return (
      <View style={[styles.container, style, styles.hidden]}>
        <TouchableOpacity 
          style={styles.showButton}
          onPress={onToggleVisibility}
        >
          <Text style={styles.showButtonText}>👁️</Text>
        </TouchableOpacity>
      </View>
    );
  }
  
  return (
    <View style={[styles.container, style]}>
      <WebView
        ref={webViewRef}
        source={require('../../../assets/web/live2d-v3.html')}
        style={styles.webview}
        onMessage={handleMessage}
        injectedJavaScript={injectedJavaScript}
        javaScriptEnabled={true}
        domStorageEnabled={false}
        scrollEnabled={false}
        bounces={false}
        overScrollMode="never"
        showsHorizontalScrollIndicator={false}
        showsVerticalScrollIndicator={false}
        mediaPlaybackRequiresUserAction={false}
        allowsInlineMediaPlayback={true}
        originWhitelist={['*']}
        mixedContentMode="always"
        androidLayerType="hardware"
        onError={(e) => console.warn('Live2D WebView error:', e)}
      />
      
      {/* 控制按钮 */}
      <View style={styles.controls}>
        <TouchableOpacity 
          style={styles.controlButton}
          onPress={onToggleVisibility}
        >
          <Text style={styles.controlText}>🙈</Text>
        </TouchableOpacity>
        
        {/* 情感指示器 */}
        <View style={[styles.emotionIndicator, { backgroundColor: getEmotionColor(currentEmotion) }]}>
          <Text style={styles.emotionText}>{getEmotionEmoji(currentEmotion)}</Text>
        </View>
      </View>
      
      {/* 加载状态 */}
      {!isLoaded && (
        <View style={styles.loading}>
          <Text style={styles.loadingText}>加载中...</Text>
        </View>
      )}
    </View>
  );
};

// 辅助函数
function getEmotionColor(emotion: string): string {
  const colors: Record<string, string> = {
    neutral: '#6366f1',
    happy: '#10b981',
    sad: '#6b7280',
    angry: '#ef4444',
    surprised: '#f59e0b',
    love: '#ec4899',
    thinking: '#8b5cf6',
  };
  return colors[emotion] || '#6366f1';
}

function getEmotionEmoji(emotion: string): string {
  const emojis: Record<string, string> = {
    neutral: '😐',
    happy: '😊',
    sad: '😢',
    angry: '😠',
    surprised: '😮',
    love: '🥰',
    thinking: '🤔',
  };
  return emojis[emotion] || '😐';
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'transparent',
    overflow: 'hidden',
    borderRadius: 16,
  },
  webview: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  hidden: {
    height: 50,
    justifyContent: 'center',
    alignItems: 'center',
  },
  showButton: {
    padding: 8,
  },
  showButtonText: {
    fontSize: 24,
  },
  controls: {
    position: 'absolute',
    top: 8,
    right: 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  controlButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  controlText: {
    fontSize: 16,
  },
  emotionIndicator: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emotionText: {
    fontSize: 16,
  },
  loading: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
  },
  loadingText: {
    fontSize: 14,
    color: '#6366f1',
  },
});

export default memo(Live2DView);
