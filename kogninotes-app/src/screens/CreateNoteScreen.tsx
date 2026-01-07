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
    Alert
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
            <LinearGradient
                colors={[theme.primary, theme.background]}
                start={{ x: 0, y: 0 }}
                end={{ x: 0, y: 0.2 }}
                style={styles.gradientHeader}
            />

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.flex}
            >
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                        <ChevronLeft size={28} color={theme.text} />
                    </TouchableOpacity>
                    <Text style={[styles.headerTitle, { color: theme.text }]}>Editor Avanzado</Text>
                    <TouchableOpacity
                        onPress={handleSave}
                        disabled={loading}
                        style={[styles.saveButton, { backgroundColor: theme.primary }, loading && styles.disabledButton]}
                    >
                        {loading ? (
                            <ActivityIndicator size="small" color="#fff" />
                        ) : (
                            <Save size={24} color="#fff" />
                        )}
                    </TouchableOpacity>
                </View>

                <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                    {/* Workspace Selector */}
                    <View style={styles.section}>
                        <View style={styles.sectionHeader}>
                            <Layout size={18} color={theme.primary} />
                            <Text style={[styles.sectionLabel, { color: theme.textMuted }]}>Espacio de Trabajo</Text>
                        </View>
                        {fetchingWorkspaces ? (
                            <ActivityIndicator size="small" color={theme.primary} />
                        ) : (
                            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.workspaceList}>
                                {/* BLINDAJE: Doble verificación de array */}
                                {(Array.isArray(workspaces) ? workspaces : []).map((ws) => (
                                    <TouchableOpacity
                                        key={ws.id}
                                        onPress={() => setSelectedWorkspace(ws.id)}
                                        style={[
                                            styles.workspaceChip,
                                            { backgroundColor: theme.surface, borderColor: theme.border },
                                            selectedWorkspace === ws.id && { backgroundColor: ws.color || theme.primary, borderColor: ws.color || theme.primary }
                                        ]}
                                    >
                                        <Text style={[
                                            styles.workspaceText,
                                            { color: theme.textMuted },
                                            selectedWorkspace === ws.id && styles.activeWorkspaceText
                                        ]}>
                                            {ws.name}
                                        </Text>
                                    </TouchableOpacity>
                                ))}
                            </ScrollView>
                        )}
                    </View>

                    {/* Category Input */}
                    <View style={styles.section}>
                        <View style={styles.sectionHeader}>
                            <Tag size={18} color={theme.primary} />
                            <Text style={[styles.sectionLabel, { color: theme.textMuted }]}>Categoría</Text>
                        </View>
                        <TextInput
                            style={[styles.categoryInput, { backgroundColor: theme.surface, color: theme.text, borderColor: theme.border }]}
                            placeholder="Ej: Ideas, Reunión, Personal..."
                            placeholderTextColor={theme.textMuted}
                            value={category}
                            onChangeText={setCategory}
                        />
                    </View>

                    {/* Title Editor */}
                    <View style={[styles.editorContainer, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                        <View style={styles.sectionHeader}>
                            <Type size={18} color={theme.primary} />
                            <Text style={[styles.sectionLabel, { color: theme.textMuted }]}>Título de la Nota</Text>
                        </View>
                        <TextInput
                            style={[styles.titleInput, { color: theme.text }]}
                            placeholder="Escribe un título impactante..."
                            placeholderTextColor={theme.textMuted}
                            value={title}
                            onChangeText={setTitle}
                            multiline
                        />

                        <View style={[styles.divider, { backgroundColor: theme.border }]} />

                        {/* Content Editor */}
                        <TextInput
                            style={[styles.contentInput, { color: theme.text }]}
                            placeholder="Empieza a escribir tus pensamientos (soporta Markdown)..."
                            placeholderTextColor={theme.textMuted}
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
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: spacing.xl * 2,
        paddingHorizontal: spacing.md,
        paddingBottom: spacing.md,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: 'bold',
    },
    backButton: {
        padding: spacing.sm,
    },
    saveButton: {
        padding: spacing.sm,
        borderRadius: borderRadius.md,
        elevation: 4,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
    },
    disabledButton: {
        opacity: 0.6,
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
        fontSize: 14,
        fontWeight: '600',
        marginLeft: spacing.xs,
        textTransform: 'uppercase',
        letterSpacing: 1,
    },
    workspaceList: {
        flexDirection: 'row',
        marginTop: spacing.xs,
    },
    workspaceChip: {
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        borderRadius: borderRadius.full,
        marginRight: spacing.sm,
        borderWidth: 1,
    },
    workspaceText: {
        fontSize: 14,
        fontWeight: '500',
    },
    activeWorkspaceText: {
        color: '#fff',
        fontWeight: 'bold',
    },
    categoryInput: {
        borderRadius: borderRadius.md,
        padding: spacing.md,
        fontSize: 15,
        borderWidth: 1,
    },
    editorContainer: {
        borderRadius: borderRadius.lg,
        padding: spacing.lg,
        marginBottom: spacing.xl * 2,
        borderWidth: 1,
        minHeight: 400,
    },
    titleInput: {
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: spacing.md,
        padding: 0,
    },
    divider: {
        height: 1,
        marginBottom: spacing.lg,
    },
    contentInput: {
        fontSize: 16,
        lineHeight: 24,
        padding: 0,
        minHeight: 300,
    },
});
