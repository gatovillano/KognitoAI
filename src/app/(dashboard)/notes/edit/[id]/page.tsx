// En: src/app/(dashboard)/notes/edit/[id]/page.tsx
'use client';

import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { TiptapEditor } from '@/components/TiptapEditor'; // Importamos el editor
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Save, Mic, Loader2 } from 'lucide-react';
import { marked } from 'marked'; // Librería para convertir Markdown a HTML
import { useAudioRecorder } from '@/hooks/useAudioRecorder'; // Importar el hook de grabación de audio

export default function EditNotePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const noteId = (params?.id as string) || '';
  const fromTeam = searchParams?.get('fromTeam');

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [content, setContent] = useState(''); // El contenido será Markdown
  const [isLoading, setIsLoading] = useState(true);
  const [isShared, setIsShared] = useState(false);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
          const [teams, setTeams] = useState<any[]>([]);
          const { isRecording, isProcessingAudio, transcript, startRecording, stopRecording, clearTranscript } = useAudioRecorder();
          const insertContentRef = useRef<((text: string) => void) | null>(null); // Ref para la función de inserción de contenido del editor
        
          useEffect(() => {
            const fetchNote = async () => {
              setIsLoading(true);
              if (noteId && noteId !== 'new') {
                try {
                  let note;
                  if (fromTeam) {
                    const response = await apiClient.get(`/api/teams/${fromTeam}/shared-items`);
                    note = response.data.find((n: { id: number, type: string }) => n.id === parseInt(noteId) && n.type === 'note');
                  } else {
                    try {
                      const directResponse = await apiClient.get(`/api/notes/${noteId}`);
                      note = directResponse.data;
                    } catch (error) {
                      const fallbackResponse = await apiClient.post('/api/notes/list-notes', { search_term: '' });
                      note = fallbackResponse.data.notes.find((n: { id: number }) => n.id === parseInt(noteId));
                    }
                    }
                  if (note) {
                    setTitle(note.title || '');
                    setCategory(note.category || 'General');
                    setIsShared(note.team_shared || false);
                    setContent(note.content || '');
                  } else {
                    toast.error("Nota no encontrada.");
                    setContent('');
                  }
                } catch (error) {
                  toast.error("No se pudo cargar la nota.");
                  setContent('');
                } finally {
                  setIsLoading(false);
                }
              }
              else {
                // Para notas nuevas, inicializar con contenido vacío
                setTitle('');
                setCategory('General');
                setContent('');
                setIsShared(false);
                setIsLoading(false);
              }
            };
            fetchNote();
          }, [noteId, fromTeam]);
        
          // Efecto para insertar la transcripción en el editor
          useEffect(() => {
            if (transcript && insertContentRef.current) {
              insertContentRef.current(transcript + ' '); // Insertar el transcript y un espacio
              clearTranscript(); // Limpiar el transcript después de usarlo
            }
          }, [transcript, clearTranscript]);  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const autoSaveNote = useCallback(async (currentTitle: string, currentCategory: string, currentContent: string, isNewNote: boolean) => {
    if (isNewNote) return; // No auto-guardar notas nuevas hasta que se guarden manualmente por primera vez

    const payload = {
      note_id: parseInt(noteId),
      title: currentTitle,
      category: currentCategory,
      content: currentContent, // El contenido ya es Markdown
    };

    let endpoint = '/api/update-note';
    let requestPayload;
    if (fromTeam) {
      endpoint = `/api/teams/${fromTeam}/shared-items/update`;
      requestPayload = {
        type: 'note',
        itemId: noteId,
        title: currentTitle,
        content: currentContent, // El contenido ya es Markdown
      };
    } else {
      requestPayload = payload;
    }

    try {
      await apiClient.post(endpoint, requestPayload);
      console.log("Nota auto-guardada.");
    } catch (error) {
      console.error("Error al auto-guardar la nota:", error);
      // Opcional: toast.error("Error al auto-guardar la nota.");
    }
  }, [noteId, fromTeam]);

  const handleSave = async () => {
    const payload = {
        note_id: noteId !== 'new' ? parseInt(noteId) : undefined,
        title,
        category,
        content: content, // El contenido ya es Markdown
    };
    
    let endpoint = noteId === 'new' ? '/api/add-note' : '/api/update-note';
    let requestPayload;
    if (fromTeam && noteId !== 'new') {
      endpoint = `/api/teams/${fromTeam}/shared-items/update`;
      requestPayload = {
        type: 'note',
        itemId: noteId,
        title,
        content: content, // El contenido ya es Markdown
      };
    } else {
      requestPayload = payload;
    }
    const toastId = toast.loading("Guardando nota...");

    try {
        const response = await apiClient.post(endpoint, requestPayload);
        toast.success("¡Nota guardada!", { id: toastId });
        if (noteId === 'new' && response.data?.id) {
          router.replace(`/notes/edit/${response.data.id}`); // Reemplazar la URL para que el auto-guardado funcione con el nuevo ID
        } else {
          router.push(fromTeam ? `/teams/${fromTeam}/dashboard` : '/notes');
        }
    } catch (error) {
        toast.error("Error al guardar la nota.", { id: toastId });
    }
  };

  useEffect(() => {
    if (noteId === 'new') return; // No auto-guardar si es una nota nueva sin guardar

    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }

    autoSaveTimeoutRef.current = setTimeout(() => {
      autoSaveNote(title, category, content, noteId === 'new');
    }, 3000); // Auto-guardar después de 3 segundos de inactividad

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [title, category, content, autoSaveNote, noteId]);

  const handleShare = async () => {
    if (noteId === 'new') return;
    try {
      const response = await apiClient.get('/api/teams');
      const teamsData = response.data;
      if (teamsData.length === 0) {
        toast.error("No tienes equipos para compartir.");
        return;
      }
      setTeams(teamsData);
      setSelectedTeam(teamsData[0].id);
      setIsShareDialogOpen(true);
    } catch (error) {
      toast.error("Error al cargar los equipos.");
      console.error(error);
    }
  };

  const handleShareWithTeam = async () => {
    if (!selectedTeam || noteId === 'new') return;
    try {
      const toastId = toast.loading(`Compartiendo nota con equipo...`);
      await apiClient.post(`/api/teams/${selectedTeam}/share/notes`, {
        noteIds: [parseInt(noteId)]
      });
      toast.success(`Nota compartida con equipo!`, { id: toastId });
      setIsShared(true);
      setIsShareDialogOpen(false);
    } catch (error) {
      toast.error("Error al compartir la nota con el equipo.");
      console.error(error);
    }
  };

  if (isLoading) return <div>Cargando editor...</div>;

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between p-4 bg-background z-10">
        <Button variant="ghost" onClick={() => router.push(fromTeam ? `/teams/${fromTeam}/dashboard` : '/notes')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> {fromTeam ? 'Volver a Equipo' : 'Volver a Notas'}
        </Button>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => {
              if (isRecording) {
                stopRecording();
              } else {
                startRecording();
              }
            }}
            disabled={isProcessingAudio}
            className={`rounded-full ${isRecording ? 'text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'}`}
          >
            {isProcessingAudio ? <Loader2 className="h-5 w-5 animate-spin" /> : <Mic className="h-5 w-5" />}
          </Button>
          {noteId !== 'new' && (
            <Button variant={isShared ? "default" : "outline"} onClick={handleShare}>
              <Users className="mr-2 h-4 w-4" /> {isShared ? 'Compartido' : 'Compartir'}
            </Button>
          )}
          <Button onClick={handleSave}>
            <Save className="mr-2 h-4 w-4" /> Guardar Nota
          </Button>
        </div>
      </header>
      <div className="px-8 py-4 space-y-4">
        <Input placeholder="Título de la nota..." value={title} onChange={(e) => setTitle(e.target.value)} className="!text-4xl font-bold h-auto border-none focus-visible:ring-0 shadow-none p-0" />
        <Input placeholder="Categoría" value={category} onChange={(e) => setCategory(e.target.value)} className="w-fit border-none focus-visible:ring-0 shadow-none p-0 text-sm text-muted-foreground" />
      </div>
            <div className="flex-grow overflow-y-auto px-8 pb-8">
            {isLoading ? (
              <div>Cargando editor...</div>
            ) : (
                      <TiptapEditor
                        content={content}
                        onChange={setContent}
                        fromTeam={fromTeam ?? undefined}
                        isRecording={isRecording}
                        isProcessingAudio={isProcessingAudio}
                        onStartRecording={startRecording}
                        onStopRecording={stopRecording}
                        onInsertContent={(insertFn) => {
                          insertContentRef.current = insertFn; // Almacenar la función de inserción del editor
                        }}
                      />            )}
            </div>      <AlertDialog open={isShareDialogOpen} onOpenChange={(open) => !open && setIsShareDialogOpen(false)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Compartir con Equipo</AlertDialogTitle>
            <AlertDialogDescription>
              Selecciona el equipo con el que deseas compartir esta nota.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              {teams.map(team => (
                <Button
                  key={team.id}
                  variant={selectedTeam === team.id ? "default" : "outline"}
                  onClick={() => setSelectedTeam(team.id)}
                  className="w-full text-left justify-start"
                >
                  {team.name}
                </Button>
              ))}
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={handleShareWithTeam}>Compartir</AlertDialogAction>
            </AlertDialogFooter>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
