"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { RefreshCw, Github, AlertCircle, CheckCircle, XCircle } from "lucide-react";
import apiClient from "@/lib/api";

interface UpdateRepositoryDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onSuccess: () => void;
  repositoryUrl: string;
  repositoryName: string;
}

export function UpdateRepositoryDialog({
  isOpen,
  onOpenChange,
  onSuccess,
  repositoryUrl,
  repositoryName
}: UpdateRepositoryDialogProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<'pending' | 'processing' | 'completed' | 'failed' | null>(null);
  const [taskResult, setTaskResult] = useState<any>(null);
  const [taskError, setTaskError] = useState<string | null>(null);
  const { toast } = useToast();

  // Polling para verificar el estado de la tarea
  useEffect(() => {
    if (!taskId || taskStatus === 'completed' || taskStatus === 'failed') return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/analysis/get-analysis-result/${taskId}`);
        const { status, result, error } = response.data;

        setTaskStatus(status);

        if (status === 'completed') {
          setTaskResult(result);
          toast({
            title: "Repositorio actualizado",
            description: result?.message || `El repositorio ${repositoryName} se ha actualizado correctamente.`,
          });
          onSuccess();
          setTimeout(() => {
            onOpenChange(false);
            resetState();
          }, 2000);
        } else if (status === 'failed') {
          setTaskError(error);
          toast({
            title: "Error al actualizar",
            description: error || "Ocurrió un error al actualizar el repositorio.",
            variant: "destructive",
          });
        }
      } catch (error) {
        console.error('Error polling task status:', error);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [taskId, taskStatus, repositoryName, onSuccess, onOpenChange, toast]);

  const resetState = () => {
    setTaskId(null);
    setTaskStatus(null);
    setTaskResult(null);
    setTaskError(null);
    setIsLoading(false);
  };

  const handleUpdate = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post("/api/github/update-repository", {
        repo_url: repositoryUrl,
        collection_topic: "repositorio",
      });

      setTaskId(response.data.task_id);
      setTaskStatus('pending');

      toast({
        title: "Actualización iniciada",
        description: "La actualización del repositorio se está ejecutando en segundo plano.",
      });
    } catch (error: any) {
      toast({
        title: "Error al iniciar actualización",
        description: error.response?.data?.detail || "Ocurrió un error al iniciar la actualización del repositorio.",
        variant: "destructive",
      });
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (taskStatus === 'processing') {
      toast({
        title: "Actualización en progreso",
        description: "La actualización continuará en segundo plano. Recibirás una notificación cuando termine.",
      });
    }
    onOpenChange(false);
    resetState();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-primary" />
            Actualizar Repositorio
          </DialogTitle>
          <DialogDescription>
            ¿Estás seguro de que quieres actualizar este repositorio desde GitHub?
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
            <Github className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="font-medium">{repositoryName}</p>
              <p className="text-sm text-muted-foreground">{repositoryUrl}</p>
            </div>
          </div>

          {!taskId && (
            <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-blue-800">
                <p className="font-medium mb-1">Esta operación:</p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li>Sincronizará los archivos con la versión más reciente de GitHub</li>
                  <li>Añadirá nuevos archivos encontrados</li>
                  <li>Actualizará archivos modificados</li>
                  <li>Re-vectorizará el contenido actualizado</li>
                </ul>
              </div>
            </div>
          )}

          {taskId && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                {taskStatus === 'pending' && (
                  <>
                    <RefreshCw className="h-4 w-4 text-yellow-600 animate-spin" />
                    <span className="text-sm text-yellow-700">Iniciando actualización...</span>
                  </>
                )}
                {taskStatus === 'processing' && (
                  <>
                    <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />
                    <span className="text-sm text-blue-700">Actualizando repositorio...</span>
                  </>
                )}
                {taskStatus === 'completed' && (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-green-700">Actualización completada</span>
                  </>
                )}
                {taskStatus === 'failed' && (
                  <>
                    <XCircle className="h-4 w-4 text-red-600" />
                    <span className="text-sm text-red-700">Error en la actualización</span>
                  </>
                )}
              </div>

              {taskStatus === 'processing' && (
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-800">
                    La actualización se está ejecutando en segundo plano. Puedes cerrar este diálogo y continuar trabajando.
                  </p>
                </div>
              )}

              {taskStatus === 'failed' && taskError && (
                <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                  <p className="text-sm text-red-800">{taskError}</p>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isLoading && !taskId}
          >
            {taskStatus === 'processing' ? 'Cerrar' : 'Cancelar'}
          </Button>

          {!taskId && (
            <Button onClick={handleUpdate} disabled={isLoading}>
              {isLoading ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Iniciando...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Actualizar
                </>
              )}
            </Button>
          )}

          {taskStatus === 'completed' && (
            <Button onClick={() => { onOpenChange(false); resetState(); }}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Cerrar
            </Button>
          )}

          {taskStatus === 'failed' && (
            <Button onClick={handleUpdate} variant="destructive">
              <RefreshCw className="mr-2 h-4 w-4" />
              Reintentar
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
