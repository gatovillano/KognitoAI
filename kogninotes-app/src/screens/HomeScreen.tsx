// src/screens/HomeScreen.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  TextInput,
  ScrollView,
  LayoutAnimation,
  Platform,
  UIManager
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { notesService, Note } from '../api/notesService';
import { workspaceService, Workspace } from '../api/workspaceService';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import { LogOut, Plus, Search, FileText, Calendar, ChevronRight, Layout, Filter, Tag, Sun, Moon, X } from 'lucide-react-native';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { LinearGradient } from 'expo-linear-gradient';

// Habilitar animaciones en Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const PAGE_SIZE = 20;

export const HomeScreen = ({ navigation }: any) => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  // Estado para mostrar/ocultar filtros
  const [showFilters, setShowFilters] = useState(false);

  // Filtros
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const { signOut, isDarkMode, toggleTheme } = useAuth();
  const theme = isDarkMode ? colors : lightColors;

  const isFiltered = !!selectedWorkspaceId || !!selectedCategory;

  // Cargar Workspaces
  useEffect(() => {
    const loadWorkspaces = async () => {
      try {
        const data = await workspaceService.listWorkspaces();
        setWorkspaces(Array.isArray(data?.workspaces) ? data.workspaces : []);
      } catch (error) {
        console.error('Error loading workspaces:', error);
      }
    };
    loadWorkspaces();
  }, []);

  const loadNotes = useCallback(async (isInitial = false, currentSkip = 0) => {
    if (isInitial) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }

    try {
      const data = await notesService.listNotes(
        searchTerm,
        selectedWorkspaceId,
        selectedCategory,
        currentSkip,
        PAGE_SIZE
      );

      const newNotes = Array.isArray(data?.notes) ? data.notes : [];

      if (isInitial) {
        setNotes(newNotes);
      } else {
        setNotes(prev => [...prev, ...newNotes]);
      }

      setHasMore(newNotes.length === PAGE_SIZE);
      setSkip(currentSkip + newNotes.length);
    } catch (error) {
      console.error('Error loading notes:', error);
      if (isInitial) setNotes([]);
    } finally {
      setLoading(false);
      setLoadingMore(false);
      setRefreshing(false);
    }
  }, [searchTerm, selectedWorkspaceId, selectedCategory]);

  useEffect(() => {
    setSkip(0);
    setHasMore(true);
    loadNotes(true, 0);
  }, [searchTerm, selectedWorkspaceId, selectedCategory]);

  const onRefresh = () => {
    setRefreshing(true);
    setSkip(0);
    setHasMore(true);
    loadNotes(true, 0);
  };

  const handleLoadMore = () => {
    if (!loadingMore && hasMore && !loading) {
      loadNotes(false, skip);
    }
  };

  const toggleFilters = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setShowFilters(!showFilters);
  };

  const clearFilters = () => {
    setSelectedWorkspaceId(null);
    setSelectedCategory(null);
  };

  // Extraer categorías únicas
  const categories = useMemo(() => {
    const cats = (Array.isArray(notes) ? notes : [])
      .map(n => n.category)
      .filter((c): c is string => !!c);
    return Array.from(new Set(cats));
  }, [notes]);

  const renderNoteItem = ({ item }: { item: Note }) => (
    <TouchableOpacity
      style={[styles.noteCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
      onPress={() => navigation.navigate('NoteDetail', { noteId: item.id })}
      activeOpacity={0.7}
    >
      <View style={styles.noteHeader}>
        <View style={styles.titleContainer}>
          <View style={[styles.iconCircle, { backgroundColor: (item.workspace_color || theme.primary) + '20' }]}>
            <FileText size={16} color={item.workspace_color || theme.primary} />
          </View>
          <Text style={[styles.noteTitle, { color: theme.text }]} numberOfLines={1}>{item.title || 'Sin título'}</Text>
        </View>
        <ChevronRight size={18} color={theme.textMuted} />
      </View>

      <Text style={[styles.noteExcerpt, { color: theme.textMuted }]} numberOfLines={2}>
        {item.content ? item.content.replace(/[#*`]/g, '') : ''}
      </Text>

      <View style={[styles.noteFooter, { borderTopColor: theme.border }]}>
        <View style={styles.metaItem}>
          <Calendar size={12} color={theme.textMuted} />
          <Text style={[styles.metaText, { color: theme.textMuted }]}>
            {item.created_at ? format(new Date(item.created_at), 'dd MMM yyyy', { locale: es }) : ''}
          </Text>
        </View>

        {item.workspace_name && (
          <View style={[styles.workspaceBadge, { backgroundColor: (item.workspace_color || theme.primary) + '20' }]}>
            <Text style={[styles.workspaceBadgeText, { color: item.workspace_color || theme.primary }]}>
              {item.workspace_name}
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <LinearGradient
        colors={[theme.primary, theme.background]}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 0.2 }}
        style={styles.gradientHeader}
      />

      <View style={styles.header}>
        <View>
          <Text style={[styles.welcomeText, { color: theme.text }]}>Mis Notas</Text>
          <Text style={[styles.countText, { color: theme.textMuted }]}>
            {isFiltered ? `Filtradas: ${notes.length}` : `Total: ${notes.length}`}
          </Text>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={toggleTheme} style={styles.actionButton}>
            {isDarkMode ? <Sun size={20} color={theme.text} /> : <Moon size={20} color={theme.text} />}
          </TouchableOpacity>
          <TouchableOpacity onPress={signOut} style={[styles.actionButton, { backgroundColor: 'rgba(239, 68, 68, 0.1)' }]}>
            <LogOut size={20} color={colors.error} />
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.searchRow}>
        <View style={[styles.searchContainer, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Search size={20} color={theme.textMuted} style={styles.searchIcon} />
          <TextInput
            style={[styles.searchInput, { color: theme.text }]}
            placeholder="Buscar..."
            placeholderTextColor={theme.textMuted}
            value={searchTerm}
            onChangeText={setSearchTerm}
          />
        </View>
        <TouchableOpacity
          onPress={toggleFilters}
          style={[
            styles.filterButton,
            { backgroundColor: theme.surface, borderColor: theme.border },
            isFiltered && { backgroundColor: theme.primary + '20', borderColor: theme.primary }
          ]}
        >
          <Filter size={22} color={isFiltered ? theme.primary : theme.textMuted} />
          {isFiltered && <View style={styles.filterDot} />}
        </TouchableOpacity>
      </View>

      {showFilters && (
        <View style={[styles.filtersPanel, { backgroundColor: theme.surface + '80', borderColor: theme.border }]}>
          <View style={styles.filtersHeader}>
            <Text style={[styles.filtersTitle, { color: theme.text }]}>Filtros Avanzados</Text>
            {isFiltered && (
              <TouchableOpacity onPress={clearFilters}>
                <Text style={[styles.clearText, { color: theme.primary }]}>Limpiar todo</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Línea 1: Filtros de Workspace */}
          <View style={styles.filtersWrapper}>
            <View style={styles.filterLabelRow}>
              <Layout size={14} color={theme.textMuted} />
              <Text style={[styles.filterLabel, { color: theme.textMuted }]}>Espacios</Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filtersContainer}>
              <TouchableOpacity
                style={[styles.filterChip, { backgroundColor: theme.surface, borderColor: theme.border }, !selectedWorkspaceId && { backgroundColor: theme.primary, borderColor: theme.primary }]}
                onPress={() => setSelectedWorkspaceId(null)}
              >
                <Text style={[styles.filterText, { color: theme.textMuted }, !selectedWorkspaceId && { color: '#fff' }]}>Todos</Text>
              </TouchableOpacity>
              {(Array.isArray(workspaces) ? workspaces : []).map(ws => (
                <TouchableOpacity
                  key={ws.id}
                  style={[
                    styles.filterChip,
                    { backgroundColor: theme.surface, borderColor: theme.border },
                    selectedWorkspaceId === String(ws.id) && { backgroundColor: ws.color || theme.primary, borderColor: ws.color || theme.primary }
                  ]}
                  onPress={() => setSelectedWorkspaceId(selectedWorkspaceId === String(ws.id) ? null : String(ws.id))}
                >
                  <Text style={[styles.filterText, { color: theme.textMuted }, selectedWorkspaceId === String(ws.id) && { color: '#fff' }]}>{ws.name}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          {/* Línea 2: Filtros de Categoría */}
          <View style={styles.filtersWrapper}>
            <View style={styles.filterLabelRow}>
              <Tag size={14} color={theme.textMuted} />
              <Text style={[styles.filterLabel, { color: theme.textMuted }]}>Categorías</Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filtersContainer}>
              <TouchableOpacity
                style={[styles.filterChip, { backgroundColor: theme.surface, borderColor: theme.border }, !selectedCategory && { backgroundColor: theme.primary, borderColor: theme.primary }]}
                onPress={() => setSelectedCategory(null)}
              >
                <Text style={[styles.filterText, { color: theme.textMuted }, !selectedCategory && { color: '#fff' }]}>Todas</Text>
              </TouchableOpacity>
              {(Array.isArray(categories) ? categories : []).map(cat => (
                <TouchableOpacity
                  key={cat}
                  style={[styles.filterChip, { backgroundColor: theme.surface, borderColor: theme.border }, selectedCategory === cat && { backgroundColor: theme.primary, borderColor: theme.primary }]}
                  onPress={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
                >
                  <Text style={[styles.filterText, { color: theme.textMuted }, selectedCategory === cat && { color: '#fff' }]}>{cat}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </View>
      )}

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
      ) : (
        <FlatList
          data={notes}
          renderItem={renderNoteItem}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContent}
          onEndReached={handleLoadMore}
          onEndReachedThreshold={0.5}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
          }
          ListFooterComponent={
            loadingMore ? (
              <View style={styles.footerLoader}>
                <ActivityIndicator size="small" color={theme.primary} />
              </View>
            ) : null
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <FileText size={48} color={theme.textMuted} />
              <Text style={[styles.emptyText, { color: theme.textMuted }]}>No hay notas que coincidan</Text>
            </View>
          }
        />
      )}

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('CreateNote')}
      >
        <LinearGradient
          colors={[theme.primary, theme.primaryLight]}
          style={styles.fabGradient}
        >
          <Plus size={30} color="#fff" />
        </LinearGradient>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  gradientHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 250,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: spacing.xl * 2,
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.lg,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionButton: {
    padding: spacing.sm,
    borderRadius: borderRadius.md,
    marginLeft: spacing.sm,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  welcomeText: {
    fontSize: 32,
    fontWeight: '900',
    letterSpacing: -0.5,
  },
  countText: {
    fontSize: 14,
    marginTop: spacing.xs,
    fontWeight: '600',
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
  },
  searchContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: borderRadius.lg,
    height: 54,
    borderWidth: 1,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  searchIcon: {
    marginRight: spacing.sm,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    fontWeight: '500',
  },
  filterButton: {
    width: 54,
    height: 54,
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: spacing.sm,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    position: 'relative',
  },
  filterDot: {
    position: 'absolute',
    top: 12,
    right: 12,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
    borderWidth: 2,
    borderColor: '#fff',
  },
  filtersPanel: {
    marginHorizontal: spacing.lg,
    borderRadius: borderRadius.xl,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
  },
  filtersHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
    paddingHorizontal: spacing.sm,
  },
  filtersTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  clearText: {
    fontSize: 13,
    fontWeight: '700',
  },
  filtersWrapper: {
    marginBottom: spacing.sm,
  },
  filterLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.sm,
    marginBottom: spacing.xs,
  },
  filterLabel: {
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginLeft: spacing.xs,
  },
  filtersContainer: {
    paddingBottom: spacing.sm,
  },
  filterChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
    borderRadius: borderRadius.full,
    marginRight: spacing.sm,
    borderWidth: 1,
    minWidth: 60,
    alignItems: 'center',
  },
  filterText: {
    fontSize: 12,
    fontWeight: '700',
  },
  listContent: {
    padding: spacing.lg,
    paddingTop: spacing.xs,
    paddingBottom: 100,
  },
  noteCard: {
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
  },
  noteHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  iconCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.sm,
  },
  noteTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    flex: 1,
    letterSpacing: -0.3,
  },
  noteExcerpt: {
    fontSize: 14,
    lineHeight: 22,
    marginBottom: spacing.lg,
    fontWeight: '400',
  },
  noteFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    paddingTop: spacing.md,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metaText: {
    fontSize: 12,
    marginLeft: spacing.xs,
    fontWeight: '600',
  },
  workspaceBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.sm,
  },
  workspaceBadgeText: {
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  footerLoader: {
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.xl * 2,
  },
  emptyText: {
    marginTop: spacing.md,
    fontSize: 16,
    fontWeight: '500',
    textAlign: 'center',
    paddingHorizontal: spacing.xl,
  },
  fab: {
    position: 'absolute',
    bottom: spacing.xl,
    right: spacing.xl,
    width: 64,
    height: 64,
    borderRadius: 32,
    elevation: 10,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.5,
    shadowRadius: 12,
  },
  fabGradient: {
    flex: 1,
    borderRadius: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
