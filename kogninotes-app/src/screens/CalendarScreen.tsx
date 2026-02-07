// src/screens/CalendarScreen.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    View,
    Text,
    StyleSheet,
    FlatList,
    TouchableOpacity,
    RefreshControl,
    ActivityIndicator,
    Platform,
    LayoutAnimation,
    UIManager,
    SectionList
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { agendaService, AgendaEvent } from '../api/agendaService';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import { ChevronLeft, Calendar as CalendarIcon, MapPin, Clock, Info, User, Layout, Filter, Sun, Moon } from 'lucide-react-native';
import { format, isToday, isTomorrow, parseISO, startOfDay, addDays } from 'date-fns';
import { es } from 'date-fns/locale';
import { LinearGradient } from 'expo-linear-gradient';

// Habilitar animaciones en Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
    UIManager.setLayoutAnimationEnabledExperimental(true);
}

export const CalendarScreen = ({ navigation }: any) => {
    const [events, setEvents] = useState<AgendaEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const { isDarkMode, toggleTheme } = useAuth();
    const theme = isDarkMode ? colors : lightColors;

    const loadEvents = useCallback(async () => {
        setLoading(true);
        try {
            const data = await agendaService.listEvents(true); // Incluir pasados para que la agenda se vea llena
            setEvents(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error('Error loading agenda:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadEvents();
    }, [loadEvents]);

    const onRefresh = () => {
        setRefreshing(true);
        loadEvents();
    };

    // Agrupar eventos por fecha
    const sections = useMemo(() => {
        const grouped: { [key: string]: AgendaEvent[] } = {};

        events.forEach(event => {
            try {
                if (!event.event_datetime_local) return;
                const date = format(parseISO(event.event_datetime_local), 'yyyy-MM-dd');
                if (!grouped[date]) {
                    grouped[date] = [];
                }
                grouped[date].push(event);
            } catch (e) {
                console.warn('Error parsing event date:', event.event_datetime_local);
            }
        });

        // Ordenar fechas y eventos
        return Object.keys(grouped)
            .sort()
            .map(date => ({
                title: date,
                data: grouped[date].sort((a, b) =>
                    new Date(a.event_datetime_local).getTime() - new Date(b.event_datetime_local).getTime()
                )
            }));
    }, [events]);

    const renderEventItem = ({ item }: { item: AgendaEvent }) => {
        let timeStr = '--:--';
        try {
            if (item.event_datetime_local) {
                const eventDate = parseISO(item.event_datetime_local);
                timeStr = format(eventDate, 'HH:mm');
            }
        } catch (e) {
            console.warn('Error formatting time for event:', item.id);
        }

        return (
            <TouchableOpacity
                style={[styles.eventCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
                activeOpacity={0.7}
            >
                <View style={styles.eventTimeContainer}>
                    <Text style={[styles.eventTime, { color: theme.primary }]}>{timeStr}</Text>
                    <View style={[styles.timeLine, { backgroundColor: item.workspace_color || theme.primary }]} />
                </View>

                <View style={styles.eventContent}>
                    <Text style={[styles.eventSummary, { color: theme.text }]} numberOfLines={1}>
                        {item.summary}
                    </Text>

                    {item.location && (
                        <View style={styles.detailRow}>
                            <MapPin size={12} color={theme.textMuted} />
                            <Text style={[styles.detailText, { color: theme.textMuted }]} numberOfLines={1}>
                                {item.location}
                            </Text>
                        </View>
                    )}

                    {item.workspace_name && (
                        <View style={[styles.workspaceBadge, { backgroundColor: (item.workspace_color || theme.primary) + '20' }]}>
                            <Text style={[styles.workspaceBadgeText, { color: item.workspace_color || theme.primary }]}>
                                {item.workspace_name}
                            </Text>
                        </View>
                    )}
                </View>

                <ChevronLeft size={18} color={theme.textMuted} style={{ transform: [{ rotate: '180deg' }] }} />
            </TouchableOpacity>
        );
    };

    const renderSectionHeader = ({ section: { title } }: any) => {
        const date = parseISO(title);
        let dateStr = format(date, "EEEE, d 'de' MMMM", { locale: es });

        if (isToday(date)) dateStr = 'Hoy';
        else if (isTomorrow(date)) dateStr = 'Mañana';

        return (
            <View style={[styles.sectionHeader, { backgroundColor: theme.background }]}>
                <Text style={[styles.sectionHeaderText, { color: theme.textMuted }]}>
                    {dateStr.charAt(0).toUpperCase() + dateStr.slice(1)}
                </Text>
            </View>
        );
    };

    return (
        <View style={[styles.container, { backgroundColor: theme.background }]}>
            <LinearGradient
                colors={[theme.primary, theme.background]}
                start={{ x: 0, y: 0 }}
                end={{ x: 0, y: 0.15 }}
                style={styles.gradientHeader}
            />

            <View style={styles.header}>
                <TouchableOpacity
                    onPress={() => navigation.goBack()}
                    style={[styles.backButton, { backgroundColor: 'rgba(255, 255, 255, 0.1)' }]}
                >
                    <ChevronLeft size={24} color={theme.text} />
                </TouchableOpacity>

                <View style={styles.headerTitleContainer}>
                    <Text style={[styles.title, { color: theme.text }]}>Agenda</Text>
                    <Text style={[styles.subtitle, { color: theme.textMuted }]}>Kognito AI</Text>
                </View>

                <TouchableOpacity onPress={toggleTheme} style={styles.actionButton}>
                    {isDarkMode ? <Sun size={20} color={theme.text} /> : <Moon size={20} color={theme.text} />}
                </TouchableOpacity>
            </View>

            {loading && !refreshing ? (
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color={theme.primary} />
                    <Text style={[styles.loadingText, { color: theme.textMuted }]}>Sincronizando agenda...</Text>
                </View>
            ) : (
                <SectionList
                    sections={sections}
                    keyExtractor={(item) => item.id.toString()}
                    renderItem={renderEventItem}
                    renderSectionHeader={renderSectionHeader}
                    contentContainerStyle={styles.listContent}
                    stickySectionHeadersEnabled={true}
                    refreshControl={
                        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
                    }
                    ListEmptyComponent={
                        <View style={styles.emptyContainer}>
                            <CalendarIcon size={64} color={theme.textMuted} />
                            <Text style={[styles.emptyText, { color: theme.textMuted }]}>No hay eventos programados</Text>
                            <Text style={[styles.emptySubtext, { color: theme.textMuted }]}>Tus eventos de Kognito AI aparecerán aquí</Text>
                        </View>
                    }
                />
            )}
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
        height: 180,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: Platform.OS === 'ios' ? 60 : 40,
        paddingHorizontal: spacing.lg,
        paddingBottom: spacing.md,
    },
    backButton: {
        width: 44,
        height: 44,
        borderRadius: borderRadius.lg,
        justifyContent: 'center',
        alignItems: 'center',
    },
    headerTitleContainer: {
        flex: 1,
        marginLeft: spacing.md,
    },
    title: {
        fontSize: 24,
        fontWeight: '900',
        letterSpacing: -0.5,
    },
    subtitle: {
        fontSize: 14,
        fontWeight: '600',
        marginTop: -2,
    },
    actionButton: {
        padding: spacing.sm,
        borderRadius: borderRadius.md,
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        marginTop: spacing.md,
        fontSize: 14,
        fontWeight: '600',
    },
    listContent: {
        paddingHorizontal: spacing.lg,
        paddingBottom: 40,
    },
    sectionHeader: {
        paddingVertical: spacing.md,
        paddingTop: spacing.lg,
    },
    sectionHeaderText: {
        fontSize: 12,
        fontWeight: '900',
        textTransform: 'uppercase',
        letterSpacing: 1.5,
    },
    eventCard: {
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: borderRadius.xl,
        padding: spacing.md,
        marginBottom: spacing.sm,
        borderWidth: 1,
        elevation: 2,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
    },
    eventTimeContainer: {
        alignItems: 'center',
        width: 55,
        marginRight: spacing.sm,
    },
    eventTime: {
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 4,
    },
    timeLine: {
        width: 3,
        height: 20,
        borderRadius: 1.5,
    },
    eventContent: {
        flex: 1,
    },
    eventSummary: {
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 4,
        letterSpacing: -0.2,
    },
    detailRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 4,
    },
    detailText: {
        fontSize: 12,
        marginLeft: 4,
        fontWeight: '500',
    },
    workspaceBadge: {
        alignSelf: 'flex-start',
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 6,
        marginTop: 2,
    },
    workspaceBadgeText: {
        fontSize: 10,
        fontWeight: '900',
        textTransform: 'uppercase',
    },
    emptyContainer: {
        marginTop: 100,
        alignItems: 'center',
        justifyContent: 'center',
    },
    emptyText: {
        marginTop: spacing.lg,
        fontSize: 18,
        fontWeight: 'bold',
    },
    emptySubtext: {
        marginTop: spacing.xs,
        fontSize: 14,
        textAlign: 'center',
        paddingHorizontal: spacing.xl,
    },
});
