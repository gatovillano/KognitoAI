// En: src/app/(dashboard)/rag/upload-document-dialog.tsx
'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import apiClient from '@/lib/api';

const formSchema = z.object({
  topic: z.string().min(3, { message: 'La base de conocimiento debe tener al menos 3 caracteres.' }),
  files: z.instanceof(FileList).refine((files) => files.length > 0, 'Debes seleccionar al menos un archivo.'),
});

interface UploadDocumentDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onUploadSuccess: () => void;
}

export function UploadDocumentDialog({ isOpen, onOpenChange, onUploadSuccess }: UploadDocumentDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      topic: 'General',
      files: undefined,
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true);
    const formData = new FormData();
    formData.append('topic', values.topic);
    for (let i = 0; i < values.files.length; i++) {
      formData.append('files', values.files[i]);
    }

    toast.info('Subiendo documentos...', {
      description: 'Esto puede tardar unos momentos.',
    });

    try {
      await apiClient.post('/upload-document', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success('¡Documentos subidos con éxito!');
      onUploadSuccess();
      onOpenChange(false);
      form.reset();
    } catch (error) {
      toast.error('Error al subir documentos', {
        description: 'Por favor, inténtalo de nuevo.',
      });
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Subir Nuevo Documento</DialogTitle>
          <DialogDescription>
            Añade archivos a tu base de conocimiento. Formatos soportados: PDF, DOCX, TXT.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="topic"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Base de Conocimiento (Tema)</FormLabel>
                  <FormControl>
                    <Input placeholder="Ej: Investigacion Q3, Apuntes Legales..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="files"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Archivos</FormLabel>
                  <FormControl>
                    <Input 
                      type="file" 
                      multiple 
                      onChange={(e) => field.onChange(e.target.files)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Subiendo...' : 'Subir'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
