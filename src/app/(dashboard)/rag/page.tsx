'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, BookMarked, Trash2, Github, Edit, Share2, FolderPlus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { UploadDocumentDialog } from './upload-document-dialog';
import { CreateCollectionDialog } from './create-collection-dialog';
import { CollectionAnalysisDialog } from './collection-analysis-dialog';
import { GitHubRepoDialog } from './github-repo-dialog';
import { EditCollectionDialog } from './edit-collection-dialog';
import { ShareCollectionDialog } from './share-collection-dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Collection {
  topic: string;
  document_count: number;
  description?: string;
  team_shared?: boolean;
}

const CollectionCard = ({
  collection,
  onAnalyze,
  onDelete,
  onEdit,
  onShare,
  onAddToWorkspace,
  isAnalyzing,
}: {
  collection: Collection;
  onAnalyze: (topic: string) => void;
  onDelete: (topic: string) => void;
  onEdit: (collection: Collection) => void;
  onShare: (collection: Collection) => void;
  onAddToWorkspace: (collection: Collection) => void;
  isAnalyzing: boolean;
}) => {
  const router = useRouter();

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't navigate if clicking on dropdown or its content
    if ((e.target as HTMLElement).closest('[data-dropdown-trigger]') ||
        (e.target as HTMLElement).closest('[data-dropdown-content]')) {
      return;
    }
    router.push(`/rag/${encodeURIComponent(collection.topic)}`);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="h-full"
    >
      <Card
        className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full"
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
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
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
                  <DropdownMenuItem onClick={() => onEdit(collection)}>
                    <Edit className="mr-2 h-4 w-4" />
                    <span>Editar</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onShare(collection)}>
                    <Share2 className="mr-2 h-4 w-4" />
                    <span>Compartir</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onAddToWorkspace(collection)}>
                    <FolderPlus className="mr-2 h-4 w-4" />
                    <span>Agregar a Workspace</span>
                  </DropdownMenuItem>
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

const StaticCollectionCard = ({
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

  // Estados para editar, compartir y agregar a workspace
  const [isEditCollectionOpen, setIsEditCollectionOpen] = useState(false);
  const [isShareCollectionOpen, setIsShareCollectionOpen] = useState(false);
  const [isAddToWorkspaceOpen, setIsAddToWorkspaceOpen] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  
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

  const handleCollectionCreated = async (newTopic: string) => {
    // Recargar las colecciones para mostrar la nueva
    await fetchCollections();
    // Luego navegar a la nueva colección
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

  const handleEditCollection = (collection: Collection) => {
    setSelectedCollection(collection);
    setIsEditCollectionOpen(true);
  };

  const handleShareCollection = (collection: Collection) => {
    setSelectedCollection(collection);
    setIsShareCollectionOpen(true);
  };

  const handleAddToWorkspace = async (collection: Collection) => {
    setSelectedCollection(collection);
    try {
      const response = await apiClient.get('/api/workspaces');
      setWorkspaces(response.data);
      setIsAddToWorkspaceOpen(true);
    } catch (error) {
      toast.error('Error al cargar los workspaces.');
    }
  };

  const handleEditSuccess = () => {
    fetchCollections();
    setSelectedCollection(null);
  };

  const handleShareSuccess = () => {
    fetchCollections();
    setSelectedCollection(null);
  };

  const handleAddToWorkspaceConfirm = async () => {
    if (!selectedCollection || !selectedWorkspaceId) return;

    try {
      const collectionIdentifier = encodeURIComponent(selectedCollection.topic);
      await apiClient.post(`/api/workspaces/${selectedWorkspaceId}/collections/${collectionIdentifier}/associate`, {});
      toast.success(`Colección "${selectedCollection.topic}" agregada al workspace.`);
      setIsAddToWorkspaceOpen(false);
      setSelectedCollection(null);
      setSelectedWorkspaceId(null);
    } catch (error) {
      toast.error('Error al agregar la colección al workspace.');
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return <p className="text-center py-10">Cargando colecciones...</p>;
    }

    if (collections.length === 0) {
      return (
        <div className="text-center py-20 px-8">
          <FolderKanban className="mx-auto h-16 w-16 text-muted-foreground/50 mb-6" />
          <h3 className="text-xl font-semibold mb-4">No tienes colecciones aún</h3>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
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
      <motion.div layout className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 px-2">
        <AnimatePresence>
          <StaticCollectionCard
            href="/rag/all"
            icon={Library}
            title="Todos los Documentos"
            description="Ver y gestionar todos tus archivos en un solo lugar."
            className="bg-muted"
          />
          <StaticCollectionCard
            href="/rag/repositories"
            icon={Github}
            title="Repositorios"
            description="Ver y gestionar todos tus repositorios de GitHub."
            className="bg-muted"
          />
          {collections.map((collection) => (
            <CollectionCard
              key={collection.topic}
              collection={collection}
              onAnalyze={handleAnalyzeCollection}
              onDelete={openDeleteDialog}
              onEdit={handleEditCollection}
              onShare={handleShareCollection}
              onAddToWorkspace={handleAddToWorkspace}
              isAnalyzing={collectionPollingId !== null && analyzingTopic === collection.topic}
            />
          ))}
          {/* Tarjeta para crear nueva colección */}
          <motion.div
            layout
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="h-full"
          >
            <Card
              className="group border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 transition-all duration-200 flex flex-col items-center justify-center text-center p-6 cursor-pointer h-full"
              onClick={() => setIsCreateOpen(true)}
            >
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
                <Plus className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-1">Crear Colección</h3>
              <p className="text-xs text-muted-foreground">Nuevo tema de documentos</p>
            </Card>
          </motion.div>
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className="p-8 mx-4">
      <div className="flex items-center justify-between mb-12">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <BookMarked className="mr-3 h-8 w-8 text-primary" />
            Colecciones de Conocimientos
          </h1>
          <p className="text-muted-foreground mt-2">Organiza tus documentos en bases de conocimiento.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setIsGitHubRepoOpen(true)} className="bg-primary hover:bg-primary/90">
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

      <EditCollectionDialog
        isOpen={isEditCollectionOpen}
        onOpenChange={setIsEditCollectionOpen}
        onEditSuccess={handleEditSuccess}
        collection={selectedCollection}
      />

      <ShareCollectionDialog
        isOpen={isShareCollectionOpen}
        onOpenChange={setIsShareCollectionOpen}
        onShareSuccess={handleShareSuccess}
        collection={selectedCollection}
      />

      {/* Diálogo para agregar a workspace */}
      <Dialog open={isAddToWorkspaceOpen} onOpenChange={setIsAddToWorkspaceOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Agregar Colección a Workspace</DialogTitle>
            <DialogDescription>
              Selecciona el workspace al que quieres agregar la colección "{selectedCollection?.topic}".
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="workspace-select" className="text-sm font-medium">
                Workspace
              </label>
              <Select value={selectedWorkspaceId || ''} onValueChange={setSelectedWorkspaceId}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona un workspace" />
                </SelectTrigger>
                <SelectContent>
                  {workspaces.map((workspace) => (
                    <SelectItem key={workspace.id} value={workspace.id}>
                      {workspace.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddToWorkspaceOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleAddToWorkspaceConfirm}
              disabled={!selectedWorkspaceId}
            >
              Agregar a Workspace
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
