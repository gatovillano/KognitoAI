// En: src/app/(dashboard)/rag/page.tsx (versión final y funcional)
'use client';

import { useEffect, useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { type ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, Upload } from 'lucide-react';
import { toast } from 'sonner';

import { DataTable } from './data-table';
import { type Document } from './columns';
import apiClient from '@/lib/api';

import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { UploadDocumentDialog } from './upload-document-dialog';
import { PreviewDocumentDialog } from './preview-document-dialog';
// Aún no hemos creado los diálogos de editar y eliminar, los añadiremos después

export default function RagManagementPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Estados para controlar los diálogos
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  // const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  // const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);


  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/list-documents');
      setDocuments(response.data);
    } catch (error) {
      toast.error('Error al cargar los documentos.');
      console.error('Error fetching documents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Definimos las columnas aquí para que tengan acceso a los handlers de estado
  const columns: ColumnDef<Document>[] = useMemo(() => [
    {
      accessorKey: 'title',
      header: 'Título',
      cell: ({ row }) => <div className="font-medium">{row.original.title || 'Sin título'}</div>
    },
    {
      accessorKey: 'file_name',
      header: 'Nombre del Archivo',
    },
    {
      accessorKey: 'topic',
      header: 'Base de Conocimiento',
    },
    {
      id: 'actions',
      cell: ({ row }) => {
        const document = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Abrir menú</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Acciones</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => setDocumentToPreview(document)}>
                Previsualizar Contenido
              </DropdownMenuItem>
              <DropdownMenuItem disabled>Editar Metadatos</DropdownMenuItem>
              <DropdownMenuItem className="text-destructive" disabled>
                Eliminar Documento
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ], []);

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-3xl font-bold">Base de Conocimiento (RAG)</h1>
          <p className="text-muted-foreground">
            Gestiona los documentos que alimentan la memoria de tu IA.
          </p>
        </div>
        <Button onClick={() => setIsUploadOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Subir Documento
        </Button>
      </div>

      <div className="flex-grow">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
              <p>Cargando documentos...</p>
          </div>
        ) : (
          <DataTable columns={columns} data={documents} />
        )}
      </div>

      {/* Renderizamos los diálogos aquí */}
      <UploadDocumentDialog 
        isOpen={isUploadOpen} 
        onOpenChange={setIsUploadOpen}
        onUploadSuccess={fetchDocuments}
      />
      <PreviewDocumentDialog
        isOpen={!!documentToPreview}
        onOpenChange={(open) => !open && setDocumentToPreview(null)}
        document={documentToPreview}
      />
    </div>
  );
}
