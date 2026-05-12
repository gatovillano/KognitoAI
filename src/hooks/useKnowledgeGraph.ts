'use client';

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api';

// Interfaces para tipar los datos
interface GraphNode {
  id: string;
  label: string;
  title?: string;
  color?: string;
  size?: number;
  type?: string; // Added type property
}

interface GraphEdge {
  id: string;
  source: string; // ID del nodo de origen
  target: string; // ID del nodo de destino
  from?: string; // Compatibilidad con Vis.js
  to?: string; // Compatibilidad con Vis.js
  label: string;  // Etiqueta principal de la relación (e.g., r.type)
  properties?: { // Hacer properties opcional
    type?: string; // e.g., 'FUNDAMENTACION_TEORICA'
    description?: string;
    [key: string]: any; // Para otras propiedades dinámicas
  };
  type?: string; // Para el tipo de relación
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata?: any; // Mantener metadata por si se usa para otras cosas
}

interface GraphStats {
  totalEntities: number;
  totalRelationships: number;
  entityTypes: string[];
  processingMethod: string;
  lastProcessed: string | null;
}

export const useKnowledgeGraph = (workspaceId: string | null) => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);

  const processKnowledgeGraph = useCallback(async () => {
    if (!workspaceId) return;

    setIsLoading(true);
    setError(null);
    setProcessingStatus('processing');

    try {
      const response = await apiClient.post('/api/knowledge-graph/process-knowledge-graph-optimized', {
        workspace_id: workspaceId,
        force_reprocess: false
      });
      console.log('🔵 Respuesta de la API (processKnowledgeGraph):', response.data);

      if (response.data && response.data.nodes && response.data.edges) {
        setGraphData({ nodes: response.data.nodes, edges: response.data.edges, metadata: response.data.metadata });
        setProcessingStatus('completed');
        if (response.data.metadata) {
          console.log('📊 Grafo procesado:', {
            nodos: response.data.nodes.length || 0,
            aristas: response.data.edges.length || 0,
            método: response.data.metadata.processing_method || 'unknown'
          });
        }
        console.log('🟢 Datos del grafo establecidos (processKnowledgeGraph):', { nodes: response.data.nodes.length, edges: response.data.edges.length });
      } else {
        console.error('🔴 Error: Datos del grafo incompletos o ausentes en la respuesta (processKnowledgeGraph):', response.data);
        throw new Error('Error procesando el grafo o datos incompletos');
      }
    } catch (err: any) {
      console.error('🔴 Error procesando grafo:', err);
      setError(err.message || 'Error procesando el grafo de conocimiento');
      setProcessingStatus('error');
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  const loadGraphData = useCallback(async (forceRefresh = false) => {
    if (!workspaceId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(`/api/knowledge-graph/${workspaceId}`);
      console.log('🔵 Respuesta de la API (loadGraphData):', response.data);

      if (response.data && response.data.nodes && response.data.edges) {
        setGraphData({ nodes: response.data.nodes, edges: response.data.edges, metadata: response.data.metadata });
        setProcessingStatus('completed');
        console.log('🟢 Datos del grafo establecidos (loadGraphData):', { nodes: response.data.nodes.length, edges: response.data.edges.length });
      } else if (response.data && response.data.error === "Grafo vacío. Procesa los documentos primero para generar el grafo.") {
        setError("Grafo vacío. Procesa los documentos primero para generar el grafo.");
        setProcessingStatus('not_processed');
        setGraphData(null); // Limpiar datos si el grafo está vacío
      } else {
        console.warn('🟡 Datos del grafo incompletos o ausentes, o error inesperado. Comprobando estado del procesamiento...');
        const statusResponse = await apiClient.get(`/api/knowledge-graph/status`, {
          params: { workspace_id: workspaceId }
        });

        if (statusResponse.data) {
          setProcessingStatus(statusResponse.data.status);
          console.log('🟡 Estado de procesamiento del grafo:', statusResponse.data.status);
          if (statusResponse.data.status === 'not_processed') {
            await processKnowledgeGraph();
          }
        }
      }
    } catch (err: any) {
      console.error('🔴 Error cargando datos del grafo:', err);
      setError(err.message || 'Error cargando el grafo de conocimiento');
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, processKnowledgeGraph]);

  const refreshGraphData = useCallback(() => {
    loadGraphData(true);
  }, [loadGraphData]);

  const searchGraph = useCallback(async (query: string) => {
    if (!workspaceId || !query) return [];

    try {
      const response = await apiClient.post('/api/knowledge-graph/search-graph', {
        workspace_id: workspaceId,
        query: query,
        limit: 50
      });

      return response.data ? (response.data.results || []) : [];
    } catch (err) {
      console.error('Error buscando en el grafo:', err);
      return [];
    }
  }, [workspaceId]);

  const getEntityConnections = useCallback(async (entityId: string, maxDepth = 2) => {
    if (!workspaceId || !entityId) return null;

    try {
      const response = await apiClient.post('/api/knowledge-graph/entity-connections', {
        workspace_id: workspaceId,
        entity_id: entityId,
        max_depth: maxDepth
      });

      return response.data ? response.data : null;
    } catch (err) {
      console.error('Error obteniendo conexiones:', err);
      return null;
    }
  }, [workspaceId]);

  const getGraphStats = useCallback(async () => {
    if (!workspaceId) return null;

    try {
      const response = await apiClient.get(`/api/knowledge-graph/stats`, {
        params: { workspace_id: workspaceId }
      });
      return response.data ? response.data : null;
    } catch (err) {
      console.error('Error obteniendo estadísticas:', err);
      return null;
    }
  }, [workspaceId]);
  const clearGraph = useCallback(async () => {
    try {
      const response = await apiClient.post('/api/knowledge-graph/clear-neo4j', { confirm_delete_all: true });
      console.log('🔵 Respuesta de la API (clearGraph):', response.data);
      if (response.data.success) {
        setGraphData(null);
        setProcessingStatus('not_processed');
      }
      return response.data;
    } catch (err) {
      console.error('Error limpiando el grafo:', err);
      return null;
    }
  }, []);

  useEffect(() => {
    if (workspaceId) {
      console.log('🟡 useEffect en useKnowledgeGraph: workspaceId detectado, cargando datos del grafo.', workspaceId);
      loadGraphData();
    } else {
      console.log('🟡 useEffect en useKnowledgeGraph: workspaceId no disponible.');
    }
  }, [workspaceId, loadGraphData]);

  const stats: GraphStats | null = graphData ? {
    totalEntities: graphData.nodes?.length || 0,
    totalRelationships: graphData.edges?.length || 0,
    entityTypes: [...new Set(graphData.nodes?.map(n => n.type).filter((type): type is string => type !== undefined) || [])], // Usar 'type' de los nodos
    processingMethod: graphData.metadata?.processing_method || 'unknown',
    lastProcessed: graphData.metadata?.processing_time || null
  } : null;

  return {
    graphData,
    stats,
    isLoading,
    error,
    processingStatus,
    loadGraphData,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    getEntityConnections,
    getGraphStats,
    clearError: () => setError(null),
    clearGraph
  };
};