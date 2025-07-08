// En: src/app/(dashboard)/rag/all/page.tsx

'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ArrowLeft, Upload, History, FileText, FolderKanban } from 'lucide-react';
import { toast } from 'sonner';

// Importaciones de componentes del directorio padre 'rag'
import { DataTable } from '../data-table';
import { getColumns, type Document } from '../columns';
import apiClient from '@/lib/api';
import { UploadDocumentDialog } from '../upload-document-dialog';
import { PreviewDocumentDialog } from '../preview-document-dialog';
import { EditDocumentDialog } from '../edit-document-dialog';
import { DeleteConfirmationDialog } from '../delete-confirmation-dialog';
import { AnalysisResultDialog } from '../analysis-result-dialog';
import { CollectionAnalysisDialog } from '../collection-analysis-dialog'; // Aunque no lo iniciamos aquí, lo necesitamos por si el usuario abre un análisis guardado de colección

export default function AllDocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Estados para los diálogos
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  
  // Estados para el análisis
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isAnalysisDialogOpen, setIsAnalysisDialogOpen] = useState(false);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false); // Necesario para el diálogo
  const [docPollingId, setDocPollingId] = useState<string | null>(null);

  // Estado para el historial
  const [savedAnalyses, setSavedAnalyses] = useState([]);

  const fetchPageData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [docsRes, analysesRes] = await Promise.all([
        apiClient.post('/api/list-documents'),
        // --- CAMBIO CLAVE: Pedimos TODOS los análisis guardados ---
        apiClient.post('/api/get-saved-analyses', { all: true })
      ]);
      setDocuments(docsRes.data);
      setSavedAnalyses(analysesRes.data);
    } catch (error) {
      toast.error('Error al cargar los datos.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPageData();
  }, [fetchPageData]);

  // Polling para el análisis de documento
  useEffect(() => {
    const pollDocumentAnalysis = async () => {
      if (docPollingId) {
        try {
          const response = await apiClient.get(`/api/get-analysis-result/${docPollingId}`);
          if (response.data.status === 'completed') {
            setAnalysisResult(response.data.result);
            setIsAnalysisDialogOpen(true);
            setDocPollingId(null);
            toast.success("¡Análisis completado!");
            fetchPageData(); // Refresca la lista de análisis guardados
          } else if (response.data.status === 'failed') {
            toast.error(`Error en el análisis: ${response.data.error || 'Error desconocido'}`);
            setDocPollingId(null);
          }
        } catch (error) {
          toast.error("Error al verificar el estado del análisis.");
          console.error(error);
          setDocPollingId(null);
        }
      }
    };

    if (docPollingId) {
      const interval = setInterval(pollDocumentAnalysis, 3000);
      return () => clearInterval(interval);
    }
  }, [docPollingId, fetchPageData]);

  const handleAnalyzeDocument = useCallback(async (doc: Document) => {
    if (docPollingId) {
      toast.info('Ya hay un análisis en progreso');
      return;
    }
    setDocumentToAnalyze(doc);
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: doc.file_name });
      setDocPollingId(response.data.task_id);
      toast.info(`Análisis para "${doc.file_name}" iniciado`);
    } catch (error) {
      toast.error('No se pudo iniciar el análisis del documento');
    }
  }, [docPollingId]);
  
  const columns = useMemo(() => getColumns(
      (doc) => setDocumentToPreview(doc),
      (doc) => setDocumentToEdit(doc),
      (doc) => setDocumentToDelete(doc),
      handleAnalyzeDocument
  ), [handleAnalyzeDocument]); // useCallback envuelve el handler para que no cambie

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <Link href="/rag" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Colecciones
          </Link>
          <h1 className="text-3xl font-bold">Todos los Documentos</h1>
        </div>
        <Button onClick={() => setIsUploadOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Subir Nuevo Documento
        </Button>
      </div>

      <div className="flex-grow">
        {isLoading ? <p>Cargando documentos...</p> : <DataTable columns={columns} data={documents} />}
      </div>
      
      {/* --- NUEVA SECCIÓN DE HISTORIAL --- */}
      <div className="mt-8 pt-6 border-t">
        <h2 className="text-2xl font-bold flex items-center gap-2 mb-4">
          <History className="h-6 w-6" />
          Historial de Análisis Recientes
        </h2>
        {savedAnalyses.length > 0 ? (
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
                    setAnalysisResult(analysis.result_payload);
                    if (analysis.file_name.startsWith('Colección:')) {
                      setIsCollectionAnalysisOpen(true);
                    } else {
                      setDocumentToAnalyze({ file_name: analysis.file_name, topic: '', title: '', author: '' });
                      setIsAnalysisDialogOpen(true);
                    }
                  }}>
                    Ver Resultados Detallados
                  </Button>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        ) : (
          !isLoading && <p className="text-sm text-muted-foreground text-center py-4">No hay análisis guardados.</p>
        )}
      </div>

      {/* Diálogos */}
      <UploadDocumentDialog isOpen={isUploadOpen} onOpenChange={setIsUploadOpen} onUploadSuccess={fetchPageData} />
      <PreviewDocumentDialog isOpen={!!documentToPreview} onOpenChange={(open) => !open && setDocumentToPreview(null)} document={documentToPreview} />
      <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={fetchPageData} document={documentToEdit} />
      <DeleteConfirmationDialog isOpen={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)} onDeleteSuccess={fetchPageData} document={documentToDelete} />
      <AnalysisResultDialog isOpen={isAnalysisDialogOpen} onOpenChange={setIsAnalysisDialogOpen} analysis={analysisResult} document={documentToAnalyze} />
      <CollectionAnalysisDialog isOpen={isCollectionAnalysisOpen} onOpenChange={setIsCollectionAnalysisOpen} analysis={analysisResult} topic={documentToAnalyze?.file_name?.replace('Colección: ', '') ?? ''} />
    </div>
  );
}
