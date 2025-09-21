'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Plus, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, BookMarked, Trash2, Github, Edit, Share2, Upload, CheckCircle, XCircle, Clock, Network, ChevronDown, Settings, Text, Brain } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface Collection {
  topic: string;
  document_count: number;
  description?: string;
  team_shared?: boolean;
  has_knowledge_graph?: boolean;
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
  onUploadDocument?: (topic: string, workspaceId?: string) => void;
  onExtractTitles?: (topic: string, workspaceId?: string) => void;
  onSemanticSummary?: (topic: string, workspaceId?: string) => void;
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
  onUploadDocument,
  onExtractTitles,
  onSemanticSummary,
  isAnalyzing = false,
  isProcessingKnowledgeGraph = false,
  className,
  onLinkProfile,
}: CollectionDisplayProps) => {
  const router = useRouter();

  const handleCardClick = (e: React.MouseEvent) => {
    if (type === 'list') {
      // Evitar la navegación si se hace clic en el menú desplegable
      if ((e.target as HTMLElement).closest('[data-dropdown-trigger]') ||
          (e.target as HTMLElement).closest('[data-dropdown-content]')) {
        return;
      }
      router.push(workspaceId 
        ? `/workspaces/${workspaceId}/collections/${encodeURIComponent(collection.topic)}`
        : `/rag/${encodeURIComponent(collection.topic)}`
      );
    }
  };

  const handleAction = (action: (topic: string, workspaceId?: string) => void) => {
    return (e: React.MouseEvent) => {
      e.stopPropagation(); // Evitar que el clic se propague al Card
      action(collection.topic, workspaceId);
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
    </div>
  );

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={`h-full ${type === 'list' ? '' : 'w-full'}`}
    >
      <Card
        className={`group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full ${className || ''}`}
        onClick={handleCardClick}
      >
        <CardHeader className="pb-3">
          <CardTitle className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <FolderKanban className="h-5 w-5 text-primary" />
              </div>
              <span className="font-semibold text-lg truncate">{collection.topic}</span>
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
              {collection.description || 'Sin descripción.'}
            </p>
          )}
        </CardContent>
        <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50">
          <span>{collection.document_count} documento(s)</span>
        </CardFooter>
      </Card>
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
      className="h-full"
    >
      <Link href={href} className="h-full block">
        <Card className={`group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full ${className || ''}`}>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-start gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <span className="font-semibold text-lg truncate">{title}</span>
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