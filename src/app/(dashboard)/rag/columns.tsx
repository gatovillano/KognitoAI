'use client';

import { type ColumnDef } from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';

export type Document = {
  file_name: string;
  topic: string;
  title: string | null;
  author: string | null;
  team_shared?: boolean | string; // Indicates if shared with a team, can be boolean or team name/id
  workspace_id?: string | null; // Añadido para soportar eliminación en workspaces
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
    cell: ({ row }) => (
      <div className="font-medium flex items-center">
        {row.original.title || <span className="text-muted-foreground italic">Sin título</span>}
        {row.original.team_shared && (
          <span className="ml-2 text-blue-500" title="Compartido con equipo">👥</span>
        )}
      </div>
    ),
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
