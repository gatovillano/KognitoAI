// src/components/chat/ToolCallBlock.tsx
import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { Folder, Loader2 } from 'lucide-react-native';

interface Props {
  part: {
    status?: 'start' | 'end' | 'error';
    tool_name?: string;
  };
  isDarkMode: boolean;
  theme: any;
}

export const ToolCallBlock: React.FC<Props> = ({ part, isDarkMode, theme }) => {
  const isPending = part.status === 'start' || !part.status;

  return (
    <View style={[
      styles.container, 
      { 
        backgroundColor: theme.primary + '08', 
        borderColor: theme.primary + '20' 
      }
    ]}>
      <View style={styles.iconContainer}>
        {isPending ? (
          <ActivityIndicator size="small" color={theme.primary} />
        ) : (
          <Folder size={16} color={theme.primary} />
        )}
      </View>
      <View style={styles.textContainer}>
        <Text style={[styles.toolText, { color: theme.primary }]}>
          {part.tool_name ? `Herramienta: ${part.tool_name}` : 'Ejecutando herramienta...'}
          {part.status === 'end' && ' - Completado'}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 12,
    gap: 12,
  },
  iconContainer: {
    width: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  textContainer: {
    flex: 1,
  },
  toolText: {
    fontSize: 12,
    fontWeight: '700',
    opacity: 0.8,
  }
});
