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
import { 
  LogOut, 
  Plus, 
  Search, 
  FileText, 
  Calendar, 
  ChevronRight, 
  Layout, 
  Filter, 
  Tag, 
  Sun, 
  Moon, 
  X, 
  Menu,
  Clock,
  Inbox
} from 'lucide-react-native';
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
  const [showAppMenu, setShowAppMenu] = useState(false);

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

  const renderNoteItem = ({ item, index }: { item: Note, index: number }) => (
    <TouchableOpacity
      style={[
        styles.noteCard, 
        { 
          backgroundColor: theme.surface, 
          borderColor: theme.border,
          shadowColor: '#000',
        }
      ]}
      onPress={() => navigation.navigate('NoteDetail', { noteId: item.id })}
      activeOpacity={0.8}
    >
      <View style={styles.noteHeader}>
        <View style={styles.titleContainer}>
          <View style={[styles.iconCircle, { backgroundColor: (item.workspace_color || theme.primary) + '15', borderColor: (item.workspace_color || theme.primary) + '30', borderWidth: 1 }]}>
            <FileText size={14} color={item.workspace_color || theme.primary} />
          </View>
          <Text style={[styles.noteTitle, { color: theme.text }]} numberOfLines={1}>{item.title || 'Sin título'}</Text>
        </View>
        <ChevronRight size={16} color={theme.textMuted} />
      </View>

      <Text style={[styles.noteExcerpt, { color: theme.textMuted }]} numberOfLines={2}>
        {item.content ? item.content.replace(/[#*`\n]/g, ' ').trim() : 'Sin contenido adicional'}
      </Text>

      <View style={[styles.noteFooter, { borderTopColor: theme.border + '50' }]}>
        <View style={styles.metaRow}>
          <View style={styles.metaItem}>
            <Calendar size={12} color={theme.textMuted} />
            <Text style={[styles.metaText, { color: theme.textMuted }]}>
              {item.created_at ? format(new Date(item.created_at), 'dd MMM', { locale: es }) : ''}
            </Text>
          </View>
          {item.category && (
             <View style={[styles.metaItem, { marginLeft: spacing.sm }]}>
                <Tag size={12} color={theme.textMuted} />
                <Text style={[styles.metaText, { color: theme.textMuted }]}>{item.category}</Text>
             </View>
          )}
        </View>

        {item.workspace_name && (
          <View style={[styles.workspaceBadge, { backgroundColor: (item.workspace_color || theme.primary) + '15' }]}>
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
        colors={[theme.primary + '20', theme.background]}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.5, y: 0.3 }}
        style={styles.gradientHeader}
      />

      <View style={styles.header}>
        <View>
          <Text style={[styles.welcomeText, { color: theme.text }]}>Mis Notas</Text>
          <View style={styles.countRow}>
             <Clock size={12} color={theme.primary} />
             <Text style={[styles.countText, { color: theme.textMuted }]}>
               {isFiltered ? `${notes.length} resultados` : `${notes.length} notas en total`}
             </Text>
          </View>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={toggleTheme} style={[styles.actionButton, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            {isDarkMode ? <Sun size={18} color={theme.text} /> : <Moon size={18} color={theme.text} />}
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setShowAppMenu(!showAppMenu)} style={[styles.actionButton, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <Menu size={18} color={theme.text} />
          </TouchableOpacity>
          <TouchableOpacity onPress={signOut} style={[styles.actionButton, { backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.2)' }]}>
            <LogOut size={18} color={colors.error} />
          </TouchableOpacity>
        </View>
      </View>

      {/* App Menu Dropdown */}
      {showAppMenu && (
          <View style={[styles.dropdownMenu, { backgroundColor: theme.surface, borderColor: theme.border }]}> 
             <TouchableOpacity onPress={() => { setShowAppMenu(false); navigation.navigate('Chat'); }} style={styles.dropdownItem}>
                <View style={styles.dropdownIconText}>
                   <Layout size={16} color={theme.primary} style={{ marginRight: 10 }} />
                   <Text style={[styles.dropdownText, { color: theme.text }]}>Chat IA</Text>
                </View>
             </TouchableOpacity>
             <TouchableOpacity onPress={() => { setShowAppMenu(false); navigation.navigate('Calendar'); }} style={styles.dropdownItem}>
                <View style={styles.dropdownIconText}>
                   <Calendar size={16} color={theme.primary} style={{ marginRight: 10 }} />
                   <Text style={[styles.dropdownText, { color: theme.text }]}>Calendario</Text>
                </View>
             </TouchableOpacity>
             <TouchableOpacity onPress={() => { setShowAppMenu(false); navigation.navigate('Inbox'); }} style={[styles.dropdownItem, { borderBottomWidth: 0 }]}>
                <View style={styles.dropdownIconText}>
                   <Inbox size={16} color={theme.primary} style={{ marginRight: 10 }} />
                   <Text style={[styles.dropdownText, { color: theme.text }]}>Bandeja</Text>
                </View>
             </TouchableOpacity>
          </View>
      )}

      <View style={styles.searchRow}>
        <View style={[styles.searchContainer, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Search size={18} color={theme.textMuted} style={styles.searchIcon} />
          <TextInput
            style={[styles.searchInput, { color: theme.text }]}
            placeholder="Buscar en tus notas..."
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
            isFiltered && { backgroundColor: theme.primary + '15', borderColor: theme.primary + '50' }
          ]}
        >
          <Filter size={20} color={isFiltered ? theme.primary : theme.textMuted} />
          {isFiltered && <View style={styles.filterDot} />}
        </TouchableOpacity>
      </View>

      {showFilters && (
        <View style={[styles.filtersPanel, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.filtersHeader}>
            <Text style={[styles.filtersTitle, { color: theme.text }]}>Filtros</Text>
            {isFiltered && (
              <TouchableOpacity onPress={clearFilters}>
                <Text style={[styles.clearText, { color: theme.primary }]}>Limpiar</Text>
              </TouchableOpacity>
            )}
          </View>

          <View style={styles.filtersWrapper}>
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
          showsVerticalScrollIndicator={false}
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
              <View style={[styles.emptyIconCircle, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                 <FileText size={32} color={theme.textMuted} />
              </View>
              <Text style={[styles.emptyText, { color: theme.textMuted }]}>No se encontraron notas</Text>
              <Text style={[styles.emptySubText, { color: theme.textMuted + '80' }]}>Intenta con otros términos de búsqueda o filtros.</Text>
            </View>
          }
        />
      )}

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('CreateNote')}
      >
        <LinearGradient
          colors={[colors.primaryLight, colors.primary]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.fabGradient}
        >
          <Plus size={28} color="#fff" />
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
    height: 300,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Platform.OS === 'ios' ? 60 : 50,
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.lg,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionButton: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: spacing.sm,
    borderWidth: 1,
  },
  welcomeText: {
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: -0.8,
  },
  countRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  countText: {
    fontSize: 13,
    marginLeft: 6,
    fontWeight: '500',
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
    borderRadius: 16,
    height: 50,
    borderWidth: 1,
  },
  searchIcon: {
    marginRight: spacing.sm,
    opacity: 0.6,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    fontWeight: '500',
  },
  filterButton: {
    width: 50,
    height: 50,
    borderRadius: 16,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: spacing.sm,
    position: 'relative',
  },
  filterDot: {
    position: 'absolute',
    top: 10,
    right: 10,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.primary,
    borderWidth: 1.5,
    borderColor: '#fff',
  },
  filtersPanel: {
    marginHorizontal: spacing.lg,
    borderRadius: 20,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.1,
        shadowRadius: 12,
      },
      android: {
        elevation: 4,
      }
    })
  },
  filtersHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  filtersTitle: {
    fontSize: 15,
    fontWeight: '700',
  },
  clearText: {
    fontSize: 12,
    fontWeight: '600',
  },
  filtersWrapper: {
    marginBottom: spacing.xs,
  },
  filtersContainer: {
    paddingBottom: spacing.xs,
  },
  filterChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: 12,
    marginRight: spacing.sm,
    borderWidth: 1,
    minWidth: 70,
    alignItems: 'center',
  },
  filterText: {
    fontSize: 12,
    fontWeight: '600',
  },
  listContent: {
    padding: spacing.lg,
    paddingTop: spacing.xs,
    paddingBottom: 120,
  },
  noteCard: {
    borderRadius: 20,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    ...Platform.select({
      ios: {
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.05,
        shadowRadius: 10,
      },
      android: {
        elevation: 2,
      }
    })
  },
  noteHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  iconCircle: {
    width: 28,
    height: 28,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  noteTitle: {
    fontSize: 17,
    fontWeight: '700',
    flex: 1,
    letterSpacing: -0.4,
  },
  noteExcerpt: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
    opacity: 0.8,
  },
  noteFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    paddingTop: 12,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metaText: {
    fontSize: 11,
    marginLeft: 4,
    fontWeight: '600',
  },
  workspaceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  workspaceBadgeText: {
    fontSize: 9,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
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
    marginTop: 60,
  },
  emptyIconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  emptySubText: {
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 40,
  },
  fab: {
    position: 'absolute',
    bottom: 80,
    right: 25,
    width: 60,
    height: 60,
    borderRadius: 30,
    ...Platform.select({
      ios: {
        shadowColor: colors.primary,
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.3,
        shadowRadius: 12,
      },
      android: {
        elevation: 6,
      }
    })
  },
  fabGradient: {
    flex: 1,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    transform: [{ rotate: '0deg' }], // Can add dynamic rotation if needed
  },
  dropdownMenu: {
      position: 'absolute',
      top: Platform.OS === 'ios' ? 105 : 95,
      right: spacing.lg,
      borderWidth: 1,
      borderRadius: 16,
      zIndex: 1000,
      padding: 6,
      minWidth: 160,
      ...Platform.select({
        ios: {
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 8 },
          shadowOpacity: 0.15,
          shadowRadius: 15,
        },
        android: {
          elevation: 8,
        }
      })
  },
  dropdownItem: {
      paddingVertical: 12,
      paddingHorizontal: 12,
      borderBottomWidth: 1,
      borderBottomColor: 'rgba(0,0,0,0.05)',
  },
  dropdownIconText: {
     flexDirection: 'row',
     alignItems: 'center',
  },
  dropdownText: {
      fontSize: 15,
      fontWeight: '600',
  }
});

