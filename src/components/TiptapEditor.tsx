'use client';

import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Mention from '@tiptap/extension-mention';
import { Markdown } from 'tiptap-markdown';
import { Bold, Italic, Strikethrough, Code, Heading1, Heading2, List, ListOrdered, Quote, CheckSquare, Table as TableIcon } from 'lucide-react';
import { Button } from './ui/button';
import Table from '@tiptap/extension-table';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import TableRow from '@tiptap/extension-table-row';
import { createMentionSuggestion } from './mention-suggestion';
import { TiptapToolbar as Toolbar } from './TiptapToolbar';


interface TiptapEditorProps {
  content: string;
  onChange: (html: string) => void;
  fromTeam?: string; // Cambiado a string | undefined
  containerClassName?: string; // Nueva propiedad
  isRecording?: boolean;
  isProcessingAudio?: boolean;
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  onInsertContent?: (text: string) => void; // Nueva prop para insertar contenido
}

// --- El Editor Principal ---
export const TiptapEditor = ({ content, onChange, fromTeam, containerClassName, isRecording, isProcessingAudio, onStartRecording, onStopRecording, onInsertContent }: TiptapEditorProps) => {
  const debounceTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const editor = useEditor({
    extensions: [
      StarterKit,
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      Mention.configure({
        HTMLAttributes: {
          class: 'mention',
          target: '_blank',
          rel: 'noopener noreferrer',
        },
        renderHTML({ node, options }) {
          return [
            'a',
            { href: `/notes/edit/${node.attrs.id}`, ...options.HTMLAttributes },
            `@${node.attrs.label ?? node.attrs.id}`,
          ]
        },
        suggestion: createMentionSuggestion(fromTeam),
      }),
      Markdown.configure({
        html: false,
      }),
    ],
    content: content,
    editorProps: {
      attributes: {
        class: `prose dark:prose-invert max-w-full rounded-b-lg p-4 focus:outline-none border-b border-l border-r border-border/20`,
      },
    },
    onUpdate({ editor }) {
      // Debounce the onChange call to prevent performance issues on frequent updates
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      debounceTimeoutRef.current = setTimeout(() => {
        onChange(editor.storage.markdown.getMarkdown()); // Tiptap ahora trabaja con Markdown
      }, 250);
    },
    onDestroy() {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    },
  });

  // Exponer la función de inserción de contenido
  React.useEffect(() => {
    if (editor && onInsertContent) {
      onInsertContent((text: string) => {
        editor.commands.insertContent(text);
      });
    }
  }, [editor, onInsertContent]);

  return (
    <div className={containerClassName}> {/* Aplicar containerClassName aquí */}
      <div className="flex flex-col flex-grow rounded-lg border border-border/20"> {/* Contenedor principal del editor con bordes curvos */}
        <div className="sticky top-0 z-10 p-2 flex flex-wrap gap-1 bg-card/80 backdrop-blur-xl border-b rounded-t-lg"> {/* Contenedor de la barra de herramientas sticky */}
          <Toolbar
            editor={editor}
            isRecording={isRecording}
            isProcessingAudio={isProcessingAudio}
            onStartRecording={onStartRecording}
            onStopRecording={onStopRecording}
          />
        </div>
        <div className="flex-1 overflow-y-auto rounded-b-lg"> {/* Contenedor del contenido con scroll y bordes curvos */}
          <EditorContent editor={editor} className="p-4" /> {/* Añadido padding */} 
        </div>
      </div>
    </div>
  );
};