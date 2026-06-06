// ============================================
// 动画卡片组件
// ============================================
import React, { useRef, useEffect } from 'react';
import { Animated, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';

interface AnimatedCardProps {
  children: React.ReactNode;
  onPress?: () => void;
  style?: ViewStyle;
  delay?: number;
  duration?: number;
}

export const AnimatedCard: React.FC<AnimatedCardProps> = ({
  children,
  onPress,
  style,
  delay = 0,
  duration = 300,
}) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;
  const scaleAnim = useRef(new Animated.Value(0.95)).current;
  
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration,
        delay,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration,
        delay,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 1,
        duration,
        delay,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);
  
  const handlePressIn = () => {
    Animated.spring(scaleAnim, {
      toValue: 0.98,
      useNativeDriver: true,
    }).start();
  };
  
  const handlePressOut = () => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      useNativeDriver: true,
    }).start();
  };
  
  const content = (
    <Animated.View
      style={[
        styles.card,
        style,
        {
          opacity: fadeAnim,
          transform: [
            { translateY: slideAnim },
            { scale: scaleAnim },
          ],
        },
      ]}
    >
      {children}
    </Animated.View>
  );
  
  if (onPress) {
    return (
      <TouchableOpacity
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={1}
      >
        {content}
      </TouchableOpacity>
    );
  }
  
  return content;
};

// 动画列表项
interface AnimatedListItemProps {
  children: React.ReactNode;
  index: number;
  delay?: number;
  style?: ViewStyle;
}

export const AnimatedListItem: React.FC<AnimatedListItemProps> = ({
  children,
  index,
  delay = 50,
  style,
}) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(20)).current;
  
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        delay: index * delay,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 300,
        delay: index * delay,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);
  
  return (
    <Animated.View
      style={[
        style,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      {children}
    </Animated.View>
  );
};

// 动画按钮
interface AnimatedButtonProps {
  children: React.ReactNode;
  onPress: () => void;
  style?: ViewStyle;
  disabled?: boolean;
}

export const AnimatedButton: React.FC<AnimatedButtonProps> = ({
  children,
  onPress,
  style,
  disabled = false,
}) => {
  const scaleAnim = useRef(new Animated.Value(1)).current;
  
  const handlePressIn = () => {
    Animated.spring(scaleAnim, {
      toValue: 0.95,
      useNativeDriver: true,
    }).start();
  };
  
  const handlePressOut = () => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      useNativeDriver: true,
    }).start();
  };
  
  return (
    <TouchableOpacity
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      disabled={disabled}
      activeOpacity={1}
    >
      <Animated.View
        style={[
          styles.button,
          style,
          disabled && styles.buttonDisabled,
          { transform: [{ scale: scaleAnim }] },
        ]}
      >
        {children}
      </Animated.View>
    </TouchableOpacity>
  );
};

// 动画图标
interface AnimatedIconProps {
  children: React.ReactNode;
  onPress?: () => void;
  size?: number;
  color?: string;
}

export const AnimatedIcon: React.FC<AnimatedIconProps> = ({
  children,
  onPress,
  size = 24,
  color = '#000',
}) => {
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  
  const handlePress = () => {
    Animated.sequence([
      Animated.timing(scaleAnim, {
        toValue: 1.2,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      }),
    ]).start();
    
    onPress?.();
  };
  
  return (
    <TouchableOpacity onPress={handlePress} activeOpacity={0.7}>
      <Animated.View
        style={{
          transform: [{ scale: scaleAnim }],
        }}
      >
        {children}
      </Animated.View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  button: {
    backgroundColor: '#6366f1',
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
});

export default AnimatedCard;
