import React, { useRef, useCallback, useEffect, useState, memo } from 'react';
import { View, StyleSheet, TouchableOpacity, Text, ActivityIndicator } from 'react-native';
import { WebView } from 'react-native-webview';

interface VRMViewProps {
  modelUrl?: string; // VRM 模型 URL
  emotion?: string;
  isSpeaking?: boolean;
  audioLevel?: number;
  onTouch?: (x: number, y: number) => void;
  onLoaded?: (animations: string[]) => void;
  onError?: (error: string) => void;
  style?: any;
  visible?: boolean;
  onToggleVisibility?: () => void;
}

const VRMView: React.FC<VRMViewProps> = ({
  modelUrl,
  emotion = 'neutral',
  isSpeaking = false,
  audioLevel = 0,
  onTouch,
  onLoaded,
  onError,
  style,
  visible = true,
  onToggleVisibility,
}) => {
  const webViewRef = useRef<WebView>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lipSyncInterval = useRef<NodeJS.Timeout | null>(null);
  
  // 加载模型
  useEffect(() => {
    if (!isLoaded || !webViewRef.current || !modelUrl) return;
    
    webViewRef.current.injectJavaScript(`
      window.loadVRM('${modelUrl}');
      true;
    `);
  }, [isLoaded, modelUrl]);
  
  // 口型同步
  useEffect(() => {
    if (!isLoaded || !webViewRef.current) return;
    
    if (isSpeaking) {
      lipSyncInterval.current = setInterval(() => {
        const lipValue = audioLevel > 0 
          ? audioLevel 
          : 0.3 + Math.random() * 0.5;
        
        webViewRef.current?.injectJavaScript(`
          window.setLipSync(${lipValue});
          true;
        `);
      }, 50);
    } else {
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
  }, [isLoaded, isSpeaking, audioLevel]);
  
  // 情感更新
  useEffect(() => {
    if (!isLoaded || !webViewRef.current) return;
    
    webViewRef.current?.injectJavaScript(`
      window.setEmotion('${emotion}');
      true;
    `);
  }, [isLoaded, emotion]);
  
  // 消息处理
  const handleMessage = useCallback((event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      
      switch (data.type) {
        case 'ready':
          setIsLoaded(true);
          setIsLoading(false);
          break;
        case 'loaded':
          setIsLoading(false);
          onLoaded?.(data.animations || []);
          break;
        case 'error':
          setError(data.message);
          setIsLoading(false);
          onError?.(data.message);
          break;
        case 'click':
          onTouch?.(data.x, data.y);
          break;
      }
    } catch (e) {}
  }, [onTouch, onLoaded, onError]);
  
  // 注入脚本
  const injectedJavaScript = `
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
          <Text style={styles.showButtonText}>📦</Text>
        </TouchableOpacity>
      </View>
    );
  }
  
  return (
    <View style={[styles.container, style]}>
      <WebView
        ref={webViewRef}
        source={require('../../../assets/web/vrm-viewer.html')}
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
        onError={(e) => {
          console.warn('VRM WebView error:', e);
          setError('WebView 加载失败');
        }}
      />
      
      {/* 控制按钮 */}
      <View style={styles.controls}>
        <TouchableOpacity 
          style={styles.controlButton}
          onPress={() => {
            webViewRef.current?.injectJavaScript(`
              window.resetCamera && window.resetCamera();
              true;
            `);
          }}
        >
          <Text style={styles.controlText}>🔄</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={styles.controlButton}
          onPress={onToggleVisibility}
        >
          <Text style={styles.controlText}>🙈</Text>
        </TouchableOpacity>
      </View>
      
      {/* 加载状态 */}
      {isLoading && (
        <View style={styles.loading}>
          <ActivityIndicator size="large" color="#6366f1" />
          <Text style={styles.loadingText}>加载 3D 模型...</Text>
        </View>
      )}
      
      {/* 错误状态 */}
      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>❌ {error}</Text>
          <TouchableOpacity 
            style={styles.retryButton}
            onPress={() => {
              setError(null);
              setIsLoading(true);
              webViewRef.current?.reload();
            }}
          >
            <Text style={styles.retryText}>重试</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

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
  loading: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#6366f1',
  },
  errorContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
  },
  errorText: {
    fontSize: 14,
    color: '#ef4444',
    marginBottom: 12,
  },
  retryButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#6366f1',
    borderRadius: 8,
  },
  retryText: {
    color: '#fff',
    fontSize: 14,
  },
});

export default memo(VRMView);
