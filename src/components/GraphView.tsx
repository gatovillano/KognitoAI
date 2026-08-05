'use client';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Info, RefreshCcw, Search, ExternalLink, Brain, Network, GitGraph, Database, ArrowLeft, ChevronLeft, ChevronRight, X, Bookmark, ChevronDown, Trash2, AlertTriangle, Filter, Upload, AlertCircle, RefreshCw } from 'lucide-react';
import { useTaskContext } from '@/contexts/TaskContext';
import { DatasetNameDialog } from '@/app/(dashboard)/rag/dataset-name-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from 'sonner';
import dynamic from 'next/dynamic';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription as SheetDescriptionComp } from '@/components/ui/sheet';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api';
import { GraphFilters } from '@/components/KnowledgeGraph/GraphFilters';
import { NodeDetailsSidebar } from '@/components/KnowledgeGraph/NodeDetailsSidebar';
import { EdgeDetailsSidebar } from '@/components/KnowledgeGraph/EdgeDetailsSidebar';
import { GraphProcessingProgress } from '@/components/GraphProcessingProgress';
import { GraphMetadata, GraphFilters as GraphFiltersType } from '@/types/graph';
import { getNodeColor } from '@/utils/graphUtils';

// Componente de visualización del grafo cargado dinámicamente
import { GraphVisualizationRef } from '@/components/KnowledgeGraph/GraphVisualization';

const GraphVisualization = dynamic(() => import('@/components/KnowledgeGraph/GraphVisualization').then(mod => mod.GraphVisualization), {
  ssr: false,
  loading: () => (
    <div className="flex justify-center items-center h-full min-h-[500px]">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  ),
});

const normalizeGraphId = (value: any): string | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'object') {
    if (value.id !== undefined && value.id !== null) {
      return String(value.id);
    }
    if (value.name !== undefined && value.name !== null) {
      return String(value.name);
    }
  }
  return String(value);
};

// Hook personalizado para el grafo de conocimiento
const useKnowledgeGraph = (maxNodes: number, maxHops: number, selectedDataset: string, filters: GraphFiltersType, processingMode: 'hybrid' | 'conceptual' = 'hybrid') => {
  const [originalGraphData, setOriginalGraphData] = useState<{ nodes: any[], edges: any[] } | null>(null); // Store full graph
  const [displayGraphData, setDisplayGraphData] = useState<{ nodes: any[], edges: any[] } | null>(null); // Displayed graph
  const [metadata, setMetadata] = useState<GraphMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [availableDatasets, setAvailableDatasets] = useState<Array<{ name: string, node_count: number }>>([]);
  const [isInitialLoad, setIsInitialLoad] = useState(true); // Track initial load
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);

  const loadAvailableDatasets = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/knowledge-graph/datasets?workspace_id=all');
      if (response.data.success && response.data.data?.datasets) {
        setAvailableDatasets(response.data.data.datasets);
      }
    } catch (err) {
      console.error('Error loading datasets:', err);
    }
  }, []);


  const loadMetadata = useCallback(async () => {
    try {
      const datasetParam = selectedDataset !== 'all' ? `&dataset_name=${encodeURIComponent(selectedDataset)}` : '';
      const response = await apiClient.get(`/api/knowledge-graph/metadata?workspace_id=all${datasetParam}`);
      if (response.data.success) {
        setMetadata(response.data.data);
      }
    } catch (err) {
      console.error('Error loading metadata:', err);
    }
  }, [selectedDataset]);

  const applyClientFilters = useCallback(() => {
    if (!originalGraphData) {
      console.log("🔍 applyClientFilters: No hay originalGraphData");
      return;
    }

    console.log("🔍 applyClientFilters: Iniciando con", originalGraphData.nodes.length, "nodos y", originalGraphData.edges.length, "edges");
    console.log("🔍 focusedNodeId:", focusedNodeId);

    let filteredNodes = [...originalGraphData.nodes];
    let filteredEdges = [...originalGraphData.edges];

    if (focusedNodeId !== null) {
      console.log("🔍 Aplicando filtro por nodo enfocado:", focusedNodeId);

      const visibleNodeIds = new Set<string>([focusedNodeId]);
      const visibleEdges = originalGraphData.edges.filter(edge => {
        const edgeSource = normalizeGraphId(edge.from ?? edge.source);
        const edgeTarget = normalizeGraphId(edge.to ?? edge.target);
        const isConnectedToFocusedNode = edgeSource === focusedNodeId || edgeTarget === focusedNodeId;

        if (isConnectedToFocusedNode) {
          if (edgeSource !== null) visibleNodeIds.add(edgeSource);
          if (edgeTarget !== null) visibleNodeIds.add(edgeTarget);
        }

        return isConnectedToFocusedNode;
      });

      filteredNodes = originalGraphData.nodes.filter(node => {
        const nodeId = normalizeGraphId(node.id);
        return nodeId !== null && visibleNodeIds.has(nodeId);
      });
      filteredEdges = visibleEdges;

      console.log("🔍 Después del filtro por nodo enfocado:", filteredNodes.length, "nodos y", filteredEdges.length, "edges");
    }

    // Aplicar filtros de inclusión de tipos de nodo
    if (filters.nodeTypes.length > 0) {
      const nodeIds = new Set(filteredNodes
        .filter(node => filters.nodeTypes.includes(node.type))
        .map(node => String(node.id))
      );

      filteredNodes = filteredNodes.filter(node => nodeIds.has(String(node.id)));
      filteredEdges = filteredEdges.filter(edge => {
        const edgeSource = normalizeGraphId(edge.from ?? edge.source);
        const edgeTarget = normalizeGraphId(edge.to ?? edge.target);
        return edgeSource !== null && edgeTarget !== null && nodeIds.has(edgeSource) && nodeIds.has(edgeTarget);
      });
    }

    // Aplicar filtros de exclusión de tipos de nodo
    if (filters.excludedNodeTypes && filters.excludedNodeTypes.length > 0) {
      const excludedNodeIds = new Set(filteredNodes
        .filter(node => filters.excludedNodeTypes?.includes(node.type))
        .map(node => String(node.id))
      );

      filteredNodes = filteredNodes.filter(node => !excludedNodeIds.has(String(node.id)));
      filteredEdges = filteredEdges.filter(edge => {
        const edgeSource = normalizeGraphId(edge.from ?? edge.source);
        const edgeTarget = normalizeGraphId(edge.to ?? edge.target);
        return (edgeSource === null || !excludedNodeIds.has(edgeSource)) && (edgeTarget === null || !excludedNodeIds.has(edgeTarget));
      });
    }

    // Aplicar filtros de inclusión de tipos de relación
    if (filters.edgeTypes.length > 0) {
      filteredEdges = filteredEdges.filter(edge =>
        filters.edgeTypes.includes(edge.type || edge.label)
      );

      const connectedNodeIds = new Set<string>();
      filteredEdges.forEach(edge => {
        const edgeSource = normalizeGraphId(edge.from ?? edge.source);
        const edgeTarget = normalizeGraphId(edge.to ?? edge.target);
        if (edgeSource !== null) connectedNodeIds.add(edgeSource);
        if (edgeTarget !== null) connectedNodeIds.add(edgeTarget);
      });

      filteredNodes = filteredNodes.filter(node => connectedNodeIds.has(String(node.id)));
    }

    // Aplicar filtros de exclusión de tipos de relación
    if (filters.excludedEdgeTypes && filters.excludedEdgeTypes.length > 0) {
      filteredEdges = filteredEdges.filter(edge =>
        !filters.excludedEdgeTypes?.includes(edge.type || edge.label)
      );
    }

    console.log("🔍 Final: Enviando al display", filteredNodes.length, "nodos y", filteredEdges.length, "edges");
    setDisplayGraphData(prev => {
      if (
        prev &&
        prev.nodes.length === filteredNodes.length &&
        prev.edges.length === filteredEdges.length &&
        prev.nodes.every((n, i) => n.id === filteredNodes[i]?.id) &&
        prev.edges.every((e, i) => e.id === filteredEdges[i]?.id)
      ) {
        return prev;
      }
      return { nodes: filteredNodes, edges: filteredEdges };
    });
  }, [originalGraphData, filters, focusedNodeId]);

  const loadGraphData = useCallback(async (forceReload: boolean = false) => {
    // Si no es recarga forzada y ya tenemos datos, aplicar filtros en cliente
    if (!forceReload && originalGraphData && !isInitialLoad) {
      applyClientFilters();
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      try {
        const datasetParam = selectedDataset !== 'all' ? `&dataset_name=${encodeURIComponent(selectedDataset)}` : '';

        // Para la carga inicial, obtener datos sin filtros restrictivos para tener un conjunto completo
        const params = new URLSearchParams();
        params.append('workspace_id', 'all');
        params.append('limit', maxNodes.toString());
        params.append('max_hops', maxHops.toString());
        if (selectedDataset !== 'all') params.append('dataset_name', selectedDataset);

        // En carga inicial, no aplicar filtros de tipos para obtener todos los datos disponibles
        if (!isInitialLoad) {
          // Filtrar por tipos de nodo según el modo de procesamiento
          let nodeTypesToFilter = [...filters.nodeTypes];

          // Si no hay filtros seleccionados por el usuario, usar tipos por defecto según el modo
          if (nodeTypesToFilter.length === 0) {
            if (processingMode === 'conceptual') {
              // En modo conceptual, mostrar solo nodos conceptuales y documentos por defecto
              nodeTypesToFilter = ['CONCEPTUAL_QUOTE', 'IDEA_PROFILE', 'DOCUMENT'];
            }
            // En modo híbrido, no hay tipos por defecto (mostrar todos)
          }
          // Si el usuario ha seleccionado filtros específicos, respetarlos independientemente del modo

          nodeTypesToFilter.forEach(type => params.append('node_types', type));
          filters.edgeTypes.forEach(type => params.append('edge_types', type));
        }

        const response = await apiClient.get(`/api/knowledge-graph/data?${params.toString()}`);
        if (response.data.success) {
          setOriginalGraphData(response.data.data); // Store the full data
          setDisplayGraphData(response.data.data); // Also set for display initially
          if (isInitialLoad) {
            setIsInitialLoad(false);
          }
        } else {
          setOriginalGraphData({ nodes: [], edges: [] });
          setDisplayGraphData({ nodes: [], edges: [] });
        }
        setProcessingStatus('completed');
      } catch (err: any) {
        setError(err.message || 'Error cargando el grafo');
      } finally {
        setIsLoading(false);
      }
    } finally {
      setIsLoading(false);
    }
  }, [applyClientFilters, maxNodes, maxHops, selectedDataset, filters, processingMode, isInitialLoad, originalGraphData]);

  const processKnowledgeGraph = useCallback(async (setProcessingProgress?: React.Dispatch<React.SetStateAction<number>>, setProcessingMessage?: React.Dispatch<React.SetStateAction<string>>) => {
    setIsLoading(true);
    setError(null);
    setProcessingStatus('processing');
    if (setProcessingProgress) setProcessingProgress(0);
    if (setProcessingMessage) setProcessingMessage('Iniciando procesamiento...');

    try {
      // Simular progreso
      const progressInterval = setInterval(() => {
        if (setProcessingProgress) {
          setProcessingProgress((prev: number) => {
            const newProgress = prev + Math.random() * 15;
            if (newProgress >= 90) {
              clearInterval(progressInterval);
              return 90;
            }

            // Actualizar mensaje según progreso
            if (setProcessingMessage) {
              if (newProgress < 25) {
                setProcessingMessage('Analizando documentos...');
              } else if (newProgress < 50) {
                setProcessingMessage('Extrayendo entidades...');
              } else if (newProgress < 75) {
                setProcessingMessage('Generando relaciones...');
              } else {
                setProcessingMessage('Guardando en base de datos...');
              }
            }

            return newProgress;
          });
        }
      }, 1000);

      await apiClient.post('/api/knowledge-graph/process-knowledge-graph-optimized', {
        processing_mode: processingMode
      });

      clearInterval(progressInterval);
      if (setProcessingProgress) setProcessingProgress(100);
      if (setProcessingMessage) setProcessingMessage('Completado exitosamente');

      await loadGraphData();
      await loadMetadata();
      await loadAvailableDatasets();
      setProcessingStatus('completed');

      // Ocultar el indicador después de 3 segundos
      setTimeout(() => {
        setProcessingStatus('idle');
        if (setProcessingProgress) setProcessingProgress(0);
        if (setProcessingMessage) setProcessingMessage('');
      }, 3000);

    } catch (err: any) {
      setError(err.message || 'Error procesando el grafo');
      setProcessingStatus('error');
      if (setProcessingProgress) setProcessingProgress(0);
      if (setProcessingMessage) setProcessingMessage('Error en el procesamiento');
    } finally {
      setIsLoading(false);
    }
  }, [loadAvailableDatasets, loadGraphData, loadMetadata, processingMode]);

  const refreshGraphData = useCallback(() => {
    loadGraphData();
  }, [loadGraphData]);

  const searchGraph = useCallback(async (query: string) => {
    if (!query) return [];
    try {
      const response = await apiClient.post('/api/knowledge-graph/search-graph', { query });
      // Verificar si la respuesta es exitosa
      if (response.data.success) {
        return response.data.data?.results || [];
      } else {
        throw new Error(response.data.error || 'Error en la búsqueda');
      }
    } catch (err) {
      console.error('Error buscando en el grafo:', err);
      throw err; // Re-lanzar el error para que el componente padre lo maneje
    }
  }, []);

  useEffect(() => {
    loadGraphData(true); // Carga inicial con forceReload=true
    loadAvailableDatasets();
    loadMetadata();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Solo al montar el componente

  // Aplicar filtros en cliente cuando cambien los filtros o el filtro por nodo
  useEffect(() => {
    if (!isInitialLoad && originalGraphData) {
      applyClientFilters();
    }
  }, [filters, focusedNodeId, applyClientFilters, isInitialLoad, originalGraphData]);

  // Recargar datos cuando cambia el modo de procesamiento o parámetros que requieren nueva consulta
  useEffect(() => {
    if (!isInitialLoad) {
      loadGraphData(true); // Recargar desde servidor
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processingMode, maxNodes, maxHops, selectedDataset]);


  const effectiveMetadata = useMemo<GraphMetadata | null>(() => {
    if (!originalGraphData || !originalGraphData.nodes || originalGraphData.nodes.length === 0) {
      return metadata;
    }

    const nodeTypeCounts: Record<string, number> = {};
    originalGraphData.nodes.forEach(node => {
      const type = node.type || 'Desconocido';
      nodeTypeCounts[type] = (nodeTypeCounts[type] || 0) + 1;
    });

    const nodeTypes = Object.entries(nodeTypeCounts)
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);

    const edgeTypeCounts: Record<string, number> = {};
    (originalGraphData.edges || []).forEach(edge => {
      const type = edge.type || edge.label || 'RELACIONADO';
      edgeTypeCounts[type] = (edgeTypeCounts[type] || 0) + 1;
    });

    const edgeTypes = Object.entries(edgeTypeCounts)
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);

    return {
      nodeTypes,
      edgeTypes,
      datasets: metadata?.datasets || []
    };
  }, [originalGraphData, metadata]);

  const resetGraphFilter = useCallback(() => {
    setFocusedNodeId(null);
  }, []);

  const updateFilteredNodeId = useCallback((nodeId: string | number | null) => {
    const normalized = normalizeGraphId(nodeId);
    setFocusedNodeId(prev => (prev === normalized ? null : normalized));
  }, []);

  return {
    graphData: displayGraphData, // Return displayGraphData
    metadata: effectiveMetadata,
    isLoading,
    error,
    processingStatus,
    setProcessingStatus,
    availableDatasets,
    loadGraphData,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    clearError: () => setError(null),
    resetGraphFilter, // Expose new function
    updateFilteredNodeId, // Expose toggle function
    focusedNodeId,
    deleteDataset: async (datasetName: string) => {
      try {
        const response = await apiClient.delete(`/api/knowledge-graph/datasets/${encodeURIComponent(datasetName)}`);
        if (response.data.success) {
          toast.success(`Dataset "${datasetName}" eliminado correctamente.`);
          await loadAvailableDatasets();
          return true;
        } else {
          toast.error(response.data.error || 'Error al eliminar el dataset');
          return false;
        }
      } catch (err) {
        console.error('Error deleting dataset:', err);
        toast.error('Error al eliminar el dataset');
        return false;
      }
    }
  };
};

export function GraphView() {
  const router = useRouter();
  const graphVisualizationRef = useRef<GraphVisualizationRef>(null); // Ref para el componente GraphVisualization
  const [graphQuery, setGraphQuery] = useState('');
  const [maxNodes, setMaxNodes] = useState(100);
  const [maxHops, setMaxHops] = useState(2);
  const [selectedDataset, setSelectedDataset] = useState('all');
  const [processingMode, setProcessingMode] = useState<'hybrid' | 'conceptual'>('hybrid');
  const [filters, setFilters] = useState<GraphFiltersType>({
    nodeTypes: [],
    edgeTypes: [],
    excludedNodeTypes: [],
    excludedEdgeTypes: [],
    datasetName: 'all'
  });


  // Estado para el panel de detalles del nodo
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [isNodeDetailsOpen, setIsNodeDetailsOpen] = useState(false);

  // Estado para el panel de detalles de la relación
  const [selectedEdge, setSelectedEdge] = useState<any>(null);
  const [isEdgeDetailsOpen, setIsEdgeDetailsOpen] = useState(false);

  // Estado para el panel de filtros desplegable
  const [isFiltersExpanded, setIsFiltersExpanded] = useState(true);

  // Estado para el progreso de procesamiento
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState('');

  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false);
  const [savedNodes, setSavedNodes] = useState<any[]>([]);
  const [isSavedNodesOpen, setIsSavedNodesOpen] = useState(false);

  // Estados para procesamiento avanzado de grafos
  const [isDatasetDialogOpen, setIsDatasetDialogOpen] = useState(false);
  const [isProcessingMemories, setIsProcessingMemories] = useState(false);
  const [processingTopic, setProcessingTopic] = useState<string | null>(null);
  const [processingWorkspaceId, setProcessingWorkspaceId] = useState<string | null>(null);

  const { analysisTasks, addAnalysisTask, updateAnalysisTask, removeAnalysisTask } = useTaskContext();

  const {
    graphData,
    metadata,
    isLoading,
    error,
    processingStatus,
    availableDatasets,
    processKnowledgeGraph: originalProcessKnowledgeGraph,
    setProcessingStatus,
    loadGraphData,
    refreshGraphData,
    searchGraph,
    clearError,
    resetGraphFilter, // Get new function from hook
    updateFilteredNodeId, // Get setter function from hook
    focusedNodeId,
    deleteDataset,
  } = useKnowledgeGraph(maxNodes, maxHops, selectedDataset, filters, processingMode);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const filterGraphByNode = useCallback((nodeId: string | number) => {
    console.log("🔍 filterGraphByNode llamado con nodeId:", nodeId);
    // Actualizar el estado del filtro por nodo usando la función del hook
    updateFilteredNodeId(nodeId);
    console.log("🔍 Nodo enfocado actualizado");
  }, [updateFilteredNodeId]);

  useEffect(() => {
    if (error) {
      toast.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleSearchGraph = useCallback(async () => {
    if (!graphQuery.trim()) {
      setSearchResults([]);
      setSearchError(null);
      return;
    }

    setIsSearching(true);
    setSearchError(null);

    try {
      const results = await searchGraph(graphQuery);
      setSearchResults(results);
      if (results.length === 0) {
        setSearchError('No se encontraron resultados para tu búsqueda.');
      }
    } catch (err: any) {
      console.error('Error en búsqueda:', err);
      setSearchError(err.message || 'Error al realizar la búsqueda');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [graphQuery, searchGraph]);

  const handleProcessGraph = useCallback(async () => {
    setProcessingTopic(null);
    setProcessingWorkspaceId(null);
    setIsDatasetDialogOpen(true);
  }, []);

  const handleConfirmProcessGraph = async (datasetName: string, mode: 'hybrid' | 'conceptual') => {
    const toastId = toast.loading(
      processingTopic
        ? `Procesando grafo de conocimiento para "${processingTopic}" (Modo: ${mode === 'hybrid' ? 'Estándar' : 'Conceptual'})...`
        : `Procesando grafo global (Modo: ${mode === 'hybrid' ? 'Estándar' : 'Conceptual'})...`
    );

    try {
      // Inicializar tarea localmente para feedback inmediato
      const tempTaskId = `temp-${Date.now()}`;
      addAnalysisTask({
        task_id: tempTaskId,
        phase: 'initializing',
        message: 'Iniciando procesamiento...',
        progress_percent: 0,
        is_complete: false,
        has_error: false,
        processing_mode: mode,
        topic: processingTopic || undefined,
        type: 'graph'
      });

      // Determinar qué endpoint usar basado en el modo
      if (mode === 'conceptual') {
        // Modo Conceptual: Usar la herramienta de Procesamiento Conceptual
        const payload = {
          tool_name: "conceptual_processing",
          action: "process_documents",
          dataset_name: datasetName,
          topic: processingTopic || undefined,
          documents: [],
          workspace_id: processingWorkspaceId || undefined,
          task_id: tempTaskId,
          background: true
        };
        const response = await apiClient.post('/api/skills/run', payload);

        if (response.data?.task_id) {
          updateAnalysisTask(tempTaskId, { task_id: response.data.task_id });
        }
      } else {
        // Modo Híbrido (Estándar): Llamar al endpoint optimizado
        const response = await apiClient.post('/api/knowledge-graph/process-knowledge-graph-optimized', {
          workspace_id: processingWorkspaceId || undefined,
          dataset_name: datasetName,
          topic: processingTopic || undefined,
          force_reprocess: true
        });

        if (response.data?.task_id) {
          updateAnalysisTask(tempTaskId, { task_id: response.data.task_id });
        }
      }

      toast.success(`¡Creación de grafo iniciada!`, { id: toastId });
    } catch (error) {
      console.error(error);
      toast.error("Error al iniciar el procesamiento del grafo.", { id: toastId });
      analysisTasks
        .filter(task => task.task_id.startsWith('temp-'))
        .forEach(task => removeAnalysisTask(task.task_id));
    } finally {
      setIsDatasetDialogOpen(false);
      setProcessingTopic(null);
      setProcessingWorkspaceId(null);
    }
  };

  const handleClearKnowledgeGraph = async () => {
    if (window.confirm('¿Estás seguro de que quieres borrar TODO el grafo de conocimiento de tu cuenta? Esta acción es irreversible y afectará a todos tus documentos procesados.')) {
      const toastId = toast.loading("Limpiando el grafo de conocimiento...");
      try {
        await apiClient.post('/api/knowledge-graph/clear-neo4j', { confirm_delete_all: true });
        toast.success("El grafo de conocimiento ha sido limpiado.", { id: toastId });
        refreshGraphData();
      } catch (error) {
        toast.error("Error al limpiar el grafo de conocimiento.", { id: toastId });
      }
    }
  };

  const handleProcessMemories = async (force: boolean = false) => {
    if (isProcessingMemories) return;

    const confirmMsg = force
      ? '¿Reprocesar TODAS las memorias desde cero? Esto ignorará las ya procesadas.'
      : '¿Deseas procesar todas las memorias pendientes de KAI e integrarlas al grafo?';

    if (!window.confirm(confirmMsg)) {
      return;
    }

    setIsProcessingMemories(true);
    setProcessingStatus('processing');
    setProcessingProgress(5);
    setProcessingMessage(force ? 'Reseteando y reprocesando todas las memorias...' : 'Iniciando procesamiento de memorias...');
    const toastId = toast.loading(force ? "Reprocesando todas las memorias..." : "Procesando memorias de KAI...");

    let pollInterval: ReturnType<typeof setInterval> | null = null;

    try {
      const url = force
        ? '/api/knowledge-graph/process-memories?force=true'
        : '/api/knowledge-graph/process-memories';
      const response = await apiClient.post(url);
      const taskId: string | undefined = response.data?.data?.task_id;

      if (!taskId) {
        // Sin task_id: fallback a toast simple
        toast.success("Procesamiento de memorias iniciado.", { id: toastId });
        setProcessingProgress(0);
        setProcessingMessage('');
        setProcessingStatus('idle');
        setIsProcessingMemories(false);
        return;
      }

      // Polling con backoff progresivo: rápido al inicio, más lento si tarda
      let pollCount = 0;
      const getNextInterval = () => {
        if (pollCount < 5) return 1500;   // primeros 7.5s: rápido
        if (pollCount < 15) return 3000;  // hasta ~37s: normal
        return 5000;                      // después: lento (reduce noise en tareas largas)
      };

      const doPoll = async () => {
        try {
          const prog = await apiClient.get(`/api/knowledge-graph/progress/${taskId}`);
          const data = prog.data?.data;
          if (!data) { scheduleNext(); return; }

          const percent: number = data.progress_percent ?? 0;
          const msg: string = data.message ?? '';
          const isComplete: boolean = data.is_complete ?? false;
          const hasError: boolean = data.has_error ?? false;

          setProcessingProgress(percent);
          setProcessingMessage(msg);

          if (isComplete) {
            setProcessingStatus('completed');
            toast.success(msg || "Memorias integradas al grafo.", { id: toastId });
            setIsProcessingMemories(false);
            await loadGraphData(true);
            setTimeout(() => {
              setProcessingProgress(0);
              setProcessingMessage('');
              setProcessingStatus('idle');
            }, 4000);
          } else if (hasError) {
            setProcessingStatus('error');
            toast.error(`Error: ${data.error || msg}`, { id: toastId });
            setIsProcessingMemories(false);
            setTimeout(() => {
              setProcessingProgress(0);
              setProcessingMessage('');
              setProcessingStatus('idle');
            }, 4000);
          } else {
            pollCount++;
            scheduleNext();
          }
        } catch {
          // Error de red: reintentar con intervalo normal
          pollCount++;
          scheduleNext();
        }
      };

      const scheduleNext = () => {
        pollInterval = setTimeout(doPoll, getNextInterval()) as unknown as ReturnType<typeof setInterval>;
      };

      scheduleNext();

    } catch (error) {
      if (pollInterval) clearTimeout(pollInterval as unknown as ReturnType<typeof setTimeout>);
      console.error(error);
      toast.error("Error al iniciar el procesamiento de memorias.", { id: toastId });
      setProcessingProgress(0);
      setProcessingMessage('');
      setProcessingStatus('error');
      setIsProcessingMemories(false);
    }
  };

  const handleOptimizeKnowledgeGraph = async () => {
    if (!window.confirm('¿Deseas analizar el grafo para fusionar duplicados y eliminar irrelevancias? Esta acción optimizará la memoria del agente.')) {
      return;
    }

    const toastId = toast.loading("Analizando grafo en busca de optimizaciones...");
    try {
      const reviewRes = await apiClient.post('/api/knowledge-graph/review-entities', {});
      const corrections = reviewRes.data?.corrections || [];
      
      if (corrections.length === 0) {
        toast.success("El grafo ya está optimizado. No se encontraron duplicados ni problemas.", { id: toastId });
        return;
      }
      
      toast.loading(`Aplicando ${corrections.length} optimizaciones...`, { id: toastId });
      
      const applyRes = await apiClient.post('/api/knowledge-graph/apply-corrections', {
        corrections: corrections,
        auto_apply: true
      });
      
      toast.success(`Grafo optimizado. Se aplicaron ${applyRes.data?.applied || 0} correcciones automáticamente.`, { id: toastId });
      refreshGraphData();
    } catch (error) {
      console.error(error);
      toast.error("Error al optimizar el grafo.", { id: toastId });
    }
  };

  const handleNodeClick = useCallback((node: any) => {
    console.log("🔍 handleNodeClick llamado con nodo:", node);
    if (!node || !node.id) {
      console.warn("⚠️ handleNodeClick: Nodo inválido recibido o sin ID.");
      setIsNodeDetailsOpen(false);
      setSelectedNode(null);
      return;
    }

    // Si el nodo clicado es el mismo que el ya seleccionado y el sidebar está abierto, cerrarlo.
    // De lo contrario, abrir el sidebar con el nuevo nodo.
    if (selectedNode && selectedNode.id === node.id && isNodeDetailsOpen) {
      setIsNodeDetailsOpen(false);
      setSelectedNode(null);
      console.log("🔍 Sidebar cerrado: click en el mismo nodo ya seleccionado.");
    } else {
      setSelectedNode(node);
      setIsNodeDetailsOpen(true);
      setIsEdgeDetailsOpen(false); // Cerrar sidebar de edge si está abierto
      setSelectedEdge(null);
      console.log("🔍 Sidebar de detalles abierto para nodo:", node.id, "Estado selectedNode:", node, "Estado isNodeDetailsOpen:", true);
    }
  }, [selectedNode, isNodeDetailsOpen]);

  const handleEdgeClick = useCallback((edge: any) => {
    console.log("🔍 handleEdgeClick llamado con edge:", edge);
    if (!edge || !edge.id) {
      console.warn("⚠️ handleEdgeClick: Edge inválido recibido o sin ID.");
      setIsEdgeDetailsOpen(false);
      setSelectedEdge(null);
      return;
    }

    // Si el edge clicado es el mismo que el ya seleccionado y el sidebar está abierto, cerrarlo.
    // De lo contrario, abrir el sidebar con el nuevo edge.
    if (selectedEdge && selectedEdge.id === edge.id && isEdgeDetailsOpen) {
      setIsEdgeDetailsOpen(false);
      setSelectedEdge(null);
      console.log("🔍 Sidebar cerrado: click en el mismo edge ya seleccionado.");
    } else {
      setSelectedEdge(edge);
      setIsEdgeDetailsOpen(true);
      setIsNodeDetailsOpen(false); // Cerrar sidebar de nodo si está abierto
      setSelectedNode(null);
      console.log("🔍 Sidebar de detalles abierto para edge:", edge.id, "Estado selectedEdge:", edge, "Estado isEdgeDetailsOpen:", true);
    }
  }, [selectedEdge, isEdgeDetailsOpen]);

  const handleCloseNodeDetails = useCallback(() => {
    setIsNodeDetailsOpen(false);
    setSelectedNode(null);
  }, []);

  const handleCloseEdgeDetails = useCallback(() => {
    setIsEdgeDetailsOpen(false);
    setSelectedEdge(null);
  }, []);

  const toggleSaveNode = useCallback((node: any) => {
    setSavedNodes(prev => {
      const isAlreadySaved = prev.some(n => n.id === node.id);
      if (isAlreadySaved) {
        toast.success(`Nodo "${node.label}" eliminado de la lista`);
        return prev.filter(n => n.id !== node.id);
      } else {
        toast.success(`Nodo "${node.label}" guardado en la lista`);
        return [...prev, node];
      }
    });
  }, []);

  const focusNode = useCallback((nodeId: string | number) => {
    // Aquí podríamos implementar el enfoque en el componente de visualización
    // Por ahora, al menos nos aseguramos de que el nodo esté en los expandidos
    updateFilteredNodeId(nodeId);
    // Y cerramos el panel de guardados para ver el grafo
    setIsSavedNodesOpen(false);
  }, [updateFilteredNodeId]);

  const renderGraphContent = () => {
    if (isLoading && !graphData) {
      return (
        <div className="flex flex-col items-center justify-center p-8">
          <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
          <p className="text-muted-foreground text-lg">Cargando grafo de conocimiento...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <Info className="h-10 w-10 text-destructive mb-4" />
          <h3 className="text-xl font-semibold text-destructive mb-2">Error al cargar el grafo</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          {processingStatus === 'not_processed' && (
            <Button onClick={handleProcessGraph}>
              <Brain className="h-4 w-4 mr-2" /> Procesar Grafo Ahora
            </Button>
          )}
        </div>
      );
    }

    if (graphData && graphData.nodes && graphData.nodes.length > 0) {
      return (
        <div className="w-full h-full relative">
          <GraphVisualization
            ref={graphVisualizationRef} // Asignar la ref
            graphData={graphData}
            metadata={metadata}
            onNodeClick={handleNodeClick}
            onNodeDoubleClick={filterGraphByNode} // Pass the new handler
            onEdgeClick={handleEdgeClick} // Pass the new handler
            savedNodeIds={new Set(savedNodes.map(n => n.id))}
            focusedNodeId={focusedNodeId}
          />
        </div>
      );
    }

    if (!isLoading && (!graphData || !graphData.nodes || graphData.nodes.length === 0)) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <GitGraph className="h-16 w-16 text-muted-foreground/50 mb-6" />
          <h3 className="text-xl font-semibold mb-4">Grafo de Conocimiento Vacío</h3>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Aún no se ha generado un grafo de conocimiento.
            Procesa tus documentos para comenzar a visualizar las conexiones.
          </p>
          <Button onClick={handleProcessGraph} disabled={processingStatus === 'processing'}>
            {processingStatus === 'processing' ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Brain className="h-4 w-4 mr-2" />
            )}
            Procesar Grafo Ahora
          </Button>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="p-2 sm:p-4 w-full flex flex-col h-[calc(100vh-10rem)] overflow-hidden">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-3xl font-bold tracking-tight">
          Grafos de Conocimiento
        </h2>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
          <Info className="h-5 w-5" />
        </Button>
      </div>

      <Card className="flex flex-col flex-1 overflow-hidden">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-6 w-6" />
            Visualización del Grafo
            <div className="flex items-center gap-2 ml-auto">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2">
                    Acciones <ChevronDown className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem onClick={() => setIsSavedNodesOpen(true)} className="cursor-pointer">
                    <Bookmark className="h-4 w-4 mr-2" /> Lista ({savedNodes.length})
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={resetGraphFilter} disabled={isLoading} className="cursor-pointer">
                    <X className="h-4 w-4 mr-2" /> Limpiar Filtro
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={refreshGraphData} disabled={isLoading} className="cursor-pointer">
                    <RefreshCcw className="h-4 w-4 mr-2" /> Actualizar
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => {
                    updateFilteredNodeId(null);
                    setSearchResults([]);
                    setGraphQuery('');
                    setSearchError(null);
                    setSelectedNode(null);
                    setSelectedEdge(null);
                    setIsNodeDetailsOpen(false);
                    setIsEdgeDetailsOpen(false);
                    graphVisualizationRef.current?.fitView();
                  }} className="cursor-pointer">
                    <GitGraph className="h-4 w-4 mr-2" /> Vista Completa
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={handleProcessGraph}
                    disabled={processingStatus === 'processing'}
                    className="cursor-pointer font-medium text-primary"
                  >
                    <Brain className="mr-2 h-4 w-4" />
                    <span>{processingStatus === 'processing' ? "Procesando Grafos..." : "Crear Grafos de Conocimiento"}</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={handleClearKnowledgeGraph}
                    className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
                  >
                    <AlertTriangle className="mr-2 h-4 w-4" />
                    <span>Limpiar Grafo Global</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={handleOptimizeKnowledgeGraph}
                    className="cursor-pointer text-blue-600 focus:text-blue-600 focus:bg-blue-50"
                  >
                    <Filter className="mr-2 h-4 w-4" />
                    <span>Optimizar y Limpiar Grafo</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => handleProcessMemories(true)}
                    disabled={isProcessingMemories}
                    className="cursor-pointer text-purple-600 focus:text-purple-600 focus:bg-purple-50"
                  >
                    {isProcessingMemories ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Brain className="mr-2 h-4 w-4" />
                    )}
                    <span>Procesar memorias de KAI</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col flex-1 overflow-hidden">
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-4">
              <Input
                placeholder="Buscar entidades en el grafo..."
                value={graphQuery}
                onChange={(e) => setGraphQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isSearching && handleSearchGraph()}
                className="flex-grow"
                disabled={isSearching}
              />
              <Button onClick={handleSearchGraph} disabled={isSearching || !graphQuery.trim()}>
                {isSearching ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Search className="h-4 w-4 mr-2" />
                )}
                {isSearching ? 'Buscando...' : 'Buscar'}
              </Button>
            </div>
            {(searchResults.length > 0 || searchError) && (
              <div className="bg-muted p-3 rounded-md max-h-40 overflow-y-auto">
                {searchError ? (
                  <div className="text-sm text-destructive">
                    <p className="font-semibold mb-1">Error en la búsqueda:</p>
                    <p>{searchError}</p>
                  </div>
                ) : (
                  <>
                    <p className="text-sm font-semibold mb-2">Resultados de la búsqueda ({searchResults.length}):</p>
                    {searchResults.map((result) => (
                      <div key={result.id} className="flex items-center justify-between text-sm py-1 hover:bg-background rounded px-1">
                        <span className="flex-1">
                          {result.label || result.name} ({result.type})
                        </span>
                        <Button
                          variant="link"
                          size="sm"
                          className="h-auto p-0 text-primary"
                          onClick={() => {
                            // Por ahora solo mostrar en consola, se puede implementar enfoque después
                            console.log('Nodo seleccionado:', result);
                          }}
                        >
                          <ExternalLink className="h-3 w-3 mr-1" /> Seleccionar
                        </Button>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Label htmlFor="dataset-select" className="mb-2 block flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Dataset
                </Label>
                <Select value={selectedDataset} onValueChange={setSelectedDataset}>
                  <SelectTrigger id="dataset-select" className="w-full max-w-[200px]">
                    <SelectValue placeholder="Seleccionar dataset" className="truncate" />
                  </SelectTrigger>
                  <SelectContent className="max-w-[400px]">
                    <SelectItem value="all">
                      <span className="truncate block">
                        Todos los datasets ({availableDatasets.reduce((sum, d) => sum + d.node_count, 0)} nodos)
                      </span>
                    </SelectItem>
                    {availableDatasets.map((dataset) => (
                      <SelectItem key={dataset.name} value={dataset.name}>
                        <span className="truncate block">
                          {dataset.name} ({dataset.node_count} nodos)
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {selectedDataset !== 'all' && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline" size="icon" className="text-destructive hover:bg-destructive/10 border-destructive/20 h-10 w-10 shrink-0">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>¿Eliminar dataset?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Esta acción eliminará permanentemente todos los nodos y relaciones asociados al dataset <strong>{selectedDataset}</strong> del grafo de conocimiento. Esta acción no se puede deshacer.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancelar</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={async () => {
                          const success = await deleteDataset(selectedDataset);
                          if (success) {
                            setSelectedDataset('all');
                            refreshGraphData();
                          }
                        }}
                        className="bg-destructive hover:bg-destructive/90"
                      >
                        Eliminar Dataset
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </div>
            <div>
              <Label htmlFor="processing-mode-select" className="mb-2 block flex items-center gap-2">
                <Brain className="h-4 w-4" />
                Modo de Procesamiento
              </Label>
              <Select value={processingMode} onValueChange={(value: 'hybrid' | 'conceptual') => setProcessingMode(value)}>
                <SelectTrigger id="processing-mode-select" className="w-full">
                  <SelectValue placeholder="Seleccionar modo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hybrid">Híbrido (spaCy + Embeddings)</SelectItem>
                  <SelectItem value="conceptual">Conceptual (LLM-driven)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="max-nodes" className="mb-2 block flex items-center gap-2">
                Número de Nodos a Mostrar: {maxNodes}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>
                        Este valor define el número máximo de nodos que se cargarán inicialmente.
                        El número real de nodos mostrados puede ser menor si los filtros aplicados
                        (por tipo de nodo, relación o dataset) reducen la cantidad de resultados disponibles.
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </Label>
              <Input
                id="max-nodes"
                type="number"
                min={10}
                value={maxNodes}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value === '') {
                    setMaxNodes(25);
                    return;
                  }
                  const numValue = parseInt(value);
                  if (!isNaN(numValue)) {
                    setMaxNodes(numValue);
                  }
                }}
                onBlur={(e) => {
                  const value = parseInt(e.target.value);
                  if (isNaN(value)) {
                    setMaxNodes(100);
                  } else {
                    // Eliminamos el límite superior de 2000
                    setMaxNodes(Math.max(10, value));
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    (e.target as HTMLInputElement).blur();
                  }
                }}
                className="w-full"
              />
            </div>
            <div>
              <Label htmlFor="max-hops" className="mb-2 block">Saltos Máximos: {maxHops}</Label>
              <Input
                id="max-hops"
                type="number"
                min={1}
                max={5}
                value={maxHops}
                onChange={(e) => {
                  const value = e.target.value;
                  // Permitir campo vacío mientras se edita
                  if (value === '') {
                    setMaxHops(2); // Valor temporal, se validará en onBlur
                    return;
                  }
                  const numValue = parseInt(value);
                  if (!isNaN(numValue)) {
                    // Permitir valores fuera de rango mientras se edita, validar en onBlur
                    setMaxHops(numValue);
                  }
                }}
                onBlur={(e) => {
                  const value = parseInt(e.target.value);
                  if (isNaN(value)) {
                    setMaxHops(2); // Valor por defecto si es inválido
                  } else {
                    setMaxHops(Math.max(1, Math.min(5, value)));
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    (e.target as HTMLInputElement).blur(); // Aplicar cambios al presionar Enter
                  }
                }}
                className="w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 overflow-hidden">
            <div className={`transition-all duration-300 ${isFiltersExpanded ? 'lg:col-span-4' : 'lg:col-span-1'} flex flex-col overflow-hidden`}>
              <div className="flex items-center justify-between mb-4 flex-shrink-0">
                <h3 className="text-lg font-semibold">Filtros</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsFiltersExpanded(!isFiltersExpanded)}
                  className="h-8 w-8 p-0"
                >
                  {isFiltersExpanded ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </Button>
              </div>
              <ScrollArea className={`flex-1 ${isFiltersExpanded ? 'block' : 'hidden'}`}>
                <GraphFilters
                  metadata={metadata}
                  filters={filters}
                  onFiltersChange={setFilters}
                  totalNodes={metadata?.nodeTypes.reduce((acc: number, t: { count: number }) => acc + t.count, 0) || 0}
                  totalEdges={metadata?.edgeTypes.reduce((acc: number, t: { count: number }) => acc + t.count, 0) || 0}
                  filteredNodes={graphData?.nodes.length || 0}
                  filteredEdges={graphData?.edges.length || 0}
                  getNodeColor={getNodeColor}
                />
              </ScrollArea>
            </div>
            <div className={`${isFiltersExpanded ? 'lg:col-span-8' : 'lg:col-span-11'} border rounded-lg overflow-hidden bg-background flex flex-col`}>
              {renderGraphContent()}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Panel de detalles del nodo */}
      <NodeDetailsSidebar
        node={selectedNode}
        onClose={handleCloseNodeDetails}
        isOpen={isNodeDetailsOpen}
        onToggleSave={toggleSaveNode}
        isSaved={selectedNode ? savedNodes.some(n => n.id === selectedNode.id) : false}
      />

      {/* Panel de detalles del edge */}
      <EdgeDetailsSidebar
        edge={selectedEdge}
        onClose={handleCloseEdgeDetails}
        isOpen={isEdgeDetailsOpen}
        sourceNode={graphData?.nodes.find(n => n.id === selectedEdge?.from)}
        targetNode={graphData?.nodes.find(n => n.id === selectedEdge?.to)}
      />

      {/* Indicador de progreso de procesamiento */}
      <GraphProcessingProgress
        isVisible={processingProgress > 0 || processingMessage !== ''}
        status={processingStatus === 'processing' ? 'processing' : processingStatus === 'completed' ? 'completed' : processingStatus === 'error' ? 'error' : 'idle'}
        progress={processingProgress}
        message={processingMessage}
        mode={processingMode}
        onClose={() => {
          setProcessingProgress(0);
          setProcessingMessage('');
        }}
      />
      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Grafos de Conocimiento</SheetTitle>
            <SheetDescriptionComp className="text-sm text-muted-foreground">
              Explora y visualiza las conexiones semánticas y conceptuales entre tus documentos y datos.
            </SheetDescriptionComp>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué es el Grafo de Conocimiento?</strong></p>
            <p>Es una representación visual de cómo se relacionan tus datos. Kognito AI analiza tus documentos para extraer entidades (personas, lugares, conceptos) y las relaciones entre ellas.</p>

            <p><strong>Modos de Procesamiento:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Híbrido (spaCy + Embeddings):</strong> Combina análisis lingüístico tradicional con modelos de lenguaje para una extracción precisa de entidades y relaciones explícitas. Ideal para ver conexiones directas.</li>
              <li><strong>Conceptual (LLM-driven):</strong> Utiliza modelos de lenguaje avanzados para identificar conceptos abstractos, temas y relaciones temáticas. Ideal para descubrir conexiones ocultas o ideas transversales.</li>
            </ul>

            <p><strong>Funcionalidades Clave:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Búsqueda de Entidades:</strong> Localiza rápidamente nodos específicos en el grafo.</li>
              <li><strong>Filtros Avanzados:</strong> Filtra por tipo de nodo (ej. Persona, Organización) o tipo de relación para enfocar tu análisis.</li>
              <li><strong>Exploración Interactiva:</strong> Haz clic en nodos y relaciones para ver detalles, metadatos y fragmentos de texto originales.</li>
              <li><strong>Doble Clic:</strong> Haz doble clic en un nodo para centrar la vista y filtrar el grafo mostrando solo sus conexiones directas.</li>
            </ul>

            <p><strong>Consejos de Uso:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Utiliza el selector de <strong>Dataset</strong> para limitar la visualización a un conjunto específico de documentos.</li>
              <li>Ajusta el número de <strong>Nodos a Mostrar</strong> y <strong>Saltos Máximos</strong> para controlar la complejidad del grafo visualizado.</li>
              <li>Si el grafo está vacío, asegúrate de haber procesado tus documentos utilizando el botón "Procesar Grafo Ahora".</li>
            </ul>
          </div>
        </SheetContent>
      </Sheet>
      <Sheet open={isSavedNodesOpen} onOpenChange={setIsSavedNodesOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md flex flex-col h-full">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Bookmark className="h-5 w-5 text-primary" />
              Nodos Guardados ({savedNodes.length})
            </SheetTitle>
            <SheetDescriptionComp>
              Lista de entidades y conceptos marcados como de interés.
            </SheetDescriptionComp>
          </SheetHeader>

          <div className="flex-1 overflow-hidden flex flex-col mt-6">
            {savedNodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-8 opacity-50">
                <Bookmark className="h-12 w-12 mb-4" />
                <p>No tienes nodos guardados aún.</p>
                <p className="text-xs">Haz clic en un nodo y usa el icono de marcador para guardarlo.</p>
              </div>
            ) : (
              <ScrollArea className="flex-1 pr-4">
                <div className="space-y-3">
                  {savedNodes.map((node) => (
                    <Card key={node.id} className="p-3 hover:bg-muted/50 transition-colors cursor-pointer group" onClick={() => focusNode(node.id)}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{node.label}</p>
                          <Badge variant="secondary" className="text-[10px] h-4 mt-1">
                            {node.type}
                          </Badge>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleSaveNode(node);
                          }}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>

          {savedNodes.length > 0 && (
            <div className="pt-4 border-t mt-auto">
              <Button variant="outline" className="w-full" onClick={() => setSavedNodes([])}>
                Limpiar Lista
              </Button>
            </div>
          )}
        </SheetContent>
      </Sheet>
      {selectedDataset !== 'all' && (
        <div className="hidden">
           {/* Mock cleanup for dataset specific stuff if needed */}
        </div>
      )}

      <DatasetNameDialog
        isOpen={isDatasetDialogOpen}
        onOpenChange={setIsDatasetDialogOpen}
        onConfirm={handleConfirmProcessGraph}
        defaultTopic={processingTopic}
        workspaceId={availableDatasets.length > 0 ? undefined : undefined} // Workspace ID could be passed if known
      />
    </div>
  );
}
