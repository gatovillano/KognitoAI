// src/screens/NoteDetailScreen.tsx
import React, { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import {
    View,
    Text,
    TextInput,
    StyleSheet,
    ScrollView,
    ActivityIndicator,
    TouchableOpacity,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { MarkdownWysiwygEditor } from '../components/MarkdownWysiwygEditor';
import { notesService, Note } from '../api/notesService';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import { useAuth } from '../context/AuthContext';
import { ChevronLeft, Calendar, Tag, CheckCircle, Clock, MoreVertical, Share2, X } from 'lucide-react-native';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const AUTOSAVE_DELAY = 1200;
type SaveStatus = 'saved' | 'saving' | 'unsaved' | 'error';

export const NoteDetailScreen = ({ route, navigation }: any) => {
    const { noteId } = route.params;
    const [note, setNote] = useState<Note | null>(null);
    const [loading, setLoading] = useState(true);
    const [title, setTitle] = useState('');
    const [content, setContent] = useState('');
    const [saveStatus, setSaveStatus] = useState<SaveStatus>('saved');
    const { isDarkMode } = useAuth();
    const theme = isDarkMode ? colors : lightColors;
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        notesService.getNote(noteId).then(data => {
            setNote(data);
            setTitle(data.title || '');
            setContent(data.content || '');
        }).catch(e => console.error('Error fetching note:', e))
          .finally(() => setLoading(false));
    }, [noteId]);

    const triggerAutoSave = useCallback((newTitle: string, newContent: string) => {
        setSaveStatus('unsaved');
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(async () => {
            setSaveStatus('saving');
            try {
                await notesService.updateNote(noteId, { title: newTitle, content: newContent });
                setSaveStatus('saved');
            } catch {
                setSaveStatus('error');
            }
        }, AUTOSAVE_DELAY);
    }, [noteId]);

    const handleTitleChange = (text: string) => { setTitle(text); triggerAutoSave(text, content); };
    const handleContentChange = (text: string) => { setContent(text); triggerAutoSave(title, text); };

    const markdownStyles = useMemo(() => ({
        body: { color: theme.text, fontSize: 16, lineHeight: 26, fontWeight: '400' },
        heading1: { color: theme.primary, fontSize: 26, fontWeight: '800', marginTop: 24, marginBottom: 12, letterSpacing: -0.5 },
        heading2: { color: theme.text, fontSize: 20, fontWeight: '700', marginTop: 20, marginBottom: 10, letterSpacing: -0.3 },
        heading3: { color: theme.text, fontSize: 18, fontWeight: '700', marginTop: 16, marginBottom: 8 },
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
        table: { borderWidth: 1, borderColor: theme.border, borderRadius: 12, marginVertical: 16, overflow: 'hidden' as 'hidden' },
        tr: { borderBottomWidth: 1, borderColor: theme.border, flexDirection: 'row' as 'row' },
        th: { backgroundColor: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)', padding: 12, fontWeight: '700', color: theme.text },
        td: { padding: 12, color: theme.textMuted },
        blockquote: {
            backgroundColor: isDarkMode ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.01)', 
            borderLeftColor: theme.primary,
            borderLeftWidth: 4, 
            paddingHorizontal: 16, 
            paddingVertical: 12, 
            marginVertical: 16,
            borderRadius: 4,
        },
        list_item: { marginVertical: 4 },
        bullet_list: { marginVertical: 8 },
        ordered_list: { marginVertical: 8 },
        strong: { fontWeight: '700', color: theme.text },
        em: { fontStyle: 'italic' },
        hr: { borderBottomColor: theme.border, borderBottomWidth: 1, marginVertical: 20 },
    }), [theme, isDarkMode]);

    const SaveStatusIndicator = () => {
        const icons = {
            saved: <CheckCircle size={12} color="#10b981" />,
            saving: <ActivityIndicator size="small" color={theme.textMuted} style={{ transform: [{ scale: 0.6 }] }} />,
            unsaved: <Clock size={12} color={theme.primary} />,
            error: <X size={12} color={colors.error} />
        };
        const texts = { saved: 'Guardado', saving: 'Guardando', unsaved: 'Editando', error: 'Error' };
        const colors_status = { saved: '#10b981', saving: theme.textMuted, unsaved: theme.primary, error: colors.error };
        
        return (
            <View style={[styles.saveIndicator, { backgroundColor: colors_status[saveStatus] + '15' }]}>
                {icons[saveStatus]}
                <Text style={[styles.saveText, { color: colors_status[saveStatus] }]}>{texts[saveStatus]}</Text>
            </View>
        );
    };

    if (loading) return (
        <View style={[styles.center, { backgroundColor: theme.background }]}>
            <ActivityIndicator size="large" color={theme.primary} />
        </View>
    );

     return (
         <View style={[styles.container, { backgroundColor: theme.background }]}>
              <KeyboardAvoidingView
                  behavior={Platform.OS === 'ios' ? 'padding' : 'padding'}
                  keyboardVerticalOffset={Platform.OS === 'ios' ? 100 : 20}
                  style={{ flex: 1 }}
              >
                 <View style={[styles.header, { borderBottomColor: theme.border + '30' }]}>
                     <TouchableOpacity onPress={() => navigation.goBack()} style={styles.iconBtn}>
                         <ChevronLeft size={24} color={theme.text} />
                     </TouchableOpacity>
                     <View style={{ flex: 1, alignItems: 'center' }}>
                        <SaveStatusIndicator />
                     </View>
                     <TouchableOpacity style={styles.iconBtn}>
                         <Share2 size={20} color={theme.textMuted} />
                     </TouchableOpacity>
                 </View>

              <ScrollView
                  contentContainerStyle={[styles.content, { paddingBottom: 120 }]}
                  keyboardShouldPersistTaps="handled"
                  showsVerticalScrollIndicator={false}
              >
                <View style={styles.metaRow}>
                    <View style={styles.metaItem}>
                        <Calendar size={13} color={theme.textMuted} />
                        <Text style={[styles.metaText, { color: theme.textMuted }]}>
                            {format(new Date(note?.created_at || new Date()), "d MMM, yyyy", { locale: es })}
                        </Text>
                    </View>
                    {note?.workspace_name && (
                       <View style={[styles.metaItem, { marginLeft: spacing.md }]}>
                          <View style={[styles.workspaceDot, { backgroundColor: note.workspace_color || theme.primary }]} />
                          <Text style={[styles.metaText, { color: theme.textMuted }]}>{note.workspace_name}</Text>
                       </View>
                    )}
                </View>

                <TextInput
                    style={[styles.titleInput, { color: theme.text }]}
                    value={title}
                    onChangeText={handleTitleChange}
                    placeholder="Sin título"
                    placeholderTextColor={theme.textMuted + '60'}
                    multiline
                    scrollEnabled={false}
                />

                <MarkdownWysiwygEditor
                    content={content}
                    markdownStyles={markdownStyles}
                    theme={theme}
                    onContentChange={handleContentChange}
                 />
             </ScrollView>
             </KeyboardAvoidingView>
         </View>
    );
};

const styles = StyleSheet.create({
    container: { flex: 1 },
    header: { 
        flexDirection: 'row', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        paddingHorizontal: spacing.md, 
        paddingTop: Platform.OS === 'ios' ? 60 : 40, 
        paddingBottom: spacing.sm, 
        borderBottomWidth: 1 
    },
    iconBtn: { 
        width: 40,
        height: 40,
        borderRadius: 20,
        justifyContent: 'center',
        alignItems: 'center',
    },
    saveIndicator: { 
        flexDirection: 'row', 
        alignItems: 'center', 
        gap: 5, 
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 20,
    },
    saveText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
    content: { padding: spacing.lg, paddingBottom: 100 },
    metaRow: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.lg },
    metaItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
    metaText: { fontSize: 13, fontWeight: '500' },
    workspaceDot: { width: 8, height: 8, borderRadius: 4 },
    titleInput: { 
        fontSize: 30, 
        fontWeight: '800', 
        marginBottom: spacing.lg, 
        lineHeight: 38,
        letterSpacing: -1,
    },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
});

