// ============================================
// GuguGaga AI VTuber Mobile - 头部组件
// ============================================
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

interface HeaderProps {
  title: string;
  subtitle?: string;
  showBack?: boolean;
  onBack?: () => void;
  rightComponent?: React.ReactNode;
  backgroundColor?: string;
  textColor?: string;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  showBack = false,
  onBack,
  rightComponent,
  backgroundColor = '#fff',
  textColor = '#1f2937',
}) => {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { backgroundColor, paddingTop: insets.top }]}>
      <View style={styles.content}>
        {/* 左侧 */}
        <View style={styles.left}>
          {showBack && (
            <TouchableOpacity style={styles.backButton} onPress={onBack}>
              <Ionicons name="arrow-back" size={24} color={textColor} />
            </TouchableOpacity>
          )}
        </View>

        {/* 中间 */}
        <View style={styles.center}>
          <Text style={[styles.title, { color: textColor }]} numberOfLines={1}>
            {title}
          </Text>
          {subtitle && (
            <Text style={[styles.subtitle, { color: textColor + '99' }]} numberOfLines={1}>
              {subtitle}
            </Text>
          )}
        </View>

        {/* 右侧 */}
        <View style={styles.right}>
          {rightComponent}
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 56,
    paddingHorizontal: 16,
  },
  left: {
    width: 48,
    alignItems: 'flex-start',
  },
  center: {
    flex: 1,
    alignItems: 'center',
  },
  right: {
    width: 48,
    alignItems: 'flex-end',
  },
  backButton: {
    padding: 8,
    marginLeft: -8,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 12,
    marginTop: 2,
  },
});
