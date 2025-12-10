'use client';

import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import dynamic from 'next/dynamic';

const TiptapEditor = dynamic(() => import('@/components/TiptapEditor').then(mod => mod.TiptapEditor), { ssr: false });
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Save, Mic, Loader2 } from 'lucide-react';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';

export default function EditNotePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const noteId = (params?.id as string) || '';

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isShared, setIsShared] = useState(false);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const { isRecording, isProcessingAudio, transcript, startRecording, stopRecording, clearTranscript } = useAudioRecorder();
  const insertContentRef = useRef<((text: string) => void) | null>(null);

  const handleImageUpload = async (file: File) => {
    const toastId = "upload-image";
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post('/api/notes/upload-image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (insertContentRef.current) {
        insertContentRef.current(`\n![${file.name}](${response.data.url})\n`);
      }
    } catch (error) {
      console.error('Error uploading image:', error);
    }
  };

  useEffect(() => {
    const fetchNote = async () => {
      setIsLoading(true);
      if (noteId && noteId !== 'new') {
        try {
          let note;
          try {
            const directResponse = await apiClient.get(`/api/notes/${noteId}`);
            note = directResponse.data;
          } catch (error) {
            const fallbackResponse = await apiClient.post('/api/notes/list-notes', { search_term: '' });
            note = fallbackResponse.data.notes.find((n: { id: number }) => n.id === parseInt(noteId));
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
        setTitle('');
        setCategory('General');
        setContent('');
        setIsShared(false);
        setIsLoading(false);
      }
    };
    fetchNote();
  }, [noteId]);

  useEffect(() => {
    if (transcript && insertContentRef.current) {
      insertContentRef.current(transcript + ' ');
      clearTranscript();
    }
  }, [transcript, clearTranscript]);

  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const autoSaveNote = useCallback(async (currentTitle: string, currentCategory: string, currentContent: string, isNewNote: boolean) => {
    if (isNewNote) return;

    const payload = {
      note_id: parseInt(noteId),
      title: currentTitle,
      category: currentCategory,
      content: currentContent,
    };

    let endpoint = '/api/update-note';
    let requestPayload;

    requestPayload = payload;

    try {
      await apiClient.post(endpoint, requestPayload);
      console.log("Nota auto-guardada.");
    } catch (error) {
      console.error("Error al auto-guardar la nota:", error);
    }
  }, [noteId]);

  const handleSave = async () => {
    const payload = {
      note_id: noteId !== 'new' ? parseInt(noteId) : undefined,
      title,
      category,
      content: content,
    };

    let endpoint = noteId === 'new' ? '/api/add-note' : '/api/update-note';
    let requestPayload;

    requestPayload = payload;
    const toastId = toast.loading("Guardando nota...");

    try {
      const response = await apiClient.post(endpoint, requestPayload);
      toast.success("¡Nota guardada!", { id: toastId });
      if (noteId === 'new' && response.data?.id) {
        router.replace(`/notes/edit/${response.data.id}`);
      } else {
        router.push('/notes');
      }
    } catch (error) {
      toast.error("Error al guardar la nota.", { id: toastId });
    }
  };

  useEffect(() => {
    if (noteId === 'new') return;

    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }

    autoSaveTimeoutRef.current = setTimeout(() => {
      autoSaveNote(title, category, content, noteId === 'new');
    }, 3000);

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [title, category, content, autoSaveNote, noteId]);

  const handleShare = async () => {
    if (noteId === 'new') return;
    try {
      const response = await apiClient.get('/api/workspaces');
      const workspacesData = response.data.workspaces;
      if (workspacesData.length === 0) {
        toast.error("No tienes espacios de trabajo para compartir.");
        return;
      }
      setWorkspaces(workspacesData);
      setSelectedWorkspace(workspacesData[0].id);
      setIsShareDialogOpen(true);
    } catch (error) {
      toast.error("Error al cargar los espacios de trabajo.");
      console.error(error);
    }
  };

  const handleShareWithWorkspace = async () => {
    if (!selectedWorkspace || noteId === 'new') return;
    try {
      const toastId = toast.loading(`Compartiendo nota con workspace...`);
      // Aquí deberías implementar la lógica para compartir con workspace
      // Por ahora, simplemente actualizamos el workspace_id de la nota
      await apiClient.post('/api/update-note', {
        note_id: parseInt(noteId),
        workspace_id: selectedWorkspace
      });
      toast.success(`Nota compartida con workspace!`, { id: toastId });
      setIsShared(true);
      setIsShareDialogOpen(false);
    } catch (error) {
      toast.error("Error al compartir la nota con el workspace.");
      console.error(error);
    }
  };

  if (isLoading) return <div>Cargando editor...</div>;

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center justify-between p-4 bg-background z-10">
        <Button variant="ghost" onClick={() => router.push('/notes')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Volver a Notas
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
            isRecording={isRecording}
            isProcessingAudio={isProcessingAudio}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            onInsertContent={(insertFn) => {
              insertContentRef.current = insertFn;
            }}
            onImageUpload={() => {
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
            }}
          />
        )}
      </div>
      <AlertDialog open={isShareDialogOpen} onOpenChange={(open) => !open && setIsShareDialogOpen(false)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Compartir con Workspace</AlertDialogTitle>
            <AlertDialogDescription>
              Selecciona el workspace con el que deseas compartir esta nota.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              {workspaces.map(workspace => (
                <Button
                  key={workspace.id}
                  variant={selectedWorkspace === workspace.id ? "default" : "outline"}
                  onClick={() => setSelectedWorkspace(workspace.id)}
                  className="w-full text-left justify-start"
                >
                  {workspace.name}
                </Button>
              ))}
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={handleShareWithWorkspace}>Compartir</AlertDialogAction>
            </AlertDialogFooter>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}