'use client';

import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Mention from '@tiptap/extension-mention';
import { Markdown } from 'tiptap-markdown';
import { Button } from './ui/button';
import { Table } from '@tiptap/extension-table';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import TableRow from '@tiptap/extension-table-row';
import { createMentionSuggestion } from './mention-suggestion';
import { TiptapToolbar as Toolbar } from './TiptapToolbar';
import Image from '@tiptap/extension-image';

interface TiptapEditorProps {
  content: string;
  onChange: (html: string) => void;
  fromTeam?: string;
  containerClassName?: string;
  isRecording?: boolean;
  isProcessingAudio?: boolean;
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  onImageUpload?: () => void;
  onInsertContent?: (insertFn: (text: string) => void) => void;
}

export const TiptapEditor = ({ content, onChange, fromTeam, containerClassName, isRecording, isProcessingAudio, onStartRecording, onStopRecording, onImageUpload, onInsertContent }: TiptapEditorProps) => {
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
      Image.configure({
        inline: true,
        allowBase64: false,
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
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      debounceTimeoutRef.current = setTimeout(() => {
        onChange((editor.storage as any).markdown.getMarkdown());
      }, 250);
    },
    onDestroy() {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    },
    immediatelyRender: false,
  });

  const handleImageUpload = React.useCallback(async (file: File) => {
    if (!editor) return;

    const toastId = "upload-image";
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/notes/upload-image', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al subir la imagen');
      }

      const data = await response.json();
      editor.chain().focus().setImage({ src: data.url }).run();
    } catch (error) {
      console.error('Error uploading image:', error);
    }
  }, [editor]);

  const handleImageButtonClick = React.useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleImageUpload(file);
      }
    };
    input.click();
  }, [handleImageUpload]);


  React.useEffect(() => {
    if (editor && onInsertContent) {
      onInsertContent((text: string) => {
        editor.commands.insertContent(text);
      });
    }
  }, [editor, onInsertContent]);

  return (
    <div className={containerClassName}>
      <div className="flex flex-col flex-grow rounded-lg border border-border/20">
        <div className="sticky top-0 z-10 p-2 flex flex-wrap gap-1 bg-card/80 backdrop-blur-xl border-b rounded-t-lg">
          <Toolbar
            editor={editor}
            isRecording={isRecording}
            isProcessingAudio={isProcessingAudio}
            onStartRecording={onStartRecording}
            onStopRecording={onStopRecording}
            onImageUpload={handleImageButtonClick}
          />
        </div>
        <div className="flex-1 overflow-y-auto rounded-b-lg">
          <EditorContent editor={editor} className="p-4" />
        </div>
      </div>
    </div>
  );
};