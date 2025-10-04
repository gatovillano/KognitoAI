'use client';

import React from 'react';
import { Editor } from '@tiptap/react';
import { Bold, Italic, Strikethrough, Code, Heading1, Heading2, List, ListOrdered, Quote, CheckSquare, Table as TableIcon } from 'lucide-react';
import { Button } from './ui/button';

interface TiptapToolbarProps {
  editor: Editor | null;
}

export const TiptapToolbar = ({ editor }: TiptapToolbarProps) => {
  if (!editor) return null;

  return (
    <div className="p-2 flex flex-wrap gap-1 bg-card/80 backdrop-blur-xl border-b">
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
      <Button variant={editor.isActive('table') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}><TableIcon className="h-4 w-4" /></Button>
    </div>
  );
};