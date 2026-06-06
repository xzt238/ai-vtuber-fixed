// ============================================
// GuguGaga AI VTuber Mobile - 搜索栏组件
// ============================================
import React from 'react';
import { View, TextInput, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface SearchBarProps {
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  onSubmit?: () => void;
  autoFocus?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChangeText,
  placeholder = '搜索...',
  onSubmit,
  autoFocus = false,
}) => {
  return (
    <View style={styles.container}>
      <Ionicons name="search" size={20} color="#9ca3af" style={styles.icon} />
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#9ca3af"
        onSubmitEditing={onSubmit}
        autoFocus={autoFocus}
        returnKeyType="search"
        clearButtonMode="while-editing"
      />
      {value.length > 0 && (
        <TouchableOpacity
          style={styles.clearButton}
          onPress={() => onChangeText('')}
        >
          <Ionicons name="close-circle" size={20} color="#9ca3af" />
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f3f4f6',
    borderRadius: 12,
    paddingHorizontal: 12,
    marginHorizontal: 16,
    marginVertical: 8,
  },
  icon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    height: 44,
    fontSize: 16,
    color: '#1f2937',
  },
  clearButton: {
    padding: 4,
    marginLeft: 8,
  },
});
