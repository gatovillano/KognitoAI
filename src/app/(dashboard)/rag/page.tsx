'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, BookMarked, Trash2, Github } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { UploadDocumentDialog } from './upload-document-dialog';
import { CreateCollectionDialog } from './create-collection-dialog';
import { CollectionAnalysisDialog } from './collection-analysis-dialog';
import { GitHubRepoDialog } from './github-repo-dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';

interface Collection {
  topic: string;
  document_count: number;
  description?: string;
}

const CollectionCard = ({
  collection,
  onAnalyze,
  onDelete,
  isAnalyzing,
}: {
  collection: Collection;
  onAnalyze: (topic: string) => void;
  onDelete: (topic: string) => void;
  isAnalyzing: boolean;
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
      <Card className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full relative">
        <Link href={`/rag/${encodeURIComponent(collection.topic)}`} className="absolute inset-0 z-0" aria-label={`Ver colección ${collection.topic}`}></Link>
        <CardHeader className="pb-3 z-10">
          <CardTitle className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <FolderKanban className="h-5 w-5 text-primary" />
              </div>
              <span className="font-semibold text-lg truncate">{collection.topic}</span>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8 p-0 hover:bg-muted" onClick={(e) => e.stopPropagation()}>
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                  <DropdownMenuItem onClick={() => onAnalyze(collection.topic)}>
                    <ScanSearch className="mr-2 h-4 w-4" />
                    <span>Analizar Colección</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onDelete(collection.topic)} className="text-red-500 focus:text-red-500 focus:bg-destructive/10">
                    <Trash2 className="mr-2 h-4 w-4" />
                    <span>Eliminar</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0 flex-grow z-10">
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
        <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50 z-10">
          <span>{collection.document_count} documento(s)</span>
        </CardFooter>
      </Card>
    </motion.div>
  );
};

const StaticCollectionCard = ({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: React.ElementType;
  title: string;
  description: string;
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
        <Card className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full">
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

export default function RagCollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isGitHubRepoOpen, setIsGitHubRepoOpen] = useState(false);
  const [deletingTopic, setDeletingTopic] = useState<string | null>(null);
  
  const [collectionAnalysisResult, setCollectionAnalysisResult] = useState<any>(null);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);
  const [analyzingTopic, setAnalyzingTopic] = useState<string | null>(null);
  
  const router = useRouter();

  const fetchCollections = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/list-collections');
      setCollections(response.data);
    } catch (error) {
      toast.error('Error al cargar las colecciones.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchCollections(); }, [fetchCollections]);

  const handleCollectionCreated = (newTopic: string) => {
    router.push(`/rag/${encodeURIComponent(newTopic)}`);
  };

  const handleAnalyzeCollection = async (topic: string) => {
    if (collectionPollingId) {
      toast.info("Ya hay un análisis en progreso. Por favor, espera.");
      return;
    }
    try {
      setCollectionAnalysisResult(null); 
      setAnalyzingTopic(topic);
      const response = await apiClient.post('/api/start-collection-analysis', { topic });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de la colección "${topic}" iniciado.`);
    } catch (error) {
      toast.error("No se pudo iniciar el análisis de la colección.");
      setAnalyzingTopic(null);
    }
  };

  useEffect(() => {
    if (!collectionPollingId) return;

    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error } = response.data;

        if (status === 'completed') {
          clearInterval(poller);
          setCollectionAnalysisResult(result);
          setIsCollectionAnalysisOpen(true);
          toast.success(`¡Análisis de "${analyzingTopic}" completado!`);
          setCollectionPollingId(null);
          setAnalyzingTopic(null);
        } else if (status === 'failed') {
          clearInterval(poller);
          toast.error(`El análisis de "${analyzingTopic}" falló.`, { description: error || "Ocurrió un error." });
          setCollectionPollingId(null);
          setAnalyzingTopic(null);
        }
      } catch (err) {
        clearInterval(poller);
        toast.error("Error al obtener el resultado del análisis.");
        setCollectionPollingId(null);
        setAnalyzingTopic(null);
      }
    }, 5000);

    return () => clearInterval(poller);
  }, [collectionPollingId, analyzingTopic]);

  const handleAnalysisDialogClose = (isOpen: boolean) => {
    setIsCollectionAnalysisOpen(isOpen);
    if (!isOpen) {
      setCollectionAnalysisResult(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingTopic) return;
    const toastId = toast.loading(`Eliminando colección...`);
    try {
      await apiClient.post('/api/delete-collection', { topic: deletingTopic });
      toast.success(`Colección "${deletingTopic}" eliminada.`, { id: toastId });
      fetchCollections();
    } catch (error) {
      toast.error(`Error al eliminar la colección "${deletingTopic}".`, { id: toastId });
    } finally {
      setDeletingTopic(null);
    }
  };

  const openDeleteDialog = (topic: string) => {
    setDeletingTopic(topic);
  };

  const renderContent = () => {
    if (isLoading) {
      return <p className="text-center py-10">Cargando colecciones...</p>;
    }

    if (collections.length === 0) {
      return (
        <div className="text-center py-16">
          <FolderKanban className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No tienes colecciones aún</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Las colecciones te ayudan a organizar tus documentos por temas. ¡Crea tu primera colección para empezar!
          </p>
          <Button onClick={() => setIsCreateOpen(true)} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            Crear tu primera Colección
          </Button>
        </div>
      );
    }

    return (
      <motion.div layout className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <AnimatePresence>
          <StaticCollectionCard
            href="/rag/all"
            icon={Library}
            title="Todos los Documentos"
            description="Ver y gestionar todos tus archivos en un solo lugar."
          />
          <StaticCollectionCard
            href="/rag/repositories"
            icon={Github}
            title="Repositorios"
            description="Ver y gestionar todos tus repositorios de GitHub."
          />
          {collections.map((collection) => (
            <CollectionCard
              key={collection.topic}
              collection={collection}
              onAnalyze={handleAnalyzeCollection}
              onDelete={openDeleteDialog}
              isAnalyzing={collectionPollingId !== null && analyzingTopic === collection.topic}
            />
          ))}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <BookMarked className="mr-3 h-8 w-8 text-primary" />
            Gestión de Documentos
          </h1>
          <p className="text-muted-foreground mt-2">Organiza tus documentos en bases de conocimiento.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setIsGitHubRepoOpen(true)}>
            <Github className="mr-2 h-4 w-4" />
            Añadir Repositorio
          </Button>
          <Button size="lg" onClick={() => setIsUploadOpen(true)} className="bg-primary hover:bg-primary/90">
            <Plus className="mr-2 h-5 w-5" />
            Subir Documento
          </Button>
        </div>
      </div>

      {renderContent()}

      <UploadDocumentDialog isOpen={isUploadOpen} onOpenChange={setIsUploadOpen} onUploadSuccess={fetchCollections} />
      <CreateCollectionDialog isOpen={isCreateOpen} onOpenChange={setIsCreateOpen} onCreateSuccess={handleCollectionCreated} />
      <GitHubRepoDialog isOpen={isGitHubRepoOpen} onOpenChange={setIsGitHubRepoOpen} onSuccess={fetchCollections} />
      <CollectionAnalysisDialog
        isOpen={isCollectionAnalysisOpen}
        onOpenChange={handleAnalysisDialogClose}
        analysis={collectionAnalysisResult}
        topic={analyzingTopic ?? ''}
      />
      <AlertDialog open={!!deletingTopic} onOpenChange={(open) => !open && setDeletingTopic(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y eliminará la colección "{deletingTopic}" y todos sus documentos permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-destructive hover:bg-destructive/90">Sí, eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
