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
import { ArrowLeft, Save } from 'lucide-react';
import TurndownService from 'turndown'; // Librería para convertir HTML a Markdown
import { marked } from 'marked'; // Librería para convertir Markdown a HTML

// Necesitamos instalar esta librería: npm install turndown @types/turndown
// Opcional, pero muy recomendado para guardar en Markdown limpio.

export default function EditNotePage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const noteId = (params?.id as string) || '';
  const fromTeam = searchParams?.get('fromTeam');

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [content, setContent] = useState(''); // El contenido será HTML
  const [isLoading, setIsLoading] = useState(true);
  const [isShared, setIsShared] = useState(false);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [teams, setTeams] = useState<any[]>([]);

  // Inicializamos el servicio de conversión
  const turndownService = useMemo(() => new TurndownService(), []);

    useEffect(() => {
    // Si es una nota nueva, el ID será 'new'. Si no, cargamos los datos.
    if (noteId && noteId !== 'new') {
      const fetchNote = async () => {
        setIsLoading(true);
        try {
          let response;
          if (fromTeam) {
            // Para notas compartidas, buscamos en los elementos compartidos del equipo
            response = await apiClient.get(`/api/teams/${fromTeam}/shared-items`);
            console.log("Datos de elementos compartidos recibidos:", response.data);
          } else {
            // Usamos /api/list-notes y filtramos por ID para notas personales
            response = await apiClient.post('/api/list-notes', { search_term: '' });
            console.log("Datos de notas personales recibidos:", response.data);
          }
          // Filtramos por ID y tipo 'note' para notas compartidas
          const note = fromTeam 
            ? response.data.find((n: { id: number, type: string }) => n.id === parseInt(noteId) && n.type === 'note')
            : response.data.notes.find((n: { id: number }) => n.id === parseInt(noteId));
          console.log("Nota encontrada:", note);
          if (note) {
            setTitle(note.title || '');
            setCategory(note.category || 'General');
            setIsShared(note.team_shared || false);
            // Convert Markdown content from API to HTML for the editor
            if (note.content) {
              try {
                const htmlContent = await marked.parse(note.content);
                setContent(htmlContent);
              } catch (error) {
                console.error("Error converting Markdown to HTML:", error);
                setContent(note.content);
                toast.error("Error al convertir el contenido de Markdown a HTML.");
              }
            } else {
              console.warn("No content field found in note object, attempting to fetch full note:", note);
              try {
                const fullNoteResponse = await apiClient.get(`/api/notes/${noteId}`);
                console.log("Full note data received:", fullNoteResponse.data);
                if (fullNoteResponse.data && fullNoteResponse.data.content) {
                  const htmlContent = await marked.parse(fullNoteResponse.data.content);
                  setContent(htmlContent);
                } else {
                  setContent('');
                  toast.error("El contenido de la nota no está disponible incluso después de intentar cargarlo.");
                }
              } catch (error) {
                console.error("Error fetching full note content:", error);
                setContent('');
                toast.error("Error al intentar cargar el contenido completo de la nota.");
              }
            }
          } else {
            toast.error("Nota no encontrada.");
          }
        } catch (error) {
          toast.error("No se pudo cargar la nota.");
        } finally {
          setIsLoading(false);
        }
      };
      fetchNote();
    } else {
      setIsLoading(false);
    }
  }, [noteId, fromTeam]);

  // Ensure content is properly set when switching between notes
  useEffect(() => {
    if (!isLoading && noteId === 'new') {
      setContent(''); // Reset content for new note
    }
  }, [isLoading, noteId]);

  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const autoSaveNote = useCallback(async (currentTitle: string, currentCategory: string, currentContent: string, isNewNote: boolean) => {
    if (isNewNote) return; // No auto-guardar notas nuevas hasta que se guarden manualmente por primera vez

    const markdownContent = turndownService.turndown(currentContent);

    const payload = {
      note_id: parseInt(noteId),
      title: currentTitle,
      category: currentCategory,
      content: markdownContent,
    };

    let endpoint = '/api/update-note';
    let requestPayload;
    if (fromTeam) {
      endpoint = `/api/teams/${fromTeam}/shared-items/update`;
      requestPayload = {
        type: 'note',
        itemId: noteId,
        title: currentTitle,
        content: markdownContent,
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
  }, [noteId, fromTeam, turndownService]);

  const handleSave = async () => {
    const markdownContent = turndownService.turndown(content);

    const payload = {
        note_id: noteId !== 'new' ? parseInt(noteId) : undefined,
        title,
        category,
        content: markdownContent,
    };
    
    let endpoint = noteId === 'new' ? '/api/add-note' : '/api/update-note';
    let requestPayload;
    if (fromTeam && noteId !== 'new') {
      endpoint = `/api/teams/${fromTeam}/shared-items/update`;
      requestPayload = {
        type: 'note',
        itemId: noteId,
        title,
        content: markdownContent,
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
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-6">
      <header className="flex items-center justify-between mb-4">
        <Button variant="ghost" onClick={() => router.push(fromTeam ? `/teams/${fromTeam}/dashboard` : '/notes')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> {fromTeam ? 'Volver a Equipo' : 'Volver a Notas'}
        </Button>
        <div className="flex gap-2">
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
      <div className="space-y-4">
        <Input placeholder="Título de la nota..." value={title} onChange={(e) => setTitle(e.target.value)} className="text-2xl font-bold h-auto border-none focus-visible:ring-0 shadow-none p-0" />
        <Input placeholder="Categoría" value={category} onChange={(e) => setCategory(e.target.value)} className="w-fit border-none focus-visible:ring-0 shadow-none p-0 text-sm text-muted-foreground" />
      </div>
      <div className="flex-grow mt-4">
        <TiptapEditor content={content} onChange={setContent} fromTeam={fromTeam ?? undefined} />
      </div>
      <AlertDialog open={isShareDialogOpen} onOpenChange={(open) => !open && setIsShareDialogOpen(false)}>
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
