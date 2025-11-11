'use client';

import { useEffect, useState, useCallback } from 'react';
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

    if (graphData && graphData.nodes.length > 0) {
      return (
        <div className="h-[70vh] min-h-[500px] w-full">
          <GraphVisualization graphData={graphData} />
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
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8">
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