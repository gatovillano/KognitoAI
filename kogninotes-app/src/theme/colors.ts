// src/theme/colors.ts

export const palette = {
    // Primary based on Kognito logo (Blue to Cyan)
    primary: '#00bfff',      // Cyan (hsl(200 100% 50%))
    primaryLight: '#3399ff', // Soft Blue (hsl(220 100% 60%))
    primaryDark: '#0099cc',  // Darker Cyan

    // Dark Theme (Modern Slate/Deep Blue)
    darkBackground: '#181b21', // hsl(222 13% 11%)
    darkSurface: '#111418',    // hsl(222 13% 8%)
    darkBorder: '#23282f',     // hsl(222 13% 16%)
    darkText: '#e2e4e9',       // hsl(220 9% 89%)
    darkTextMuted: '#898fa3',  // hsl(220 9% 56%)

    // Light Theme (Soft Gray)
    lightBackground: '#fafafa', // hsl(0 0% 98%)
    lightSurface: '#ffffff',    // white
    lightBorder: '#e5e7eb',     // hsl(220 13% 91%)
    lightText: '#14171c',       // hsl(220 13% 9%)
    lightTextMuted: '#6b7280',  // hsl(220 9% 46%)

    error: '#ef4444',
    success: '#10b981',
    warning: '#f59e0b',
};

export const colors = {
    primary: palette.primary,
    primaryLight: palette.primaryLight,
    primaryDark: palette.primaryDark,
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
    primaryDark: palette.primaryDark,
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
    lg: 14, // Aligned with --radius: 0.875rem
    xl: 20,
    xxl: 28,
    full: 9999,
};

