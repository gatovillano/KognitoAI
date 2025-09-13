// En: src/app/(dashboard)/notes/view-note-dialog.tsx

'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button'; // Importar Button
import { Volume2, Pencil, Lightbulb, FileText, MoreHorizontal } from 'lucide-react'; // Importar el icono de volumen y el de lápiz
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import { MarkdownRenderer } from '@/components/MarkdownRenderer'; // Reutilizamos nuestro potente renderizador
import { useState } from 'react'; // Importar useState
import apiClient from '@/lib/api'; // Importar apiClient
import { NoteDialog } from './note-dialog'; // Importar NoteDialog para la edición
import type { Note } from './page'; // Importamos el tipo de dato 'Note' desde la página principal

interface ViewNoteDialogProps {
  note: Note | null; // La nota a mostrar. Si es null, el diálogo no se muestra o está vacío.
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onNoteUpdated: () => void; // Callback para cuando la nota se actualiza
}

export function ViewNoteDialog({ note, isOpen, onOpenChange, onNoteUpdated }: ViewNoteDialogProps) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isNoteEditDialogOpen, setIsNoteEditDialogOpen] = useState(false); // Estado para el diálogo de edición

  const handleSummarizeSingleNoteFromDialog = async () => {
    if (!note) return;
    const toastId = toast.loading("Iniciando resumen de la nota...");
    try {
      const response = await apiClient.post('/api/start-single-note-summary', {
        title: note.title || "Nota sin título",
        content: note.content,
        note_id: note.id
      });
      toast.success(`Resumen de nota iniciado. ID de tarea: ${response.data.task_id}`, { id: toastId });
    } catch (error) {
      toast.error("Error al iniciar el resumen de la nota.", { id: toastId });
      console.error("Error al iniciar el resumen de la nota:", error);
    }
  };

  const handleAnalyzeSingleNoteFromDialog = async () => {
    if (!note) return;
    const toastId = toast.loading("Iniciando análisis de la nota...");
    try {
      // Aquí iría la lógica para analizar la nota
      console.log("Analizar nota desde el diálogo:", note.id);
      toast.success("Análisis de nota iniciado.", { id: toastId });
    } catch (error) {
      toast.error("Error al iniciar el análisis de la nota.", { id: toastId });
      console.error("Error al iniciar el análisis de la nota:", error);
    }
  };

  const handleTextToSpeech = async () => {
    if (!note || !note.content) return;

    setIsSpeaking(true);
    try {
      const response = await apiClient.post('/api/text-to-speech', { text: note.content }, {
        responseType: 'blob', // Importante para manejar la respuesta como un blob de audio
      });

      const audioBlob = new Blob([response.data], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      audio.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = (e) => {
        console.error('Error al reproducir el audio:', e);
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
        alert('Error al reproducir el audio.');
      };

      audio.play();
    } catch (error) {
      console.error('Error al generar el audio:', error);
      setIsSpeaking(false);
      alert('Error al generar el audio.');
    }
  };

  // Si no hay nota para mostrar, no renderizamos nada para evitar errores.
  if (!note) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl sm:max-w-3xl">
        <DialogHeader className="pr-6"> {/* Añadimos padding a la derecha para que no se pegue al botón de cerrar */}
          <div className="flex justify-between items-center">
            <DialogTitle className="text-2xl">{note.title || "Nota sin título"}</DialogTitle>
            <div className="flex items-center gap-2"> {/* Contenedor para los botones */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="ml-4">
                    <MoreHorizontal className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[180px]">
                  <DropdownMenuItem onClick={() => setIsNoteEditDialogOpen(true)}>
                    <Pencil className="mr-2 h-4 w-4" />
                    Editar nota
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleAnalyzeSingleNoteFromDialog}>
                    <Lightbulb className="mr-2 h-4 w-4" />
                    Analizar Nota
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleSummarizeSingleNoteFromDialog}>
                    <FileText className="mr-2 h-4 w-4" />
                    Resumen Semántico
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleTextToSpeech} disabled={isSpeaking}>
                    <Volume2 className={isSpeaking ? "mr-2 h-4 w-4 animate-pulse text-primary" : "mr-2 h-4 w-4"} />
                    Reproducir Audio
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
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

      {note && (
        <NoteDialog
          isOpen={isNoteEditDialogOpen}
          onOpenChange={setIsNoteEditDialogOpen}
          onSaveSuccess={() => {
            onNoteUpdated(); // Notificar al padre que la nota se actualizó
            setIsNoteEditDialogOpen(false); // Cerrar el diálogo de edición
          }}
          note={note} // Pasar la nota actual para edición
          workspaceId={note.workspace_id} // Asegurarse de pasar el workspace_id
        />
      )}
    </Dialog>
  );
}