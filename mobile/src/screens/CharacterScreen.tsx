/**
 * 角色页面
 *
 * 角色列表、选择、切换
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/Ionicons';
import { COLORS } from '../utils/constants';
import { useCharacterStore } from '../store/characterStore';
import { Character } from '../types/character';

const CharacterScreen: React.FC = () => {
  const { characters, activeCharacter, setActiveCharacter } = useCharacterStore();

  // 选择角色
  const handleSelectCharacter = (character: Character) => {
    if (character.id === activeCharacter?.id) return;

    Alert.alert(
      '切换角色',
      `确定要切换到 "${character.name}" 吗？当前对话上下文将保留。`,
      [
        { text: '取消', style: 'cancel' },
        {
          text: '确定',
          onPress: () => {
            setActiveCharacter(character.id);
            Alert.alert('成功', `已切换到 ${character.name}`);
          },
        },
      ]
    );
  };

  // 渲染角色卡片
  const renderCharacter = ({ item }: { item: Character }) => {
    const isActive = activeCharacter?.id === item.id;

    return (
      <TouchableOpacity
        style={[styles.characterCard, isActive && styles.selectedCard]}
        onPress={() => handleSelectCharacter(item)}
      >
        <View style={styles.avatarContainer}>
          {item.avatar ? (
            <Image source={{ uri: item.avatar }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatarPlaceholder, isActive && styles.avatarActive]}>
              <Icon name="person" size={40} color={COLORS.white} />
            </View>
          )}
        </View>
        <View style={styles.characterInfo}>
          <View style={styles.nameRow}>
            <Text style={styles.characterName}>{item.name}</Text>
            {item.isDefault && (
              <View style={styles.defaultBadge}>
                <Text style={styles.defaultBadgeText}>内置</Text>
              </View>
            )}
          </View>
          <Text style={styles.characterDesc}>{item.description}</Text>
          <View style={styles.traitsContainer}>
            {item.traits.slice(0, 3).map((trait, index) => (
              <View key={index} style={styles.traitTag}>
                <Text style={styles.traitText}>{trait.name}</Text>
              </View>
            ))}
          </View>
          <Text style={styles.greetingText} numberOfLines={2}>
            "{item.greeting}"
          </Text>
        </View>
        {isActive && (
          <View style={styles.checkContainer}>
            <Icon name="checkmark-circle" size={28} color={COLORS.primary} />
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* 头部 */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.headerTitle}>选择角色</Text>
          <Text style={styles.headerSubtitle}>
            当前: {activeCharacter?.name || '未选择'}
          </Text>
        </View>
      </View>

      {/* 角色列表 */}
      <FlatList
        data={characters}
        renderItem={renderCharacter}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListHeaderComponent={
          <View style={styles.sectionHeader}>
            <Icon name="information-circle-outline" size={16} color={COLORS.textSecondary} />
            <Text style={styles.sectionHeaderText}>
              选择一个角色开始对话，不同角色有不同的性格和说话风格
            </Text>
          </View>
        }
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: COLORS.white,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGray,
  },
  headerLeft: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.text,
  },
  headerSubtitle: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  listContent: {
    padding: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.primaryLight,
    padding: 12,
    borderRadius: 12,
    marginBottom: 16,
    gap: 8,
  },
  sectionHeaderText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    flex: 1,
  },
  characterCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  selectedCard: {
    borderWidth: 2,
    borderColor: COLORS.primary,
  },
  avatarContainer: {
    marginRight: 12,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
  },
  avatarPlaceholder: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarActive: {
    backgroundColor: COLORS.primaryDark,
  },
  characterInfo: {
    flex: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  characterName: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.text,
  },
  defaultBadge: {
    backgroundColor: COLORS.primaryLight,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  defaultBadgeText: {
    fontSize: 10,
    color: COLORS.primary,
    fontWeight: '600',
  },
  characterDesc: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginTop: 4,
  },
  traitsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
    gap: 6,
  },
  traitTag: {
    backgroundColor: COLORS.primaryLight,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  traitText: {
    fontSize: 12,
    color: COLORS.primary,
    fontWeight: '600',
  },
  greetingText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    fontStyle: 'italic',
    marginTop: 8,
    lineHeight: 18,
  },
  checkContainer: {
    marginLeft: 8,
    alignSelf: 'center',
  },
});

export default CharacterScreen;
