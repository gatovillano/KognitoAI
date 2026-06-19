// src/screens/InboxDetailScreen.tsx
import React, { useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Platform,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { inboxService } from '../api/inboxService';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import {
  ChevronLeft,
  Trash2,
  Lightbulb,
  Bot,
  Calendar as CalendarIcon,
} from 'lucide-react-native';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import Markdown from 'react-native-markdown-display';

export const InboxDetailScreen = ({ route, navigation }: any) => {
  const { item } = route.params;
  const { isDarkMode } = useAuth();
  const theme = isDarkMode ? colors : lightColors;

  const isInsight = item.kind === 'insight';
  const accentColor = isInsight ? theme.warning : theme.primary;

  const formatItemDate = (dateString: string) => {
    try {
      return format(new Date(dateString), "d 'de' MMMM, yyyy - HH:mm", { locale: es });
    } catch (e) {
      return dateString;
    }
  };

  const handleDelete = () => {
    Alert.alert(
      'Eliminar elemento',
      '¿Estás seguro de que deseas eliminar este elemento de tu bandeja de entrada?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: async () => {
            try {
              if (item.kind === 'agent_message') {
                await inboxService.deleteAgentMessage(item.payload.id);
              } else {
                await inboxService.deleteInsight(Number(item.payload.id));
              }
              // Volver a la pantalla anterior notificando que se borró el item
              if (route.params?.onDelete) {
                route.params.onDelete(item.id);
              }
              navigation.goBack();
            } catch (error) {
              console.error('Error deleting item:', error);
              Alert.alert('Error', 'No se pudo eliminar el elemento.');
            }
          },
        },
      ]
    );
  };

  const markdownStyles = useMemo(() => ({
    body: { color: theme.text, fontSize: 16, lineHeight: 26, fontWeight: '400' },
    paragraph: { marginVertical: 8 },
    link: { color: theme.primary, textDecorationLine: 'none' as 'none', fontWeight: '600' },
    code_inline: {
      backgroundColor: isDarkMode ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
      color: theme.primary,
      paddingHorizontal: 6,
      paddingVertical: 2,
      borderRadius: 6,
      fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
      fontSize: 14,
      borderWidth: 1,
      borderColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)',
    },
    fence: {
      backgroundColor: isDarkMode ? '#111' : '#f8f9fa',
      borderRadius: 12,
      padding: 16,
      marginVertical: 16,
      borderWidth: 1,
      borderColor: theme.border,
      fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
      fontSize: 13,
      lineHeight: 20,
    },
    blockquote: {
      backgroundColor: isDarkMode ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.01)',
      borderLeftColor: theme.primary,
      borderLeftWidth: 4,
      paddingHorizontal: 16,
      paddingVertical: 12,
      marginVertical: 16,
      borderRadius: 4,
    },
    bullet_list: { marginVertical: 8 },
    ordered_list: { marginVertical: 8 },
    list_item: { marginVertical: 4 },
    strong: { fontWeight: '700', color: theme.text },
    em: { fontStyle: 'italic' },
    hr: { borderBottomColor: theme.border, borderBottomWidth: 1, marginVertical: 20 },
  }), [theme, isDarkMode]);

  const content = isInsight ? item.payload.summary : item.payload.content;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border + '30' }]}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.iconBtn}>
          <ChevronLeft size={24} color={theme.text} />
        </TouchableOpacity>
        
        {/* Badge of type */}
        <View style={styles.typeBadgeContainer}>
          <View style={[styles.badgeIconBg, { backgroundColor: accentColor + '15' }]}>
            {isInsight ? (
              <Lightbulb size={12} color={accentColor} />
            ) : (
              <Bot size={12} color={accentColor} />
            )}
          </View>
          <Text style={[styles.typeBadgeText, { color: accentColor }]}>
            {isInsight ? 'Insight' : 'Mensaje'}
          </Text>
        </View>

        <TouchableOpacity onPress={handleDelete} style={styles.iconBtn}>
          <Trash2 size={20} color={theme.error} />
        </TouchableOpacity>
      </View>

      {/* Content Scroll */}
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={true}
        keyboardShouldPersistTaps="handled"
      >
        {/* Meta Row (Date & Workspace) */}
        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <CalendarIcon size={13} color={theme.textMuted} />
            <Text style={[styles.metaText, { color: theme.textMuted }]}>
              {formatItemDate(item.created_at)}
            </Text>
          </View>
          {item.payload.workspace_name && (
            <View style={[styles.metaItem, { marginLeft: spacing.md }]}>
              <View style={[styles.workspaceDot, { backgroundColor: item.payload.workspace_color || theme.primary }]} />
              <Text style={[styles.metaText, { color: theme.textMuted }]}>
                {item.payload.workspace_name}
              </Text>
            </View>
          )}
        </View>

        {/* Title */}
        <Text style={[styles.title, { color: theme.text }]}>
          {item.title}
        </Text>

        {/* Markdown Content */}
        <View style={styles.markdownContainer}>
          <Markdown style={markdownStyles}>
            {content}
          </Markdown>
        </View>

        {/* Action Suggestion box for Insights */}
        {isInsight && item.payload.action_suggestion && (
          <View
            style={[
              styles.suggestionBox,
              {
                backgroundColor: isDarkMode ? 'rgba(245, 158, 11, 0.05)' : 'rgba(245, 158, 11, 0.03)',
                borderColor: theme.warning + '30',
              },
            ]}
          >
            <View style={styles.suggestionTitleRow}>
              <Lightbulb size={16} color={theme.warning} style={{ marginRight: 6 }} />
              <Text style={[styles.suggestionTitle, { color: theme.warning }]}>
                Acción Sugerida
              </Text>
            </View>
            <Text style={[styles.suggestionContent, { color: theme.text }]}>
              {item.payload.action_suggestion}
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
  },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  typeBadgeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.03)',
  },
  badgeIconBg: {
    width: 18,
    height: 18,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 6,
  },
  typeBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  scrollContent: {
    padding: spacing.lg,
    paddingBottom: 80,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaText: {
    fontSize: 13,
    fontWeight: '500',
  },
  workspaceDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    marginBottom: spacing.lg,
    lineHeight: 36,
    letterSpacing: -0.5,
  },
  markdownContainer: {
    marginVertical: spacing.xs,
  },
  suggestionBox: {
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    padding: spacing.md,
    marginTop: spacing.xl,
  },
  suggestionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  suggestionTitle: {
    fontSize: 13,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  suggestionContent: {
    fontSize: 14,
    lineHeight: 22,
  },
});
