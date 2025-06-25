// En: src/app/(dashboard)/rag/columns.tsx
'use client';

import { type ColumnDef } from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';

// Este es el tipo de dato que esperamos de la API
export type Document = {
  file_name: string;
  topic: string;
  title: string | null;
  author: string | null;
};

export const columns: ColumnDef<Document>[] = [
  {
    accessorKey: 'title',
    header: 'Título',
    cell: ({ row }: { row: any }) => {
        return <div className="font-medium">{row.original.title || 'Sin título'}</div>
    }
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
            <DropdownMenuItem onClick={() => navigator.clipboard.writeText(document.file_name)}>
              Copiar nombre
            </DropdownMenuItem>
            <DropdownMenuItem>Editar Metadatos</DropdownMenuItem>
            <DropdownMenuItem className="text-destructive">Eliminar Documento</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];
