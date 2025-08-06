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
import { RefreshCw, Search, SlidersHorizontal, X } from 'lucide-react';
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

  // Colores por tipo de entidad
  const nodeColors = useMemo(() => ({
    'PERSON': '#FF6B6B',
    'ORG': '#4ECDC4',
    'LOC': '#45B7D1',
    'CONCEPT': '#96CEB4',
    'MISC': '#FFEAA7',
    'default': '#DDA0DD'
  }), []);

  const convertGraphData = useCallback((data: any) => {
    if (!data || !data.entities) return { nodes: [], edges: [] };

    const flowNodes: Node[] = data.entities.map((entity: any, index: number) => {
      const entityType = entity.type || 'default';
      return {
        id: entity.id || `entity_${index}`,
        type: 'default',
        position: { x: Math.random() * 800, y: Math.random() * 600 },
        data: {
          label: entity.name || 'Sin nombre',
          type: entityType,
          description: entity.description || '',
          confidence: entity.confidence || 0,
          source: entity.source_document || 'Desconocido'
        },
        style: {
          background: nodeColors[entityType as keyof typeof nodeColors] || nodeColors.default,
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

    const maxEdges = 1000;
    const flowEdges: Edge[] = (data.relationships || [])
      .slice(0, maxEdges)
      .map((rel: any, index: number) => ({
        id: rel.id || `edge_${index}`,
        source: rel.source_entity_id || rel.source_entity,
        target: rel.target_entity_id || rel.target_entity,
        type: 'smoothstep',
        animated: rel.confidence > 0.8,
        style: {
          stroke: rel.confidence > 0.8 ? '#FF6B6B' : '#999',
          strokeWidth: Math.max(1, (rel.confidence || 0.5) * 3)
        },
        label: rel.relationship_type || 'RELACIONADO',
        labelStyle: { fontSize: '10px', fontWeight: 'bold', fill: '#666' },
        data: {
          type: rel.relationship_type || 'RELACIONADO',
          description: rel.description || '',
          confidence: rel.confidence || 0
        }
      }))
      .filter((edge: Edge) => edge.source && edge.target);

    return { nodes: flowNodes, edges: flowEdges };
  }, [nodeColors]);

  useEffect(() => {
    if (graphData) {
      setIsLoading(true);
      const { nodes: newNodes, edges: newEdges } = convertGraphData(graphData);
      setNodes(newNodes);
      setEdges(newEdges);
      setIsLoading(false);
      setTimeout(() => fitView(), 100);
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
              <p><strong>Descripción:</strong> {selectedNode.data.description}</p>
              <p><strong>Confianza:</strong> {Math.round((selectedNode.data.confidence || 0) * 100)}%</p>
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