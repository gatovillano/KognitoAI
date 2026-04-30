// src/components/MarkdownEditor.tsx
import React, { useRef, useState, useCallback } from 'react';
import {
    View,
    Text,
    TextInput,
    ScrollView,
    TouchableOpacity,
    StyleSheet,
    Modal,
    Platform,
    KeyboardAvoidingView,
    NativeSyntheticEvent,
    TextInputSelectionChangeEventData,
} from 'react-native';
import {
    Bold,
    Italic,
    Heading1,
    Heading2,
    List,
    CheckSquare,
    Code,
    Quote,
    Minus,
    Link,
    X,
    Check,
} from 'lucide-react-native';
import { MarkdownWithTasks } from './MarkdownWithTasks';
import { borderRadius, spacing } from '../theme/colors';

interface Props {
    content: string;
    markdownStyles: any;
    theme: any;
    onContentChange: (text: string) => void;
}

type SelectionRange = { start: number; end: number };

// Aplica un wrapper alrededor de la selección o inserta al inicio de la línea
function applyInline(content: string, sel: SelectionRange, before: string, after = before): [string, SelectionRange] {
    const pre = content.slice(0, sel.start);
    const mid = content.slice(sel.start, sel.end);
    const post = content.slice(sel.end);

    // Toggle: si ya está envuelto, quitar; si no, añadir
    if (mid.startsWith(before) && mid.endsWith(after)) {
        const newMid = mid.slice(before.length, mid.length - after.length);
        const newContent = pre + newMid + post;
        return [newContent, { start: sel.start, end: sel.start + newMid.length }];
    }
    const newMid = before + mid + after;
    const newContent = pre + newMid + post;
    return [newContent, { start: sel.start + before.length, end: sel.start + before.length + mid.length }];
}

// Inserta un prefijo al inicio de la línea actual
function applyLinePrefix(content: string, sel: SelectionRange, prefix: string): [string, SelectionRange] {
    const lineStart = content.lastIndexOf('\n', sel.start - 1) + 1;
    const lineEnd = content.indexOf('\n', sel.end);
    const actualLineEnd = lineEnd === -1 ? content.length : lineEnd;

    const line = content.slice(lineStart, actualLineEnd);

    let newLine: string;
    let cursorDelta: number;
    if (line.startsWith(prefix)) {
        newLine = line.slice(prefix.length);
        cursorDelta = -prefix.length;
    } else {
        newLine = prefix + line;
        cursorDelta = prefix.length;
    }

    const newContent = content.slice(0, lineStart) + newLine + content.slice(actualLineEnd);
    return [
        newContent,
        { start: sel.start + cursorDelta, end: sel.end + cursorDelta },
    ];
}

export const MarkdownEditor: React.FC<Props> = ({ content, markdownStyles, theme, onContentChange }) => {
    const [editOpen, setEditOpen] = useState(false);
    const [editContent, setEditContent] = useState(content);
    const [selection, setSelection] = useState<SelectionRange>({ start: 0, end: 0 });
    const inputRef = useRef<TextInput>(null);

    const openEdit = () => {
        setEditContent(content);
        setEditOpen(true);
    };

    const closeEdit = () => {
        setEditOpen(false);
        onContentChange(editContent);
    };

    const handleSelectionChange = useCallback(
        (e: NativeSyntheticEvent<TextInputSelectionChangeEventData>) => {
            setSelection(e.nativeEvent.selection);
        },
        []
    );

    // Herramientas de formato
    const applyBold = () => {
        const [nc, ns] = applyInline(editContent, selection, '**');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyItalic = () => {
        const [nc, ns] = applyInline(editContent, selection, '*');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyCode = () => {
        const [nc, ns] = applyInline(editContent, selection, '`');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyH1 = () => {
        const [nc, ns] = applyLinePrefix(editContent, selection, '# ');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyH2 = () => {
        const [nc, ns] = applyLinePrefix(editContent, selection, '## ');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyBullet = () => {
        const [nc, ns] = applyLinePrefix(editContent, selection, '- ');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyTask = () => {
        const [nc, ns] = applyLinePrefix(editContent, selection, '- [ ] ');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyQuote = () => {
        const [nc, ns] = applyLinePrefix(editContent, selection, '> ');
        setEditContent(nc);
        setSelection(ns);
    };
    const applyHR = () => {
        const ins = '\n---\n';
        const nc = editContent.slice(0, selection.end) + ins + editContent.slice(selection.end);
        setEditContent(nc);
        const pos = selection.end + ins.length;
        setSelection({ start: pos, end: pos });
    };

    const ToolBtn = ({ icon, onPress, label }: { icon: React.ReactNode; onPress: () => void; label: string }) => (
        <TouchableOpacity onPress={onPress} style={styles.toolBtn} accessibilityLabel={label}>
            {icon}
        </TouchableOpacity>
    );

    return (
        <>
            {/* Vista renderizada - siempre visible, toca para editar */}
            <TouchableOpacity onPress={openEdit} activeOpacity={0.9} style={styles.renderedArea}>
                <MarkdownWithTasks
                    content={content}
                    markdownStyles={markdownStyles}
                    theme={theme}
                    onContentChange={onContentChange}
                />
                <View style={[styles.editHint, { backgroundColor: theme.primary + '15', borderColor: theme.primary + '40' }]}>
                    <Text style={[styles.editHintText, { color: theme.primary }]}>✏️ Toca para editar</Text>
                </View>
            </TouchableOpacity>

            {/* Modal de edición */}
            <Modal
                visible={editOpen}
                animationType="slide"
                onRequestClose={closeEdit}
            >
                <KeyboardAvoidingView
                    style={[styles.editorRoot, { backgroundColor: theme.background }]}
                    behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                >
                    {/* Editor Header */}
                    <View style={[styles.editorHeader, { borderBottomColor: theme.border, backgroundColor: theme.surface }]}>
                        <TouchableOpacity onPress={closeEdit} style={styles.editorHeaderBtn}>
                            <X size={22} color={theme.text} />
                        </TouchableOpacity>
                        <Text style={[styles.editorHeaderTitle, { color: theme.text }]}>Editar nota</Text>
                        <TouchableOpacity onPress={closeEdit} style={[styles.editorHeaderBtn, { backgroundColor: theme.primary }]}>
                            <Check size={20} color="#fff" />
                        </TouchableOpacity>
                    </View>

                    {/* Toolbar */}
                    <View style={[styles.toolbar, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.toolbarInner}>
                            <ToolBtn icon={<Bold size={18} color={theme.text} />} onPress={applyBold} label="Negrita" />
                            <ToolBtn icon={<Italic size={18} color={theme.text} />} onPress={applyItalic} label="Cursiva" />
                            <ToolBtn icon={<Code size={18} color={theme.text} />} onPress={applyCode} label="Código" />
                            <View style={[styles.toolSep, { backgroundColor: theme.border }]} />
                            <ToolBtn icon={<Heading1 size={18} color={theme.text} />} onPress={applyH1} label="H1" />
                            <ToolBtn icon={<Heading2 size={18} color={theme.text} />} onPress={applyH2} label="H2" />
                            <View style={[styles.toolSep, { backgroundColor: theme.border }]} />
                            <ToolBtn icon={<List size={18} color={theme.text} />} onPress={applyBullet} label="Lista" />
                            <ToolBtn icon={<CheckSquare size={18} color={theme.text} />} onPress={applyTask} label="Tarea" />
                            <ToolBtn icon={<Quote size={18} color={theme.text} />} onPress={applyQuote} label="Cita" />
                            <ToolBtn icon={<Minus size={18} color={theme.text} />} onPress={applyHR} label="Separador" />
                        </ScrollView>
                    </View>

                    {/* Text Input */}
                    <ScrollView style={{ flex: 1 }} keyboardShouldPersistTaps="handled">
                        <TextInput
                            ref={inputRef}
                            style={[styles.editorInput, { color: theme.text }]}
                            value={editContent}
                            onChangeText={setEditContent}
                            onSelectionChange={handleSelectionChange}
                            selection={selection}
                            multiline
                            autoCorrect={false}
                            autoCapitalize="sentences"
                            textAlignVertical="top"
                            placeholder="Escribe tu nota en Markdown..."
                            placeholderTextColor={theme.textMuted}
                            scrollEnabled={false}
                        />
                    </ScrollView>
                </KeyboardAvoidingView>
            </Modal>
        </>
    );
};

const styles = StyleSheet.create({
    renderedArea: {
        gap: 12,
    },
    editHint: {
        alignSelf: 'flex-start',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: borderRadius.lg,
        borderWidth: 1,
        marginTop: 8,
    },
    editHintText: {
        fontSize: 12,
        fontWeight: '500',
    },
    editorRoot: {
        flex: 1,
        paddingTop: Platform.OS === 'ios' ? 44 : 0,
    },
    editorHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        borderBottomWidth: 1,
    },
    editorHeaderBtn: {
        padding: 8,
        borderRadius: borderRadius.md,
    },
    editorHeaderTitle: {
        fontSize: 16,
        fontWeight: '600',
    },
    toolbar: {
        borderBottomWidth: 1,
    },
    toolbarInner: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: spacing.sm,
        paddingVertical: 6,
        gap: 4,
    },
    toolBtn: {
        padding: 8,
        borderRadius: borderRadius.sm,
    },
    toolSep: {
        width: 1,
        height: 20,
        marginHorizontal: 4,
    },
    editorInput: {
        flex: 1,
        fontSize: 16,
        lineHeight: 26,
        padding: spacing.lg,
        fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
        minHeight: 400,
    },
});
