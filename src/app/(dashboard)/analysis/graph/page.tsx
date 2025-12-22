'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Info, RefreshCcw, Search, ExternalLink, Brain, Network, GitGraph, Database, ArrowLeft, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { toast } from 'sonner';
import dynamic from 'next/dynamic';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api';
import { GraphFilters } from '@/components/KnowledgeGraph/GraphFilters';
import { NodeDetailsSidebar } from '@/components/KnowledgeGraph/NodeDetailsSidebar';
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
  const [filteredNodeId, setFilteredNodeId] = useState<string | number | null>(null); // Estado para filtro por nodo

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
              // En modo conceptual, mostrar solo nodos conceptuales por defecto
              nodeTypesToFilter = ['CONCEPTUAL_QUOTE', 'IDEA_PROFILE'];
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
  }, [maxNodes, maxHops, selectedDataset, filters, processingMode, originalGraphData, isInitialLoad, filteredNodeId]);

  // Función para aplicar filtros en el cliente sin recargar datos
  const applyClientFilters = useCallback(() => {
    if (!originalGraphData) {
      console.log("🔍 applyClientFilters: No hay originalGraphData");
      return;
    }

    console.log("🔍 applyClientFilters: Iniciando con", originalGraphData.nodes.length, "nodos y", originalGraphData.edges.length, "edges");
    console.log("🔍 filteredNodeId:", filteredNodeId);

    let filteredNodes = [...originalGraphData.nodes];
    let filteredEdges = [...originalGraphData.edges];

    // Primero aplicar filtro por nodo (doble click) si está activo
    if (filteredNodeId !== null) {
      console.log("🔍 Aplicando filtro por nodo:", filteredNodeId);

      const connectedEdges = originalGraphData.edges.filter(edge =>
        edge.from === filteredNodeId || edge.to === filteredNodeId
      );

      console.log("🔍 Edges conectadas encontradas:", connectedEdges.length);

      const connectedNodeIds = new Set<string | number>();
      connectedNodeIds.add(filteredNodeId);
      connectedEdges.forEach(edge => {
        connectedNodeIds.add(edge.from);
        connectedNodeIds.add(edge.to);
      });

      console.log("🔍 Nodos conectados:", connectedNodeIds.size);

      filteredNodes = originalGraphData.nodes.filter(node =>
        connectedNodeIds.has(node.id)
      );
      filteredEdges = connectedEdges;

      console.log("🔍 Después del filtro por nodo:", filteredNodes.length, "nodos y", filteredEdges.length, "edges");
    }

    // Aplicar filtros de tipos de nodo (sobre el resultado anterior)
    if (filters.nodeTypes.length > 0) {
      const nodeIds = new Set(filteredNodes
        .filter(node => filters.nodeTypes.includes(node.type))
        .map(node => node.id)
      );

      // Filtrar nodos
      filteredNodes = filteredNodes.filter(node => nodeIds.has(node.id));

      // Filtrar edges que conecten nodos filtrados
      filteredEdges = filteredEdges.filter(edge =>
        nodeIds.has(edge.from) && nodeIds.has(edge.to)
      );
    }

    // Aplicar filtros de tipos de relación (sobre el resultado anterior)
    if (filters.edgeTypes.length > 0) {
      filteredEdges = filteredEdges.filter(edge =>
        filters.edgeTypes.includes(edge.type || edge.label)
      );

      // Obtener nodos conectados por las edges filtradas
      const connectedNodeIds = new Set<string | number>();
      filteredEdges.forEach(edge => {
        connectedNodeIds.add(edge.from);
        connectedNodeIds.add(edge.to);
      });

      // Filtrar nodos para incluir solo los conectados por edges filtradas
      filteredNodes = filteredNodes.filter(node => connectedNodeIds.has(node.id));
    }

    console.log("🔍 Final: Enviando al display", filteredNodes.length, "nodos y", filteredEdges.length, "edges");
    setDisplayGraphData({ nodes: filteredNodes, edges: filteredEdges });
  }, [originalGraphData, filters, filteredNodeId]);

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
  }, [loadGraphData, processingMode]);

  const refreshGraphData = useCallback(() => {
    loadGraphData();
  }, [loadGraphData]);

  const searchGraph = useCallback(async (query: string) => {
    if (!query) return [];
    try {
      const response = await apiClient.post('/api/search-graph', { query });
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
  }, [loadGraphData, loadAvailableDatasets, loadMetadata]);

  // Aplicar filtros en cliente cuando cambien los filtros o el filtro por nodo
  useEffect(() => {
    if (!isInitialLoad && originalGraphData) {
      applyClientFilters();
    }
  }, [filters, filteredNodeId, applyClientFilters, isInitialLoad, originalGraphData]);

  // Recargar datos cuando cambia el modo de procesamiento o parámetros que requieren nueva consulta
  useEffect(() => {
    if (!isInitialLoad) {
      loadGraphData(true); // Recargar desde servidor
    }
  }, [processingMode, maxNodes, maxHops, selectedDataset, loadGraphData, isInitialLoad]);


  const resetGraphFilter = useCallback(() => {
    setFilteredNodeId(null); // Reset filter to show all nodes
    // También se puede llamar a applyClientFilters aquí si se quiere actualizar inmediatamente
    // applyClientFilters();
  }, []);

  const updateFilteredNodeId = useCallback((nodeId: string | number | null) => {
    setFilteredNodeId(nodeId);
  }, []);

  return {
    graphData: displayGraphData, // Return displayGraphData
    metadata,
    isLoading,
    error,
    processingStatus,
    availableDatasets,
    loadGraphData,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    clearError: () => setError(null),
    resetGraphFilter, // Expose new function
    updateFilteredNodeId, // Expose setter for filteredNodeId
  };
};

export default function KnowledgeGraphPage() {
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
    datasetName: 'all'
  });


  // Estado para el panel de detalles del nodo
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [isNodeDetailsOpen, setIsNodeDetailsOpen] = useState(false);

  // Estado para el panel de filtros desplegable
  const [isFiltersExpanded, setIsFiltersExpanded] = useState(true);

  // Estado para el progreso de procesamiento
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState('');

  const {
    graphData,
    metadata,
    isLoading,
    error,
    processingStatus,
    availableDatasets,
    processKnowledgeGraph: originalProcessKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    clearError,
    resetGraphFilter, // Get new function from hook
    updateFilteredNodeId, // Get setter function from hook
  } = useKnowledgeGraph(maxNodes, maxHops, selectedDataset, filters, processingMode);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const filterGraphByNode = useCallback((nodeId: string | number) => {
    console.log("🔍 filterGraphByNode llamado con nodeId:", nodeId);
    // Actualizar el estado del filtro por nodo usando la función del hook
    updateFilteredNodeId(nodeId);
    console.log("🔍 Estado filteredNodeId actualizado a:", nodeId);
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
    await originalProcessKnowledgeGraph(setProcessingProgress, setProcessingMessage);
  }, [originalProcessKnowledgeGraph]);

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
      console.log("🔍 Sidebar de detalles abierto para nodo:", node.id, "Estado selectedNode:", node, "Estado isNodeDetailsOpen:", true);
    }
  }, [selectedNode, isNodeDetailsOpen]);

  const handleCloseNodeDetails = useCallback(() => {
    setIsNodeDetailsOpen(false);
    setSelectedNode(null);
  }, []);

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
        <div className="flex-1 w-full relative">
          <GraphVisualization
            ref={graphVisualizationRef} // Asignar la ref
            graphData={graphData}
            metadata={metadata}
            onNodeClick={handleNodeClick}
            onNodeDoubleClick={filterGraphByNode} // Pass the new handler
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
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8 flex flex-col h-full">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={() => router.push('/analysis')} className="h-8 w-8 text-muted-foreground">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent spacing-tight">
          Grafos de Conocimiento
        </h1>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
                <Info className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Visualiza las relaciones entre tus datos en un grafo interactivo.</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <Card className="flex flex-col flex-1">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-6 w-6" />
            Visualización del Grafo
            <div className="flex items-center gap-2 ml-auto"> {/* Added div for grouping buttons */}
              <Button variant="ghost" size="sm" onClick={resetGraphFilter} disabled={isLoading}>
                <X className="h-4 w-4 mr-2" /> Limpiar Filtro
              </Button>
              <Button variant="ghost" size="sm" onClick={refreshGraphData} disabled={isLoading}>
                <RefreshCcw className="h-4 w-4 mr-2" /> Actualizar
              </Button>
              <Button variant="ghost" size="sm" onClick={() => {
                updateFilteredNodeId(null); // Limpiar filtro de nodo
                setSearchResults([]); // Limpiar resultados de búsqueda
                setGraphQuery(''); // Limpiar query de búsqueda
                setSearchError(null); // Limpiar error de búsqueda
                graphVisualizationRef.current?.fitView(); // Ajustar la vista del grafo
              }}>
                <GitGraph className="h-4 w-4 mr-2" /> Vista Completa
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col flex-1">
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
            <div>
              <Label htmlFor="dataset-select" className="mb-2 block flex items-center gap-2">
                <Database className="h-4 w-4" />
                Dataset
              </Label>
              <Select value={selectedDataset} onValueChange={setSelectedDataset}>
                <SelectTrigger id="dataset-select" className="w-full">
                  <SelectValue placeholder="Seleccionar dataset" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">
                    Todos los datasets ({availableDatasets.reduce((sum, d) => sum + d.node_count, 0)} nodos)
                  </SelectItem>
                  {availableDatasets.map((dataset) => (
                    <SelectItem key={dataset.name} value={dataset.name}>
                      {dataset.name} ({dataset.node_count} nodos)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
                max={2000}
                value={maxNodes}
                onChange={(e) => {
                  const value = e.target.value;
                  // Permitir campo vacío mientras se edita
                  if (value === '') {
                    setMaxNodes(25); // Valor temporal, se validará en onBlur
                    return;
                  }
                  const numValue = parseInt(value);
                  if (!isNaN(numValue)) {
                    // Permitir valores fuera de rango mientras se edita, validar en onBlur
                    setMaxNodes(numValue);
                  }
                }}
                onBlur={(e) => {
                  const value = parseInt(e.target.value);
                  if (isNaN(value)) {
                    setMaxNodes(100); // Valor por defecto si es inválido
                  } else {
                    setMaxNodes(Math.max(10, Math.min(2000, value)));
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

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 flex flex-col h-full">
            <div className={`transition-all duration-300 ${isFiltersExpanded ? 'lg:col-span-4' : 'lg:col-span-1'}`}>
              <div className="sticky top-4">
                <div className="flex items-center justify-between mb-4">
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
                <div className={`${isFiltersExpanded ? 'block' : 'hidden'}`}>
                  <GraphFilters
                    metadata={metadata}
                    filters={filters}
                    onFiltersChange={setFilters}
                    totalNodes={metadata?.nodeTypes.reduce((acc, t) => acc + t.count, 0) || 0}
                    totalEdges={metadata?.edgeTypes.reduce((acc, t) => acc + t.count, 0) || 0}
                    filteredNodes={graphData?.nodes.length || 0}
                    filteredEdges={graphData?.edges.length || 0}
                    getNodeColor={getNodeColor}
                  />
                </div>
              </div>
            </div>
            <div className={`${isFiltersExpanded ? 'lg:col-span-8' : 'lg:col-span-11'} border rounded-lg overflow-hidden bg-background flex flex-col flex-1`}>
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
    </div>
  );
}