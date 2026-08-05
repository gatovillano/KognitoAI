'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Plus, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, BookMarked, Trash2, Github, Edit, Share2, Upload, CheckCircle, XCircle, Clock, Network, ChevronDown, Settings, Text, Brain, FileText } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { useDraggable, useDroppable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';

export interface Collection {
  id?: string;
  name?: string;
  topic: string;
  document_count: number;
  description?: string;
  team_shared?: boolean;
  has_knowledge_graph?: boolean;
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string;
  parent_id?: string | null;
  subcollection_count?: number;
}

interface CollectionDisplayProps {
  collection: Collection;
  type: 'list' | 'detail'; // 'list' para la vista de listado, 'detail' para la vista de detalle de una colección
  workspaceId?: string; // Opcional para el contexto del workspace
  onAnalyze?: (topic: string, workspaceId?: string) => void;
  onDelete?: (topic: string, workspaceId?: string) => void;
  onEdit?: (collection: Collection, workspaceId?: string) => void;
  onShare?: (collection: Collection, workspaceId?: string) => void;
  onProcessKnowledgeGraph?: (topic: string, workspaceId?: string) => void;
  onProcessAnthropologicalGraph?: (topic: string, workspaceId?: string) => void;
  onUploadDocument?: (topic: string, workspaceId?: string) => void;
  onExtractTitles?: (topic: string, workspaceId?: string) => void;
  onSemanticSummary?: (topic: string, workspaceId?: string) => void;
  onChat?: (collection: Collection) => void;
  isAnalyzing?: boolean;
  isProcessingKnowledgeGraph?: boolean;
  className?: string; // Para estilos adicionales
  onLinkProfile?: (collection: Collection) => void;
}

export const CollectionDisplay = ({
  collection,
  type,
  workspaceId,
  onAnalyze,
  onDelete,
  onEdit,
  onShare,
  onProcessKnowledgeGraph,
  onProcessAnthropologicalGraph,
  onUploadDocument,
  onExtractTitles,
  onSemanticSummary,
  onChat,
  isAnalyzing = false,
  isProcessingKnowledgeGraph = false,
  className,
  onLinkProfile,
}: CollectionDisplayProps) => {
  const router = useRouter();

  const ensureString = (val: any) => {
    if (typeof val === 'string') return val;
    if (val && typeof val === 'object') {
      if ('description' in val && typeof val.description === 'string') {
        return val.description;
      }
      if ('key_themes' in val || 'description' in val) {
        // Es un objeto de descripción enriquecida, extraer el texto
        const parts = [];
        if (val.description && typeof val.description === 'string') parts.push(val.description);
        if (val.key_themes && Array.isArray(val.key_themes)) {
          parts.push(`Temas: ${val.key_themes.join(', ')}`);
        }
        return parts.join('. ') || 'Sin descripción.';
      }
      return JSON.stringify(val);
    }
    return 'Sin descripción.';
  };

  const handleCardClick = (e: React.MouseEvent) => {
    if (type === 'list') {
      // Evitar la navegación si se hace clic en el menú desplegable
      if ((e.target as HTMLElement).closest('[data-dropdown-trigger]') ||
        (e.target as HTMLElement).closest('[data-dropdown-content]')) {
        return;
      }
      const collectionIdentifier = collection.name || collection.topic || '';
      const url = `/rag/${encodeURIComponent(collectionIdentifier)}`;
      // La API ahora provee workspace_id dentro del objeto collection
      const activeWorkspaceId = collection.workspace_id || workspaceId;
      if (activeWorkspaceId) {
        router.push(`/workspaces/${activeWorkspaceId}/collections/${encodeURIComponent(collectionIdentifier)}`);
      } else {
        router.push(url);
      }
    }
  };

  const handleAction = (action: (topic: string, workspaceId?: string) => void) => {
    return (e: React.MouseEvent) => {
      e.stopPropagation(); // Evitar que el clic se propague al Card
      const collectionIdentifier = collection.name || collection.topic || '';
      action(collectionIdentifier, collection.workspace_id);
    };
  };

  const renderActions = () => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 p-0 hover:bg-muted"
          onClick={(e) => e.stopPropagation()}
          data-dropdown-trigger
        >
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()} data-dropdown-content>
        {onChat && (
          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onChat(collection); }}>
            <Brain className="mr-2 h-4 w-4 text-primary" />
            <span className="font-medium text-primary">Chatear con Colección</span>
          </DropdownMenuItem>
        )}
        {onAnalyze && (
          <DropdownMenuItem onClick={handleAction(onAnalyze)} disabled={isAnalyzing}>
            <ScanSearch className="mr-2 h-4 w-4" />
            <span>Analizar Colección</span>
          </DropdownMenuItem>
        )}
        {onProcessKnowledgeGraph && (
          <DropdownMenuItem onClick={handleAction(onProcessKnowledgeGraph)} disabled={isProcessingKnowledgeGraph}>
            <Network className="mr-2 h-4 w-4" />
            <span>Crear Grafo</span>
          </DropdownMenuItem>
        )}
        {onProcessAnthropologicalGraph && (
          <DropdownMenuItem onClick={handleAction(onProcessAnthropologicalGraph)} disabled={isProcessingKnowledgeGraph}>
            <BookMarked className="mr-2 h-4 w-4 text-indigo-500" />
            <span className="font-medium text-indigo-600 dark:text-indigo-400">Grafo Antropológico (1:N)</span>
          </DropdownMenuItem>
        )}

        {onEdit && (
          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(collection, workspaceId); }}>
            <Edit className="mr-2 h-4 w-4" />
            <span>Editar</span>
          </DropdownMenuItem>
        )}
        {onShare && (
          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onShare(collection, workspaceId); }}>
            <Share2 className="mr-2 h-4 w-4" />
            <span>Compartir</span>
          </DropdownMenuItem>
        )}
        {onDelete && (
          <DropdownMenuItem onClick={handleAction(onDelete)} className="text-red-500 focus:text-red-500 focus:bg-destructive/10">
            <Trash2 className="mr-2 h-4 w-4" />
            <span>Eliminar</span>
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  const renderDetailActions = () => (
    <div className="flex items-center gap-2">
      {onChat && (
        <Button onClick={(e) => { e.stopPropagation(); onChat(collection); }} className="gap-2">
          <Brain className="h-4 w-4" />
          Chatear con Colección
        </Button>
      )}
      {onAnalyze && (
        <Button onClick={handleAction(onAnalyze)} variant="outline" disabled={isAnalyzing}>
          {isAnalyzing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ScanSearch className="mr-2 h-4 w-4" />}
          Analizar Colección
        </Button>
      )}
      {onUploadDocument && (
        <Button onClick={handleAction(onUploadDocument)}>
          <Upload className="mr-2 h-4 w-4" />
          Subir a esta Colección
        </Button>
      )}
      {onExtractTitles && (
        <Button onClick={handleAction(onExtractTitles)} variant="outline" disabled={isAnalyzing}>
          <Text className="mr-2 h-4 w-4" />
          Extraer Títulos
        </Button>
      )}
      {onSemanticSummary && (
        <Button onClick={handleAction(onSemanticSummary)} variant="outline" disabled={isAnalyzing}>
          <Brain className="mr-2 h-4 w-4" />
          Resumen Semántico
        </Button>
      )}
      {onProcessKnowledgeGraph && (
        <Button onClick={handleAction(onProcessKnowledgeGraph)} variant="outline" disabled={isProcessingKnowledgeGraph}>
          {isProcessingKnowledgeGraph ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Network className="mr-2 h-4 w-4" />}
          Crear Grafo
        </Button>
      )}
      {onProcessAnthropologicalGraph && (
        <Button onClick={handleAction(onProcessAnthropologicalGraph)} variant="outline" className="border-indigo-500/30 hover:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400" disabled={isProcessingKnowledgeGraph}>
          {isProcessingKnowledgeGraph ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookMarked className="mr-2 h-4 w-4" />}
          Grafo Antropológico (1:N)
        </Button>
      )}
    </div>
  );

  const {
    attributes,
    listeners,
    setNodeRef: setDraggableRef,
    transform,
    isDragging,
  } = useDraggable({
    id: `draggable-${collection.id || collection.name || collection.topic}`,
    data: { collection },
  });

  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: `droppable-${collection.id || collection.name || collection.topic}`,
    data: { collection },
  });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 50 : undefined,
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={`h-full w-full transition-all duration-200 ${isOver ? 'ring-2 ring-primary ring-offset-2 scale-[1.02]' : ''}`}
      style={style}
      ref={setDroppableRef}
    >
      <div 
        ref={setDraggableRef} 
        {...attributes} 
        {...listeners}
        className="h-full w-full"
      >
        <Card
          className={`cursor-pointer h-full transition-all hover:border-primary/20 ${isOver ? 'border-primary shadow-lg bg-primary/5' : ''} ${className || ''}`}
          onClick={handleCardClick}
        >
        <CardHeader className="pb-3">
          <CardTitle className="flex items-start gap-3 flex-wrap overflow-hidden">
            <div className="flex items-center gap-3 min-w-0 max-w-full">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <FolderKanban className="h-5 w-5 text-primary" />
              </div>
              <span className="font-semibold text-lg whitespace-normal break-words flex-shrink min-w-0 text-wrap">{collection.name || collection.topic}</span>
              {collection.team_shared && (
                <span className="text-blue-500" title="Compartido con equipo">👥</span>
              )}
            </div>
            {type === 'list' && (
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {renderActions()}
              </div>
            )}
            {type === 'detail' && (
              <div className="flex items-center gap-1">
                {renderDetailActions()}
              </div>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0 flex-grow">
          {isAnalyzing ? (
            <div className="flex items-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              <span>Analizando...</span>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
              {ensureString(collection.description)}
            </p>
          )}
        </CardContent>
        <div className="flex items-center justify-between p-3 border-t border-border/50">
          <div className="flex items-center gap-3">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-default">
                    <FileText className="h-3.5 w-3.5" />
                    <span>{collection.document_count ?? 0}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{collection.document_count ?? 0} documento(s)</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-default">
                    <FolderKanban className="h-3.5 w-3.5" />
                    <span>{collection.subcollection_count ?? 0}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{collection.subcollection_count ?? 0} subcolección(es)</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div className="flex items-center gap-2">
            {collection.workspace_name && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div
                      className="inline-flex items-center gap-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full"
                      style={{
                        backgroundColor: collection.workspace_color ? `${collection.workspace_color}15` : '#f3f4f6',
                        border: `1px solid ${collection.workspace_color ? `${collection.workspace_color}30` : '#e5e7eb'}`
                      }}
                    >
                      <span
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: collection.workspace_color || '#888888' }}
                      ></span>
                      <span style={{ color: collection.workspace_color || '#374151' }}>
                        {collection.workspace_name}
                      </span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Workspace: {collection.workspace_name}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </div>
      </Card>
      </div>
    </motion.div>
  );
};

export const StaticCollectionCard = ({
  href,
  icon: Icon,
  title,
  description,
  className,
}: {
  href: string;
  icon: React.ElementType;
  title: string;
  description: string;
  className?: string;
}) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="h-full w-full"
    >
      <Link href={href} className="h-full block">
        <Card className={`cursor-pointer h-full hover:border-primary/20 ${className || ''}`}>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-start gap-3 flex-wrap overflow-hidden">
              <div className="flex items-center gap-3 min-w-0">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <span className="font-semibold text-lg whitespace-normal break-words flex-shrink min-w-0 text-wrap">{title}</span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-grow">
            <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
              {description}
            </p>
          </CardContent>
        </Card>
      </Link>
    </motion.div>
  );
};