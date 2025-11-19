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
      className={`relative border-2 rounded-lg transition-colors ${
        isDragging ? 'border-primary bg-primary/10' : 'border-dashed border-gray-300 dark:border-gray-700'
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
  const [activeTab, setActiveTab] = useState('files'); // 'files' o 'text'
  const [isDragging, setIsDragging] = useState(false); // Nuevo estado para drag and drop

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      topic: 'General',
      files: undefined,
      text_content: '',
    },
  });

  const files = form.watch('files');
  
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
      form.clearErrors('files'); // Limpiar errores si se sueltan archivos
    }
  };

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true);
    
    const topicForUpload = defaultTopic || values.topic || 'General';
    const fileNames: string[] = [];
    const formData = new FormData();

    formData.append('topic', topicForUpload);
    if (workspaceId) {
      formData.append('workspace_id', workspaceId);
    }

    try {
      if (activeTab === 'files' && values.files && values.files.length > 0) {
        for (let i = 0; i < values.files.length; i++) {
          formData.append('files', values.files[i]);
          fileNames.push(values.files[i].name);
        }
        toast.info('Subiendo documentos...', {
          description: `A la colección: ${topicForUpload}`,
          id: 'upload-progress'
        });

      } else if (activeTab === 'text' && values.text_content) {
        const textFile = new File([values.text_content], `texto-${Date.now()}.md`, { type: 'text/markdown' });
        formData.append('files', textFile);
        fileNames.push(textFile.name);

        toast.info('Guardando texto como documento...', {
          description: `En la colección: ${topicForUpload}`,
          duration: 0,
          id: 'upload-progress'
        });

      } else {
        toast.error('Por favor, selecciona al menos un archivo o introduce texto.');
        setIsSubmitting(false);
        return;
      }
      
      onUploadStart(fileNames, topicForUpload);
      onOpenChange(false); // Cierra el diálogo inmediatamente

      // La subida ahora ocurre en segundo plano. El componente padre
      // escuchará los eventos de WebSocket para actualizar el estado.
      apiClient.post('/api/documents/upload-document', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }).then(response => {
        // El éxito se maneja a través de WebSockets, pero podemos loguear aquí si es necesario
        console.log('Upload request sent successfully for', fileNames);
        // Opcional: podrías llamar a onUploadSuccess aquí si necesitas hacer algo
        // general después de que la petición se complete, pero el estado de los
        // documentos individuales es manejado por WebSockets.
        onUploadSuccess(fileNames, topicForUpload);
      }).catch(error => {
        // Si la petición inicial falla, mostramos un error genérico.
        // Los fallos de procesamiento de archivos individuales se manejan por WebSockets.
        toast.error('Error al iniciar la subida de documentos.', {
          description: 'Por favor, revisa tu conexión e inténtalo de nuevo.',
        });
        console.error(error);
      }).finally(() => {
        setIsSubmitting(false);
        form.reset();
      });

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
      <DialogContent className="max-w-xl w-full p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Subir Nuevo Documento</DialogTitle>
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
                <Dropzone onDrop={handleDrop} isDragging={isDragging} onDragOver={handleDragOver} onDragLeave={handleDragLeave}>
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
                            className="hidden" // Ocultar el input de archivo original
                            id="file-upload-input"
                          />
                        </FormControl>
                        <label htmlFor="file-upload-input" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-muted hover:bg-muted/80 transition-colors">
                          <div className="flex flex-col items-center justify-center pt-5 pb-6">
                            <svg className="w-8 h-8 mb-4 text-muted-foreground" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16">
                              <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L7 9m3-3 3 3"/>
                            </svg>
                            <p className="mb-2 text-sm text-muted-foreground"><span className="font-semibold">Haz clic para subir</span> o arrastra y suelta</p>
                            <p className="text-xs text-muted-foreground">PDF, DOCX, TXT, MD, HTML (MAX. 5MB)</p>
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
                    <ul className="list-disc list-inside space-y-1">
                      {Array.from(files as FileList).map((file: File) => (
                        <li key={file.name} className="truncate">
                          {file.name} ({Math.round(file.size / 1024)} KB)
                        </li>
                      ))}
                    </ul>
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
            </Tabs>

            <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
              <Button type="submit" disabled={isSubmitting} className="relative w-full sm:w-auto">
                {isSubmitting ? (
                  <>
                    <span className="absolute left-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span className="pl-6">{activeTab === 'files' ? 'Subiendo...' : 'Guardando...'}</span>
                  </>
                ) : (
                  activeTab === 'files' ? 'Subir Documento' : 'Guardar Conocimiento'
                )}
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