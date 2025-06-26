// En: src/app/(dashboard)/notes/view-note-dialog.tsx
'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import type { Note } from './page';

interface ViewNoteDialogProps {
  note: Note | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ViewNoteDialog({ note, isOpen, onOpenChange }: ViewNoteDialogProps) {
  if (!note) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{note.title || "Nota sin título"}</DialogTitle>
          <DialogDescription>
            Categoría: {note.category} | Creada el: {new Date(note.created_at).toLocaleDateString()}
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] pr-4">
          <div className="py-4">
            <MarkdownRenderer content={note.content} />
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
