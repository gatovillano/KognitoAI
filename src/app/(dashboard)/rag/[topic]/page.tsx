// En: src/app/(dashboard)/rag/[topic]/page.tsx

'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Upload } from 'lucide-react';
import { toast } from 'sonner';

// Corregimos las rutas de importación para que suban un nivel
import { DataTable } from '../data-table';
import { getColumns, type Document } from '../columns';
import apiClient from '@/lib/api';
import { UploadDocumentDialog } from '../upload-document-dialog';
import { PreviewDocumentDialog } from '../preview-document-dialog';
import { EditDocumentDialog } from '../edit-document-dialog';
import { DeleteConfirmationDialog } from '../delete-confirmation-dialog';
import { AnalysisResultDialog } from '../analysis-result-dialog';

export default function CollectionDetailPage() {
  const params = useParams();
  const topic = decodeURIComponent(params.topic as string);

  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  
  // Estados para el análisis
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null); // Guardamos el doc entero
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isAnalysisDialogOpen, setIsAnalysisDialogOpen] = useState(false);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/list-documents');
      const filteredDocs = response.data.filter((doc: Document) => doc.topic === topic);
      setDocuments(filteredDocs);
    } catch (error) {
      toast.error('Error al cargar los documentos de la colección.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [topic]);

  const handleAnalyzeDocument = async (doc: Document) => {
    setDocumentToAnalyze(doc); // Guardamos el documento que se está analizando
    const toastId = toast.loading(`Analizando "${doc.file_name}"...`);
    try {
        const response = await apiClient.post('/api/analyze-document', { file_name: doc.file_name });
        setAnalysisResult(response.data);
        setIsAnalysisDialogOpen(true);
        toast.success("¡Análisis completado!", { id: toastId });
    } catch (error) {
        toast.error("Fallo en el análisis del documento.", { id: toastId });
        setDocumentToAnalyze(null); // Limpiamos en caso de error
    }
  };

  const columns = useMemo(() => getColumns(
      (doc) => setDocumentToPreview(doc),
      (doc) => setDocumentToEdit(doc),
      (doc) => setDocumentToDelete(doc),
      handleAnalyzeDocument
  ), [topic]); // Añadimos topic a las dependencias por si acaso
  
  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <Link href="/rag" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Colecciones
          </Link>
          <h1 className="text-3xl font-bold break-all">Colección: {topic}</h1>
        </div>
        <Button onClick={() => setIsUploadOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Subir a esta Colección
        </Button>
      </div>

      <div className="flex-grow">
        {isLoading ? (
          <p>Cargando documentos...</p>
        ) : (
          <DataTable columns={columns} data={documents} />
        )}
      </div>

      {/* Diálogos */}
      <UploadDocumentDialog 
        isOpen={isUploadOpen} 
        onOpenChange={setIsUploadOpen}
        onUploadSuccess={fetchDocuments}
        defaultTopic={topic}
      />
      <PreviewDocumentDialog
        isOpen={!!documentToPreview}
        onOpenChange={(open) => !open && setDocumentToPreview(null)}
        document={documentToPreview}
      />
      <EditDocumentDialog 
        isOpen={!!documentToEdit}
        onOpenChange={(open) => !open && setDocumentToEdit(null)}
        onUpdateSuccess={fetchDocuments}
        document={documentToEdit}
      />
      <DeleteConfirmationDialog
        isOpen={!!documentToDelete}
        onOpenChange={(open) => !open && setDocumentToDelete(null)}
        onDeleteSuccess={fetchDocuments}
        document={documentToDelete}
      />
      {/* --- CORRECCIÓN: Añadimos la prop 'document' que faltaba --- */}
      <AnalysisResultDialog
        isOpen={isAnalysisDialogOpen}
        onOpenChange={setIsAnalysisDialogOpen}
        analysis={analysisResult}
        document={documentToAnalyze} 
      />
    </div>
  );
}