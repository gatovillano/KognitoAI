'use client';

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api';

// Interfaces para tipar los datos
interface Entity {
  id: string;
  name: string;
  type: string;
  description?: string;
  confidence?: number;
  source_document?: string;
}

interface Relationship {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  description?: string;
  confidence?: number;
}

interface GraphData {
  entities: Entity[];
  relationships: Relationship[];
  metadata?: any;
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
      const response = await apiClient.post('/api/process-knowledge-graph', {
        workspace_id: workspaceId,
        force_reprocess: false
      });

      if (response.data) {
        setGraphData(response.data);
        setProcessingStatus('completed');
        if (response.data.metadata) {
          console.log('📊 Grafo procesado:', {
            entidades: response.data.entities?.length || 0,
            relaciones: response.data.relationships?.length || 0,
            método: response.data.metadata.processing_method || 'unknown'
          });
        }
      } else {
        throw new Error('Error procesando el grafo');
      }
    } catch (err: any) {
      console.error('Error procesando grafo:', err);
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

      if (response.data) {
        setGraphData(response.data);
        setProcessingStatus('completed');
      } else {
        const statusResponse = await apiClient.get(`/api/knowledge-graph/${workspaceId}/status`);

        if (statusResponse.data) {
          setProcessingStatus(statusResponse.data.status);
          if (statusResponse.data.status === 'not_processed') {
            await processKnowledgeGraph();
          }
        }
      }
    } catch (err: any) {
      console.error('Error cargando datos del grafo:', err);
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
      const response = await apiClient.post('/api/search-graph', {
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
      const response = await apiClient.post('/api/entity-connections', {
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
      const response = await apiClient.get(`/api/knowledge-graph/${workspaceId}/stats`);
      return response.data ? response.data : null;
    } catch (err) {
      console.error('Error obteniendo estadísticas:', err);
      return null;
    }
  }, [workspaceId]);

  useEffect(() => {
    if (workspaceId) {
      loadGraphData();
    }
  }, [workspaceId, loadGraphData]);

  const stats: GraphStats | null = graphData ? {
    totalEntities: graphData.entities?.length || 0,
    totalRelationships: graphData.relationships?.length || 0,
    entityTypes: [...new Set(graphData.entities?.map(e => e.type) || [])],
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
    clearError: () => setError(null)
  };
};