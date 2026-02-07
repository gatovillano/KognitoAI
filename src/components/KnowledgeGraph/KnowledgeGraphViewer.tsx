'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  Panel,
  useReactFlow,
  ReactFlowProvider
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Search, SlidersHorizontal, X, Volume2, Loader2, Square } from 'lucide-react';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import './KnowledgeGraphViewer.css';

interface KnowledgeGraphViewerInnerProps {
  graphData: any;
  onNodeSelect: (node: any) => void;
  selectedWorkspace: string;
}

// Componente interno que usa ReactFlow
const KnowledgeGraphViewerInner = ({ graphData, onNodeSelect, selectedWorkspace }: KnowledgeGraphViewerInnerProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const { fitView } = useReactFlow();
  const { play, stop, isLoading: isTtsLoading, isPlaying: isTtsPlaying, activeText } = useTextToSpeech();

  // Colores por tipo de entidad
  const nodeColors = useMemo(() => ({
    'CONCEPTUAL_QUOTE': '#FF6B6B', // Color para nodos de citas conceptuales
    'IDEA_PROFILE': '#4ECDC4',     // Color para nodos de perfiles de ideas
    'default': '#DDA0DD'           // Color por defecto para otros tipos de nodos
  }), []);

  const convertGraphData = useCallback((data: any) => {
    console.log("🔵 convertGraphData: Datos de entrada:", data);
    // Asegurarse de que data.nodes y data.edges existan
    if (!data || !data.nodes || !data.edges) {
      console.warn("🟡 convertGraphData: Datos de grafo incompletos o ausentes.");
      return { nodes: [], edges: [] };
    }

    // Convertir nodos del backend a formato ReactFlow
    const flowNodes: Node[] = data.nodes.map((node: any, index: number) => {
      const nodeType = node.type || 'default'; // Usar 'type' del nodo
      return {
        id: node.id || `node_${index}`,
        type: 'default', // Tipo de nodo de ReactFlow (puede ser 'input', 'output', 'default')
        position: { x: Math.random() * 800, y: Math.random() * 600 },
        data: {
          label: node.label || 'Sin nombre',
          type: node.type || 'default',
          description: node.description || node.title || node.label || '',
          confidence: node.confidence || node.properties?.confidence || 0,
          source: node.source || node.properties?.source || 'Desconocido',
        },
        style: {
          background: nodeColors[nodeType as keyof typeof nodeColors] || nodeColors.default,
          color: '#333',
          border: '2px solid #222',
          borderRadius: '8px',
          fontSize: '12px',
          fontWeight: 'bold',
          padding: '8px',
          minWidth: '120px',
          textAlign: 'center'
        }
      };
    });
    console.log("🟢 convertGraphData: Nodos convertidos:", flowNodes.length, flowNodes);

    const maxEdges = 1000; // Limitar el número de aristas para evitar sobrecarga
    // Convertir aristas del backend a formato ReactFlow
    const flowEdges: Edge[] = (data.edges || [])
      .slice(0, maxEdges)
      .map((edge: any, index: number) => ({
        id: edge.id || `edge_${index}`,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep', // Tipo de arista de ReactFlow
        animated: edge.properties?.confidence > 0.8,
        style: {
          stroke: edge.properties?.confidence > 0.8 ? '#FF6B6B' : '#999',
          strokeWidth: Math.max(1, (edge.properties?.confidence || 0.5) * 3),
        },
        label: edge.label || 'RELACIONADO',
        labelStyle: { fontSize: '10px', fontWeight: 'bold', fill: '#666' },
        data: {
          type: edge.type || 'RELACIONADO',
          description: edge.title || '',
        }
      }))
      .filter((edge: Edge) => edge.source && edge.target); // Filtrar aristas inválidas
    console.log("🟢 convertGraphData: Aristas convertidas:", flowEdges.length, flowEdges);

    return { nodes: flowNodes, edges: flowEdges };
  }, [nodeColors]);

  useEffect(() => {
    if (graphData) {
      console.log("🔵 KnowledgeGraphViewer: graphData recibido en useEffect:", graphData);
      setIsLoading(true);
      const { nodes: newNodes, edges: newEdges } = convertGraphData(graphData);
      console.log("🟢 KnowledgeGraphViewer: Nodos ReactFlow listos para setear:", newNodes.length);
      console.log("🟢 KnowledgeGraphViewer: Aristas ReactFlow listas para setear:", newEdges.length);
      setNodes(newNodes);
      setEdges(newEdges);
      setIsLoading(false);
      setTimeout(() => {
        fitView();
        console.log("🟢 KnowledgeGraphViewer: fitView ejecutado.");
      }, 100);
    } else {
      console.log("🟡 KnowledgeGraphViewer: graphData es nulo o indefinido en useEffect.");
      setNodes([]);
      setEdges([]);
    }
  }, [graphData, convertGraphData, setNodes, setEdges, fitView]);

  const filteredNodes = useMemo(() => {
    return nodes.filter((node: Node) => {
      const matchesSearch = !searchTerm ||
        node.data.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        node.data.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === 'all' || node.data.type === filterType;
      return matchesSearch && matchesType;
    });
  }, [nodes, searchTerm, filterType]);

  const filteredEdges = useMemo(() => {
    const visibleNodeIds = new Set(filteredNodes.map(n => n.id));
    return edges.filter((edge: Edge) =>
      visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
    );
  }, [edges, filteredNodes]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    console.log("🎯 Nodo seleccionado:", node);
    setSelectedNode(node);
    if (onNodeSelect) {
      onNodeSelect(node);
    }
  }, [onNodeSelect]);

  const entityTypes = useMemo(() => {
    const types = [...new Set(nodes.map(node => node.data.type))];
    return types.sort();
  }, [nodes]);

  const stats = useMemo(() => ({
    totalNodes: nodes.length,
    visibleNodes: filteredNodes.length,
    totalEdges: edges.length,
    visibleEdges: filteredEdges.length,
    entityTypes: entityTypes.length
  }), [nodes, filteredNodes, edges, filteredEdges, entityTypes]);

  return (
    <div className="knowledge-graph-viewer">
      <Panel position="top-left">
        <Card className="graph-controls">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">🧠 Grafo de Conocimiento</CardTitle>
            {selectedWorkspace && <Badge>{selectedWorkspace}</Badge>}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar entidades..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Tipo de entidad:</label>
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos los tipos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los tipos</SelectItem>
                  {entityTypes.map(type => (
                    <SelectItem key={type} value={type}>
                      {type} ({nodes.filter(n => n.data.type === type).length})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2 rounded-lg bg-muted p-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Entidades:</span>
                <span className="font-medium">{stats.visibleNodes}/{stats.totalNodes}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Relaciones:</span>
                <span className="font-medium">{stats.visibleEdges}/{stats.totalEdges}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Tipos:</span>
                <span className="font-medium">{stats.entityTypes}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => fitView()} className="flex-1">
                🎯 Centrar vista
              </Button>
              <Button
                onClick={() => { setSearchTerm(''); setFilterType('all'); }}
                variant="outline"
                className="flex-1"
              >
                <RefreshCw className="mr-2 h-4 w-4" /> Limpiar
              </Button>
            </div>
          </CardContent>
        </Card>
      </Panel>

      {selectedNode && (
        <Panel position="top-right">
          <Card className="node-details">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Detalles de la entidad
                <Button variant="ghost" size="icon" onClick={() => setSelectedNode(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p><strong>Nombre:</strong> {selectedNode.data.label}</p>
              <p><strong>Tipo:</strong> <Badge style={{ backgroundColor: nodeColors[selectedNode.data.type as keyof typeof nodeColors] }}>{selectedNode.data.type}</Badge></p>
              <div className="flex flex-col gap-2 p-2 rounded-md bg-muted/50 border border-border">
                <div className="flex items-center justify-between">
                  <strong className="text-xs uppercase tracking-wider text-muted-foreground">Descripción</strong>
                  {selectedNode.data.description && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-full hover:scale-110 transition-all duration-200"
                      onClick={() => {
                        if (isTtsPlaying && activeText === selectedNode.data.description) {
                          stop();
                        } else {
                          play(selectedNode.data.description);
                        }
                      }}
                      title={isTtsPlaying && activeText === selectedNode.data.description ? "Detener" : "Escuchar descripción"}
                    >
                      {isTtsLoading && activeText === selectedNode.data.description ? (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      ) : (isTtsPlaying && activeText === selectedNode.data.description) ? (
                        <Square className="h-4 w-4 text-primary fill-primary" />
                      ) : (
                        <Volume2 className="h-4 w-4 text-primary" />
                      )}
                    </Button>
                  )}
                </div>
                <p className="text-sm italic text-foreground/90 leading-relaxed">{selectedNode.data.description || 'Sin descripción disponible'}</p>
              </div>
              <p className="mt-2"><strong>Confianza:</strong> {Math.round((selectedNode.data.confidence || 0) * 100)}%</p>
              <p><strong>Documento:</strong> {selectedNode.data.source}</p>
            </CardContent>
          </Card>
        </Panel>
      )}

      {isLoading && (
        <Panel position="top-center">
          <Card className="loading-panel">
            <CardContent className="flex flex-col items-center gap-4">
              <div className="spinner"></div>
              <p>Cargando grafo de conocimiento...</p>
            </CardContent>
          </Card>
        </Panel>
      )}

      <ReactFlow
        nodes={filteredNodes}
        edges={filteredEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        attributionPosition="bottom-left"
      >
        <Controls />
        <MiniMap nodeColor={(node: Node) => nodeColors[node.data?.type as keyof typeof nodeColors] || nodeColors.default} nodeStrokeWidth={3} zoomable pannable />
        <Background color="#aaa" gap={16} />
      </ReactFlow>
    </div>
  );
};

const KnowledgeGraphViewer = (props: KnowledgeGraphViewerInnerProps) => {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphViewerInner {...props} />
    </ReactFlowProvider>
  );
};

export default KnowledgeGraphViewer;