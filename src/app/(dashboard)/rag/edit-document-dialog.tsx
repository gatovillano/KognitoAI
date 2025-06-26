'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import apiClient from '@/lib/api';
import { type Document } from './columns';

const formSchema = z.object({
  new_title: z.string().optional(),
  new_topic: z.string().min(3, { message: 'El tema debe tener al menos 3 caracteres.' }),
});

interface EditDocumentDialogProps {
  document: Document | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdateSuccess: () => void;
}

export function EditDocumentDialog({ document, isOpen, onOpenChange, onUpdateSuccess }: EditDocumentDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });
  
  useEffect(() => {
    // Rellenar el formulario cuando se abre el diálogo con un documento
    if (document) {
      form.reset({
        new_title: document.title || '',
        new_topic: document.topic,
      });
    }
  }, [document, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    if (!document) return;
    setIsSubmitting(true);
    const payload = {
        file_name: document.file_name,
        new_topic: values.new_topic,
        new_title: values.new_title || null, // Envía null si está vacío
    };

    toast.info('Actualizando metadatos...');
    try {
      await apiClient.post('/api/update-document-metadata', payload);
      toast.success('¡Metadatos actualizados!');
      onUpdateSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al actualizar los metadatos.');
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar Metadatos</DialogTitle>
          <DialogDescription className="truncate">
            Archivo: {document?.file_name}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="new_title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nuevo Título (Opcional)</FormLabel>
                  <FormControl>
                    <Input placeholder="Título descriptivo del documento" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="new_topic"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nueva Base de Conocimiento (Tema)</FormLabel>
                  <FormControl>
                    <Input placeholder="Ej: Investigacion Q3" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
