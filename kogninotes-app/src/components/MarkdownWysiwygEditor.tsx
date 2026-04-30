// src/components/MarkdownWysiwygEditor.tsx
import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Modal,
    Platform,
    KeyboardAvoidingView,
    ActivityIndicator,
} from 'react-native';
import { WebView } from 'react-native-webview';
import {
    Bold,
    Italic,
    Heading1,
    Heading2,
    List,
    CheckSquare,
    Code,
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

export const MarkdownWysiwygEditor: React.FC<Props> = ({ content, markdownStyles, theme, onContentChange }) => {
    const [editOpen, setEditOpen] = useState(false);
    const [loading, setLoading] = useState(true);
    const webViewRef = useRef<WebView>(null);
    const [localContent, setLocalContent] = useState(content);

    // HTML del editor visual (basado en un simple editor Markdown WYSIWYG)
    const editorHtml = `
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css">
        <script src="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js"></script>
        <style>
            body { margin: 0; padding: 0; background: ${theme.background}; color: ${theme.text}; font-family: -apple-system, system-ui; }
            .EasyMDEContainer .CodeMirror { border: none; height: 100vh; background: ${theme.background}; color: ${theme.text}; font-size: 16px; padding: 15px; }
            .cm-header-1 { font-size: 24px; color: ${theme.primary}; }
            .cm-header-2 { font-size: 20px; }
            .cm-strong { font-weight: bold; }
            .cm-em { font-style: italic; }
            .editor-toolbar { display: none; } /* Ocultamos la nativa de EasyMDE para usar la nuestra */
            .CodeMirror-cursor { border-left: 2px solid ${theme.primary}; }
            .CodeMirror-selected { background: ${theme.primary}40 !important; }
        </style>
    </head>
    <body>
        <textarea id="editor"></textarea>
        <script>
            const easyMDE = new EasyMDE({
                element: document.getElementById('editor'),
                initialValue: ${JSON.stringify(content)},
                spellChecker: false,
                status: false,
                autofocus: true,
                toolbar: false,
            });

            easyMDE.codemirror.on('change', () => {
                const value = easyMDE.value();
                window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'change', value: value }));
            });

            // Escuchar comandos de la barra de herramientas nativa
            window.addEventListener('message', (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'command') {
                    easyMDE.toggleBlock(data.command);
                } else if (data.type === 'inline') {
                    easyMDE.toggleLine(data.command);
                }
            });
        </script>
    </body>
    </html>
    `;

    const openEdit = () => {
        setLocalContent(content);
        setEditOpen(true);
        setLoading(true);
    };

    const closeEdit = () => {
        setEditOpen(false);
        onContentChange(localContent);
    };

    const onMessage = (event: any) => {
        try {
            const data = JSON.parse(event.nativeEvent.data);
            if (data.type === 'change') {
                setLocalContent(data.value);
            }
        } catch (e) {
            console.error(e);
        }
    };

    const runCommand = (cmd: string, type: 'command' | 'inline' = 'command') => {
        webViewRef.current?.postMessage(JSON.stringify({ type, command: cmd }));
    };

    const ToolBtn = ({ icon, onPress }: { icon: React.ReactNode; onPress: () => void }) => (
        <TouchableOpacity onPress={onPress} style={styles.toolBtn}>
            {icon}
        </TouchableOpacity>
    );

    return (
        <>
            <TouchableOpacity onPress={openEdit} activeOpacity={0.9} style={styles.renderedArea}>
                <MarkdownWithTasks
                    content={content}
                    markdownStyles={markdownStyles}
                    theme={theme}
                    onContentChange={onContentChange}
                />
                <View style={[styles.editHint, { backgroundColor: theme.primary + '15', borderColor: theme.primary + '40' }]}>
                    <Text style={[styles.editHintText, { color: theme.primary }]}>✏️ Editar nota con formato rico</Text>
                </View>
            </TouchableOpacity>

            <Modal visible={editOpen} animationType="slide">
                <SafeAreaView style={[styles.editorRoot, { backgroundColor: theme.background }]}>
                    <View style={[styles.editorHeader, { borderBottomColor: theme.border, backgroundColor: theme.surface }]}>
                        <TouchableOpacity onPress={closeEdit} style={styles.editorHeaderBtn}>
                            <X size={22} color={theme.text} />
                        </TouchableOpacity>
                        <Text style={[styles.editorHeaderTitle, { color: theme.text }]}>Editor Rico</Text>
                        <TouchableOpacity onPress={closeEdit} style={[styles.editorHeaderBtn, { backgroundColor: theme.primary }]}>
                            <Check size={20} color="#fff" />
                        </TouchableOpacity>
                    </View>

                    <View style={{ flex: 1 }}>
                        <WebView
                            ref={webViewRef}
                            source={{ html: editorHtml }}
                            onMessage={onMessage}
                            onLoadEnd={() => setLoading(false)}
                            keyboardDisplayRequiresUserAction={false}
                            hideKeyboardAccessoryView={true}
                            style={{ backgroundColor: theme.background }}
                        />
                        {loading && (
                            <View style={[StyleSheet.absoluteFill, { backgroundColor: theme.background, justifyContent: 'center' }]}>
                                <ActivityIndicator size="large" color={theme.primary} />
                            </View>
                        )}
                    </View>

                    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
                        <View style={[styles.toolbar, { backgroundColor: theme.surface, borderTopColor: theme.border }]}>
                            <View style={styles.toolbarInner}>
                                <ToolBtn icon={<Bold size={20} color={theme.text} />} onPress={() => runCommand('bold')} />
                                <ToolBtn icon={<Italic size={20} color={theme.text} />} onPress={() => runCommand('italic')} />
                                <View style={[styles.toolSep, { backgroundColor: theme.border }]} />
                                <ToolBtn icon={<Heading1 size={20} color={theme.text} />} onPress={() => runCommand('heading-1')} />
                                <ToolBtn icon={<Heading2 size={20} color={theme.text} />} onPress={() => runCommand('heading-2')} />
                                <View style={[styles.toolSep, { backgroundColor: theme.border }]} />
                                <ToolBtn icon={<List size={20} color={theme.text} />} onPress={() => runCommand('unordered-list')} />
                                <ToolBtn icon={<CheckSquare size={20} color={theme.text} />} onPress={() => runCommand('task-list', 'inline')} />
                            </View>
                        </View>
                    </KeyboardAvoidingView>
                </SafeAreaView>
            </Modal>
        </>
    );
};

// Importar SafeAreaView si no está arriba
import { SafeAreaView } from 'react-native-safe-area-context';

const styles = StyleSheet.create({
    renderedArea: { gap: 12 },
    editHint: { alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: borderRadius.lg, borderWidth: 1, marginTop: 8 },
    editHintText: { fontSize: 12, fontWeight: '500' },
    editorRoot: { flex: 1 },
    editorHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1 },
    editorHeaderBtn: { padding: 8, borderRadius: borderRadius.md },
    editorHeaderTitle: { fontSize: 16, fontWeight: '600' },
    toolbar: { borderTopWidth: 1, paddingBottom: Platform.OS === 'ios' ? 20 : 0 },
    toolbarInner: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: spacing.sm, paddingVertical: 10, gap: 12, justifyContent: 'center' },
    toolBtn: { padding: 8, borderRadius: borderRadius.sm },
    toolSep: { width: 1, height: 20, marginHorizontal: 4 },
});
