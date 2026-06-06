// ============================================
// GuguGaga AI VTuber Mobile - 角色卡片组件
// ============================================
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { Character } from '../types';

interface CharacterCardProps {
  character: Character;
  onPress: (character: Character) => void;
  onLongPress?: (character: Character) => void;
  isSelected?: boolean;
}

export const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  onPress,
  onLongPress,
  isSelected = false,
}) => {
  return (
    <TouchableOpacity
      style={[styles.container, isSelected && styles.selectedContainer]}
      onPress={() => onPress(character)}
      onLongPress={() => onLongPress?.(character)}
      activeOpacity={0.7}
    >
      {/* 角色头像 */}
      <View style={styles.avatarContainer}>
        {character.avatar ? (
          <Image source={{ uri: character.avatar }} style={styles.avatar} />
        ) : (
          <View style={[styles.avatar, styles.defaultAvatar]}>
            <Ionicons name="person" size={32} color="#fff" />
          </View>
        )}
        {/* 在线状态指示器 */}
        <View style={styles.onlineIndicator} />
      </View>

      {/* 角色信息 */}
      <View style={styles.infoContainer}>
        <Text style={styles.name} numberOfLines={1}>
          {character.name}
        </Text>
        <Text style={styles.description} numberOfLines={2}>
          {character.description}
        </Text>
        
        {/* 标签 */}
        {character.tags.length > 0 && (
          <View style={styles.tagsContainer}>
            {character.tags.slice(0, 3).map((tag, index) => (
              <View key={index} style={styles.tag}>
                <Text style={styles.tagText}>{tag}</Text>
              </View>
            ))}
            {character.tags.length > 3 && (
              <Text style={styles.moreTag}>+{character.tags.length - 3}</Text>
            )}
          </View>
        )}
      </View>

      {/* 操作按钮 */}
      <View style={styles.actionContainer}>
        <TouchableOpacity
          style={styles.chatButton}
          onPress={() => onPress(character)}
        >
          <Ionicons name="chatbubble" size={20} color="#fff" />
          <Text style={styles.chatButtonText}>聊天</Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    marginHorizontal: 16,
    marginVertical: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  selectedContainer: {
    borderWidth: 2,
    borderColor: '#6366f1',
    backgroundColor: '#f5f3ff',
  },
  avatarContainer: {
    position: 'relative',
    marginRight: 12,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
  defaultAvatar: {
    backgroundColor: '#6366f1',
  },
  onlineIndicator: {
    position: 'absolute',
    bottom: 2,
    right: 2,
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: '#10b981',
    borderWidth: 2,
    borderColor: '#fff',
  },
  infoContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  name: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 4,
  },
  description: {
    fontSize: 14,
    color: '#6b7280',
    lineHeight: 20,
    marginBottom: 8,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  tag: {
    backgroundColor: '#e0e7ff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 6,
    marginBottom: 4,
  },
  tagText: {
    fontSize: 12,
    color: '#6366f1',
    fontWeight: '500',
  },
  moreTag: {
    fontSize: 12,
    color: '#9ca3af',
    marginLeft: 4,
  },
  actionContainer: {
    justifyContent: 'center',
    marginLeft: 12,
  },
  chatButton: {
    backgroundColor: '#6366f1',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
  },
  chatButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
});
