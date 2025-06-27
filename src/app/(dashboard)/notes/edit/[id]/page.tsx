// En: src/app/(dashboard)/notes/edit/[id]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { TiptapEditor } from '@/components/TiptapEditor'; // Importamos el editor
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Save } from 'lucide-react';
import TurndownService from 'turndown'; // Librería para convertir HTML a Markdown

// Necesitamos instalar esta librería: npm install turndown @types/turndown
// Opcional, pero muy recomendado para guardar en Markdown limpio.

export default function EditNotePage() {
  const params = useParams();
  const router = useRouter();
  const noteId = params.id as string;

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('');
  const [content, setContent] = useState(''); // El contenido será HTML
  const [isLoading, setIsLoading] = useState(true);

  // Inicializamos el servicio de conversión
  const turndownService = new TurndownService();

  useEffect(() => {
    // Si es una nota nueva, el ID será 'new'. Si no, cargamos los datos.
    if (noteId && noteId !== 'new') {
      const fetchNote = async () => {
        setIsLoading(true);
        try {
          // Necesitaremos un endpoint para obtener una sola nota
          const response = await apiClient.post('/api/get-note', { note_id: parseInt(noteId) });
          setTitle(response.data.title || '');
          setCategory(response.data.category || 'General');
          setContent(response.data.content); // Aquí guardamos el Markdown como contenido inicial
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
  }, [noteId]);

  const handleSave = async () => {
    // Convertimos el HTML de Tiptap a Markdown antes de guardar
    const markdownContent = turndownService.turndown(content);

    const payload = {
        note_id: noteId !== 'new' ? parseInt(noteId) : undefined,
        title,
        category,
        content: markdownContent,
    };
    
    const endpoint = noteId === 'new' ? '/api/add-note' : '/api/update-note';
    const toastId = toast.loading("Guardando nota...");

    try {
        await apiClient.post(endpoint, payload);
        toast.success("¡Nota guardada!", { id: toastId });
        router.push('/notes');
    } catch (error) {
        toast.error("Error al guardar la nota.", { id: toastId });
    }
  };

  if (isLoading) return <div>Cargando editor...</div>;

  return (
    <div className="p-6 h-full flex flex-col">
      <header className="flex items-center justify-between mb-4">
        <Button variant="ghost" onClick={() => router.push('/notes')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Volver a Notas
        </Button>
        <Button onClick={handleSave}>
          <Save className="mr-2 h-4 w-4" /> Guardar Nota
        </Button>
      </header>
      <div className="space-y-4">
        <Input placeholder="Título de la nota..." value={title} onChange={(e) => setTitle(e.target.value)} className="text-2xl font-bold h-auto border-none focus-visible:ring-0 shadow-none p-0" />
        <Input placeholder="Categoría" value={category} onChange={(e) => setCategory(e.target.value)} className="w-fit border-none focus-visible:ring-0 shadow-none p-0 text-sm text-muted-foreground" />
      </div>
      <div className="flex-grow mt-4">
        <TiptapEditor content={content} onChange={setContent} />
      </div>
    </div>
  );
}