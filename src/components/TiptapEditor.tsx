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
}

// --- El Editor Principal ---
export const TiptapEditor = ({ content, onChange, fromTeam, containerClassName }: TiptapEditorProps) => {
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
        class: `prose dark:prose-invert max-w-full rounded-b-md p-4 focus:outline-none`,
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

  return (
    <div className={containerClassName}> {/* Aplicar containerClassName aquí */}
      <div className="flex flex-col flex-grow"> {/* Contenedor principal del editor con flex y altura flexible */}
        <div className="sticky top-0 z-10 p-2 flex flex-wrap gap-1 bg-background border-b rounded-md rounded-b-none"> {/* Contenedor de la barra de herramientas sticky */}
          <Toolbar editor={editor} />
        </div>
        <div className="flex-1 overflow-y-auto"> {/* Contenedor del contenido con scroll */}
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  );
};