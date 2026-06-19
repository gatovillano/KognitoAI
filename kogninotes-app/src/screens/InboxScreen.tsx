// src/screens/InboxScreen.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../context/AuthContext';
import { inboxService, InboxItem } from '../api/inboxService';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import {
  Inbox,
  Trash2,
  Lightbulb,
  Bot,
  ChevronLeft,
  RotateCw,
  Calendar as CalendarIcon,
} from 'lucide-react-native';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

export const InboxScreen = ({ navigation }: any) => {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'messages' | 'insights'>('all');

  const { isDarkMode } = useAuth();
  const theme = isDarkMode ? colors : lightColors;

  const loadInbox = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const data = await inboxService.fetchInbox();
      setItems(data);
    } catch (error) {
      console.error('Error loading inbox:', error);
      Alert.alert('Error', 'No se pudo cargar la bandeja de entrada.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadInbox();
  }, [loadInbox]);

  const onRefresh = () => {
    setRefreshing(true);
    loadInbox(true);
  };

  const handleDelete = (item: InboxItem) => {
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
              setItems((prev) => prev.filter((i) => i.id !== item.id));
            } catch (error) {
              console.error('Error deleting item:', error);
              Alert.alert('Error', 'No se pudo eliminar el elemento.');
            }
          },
        },
      ]
    );
  };

  const handleItemPress = (item: InboxItem) => {
    navigation.navigate('InboxDetail', {
      item,
      onDelete: (deletedId: string) => {
        setItems((prev) => prev.filter((i) => i.id !== deletedId));
      },
    });
  };

  const filteredItems = useMemo(() => {
    if (activeTab === 'messages') {
      return items.filter((i) => i.kind === 'agent_message');
    }
    if (activeTab === 'insights') {
      return items.filter((i) => i.kind === 'insight');
    }
    return items;
  }, [items, activeTab]);

  const formatItemDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'dd MMM yyyy, HH:mm', { locale: es });
    } catch (e) {
      return dateString;
    }
  };

  const renderInboxCard = ({ item }: { item: InboxItem }) => {
    const isInsight = item.kind === 'insight';
    const accentColor = isInsight ? theme.warning : theme.primary;
    const itemDate = formatItemDate(item.created_at);

    return (
      <TouchableOpacity
        style={[
          styles.card,
          {
            backgroundColor: theme.surface,
            borderColor: theme.border,
            shadowColor: isDarkMode ? '#000' : '#d1d5db',
          },
        ]}
        onPress={() => handleItemPress(item)}
        activeOpacity={0.7}
      >
        <View style={styles.cardHeader}>
          <View style={styles.badgeContainer}>
            <View
              style={[
                styles.iconCircle,
                {
                  backgroundColor: accentColor + '15',
                  borderColor: accentColor + '30',
                },
              ]}
            >
              {isInsight ? (
                <Lightbulb size={14} color={accentColor} />
              ) : (
                <Bot size={14} color={accentColor} />
              )}
            </View>
            <Text
              style={[
                styles.badgeText,
                {
                  color: isInsight ? theme.warning : theme.primary,
                  backgroundColor: isInsight ? 'rgba(245, 158, 11, 0.08)' : 'rgba(0, 191, 255, 0.08)',
                  borderColor: isInsight ? 'rgba(245, 158, 11, 0.15)' : 'rgba(0, 191, 255, 0.15)',
                },
              ]}
            >
              {isInsight ? 'Insight' : 'Mensaje del Agente'}
            </Text>
          </View>
          <TouchableOpacity onPress={() => handleDelete(item)} style={styles.deleteButton}>
            <Trash2 size={16} color={theme.error} />
          </TouchableOpacity>
        </View>

        <Text style={[styles.cardTitle, { color: theme.text }]} numberOfLines={1}>
          {item.title}
        </Text>

        <Text style={[styles.cardExcerpt, { color: theme.textMuted }]} numberOfLines={2}>
          {item.preview ? item.preview.replace(/[#*`\n]/g, ' ').trim() : ''}
        </Text>

        <View style={[styles.cardFooter, { borderTopColor: theme.border + '30' }]}>
          <View style={styles.metaRow}>
            <CalendarIcon size={12} color={theme.textMuted} style={{ marginRight: 4 }} />
            <Text style={[styles.metaText, { color: theme.textMuted }]}>{itemDate}</Text>
          </View>
          {item.payload.workspace_name && (
            <View
              style={[
                styles.workspaceBadge,
                {
                  backgroundColor: (item.payload.workspace_color || theme.primary) + '15',
                  borderColor: (item.payload.workspace_color || theme.primary) + '30',
                },
              ]}
            >
              <View
                style={[
                  styles.workspaceColorDot,
                  { backgroundColor: item.payload.workspace_color || theme.primary },
                ]}
              />
              <Text
                style={[
                  styles.workspaceBadgeText,
                  { color: item.payload.workspace_color || theme.primary },
                ]}
                numberOfLines={1}
              >
                {item.payload.workspace_name}
              </Text>
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  const emptyState = () => (
    <View style={styles.emptyContainer}>
      <Inbox size={48} color={theme.textMuted} style={{ opacity: 0.5, marginBottom: spacing.md }} />
      <Text style={[styles.emptyTitle, { color: theme.text }]}>Bandeja vacía</Text>
      <Text style={[styles.emptySubtitle, { color: theme.textMuted }]}>
        Aquí verás los mensajes del agente y los insights proactivos generados a partir de tus notas.
      </Text>
      <TouchableOpacity
        onPress={() => loadInbox(false)}
        style={[styles.refreshButton, { backgroundColor: theme.primary }]}
      >
        <RotateCw size={14} color="#fff" style={{ marginRight: 8 }} />
        <Text style={styles.refreshBtnText}>Actualizar</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]} edges={['top']}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border + '30' }]}>
        <View style={styles.headerLeft}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
            <ChevronLeft size={24} color={theme.text} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: theme.text }]}>Bandeja</Text>
        </View>
        <TouchableOpacity
          onPress={() => loadInbox(true)}
          style={[styles.actionButton, { backgroundColor: theme.surface, borderColor: theme.border }]}
        >
          {loading ? (
            <ActivityIndicator size="small" color={theme.primary} />
          ) : (
            <RotateCw size={18} color={theme.text} />
          )}
        </TouchableOpacity>
      </View>

      {/* Tabs */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[
            styles.tab,
            activeTab === 'all' && {
              borderBottomColor: theme.primary,
              borderBottomWidth: 2,
            },
          ]}
          onPress={() => setActiveTab('all')}
        >
          <Text
            style={[
              styles.tabText,
              { color: activeTab === 'all' ? theme.text : theme.textMuted },
              activeTab === 'all' && { fontWeight: '700' },
            ]}
          >
            Todos
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.tab,
            activeTab === 'messages' && {
              borderBottomColor: theme.primary,
              borderBottomWidth: 2,
            },
          ]}
          onPress={() => setActiveTab('messages')}
        >
          <Text
            style={[
              styles.tabText,
              { color: activeTab === 'messages' ? theme.text : theme.textMuted },
              activeTab === 'messages' && { fontWeight: '700' },
            ]}
          >
            Mensajes
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.tab,
            activeTab === 'insights' && {
              borderBottomColor: theme.primary,
              borderBottomWidth: 2,
            },
          ]}
          onPress={() => setActiveTab('insights')}
        >
          <Text
            style={[
              styles.tabText,
              { color: activeTab === 'insights' ? theme.text : theme.textMuted },
              activeTab === 'insights' && { fontWeight: '700' },
            ]}
          >
            Insights
          </Text>
        </TouchableOpacity>
      </View>

      {/* Content */}
      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
      ) : (
        <FlatList
          data={filteredItems}
          keyExtractor={(item) => item.id}
          renderItem={renderInboxCard}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={emptyState}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={theme.primary}
              colors={[theme.primary]}
            />
          }
        />
      )}
    </SafeAreaView>
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
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  backButton: {
    padding: spacing.xs,
    marginRight: spacing.xs,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '800',
  },
  actionButton: {
    padding: spacing.sm,
    borderRadius: borderRadius.md,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    marginVertical: spacing.xs,
  },
  tab: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginRight: spacing.sm,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '500',
  },
  centerContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listContent: {
    padding: spacing.md,
    paddingBottom: spacing.xl,
  },
  card: {
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    padding: spacing.md,
    marginBottom: spacing.md,
    elevation: 2,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  badgeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconCircle: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.sm,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: borderRadius.full,
    borderWidth: 1,
    overflow: 'hidden',
  },
  deleteButton: {
    padding: spacing.xs,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: spacing.xs,
  },
  cardExcerpt: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: spacing.md,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    paddingTop: spacing.sm,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metaText: {
    fontSize: 11,
  },
  workspaceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: borderRadius.full,
    borderWidth: 1,
  },
  workspaceColorDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 5,
  },
  workspaceBadgeText: {
    fontSize: 10,
    fontWeight: '600',
    maxWidth: 100,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl * 2,
    paddingHorizontal: spacing.xl,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: spacing.xs,
  },
  emptySubtitle: {
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: spacing.lg,
  },
  refreshButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.md,
  },
  refreshBtnText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 13,
  },
});
