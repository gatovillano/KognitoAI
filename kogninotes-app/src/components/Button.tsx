// src/components/Button.tsx
import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator, ViewStyle } from 'react-native';
import { colors, borderRadius, spacing } from '../theme/colors';

interface ButtonProps {
    title: string;
    onPress: () => void;
    loading?: boolean;
    disabled?: boolean;
    variant?: 'primary' | 'secondary' | 'outline';
    style?: ViewStyle;
}

export const Button: React.FC<ButtonProps> = ({
    title,
    onPress,
    loading,
    disabled,
    variant = 'primary',
    style
}) => {
    const isButtonDisabled = loading || disabled;
    const getButtonStyle = () => {
        switch (variant) {
            case 'outline': return styles.outline;
            case 'secondary': return styles.secondary;
            default: return styles.primary;
        }
    };

    const getTextStyle = () => {
        switch (variant) {
            case 'outline': return styles.outlineText;
            default: return styles.text;
        }
    };

    return (
        <TouchableOpacity
            style={[
                styles.base, 
                getButtonStyle(), 
                style, 
                isButtonDisabled && styles.disabled
            ]}
            onPress={onPress}
            disabled={isButtonDisabled}
        >
            {loading ? (
                <ActivityIndicator color={variant === 'outline' ? colors.primary : colors.text} />
            ) : (
                <Text style={[styles.textBase, getTextStyle()]}>{title}</Text>
            )}
        </TouchableOpacity>
    );
};

const styles = StyleSheet.create({
    base: {
        paddingVertical: spacing.md,
        paddingHorizontal: spacing.lg,
        borderRadius: borderRadius.lg,
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 56,
    },
    primary: {
        backgroundColor: colors.primary,
    },
    secondary: {
        backgroundColor: colors.surface,
        borderWidth: 1,
        borderColor: colors.border,
    },
    outline: {
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderColor: colors.primary,
    },
    textBase: {
        fontSize: 16,
        fontWeight: '600',
    },
    text: {
        color: colors.text,
    },
    outlineText: {
        color: colors.primary,
    },
    disabled: {
        opacity: 0.5,
    },
});
