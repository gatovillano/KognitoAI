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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'; // Importar Tabs
import { TiptapEditor } from '@/components/TiptapEditor'; // Importar TiptapEditor
import apiClient from '@/lib/api';

const formSchema = z.object({
  topic: z.string().min(3, { message: 'La base de conocimiento debe tener al menos 3 caracteres.' }).optional(),
  files: z.instanceof(FileList).optional(), // Ahora es opcional
  text_content: z.string().optional(), // Nuevo campo para el contenido de texto
}).superRefine((data, ctx) => {
  // Validar condicionalmente: o files o text_content debe estar presente
  if (!data.files?.length && !data.text_content) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Debes seleccionar al menos un archivo o introducir texto.',
      path: ['files'], // Asociar el error al campo files para que se muestre debajo
    });
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Debes seleccionar al menos un archivo o introducir texto.',
      path: ['text_content'], // Asociar el error al campo text_content
    });
  }
  // Si hay archivos, el campo de texto no debe tener contenido
  if (data.files?.length && data.text_content) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'No puedes subir archivos y texto a la vez.',
      path: ['files'],
    });
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'No puedes subir archivos y texto a la vez.',
      path: ['text_content'],
    });
  }
});

interface UploadDocumentDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onUploadSuccess: (fileNames: string[], topic: string) => void;
  onUploadStart: (fileNames: string[], topic: string) => void; // Nueva prop
  defaultTopic?: string;
  workspaceId?: string;
}

export function UploadDocumentDialog({ isOpen, onOpenChange, onUploadSuccess, onUploadStart, defaultTopic, workspaceId }: UploadDocumentDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('files'); // 'files' o 'text'

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      topic: 'General',
      files: undefined,
      text_content: '',
    },
  });
  
  // Rellenamos el formulario cuando cambia el estado de apertura o el defaultTopic
  useEffect(() => {
    if (isOpen) {
      form.reset({
        // Si hay un defaultTopic, lo usamos; si no, el usuario debe escribirlo.
        topic: defaultTopic || 'General',
        files: undefined,
        text_content: '', // Resetear también el contenido de texto
      });
      setActiveTab('files'); // Resetear a la pestaña de archivos al abrir
    }
  }, [isOpen, defaultTopic, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true);
    
    const topicForUpload = defaultTopic || values.topic || 'General';
    const fileNames: string[] = []; // Para el feedback al usuario

    try {
      if (activeTab === 'files' && values.files && values.files.length > 0) {
        const formData = new FormData();
        formData.append('topic', topicForUpload);
        if (workspaceId) {
          formData.append('workspace_id', workspaceId);
          console.log("Frontend: workspaceId = " + workspaceId);
        }
        for (let i = 0; i < values.files.length; i++) {
          formData.append('files', values.files[i]);
          fileNames.push(values.files[i].name);
        }

        toast.info('Subiendo documentos...', {
          description: `A la colección: ${topicForUpload}`,
          duration: 0,
          id: 'upload-progress'
        });

        onUploadStart(fileNames, topicForUpload);
        onOpenChange(false);

        await apiClient.post('/api/upload-document', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        toast.success('¡Documentos subidos con éxito!', {
          id: 'upload-progress'
        });

      } else if (activeTab === 'text' && values.text_content) {
        const textFileName = `texto-${Date.now()}.md`; // Generar un nombre de archivo para el texto
        fileNames.push(textFileName);

        toast.info('Guardando texto como documento...', {
          description: `En la colección: ${topicForUpload}`,
          duration: 0,
          id: 'upload-progress'
        });

        onUploadStart(fileNames, topicForUpload);
        onOpenChange(false);

        await apiClient.post('/api/upload-text-document', { // Nueva API para subir texto
          topic: topicForUpload,
          file_name: textFileName,
          content: values.text_content,
          workspace_id: workspaceId,
        });
        toast.success('¡Texto guardado como documento con éxito!', {
          id: 'upload-progress'
        });

      } else {
        toast.error('Por favor, selecciona al menos un archivo o introduce texto.');
        return;
      }
      
      onUploadSuccess(fileNames, topicForUpload);
      form.reset();
    } catch (error) {
      toast.error('Error al subir/guardar documento', {
        description: 'Por favor, inténtalo de nuevo.',
        id: 'upload-progress'
      });
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]"> {/* Ajustar el ancho del diálogo */}
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

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="files">Subir Archivos</TabsTrigger>
                <TabsTrigger value="text">Añadir Texto</TabsTrigger>
              </TabsList>
              <TabsContent value="files">
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
                          accept=".pdf,.docx,.txt,.md,.html"
                          onChange={(e) => field.onChange(e.target.files)}
                          disabled={isSubmitting}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </TabsContent>
              <TabsContent value="text">
                <FormField
                  control={form.control}
                  name="text_content"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Contenido de Texto</FormLabel>
                      <FormControl>
                        <TiptapEditor content={field.value || ''} onChange={field.onChange} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </TabsContent>
            </Tabs>

            <DialogFooter>
              <Button type="submit" disabled={isSubmitting} className="relative">
                {isSubmitting ? (
                  <>
                    <span className="absolute left-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span className="pl-6">{activeTab === 'files' ? 'Subiendo...' : 'Guardando...'}</span>
                  </>
                ) : (
                  activeTab === 'files' ? 'Subir Documento' : 'Guardar Conocimiento'
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
