// frontend/src/components/KnowledgeGraph/KnowledgeGraphViewer.jsx

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
import './KnowledgeGraphViewer.css';

// Componente interno que usa ReactFlow
const KnowledgeGraphViewerInner = ({ graphData, onNodeSelect, selectedWorkspace }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const { fitView } = useReactFlow();

  // Colores por tipo de entidad
  const nodeColors = {
    'PERSON': '#FF6B6B',      // Rojo suave para personas
    'ORG': '#4ECDC4',         // Verde azulado para organizaciones
    'LOC': '#45B7D1',         // Azul para lugares
    'CONCEPT': '#96CEB4',     // Verde suave para conceptos
    'MISC': '#FFEAA7',        // Amarillo para misceláneos
    'default': '#DDA0DD'      // Púrpura por defecto
  };

  // Convertir datos del grafo a formato ReactFlow
  const convertGraphData = useCallback((data) => {
    if (!data || !data.entities) return { nodes: [], edges: [] };

    // Convertir entidades a nodos
    const flowNodes = data.entities.map((entity, index) => {
      const entityType = entity.type || 'default';
      return {
        id: entity.id || `entity_${index}`,
        type: 'default',
        position: { 
          x: Math.random() * 800, 
          y: Math.random() * 600 
        },
        data: {
          label: entity.name || 'Sin nombre',
          type: entityType,
          description: entity.description || '',
          confidence: entity.confidence || 0,
          source: entity.source_document || 'Desconocido'
        },
        style: {
          background: nodeColors[entityType] || nodeColors.default,
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

    // Convertir relaciones a edges (limitamos para performance)
    const maxEdges = 1000; // Limitar edges para mejor performance
    const flowEdges = (data.relationships || [])
      .slice(0, maxEdges)
      .map((rel, index) => ({
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
        labelStyle: { 
          fontSize: '10px', 
          fontWeight: 'bold',
          fill: '#666'
        },
        data: {
          type: rel.relationship_type || 'RELACIONADO',
          description: rel.description || '',
          confidence: rel.confidence || 0
        }
      }))
      .filter(edge => edge.source && edge.target); // Solo edges válidos

    return { nodes: flowNodes, edges: flowEdges };
  }, []);

  // Cargar datos cuando cambie graphData
  useEffect(() => {
    if (graphData) {
      setIsLoading(true);
      const { nodes: newNodes, edges: newEdges } = convertGraphData(graphData);
      setNodes(newNodes);
      setEdges(newEdges);
      setIsLoading(false);
      
      // Auto-fit después de cargar
      setTimeout(() => fitView(), 100);
    }
  }, [graphData, convertGraphData, setNodes, setEdges, fitView]);

  // Filtrar nodos según búsqueda y tipo
  const filteredNodes = useMemo(() => {
    return nodes.filter(node => {
      const matchesSearch = !searchTerm || 
        node.data.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        node.data.description.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesType = filterType === 'all' || node.data.type === filterType;
      
      return matchesSearch && matchesType;
    });
  }, [nodes, searchTerm, filterType]);

  // Filtrar edges para mostrar solo los de nodos visibles
  const filteredEdges = useMemo(() => {
    const visibleNodeIds = new Set(filteredNodes.map(n => n.id));
    return edges.filter(edge => 
      visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
    );
  }, [edges, filteredNodes]);

  // Manejar selección de nodo
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
    if (onNodeSelect) {
      onNodeSelect(node);
    }
  }, [onNodeSelect]);

  // Obtener tipos únicos para el filtro
  const entityTypes = useMemo(() => {
    const types = [...new Set(nodes.map(node => node.data.type))];
    return types.sort();
  }, [nodes]);

  // Estadísticas del grafo
  const stats = useMemo(() => ({
    totalNodes: nodes.length,
    visibleNodes: filteredNodes.length,
    totalEdges: edges.length,
    visibleEdges: filteredEdges.length,
    entityTypes: entityTypes.length
  }), [nodes, filteredNodes, edges, filteredEdges, entityTypes]);

  return (
    <div className="knowledge-graph-viewer">
      {/* Panel de control */}
      <Panel position="top-left" className="graph-controls">
        <div className="controls-header">
          <h3>🧠 Grafo de Conocimiento</h3>
          {selectedWorkspace && (
            <span className="workspace-name">📁 {selectedWorkspace}</span>
          )}
        </div>
        
        {/* Búsqueda */}
        <div className="search-section">
          <input
            type="text"
            placeholder="🔍 Buscar entidades..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        {/* Filtros */}
        <div className="filter-section">
          <label>Tipo de entidad:</label>
          <select 
            value={filterType} 
            onChange={(e) => setFilterType(e.target.value)}
            className="filter-select"
          >
            <option value="all">Todos los tipos</option>
            {entityTypes.map(type => (
              <option key={type} value={type}>
                {type} ({nodes.filter(n => n.data.type === type).length})
              </option>
            ))}
          </select>
        </div>

        {/* Estadísticas */}
        <div className="stats-section">
          <div className="stat-item">
            <span className="stat-label">Entidades:</span>
            <span className="stat-value">{stats.visibleNodes}/{stats.totalNodes}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Relaciones:</span>
            <span className="stat-value">{stats.visibleEdges}/{stats.totalEdges}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Tipos:</span>
            <span className="stat-value">{stats.entityTypes}</span>
          </div>
        </div>

        {/* Botones de acción */}
        <div className="action-buttons">
          <button onClick={() => fitView()} className="action-btn">
            🎯 Centrar vista
          </button>
          <button 
            onClick={() => {
              setSearchTerm('');
              setFilterType('all');
            }} 
            className="action-btn"
          >
            🔄 Limpiar filtros
          </button>
        </div>
      </Panel>

      {/* Panel de detalles del nodo seleccionado */}
      {selectedNode && (
        <Panel position="top-right" className="node-details">
          <div className="details-header">
            <h4>📋 Detalles de la entidad</h4>
            <button 
              onClick={() => setSelectedNode(null)}
              className="close-btn"
            >
              ✕
            </button>
          </div>
          <div className="details-content">
            <div className="detail-item">
              <strong>Nombre:</strong> {selectedNode.data.label}
            </div>
            <div className="detail-item">
              <strong>Tipo:</strong> 
              <span 
                className="entity-type-badge"
                style={{ backgroundColor: nodeColors[selectedNode.data.type] }}
              >
                {selectedNode.data.type}
              </span>
            </div>
            <div className="detail-item">
              <strong>Descripción:</strong> {selectedNode.data.description}
            </div>
            <div className="detail-item">
              <strong>Confianza:</strong> 
              <span className="confidence-score">
                {Math.round((selectedNode.data.confidence || 0) * 100)}%
              </span>
            </div>
            <div className="detail-item">
              <strong>Documento:</strong> {selectedNode.data.source}
            </div>
          </div>
        </Panel>
      )}

      {/* Indicador de carga */}
      {isLoading && (
        <Panel position="center" className="loading-panel">
          <div className="loading-content">
            <div className="spinner"></div>
            <p>Cargando grafo de conocimiento...</p>
          </div>
        </Panel>
      )}

      {/* ReactFlow */}
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
        <MiniMap 
          nodeColor={(node) => nodeColors[node.data?.type] || nodeColors.default}
          nodeStrokeWidth={3}
          zoomable
          pannable
        />
        <Background color="#aaa" gap={16} />
      </ReactFlow>
    </div>
  );
};

// Componente principal con Provider
const KnowledgeGraphViewer = (props) => {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphViewerInner {...props} />
    </ReactFlowProvider>
  );
};

export default KnowledgeGraphViewer;
