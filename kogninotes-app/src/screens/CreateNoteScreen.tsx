// src/screens/CreateNoteScreen.tsx
import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TextInput,
    TouchableOpacity,
    ScrollView,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
    Alert,
    StatusBar
} from 'react-native';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import { notesService } from '../api/notesService';
import { workspaceService, Workspace } from '../api/workspaceService';
import { ChevronLeft, Save, Layout, Tag, Type } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuth } from '../context/AuthContext';

export const CreateNoteScreen = ({ navigation }: any) => {
    const [title, setTitle] = useState('');
    const [content, setContent] = useState('');
    const [category, setCategory] = useState('');
    const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [loading, setLoading] = useState(false);
    const [fetchingWorkspaces, setFetchingWorkspaces] = useState(true);

    const { isDarkMode } = useAuth();
    const theme = isDarkMode ? colors : lightColors;

    useEffect(() => {
        loadWorkspaces();
    }, []);

    const loadWorkspaces = async () => {
        try {
            const data = await workspaceService.listWorkspaces();
            // BLINDAJE: Aseguramos que data sea un array
            const workspacesArray = Array.isArray(data) ? data : [];
            setWorkspaces(workspacesArray);
            if (workspacesArray.length > 0) {
                setSelectedWorkspace(workspacesArray[0].id);
            }
        } catch (error) {
            console.error('Error loading workspaces:', error);
            setWorkspaces([]); // Fallback a array vacío
        } finally {
            setFetchingWorkspaces(false);
        }
    };

    const handleSave = async () => {
        if (!title || !content) {
            Alert.alert('Campos requeridos', 'Por favor, añade al menos un título y contenido a tu nota.');
            return;
        }

        setLoading(true);
        try {
            await notesService.createNote({
                title,
                content,
                category,
                workspace_id: selectedWorkspace || undefined
            });
            Alert.alert('¡Éxito!', 'Nota creada correctamente', [
                { text: 'OK', onPress: () => navigation.goBack() }
            ]);
        } catch (error) {
            Alert.alert('Error', 'No se pudo guardar la nota. Inténtalo de nuevo.');
        } finally {
            setLoading(false);
        }
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

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                keyboardVerticalOffset={Platform.OS === 'ios' ? 100 : 20}
                style={styles.flex}
            >
                <View style={styles.header}>
                    <View>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                            <TouchableOpacity onPress={() => navigation.goBack()} style={{ marginRight: 10 }}>
                                <ChevronLeft size={24} color={theme.text} />
                            </TouchableOpacity>
                            <Text style={[styles.welcomeText, { color: theme.text }]}>Nueva Nota</Text>
                        </View>
                        <View style={styles.countRow}>
                            <Type size={12} color={theme.primary} />
                            <Text style={[styles.countText, { color: theme.textMuted }]}>
                                Captura tus ideas y conocimientos
                            </Text>
                        </View>
                    </View>

                    <TouchableOpacity
                        onPress={handleSave}
                        disabled={loading}
                        style={[
                            styles.actionButton, 
                            { backgroundColor: theme.surface, borderColor: theme.border },
                            loading && { opacity: 0.7 }
                        ]}
                    >
                        {loading ? (
                            <ActivityIndicator size="small" color={theme.primary} />
                        ) : (
                            <Save size={20} color={theme.primary} />
                        )}
                    </TouchableOpacity>
                </View>

                <ScrollView
                    style={styles.content}
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={{ paddingBottom: 120 }}
                >
                    {/* Workspace Selector */}
                    <View style={styles.section}>
                        <View style={styles.sectionHeader}>
                            <Layout size={16} color={theme.primary} />
                            <Text style={[styles.sectionLabel, { color: theme.textMuted }]}>Espacio de Trabajo</Text>
                        </View>
                        {fetchingWorkspaces ? (
                            <ActivityIndicator size="small" color={theme.primary} />
                        ) : (
                            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.workspaceList}>
                                {(Array.isArray(workspaces) ? workspaces : []).map((ws) => (
                                    <TouchableOpacity
                                        key={ws.id}
                                        onPress={() => setSelectedWorkspace(ws.id)}
                                        style={[
                                            styles.workspaceChip,
                                            { backgroundColor: theme.surface, borderColor: theme.border },
                                            selectedWorkspace === ws.id && { 
                                                backgroundColor: (ws.color || theme.primary) + '15', 
                                                borderColor: ws.color || theme.primary 
                                            }
                                        ]}
                                    >
                                        <Text style={[
                                            styles.workspaceText,
                                            { color: theme.textMuted },
                                            selectedWorkspace === ws.id && { color: ws.color || theme.primary, fontWeight: '700' }
                                        ]}>
                                            {ws.name}
                                        </Text>
                                    </TouchableOpacity>
                                ))}
                            </ScrollView>
                        )}
                    </View>

                    {/* Editor Container */}
                    <View style={[styles.editorCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                        {/* Title Editor */}
                        <TextInput
                            style={[styles.titleInput, { color: theme.text }]}
                            placeholder="Título de la nota..."
                            placeholderTextColor={theme.textMuted + '80'}
                            value={title}
                            onChangeText={setTitle}
                            multiline
                        />

                        <View style={[styles.divider, { backgroundColor: theme.border + '50' }]} />

                        {/* Category & Metadata Row */}
                        <View style={styles.metaInputRow}>
                            <Tag size={16} color={theme.textMuted} style={{ marginRight: 8 }} />
                            <TextInput
                                style={[styles.categoryInput, { color: theme.text }]}
                                placeholder="Añadir categoría..."
                                placeholderTextColor={theme.textMuted + '60'}
                                value={category}
                                onChangeText={setCategory}
                            />
                        </View>

                        <View style={[styles.divider, { backgroundColor: theme.border + '30', marginBottom: spacing.md }]} />

                        {/* Content Editor */}
                        <TextInput
                            style={[styles.contentInput, { color: theme.text }]}
                            placeholder="Empieza a escribir tus pensamientos (soporta Markdown)..."
                            placeholderTextColor={theme.textMuted + '60'}
                            value={content}
                            onChangeText={setContent}
                            multiline
                            textAlignVertical="top"
                        />
                    </View>
                </ScrollView>
            </KeyboardAvoidingView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    flex: {
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
    actionButton: {
        width: 44,
        height: 44,
        borderRadius: 14,
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
        ...Platform.select({
            ios: {
                shadowColor: '#000',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.1,
                shadowRadius: 8,
            },
            android: {
                elevation: 4,
            }
        })
    },
    content: {
        flex: 1,
        paddingHorizontal: spacing.lg,
    },
    section: {
        marginBottom: spacing.lg,
    },
    sectionHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: spacing.sm,
    },
    sectionLabel: {
        fontSize: 12,
        fontWeight: '700',
        marginLeft: spacing.xs,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    workspaceList: {
        marginTop: spacing.xs,
    },
    workspaceChip: {
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 14,
        marginRight: spacing.sm,
        borderWidth: 1,
    },
    workspaceText: {
        fontSize: 14,
        fontWeight: '600',
    },
    editorCard: {
        borderRadius: 24,
        padding: spacing.lg,
        borderWidth: 1,
        minHeight: 500,
        ...Platform.select({
            ios: {
                shadowColor: '#000',
                shadowOffset: { width: 0, height: 10 },
                shadowOpacity: 0.05,
                shadowRadius: 15,
            },
            android: {
                elevation: 3,
            }
        })
    },
    titleInput: {
        fontSize: 26,
        fontWeight: '800',
        marginBottom: spacing.md,
        padding: 0,
        letterSpacing: -0.5,
    },
    divider: {
        height: 1,
        marginBottom: spacing.md,
    },
    metaInputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: spacing.sm,
    },
    categoryInput: {
        flex: 1,
        fontSize: 15,
        fontWeight: '600',
        paddingVertical: 4,
    },
    contentInput: {
        fontSize: 17,
        lineHeight: 26,
        padding: 0,
        flex: 1,
        minHeight: 300,
        fontWeight: '400',
    },
});
