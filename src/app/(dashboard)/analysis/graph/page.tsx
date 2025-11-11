'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, Info, RefreshCcw, Search, ExternalLink, Brain, Network, GitGraph } from 'lucide-react';
import { toast } from 'sonner';
import dynamic from 'next/dynamic';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api';

// Componente de visualización del grafo cargado dinámicamente
const GraphVisualization = dynamic(() => import('@/components/KnowledgeGraph/GraphVisualization').then(mod => mod.GraphVisualization), {
  ssr: false,
  loading: () => (
    <div className="flex justify-center items-center h-full min-h-[500px]">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  ),
});

// Hook personalizado para el grafo de conocimiento
const useKnowledgeGraph = (maxNodes: number, maxHops: number) => {
  const [graphData, setGraphData] = useState<{ nodes: any[], edges: any[] } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);

  const loadGraphData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`/api/knowledge-graph/data?workspace_id=all&limit=${maxNodes}&max_hops=${maxHops}`);
      if (response.data.success) {
        setGraphData(response.data.data);
      } else {
        setGraphData({ nodes: [], edges: [] });
      }
      setProcessingStatus('completed');
    } catch (err: any) {
      setError(err.message || 'Error cargando el grafo');
    } finally {
      setIsLoading(false);
    }
  }, [maxNodes, maxHops]);

  const processKnowledgeGraph = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setProcessingStatus('processing');
    try {
      await apiClient.post('/api/process-knowledge-graph-optimized');
      await loadGraphData();
    } catch (err: any) {
      setError(err.message || 'Error procesando el grafo');
      setProcessingStatus('error');
    } finally {
      setIsLoading(false);
    }
  }, [loadGraphData]);

  const refreshGraphData = useCallback(() => {
    loadGraphData();
  }, [loadGraphData]);

  const searchGraph = useCallback(async (query: string) => {
    if (!query) return [];
    try {
      const response = await apiClient.post('/api/search-graph', { query });
      return response.data.results || [];
    } catch (err) {
      console.error('Error buscando en el grafo:', err);
      return [];
    }
  }, []);

  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  return {
    graphData,
    isLoading,
    error,
    processingStatus,
    loadGraphData,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    clearError: () => setError(null)
  };
};

export default function KnowledgeGraphPage() {
  const [graphQuery, setGraphQuery] = useState('');
  const [maxNodes, setMaxNodes] = useState(25);
  const [maxHops, setMaxHops] = useState(2);

  const {
    graphData,
    isLoading,
    error,
    processingStatus,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    clearError,
  } = useKnowledgeGraph(maxNodes, maxHops);
  const [searchResults, setSearchResults] = useState<any[]>([]);

  useEffect(() => {
    if (error) {
      toast.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleSearchGraph = useCallback(async () => {
    if (!graphQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const results = await searchGraph(graphQuery);
    setSearchResults(results);
  }, [graphQuery, searchGraph]);

  const handleProcessGraph = useCallback(async () => {
    await processKnowledgeGraph();
  }, [processKnowledgeGraph]);

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
        <div className="h-[70vh] min-h-[500px] w-full">
          <GraphVisualization graphData={graphData} />
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
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center gap-2">
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-6 w-6" />
            Visualización del Grafo
            <Button variant="ghost" size="sm" onClick={refreshGraphData} disabled={isLoading}>
              <RefreshCcw className="h-4 w-4 mr-2" /> Actualizar
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-4">
              <Input
                placeholder="Buscar entidades en el grafo..."
                value={graphQuery}
                onChange={(e) => setGraphQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearchGraph()}
                className="flex-grow"
              />
              <Button onClick={handleSearchGraph}>
                <Search className="h-4 w-4 mr-2" /> Buscar
              </Button>
            </div>
            {searchResults.length > 0 && (
              <div className="bg-muted p-3 rounded-md max-h-40 overflow-y-auto">
                <p className="text-sm font-semibold mb-2">Resultados de la búsqueda:</p>
                {searchResults.map((result) => (
                  <div key={result.id} className="flex items-center justify-between text-sm py-1">
                    <span>{result.label} ({result.type})</span>
                    <Button variant="link" size="sm" className="h-auto p-0">
                      <ExternalLink className="h-3 w-3 mr-1" /> Ver
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <Label htmlFor="max-nodes" className="mb-2 block">Máximo de Nodos: {maxNodes}</Label>
              <Input
                id="max-nodes"
                type="number"
                min={10}
                max={200}
                value={maxNodes}
                onChange={(e) => setMaxNodes(parseInt(e.target.value))}
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
                onChange={(e) => setMaxHops(parseInt(e.target.value))}
                className="w-full"
              />
            </div>
          </div>

          {renderGraphContent()}
        </CardContent>
      </Card>
    </div>
  );
}