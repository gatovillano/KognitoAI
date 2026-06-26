'use client';

import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ArrowLeft, Loader2, FileText, Folder, Eye, Edit, ScanSearch, Share2, Trash2, History, FolderKanban, RefreshCw, MoreHorizontal, ChevronDown } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';

import apiClient from '@/lib/api';
import { PreviewDocumentDialog } from '../../preview-document-dialog';
import { EditDocumentDialog } from '../../edit-document-dialog';
import { DeleteConfirmationDialog } from '../../delete-confirmation-dialog';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import { ShareDocumentDialog } from '../../share-document-dialog';
import { UpdateRepositoryDialog } from '../../update-repository-dialog';
import { StartCodeAnalysisDialog } from '@/app/(dashboard)/analysis/StartCodeAnalysisDialog';
import type { Document } from '../../columns';
import { useTaskContext } from '@/contexts/TaskContext';

// Definir un tipo extendido para documentos de GitHub que incluye repo_url
interface GitHubDocument extends Document {
  repo_url?: string;
}

export default function RepositoryDetailPage() {
  const rawParams = useParams();
  const params = { ...rawParams }; // Create a shallow copy
  const router = useRouter();
  const repoName = (params?.repoName as string) || '';
  const [documents, setDocuments] = useState<GitHubDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { addAnalysisTask } = useTaskContext();
  const [repoUrl, setRepoUrl] = useState<string>('');

  // Estados para diálogos
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [documentToShare, setDocumentToShare] = useState<Document | null>(null);
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [isUpdateRepoOpen, setIsUpdateRepoOpen] = useState(false);
  const [isStartAnalysisDialogOpen, setIsStartAnalysisDialogOpen] = useState(false);
  const [analysisTarget, setAnalysisTarget] = useState<{ type: 'repo' | 'doc'; data: any } | null>(null);

  // Estados para análisis
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<any>(null);
  const [isAnalysisDetailOpen, setIsAnalysisDetailOpen] = useState(false);
  const [docPollingId, setDocPollingId] = useState<string | null>(null);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);
  const [vectorizationPollingId, setVectorizationPollingId] = useState<string | null>(null);

  // Componente auxiliar para el menú de acciones del documento
  const DocumentActionsDropdown = ({ doc }: { doc: Document }) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
          <span className="sr-only">Abrir menú</span>
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setDocumentToPreview(doc)}>
          <Eye className="mr-2 h-4 w-4" />
          <span>Ver</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setDocumentToEdit(doc)}>
          <Edit className="mr-2 h-4 w-4" />
          <span>Editar</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleAnalyzeDocument(doc)}>
          <ScanSearch className="mr-2 h-4 w-4" />
          <span>Analizar</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => { setDocumentToShare(doc); setIsShareOpen(true); }}>
          <Share2 className="mr-2 h-4 w-4" />
          <span>Compartir</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => setDocumentToDelete(doc)} className="text-red-600">
          <Trash2 className="mr-2 h-4 w-4" />
          <span>Eliminar</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  // Estado para el historial de análisis
  const [savedAnalyses, setSavedAnalyses] = useState<any[]>([]);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [docsRes, analysesRes] = await Promise.all([
        apiClient.post('/api/github/list-github-documents', {}),
        apiClient.post('/api/get-repo-analyses', { repo_name: repoName })
      ]);
      // Filtrar documentos por repo_url que termine con el repoName
      const filteredDocs = docsRes.data.filter((doc: GitHubDocument) => doc.repo_url && doc.repo_url.endsWith(`/${repoName}`));

      // Obtener la URL del repositorio del primer documento
      if (filteredDocs.length > 0 && filteredDocs[0].repo_url) {
        setRepoUrl(filteredDocs[0].repo_url);
      }
      // Usar los análisis directamente del endpoint específico para el repositorio
      const repoAnalyses = analysesRes.data
        .map((analysis: any) => {
          let fileName = 'Análisis sin título';
          if (analysis.result_payload && typeof analysis.result_payload === 'object') {
            fileName = analysis.result_payload.file_name || analysis.result_payload.title || fileName;
          }
          return {
            ...analysis,
            file_name: fileName
          };
        });
      console.log('Total de análisis cargados desde la API para este repositorio:', repoAnalyses.length);
      toast.info(`Análisis cargados desde API para ${repoName}: ${repoAnalyses.length}`);
      setDocuments(filteredDocs);
      setSavedAnalyses(repoAnalyses);
    } catch (error) {
      toast.error('Error al cargar los datos del repositorio');
    } finally {
      setIsLoading(false);
    }
  }, [repoName]);

  const refreshDocuments = () => {
    fetchData();
  };

  const handleDeleteFolder = async (folderPath: string) => {
    try {
      // Asegurarse de que folderPath no termine con '/' si es la raíz del repo
      const cleanedFolderPath = folderPath === '/' ? '' : folderPath;

      await apiClient.post('/api/github/delete-folder', {
        repo_name: repoName,
        folder_path: cleanedFolderPath,
        repo_url: repoUrl,
        // workspace_id: ... si es necesario pasarlo
      });
      toast.success(`Carpeta "${folderPath}" eliminada con éxito.`);
      refreshDocuments(); // Recargar documentos después de eliminar la carpeta
    } catch (error) {
      toast.error(`Error al eliminar la carpeta "${folderPath}".`);
      console.error(error);
    }
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAnalyzeDocument = (doc: Document) => {
    if (docPollingId) { toast.info('Ya hay un análisis en progreso'); return; }
    setAnalysisTarget({ type: 'doc', data: doc });
    setIsStartAnalysisDialogOpen(true);
  };

  const handleAnalyzeRepository = () => {
    if (docPollingId || collectionPollingId) { toast.info('Ya hay un análisis en progreso'); return; }
    setAnalysisTarget({ type: 'repo', data: repoName });
    setIsStartAnalysisDialogOpen(true);
  };

  const onConfirmAnalysis = async (analysisType: string) => {
    if (!analysisTarget) return;

    if (analysisTarget.type === 'doc') {
      const doc = analysisTarget.data;
      setDocumentToAnalyze(doc);
      try {
        const response = await apiClient.post('/api/start-document-analysis', { 
          file_name: doc.file_name,
          analysis_type: analysisType 
        });
        const taskId = response.data.task_id;
        setDocPollingId(taskId);
        addAnalysisTask({
          task_id: taskId,
          phase: 'initializing',
          message: `Iniciando análisis (${analysisType}) de "${doc.file_name}"...`,
          progress_percent: 0,
          is_complete: false,
          has_error: false,
          file_name: doc.file_name,
          type: 'document'
        });
        toast.info(`Análisis (${analysisType}) para "${doc.file_name}" iniciado`);
      } catch (error) { toast.error('No se pudo iniciar el análisis del documento'); }
    } else {
      try {
        const response = await apiClient.post('/api/start-code-analysis', { 
          repo_name: repoName,
          analysis_type: analysisType
        });
        const taskId = response.data.task_id;
        setCollectionPollingId(taskId);
        addAnalysisTask({
          task_id: taskId,
          phase: 'initializing',
          message: `Iniciando análisis (${analysisType}) del repositorio "${repoName}"...`,
          progress_percent: 0,
          is_complete: false,
          has_error: false,
          topic: repoName,
          type: 'collection'
        });
        toast.info(`Análisis (${analysisType}) del repositorio "${repoName}" iniciado`);
      } catch (error) { toast.error('No se pudo iniciar el análisis del repositorio'); }
    }
    setAnalysisTarget(null);
  };

  const handleVectorizeRepository = async () => {
    if (docPollingId || collectionPollingId || vectorizationPollingId) { toast.info('Ya hay un proceso en progreso'); return; }
    try {
      const response = await apiClient.post('/api/github/start-vectorization', { repo_name: repoName });
      setVectorizationPollingId(response.data.task_id);
      toast.info(`Vectorización del repositorio "${repoName}" iniciada`);
    } catch (error) { toast.error('No se pudo iniciar la vectorización del repositorio'); }
  };

  // Polling para análisis de documento
  useEffect(() => {
    if (!docPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${docPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setDocPollingId(null);
          // Construir objeto Analysis completo
          const analysisObject = {
            id: docPollingId,
            type: 'document' as const,
            title: documentToAnalyze?.file_name || 'Análisis de Documento',
            summary: result?.executive_summary || 'Análisis completado',
            result: result,
            full_data: result
          };
          setSelectedAnalysis(analysisObject);
          setIsAnalysisDetailOpen(true); toast.success('Análisis de documento completado');
        } else if (status === 'failed') {
          clearInterval(poller); setDocPollingId(null); toast.error('El análisis del documento falló: ' + error);
        }
      } catch (err) { clearInterval(poller); setDocPollingId(null); toast.error('Error al consultar el análisis'); }
    }, 5000);
    return () => clearInterval(poller);
  }, [docPollingId]);

  // Polling para análisis de colección
  useEffect(() => {
    if (!collectionPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setCollectionPollingId(null);
          // Construir objeto Analysis completo para análisis de código
          const analysisObject = {
            id: collectionPollingId,
            type: 'code' as const,
            title: `Análisis de Repositorio: ${repoName}`,
            summary: result?.executive_summary || 'Análisis de código completado',
            result: result,
            full_data: result
          };
          setSelectedAnalysis(analysisObject);
          setIsAnalysisDetailOpen(true); toast.success('Análisis de repositorio completado');
          // Actualizar el historial de análisis
          window.dispatchEvent(new Event('updateAnalysisHistory'));
        } else if (status === 'failed') {
          clearInterval(poller); setCollectionPollingId(null); toast.error('El análisis del repositorio falló: ' + error);
        }
      } catch (err) { clearInterval(poller); setCollectionPollingId(null); toast.error('Error al consultar el análisis'); }
    }, 5000);
    return () => clearInterval(poller);
  }, [collectionPollingId]);

  // Polling para vectorización de repositorio
  useEffect(() => {
    if (!vectorizationPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/github/get-vectorization-result/${vectorizationPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setVectorizationPollingId(null);
          // Construir objeto Analysis completo para vectorización
          const analysisObject = {
            id: vectorizationPollingId,
            type: 'code' as const,
            title: `Vectorización: ${repoName}`,
            summary: result?.message || 'Vectorización completada',
            result: result,
            full_data: result
          };
          setSelectedAnalysis(analysisObject);
          setIsAnalysisDetailOpen(true); toast.success('Vectorización de repositorio completada');
        } else if (status === 'failed') {
          clearInterval(poller); setVectorizationPollingId(null); toast.error('La vectorización del repositorio falló: ' + error);
        }
      } catch (err) { clearInterval(poller); setVectorizationPollingId(null); toast.error('Error al consultar la vectorización'); }
    }, 5000);
    return () => clearInterval(poller);
  }, [vectorizationPollingId]);

  const isAnyAnalysisInProgress = useMemo(() => {
    return !!docPollingId || !!collectionPollingId || !!vectorizationPollingId;
  }, [docPollingId, collectionPollingId, vectorizationPollingId]);

  // Organizar documentos en una estructura de árbol de carpetas
  interface FolderNode {
    name: string;
    path: string;
    children: { [key: string]: FolderNode };
    files: Document[];
  }

  const folderTree = useMemo(() => {
    const root: FolderNode = { name: 'Raíz', path: '/', children: {}, files: [] };
    documents.forEach(doc => {
      // Extraer la parte del file_name después del nombre del repositorio
      const repoPart = doc.repo_url ? doc.repo_url.split('/').pop() || repoName : repoName;
      const pathParts = doc.file_name.replace(`${repoPart}/`, '').split('/');
      if (pathParts.length === 1) {
        // Archivo en la raíz
        root.files.push(doc);
      } else {
        // Construir la estructura de carpetas anidadas
        let currentNode = root;
        const folderPathParts = pathParts.slice(0, -1); // Excluir el nombre del archivo
        let currentPath = '';
        folderPathParts.forEach((part, index) => {
          currentPath = currentPath ? `${currentPath}/${part}` : part;
          if (!currentNode.children[part]) {
            currentNode.children[part] = {
              name: part,
              path: currentPath,
              children: {},
              files: []
            };
          }
          currentNode = currentNode.children[part];
          if (index === folderPathParts.length - 1) {
            // Última carpeta, agregar el archivo aquí
            currentNode.files.push(doc);
          }
        });
      }
    });
    return root;
  }, [documents, repoName]);

  // Componente recursivo para renderizar el árbol de carpetas
  const renderFolder = (node: FolderNode, level = 0): React.ReactNode => {
    const indent = level * 16; // 16px por nivel de anidamiento
    if (node.path === '/') {
      // Para la raíz, no renderizamos un AccordionItem, solo sus contenidos
      return (
        <>
          {Object.values(node.children).map(child => (
            <React.Fragment key={child.path}>{renderFolder(child, level)}</React.Fragment>
          ))}
          {node.files.length > 0 && (
            <ul className="list-disc pl-5" style={{ paddingLeft: `${indent + 20}px` }}>
              {node.files.map(file => {
                const repoPart = (file as GitHubDocument).repo_url?.split('/').pop() || repoName;
                const folderPath = node.path === '/' ? '' : `${node.path}/`;
                return (
                  <li key={file.file_name} className="text-sm truncate flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span>{file.file_name.replace(`${repoPart}/${folderPath}`, '').split('/').pop()}</span>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => setDocumentToPreview(file)} title="Ver">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setDocumentToEdit(file)} title="Editar">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleAnalyzeDocument(file)} title="Analizar">
                        <ScanSearch className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => { setDocumentToShare(file); setIsShareOpen(true); }} title="Compartir">
                        <Share2 className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setDocumentToDelete(file)} title="Eliminar">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      );
    } else {
      return (
        <AccordionItem key={node.path} value={node.path}>
          <div className="flex items-center w-full">
            <AccordionTrigger
              style={{ paddingLeft: `${indent + 16}px` }}
              className="flex-grow justify-start"
            >
              <div className="flex items-center gap-2">
                <Folder className="h-5 w-5" />
                <span>{node.name}</span>
              </div>
            </AccordionTrigger>
            <div className="flex gap-1 pr-4">
              <Button size="sm" variant="ghost" onClick={() => { /* Lógica para analizar carpeta */ toast.info(`Analizando carpeta ${node.name}`); }} title="Analizar Carpeta">
                <ScanSearch className="h-4 w-4" />
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { /* Lógica para compartir carpeta */ toast.info(`Compartiendo carpeta ${node.name}`); }} title="Compartir Carpeta">
                <Share2 className="h-4 w-4" />
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { handleDeleteFolder(node.path); }} title="Eliminar Carpeta">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <AccordionContent>
            {Object.values(node.children).length > 0 &&
              Object.values(node.children).map(child => (
                <React.Fragment key={child.path}>{renderFolder(child, level + 1)}</React.Fragment>
              ))
            }
            {node.files.length > 0 && (
              <ul className="list-disc pl-5" style={{ paddingLeft: `${indent + 20}px` }}>
                {node.files.map(file => {
                  const repoPart = (file as GitHubDocument).repo_url?.split('/').pop() || repoName;
                  const folderPath = node.path === '/' ? '' : `${node.path}/`;
                  return (
                    <li key={file.file_name} className="text-sm truncate flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        <span>{file.file_name.replace(`${repoPart}/${folderPath}`, '').split('/').pop()}</span>
                      </div>
                      <div className="flex gap-1">
                        <DocumentActionsDropdown doc={file} />
                        <DocumentActionsDropdown doc={file} />
                        <DocumentActionsDropdown doc={file} />
                        <DocumentActionsDropdown doc={file} />
                        <DocumentActionsDropdown doc={file} />
                        <DocumentActionsDropdown doc={file} />
                        <DocumentActionsDropdown doc={file} />
                        <DocumentActionsDropdown doc={file} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </AccordionContent>
        </AccordionItem>
      );
    }
  };

  return (
    <React.Fragment>
      {isAnyAnalysisInProgress && (
        <div className="sticky top-0 left-0 right-0 p-2 bg-primary/10 border-b border-primary/20 text-center z-50">
          <div className="flex items-center justify-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-sm font-medium text-primary">Análisis en curso... Por favor, espere.</span>
          </div>
        </div>
      )}
      <div className="h-full flex flex-col p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <Link href="/rag/repositories" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-1 sm:mb-2">
              <ArrowLeft className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
              Volver a Repositorios
            </Link>
            <h1 className="text-2xl sm:text-3xl font-bold break-all">{repoName}</h1>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
            {/* MENÚ DE ACCIONES PARA EL REPOSITORIO */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2" disabled={!!docPollingId || !!collectionPollingId || !!vectorizationPollingId}>
                  <MoreHorizontal className="h-4 w-4" />
                  <span className="hidden sm:inline">Acciones</span>
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onClick={() => setIsUpdateRepoOpen(true)}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  <span>Actualizar Repositorio</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleAnalyzeRepository} disabled={!!docPollingId || !!collectionPollingId}>
                  {collectionPollingId ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <ScanSearch className="mr-2 h-4 w-4" />
                  )}
                  <span>{collectionPollingId ? 'Analizando...' : 'Analizar Repositorio'}</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleVectorizeRepository} disabled={!!docPollingId || !!collectionPollingId || !!vectorizationPollingId}>
                  <FileText className="mr-2 h-4 w-4" />
                  <span>Vectorizar Repositorio</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-full">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : (
          <>
            <div className="flex-grow overflow-auto">
              {Object.keys(folderTree.children).length > 0 || folderTree.files.length > 0 ? (
                <Accordion type="multiple" className="w-full">
                  {renderFolder(folderTree)}
                </Accordion>
              ) : (
                <p className="text-center text-muted-foreground py-8">No hay archivos en este repositorio.</p>
              )}
            </div>

            <div className="mt-6 sm:mt-8 pt-4 sm:pt-6 border-t">
              <h2 className="text-xl sm:text-2xl font-bold flex items-center gap-2 mb-3 sm:mb-4">
                <History className="h-5 w-5 sm:h-6 sm:w-6" />
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
                          <Button variant="link" className="p-0 h-auto text-xs sm:text-sm" onClick={() => {
                            // Construir un objeto Analysis completo para el diálogo
                            const analysisObject = {
                              id: analysis.id,
                              type: 'code' as const, // Tipo de análisis de código
                              title: analysis.file_name || 'Análisis de Código',
                              summary: analysis.result_payload?.executive_summary || 'Análisis de repositorio',
                              created_at: analysis.created_at,
                              updated_at: analysis.updated_at,
                              result: analysis.result_payload, // Los datos del análisis
                              full_data: analysis.result_payload // También en full_data por compatibilidad
                            };
                            setSelectedAnalysis(analysisObject);
                            setIsAnalysisDetailOpen(true);
                          }}>
                            Ver Resultados Detallados
                          </Button>
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </div>
              ) : (
                !isLoading && <p className="text-sm text-muted-foreground text-center py-4">No hay análisis guardados para este repositorio.</p>
              )}
            </div>
          </>
        )}

        {/* Diálogos */}
        <PreviewDocumentDialog isOpen={!!documentToPreview} onOpenChange={(open) => !open && setDocumentToPreview(null)} document={documentToPreview} />
        <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={() => { }} document={documentToEdit} />
        <DeleteConfirmationDialog
          isOpen={!!documentToDelete}
          onOpenChange={(open) => !open && setDocumentToDelete(null)}
          onDeleteSuccess={refreshDocuments}
          document={documentToDelete}
        />
        <AnalysisDetailDialog isOpen={isAnalysisDetailOpen} onOpenChange={setIsAnalysisDetailOpen} analysis={selectedAnalysis} />
        <ShareDocumentDialog isOpen={isShareOpen} onOpenChange={setIsShareOpen} onShareSuccess={() => { }} document={documentToShare} />
        <UpdateRepositoryDialog
          isOpen={isUpdateRepoOpen}
          onOpenChange={setIsUpdateRepoOpen}
          onSuccess={() => window.location.reload()}
          repositoryUrl={repoUrl}
          repositoryName={repoName}
        />
        <StartCodeAnalysisDialog 
          isOpen={isStartAnalysisDialogOpen} 
          onOpenChange={setIsStartAnalysisDialogOpen} 
          onConfirm={onConfirmAnalysis}
          title={analysisTarget?.type === 'repo' ? "Analizar Repositorio" : "Analizar Archivo"}
          isRepo={analysisTarget?.type === 'repo'}
        />
      </div>
    </React.Fragment>
  );
}
