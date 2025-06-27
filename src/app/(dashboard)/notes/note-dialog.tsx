// En: src/app/(dashboard)/notes/note-dialog.tsx

'use client';

import { useEffect } from 'react';
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
});

interface NoteDialogProps {
  note: Note | null; // Si es null, estamos creando. Si tiene valor, estamos editando.
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (note: Note | any) => void; // Acepta la nota actualizada o la nueva
}

export function NoteDialog({ note, isOpen, onOpenChange, onSaveSuccess }: NoteDialogProps) {
  const router = useRouter();
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  const isEditing = !!note;

  // Este useEffect se encarga de rellenar el formulario con los datos de la nota
  // cuando el diálogo se abre para editar, o de limpiarlo si es para crear.
  useEffect(() => {
    if (isOpen) {
      form.reset({
        title: note?.title || '',
        category: note?.category || 'General',
        content: note?.content || '',
      });
    }
  }, [isOpen, note, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const toastId = toast.loading(isEditing ? 'Actualizando nota...' : 'Creando nota...');

    try {
      let response;
      const endpoint = isEditing ? '/api/update-note' : '/api/add-note';
      const payload = isEditing ? { note_id: note.id, ...values } : values;

      response = await apiClient.post(endpoint, payload);
      
      toast.success(isEditing ? '¡Nota actualizada!' : '¡Nota creada!', { id: toastId });
      
      // Llamamos al callback para actualizar la UI de la página principal
      // Si estamos editando, fusionamos los datos viejos y nuevos. Si no, usamos la respuesta de la API.
      onSaveSuccess(isEditing ? { ...note, ...values } : response.data);
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
      <DialogContent className="sm:max-w-[625px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Editar Nota Rápida' : 'Crear Nueva Nota'}</DialogTitle>
          <DialogDescription>
            Realiza cambios rápidos aquí o usa el editor avanzado para más opciones de formato.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="title" render={({ field }) => (
                <FormItem><FormLabel>Título</FormLabel><FormControl><Input placeholder="Título de la nota" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="category" render={({ field }) => (
                <FormItem><FormLabel>Categoría</FormLabel><FormControl><Input placeholder="Ej: Trabajo, Personal" {...field} value={field.value || ''} /></FormControl><FormMessage /></FormItem>
                )} />
            </div>
            <FormField control={form.control} name="content" render={({ field }) => (
              <FormItem><FormLabel>Contenido (soporta Markdown)</FormLabel><FormControl><Textarea placeholder="Escribe tu nota aquí..." className="min-h-[200px] resize-y" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
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