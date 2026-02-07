// src/screens/NoteDetailScreen.tsx
import React, { useEffect, useState, useMemo } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, TouchableOpacity } from 'react-native';
import Markdown from 'react-native-markdown-display';
import { notesService, Note } from '../api/notesService';
import { colors, lightColors, spacing } from '../theme/colors';
import { useAuth } from '../context/AuthContext';
import { ChevronLeft, Calendar, Tag } from 'lucide-react-native';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

export const NoteDetailScreen = ({ route, navigation }: any) => {
    const { noteId } = route.params;
    const [note, setNote] = useState<Note | null>(null);
    const [loading, setLoading] = useState(true);
    const { isDarkMode } = useAuth();
    const theme = isDarkMode ? colors : lightColors;

    useEffect(() => {
        const fetchNote = async () => {
            try {
                const data = await notesService.getNote(noteId);
                setNote(data);
            } catch (error) {
                console.error('Error fetching note detail:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchNote();
    }, [noteId]);

    const markdownStyles = useMemo(() => ({
        body: {
            color: theme.text,
            fontSize: 16,
            lineHeight: 24,
        },
        heading1: {
            color: theme.primary,
            fontSize: 24,
            fontWeight: 'bold',
            marginVertical: 10,
        },
        heading2: {
            color: theme.text,
            fontSize: 20,
            fontWeight: 'bold',
            marginVertical: 8,
        },
        paragraph: {
            marginVertical: 8,
        },
        link: {
            color: theme.primary,
            textDecorationLine: 'underline' as 'underline',
        },
        code_inline: {
            backgroundColor: theme.surface,
            color: theme.text,
            padding: 4,
            borderRadius: 4,
        },
        fence: {
            backgroundColor: theme.surface,
            borderRadius: 8,
            padding: 12,
            marginVertical: 10,
            borderWidth: 1,
            borderColor: theme.border,
        },
        table: {
            borderWidth: 1,
            borderColor: theme.border,
            borderRadius: 4,
        },
        tr: {
            borderBottomWidth: 1,
            borderColor: theme.border,
            flexDirection: 'row' as 'row',
        },
        th: {
            backgroundColor: theme.surface,
            padding: 8,
            fontWeight: 'bold',
        },
        td: {
            padding: 8,
        },
        blockquote: {
            backgroundColor: theme.surface,
            borderLeftColor: theme.primary,
            borderLeftWidth: 4,
            paddingHorizontal: 12,
            paddingVertical: 8,
            marginVertical: 10,
        },
        list_item: {
            marginVertical: 4,
        },
        bullet_list: {
            marginVertical: 8,
        },
        ordered_list: {
            marginVertical: 8,
        },
    }), [theme]);

    if (loading) {
        return (
            <View style={[styles.center, { backgroundColor: theme.background }]}>
                <ActivityIndicator size="large" color={theme.primary} />
            </View>
        );
    }

    if (!note) {
        return (
            <View style={[styles.center, { backgroundColor: theme.background }]}>
                <Text style={[styles.errorText, { color: theme.error }]}>No se pudo cargar la nota</Text>
            </View>
        );
    }

    return (
        <View style={[styles.container, { backgroundColor: theme.background }]}>
            <View style={[styles.header, { borderBottomColor: theme.border }]}>
                <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
                    <ChevronLeft size={28} color={theme.text} />
                </TouchableOpacity>
                <Text style={[styles.headerTitle, { color: theme.text }]} numberOfLines={1}>{note.title || 'Nota'}</Text>
            </View>

            <ScrollView contentContainerStyle={styles.content}>
                <View style={styles.metaContainer}>
                    <View style={styles.metaItem}>
                        <Calendar size={16} color={theme.textMuted} />
                        <Text style={[styles.metaText, { color: theme.textMuted }]}>
                            {format(new Date(note.created_at), "d 'de' MMMM, yyyy", { locale: es })}
                        </Text>
                    </View>
                    {note.category && (
                        <View style={styles.metaItem}>
                            <Tag size={16} color={theme.textMuted} />
                            <Text style={[styles.metaText, { color: theme.textMuted }]}>{note.category}</Text>
                        </View>
                    )}
                </View>

                <Text style={[styles.title, { color: theme.text }]}>{note.title || 'Sin título'}</Text>

                <View style={styles.markdownContainer}>
                    <Markdown style={markdownStyles}>
                        {note.content}
                    </Markdown>
                </View>
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
        paddingHorizontal: spacing.md,
        paddingTop: spacing.xl * 2,
        paddingBottom: spacing.md,
        borderBottomWidth: 1,
    },
    backButton: {
        padding: spacing.sm,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '600',
        marginLeft: spacing.sm,
        flex: 1,
    },
    content: {
        padding: spacing.lg,
    },
    metaContainer: {
        flexDirection: 'row',
        marginBottom: spacing.lg,
        flexWrap: 'wrap',
    },
    metaItem: {
        flexDirection: 'row',
        alignItems: 'center',
        marginRight: spacing.lg,
        marginBottom: spacing.xs,
    },
    metaText: {
        fontSize: 13,
        marginLeft: 6,
    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        marginBottom: spacing.xl,
    },
    markdownContainer: {
        marginTop: spacing.sm,
    },
    center: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    errorText: {
        fontSize: 16,
    },
});
