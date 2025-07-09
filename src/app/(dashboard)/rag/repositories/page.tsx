// En: src/app/(dashboard)/rag/repositories/page.tsx

'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Upload, History, Loader2, ScanSearch, FileText, FolderKanban, Text, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import { DataTable } from '../data-table';
import { getColumns, type Document } from '../columns';

// Definir un tipo extendido para documentos de GitHub que incluye repo_url
interface GitHubDocument extends Document {
  repo_url?: string;
}
import apiClient from '@/lib/api';
import { UploadDocumentDialog } from '../upload-document-dialog';
import { PreviewDocumentDialog } from '../preview-document-dialog';
import { EditDocumentDialog } from '../edit-document-dialog';
import { DeleteConfirmationDialog } from '../delete-confirmation-dialog';
import { AnalysisResultDialog } from '../analysis-result-dialog';
import { CollectionAnalysisDialog } from '../collection-analysis-dialog';
import { ShareDocumentDialog } from '../share-document-dialog';
import { GitHubRepoDialog } from '../github-repo-dialog';
import { UpdateRepositoryDialog } from '../update-repository-dialog';

export default function RepositoriesPage() {
  const [documents, setDocuments] = useState<GitHubDocument[]>([]);
  const [repositoriesData, setRepositoriesData] = useState<{ repo_url: string, repo_name: string }[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Estados para diálogos
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isGitHubRepoOpen, setIsGitHubRepoOpen] = useState(false);
  const [isUpdateRepoOpen, setIsUpdateRepoOpen] = useState(false);
  const [repoToUpdate, setRepoToUpdate] = useState<{name: string, url: string} | null>(null);
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [documentToShare, setDocumentToShare] = useState<Document | null>(null);
  const [isShareOpen, setIsShareOpen] = useState(false);
  
  // Estados para análisis de documento individual
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null);
  const [docAnalysisResult, setDocAnalysisResult] = useState<any>(null);
  const [isDocAnalysisOpen, setIsDocAnalysisOpen] = useState(false);
  const [docPollingId, setDocPollingId] = useState<string | null>(null);

  // Estados para análisis de colección completa
  const [collectionAnalysisResult, setCollectionAnalysisResult] = useState<any>(null);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);

  // Estados para actualización de repositorios
  const [updatePollingId, setUpdatePollingId] = useState<string | null>(null);
  const [updatingRepoName, setUpdatingRepoName] = useState<string | null>(null);

  // Estado para el historial de análisis
  const [savedAnalyses, setSavedAnalyses] = useState<any[]>([]);

  const fetchPageData = useCallback(async () => {
    setIsLoading(true);
    try {
        const [docsRes, reposRes, analysesRes] = await Promise.all([
          apiClient.post('/api/github/list-github-documents', {}),
          apiClient.post('/api/github/list-github-repositories', {}),
          apiClient.post('/api/get-saved-analyses', { topic: 'Repositories', all: true })
        ]);
        
        // Confiar en el filtrado del backend como en las páginas de topics
        // Intentar extraer file_name de result_payload si está disponible
        const repoAnalyses = analysesRes.data.map((analysis: any) => {
          let fileName = 'Análisis sin título';
          if (analysis.result_payload && typeof analysis.result_payload === 'object') {
            fileName = analysis.result_payload.file_name || analysis.result_payload.title || fileName;
          }
          return {
            ...analysis,
            file_name: fileName
          };
        });
        
        setDocuments(docsRes.data);
        setRepositoriesData(reposRes.data);
        setSavedAnalyses(repoAnalyses);
        console.log('Análisis guardados:', repoAnalyses.length);
        toast.info(`Análisis guardados: ${repoAnalyses.length}`);
    } catch (error) {
      toast.error('Error al cargar los datos de los repositorios.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPageData();
  }, [fetchPageData]);

  useEffect(() => {
    const handleUpdateAnalysisHistory = () => {
      fetchPageData();
    };
    window.addEventListener('updateAnalysisHistory', handleUpdateAnalysisHistory);
    return () => {
      window.removeEventListener('updateAnalysisHistory', handleUpdateAnalysisHistory);
    };
  }, [fetchPageData]);

  // --- Handlers de Análisis ---

  const handleAnalyzeDocument = async (doc: Document) => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    setDocumentToAnalyze(doc);
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: doc.file_name });
      setDocPollingId(response.data.task_id);
      toast.info(`Análisis para "${doc.file_name}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis del documento."); }
  };
  
  const handleAnalyzeCollection = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/start-collection-analysis', { topic: 'Repositories' });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de la colección de repositorios iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis de la colección."); }
  };

  // --- Polling para Análisis de Documento ---
  useEffect(() => {
    if (!docPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${docPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setDocPollingId(null); setDocAnalysisResult(result);
          setIsDocAnalysisOpen(true); toast.success("¡Análisis de documento completado!"); fetchPageData();
        } else if (status === 'failed') {
          clearInterval(poller); setDocPollingId(null); toast.error("El análisis del documento falló: " + error);
        }
      } catch (err) { clearInterval(poller); setDocPollingId(null); toast.error("Error al consultar el análisis."); }
    }, 5000);
    return () => clearInterval(poller);
  }, [docPollingId, fetchPageData]);

  // --- Polling para Análisis de Colección ---
  useEffect(() => {
    if (!collectionPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setCollectionPollingId(null); setCollectionAnalysisResult(result);
          setIsCollectionAnalysisOpen(true); toast.success("¡Análisis de colección completado!"); fetchPageData();
        } else if (status === 'failed') {
          clearInterval(poller); setCollectionPollingId(null); toast.error("El análisis de la colección falló: " + error);
        }
      } catch (err) { clearInterval(poller); setCollectionPollingId(null); toast.error("Error al consultar el análisis."); }
    }, 5000);
    return () => clearInterval(poller);
  }, [collectionPollingId, fetchPageData]);

  // --- Polling para Actualización de Repositorios ---
  useEffect(() => {
    if (!updatePollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/analysis/get-analysis-result/${updatePollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller);
          setUpdatePollingId(null);
          setUpdatingRepoName(null);
          toast.success(`¡Repositorio ${updatingRepoName} actualizado correctamente!`);
          fetchPageData();
        } else if (status === 'failed') {
          clearInterval(poller);
          setUpdatePollingId(null);
          setUpdatingRepoName(null);
          toast.error(`Error al actualizar el repositorio: ${error}`);
        }
      } catch (err) {
        clearInterval(poller);
        setUpdatePollingId(null);
        setUpdatingRepoName(null);
        toast.error("Error al consultar el estado de la actualización.");
      }
    }, 3000); // Polling cada 3 segundos para actualizaciones
    return () => clearInterval(poller);
  }, [updatePollingId, updatingRepoName, fetchPageData]);

  // --- Handler para Extraer Títulos de la Colección ---
  const handleExtractTitles = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/extract-title', { topic: 'Repositories' });
      toast.info(`Extracción de títulos para la colección de repositorios iniciada.`);
      fetchPageData();
    } catch (error) { toast.error("No se pudo iniciar la extracción de títulos."); }
  };

  // --- Handler para Extraer Título de un Documento Individual ---
  const handleExtractTitleForDocument = async (doc: Document) => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/extract-title', { file_name: doc.file_name });
      toast.info(`Extracción de título para "${doc.file_name}" iniciada.`);
      fetchPageData();
    } catch (error) { toast.error(`No se pudo iniciar la extracción de título para "${doc.file_name}".`); }
  };

  // --- Handler para Actualizar Repositorio ---
  const handleUpdateRepository = async (repoName: string, repoUrl: string) => {
    if (docPollingId || collectionPollingId || updatePollingId) {
      toast.info("Ya hay un proceso en progreso.");
      return;
    }

    try {
      const response = await apiClient.post("/api/github/update-repository", {
        repo_url: repoUrl,
      });

      setUpdatePollingId(response.data.task_id);
      setUpdatingRepoName(repoName);
      toast.info(`Actualización del repositorio "${repoName}" iniciada en segundo plano.`);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Error al iniciar la actualización del repositorio.");
    }
  };

  // Usar datos de repositorios directamente desde la API
  const repositories = useMemo(() => {
    return repositoriesData.map(repo => ({
      name: repo.repo_name,
      url: repo.repo_url,
      files: documents.filter(doc => doc.repo_url === repo.repo_url)
    }));
  }, [repositoriesData, documents]);

  const columns = useMemo(() => getColumns(
      (doc) => setDocumentToPreview(doc),
      (doc) => setDocumentToEdit(doc),
      (doc) => setDocumentToDelete(doc),
      handleAnalyzeDocument,
      (doc) => {
        setDocumentToShare(doc);
        setIsShareOpen(true);
      },
      handleExtractTitleForDocument
  ), [handleAnalyzeDocument, handleExtractTitleForDocument]);
  
  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <Link href="/rag" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Colecciones
          </Link>
          <h1 className="text-3xl font-bold break-all">Repositorios de GitHub</h1>
        </div>
        <div className="flex items-center gap-2">
            <Button onClick={() => setIsGitHubRepoOpen(true)}>
                <Upload className="mr-2 h-4 w-4" />
                Añadir Repositorio
            </Button>
        </div>
      </div>
      
      {(docPollingId || collectionPollingId || updatePollingId) && (
          <div className="bg-muted text-muted-foreground p-3 rounded-md mb-4 flex items-center gap-2 text-sm animate-pulse">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>
                {updatePollingId
                  ? `Actualizando repositorio "${updatingRepoName}" en segundo plano...`
                  : "Un análisis está en progreso. La interfaz sigue siendo funcional..."
                }
              </span>
          </div>
      )}

      <div className="flex-grow">
        {isLoading ? (
          <div className="flex justify-center items-center h-full">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : repositories.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {repositories.map(repo => (
              <Card key={repo.url} className="flex flex-col h-full min-h-[150px] hover:border-primary/50 transition-colors relative group">
                <Link href={`/rag/repositories/${repo.name}`} className="absolute inset-0 z-10" aria-label={`Ver repositorio ${repo.name}`}></Link>
                <div className="flex justify-between items-start p-4 pb-0 z-20">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-primary flex-shrink-0 mt-1"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/></svg>
                    <div className="flex-1 min-w-0">
                      <CardTitle className="break-words">{repo.name}</CardTitle>
                      <CardContent className="p-0 pt-2">
                        <p className="text-xs text-muted-foreground/80 italic truncate">{repo.url}</p>
                        <p className="text-sm text-muted-foreground mt-1">{repo.files.length} documento(s)</p>
                      </CardContent>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className={`transition-opacity z-30 ${
                      updatePollingId && updatingRepoName === repo.name
                        ? "opacity-100"
                        : "opacity-0 group-hover:opacity-100"
                    }`}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleUpdateRepository(repo.name, repo.url);
                    }}
                    title={
                      updatePollingId && updatingRepoName === repo.name
                        ? "Actualizando..."
                        : "Actualizar repositorio"
                    }
                    disabled={!!updatePollingId && updatingRepoName === repo.name}
                  >
                    <RefreshCw className={`h-4 w-4 ${
                      updatePollingId && updatingRepoName === repo.name ? "animate-spin" : ""
                    }`} />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-center text-muted-foreground py-8">No hay repositorios disponibles.</p>
        )}
      </div>

      <div className="mt-8 pt-6 border-t">
        <h2 className="text-2xl font-bold flex items-center gap-2 mb-4">
          <History className="h-6 w-6" />
          Historial de Análisis
        </h2>
        {savedAnalyses.length > 0 ? (
          <div className="w-full max-h-[300px] overflow-y-auto">
            <Accordion type="single" collapsible className="w-full">
              {savedAnalyses.map((analysis: any) => (
                <AccordionItem value={`item-${analysis.id}`} key={analysis.id}>
                  <AccordionTrigger>
                    <div className="flex items-center gap-2 text-left flex-1 min-w-0">
                      {analysis.file_name.startsWith('Colección:') ? <FolderKanban className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                      <span className="font-medium truncate">{analysis.file_name}</span>
                      <span className="ml-auto text-xs text-muted-foreground pr-4">{new Date(analysis.created_at).toLocaleDateString()}</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <Button variant="link" className="p-0 h-auto" onClick={() => {
                      if (analysis.file_name.startsWith('Colección:')) {
                        setCollectionAnalysisResult(analysis.result_payload);
                        setIsCollectionAnalysisOpen(true);
                      } else {
                        setDocAnalysisResult(analysis.result_payload);
                        setDocumentToAnalyze({ file_name: analysis.file_name, topic: 'Repositories', title: '', author: '' });
                        setIsDocAnalysisOpen(true);
                      }
                    }}>
                      Ver Resultados Detallados
                    </Button>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        ) : (
          !isLoading && <p className="text-sm text-muted-foreground text-center py-4">No hay análisis guardados para esta vista.</p>
        )}
      </div>

      {/* Diálogos */}
      <UploadDocumentDialog isOpen={isUploadOpen} onOpenChange={setIsUploadOpen} onUploadSuccess={fetchPageData} defaultTopic="Repositories" />
      <GitHubRepoDialog isOpen={isGitHubRepoOpen} onOpenChange={setIsGitHubRepoOpen} onSuccess={fetchPageData} />
      <UpdateRepositoryDialog
        isOpen={isUpdateRepoOpen}
        onOpenChange={setIsUpdateRepoOpen}
        onSuccess={fetchPageData}
        repositoryUrl={repoToUpdate?.url || ""}
        repositoryName={repoToUpdate?.name || ""}
      />
      <PreviewDocumentDialog isOpen={!!documentToPreview} onOpenChange={(open) => !open && setDocumentToPreview(null)} document={documentToPreview} />
      <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={fetchPageData} document={documentToEdit} />
      <DeleteConfirmationDialog isOpen={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)} onDeleteSuccess={fetchPageData} document={documentToDelete} />
      <AnalysisResultDialog isOpen={isDocAnalysisOpen} onOpenChange={setIsDocAnalysisOpen} analysis={docAnalysisResult} document={documentToAnalyze ?? { file_name: '', topic: 'Repositories', title: '', author: '' }} />
      <CollectionAnalysisDialog isOpen={isCollectionAnalysisOpen} onOpenChange={setIsCollectionAnalysisOpen} analysis={collectionAnalysisResult} topic="Repositories" />
      <ShareDocumentDialog isOpen={isShareOpen} onOpenChange={setIsShareOpen} onShareSuccess={fetchPageData} document={documentToShare} />
    </div>
  );
}
