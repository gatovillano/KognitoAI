// En: src/app/(dashboard)/notes/note-dialog.tsx
'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import apiClient from '@/lib/api';

export interface Note {
  id: number;
  title: string | null;
  content: string;
  category: string;
  created_at: string;
}

const formSchema = z.object({
  title: z.string().optional(),
  category: z.string().min(2, "La categoría es muy corta.").optional(),
  content: z.string().min(1, "El contenido no puede estar vacío."),
});

interface NoteDialogProps {
  note: Note | null; // Si es null, estamos creando. Si tiene valor, estamos editando.
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (note: Note) => void;
}

export function NoteDialog({ note, isOpen, onOpenChange, onSaveSuccess }: NoteDialogProps) {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  const isEditing = !!note;

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
      if (isEditing) {
        // Lógica de actualización
        response = await apiClient.post('/api/update-note', {
          note_id: note.id,
          ...values,
        });
      } else {
        // Lógica de creación
        response = await apiClient.post('/api/add-note', values);
      }
      
      toast.success(isEditing ? '¡Nota actualizada!' : '¡Nota creada!', { id: toastId });
      onSaveSuccess(isEditing ? { ...note, ...values } : response.data);
      onOpenChange(false);
    } catch (error) {
      toast.error(isEditing ? 'Error al actualizar' : 'Error al crear', { id: toastId });
      console.error(error);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Editar Nota' : 'Crear Nueva Nota'}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField control={form.control} name="title" render={({ field }) => (
              <FormItem><FormLabel>Título</FormLabel><FormControl><Input placeholder="Título de la nota" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="category" render={({ field }) => (
              <FormItem><FormLabel>Categoría</FormLabel><FormControl><Input placeholder="Ej: Trabajo, Personal" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="content" render={({ field }) => (
              <FormItem><FormLabel>Contenido</FormLabel><FormControl><Textarea placeholder="Escribe tu nota aquí..." className="min-h-[200px]" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <DialogFooter>
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
