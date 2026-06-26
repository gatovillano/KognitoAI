// En: src/app/(dashboard)/notes/view-note-dialog.tsx

'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button'; // Importar Button
import { Volume2, Pencil, Lightbulb, FileText, MoreHorizontal, Link, Download, FileType, MessageSquare } from 'lucide-react'; // Importar el icono de volumen, el de lápiz, el de enlace y el de descarga
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import { MarkdownRenderer } from '@/components/MarkdownRenderer'; // Reutilizamos nuestro potente renderizador
import { useState, useEffect } from 'react'; // Importar useState y useEffect
import apiClient from '@/lib/api'; // Importar apiClient
import { NoteDialog } from './note-dialog'; // Importar NoteDialog para la edición
import { useRouter } from 'next/navigation'; // Importar useRouter
import type { Note } from './Notes';
import { DialogFooter } from '@/components/ui/dialog'; // Importar DialogFooter
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'; // Importar Select components
import { ContextualChat } from '@/components/ContextualChat';
import { useUserSettings } from '@/contexts/UserSettingsContext';

interface ContactProfile {
  id: string;
  name: string;
}

interface ViewNoteDialogProps {
  note: Note | null; // La nota a mostrar. Si es null, el diálogo no se muestra o está vacío.
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onNoteUpdated: () => void; // Callback para cuando la nota se actualiza
}

export function ViewNoteDialog({ note, isOpen, onOpenChange, onNoteUpdated }: ViewNoteDialogProps) {
  const router = useRouter(); // Hook para navegación
  const { settings } = useUserSettings();
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isNoteEditDialogOpen, setIsNoteEditDialogOpen] = useState(false); // Estado para el diálogo de edición
  const [isLinkProfileDialogOpen, setIsLinkProfileDialogOpen] = useState(false); // Estado para el diálogo de vincular perfil
  const [contactProfiles, setContactProfiles] = useState<ContactProfile[]>([]); // Estado para almacenar los perfiles de contacto
  const [loadingContactProfiles, setLoadingContactProfiles] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null); // Estado para el perfil seleccionado
  const [isChatOpen, setIsChatOpen] = useState(false); // Estado para abrir el chat contextual

  useEffect(() => {
    const fetchContactProfiles = async () => {
      setLoadingContactProfiles(true);
      try {
        const response = await apiClient.get('/api/contact-profiles');
        // Asumimos que la API devuelve un array de perfiles directamente
        if (Array.isArray(response.data)) {
          setContactProfiles(response.data);
        } else {
          console.error("API /api/contact-profiles did not return an array:", response.data);
          setContactProfiles([]);
        }
      } catch (error) {
        console.error("Error fetching contact profiles:", error);
        toast.error('Error al cargar los perfiles de contacto.');
      } finally {
        setLoadingContactProfiles(false);
      }
    };

    if (isLinkProfileDialogOpen) {
      fetchContactProfiles();
    }
  }, [isLinkProfileDialogOpen]);

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
      // Construir payload con configuración TTS del usuario
      const ttsPayload: any = { text: note.content };

      // Si el usuario tiene configuración TTS personalizada, usarla
      if (settings) {
        if (settings.tts_provider) {
          ttsPayload.provider = settings.tts_provider;
        }
        if (settings.tts_voice) {
          ttsPayload.voice = settings.tts_voice;
        }
        if (settings.tts_speed) {
          ttsPayload.speed = settings.tts_speed;
        }
        if (settings.tts_region) {
          ttsPayload.region = settings.tts_region;
        }
      }

      const response = await apiClient.post('/api/text-to-speech', ttsPayload, {
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

  const handleLinkToProfile = () => {
    setIsLinkProfileDialogOpen(true); // Abrir el diálogo de selección de perfil
  };

  const handleConfirmLinkToProfile = async () => {
    if (!note || !selectedProfileId) return;

    const toastId = toast.loading("Vinculando nota a perfil...");
    try {
      await apiClient.post(`/api/contact-profiles/${selectedProfileId}/link-note`, {
        note_id: note.id,
      });
      toast.success("Nota vinculada exitosamente al perfil.", { id: toastId });
      setIsLinkProfileDialogOpen(false); // Cerrar el diálogo
      setSelectedProfileId(null); // Resetear la selección
      onNoteUpdated(); // Opcional: para refrescar la UI si es necesario
    } catch (error) {
      toast.error("Error al vincular la nota a perfil.", { id: toastId });
      console.error("Error al vincular la nota a perfil:", error);
    }
  };

  const handleDownloadPdf = async () => {
    if (!note) {
      toast.error("No hay nota para descargar.");
      return;
    }
    const toastId = toast.loading("Generando PDF...");
    try {
      const response = await apiClient.post(
        '/api/notes/generate-pdf',
        { note_id: note.id, format: 'markdown' }, // Puedes ajustar el formato si el backend lo permite
        { responseType: 'blob' } // Importante para recibir el archivo como blob
      );

      // Crear un blob a partir de la respuesta
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);

      // Crear un enlace temporal y simular un click para descargar el archivo
      const a = document.createElement('a');
      a.href = url;
      a.download = `${note.title || 'nota-sin-titulo'}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      toast.success("PDF generado y descargado.", { id: toastId });
    } catch (error) {
      toast.error("Error al generar el PDF.", { id: toastId });
      console.error("Error al generar el PDF:", error);
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
              <Button size="sm" className="gap-2 ml-4" onClick={() => setIsChatOpen(true)}>
                <MessageSquare className="h-4 w-4" />
                Chat IA
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <MoreHorizontal className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[180px]">
                  <DropdownMenuItem onClick={() => setIsNoteEditDialogOpen(true)}>
                    <Pencil className="mr-2 h-4 w-4" />
                    Editar nota
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setIsChatOpen(true)}>
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Chatear con Nota
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
                  <DropdownMenuItem onClick={handleLinkToProfile}>
                    <Link className="mr-2 h-4 w-4" />
                    Vincular a Perfil
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleDownloadPdf}>
                    <Download className="mr-2 h-4 w-4" />
                    Descargar PDF
                  </DropdownMenuItem>

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
          <div className="py-4 text-xl">
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

      {/* Diálogo para vincular a perfil */}
      <Dialog open={isLinkProfileDialogOpen} onOpenChange={setIsLinkProfileDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Vincular Nota a Perfil</DialogTitle>
            <DialogDescription>
              Selecciona un perfil de contacto para vincular esta nota.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Select onValueChange={setSelectedProfileId} value={selectedProfileId || ""} disabled={loadingContactProfiles}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder={loadingContactProfiles ? "Cargando perfiles..." : "Selecciona un perfil"} />
              </SelectTrigger>
              <SelectContent>
                {contactProfiles.length === 0 && !loadingContactProfiles ? (
                  <SelectItem value="" disabled>No hay perfiles disponibles</SelectItem>
                ) : (
                  contactProfiles.map((profile) => (
                    <SelectItem key={profile.id} value={profile.id}>
                      {profile.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsLinkProfileDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleConfirmLinkToProfile} disabled={!selectedProfileId}>Vincular</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {note && (
        <ContextualChat
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          title={note.title || "Nota sin título"}
          context={{
            type: 'note',
            id: note.id.toString(),
            snapshot: {
              title: note.title || "Nota sin título",
              content: note.content,
              category: note.category,
            }
          }}
        />
      )}
    </Dialog>
  );
}