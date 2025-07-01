import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Copy, Maximize2, Minimize2 } from 'lucide-react';

interface Artifact {
  id: number;
  content: string;
  type: 'html' | 'css' | 'js' | 'svg' | 'webpage';
  version: number;
}

interface ArtifactPanelProps {
  artifacts: Artifact[];
  onCopyContent: (content: string) => void;
  isVisible: boolean;
  onToggleVisibility: () => void;
}

export const ArtifactPanel: React.FC<ArtifactPanelProps> = ({ artifacts, onCopyContent, isVisible, onToggleVisibility }) => {
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (artifacts.length > 0) {
      setSelectedArtifact(artifacts[artifacts.length - 1]);
    } else {
      setSelectedArtifact(null);
    }
  }, [artifacts]);

  const handleVersionChange = (direction: 'prev' | 'next') => {
    if (!selectedArtifact) return;
    const currentIndex = artifacts.findIndex(a => a.id === selectedArtifact.id && a.version === selectedArtifact.version);
    if (direction === 'prev' && currentIndex > 0) {
      setSelectedArtifact(artifacts[currentIndex - 1]);
    } else if (direction === 'next' && currentIndex < artifacts.length - 1) {
      setSelectedArtifact(artifacts[currentIndex + 1]);
    }
  };

  const renderArtifactContent = (artifact: Artifact) => {
    try {
      switch (artifact.type) {
        case 'html':
        case 'webpage':
          return (
            <iframe
              srcDoc={artifact.content}
              title={`Artifact ${artifact.id} v${artifact.version}`}
              className="w-full h-full border-none"
              sandbox="allow-same-origin allow-scripts"
            />
          );
        case 'svg':
          return (
            <div
              dangerouslySetInnerHTML={{ __html: artifact.content }}
              className="w-full h-full overflow-auto"
            />
          );
        default:
          return (
            <pre className="p-4 bg-gray-100 rounded-md overflow-auto text-sm">
              <code>{artifact.content}</code>
            </pre>
          );
      }
    } catch (error: unknown) {
      return (
        <div className="p-4 text-red-500">
          Error al renderizar el artefacto: {(error as Error).message || 'Error desconocido'}
        </div>
      );
    }
  };

  if (artifacts.length === 0) {
    return (
      <div className="h-full w-full flex items-center justify-center text-gray-500">
        No hay artefactos para mostrar
      </div>
    );
  }

  // No renderizamos nada si no está visible, ya que el contenedor padre controla la visibilidad
  if (!isVisible) {
    return null;
  }

  return (
    <div className={`h-full flex flex-col bg-white border-l border-gray-200 ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>
      <div className="p-4 border-b border-gray-200 flex justify-between items-center">
        <h2 className="text-lg font-semibold">Artefactos</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onToggleVisibility}>
            Ocultar
          </Button>
          {selectedArtifact && (
            <>
              <Button variant="outline" size="sm" onClick={() => onCopyContent(selectedArtifact.content)}>
                <Copy className="h-3 w-3 mr-1" /> Copiar
              </Button>
              <Button variant="outline" size="sm" onClick={() => setIsFullscreen(!isFullscreen)}>
                {isFullscreen ? <Minimize2 className="h-3 w-3 mr-1" /> : <Maximize2 className="h-3 w-3 mr-1" />}
                {isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
              </Button>
            </>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        {selectedArtifact ? renderArtifactContent(selectedArtifact) : (
          <div className="h-full flex items-center justify-center text-gray-500">
            Selecciona un artefacto para previsualizar
          </div>
        )}
      </div>
      {selectedArtifact && artifacts.length > 1 && (
        <div className="p-2 border-t border-gray-200 flex justify-between items-center bg-gray-50">
          <Button variant="outline" size="sm" onClick={() => handleVersionChange('prev')} disabled={artifacts.findIndex(a => a.id === selectedArtifact.id && a.version === selectedArtifact.version) === 0}>
            Versión anterior
          </Button>
          <span className="text-sm text-gray-500">Versión {selectedArtifact.version} de {artifacts.filter(a => a.id === selectedArtifact.id).length}</span>
          <Button variant="outline" size="sm" onClick={() => handleVersionChange('next')} disabled={artifacts.findIndex(a => a.id === selectedArtifact.id && a.version === selectedArtifact.version) === artifacts.length - 1}>
            Versión siguiente
          </Button>
        </div>
      )}
    </div>
  );
};
