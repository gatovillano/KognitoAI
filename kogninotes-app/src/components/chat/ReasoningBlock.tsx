// src/components/chat/ReasoningBlock.tsx
import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, LayoutAnimation, Platform, UIManager } from 'react-native';
import { BrainCircuit, ChevronDown, Sparkles } from 'lucide-react-native';
import Markdown from 'react-native-markdown-display';

// Enable LayoutAnimation for Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

interface Props {
  content: string;
  isDarkMode: boolean;
  theme: any;
  markdownStyles: any;
}

export const ReasoningBlock: React.FC<Props> = ({ content, isDarkMode, theme, markdownStyles }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggle = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setIsExpanded(!isExpanded);
  };

  if (!content) return null;

  return (
    <View style={[
      styles.container, 
      { 
        backgroundColor: isDarkMode ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
        borderColor: theme.border + '30'
      }
    ]}>
      <TouchableOpacity 
        onPress={toggle} 
        style={styles.header}
        activeOpacity={0.7}
      >
        <View style={styles.titleRow}>
          <BrainCircuit size={14} color={theme.primary} style={{ marginRight: 8 }} />
          <Text style={[styles.title, { color: theme.textMuted }]}>
            {isExpanded ? 'Pensamiento del Sistema' : 'Pensamiento'}
          </Text>
        </View>
        <ChevronDown 
          size={16} 
          color={theme.textMuted} 
          style={{ 
            transform: [{ rotate: isExpanded ? '180deg' : '0deg' }],
            opacity: 0.6
          }} 
        />
      </TouchableOpacity>
      
      {isExpanded && (
        <View style={styles.body}>
          <View style={[styles.borderLeft, { backgroundColor: theme.primary + '40' }]} />
          <View style={styles.content}>
            {/* @ts-ignore */}
            <Markdown style={{
              ...markdownStyles,
              body: { ...markdownStyles.body, fontSize: 13, color: theme.textMuted, fontStyle: 'italic' }
            }}>
              {content}
            </Markdown>
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
    width: '100%',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    paddingHorizontal: 16,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  title: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  body: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  borderLeft: {
    width: 2,
    borderRadius: 1,
    marginRight: 14,
  },
  content: {
    flex: 1,
  }
});
