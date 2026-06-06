/**
 * 应用导航器
 *
 * 包含引导流程、底部标签导航和堆栈导航
 */

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import Icon from 'react-native-vector-icons/Ionicons';

// 导入页面
import ChatScreen from '../screens/ChatScreen';
import CharacterScreen from '../screens/CharacterScreen';
import SettingsScreen from '../screens/SettingsScreen';
import MemoryScreen from '../screens/MemoryScreen';
import LiveScreen from '../screens/LiveScreen';
import OnboardingScreen from '../screens/OnboardingScreen';

// 导入类型和常量
import { COLORS } from '../utils/constants';
import { RootStackParamList, MainTabParamList } from '../types';

const Tab = createBottomTabNavigator<MainTabParamList>();
const Stack = createNativeStackNavigator<RootStackParamList>();

// 底部标签导航
const TabNavigator = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: string;

          switch (route.name) {
            case 'Chat':
              iconName = focused ? 'chatbubbles' : 'chatbubbles-outline';
              break;
            case 'Character':
              iconName = focused ? 'person' : 'person-outline';
              break;
            case 'Memory':
              iconName = focused ? 'library' : 'library-outline';
              break;
            case 'Live':
              iconName = focused ? 'videocam' : 'videocam-outline';
              break;
            case 'Settings':
              iconName = focused ? 'settings' : 'settings-outline';
              break;
            default:
              iconName = 'help-outline';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: COLORS.primary,
        tabBarInactiveTintColor: COLORS.gray,
        tabBarStyle: {
          backgroundColor: COLORS.white,
          borderTopWidth: 1,
          borderTopColor: COLORS.lightGray,
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '600',
        },
        headerShown: false,
      })}
    >
      <Tab.Screen
        name="Chat"
        component={ChatScreen}
        options={{ tabBarLabel: '对话' }}
      />
      <Tab.Screen
        name="Character"
        component={CharacterScreen}
        options={{ tabBarLabel: '角色' }}
      />
      <Tab.Screen
        name="Memory"
        component={MemoryScreen}
        options={{ tabBarLabel: '记忆' }}
      />
      <Tab.Screen
        name="Live"
        component={LiveScreen}
        options={{ tabBarLabel: '直播' }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ tabBarLabel: '设置' }}
      />
    </Tab.Navigator>
  );
};

// 主导航器
interface AppNavigatorProps {
  onboardingCompleted: boolean;
  onCompleteOnboarding: () => void;
}

const AppNavigator: React.FC<AppNavigatorProps> = ({
  onboardingCompleted,
  onCompleteOnboarding,
}) => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      {!onboardingCompleted ? (
        <Stack.Screen name="Onboarding">
          {() => <OnboardingScreen onComplete={onCompleteOnboarding} />}
        </Stack.Screen>
      ) : (
        <Stack.Screen name="Main" component={TabNavigator} />
      )}
    </Stack.Navigator>
  );
};

export default AppNavigator;
