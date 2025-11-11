'use client';

import React from 'react';
import { Editor } from '@tiptap/react';
import { Bold, Italic, Strikethrough, Code, Heading1, Heading2, List, ListOrdered, Quote, CheckSquare, Table as TableIcon, Rows3, Columns3, MinusSquare, Trash2, Image as ImageIcon } from 'lucide-react';
import { Button } from './ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { Mic, Loader2 } from 'lucide-react';

interface TiptapToolbarProps {
  editor: Editor | null;
  isRecording?: boolean;
  isProcessingAudio?: boolean;
  onStartRecording?: () => void;
  onStopRecording?: () => void;
  onImageUpload?: () => void;
}

export const TiptapToolbar = ({ editor, isRecording, isProcessingAudio, onStartRecording, onStopRecording, onImageUpload }: TiptapToolbarProps) => {
  if (!editor) return null;

  return (
    <TooltipProvider>
      <div className="p-2 flex flex-wrap gap-1 bg-card/80 backdrop-blur-xl border-b rounded-t-md">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            if (isRecording) {
              onStopRecording?.();
            } else {
              onStartRecording?.();
            }
          }}
          disabled={isProcessingAudio}
          className={`rounded-md ${isRecording ? 'text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}`}
        >
          {isProcessingAudio ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
        </Button>
        <Button variant={editor.isActive('bold') ? 'secondary' : 'ghost'} size="sm" onClick={() => editor.chain().focus().toggleBold().run()}><Bold className="h-4 w-4" /></Button>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="sm" onClick={() => onImageUpload?.()}><ImageIcon className="h-4 w-4" /></Button>
          </TooltipTrigger>
          <TooltipContent>Insertar imagen</TooltipContent>
        </Tooltip>
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
        {editor.isActive('table') && (
          <>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().addRowBefore().run()}><Rows3 className="h-4 w-4" /></Button>
              </TooltipTrigger>
              <TooltipContent>Añadir fila antes</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().addRowAfter().run()}><Rows3 className="h-4 w-4 rotate-180" /></Button>
              </TooltipTrigger>
              <TooltipContent>Añadir fila después</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().deleteRow().run()}><MinusSquare className="h-4 w-4" /></Button>
              </TooltipTrigger>
              <TooltipContent>Borrar fila</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().addColumnBefore().run()}><Columns3 className="h-4 w-4" /></Button>
              </TooltipTrigger>
              <TooltipContent>Añadir columna antes</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().addColumnAfter().run()}><Columns3 className="h-4 w-4 rotate-180" /></Button>
              </TooltipTrigger>
              <TooltipContent>Añadir columna después</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().deleteColumn().run()}><MinusSquare className="h-4 w-4 rotate-90" /></Button>
              </TooltipTrigger>
              <TooltipContent>Borrar columna</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" onClick={() => editor.chain().focus().deleteTable().run()}><Trash2 className="h-4 w-4" /></Button>
              </TooltipTrigger>
              <TooltipContent>Borrar tabla</TooltipContent>
            </Tooltip>
          </>
        )}
      </div>
    </TooltipProvider>
  );
};