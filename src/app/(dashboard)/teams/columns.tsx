"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { MoreHorizontal } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export const getColumns = (
  onShareDocuments?: (team: any) => void,
  onShareEvents?: (team: any) => void,
  onShareNotes?: (team: any) => void
): ColumnDef<any>[] => [
  {
    accessorKey: "name",
    header: "Nombre",
  },
  {
    accessorKey: "created_at",
    header: "Creado el",
    cell: ({ row }) => {
      const date = new Date(row.getValue("created_at"));
      return date.toLocaleDateString();
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const team = row.original;

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Abrir menú</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => {
                // Placeholder for edit action
                console.log(`Editar equipo ${team.id}`);
              }}
            >
              Editar
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                // Placeholder for delete action
                console.log(`Eliminar equipo ${team.id}`);
              }}
            >
              Eliminar
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                if (onShareDocuments) onShareDocuments(team);
              }}
            >
              Compartir Documentos
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                if (onShareEvents) onShareEvents(team);
              }}
            >
              Compartir Eventos
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                if (onShareNotes) onShareNotes(team);
              }}
            >
              Compartir Notas
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },
];

// Default export for when handlers are not provided
export const columns = getColumns();
