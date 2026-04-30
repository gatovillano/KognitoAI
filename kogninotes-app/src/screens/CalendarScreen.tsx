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
    SectionList,
    Modal,
    ScrollView,
    KeyboardAvoidingView,
    Alert,
    StatusBar
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { agendaService, AgendaEvent, Task } from '../api/agendaService';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import { ChevronLeft, Calendar as CalendarIcon, MapPin, Clock, Info, User, Layout, Filter, Sun, Moon, Plus, CheckCircle2, Circle, X, Menu, FileText, MessageSquare, LogOut } from 'lucide-react-native';
import { format, isToday, isTomorrow, parseISO, startOfDay, addDays, isValid } from 'date-fns';
import { es } from 'date-fns/locale';
import { LinearGradient } from 'expo-linear-gradient';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { workspaceService, Workspace } from '../api/workspaceService';
import { cancelAllNotifications, registerForPushNotificationsAsync, scheduleEventNotification } from '../services/NotificationService';

// Habilitar animaciones en Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
    UIManager.setLayoutAnimationEnabledExperimental(true);
}

type AgendaItem = (AgendaEvent & { type: 'event' }) | (Task & { type: 'task' });

export const CalendarScreen = ({ navigation }: any) => {
    const [events, setEvents] = useState<AgendaEvent[]>([]);
    const [tasks, setTasks] = useState<Task[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const { isDarkMode, toggleTheme, signOut } = useAuth();
    const theme = isDarkMode ? colors : lightColors;

    const [showAppMenu, setShowAppMenu] = useState(false);

    // Modal state
    const [modalVisible, setModalVisible] = useState(false);
    const [createType, setCreateType] = useState<'event' | 'task'>('event');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [editingItem, setEditingItem] = useState<AgendaItem | null>(null);

    // Form state
    const [summary, setSummary] = useState('');
    const [description, setDescription] = useState('');
    const [eventDate, setEventDate] = useState(format(new Date(), 'yyyy-MM-dd'));
    const [eventTime, setEventTime] = useState(format(new Date(), 'HH:mm'));
    const [location, setLocation] = useState('');
    const [selectedWsId, setSelectedWsId] = useState<string | null>(null);
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);

    const scheduleAllNotifications = async (eventsData: AgendaEvent[], tasksData: Task[]) => {
        await cancelAllNotifications();
        const now = new Date();
        
        eventsData.forEach(event => {
            if (event.event_datetime_local) {
                const eventDate = new Date(event.event_datetime_local);
                // Schedule 15 minutes before
                const triggerDate = new Date(eventDate.getTime() - 15 * 60000);
                if (triggerDate > now) {
                    scheduleEventNotification(`Recordatorio: ${event.summary}`, event.location ? `En: ${event.location}` : 'El evento está por comenzar.', triggerDate);
                }
            }
        });

        tasksData.forEach(task => {
            const dateSource = task.start_date;
            if (dateSource) {
                const taskDate = new Date(dateSource);
                const triggerDate = new Date(taskDate.getTime() - 15 * 60000);
                if (triggerDate > now) {
                    scheduleEventNotification('Tarea Pendiente', task.description, triggerDate);
                }
            }
        });
    };

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [eventsData, tasksData] = await Promise.all([
                agendaService.listEvents(true),
                agendaService.listTasks({ is_completed: false })
            ]);
            setEvents(Array.isArray(eventsData) ? eventsData : []);
            setTasks(Array.isArray(tasksData) ? tasksData : []);
            
            // Schedule notifications
            await scheduleAllNotifications(
               Array.isArray(eventsData) ? eventsData : [], 
               Array.isArray(tasksData) ? tasksData : []
            );
            
        } catch (error) {
            console.error('Error loading agenda data:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        registerForPushNotificationsAsync();
        loadData();
        workspaceService.listWorkspaces()
            .then(data => setWorkspaces(data?.workspaces || []))
            .catch(e => console.error('Error loading workspaces:', e));
    }, [loadData]);

    const onRefresh = () => {
        setRefreshing(true);
        loadData();
    };

    const handleCreate = async () => {
        if (createType === 'event') {
            if (!summary.trim()) { Alert.alert('Error', 'El título es obligatorio'); return; }
        } else {
            if (!description.trim()) { Alert.alert('Error', 'La descripción es obligatoria'); return; }
        }

        setIsSubmitting(true);
        try {
            if (editingItem) {
                // UPDATE mode
                if (editingItem.type === 'event') {
                    const updated = await agendaService.updateEvent(editingItem.id as number, {
                        summary,
                        description,
                        location: location || undefined,
                        event_datetime_local: `${eventDate}T${eventTime}:00`,
                        workspace_id: selectedWsId || undefined,
                    });
                    setEvents(prev => prev.map(e => e.id === updated.id ? updated : e));
                } else {
                    const updated = await agendaService.updateTask(editingItem.id as string, {
                        description,
                        start_date: `${eventDate}T${eventTime}:00Z`,
                        workspace_id: selectedWsId || undefined,
                    });
                    setTasks(prev => prev.map(t => t.id === updated.id ? updated : t));
                }
                Alert.alert('Guardado', 'Los cambios fueron guardados correctamente.');
            } else {
                // CREATE mode
                if (createType === 'event') {
                    await agendaService.createEvent({
                        summary, description,
                        event_date: eventDate,
                        event_time: eventTime,
                        location: location || undefined,
                        workspace_id: selectedWsId || undefined,
                    });
                } else {
                    await agendaService.createTask({
                        description,
                        start_date: `${eventDate}T${eventTime}:00Z`,
                        workspace_id: selectedWsId || undefined,
                    });
                }
                Alert.alert('Éxito', `${createType === 'event' ? 'Evento' : 'Tarea'} creado correctamente`);
            }
            setModalVisible(false);
            resetForm();
            loadData();
        } catch (error) {
            console.error('Error saving item:', error);
            Alert.alert('Error', 'No se pudo guardar el elemento. Por favor, intenta de nuevo.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleEdit = (item: AgendaItem) => {
        resetForm();
        if (item.type === 'event') {
            setCreateType('event');
            setSummary(item.summary);
            setDescription(item.description || '');
            setLocation(item.location || '');
            setSelectedWsId(item.workspace_id || null);
            const dt = item.event_datetime_local;
            if (dt) {
                setEventDate(dt.split('T')[0]);
                const match = dt.match(/T(\d{2}:\d{2})/);
                if (match) setEventTime(match[1]);
            }
        } else {
            setCreateType('task');
            setDescription(item.description);
            setSelectedWsId(item.workspace_id || null);
            const ds = item.start_date || item.created_at;
            if (ds) {
                setEventDate(ds.split('T')[0]);
                const match = ds.match(/T(\d{2}:\d{2})/);
                if (match) setEventTime(match[1]);
            }
        }
        setEditingItem(item);
        setModalVisible(true);
    };

    const handleDelete = async () => {
        if (!editingItem) return;
        const label = editingItem.type === 'event' ? 'evento' : 'tarea';
        Alert.alert(
            `Eliminar ${label}`,
            `¿Estás seguro de que deseas eliminar este ${label}?`,
            [
                { text: 'Cancelar', style: 'cancel' },
                {
                    text: 'Eliminar',
                    style: 'destructive',
                    onPress: async () => {
                        setIsSubmitting(true);
                        try {
                            if (editingItem.type === 'event') {
                                await agendaService.cancelEvent(editingItem.id as number);
                                setEvents(prev => prev.filter(e => e.id !== editingItem.id));
                            } else {
                                await agendaService.deleteTask(editingItem.id as string);
                                setTasks(prev => prev.filter(t => t.id !== editingItem.id));
                            }
                            setModalVisible(false);
                            resetForm();
                        } catch (e) {
                            Alert.alert('Error', 'No se pudo eliminar el elemento.');
                        } finally {
                            setIsSubmitting(false);
                        }
                    }
                }
            ]
        );
    };

    const resetForm = () => {
        setSummary('');
        setDescription('');
        setEventDate(format(new Date(), 'yyyy-MM-dd'));
        setEventTime(format(new Date(), 'HH:mm'));
        setLocation('');
        setSelectedWsId(null);
        setEditingItem(null);
    };

    const toggleTaskCompletion = async (task: Task) => {
        try {
            const updatedTask = await agendaService.updateTask(task.id, { is_completed: !task.is_completed });
            setTasks(prev => prev.map(t => t.id === task.id ? updatedTask : t));
        } catch (error) {
            console.error('Error toggling task:', error);
        }
    };

    // Agrupar eventos y tareas por fecha
    const sections = useMemo(() => {
        const grouped: { [key: string]: AgendaItem[] } = {};
        const todayStr = format(new Date(), 'yyyy-MM-dd');

        // Agregar eventos
        events.forEach(event => {
            try {
                if (!event.event_datetime_local) return;
                const datePart = event.event_datetime_local.split('T')[0];
                if (!grouped[datePart]) grouped[datePart] = [];
                grouped[datePart].push({ ...event, type: 'event' });
            } catch (e) {
                console.warn('Error parsing event date:', event.id);
            }
        });

        // Agregar tareas
        tasks.forEach(task => {
            try {
                const dateSource = task.start_date || task.created_at;
                if (!dateSource) return;
                const datePart = dateSource.split('T')[0];
                if (!grouped[datePart]) grouped[datePart] = [];
                grouped[datePart].push({ ...task, type: 'task' });
            } catch (e) {
                console.warn('Error parsing task date:', task.id);
            }
        });

        return Object.keys(grouped)
            .sort((a, b) => {
                if (a === b) return 0;
                
                // Comparación de fechas futuras (incluyendo hoy) vs pasadas
                const isAFuture = a >= todayStr;
                const isBFuture = b >= todayStr;

                if (isAFuture && !isBFuture) return -1;
                if (!isAFuture && isBFuture) return 1;

                if (isAFuture) {
                    // Ambas futuras: ascendente (más cercana primero)
                    return a.localeCompare(b);
                } else {
                    // Ambas pasadas: descendente (más reciente primero)
                    return b.localeCompare(a);
                }
            })
            .map(datePart => ({
                title: datePart,
                data: grouped[datePart].sort((a, b) => {
                    const getTime = (item: AgendaItem) => {
                        if (item.type === 'event') return new Date(item.event_datetime_local).getTime();
                        const d = item.start_date || item.created_at;
                        return d ? new Date(d).getTime() : 0;
                    };
                    return getTime(a) - getTime(b);
                })
            }));

    }, [events, tasks]);

    const renderItem = ({ item }: { item: AgendaItem }) => {
        if (item.type === 'event') {
            return renderEventCard(item);
        } else {
            return renderTaskCard(item);
        }
    };

    const renderEventCard = (item: AgendaEvent) => {
        let timeStr = '--:--';
        try {
            if (item.event_datetime_local) {
                const match = item.event_datetime_local.match(/T(\d{2}:\d{2})/);
                if (match) timeStr = match[1];
            }
        } catch (e) {}

        const accentColor = item.workspace_color || theme.primary;

        return (
            <TouchableOpacity
                style={[styles.itemCard, { backgroundColor: theme.surface, borderColor: theme.border + '40' }]}
                activeOpacity={0.7}
                onPress={() => handleEdit({ ...item, type: 'event' })}
            >
                <View style={styles.timeSection}>
                    <Text style={[styles.timeText, { color: theme.text }]}>{timeStr}</Text>
                    <View style={[styles.typeIndicator, { backgroundColor: accentColor }]} />
                </View>

                <View style={styles.contentContainer}>
                    <Text style={[styles.summaryText, { color: theme.text }]}>
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
                        <View style={[styles.workspaceBadge, { backgroundColor: accentColor + '15' }]}>
                            <Text style={[styles.workspaceBadgeText, { color: accentColor }]}>
                                {item.workspace_name}
                            </Text>
                        </View>
                    )}
                </View>
                <CalendarIcon size={16} color={theme.textMuted} style={{ opacity: 0.5 }} />
            </TouchableOpacity>
        );
    };

    const renderTaskCard = (item: Task) => {
        return (
            <TouchableOpacity
                style={[styles.itemCard, { backgroundColor: theme.surface, borderColor: theme.border + '40' }]}
                activeOpacity={0.7}
                onPress={() => handleEdit({ ...item, type: 'task' })}
                onLongPress={() => toggleTaskCompletion(item)}
            >
                <View style={[styles.checkContainer, { marginRight: spacing.md }]}>
                    {item.is_completed ? (
                       <View style={[styles.checkFilled, { backgroundColor: theme.success }]}>
                          <CheckCircle2 size={16} color="#fff" />
                       </View>
                    ) : (
                        <Circle size={24} color={theme.border} />
                    )}
                </View>

                <View style={styles.contentContainer}>
                    <Text 
                        style={[
                            styles.summaryText, 
                            { color: theme.text, textDecorationLine: item.is_completed ? 'line-through' : 'none', opacity: item.is_completed ? 0.6 : 1 }
                        ]} 
                        numberOfLines={2}
                    >
                        {item.description}
                    </Text>
                    {!item.is_completed && item.start_date && (
                       <View style={styles.detailRow}>
                          <Clock size={11} color={theme.primary} />
                          <Text style={[styles.detailText, { color: theme.primary }]}>
                             {format(new Date(item.start_date), 'HH:mm')}
                          </Text>
                       </View>
                    )}
                </View>
                <Layout size={16} color={theme.textMuted} style={{ opacity: 0.5 }} />
            </TouchableOpacity>
        );
    };

    const renderSectionHeader = ({ section: { title } }: any) => {
        const date = parseISO(title);
        let dateStr = isValid(date) ? format(date, "EEEE, d 'de' MMMM", { locale: es }) : title;

        if (isToday(date)) dateStr = 'Hoy';
        else if (isTomorrow(date)) dateStr = 'Mañana';

        return (
            <View style={styles.sectionHeader}>
                <Text style={[styles.sectionHeaderText, { color: theme.text }]}>
                    {dateStr.charAt(0).toUpperCase() + dateStr.slice(1)}
                </Text>
                <View style={[styles.headerLine, { backgroundColor: theme.border + '30' }]} />
            </View>
        );
    };

    return (
        <View style={[styles.container, { backgroundColor: theme.background }]}>
            <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
            
            <LinearGradient
                colors={[theme.primary + '20', theme.background]}
                start={{ x: 0, y: 0 }}
                end={{ x: 0.5, y: 0.3 }}
                style={styles.gradientHeader}
            />

            <View style={styles.header}>
                <View>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <TouchableOpacity 
                            onPress={() => navigation.goBack()}
                            style={{ marginRight: 10 }}
                        >
                            <ChevronLeft size={24} color={theme.text} />
                        </TouchableOpacity>
                        <Text style={[styles.welcomeText, { color: theme.text }]}>Agenda</Text>
                    </View>
                    <View style={styles.countRow}>
                        <Clock size={12} color={theme.primary} />
                        <Text style={[styles.countText, { color: theme.textMuted }]}>
                            {events.length} eventos y {tasks.length} tareas
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
                        <MessageSquare size={16} color={theme.primary} style={{ marginRight: 10 }} />
                        <Text style={[styles.dropdownText, { color: theme.text }]}>Chat</Text>
                      </View>
                   </TouchableOpacity>
                   <TouchableOpacity onPress={() => { setShowAppMenu(false); navigation.navigate('Home'); }} style={styles.dropdownItem}>
                      <View style={styles.dropdownIconText}>
                        <FileText size={16} color={theme.primary} style={{ marginRight: 10 }} />
                        <Text style={[styles.dropdownText, { color: theme.text }]}>Notas</Text>
                      </View>
                   </TouchableOpacity>
                </View>
            )}

            {loading && !refreshing ? (
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color={theme.primary} />
                </View>
            ) : (
                <SectionList
                    sections={sections}
                    keyExtractor={(item) => (item.type === 'event' ? `event-${item.id}` : `task-${item.id}`)}
                    renderItem={renderItem}
                    renderSectionHeader={renderSectionHeader}
                    contentContainerStyle={styles.listContent}
                    stickySectionHeadersEnabled={true}
                    showsVerticalScrollIndicator={false}
                    refreshControl={
                        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
                    }
                    ListEmptyComponent={
                        <View style={styles.emptyContainer}>
                            <View style={[styles.emptyIconCircle, { backgroundColor: theme.surface }]}>
                               <CalendarIcon size={32} color={theme.textMuted} />
                            </View>
                            <Text style={[styles.emptyText, { color: theme.text }]}>Agenda Libre</Text>
                            <Text style={[styles.emptySubtext, { color: theme.textMuted }]}>No tienes compromisos pendientes para este periodo.</Text>
                        </View>
                    }
                />
            )}

            <TouchableOpacity 
                activeOpacity={0.9}
                style={[styles.fab, { backgroundColor: 'transparent' }]}
                onPress={() => setModalVisible(true)}
            >
                <LinearGradient
                   colors={[colors.primary, colors.primaryDark]}
                   style={styles.fabGradient}
                >
                   <Plus color="#fff" size={28} />
                </LinearGradient>
            </TouchableOpacity>

            <Modal
                animationType="slide"
                transparent={true}
                visible={modalVisible}
                onRequestClose={() => setModalVisible(false)}
            >
                 <View style={styles.modalOverlay}>
                     <KeyboardAvoidingView
                         behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                         keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
                         style={{ width: '100%', justifyContent: 'flex-end' }}
                     >
                        <View style={[styles.modalContent, { backgroundColor: theme.surface }]}>
                            <View style={styles.modalHandle} />
                            <View style={styles.modalHeader}>
                                <Text style={[styles.modalTitle, { color: theme.text }]}>
                                    {editingItem ? `Editar ${editingItem.type === 'event' ? 'Evento' : 'Tarea'}` : 'Nuevo Ítem'}
                                </Text>
                                <TouchableOpacity onPress={() => { setModalVisible(false); resetForm(); }} style={styles.closeBtn}>
                                    <X color={theme.textMuted} size={20} />
                                </TouchableOpacity>
                            </View>

                            <View style={[
                                styles.typeSelector, 
                                { backgroundColor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }
                            ]}>
                                <TouchableOpacity 
                                    style={[
                                        styles.typeTab, 
                                        createType === 'event' && { backgroundColor: theme.surface, ...styles.activeTabShadow }
                                    ]}
                                    onPress={() => setCreateType('event')}
                                >
                                    <Text style={[styles.typeTabText, { color: createType === 'event' ? theme.primary : theme.textMuted }]}>Evento</Text>
                                </TouchableOpacity>
                                <TouchableOpacity 
                                    style={[
                                        styles.typeTab, 
                                        createType === 'task' && { backgroundColor: theme.surface, ...styles.activeTabShadow }
                                    ]}
                                    onPress={() => setCreateType('task')}
                                >
                                    <Text style={[styles.typeTabText, { color: createType === 'task' ? theme.primary : theme.textMuted }]}>Tarea</Text>
                                </TouchableOpacity>
                            </View>

                            <ScrollView
                                style={styles.formContent}
                                contentContainerStyle={{ paddingBottom: 40 }}
                                showsVerticalScrollIndicator={false}
                            >
                            {/* Workspace Selector */}
                            {workspaces.length > 0 && (
                                <View style={{ marginBottom: 16 }}>
                                    <Text style={[styles.wsLabel, { color: theme.textMuted }]}>Libreta</Text>
                                    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                                        <TouchableOpacity
                                            style={[styles.wsChip, !selectedWsId && { backgroundColor: theme.primary + '20', borderColor: theme.primary + '60' }]}
                                            onPress={() => setSelectedWsId(null)}
                                        >
                                            <Text style={[styles.wsChipText, { color: !selectedWsId ? theme.primary : theme.textMuted }]}>Global</Text>
                                        </TouchableOpacity>
                                        {workspaces.map(ws => (
                                            <TouchableOpacity
                                                key={ws.id}
                                                style={[styles.wsChip, selectedWsId === ws.id && { backgroundColor: (ws.color || theme.primary) + '20', borderColor: (ws.color || theme.primary) + '60' }]}
                                                onPress={() => setSelectedWsId(ws.id)}
                                            >
                                                <View style={[styles.wsDot, { backgroundColor: ws.color || theme.primary }]} />
                                                <Text style={[styles.wsChipText, { color: selectedWsId === ws.id ? (ws.color || theme.primary) : theme.textMuted }]}>{ws.name}</Text>
                                            </TouchableOpacity>
                                        ))}
                                    </ScrollView>
                                </View>
                            )}
                            {createType === 'event' ? (
                                <>
                                    <Input
                                        label="Título"
                                        value={summary}
                                        onChangeText={setSummary}
                                        placeholder="Ej: Reunión de estrategia"
                                        theme={isDarkMode ? 'dark' : 'light'}
                                    />
                                    <View style={styles.row}>
                                        <View style={{ flex: 1, marginRight: spacing.sm }}>
                                            <Input
                                                label="Fecha"
                                                value={eventDate}
                                                onChangeText={setEventDate}
                                                theme={isDarkMode ? 'dark' : 'light'}
                                            />
                                        </View>
                                        <View style={{ flex: 1, marginRight: spacing.sm }}>
                                            <Input
                                                label="Hora"
                                                value={eventTime}
                                                onChangeText={setEventTime}
                                                theme={isDarkMode ? 'dark' : 'light'}
                                            />
                                        </View>
                                        <View style={{ flex: 1.5 }}>
                                            <Input
                                                label="Ubicación"
                                                value={location}
                                                onChangeText={setLocation}
                                                placeholder="Lugar o Link"
                                                theme={isDarkMode ? 'dark' : 'light'}
                                            />
                                        </View>
                                    </View>
                                    <Input
                                        label="Descripción"
                                        value={description}
                                        onChangeText={setDescription}
                                        placeholder="Notas adicionales..."
                                        multiline
                                        theme={isDarkMode ? 'dark' : 'light'}
                                    />
                                </>
                            ) : (
                                <>
                                    <Input
                                        label="Descripción de la Tarea"
                                        value={description}
                                        onChangeText={setDescription}
                                        placeholder="Ej: Revisar reporte trimestral"
                                        multiline
                                        theme={isDarkMode ? 'dark' : 'light'}
                                    />
                                    <View style={styles.row}>
                                        <View style={{ flex: 1, marginRight: spacing.sm }}>
                                            <Input
                                                label="Fecha"
                                                value={eventDate}
                                                onChangeText={setEventDate}
                                                theme={isDarkMode ? 'dark' : 'light'}
                                            />
                                        </View>
                                        <View style={{ flex: 1 }}>
                                            <Input
                                                label="Prioridad (Hora)"
                                                value={eventTime}
                                                onChangeText={setEventTime}
                                                theme={isDarkMode ? 'dark' : 'light'}
                                            />
                                        </View>
                                    </View>
                                </>
                            )}
                        </ScrollView>

                        <View style={styles.modalFooter}>
                            {editingItem && (
                                <TouchableOpacity onPress={handleDelete} disabled={isSubmitting} style={[styles.deleteBtn, { borderColor: 'rgba(239,68,68,0.3)' }]}>
                                    <Text style={styles.deleteBtnText}>Eliminar</Text>
                                </TouchableOpacity>
                            )}
                            <TouchableOpacity onPress={handleCreate} disabled={isSubmitting} style={{ flex: 1 }}>
                               <LinearGradient
                                  colors={[colors.primary, colors.primaryDark]}
                                  style={styles.submitBtn}
                               >
                                  {isSubmitting ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.submitBtnText}>{editingItem ? 'Guardar Cambios' : 'Confirmar Creación'}</Text>}
                               </LinearGradient>
                            </TouchableOpacity>
                        </View>
                    </View>
                </KeyboardAvoidingView>
            </View>
        </Modal>
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
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    listContent: {
        paddingHorizontal: spacing.lg,
        paddingBottom: 120,
    },
    sectionHeader: {
        paddingVertical: 15,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    sectionHeaderText: {
        fontSize: 14,
        fontWeight: '800',
        letterSpacing: -0.3,
    },
    headerLine: {
       flex: 1,
       height: 1,
       borderRadius: 1,
    },
    itemCard: {
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: 20,
        padding: 16,
        marginBottom: 10,
        borderWidth: 1,
        ...Platform.select({
           ios: {
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 4 },
              shadowOpacity: 0.05,
              shadowRadius: 10,
           },
           android: {
              elevation: 2,
           }
        })
    },
    timeSection: {
        alignItems: 'center',
        width: 50,
        marginRight: 15,
    },
    timeText: {
        fontSize: 15,
        fontWeight: '800',
        marginBottom: 6,
    },
    typeIndicator: {
        width: 4,
        height: 16,
        borderRadius: 2,
    },
    checkContainer: {
        justifyContent: 'center',
        alignItems: 'center',
    },
    checkFilled: {
       width: 24,
       height: 24,
       borderRadius: 12,
       justifyContent: 'center',
       alignItems: 'center',
    },
    contentContainer: {
        flex: 1,
    },
    summaryText: {
        fontSize: 16,
        fontWeight: '700',
        marginBottom: spacing.xs,
        letterSpacing: -0.3,
    },
    detailRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    detailText: {
        fontSize: 12,
        fontWeight: '600',
    },
    workspaceBadge: {
        alignSelf: 'flex-start',
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 6,
        marginTop: 6,
    },
    workspaceBadgeText: {
        fontSize: 9,
        fontWeight: '900',
        textTransform: 'uppercase',
    },
    emptyContainer: {
        marginTop: 100,
        alignItems: 'center',
        paddingHorizontal: 40,
    },
    emptyIconCircle: {
       width: 70,
       height: 70,
       borderRadius: 35,
       justifyContent: 'center',
       alignItems: 'center',
       marginBottom: 20,
    },
    emptyText: {
        fontSize: 20,
        fontWeight: '800',
        marginBottom: 10,
    },
    emptySubtext: {
        fontSize: 14,
        textAlign: 'center',
        opacity: 0.6,
        lineHeight: 20,
    },
  fab: {
    position: 'absolute',
    right: 25,
    bottom: 80,
    width: 60,
    height: 60,
    borderRadius: 30,
    ...Platform.select({
       ios: {
          shadowColor: colors.primary,
          shadowOffset: { width: 0, height: 10 },
          shadowOpacity: 0.4,
          shadowRadius: 15,
       },
       android: {
          elevation: 8,
       }
    })
  },
    fabGradient: {
       width: 60,
       height: 60,
       borderRadius: 30,
       justifyContent: 'center',
       alignItems: 'center',
    },
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.4)',
        justifyContent: 'flex-end',
    },
    modalContent: {
        borderTopLeftRadius: 32,
        borderTopRightRadius: 32,
        padding: 24,
        paddingBottom: Platform.OS === 'ios' ? 40 : 34,
        maxHeight: '90%',
    },
    modalHandle: {
       width: 40,
       height: 4,
       borderRadius: 2,
       backgroundColor: 'rgba(0,0,0,0.1)',
       alignSelf: 'center',
       marginBottom: 15,
    },
    modalHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
    },
    modalTitle: {
        fontSize: 22,
        fontWeight: '900',
    },
    closeBtn: {
       padding: 8,
       borderRadius: 12,
       backgroundColor: 'rgba(0,0,0,0.03)',
    },
    typeSelector: {
        flexDirection: 'row',
        borderRadius: 16,
        padding: 4,
        marginBottom: 24,
    },
    typeTab: {
        flex: 1,
        paddingVertical: 12,
        alignItems: 'center',
        borderRadius: 12,
    },
    activeTabShadow: {
       ...Platform.select({
          ios: {
             shadowColor: '#000',
             shadowOffset: { width: 0, height: 2 },
             shadowOpacity: 0.05,
             shadowRadius: 4,
          },
          android: {
             elevation: 2,
          }
       })
    },
    typeTabText: {
        fontWeight: '800',
        fontSize: 14,
    },
    formContent: {
        marginBottom: 24,
    },
    modalFooter: {
        flexDirection: 'row',
        gap: 12,
        marginTop: 10,
    },
    submitBtn: {
       height: 56,
       borderRadius: 18,
       justifyContent: 'center',
       alignItems: 'center',
    },
    submitBtnText: {
       color: '#fff',
       fontSize: 16,
       fontWeight: '800',
    },
    deleteBtn: {
        paddingHorizontal: 20,
        height: 54,
        borderRadius: 16,
        borderWidth: 1,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 10,
        backgroundColor: 'rgba(239,68,68,0.08)',
    },
    deleteBtnText: {
        color: '#ef4444',
        fontSize: 15,
        fontWeight: '800',
    },
    row: {
        flexDirection: 'row',
    },
    wsLabel: {
        fontSize: 11,
        fontWeight: '700',
        textTransform: 'uppercase',
        letterSpacing: 1,
        marginBottom: 10,
    },
    wsChip: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: 'rgba(0,0,0,0.1)',
        marginRight: 8,
        backgroundColor: 'transparent',
    },
    wsChipText: {
        fontSize: 13,
        fontWeight: '700',
    },
    wsDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        marginRight: 6,
    },
    dropdownMenu: {
        position: 'absolute',
        top: Platform.OS === 'ios' ? 120 : 90,
        right: spacing.lg,
        borderWidth: 1,
        borderRadius: 16,
        zIndex: 2000,
        padding: 6,
        minWidth: 160,
        ...Platform.select({
          ios: {
            shadowColor: '#000',
            shadowOffset: { width: 0, height: 8 },
            shadowOpacity: 0.1,
            shadowRadius: 12,
          },
          android: {
            elevation: 6,
          }
        })
    },
    dropdownItem: {
        paddingVertical: 12,
        paddingHorizontal: 15,
    },
    dropdownIconText: {
       flexDirection: 'row',
       alignItems: 'center',
    },
    dropdownText: {
        fontSize: 14,
        fontWeight: '600',
    }
});

