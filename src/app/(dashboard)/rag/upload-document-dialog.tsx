// En: src/app/(dashboard)/rag/upload-document-dialog.tsx
'use client';

import { useState, useEffect } from 'react';
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
  topic: z.string().min(3, { message: 'La base de conocimiento debe tener al menos 3 caracteres.' }).optional(),
  files: z.instanceof(FileList).refine((files) => files.length > 0, 'Debes seleccionar al menos un archivo.'),
});

interface UploadDocumentDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onUploadSuccess: () => void;
  defaultTopic?: string; // <-- NUEVA PROP OPCIONAL
}

export function UploadDocumentDialog({ isOpen, onOpenChange, onUploadSuccess, defaultTopic }: UploadDocumentDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      topic: 'General',
      files: undefined,
    },
  });
  
  // Rellenamos el formulario cuando cambia el estado de apertura o el defaultTopic
  useEffect(() => {
    if (isOpen) {
      form.reset({
        // Si hay un defaultTopic, lo usamos; si no, el usuario debe escribirlo.
        topic: defaultTopic || 'General', 
        files: undefined,
      });
    }
  }, [isOpen, defaultTopic, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true);
    
    // ---- CAMBIO LÓGICO: Usamos el defaultTopic si existe, si no, el del formulario ----
    const topicForUpload = defaultTopic || values.topic || 'General';
    const formData = new FormData();
    formData.append('topic', topicForUpload);
    for (let i = 0; i < values.files.length; i++) {
      formData.append('files', values.files[i]);
    }

    toast.info('Subiendo documentos...', {
      description: `A la colección: ${topicForUpload}`,
    });

    try {
      await apiClient.post('/api/upload-document', formData, {
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
            {defaultTopic 
              ? `Los archivos se añadirán a la colección "${defaultTopic}".`
              : "Crea o selecciona una base de conocimiento para tus nuevos archivos."
            }
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* ---- CAMBIO DE RENDERIZADO: El campo 'topic' solo se muestra si NO hay defaultTopic ---- */}
            {!defaultTopic && (
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
            )}
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
                      accept=".pdf,.docx,.txt,.md"
                      onChange={(e) => field.onChange(e.target.files)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="submit" disabled={isSubmitting} className="relative">
                {isSubmitting ? (
                  <>
                    <span className="absolute left-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    Subiendo...
                  </>
                ) : (
                  'Subir'
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
