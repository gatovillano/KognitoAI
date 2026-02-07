'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, Info, RefreshCcw, Search, ExternalLink, Brain, Network, GitGraph } from 'lucide-react';
import { toast } from 'sonner';
import { useKnowledgeGraph } from '@/hooks/useKnowledgeGraph';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
// import { Slider } from '@/components/ui/slider'; // Temporalmente comentado
import { Label } from '@/components/ui/label';

// Componente de visualización del grafo cargado dinámicamente
const GraphVisualization = dynamic(() => import('@/components/KnowledgeGraph/GraphVisualization').then(mod => mod.GraphVisualization), {
  ssr: false,
  loading: () => (
    <div className="flex justify-center items-center h-full min-h-[500px]">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  ),
});

export default function KnowledgeGraphPage() {
  const params = useParams();
  const workspaceId = params?.workspaceId as string;

  const {
    graphData,
    isLoading,
    error,
    processingStatus,
    loadGraphData,
    processKnowledgeGraph,
    refreshGraphData,
    searchGraph,
    getEntityConnections,
    clearError,
    stats
  } = useKnowledgeGraph(workspaceId);

  const [graphQuery, setGraphQuery] = useState('');
  const [maxNodes, setMaxNodes] = useState(50);
  const [maxHops, setMaxHops] = useState(2);
  const [searchResults, setSearchResults] = useState<any[]>([]);

  // Filtrar los datos del grafo basándose en maxNodes y maxHops
  const filteredGraphData = useMemo(() => {
    if (!graphData || !graphData.nodes || !graphData.edges) {
      return null;
    }

    // Si no hay límites, devolver todos los datos
    if (maxNodes >= graphData.nodes.length) {
      return graphData;
    }

    // Calcular el grado (número de conexiones) de cada nodo
    const nodeDegrees = new Map<string, number>();
    graphData.nodes.forEach(node => nodeDegrees.set(node.id, 0));

    graphData.edges.forEach(edge => {
      nodeDegrees.set(edge.source, (nodeDegrees.get(edge.source) || 0) + 1);
      nodeDegrees.set(edge.target, (nodeDegrees.get(edge.target) || 0) + 1);
    });

    // Ordenar nodos por grado (más conectados primero) y tomar los primeros maxNodes
    const sortedNodes = [...graphData.nodes].sort((a, b) =>
      (nodeDegrees.get(b.id) || 0) - (nodeDegrees.get(a.id) || 0)
    );

    // Aplicar BFS desde los nodos más conectados para respetar maxHops
    const selectedNodeIds = new Set<string>();
    const queue: Array<{ id: string; depth: number }> = [];

    // Comenzar con los nodos más conectados
    const seedNodes = sortedNodes.slice(0, Math.min(10, maxNodes));
    seedNodes.forEach(node => {
      selectedNodeIds.add(node.id);
      queue.push({ id: node.id, depth: 0 });
    });

    // BFS para expandir hasta maxHops
    while (queue.length > 0 && selectedNodeIds.size < maxNodes) {
      const current = queue.shift()!;

      if (current.depth >= maxHops) continue;

      // Encontrar vecinos
      const neighbors = graphData.edges
        .filter(edge => edge.source === current.id || edge.target === current.id)
        .map(edge => edge.source === current.id ? edge.target : edge.source)
        .filter(neighborId => !selectedNodeIds.has(neighborId));

      // Agregar vecinos hasta alcanzar maxNodes
      for (const neighborId of neighbors) {
        if (selectedNodeIds.size >= maxNodes) break;
        selectedNodeIds.add(neighborId);
        queue.push({ id: neighborId, depth: current.depth + 1 });
      }
    }

    // Filtrar nodos y aristas
    const filteredNodes = graphData.nodes.filter(node => selectedNodeIds.has(node.id));
    const filteredEdges = graphData.edges.filter(edge =>
      selectedNodeIds.has(edge.source) && selectedNodeIds.has(edge.target)
    );

    return {
      nodes: filteredNodes,
      edges: filteredEdges,
      metadata: graphData.metadata
    };
  }, [graphData, maxNodes, maxHops]);

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

    if (filteredGraphData && filteredGraphData.nodes.length > 0) {
      return (
        <div className="h-full w-full">
          <GraphVisualization graphData={filteredGraphData} />
        </div>
      );
    }

    if (!isLoading && (!graphData || graphData.nodes.length === 0)) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <GitGraph className="h-16 w-16 text-muted-foreground/50 mb-6" />
          <h3 className="text-xl font-semibold mb-4">Grafo de Conocimiento Vacío</h3>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Aún no se ha generado un grafo de conocimiento para este espacio de trabajo.
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
    <div className="p-4 sm:p-8 space-y-8">
      <div className="flex items-center gap-2">
        <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent spacing-tight">
          Grafo de Conocimiento
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

      <Card className="flex flex-col flex-grow">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-6 w-6" />
            Visualización del Grafo
            <Button variant="ghost" size="sm" onClick={refreshGraphData} disabled={isLoading}>
              <RefreshCcw className="h-4 w-4 mr-2" /> Actualizar
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col flex-grow">
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
              <div className="bg-muted p-3 rounded-md max-h-[calc(100vh-200px)] overflow-y-auto">
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
                onChange={(e) => {
                  const value = parseInt(e.target.value);
                  if (!isNaN(value) && value >= 10 && value <= 200) {
                    setMaxNodes(value);
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
                  const value = parseInt(e.target.value);
                  if (!isNaN(value) && value >= 1 && value <= 5) {
                    setMaxHops(value);
                  }
                }}
                className="w-full"
              />
            </div>
          </div>

          {graphData && filteredGraphData && (
            <div className="bg-muted/50 p-3 rounded-lg mb-4 text-sm">
              <p className="font-medium">
                📊 Mostrando {filteredGraphData.nodes.length} de {graphData.nodes.length} nodos
                {' '}y {filteredGraphData.edges.length} de {graphData.edges.length} relaciones
              </p>
            </div>
          )}

          <div className="flex-grow w-full">
            {renderGraphContent()}
          </div>
        </CardContent>
      </Card>

      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>Estadísticas del Grafo</CardTitle>
          </CardHeader>
          <CardContent>
            <p><strong>Total de Entidades:</strong> {stats.totalEntities}</p>
            <p><strong>Total de Relaciones:</strong> {stats.totalRelationships}</p>
            <p><strong>Tipos de Entidades:</strong> {stats.entityTypes.join(', ')}</p>
            <p><strong>Método de Procesamiento:</strong> {stats.processingMethod}</p>
            <p><strong>Último Procesamiento:</strong> {stats.lastProcessed ? new Date(stats.lastProcessed).toLocaleString() : 'N/A'}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}