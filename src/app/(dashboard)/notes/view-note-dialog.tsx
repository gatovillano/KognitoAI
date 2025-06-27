// En: src/app/(dashboard)/notes/view-note-dialog.tsx

'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MarkdownRenderer } from '@/components/MarkdownRenderer'; // Reutilizamos nuestro potente renderizador
import type { Note } from './page'; // Importamos el tipo de dato 'Note' desde la página principal

interface ViewNoteDialogProps {
  note: Note | null; // La nota a mostrar. Si es null, el diálogo no se muestra o está vacío.
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ViewNoteDialog({ note, isOpen, onOpenChange }: ViewNoteDialogProps) {
  // Si no hay nota para mostrar, no renderizamos nada para evitar errores.
  if (!note) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl sm:max-w-3xl">
        <DialogHeader className="pr-6"> {/* Añadimos padding a la derecha para que no se pegue al botón de cerrar */}
          <DialogTitle className="text-2xl">{note.title || "Nota sin título"}</DialogTitle>
          <DialogDescription>
            En la categoría: <span className="font-semibold text-primary">{note.category}</span>
            {' | '}
            Creada el: {new Date(note.created_at).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}
          </DialogDescription>
        </DialogHeader>
        
        {/* Usamos ScrollArea para que el contenido de la nota sea navegable si es muy largo */}
        <ScrollArea className="max-h-[65vh] mt-4 pr-6">
          <div className="py-4">
            {/* Aquí está la magia: usamos el MarkdownRenderer que ya creamos */}
            <MarkdownRenderer content={note.content} />
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}