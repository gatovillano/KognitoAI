// src/components/MarkdownWithTasks.tsx
import React, { useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import Markdown from 'react-native-markdown-display';

interface Props {
    content: string;
    markdownStyles?: any;
    theme: any;
    onContentChange?: (newContent: string) => void;
}

/**
 * Segmento de contenido: puede ser un bloque markdown normal
 * o una lista de items de tarea (checkboxes).
 */
type Segment =
    | { type: 'markdown'; text: string }
    | { type: 'tasklist'; items: { checked: boolean; label: string; lineIndex: number }[] };

/**
 * Divide el contenido markdown en segmentos alternados:
 * bloques de markdown puro y bloques de task list.
 */
function parseSegments(content: string): Segment[] {
    const lines = content.split('\n');
    const segments: Segment[] = [];
    let mdBuffer: string[] = [];
    let taskBuffer: { checked: boolean; label: string; lineIndex: number }[] = [];

    const flushMd = () => {
        if (mdBuffer.length > 0) {
            segments.push({ type: 'markdown', text: mdBuffer.join('\n') });
            mdBuffer = [];
        }
    };
    const flushTasks = () => {
        if (taskBuffer.length > 0) {
            segments.push({ type: 'tasklist', items: [...taskBuffer] });
            taskBuffer = [];
        }
    };

    lines.forEach((line, idx) => {
        // Detectar - [ ] o - [x] o * [ ] o * [x]
        const taskMatch = line.match(/^(\s*[-*]\s+)\[( |x|X)\]\s+(.*)/);
        if (taskMatch) {
            flushMd();
            taskBuffer.push({
                checked: taskMatch[2].toLowerCase() === 'x',
                label: taskMatch[3],
                lineIndex: idx,
            });
        } else {
            flushTasks();
            mdBuffer.push(line);
        }
    });

    flushMd();
    flushTasks();

    return segments;
}

export const MarkdownWithTasks: React.FC<Props> = ({
    content,
    markdownStyles,
    theme,
    onContentChange,
}) => {
    const [contentState, setContentState] = useState(content);

    const segments = parseSegments(contentState);

    const handleToggle = useCallback((lineIndex: number, currentChecked: boolean) => {
        const lines = contentState.split('\n');
        const line = lines[lineIndex];
        if (currentChecked) {
            lines[lineIndex] = line.replace(/\[x\]/i, '[ ]');
        } else {
            lines[lineIndex] = line.replace(/\[ \]/, '[x]');
        }
        const newContent = lines.join('\n');
        setContentState(newContent);
        onContentChange?.(newContent);
    }, [contentState, onContentChange]);

    return (
        <View>
            {segments.map((seg, i) => {
                if (seg.type === 'markdown') {
                    return (
                        // @ts-ignore
                        <Markdown key={i} style={markdownStyles}>
                            {seg.text}
                        </Markdown>
                    );
                }

                // Render task list
                return (
                    <View key={i} style={styles.taskList}>
                        {seg.items.map((item) => (
                            <TouchableOpacity
                                key={item.lineIndex}
                                style={styles.taskItem}
                                onPress={() => handleToggle(item.lineIndex, item.checked)}
                                activeOpacity={0.7}
                            >
                                <View style={[
                                    styles.checkbox,
                                    {
                                        borderColor: item.checked ? theme.primary : theme.border,
                                        backgroundColor: item.checked ? theme.primary : 'transparent',
                                    }
                                ]}>
                                    {item.checked && (
                                        <Text style={styles.checkmark}>✓</Text>
                                    )}
                                </View>
                                <Text style={[
                                    styles.taskLabel,
                                    {
                                        color: item.checked ? theme.textMuted : theme.text,
                                        textDecorationLine: item.checked ? 'line-through' : 'none',
                                    }
                                ]}>
                                    {item.label}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                );
            })}
        </View>
    );
};

const styles = StyleSheet.create({
    taskList: {
        marginVertical: 8,
    },
    taskItem: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 6,
        paddingHorizontal: 4,
    },
    checkbox: {
        width: 22,
        height: 22,
        borderRadius: 6,
        borderWidth: 2,
        marginRight: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    checkmark: {
        color: '#fff',
        fontSize: 13,
        fontWeight: 'bold',
        lineHeight: 16,
    },
    taskLabel: {
        fontSize: 16,
        lineHeight: 22,
        flex: 1,
    },
});
