'use client';

import { type ColumnDef } from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MoreHorizontal, Loader2, XCircle } from 'lucide-react';

// Definición extendida de Document para incluir estados de subida
export type Document = {
  id?: string; // ID único, especialmente para placeholders
  file_name: string;
  topic: string;
  title: string | null;
  author: string | null;
  team_shared?: boolean | string;
  workspace_id?: string | null;
  created_at?: string; // Para ordenar
  // Campos para el estado de la subida
  status?: 'processing' | 'completed' | 'failed' | 'placeholder';
  progress?: number;
  error?: string;
  document_type?: 'placeholder';
};

// La función ahora recibe los handlers para cada acción
export const getColumns = (
    onPreview: (doc: Document) => void,
    onEdit: (doc: Document) => void,
    onDelete: (doc: Document) => void,
    onAnalyze?: (doc: Document) => void,
    onShare?: (doc: Document) => void,
    onExtractTitle?: (doc: Document) => void
): ColumnDef<Document>[] => [
  {
    accessorKey: 'title',
    header: 'Título',
    enableSorting: true,
    cell: ({ row }) => {
      const doc = row.original;

      if (doc.status === 'processing') {
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="italic">{doc.title || 'Procesando...'}</span>
          </div>
        );
      }

      if (doc.status === 'failed') {
        return (
          <div className="flex items-center gap-2 text-destructive">
            <XCircle className="h-4 w-4" />
            <span className="italic" title={doc.error}>Error al procesar</span>
          </div>
        );
      }

      return (
        <div className="font-medium flex items-center">
          {doc.title || <span className="text-muted-foreground italic">Sin título</span>}
          {doc.team_shared && (
            <span className="ml-2 text-blue-500" title="Compartido con equipo">👥</span>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: 'file_name',
    header: 'Nombre del Archivo',
    enableSorting: true,
  },
  {
    accessorKey: 'topic',
    header: 'Base de Conocimiento',
    enableSorting: true,
  },
  {
    id: 'actions',
    cell: ({ row }) => {
      const document = row.original;
      const isProcessing = document.status === 'processing';

      if (isProcessing) {
        return (
          <div className="flex items-center justify-center pr-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        );
      }

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" disabled={isProcessing}>
              <span className="sr-only">Abrir menú</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Acciones</DropdownMenuLabel>
            <DropdownMenuItem onClick={() => onPreview(document)}>
              Previsualizar
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onEdit(document)}>
              Editar Metadatos
            </DropdownMenuItem>
            {onAnalyze && (
              <DropdownMenuItem onClick={() => onAnalyze(document)}>
                Analizar Documento
              </DropdownMenuItem>
            )}
            {onShare && (
              <DropdownMenuItem onClick={() => onShare(document)}>
                Compartir Documento
              </DropdownMenuItem>
            )}
            {onExtractTitle && (
              <DropdownMenuItem onClick={() => onExtractTitle(document)}>
                Extraer Título
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onDelete(document)} className="text-destructive focus:bg-destructive/30">
              Eliminar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];
