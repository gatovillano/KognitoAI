import React, { useState, useCallback } from 'react';
import Image from 'next/image';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useDropzone } from 'react-dropzone';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { XCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface UploadPhotosModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  albumId: string;
  onUploadSuccess: () => void;
}

export const UploadPhotosModal: React.FC<UploadPhotosModalProps> = ({
  isOpen,
  onOpenChange,
  albumId,
  onUploadSuccess,
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prevFiles => [...prevFiles, ...acceptedFiles]);
    setUploadError(null); // Clear previous errors
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [] },
    multiple: true,
  });

  const handleRemoveFile = (fileToRemove: File) => {
    setFiles(prevFiles => prevFiles.filter(file => file !== fileToRemove));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.info('Por favor, selecciona al menos una imagen para subir.');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);

    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      await apiClient.post(`/api/galleries/albums/${albumId}/photos`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          }
        },
      });

      toast.success('Fotos subidas correctamente.');
      setFiles([]); // Clear selected files
      onUploadSuccess(); // Trigger refresh in parent
      onOpenChange(false); // Close modal
    } catch (e: any) {
      setUploadError(e.message || 'Error al subir las fotos.');
      toast.error('Error al subir las fotos.');
      console.error('Error uploading photos:', e);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Subir Fotos al Álbum</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors duration-200 ${
              isDragActive ? 'border-blue-500 bg-blue-50 dark:bg-blue-900' : 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700'
            }`}
          >
            <input {...getInputProps()} />
            {isDragActive ? (
              <p className="text-blue-600 dark:text-blue-400">Suelta las fotos aquí...</p>
            ) : (
              <p className="text-gray-600 dark:text-gray-300">Arrastra y suelta algunas fotos aquí, o haz clic para seleccionar archivos</p>
            )}
          </div>

          {files.length > 0 && (
            <div className="mt-4">
              <h4 className="text-lg font-semibold mb-2">Archivos seleccionados ({files.length})</h4>

// ... (the rest of the imports)

// ... (the rest of the component)

              <div className="grid grid-cols-3 gap-2 max-h-40 overflow-y-auto border rounded-md p-2">
                {files.map((file, index) => (
                  <div key={index} className="relative group">
                    <Image src={URL.createObjectURL(file)} alt={file.name} width={100} height={100} className="w-full h-24 object-cover rounded-md" />
                    <Button
                      variant="destructive"
                      size="icon"
                      className="absolute top-1 right-1 h-6 w-6 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleRemoveFile(file)}
                    >
                      <XCircle className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {uploading && (
            <div className="mt-4">
              <Progress value={uploadProgress} className="w-full" />
              <p className="text-center text-sm mt-2">{uploadProgress}% completado</p>
            </div>
          )}

          {uploadError && <p className="text-red-500 text-sm mt-2 text-center">Error al subir: {uploadError}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={uploading}>
            Cancelar
          </Button>
          <Button onClick={handleUpload} disabled={uploading || files.length === 0}>
            {uploading ? 'Subiendo...' : 'Subir Fotos'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};