// frontend/src/hooks/useKnowledgeGraph.js

import { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '../utils/api';

export const useKnowledgeGraph = (workspaceId) => {
  const [graphData, setGraphData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);

  // Cargar datos del grafo
  const loadGraphData = useCallback(async (forceRefresh = false) => {
    if (!workspaceId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Primero verificar si hay datos del grafo
      const response = await apiRequest(`/api/knowledge-graph/${workspaceId}`, {
        method: 'GET'
      });

      if (response.success && response.data) {
        setGraphData(response.data);
        setProcessingStatus('completed');
      } else {
        // Si no hay datos, verificar si hay procesamiento en curso
        const statusResponse = await apiRequest(`/api/knowledge-graph/${workspaceId}/status`, {
          method: 'GET'
        });

        if (statusResponse.success) {
          setProcessingStatus(statusResponse.data.status);
          
          if (statusResponse.data.status === 'not_processed') {
            // Iniciar procesamiento automáticamente
            await processKnowledgeGraph();
          }
        }
      }
    } catch (err) {
      console.error('Error cargando datos del grafo:', err);
      setError(err.message || 'Error cargando el grafo de conocimiento');
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  // Procesar grafo de conocimiento
  const processKnowledgeGraph = useCallback(async () => {
    if (!workspaceId) return;

    setIsLoading(true);
    setError(null);
    setProcessingStatus('processing');

    try {
      const response = await apiRequest('/api/process-knowledge-graph', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: workspaceId,
          force_reprocess: false
        })
      });

      if (response.success) {
        setGraphData(response.data);
        setProcessingStatus('completed');
        
        // Mostrar estadísticas del procesamiento
        if (response.data.metadata) {
          console.log('📊 Grafo procesado:', {
            entidades: response.data.entities?.length || 0,
            relaciones: response.data.relationships?.length || 0,
            método: response.data.metadata.processing_method || 'unknown'
          });
        }
      } else {
        throw new Error(response.error || 'Error procesando el grafo');
      }
    } catch (err) {
      console.error('Error procesando grafo:', err);
      setError(err.message || 'Error procesando el grafo de conocimiento');
      setProcessingStatus('error');
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  // Recargar datos del grafo
  const refreshGraphData = useCallback(() => {
    loadGraphData(true);
  }, [loadGraphData]);

  // Buscar en el grafo
  const searchGraph = useCallback(async (query) => {
    if (!workspaceId || !query) return [];

    try {
      const response = await apiRequest('/api/search-graph', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: workspaceId,
          query: query,
          limit: 50
        })
      });

      if (response.success) {
        return response.data.results || [];
      }
      return [];
    } catch (err) {
      console.error('Error buscando en el grafo:', err);
      return [];
    }
  }, [workspaceId]);

  // Obtener conexiones de una entidad
  const getEntityConnections = useCallback(async (entityId, maxDepth = 2) => {
    if (!workspaceId || !entityId) return null;

    try {
      const response = await apiRequest('/api/entity-connections', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: workspaceId,
          entity_id: entityId,
          max_depth: maxDepth
        })
      });

      if (response.success) {
        return response.data;
      }
      return null;
    } catch (err) {
      console.error('Error obteniendo conexiones:', err);
      return null;
    }
  }, [workspaceId]);

  // Obtener estadísticas del grafo
  const getGraphStats = useCallback(async () => {
    if (!workspaceId) return null;

    try {
      const response = await apiRequest(`/api/knowledge-graph/${workspaceId}/stats`, {
        method: 'GET'
      });

      if (response.success) {
        return response.data;
      }
      return null;
    } catch (err) {
      console.error('Error obteniendo estadísticas:', err);
      return null;
    }
  }, [workspaceId]);

  // Cargar datos automáticamente cuando cambie el workspace
  useEffect(() => {
    if (workspaceId) {
      loadGraphData();
    }
  }, [workspaceId, loadGraphData]);

  // Estadísticas derivadas de los datos actuales
  const stats = graphData ? {
    totalEntities: graphData.entities?.length || 0,
    totalRelationships: graphData.relationships?.length || 0,
    entityTypes: [...new Set(graphData.entities?.map(e => e.type) || [])],
    processingMethod: graphData.metadata?.processing_method || 'unknown',
    lastProcessed: graphData.metadata?.processing_time || null
  } : null;

  return {
    // Datos
    graphData,
    stats,
    
    // Estados
    isLoading,
    error,
    processingStatus,
    
    // Acciones
    loadGraphData,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    getEntityConnections,
    getGraphStats,
    
    // Utilidades
    clearError: () => setError(null)
  };
};
