'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ArrowLeft, Loader2, FileText, Folder, Eye, Edit, ScanSearch, Share2, Trash2, History, FolderKanban, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import apiClient from '@/lib/api';
import { PreviewDocumentDialog } from '../../preview-document-dialog';
import { EditDocumentDialog } from '../../edit-document-dialog';
import { DeleteConfirmationDialog } from '../../delete-confirmation-dialog';
import { AnalysisResultDialog } from '../../analysis-result-dialog';
import { CodeAnalysisResultDialog } from '../../code-analysis-result-dialog';
import { ShareDocumentDialog } from '../../share-document-dialog';
import { UpdateRepositoryDialog } from '../../update-repository-dialog';
import type { Document } from '../../columns';

// Definir un tipo extendido para documentos de GitHub que incluye repo_url
interface GitHubDocument extends Document {
  repo_url?: string;
}

export default function RepositoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const repoName = params.repoName as string;
  const [documents, setDocuments] = useState<GitHubDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [repoUrl, setRepoUrl] = useState<string>('');
  
  // Estados para diálogos
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [documentToShare, setDocumentToShare] = useState<Document | null>(null);
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [isUpdateRepoOpen, setIsUpdateRepoOpen] = useState(false);
  
  // Estados para análisis de documento individual
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null);
  const [docAnalysisResult, setDocAnalysisResult] = useState<any>(null);
  const [isDocAnalysisOpen, setIsDocAnalysisOpen] = useState(false);
  const [docPollingId, setDocPollingId] = useState<string | null>(null);

  // Estados para análisis de colección completa
  const [collectionAnalysisResult, setCollectionAnalysisResult] = useState<any>(null);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);

  // Estados para vectorización de repositorio
  const [vectorizationPollingId, setVectorizationPollingId] = useState<string | null>(null);
  const [vectorizationResult, setVectorizationResult] = useState<any>(null);
  const [isVectorizationOpen, setIsVectorizationOpen] = useState(false);

  // Estado para el historial de análisis
  const [savedAnalyses, setSavedAnalyses] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
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
    };

    fetchData();
  }, [repoName]);

  const handleAnalyzeDocument = async (doc: Document) => {
    if (docPollingId) { toast.info('Ya hay un análisis en progreso'); return; }
    setDocumentToAnalyze(doc);
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: doc.file_name });
      setDocPollingId(response.data.task_id);
      toast.info(`Análisis para "${doc.file_name}" iniciado`);
    } catch (error) { toast.error('No se pudo iniciar el análisis del documento'); }
  };

  const handleAnalyzeRepository = async () => {
    if (docPollingId || collectionPollingId) { toast.info('Ya hay un análisis en progreso'); return; }
    try {
      const response = await apiClient.post('/api/start-code-analysis', { repo_name: repoName });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis del repositorio "${repoName}" iniciado`);
      // Deshabilitar el botón de análisis hasta que termine el proceso actual
      // Esto se manejará mediante el estado `collectionPollingId`
    } catch (error) { toast.error('No se pudo iniciar el análisis del repositorio'); }
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
          clearInterval(poller); setDocPollingId(null); setDocAnalysisResult(result);
          setIsDocAnalysisOpen(true); toast.success('Análisis de documento completado');
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
          clearInterval(poller); setCollectionPollingId(null); setCollectionAnalysisResult(result);
          setIsCollectionAnalysisOpen(true); toast.success('Análisis de repositorio completado');
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
          clearInterval(poller); setVectorizationPollingId(null); setVectorizationResult(result);
          setIsVectorizationOpen(true); toast.success('Vectorización de repositorio completada');
        } else if (status === 'failed') {
          clearInterval(poller); setVectorizationPollingId(null); toast.error('La vectorización del repositorio falló: ' + error);
        }
      } catch (err) { clearInterval(poller); setVectorizationPollingId(null); toast.error('Error al consultar la vectorización'); }
    }, 5000);
    return () => clearInterval(poller);
  }, [vectorizationPollingId]);

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
          <AccordionTrigger style={{ paddingLeft: `${indent + 16}px` }}>
            <div className="flex items-center gap-2 flex-1 justify-between">
              <div className="flex items-center gap-2">
                <Folder className="h-5 w-5" />
                <span>{node.name}</span>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); /* Lógica para analizar carpeta */ toast.info(`Analizando carpeta ${node.name}`); }} title="Analizar Carpeta">
                  <ScanSearch className="h-4 w-4" />
                </Button>
                <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); /* Lógica para compartir carpeta */ toast.info(`Compartiendo carpeta ${node.name}`); }} title="Compartir Carpeta">
                  <Share2 className="h-4 w-4" />
                </Button>
                <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); /* Lógica para eliminar carpeta */ toast.info(`Eliminando carpeta ${node.name}`); }} title="Eliminar Carpeta">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </AccordionTrigger>
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
          </AccordionContent>
        </AccordionItem>
      );
    }
  };

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <Link href="/rag/repositories" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Repositorios
          </Link>
          <h1 className="text-3xl font-bold break-all">{repoName}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="border-orange-400 text-orange-400 hover:bg-orange-50" onClick={() => setIsUpdateRepoOpen(true)}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Actualizar Repositorio
          </Button>
          <Button variant="outline" className="border-blue-400 text-blue-400 hover:bg-blue-50" disabled={!!docPollingId || !!collectionPollingId} onClick={handleAnalyzeRepository}>
            {collectionPollingId ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ScanSearch className="mr-2 h-4 w-4" />
            )}
            {collectionPollingId ? 'Analizando...' : 'Analizar Repositorio'}
          </Button>
          <Button variant="outline" className="border-green-400 text-green-400 hover:bg-green-50" disabled={!!docPollingId || !!collectionPollingId || !!vectorizationPollingId} onClick={handleVectorizeRepository}>
            <FileText className="mr-2 h-4 w-4" />
            Vectorizar Repositorio
          </Button>
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
              !isLoading && <p className="text-sm text-muted-foreground text-center py-4">No hay análisis guardados para este repositorio.</p>
            )}
          </div>
        </>
      )}

      {/* Diálogos */}
      <PreviewDocumentDialog isOpen={!!documentToPreview} onOpenChange={(open) => !open && setDocumentToPreview(null)} document={documentToPreview} />
      <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={() => {}} document={documentToEdit} />
      <DeleteConfirmationDialog isOpen={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)} onDeleteSuccess={() => {}} document={documentToDelete} />
      <CodeAnalysisResultDialog isOpen={isDocAnalysisOpen} onOpenChange={setIsDocAnalysisOpen} analysis={docAnalysisResult} repoName={repoName} />
      <CodeAnalysisResultDialog isOpen={isCollectionAnalysisOpen} onOpenChange={setIsCollectionAnalysisOpen} analysis={collectionAnalysisResult} repoName={repoName} />
      <AnalysisResultDialog isOpen={isVectorizationOpen} onOpenChange={setIsVectorizationOpen} analysis={vectorizationResult} document={{ file_name: repoName, topic: 'Repositories', title: 'Vectorización de ' + repoName, author: '' }} />
      <ShareDocumentDialog isOpen={isShareOpen} onOpenChange={setIsShareOpen} onShareSuccess={() => {}} document={documentToShare} />
      <UpdateRepositoryDialog
        isOpen={isUpdateRepoOpen}
        onOpenChange={setIsUpdateRepoOpen}
        onSuccess={() => window.location.reload()}
        repositoryUrl={repoUrl}
        repositoryName={repoName}
      />
    </div>
  );
}
