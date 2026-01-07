// src/theme/colors.ts

export const palette = {
    primary: '#6366f1',
    primaryLight: '#818cf8',
    primaryDark: '#4f46e5',

    // Dark Theme (Slate)
    darkBackground: '#0f172a',
    darkSurface: '#1e293b',
    darkBorder: '#334155',
    darkText: '#f8fafc',
    darkTextMuted: '#94a3b8',

    // Light Theme (Slate)
    lightBackground: '#f8fafc',
    lightSurface: '#ffffff',
    lightBorder: '#e2e8f0',
    lightText: '#0f172a',
    lightTextMuted: '#64748b',

    error: '#ef4444',
    success: '#10b981',
    warning: '#f59e0b',
};

export const colors = {
    primary: palette.primary,
    primaryLight: palette.primaryLight,
    background: palette.darkBackground,
    surface: palette.darkSurface,
    border: palette.darkBorder,
    text: palette.darkText,
    textMuted: palette.darkTextMuted,
    error: palette.error,
    success: palette.success,
    warning: palette.warning,
};

export const lightColors = {
    primary: palette.primary,
    primaryLight: palette.primaryLight,
    background: palette.lightBackground,
    surface: palette.lightSurface,
    border: palette.lightBorder,
    text: palette.lightText,
    textMuted: palette.lightTextMuted,
    error: palette.error,
    success: palette.success,
    warning: palette.warning,
};

export const spacing = {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
};

export const borderRadius = {
    sm: 4,
    md: 8,
    lg: 16,
    xl: 24,
    full: 9999,
};
