// src/components/Input.tsx
import React from 'react';
import { View, TextInput, Text, StyleSheet, TextInputProps } from 'react-native';
import { colors, borderRadius, spacing } from '../theme/colors';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({ label, error, style, ...props }) => {
  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}
      <TextInput
        style={[styles.input, error ? styles.inputError : null, style]}
        placeholderTextColor={colors.textMuted}
        {...props}
      />
      {error && <Text style={styles.errorText}>{error}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.md,
    width: '100%',
  },
  label: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '500',
    marginBottom: spacing.xs,
    marginLeft: 4,
  },
  input: {
    backgroundColor: colors.surface,
    color: colors.text,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    fontSize: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  inputError: {
    borderColor: colors.error,
  },
  errorText: {
    color: colors.error,
    fontSize: 12,
    marginTop: 4,
    marginLeft: 4,
  },
});
