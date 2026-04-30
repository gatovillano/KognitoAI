import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MoreHorizontal, FileText, Edit, Trash2, ScanSearch, Text, Share2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

import { Document } from './columns';

interface DocumentCardProps {
  document: Document;
  onPreview: (doc: Document) => void;
  onEdit: (doc: Document) => void;
  onDelete: (doc: Document) => void;
  onAnalyze: (doc: Document) => void;
  onShare: (doc: Document) => void;
  onExtractTitle: (doc: Document) => void;
  onMoveToCollection?: (doc: Document) => void;
}

export function DocumentCard({
  document,
  onPreview,
  onEdit,
  onDelete,
  onAnalyze,
  onShare,
  onExtractTitle,
  onMoveToCollection,
}: DocumentCardProps) {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <span>{document.title || document.file_name}</span>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onPreview(document)}>
                Ver Contenido
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onEdit(document)}>
                Editar
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDelete(document)}>
                Eliminar
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onAnalyze(document)}>
                Analizar Documento
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onExtractTitle(document)}>
                Extraer Título
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onShare(document)}>
                Compartir
              </DropdownMenuItem>
              {onMoveToCollection && (
                <DropdownMenuItem onClick={() => onMoveToCollection(document)}>
                  Mover a Colección
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground flex-grow">
        <p>Autor: {document.author || 'N/A'}</p>
        <p>Tipo: <Badge variant="secondary">{document.document_type}</Badge></p>
        <p>Fecha: {document.created_at && !isNaN(new Date(document.created_at).getTime()) ? format(new Date(document.created_at), "PPP", { locale: es }) : 'N/A'}</p>
        {document.status && (
          <p>Estado: <Badge variant="outline" className={`ml-2 ${document.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : document.status === 'processing' ? 'bg-blue-100 text-blue-800' : document.status === 'failed' ? 'bg-red-100 text-red-800' : ''}`}>
            {document.status === 'pending' ? 'Pendiente' : document.status === 'processing' ? 'Procesando' : document.status === 'failed' ? 'Error' : ''}
          </Badge></p>
        )}
      </CardContent>
    </Card>
  );
}
