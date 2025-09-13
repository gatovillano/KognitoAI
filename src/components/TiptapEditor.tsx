'use client';

import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Mention from '@tiptap/extension-mention';
import { Bold, Italic, Strikethrough, Code, Heading1, Heading2, List, ListOrdered, Quote, CheckSquare } from 'lucide-react';
import { Button } from './ui/button';
import { mentionSuggestion } from './mention-suggestion';

// --- La Barra de Herramientas ---
const Toolbar = ({ editor }: { editor: any }) => {
  if (!editor) return null;

  return (
    <div className="border rounded-t-md p-2 flex flex-wrap gap-1">
      <Button variant={editor.isActive('bold') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleBold().run()}><Bold className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('italic') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleItalic().run()}><Italic className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('strike') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleStrike().run()}><Strikethrough className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('code') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleCode().run()}><Code className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('heading', { level: 1 }) ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}><Heading1 className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('heading', { level: 2 }) ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}><Heading2 className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('bulletList') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleBulletList().run()}><List className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('orderedList') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleOrderedList().run()}><ListOrdered className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('taskList') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleTaskList().run()}><CheckSquare className="h-4 w-4" /></Button>
      <Button variant={editor.isActive('blockquote') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleBlockquote().run()}><Quote className="h-4 w-4" /></Button>
    </div>
  );
};

// --- El Editor Principal ---
export function TiptapEditor({ content, onChange, containerClassName }: { content: string; onChange: (html: string) => void; containerClassName?: string }) {
  const debounceTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const editor = useEditor({
    extensions: [
      StarterKit,
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
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
        suggestion: mentionSuggestion,
      }),
    ],
    content: content,
    editorProps: {
      attributes: {
        class: `prose dark:prose-invert max-w-full rounded-b-md border p-4 focus:outline-none ${containerClassName || 'min-h-[300px]'}`,
      },
    },
    onUpdate({ editor }) {
      // Debounce the onChange call to prevent performance issues on frequent updates
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      debounceTimeoutRef.current = setTimeout(() => {
        onChange(editor.getHTML()); // Tiptap trabaja con HTML, no con Markdown
      }, 250);
    },
    onDestroy() {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    },
  });

  return (
    <div>
      <Toolbar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
}
