'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Box, Typography, Paper } from '@mui/material';
import { Settings as SettingsIcon } from '@mui/icons-material';
import { Button } from '@/components/ui/button';
import KnowledgeGraphViewer from '@/components/KnowledgeGraph/KnowledgeGraphViewer';
import { useKnowledgeGraph } from '@/hooks/useKnowledgeGraph';
import { useWorkspaces } from '@/hooks/useWorkspaces';
import { type Node } from 'reactflow';
import './KnowledgeGraphPage.css';

interface CustomNodeData {
  label: string;
  type: string;
}

const KnowledgeGraphPage = () => {
  const params = useParams();
  const workspaceId = params?.id as string;
  const router = useRouter();
  const [selectedNode, setSelectedNode] = useState<Node<CustomNodeData> | null>(null);
  const [showProcessingModal, setShowProcessingModal] = useState(false);

  // Hooks
  const { workspaces, currentWorkspace, isLoading: workspacesLoading } = useWorkspaces();
  const {
    graphData,
    stats,
    isLoading,
    error,
    processingStatus,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    clearError
  } = useKnowledgeGraph(workspaceId);

  // Obtener información del workspace actual
  const workspace = workspaces.find(w => w.id === workspaceId) || currentWorkspace;

  // Manejar selección de nodo
  const handleNodeSelect = (node: Node<CustomNodeData>) => {
    setSelectedNode(node);
  };

  // Manejar procesamiento del grafo
  const handleProcessGraph = async () => {
    setShowProcessingModal(true);
    await processKnowledgeGraph();
    setShowProcessingModal(false);
  };

  // Renderizar estado de carga inicial
  if (workspacesLoading || (isLoading && !graphData)) {
    return (
      <div className="knowledge-graph-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <h2>Cargando grafo de conocimiento...</h2>
          <p>Preparando la visualización de datos</p>
        </div>
      </div>
    );
  }

  // Renderizar error
  if (error) {
    return (
      <div className="knowledge-graph-page">
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <h2>Error cargando el grafo</h2>
          <p>{error}</p>
          <div className="error-actions">
            <Button onClick={clearError} variant="secondary">
              Reintentar
            </Button>
            <Button onClick={() => router.push('/workspaces')}>
              Volver a Workspaces
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Renderizar estado sin datos
  if (!graphData && processingStatus === 'not_processed') {
    return (
      <div className="knowledge-graph-page">
        <div className="no-data-container">
          <div className="no-data-icon">🧠</div>
          <h2>Grafo de conocimiento no generado</h2>
          <p>
            Este workspace aún no tiene un grafo de conocimiento generado.
            Procesa los documentos para crear visualizaciones interactivas.
          </p>
          <div className="no-data-stats">
            <div className="stat-card">
              <span className="stat-number">{workspace?.document_count || 0}</span>
              <span className="stat-label">Documentos disponibles</span>
            </div>
          </div>
          <Button onClick={handleProcessGraph} size="lg">
            🚀 Generar grafo de conocimiento
          </Button>
        </div>
      </div>
    );
  }

  // Renderizar estado de procesamiento
  if (processingStatus === 'processing' || showProcessingModal) {
    return (
      <div className="knowledge-graph-page">
        <div className="processing-container">
          <div className="processing-animation">
            <div className="processing-spinner"></div>
            <div className="processing-nodes">
              <div className="node node-1"></div>
              <div className="node node-2"></div>
              <div className="node node-3"></div>
            </div>
          </div>
          <h2>Procesando grafo de conocimiento</h2>
          <p>Analizando documentos y extrayendo relaciones semánticas...</p>
          <div className="processing-steps">
            <div className="step active">
              <span className="step-icon">📄</span>
              <span>Reconstruyendo documentos</span>
            </div>
            <div className="step active">
              <span className="step-icon">🔍</span>
              <span>Extrayendo entidades</span>
            </div>
            <div className="step processing">
              <span className="step-icon">🔗</span>
              <span>Analizando relaciones</span>
            </div>
            <div className="step">
              <span className="step-icon">🧠</span>
              <span>Generando grafo</span>
            </div>
          </div>
          <p className="processing-note">
            Este proceso puede tomar varios minutos dependiendo del número de documentos.
          </p>
        </div>
      </div>
    );
  }

  // Renderizar grafo principal
  return (
    <div className="knowledge-graph-page">
      {/* Header */}
      <div className="graph-header">
        <div className="header-left">
          <Button
            onClick={() => router.push('/workspaces')}
            variant="outline"
          >
            ← Volver
          </Button>
          <div className="header-info">
            <h1>Grafo de Conocimiento</h1>
            {workspace && (
              <span className="workspace-info">
                📁 {workspace.name} • {workspace.document_count} documentos
              </span>
            )}
          </div>
        </div>
        <div className="header-right">
          <Button
            variant="outline"
            onClick={() => router.push('/admin/knowledge-graph')}
          >
            <SettingsIcon className="mr-2 h-4 w-4" />
            Administración
          </Button>
        </div>
        
        <div className="header-actions">
          {stats && (
            <div className="header-stats">
              <div className="stat-item">
                <span className="stat-value">{stats.totalEntities.toLocaleString()}</span>
                <span className="stat-label">Entidades</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{stats.totalRelationships.toLocaleString()}</span>
                <span className="stat-label">Relaciones</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{stats.entityTypes.length}</span>
                <span className="stat-label">Tipos</span>
              </div>
            </div>
          )}
          
          <Button 
            onClick={refreshGraphData} 
            variant="secondary"
            disabled={isLoading}
          >
            🔄 Actualizar
          </Button>
          
          <Button 
            onClick={handleProcessGraph} 
            disabled={isLoading}
          >
            ⚡ Reprocesar
          </Button>
        </div>
      </div>

      {/* Visualizador principal */}
      <div className="graph-container">
        <KnowledgeGraphViewer
          graphData={graphData}
          onNodeSelect={handleNodeSelect}
          selectedWorkspace={workspace?.name || ''}
        />
      </div>

      {/* Panel lateral de información adicional */}
      {selectedNode && (
        <div className="side-panel">
          <div className="panel-header">
            <h3>🔍 Explorar conexiones</h3>
            <Button 
              onClick={() => setSelectedNode(null)}
              variant="destructive"
              size="icon"
              className="close-panel-btn"
            >
              ✕
            </Button>
          </div>
          
          <div className="panel-content">
            <div className="selected-entity">
              <h4>{selectedNode.data.label}</h4>
              <span className="entity-type">{selectedNode.data.type}</span>
            </div>
            
            <div className="connection-actions">
              <Button className="action-btn">
                🔗 Ver conexiones directas
              </Button>
              <Button className="action-btn">
                📄 Documentos relacionados
              </Button>
              <Button className="action-btn">
                🎯 Centrar en esta entidad
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Información del método de procesamiento */}
      {stats && (
        <div className="processing-info">
          <span className="processing-method">
            Procesado con: {stats.processingMethod === 'hybrid_pipeline' ? '🚀 Pipeline Híbrido' : '🧠 Cognee'}
          </span>
          {stats.lastProcessed && (
            <span className="last-processed">
              Última actualización: {new Date(stats.lastProcessed).toLocaleString()}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraphPage;