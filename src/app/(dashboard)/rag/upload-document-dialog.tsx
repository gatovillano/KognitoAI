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
import { ScrollArea } from '@/components/ui/scroll-area'; // Importar ScrollArea
import apiClient from '@/lib/api';
import { Globe } from 'lucide-react';

const formSchema = z.object({
  topic: z.string().optional(),
  files: z.any().optional(),
  text_content: z.string().optional(),
  web_url: z.string().optional(),
}).superRefine((data, ctx) => {
  const sources = [
    data.files && data.files.length > 0,
    data.text_content && data.text_content.trim().length > 0,
    data.web_url && data.web_url.trim().length > 0
  ].filter(Boolean).length;

  if (sources === 0) {
    const message = 'Debes seleccionar al menos un archivo, introducir texto o una URL.';
    ctx.addIssue({ code: z.ZodIssueCode.custom, message, path: ['files'] });
  }

  if (sources > 1) {
    const message = 'No puedes subir archivos, texto y URL a la vez.';
    ctx.addIssue({ code: z.ZodIssueCode.custom, message, path: ['files'] });
    ctx.addIssue({ code: z.ZodIssueCode.custom, message, path: ['text_content'] });
    ctx.addIssue({ code: z.ZodIssueCode.custom, message, path: ['web_url'] });
  }

  if (data.topic && data.topic.length > 0 && data.topic.length < 3) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'La base de conocimiento debe tener al menos 3 caracteres.',
      path: ['topic'],
    });
  }

  if (data.web_url && data.web_url.trim().length > 0) {
    try {
      new URL(data.web_url);
    } catch {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Por favor, introduce una URL válida.",
        path: ['web_url'],
      });
    }
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

interface DropzoneProps {
  children: React.ReactNode;
  onDrop: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragLeave: (event: React.DragEvent<HTMLDivElement>) => void;
  isDragging: boolean;
}

function Dropzone({ children, onDrop, onDragOver, onDragLeave, isDragging }: DropzoneProps) {
  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      className={`relative border-2 rounded-lg transition-colors ${isDragging ? 'border-primary bg-primary/10' : 'border-dashed border-gray-300 dark:border-gray-700'
        }`}
    >
      {children}
      {isDragging && (
        <div className="absolute inset-0 bg-primary/20 flex items-center justify-center text-primary-foreground text-lg font-semibold pointer-events-none">
          Suelta tus archivos aquí
        </div>
      )}
    </div>
  );
}

export function UploadDocumentDialog({ isOpen, onOpenChange, onUploadSuccess, onUploadStart, defaultTopic, workspaceId }: UploadDocumentDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('files');
  const [isDragging, setIsDragging] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      topic: 'General',
      files: undefined,
      text_content: '',
      web_url: '',
    },
  });

  const files = form.watch('files');

  useEffect(() => {
    if (isOpen) {
      form.reset({
        topic: defaultTopic || 'General',
        files: undefined,
        text_content: '',
        web_url: '',
      });
      setActiveTab('files');
    }
  }, [isOpen, defaultTopic, form]);

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const droppedFiles = event.dataTransfer.files;
    if (droppedFiles && droppedFiles.length > 0) {
      form.setValue('files', droppedFiles);
      form.clearErrors('files');
    }
  };

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true);
    const topicForUpload = defaultTopic || values.topic || 'General';

    try {
      if (activeTab === 'web' && values.web_url) {
        onUploadStart([values.web_url], topicForUpload);
        onOpenChange(false);

        apiClient.post('/api/tools/run', {
          tool_name: 'add_web_to_rag',
          url: values.web_url,
          topic: topicForUpload,
          workspace_id: workspaceId,
        }).catch((error: any) => {
          // Captura errores de la petición inicial (ej. red, 4xx)
          // Los errores de procesamiento de la tarea se reciben por WebSocket
          toast.error('Error al iniciar el procesamiento de la URL.', {
            description: error.response?.data?.detail || 'Por favor, revisa la URL y tu conexión.',
          });
          // Aquí podrías querer enviar un evento de fallo por WS si el backend no lo hace
        });

      } else if (activeTab === 'files' && values.files && values.files.length > 0) {
        const fileNames = (Array.from(values.files) as File[]).map(f => f.name);
        const formData = new FormData();
        formData.append('topic', topicForUpload);
        if (workspaceId) formData.append('workspace_id', workspaceId);
        (Array.from(values.files) as File[]).forEach(file => formData.append('files', file));

        toast.info('Subiendo documentos...', {
          description: `A la colección: ${topicForUpload}`,
        });

        onUploadStart(fileNames, topicForUpload);
        onOpenChange(false);

        apiClient.post('/api/documents/upload-document', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        }).then(() => {
          console.log('Upload request sent successfully for', fileNames);
          // onUploadSuccess es llamado por el websocket en este caso
        }).catch(error => {
          toast.error('Error al iniciar la subida de documentos.', {
            description: 'Por favor, revisa tu conexión e inténtalo de nuevo.',
          });
          console.error(error);
        });

      } else if (activeTab === 'text' && values.text_content) {
        const textFile = new File([values.text_content], `texto-${Date.now()}.md`, { type: 'text/markdown' });
        const formData = new FormData();
        formData.append('topic', topicForUpload);
        if (workspaceId) formData.append('workspace_id', workspaceId);
        formData.append('files', textFile);

        toast.info('Guardando texto como documento...', {
          description: `En la colección: ${topicForUpload}`,
        });

        onUploadStart([textFile.name], topicForUpload);
        onOpenChange(false);

        apiClient.post('/api/documents/upload-document', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        }).then(() => {
          console.log('Text content sent successfully');
        }).catch(error => {
          toast.error('Error al guardar el texto.', {
            description: 'Por favor, inténtalo de nuevo.',
          });
          console.error(error);
        });

      } else {
        // Este caso debería ser prevenido por la validación del schema
        toast.error('Por favor, proporciona una fuente de datos.');
      }
    } catch (error) {
      toast.error('Ha ocurrido un error inesperado.', {
        description: 'Por favor, inténtalo de nuevo.',
      });
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  const getSubmitButtonText = () => {
    if (isSubmitting) {
      switch (activeTab) {
        case 'files': return 'Subiendo...';
        case 'text': return 'Guardando...';
        case 'web': return 'Añadiendo...';
        default: return 'Procesando...';
      }
    }
    switch (activeTab) {
      case 'files': return 'Subir Documento(s)';
      case 'text': return 'Guardar Conocimiento';
      case 'web': return 'Añadir desde Web';
      default: return 'Enviar';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl w-full max-h-[90vh] flex flex-col p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Añadir Conocimiento</DialogTitle>
          <DialogDescription>
            {defaultTopic
              ? `El contenido se añadirá a la colección "${defaultTopic}".`
              : "Crea o selecciona una base de conocimiento para tu nuevo contenido."
            }
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form 
            onSubmit={form.handleSubmit(onSubmit, (errors) => {
              console.error('Validation Errors:', errors);
              const firstError = Object.values(errors)[0];
              if (firstError?.message) {
                toast.error(firstError.message as string);
              } else {
                toast.error("Por favor, revisa los campos del formulario.");
              }
            })} 
            className="flex-1 flex flex-col space-y-4 overflow-hidden"
          >
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

            <Tabs 
              value={activeTab} 
              onValueChange={(val) => {
                setActiveTab(val);
                // Limpiar otros campos al cambiar de pestaña para evitar conflictos de validación
                if (val === 'files') {
                  form.setValue('text_content', '');
                  form.setValue('web_url', '');
                } else if (val === 'text') {
                  form.setValue('files', undefined);
                  form.setValue('web_url', '');
                } else if (val === 'web') {
                  form.setValue('files', undefined);
                  form.setValue('text_content', '');
                }
              }} 
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="files">Subir Archivos</TabsTrigger>
                <TabsTrigger value="text">Añadir Texto</TabsTrigger>
                <TabsTrigger value="web">Añadir Web</TabsTrigger>
              </TabsList>
              <TabsContent value="files">
                <Dropzone onDrop={handleDrop} isDragging={isDragging} onDragOver={handleDragOver} onDragLeave={handleDragLeave}>
                  <FormField
                    control={form.control}
                    name="files"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <Input
                            type="file"
                            multiple
                            accept=".pdf,.docx,.txt,.md,.html"
                            onChange={(e) => field.onChange(e.target.files)}
                            disabled={isSubmitting}
                            className="hidden"
                            id="file-upload-input"
                          />
                        </FormControl>
                        <label htmlFor="file-upload-input" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-muted hover:bg-muted/80 transition-colors">
                          <div className="flex flex-col items-center justify-center pt-5 pb-6">
                            <svg className="w-8 h-8 mb-4 text-muted-foreground" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16">
                              <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L7 9m3-3 3 3" />
                            </svg>
                            <p className="mb-2 text-sm text-muted-foreground"><span className="font-semibold">Haz clic para subir</span> o arrastra y suelta</p>
                            <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, MD, HTML</p>
                          </div>
                        </label>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </Dropzone>
                {files && files.length > 0 && (
                  <div className="mt-4 space-y-2 text-sm">
                    <p className="font-medium">Archivos seleccionados:</p>
                    <ScrollArea className="max-h-[200px] w-full rounded-md border p-2">
                      <ul className="list-disc list-inside space-y-1">
                        {Array.from(files as FileList).map((file: File) => (
                          <li key={file.name} className="break-all">
                            <span>{file.name}</span> ({Math.round(file.size / 1024)} KB)
                          </li>
                        ))}
                      </ul>
                    </ScrollArea>
                  </div>
                )}
              </TabsContent>
              <TabsContent value="text">
                <FormField
                  control={form.control}
                  name="text_content"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Contenido de Texto</FormLabel>
                      <FormControl>
                        <TiptapEditor content={field.value || ''} onChange={field.onChange} containerClassName="max-h-[250px] sm:max-h-60 overflow-y-auto" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </TabsContent>
              <TabsContent value="web">
                <div className="p-4 border-dashed border-2 rounded-lg h-48 flex flex-col justify-center">
                  <FormField
                    control={form.control}
                    name="web_url"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-center block mb-2">URL de la página web</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input placeholder="https://ejemplo.com/articulo" {...field} className="pl-10" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </TabsContent>
            </Tabs>

            <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
              <Button type="submit" disabled={isSubmitting} className="relative w-full sm:w-auto">
                {isSubmitting && (
                  <span className="absolute left-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                )}
                <span className={isSubmitting ? 'pl-6' : ''}>{getSubmitButtonText()}</span>
              </Button>
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting} className="w-full sm:w-auto">
                Cancelar
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}