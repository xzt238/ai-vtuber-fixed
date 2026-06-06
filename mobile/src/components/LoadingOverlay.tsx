// ============================================
// GuguGaga AI VTuber Mobile - 加载遮罩组件
// ============================================
import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Modal } from 'react-native';

interface LoadingOverlayProps {
  visible: boolean;
  message?: string;
  transparent?: boolean;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  visible,
  message = '加载中...',
  transparent = false,
}) => {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
    >
      <View style={[styles.container, transparent && styles.transparent]}>
        <View style={styles.content}>
          <ActivityIndicator size="large" color="#6366f1" />
          {message && <Text style={styles.message}>{message}</Text>}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  transparent: {
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  content: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 5,
  },
  message: {
    marginTop: 12,
    fontSize: 15,
    color: '#4b5563',
  },
});
