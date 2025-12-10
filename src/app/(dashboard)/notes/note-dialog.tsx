// En: src/app/(dashboard)/notes/note-dialog.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';

import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import apiClient from '@/lib/api';
import type { Note } from './page';
import { BookUp } from 'lucide-react';


// Schema de validación para el formulario
const formSchema = z.object({
  title: z.string().optional(),
  category: z.string().min(2, "La categoría es muy corta.").optional(),
  content: z.string().min(1, "El contenido no puede estar vacío."),
  workspace_id: z.string().optional(),
  team_id: z.string().optional(),
});

interface NoteDialogProps {
  note: Note | null; // Si es null, estamos creando. Si tiene valor, estamos editando.
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (note: Note | any) => void; // Acepta la nota actualizada o la nueva
  workspaceId?: string; // New prop
}

export function NoteDialog({ note, isOpen, onOpenChange, onSaveSuccess, workspaceId }: NoteDialogProps) {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [teams, setTeams] = useState<any[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  useEffect(() => {
    const fetchTeams = async () => {
      setLoadingTeams(true);
      try {
        const response = await apiClient.get('/api/teams');
        setTeams(response.data.teams || []);
      } catch (error) {
        console.error("Error fetching teams:", error);
        toast.error('Error al cargar los equipos.');
      } finally {
        setLoadingTeams(false);
      }
    };
    if (isOpen) {
      fetchTeams();
    }
  }, [isOpen]);

  useEffect(() => {
    const fetchWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const response = await apiClient.get('/api/workspaces');
        // Asegurarse de que response.data sea un array antes de asignarlo
        if (Array.isArray(response.data)) {
          setWorkspaces(response.data);
        } else if (response.data && Array.isArray(response.data.workspaces)) {
          setWorkspaces(response.data.workspaces);
        } else {
          console.warn("API /api/workspaces did not return an array or an object with a 'workspaces' array:", response.data);
          setWorkspaces([]);
        }
      } catch (error) {
        console.error("Error fetching workspaces:", error);
        toast.error('Error al cargar los workspaces.');
      } finally {
        setLoadingWorkspaces(false);
      }
    };
    if (isOpen) {
      fetchWorkspaces();
    }
  }, [isOpen]);

  const isEditing = !!note;

  // Este useEffect se encarga de rellenar el formulario con los datos de la nota
  // cuando el diálogo se abre para editar, o de limpiarlo si es para crear.
  useEffect(() => {
    if (isOpen) {
      console.log("NoteDialog: isOpen is true, note prop:", note); // DEBUG
      form.reset({
        title: note?.title || '',
        category: note?.category || 'General',
        content: note?.content || '',
        workspace_id: note?.workspace_id || '',
        team_id: note?.team_id || '',
      });
    }
  }, [isOpen, note, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const toastId = toast.loading(isEditing ? 'Actualizando nota...' : 'Creando nota...');

    try {
      const endpoint = isEditing ? '/api/update-note' : '/api/add-note';
      const payload = isEditing
        ? { note_id: note.id, ...values }
        : { workspace_id: workspaceId, ...values };

      const response = await apiClient.post(endpoint, payload);
      toast.success(isEditing ? '¡Nota actualizada!' : '¡Nota creada!', { id: toastId });

      const noteId = isEditing ? note.id : response.data.id;

      // Llamamos al callback para actualizar la UI de la página principal
      // Si estamos editando, fusionamos los datos viejos y nuevos. Si no, usamos la respuesta de la API.
      // Aseguramos que team_shared se actualice basado en si hay un team_id seleccionado.
      const selectedWorkspace = workspaces.find(ws => ws.id === values.workspace_id);

      const updatedNote = isEditing
        ? {
          ...note,
          ...values,
          team_shared: !!values.team_id,
          workspace_name: selectedWorkspace?.name || '',
          workspace_color: selectedWorkspace?.color || '',
        }
        : {
          ...response.data,
          team_shared: !!values.team_id,
          workspace_id: values.workspace_id,
          workspace_name: selectedWorkspace?.name || '',
          workspace_color: selectedWorkspace?.color || '',
        };
      onSaveSuccess(updatedNote);
      onOpenChange(false);
    } catch (error) {
      toast.error(isEditing ? 'Error al actualizar la nota.' : 'Error al crear la nota.', { id: toastId });
      console.error(error);
    }
  }

  const handleGoToAdvancedEditor = () => {
    // Cerramos el diálogo actual
    onOpenChange(false);
    // Navegamos a la página de edición a pantalla completa
    // Si es una nota nueva, el ID es 'new'. Si no, usamos el ID de la nota.
    router.push(`/notes/edit/${note?.id || 'new'}`);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg md:max-w-2xl lg:max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Editar Nota Rápida' : 'Crear Nueva Nota'}</DialogTitle>
          <DialogDescription>
            Realiza cambios rápidos aquí o usa el editor avanzado para más opciones de formato.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <ScrollArea className="h-[400px] pr-4">
              <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="title" render={({ field }) => (
                  <FormItem><FormLabel>Título</FormLabel><FormControl><Input placeholder="Título de la nota" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="category" render={({ field }) => (
                  <FormItem><FormLabel>Categoría</FormLabel><FormControl><Input placeholder="Ej: Trabajo, Personal" {...field} value={field.value || ''} /></FormControl><FormMessage /></FormItem>
                )} />
              </div>
              <FormField control={form.control} name="workspace_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>Workspace</FormLabel>
                  <FormControl>
                    <select
                      className="w-full border rounded-md p-2"
                      onChange={field.onChange}
                      value={field.value || ''}
                      disabled={loadingWorkspaces}
                    >
                      <option value="">{loadingWorkspaces ? "Cargando workspaces..." : "Ninguno"}</option>
                      {workspaces.map(workspace => (
                        <option key={workspace.id} value={workspace.id}>
                          {workspace.name}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="content" render={({ field }) => (
                <FormItem><FormLabel>Contenido</FormLabel><FormControl><Textarea placeholder="Contenido de la nota" {...field} rows={10} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="team_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>Compartir con Equipo</FormLabel>
                  <FormControl>
                    <select
                      className="w-full border rounded-md p-2"
                      onChange={field.onChange}
                      value={field.value || ''}
                      disabled={loadingTeams}
                    >
                      <option value="">{loadingTeams ? "Cargando equipos..." : "Ninguno"}</option>
                      {teams.map(team => (
                        <option key={team.id} value={team.id.toString()}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            </ScrollArea>
            <DialogFooter className="flex-col-reverse sm:flex-row sm:justify-between sm:space-x-2">
              <Button type="button" variant="outline" onClick={handleGoToAdvancedEditor}>
                <BookUp className="mr-2 h-4 w-4" />
                Editor Avanzado
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? 'Guardando...' : 'Guardar Nota'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
