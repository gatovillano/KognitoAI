// src/components/KnowledgeGraph/GraphVisualization.tsx
'use client';

import React, { useRef, useEffect, useImperativeHandle, forwardRef, useCallback } from 'react';
import { Network, DataSet } from 'vis-network/standalone';
import { getNodeColor } from '@/utils/graphUtils';
import { GraphLegend } from './GraphLegend';
import { GraphMetadata } from '@/types/graph';

export interface GraphVisualizationRef {
  fitView: () => void;
  focusNode: (nodeId: string | number) => void;
}

const normalizeGraphId = (value: string | number | null | undefined) => {
  if (value === null || value === undefined) {
    return null;
  }

  return String(value);
};

// Interfaces locales para mayor claridad y control
interface VisGraphNode {
  id: string | number;
  label: string;
  title?: string;
  hidden?: boolean;
  color?: string | {
    background?: string;
    border?: string;
    highlight?: string | { background?: string; border?: string };
    hover?: string | { background?: string; border?: string };
  };
  size?: number;
  type?: string;
  properties?: any; // Mantenemos properties por si acaso
  borderWidth?: number;
  shadow?: any;
  font?: any;
  x?: number;
  y?: number;
}

interface VisGraphEdge {
  id?: string | number;
  from: string | number;
  to: string | number;
  hidden?: boolean;
  arrows?: string;
  label?: string;
  title?: string;
  properties?: any;
  type?: string;
}

interface GraphVisualizationProps {
  graphData: {
    nodes: VisGraphNode[];
    edges: VisGraphEdge[];
    metadata?: any;
  } | null;
  metadata?: GraphMetadata | null;
  isLoading?: boolean;
  error?: string | null;
  onNodeClick?: (node: VisGraphNode) => void;
  onNodeDoubleClick?: (nodeId: string | number) => void; // Nuevo prop para doble clic
  onEdgeClick?: (edge: VisGraphEdge) => void; // Handler para clic en aristas
  savedNodeIds?: Set<string | number>; // IDs de nodos guardados
  focusedNodeId?: string | number | null;
}

export const GraphVisualization = forwardRef<GraphVisualizationRef, GraphVisualizationProps>(({
  graphData,
  metadata,
  isLoading = false,
  error = null,
  onNodeClick,
  onNodeDoubleClick, // Desestructurar el nuevo prop
  onEdgeClick, // Desestructurar el prop para aristas
  savedNodeIds = new Set(),
  focusedNodeId = null,
}, ref) => {
  const nodes = React.useMemo(() => graphData?.nodes || [], [graphData?.nodes]);
  const edges = React.useMemo(() => graphData?.edges || [], [graphData?.edges]);
  const visJsContainer = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const nodesDatasetRef = useRef<DataSet<VisGraphNode> | null>(null);
  const edgesDatasetRef = useRef<DataSet<VisGraphEdge> | null>(null);
  const focusedNodeIdRef = useRef<string | number | null>(focusedNodeId);
  const isInitialLoadRef = useRef<boolean>(true);
  const lastFocusedNodeIdRef = useRef<string | number | null>(null);

  useEffect(() => {
    focusedNodeIdRef.current = focusedNodeId;
  }, [focusedNodeId]);

  const resolveDatasetNodeId = useCallback((nodeId: string | number) => {
    if (!nodesDatasetRef.current) {
      return null;
    }

    const candidateIds = [nodeId];
    const normalizedNodeId = normalizeGraphId(nodeId);

    if (normalizedNodeId !== null && normalizedNodeId !== nodeId) {
      candidateIds.push(normalizedNodeId);
    }

    const numericNodeId = Number(nodeId);
    if (!Number.isNaN(numericNodeId) && numericNodeId !== nodeId) {
      candidateIds.push(numericNodeId);
    }

    return candidateIds.find(candidateId => nodesDatasetRef.current?.get(candidateId)) ?? null;
  }, []);

  // Función para truncar texto largo
  const truncateText = (text: string, maxLength: number = 30) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Función para convertir nodos del backend al formato vis.js
  const convertNodesToVis = useCallback((backendNodes: any[]) => {
    return backendNodes.map(node => {
      const isSaved = savedNodeIds.has(node.id);
      // Priorizar name o title de properties, luego node.label, y finalmente node.id
      const fullLabel = node.properties?.name || node.properties?.title || node.label || String(node.id);
      const truncatedLabel = truncateText(fullLabel);
      const description = node.properties?.description || node.properties?.text || fullLabel;

      // Asegurarse de que el tipo sea 'Desconocido' si no está definido o es nulo
      const nodeType = node.type || 'Desconocido';
      const nodeColor = getNodeColor(nodeType);

      let x: number | undefined;
      let y: number | undefined;
      // Recuperar posiciones guardadas si existen
      try {
        const savedPositionsStr = localStorage.getItem('kognito_graph_positions');
        if (savedPositionsStr) {
          const savedPositions = JSON.parse(savedPositionsStr);
          if (savedPositions[node.id]) {
            x = savedPositions[node.id].x;
            y = savedPositions[node.id].y;
          }
        }
      } catch (e) {
        console.warn("No se pudieron cargar las posiciones del grafo desde localStorage", e);
      }

      const nodeObj: VisGraphNode = {
        id: node.id,
        label: truncatedLabel,
        title: description.length > 100 ? `${truncateText(description, 100)}\n\nClic para ver detalles completos` : description,
        properties: node.properties,
        type: nodeType,
        color: isSaved ? {
          background: '#FACC15', // Gold/Yellow
          border: '#EAB308',
          highlight: { background: '#FDE047', border: '#CA8A04' }
        } : nodeColor,
        borderWidth: isSaved ? 4 : 2,
        size: isSaved ? 20 : 15,
        shadow: isSaved ? { enabled: true, color: 'rgba(234, 179, 8, 0.5)', size: 10 } : false,
        font: {
          color: '#000000',
          size: truncatedLabel.length > 20 ? 12 : 14,
          bold: isSaved
        }
      };

      if (x !== undefined && y !== undefined) {
        nodeObj.x = x;
        nodeObj.y = y;
      }

      return nodeObj;
    });
  }, [savedNodeIds]);

  // Función para convertir edges del backend al formato vis.js
  const convertEdgesToVis = (backendEdges: any[]) => {
    return backendEdges.map(edge => {
      const e = edge as any;

      // Si no hay propiedades, crear un objeto properties con todos los campos disponibles
      let edgeProperties = e.properties || {};

      // Si properties está vacío pero hay otros campos, incluirlos
      if (Object.keys(edgeProperties).length === 0) {
        edgeProperties = {
          id: e.id,
          type: e.type,
          label: e.label,
          from: e.from || e.source,
          to: e.to || e.target,
          description: e.description,
          confidence: e.confidence,
          weight: e.weight,
          source_document: e.source_document,
          extraction_method: e.extraction_method,
          context: e.context,
          position: e.position,
          // Incluir cualquier otro campo que no esté ya incluido
          ...Object.fromEntries(Object.entries(e).filter(([key]) => !['id', 'type', 'label', 'from', 'to', 'source', 'target'].includes(key)))
        };
      }

      return {
        id: e.id,
        from: e.from || e.source,
        to: e.to || e.target,
        label: '', // Ocultar etiqueta por defecto
        title: e.properties?.description || e.description || e.label, // Mostrar al pasar el mouse
        properties: edgeProperties,
        type: e.type,
        arrows: 'to',
        color: { color: '#475569', highlight: '#1e293b', hover: '#1e293b' },
        dashes: e.type === 'IMPLIES' || e.type === 'RELATED_TO',
        width: 1.5
      };
    });
  };

  useEffect(() => {
    if (!visJsContainer.current || isLoading || error) return;

    // Si no hay red creada, crearla
    if (!networkRef.current) {
      // Crear DataSets
      nodesDatasetRef.current = new DataSet<VisGraphNode>();
      edgesDatasetRef.current = new DataSet<VisGraphEdge>();

      const data = {
        nodes: nodesDatasetRef.current,
        edges: edgesDatasetRef.current
      };

      const options = {
        nodes: {
          shape: 'dot',
          size: 15,
          font: { size: 14, color: '#000000' },
          borderWidth: 2,
        },
        edges: {
          width: 2,
          color: { color: '#475569', highlight: '#1e293b', hover: '#1e293b' },
          arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          font: { size: 10, color: '#000000', align: 'middle' }
        },
        physics: {
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -100,
            centralGravity: 0.01,
            springConstant: 0.08,
            springLength: 100,
            damping: 0.4,
            avoidOverlap: 0.5
          },
          stabilization: {
            enabled: true,
            iterations: 150, // Pequeño número de iteraciones para que calcule la forma rápidamente antes de pintar
            updateInterval: 150, // Previene emitir eventos intermedios, calculando en bloque (muy rápido)
            fit: true
          }
        },
        layout: {
          randomSeed: 2,
          improvedLayout: false // Desactivación para acelerar el inicio en grafos gigantes
        },
        interaction: { navigationButtons: true, keyboard: true, hover: true }
      };

      networkRef.current = new Network(visJsContainer.current, data, options);

      // Eventos de clic
      networkRef.current.on("click", (properties) => {
        if (properties.nodes.length > 0 && onNodeClick && nodesDatasetRef.current) {
          // Clic en Nodo
          const nodeId = properties.nodes[0];
          const rawClickedNode = nodesDatasetRef.current.get(nodeId);
          let clickedNode: VisGraphNode | undefined;

          if (Array.isArray(rawClickedNode)) {
            clickedNode = rawClickedNode[0] as VisGraphNode;
          } else {
            clickedNode = rawClickedNode as VisGraphNode;
          }

          if (clickedNode) {
            console.log("🔍 Node clicked:", clickedNode);
            onNodeClick(clickedNode);
          }
        } else if (properties.edges.length > 0 && properties.nodes.length === 0 && onEdgeClick && edgesDatasetRef.current) {
          // Clic en Arista
          const edgeId = properties.edges[0];
          const rawClickedEdge = edgesDatasetRef.current.get(edgeId);
          let clickedEdge: VisGraphEdge | undefined;

          if (Array.isArray(rawClickedEdge)) {
            clickedEdge = rawClickedEdge[0] as VisGraphEdge;
          } else {
            clickedEdge = rawClickedEdge as VisGraphEdge;
          }

          if (clickedEdge) {
            onEdgeClick(clickedEdge);
          }
        }
      });

      // Evento de doble clic en nodo
      networkRef.current.on("doubleClick", (properties) => {
        if (properties.nodes.length > 0 && onNodeDoubleClick) {
          const nodeId = properties.nodes[0];
          onNodeDoubleClick(nodeId);
        }
      });

      // Guardar posiciones al terminar de arrastrar un nodo
      networkRef.current.on("dragEnd", (params) => {
        if (params.nodes && params.nodes.length > 0 && networkRef.current) {
          const positions = networkRef.current.getPositions(params.nodes);
          try {
            const savedStr = localStorage.getItem('kognito_graph_positions');
            const saved = savedStr ? JSON.parse(savedStr) : {};
            
            Object.keys(positions).forEach(id => {
              saved[id] = positions[id];
            });
            
            localStorage.setItem('kognito_graph_positions', JSON.stringify(saved));
          } catch (e) {
            console.warn("No se pudo guardar la posición en localStorage", e);
          }
        }
      });

      // Detener física después del cálculo estático bloqueante
      networkRef.current.on("stabilizationIterationsDone", () => {
        networkRef.current?.setOptions({ physics: { enabled: false } });
        if (isInitialLoadRef.current) {
          isInitialLoadRef.current = false;
          if (focusedNodeIdRef.current === null) {
            networkRef.current?.fit();
          }
        }
      });
    }

    // Actualizar DataSets con los nuevos datos (sin recrear la red)
    if (nodesDatasetRef.current && edgesDatasetRef.current) {
      const visNodes = convertNodesToVis(nodes);
      const visEdges = convertEdgesToVis(edges);

      // Obtener IDs actuales
      const currentNodeIds = new Set(nodesDatasetRef.current.getIds());
      const currentEdgeIds = new Set(edgesDatasetRef.current.getIds());

      const newNodeIds = new Set(visNodes.map(n => n.id));
      const newEdgeIds = new Set(visEdges.map(e => e.id));

      // Nodos a remover
      const nodesToRemove = [...currentNodeIds].filter(id => !newNodeIds.has(id));
      // Edges a remover
      const edgesToRemove = [...currentEdgeIds].filter(id => !newEdgeIds.has(id));

      // Nodos a agregar
      const nodesToAdd = visNodes.filter(node => !currentNodeIds.has(node.id));
      // Edges a agregar
      const edgesToAdd = visEdges.filter(edge => !currentEdgeIds.has(edge.id));

      // Nodos a actualizar (solo actualizar si realmente cambió alguna propiedad relevante)
      const nodesToUpdate = visNodes.filter(node => currentNodeIds.has(node.id));
      // Edges a actualizar
      const edgesToUpdate = visEdges.filter(edge => currentEdgeIds.has(edge.id));

      // Aplicar cambios
      if (nodesToRemove.length > 0) nodesDatasetRef.current.remove(nodesToRemove);
      if (edgesToRemove.length > 0) edgesDatasetRef.current.remove(edgesToRemove);
      if (nodesToAdd.length > 0) nodesDatasetRef.current.add(nodesToAdd);
      if (edgesToAdd.length > 0) edgesDatasetRef.current.add(edgesToAdd);
      if (nodesToUpdate.length > 0) nodesDatasetRef.current.update(nodesToUpdate);
      if (edgesToUpdate.length > 0) edgesDatasetRef.current.update(edgesToUpdate);

      // Re-habilitar la física al actualizar datos para permitir el re-layout si hay nuevos nodos
      if (nodesToAdd.length > 0) {
        networkRef.current?.setOptions({ physics: { enabled: true } });
        networkRef.current?.stabilize(150); // Fuerza la estabilización bloqueante de manera invisible
      }
    }

  }, [nodes, edges, isLoading, error, onNodeClick, onNodeDoubleClick, onEdgeClick, convertNodesToVis]);

  useEffect(() => {
    if (!nodesDatasetRef.current || !edgesDatasetRef.current) {
      return;
    }

    const allNodes = nodesDatasetRef.current.get();
    const allEdges = edgesDatasetRef.current.get();

    if (focusedNodeId === null) {
      const needsUpdateNodes = allNodes.filter(n => n.hidden);
      const needsUpdateEdges = allEdges.filter(e => e.hidden);
      if (needsUpdateNodes.length > 0) {
        nodesDatasetRef.current.update(needsUpdateNodes.map(node => ({ id: node.id, hidden: false })));
      }
      if (needsUpdateEdges.length > 0) {
        edgesDatasetRef.current.update(needsUpdateEdges.map(edge => ({ id: edge.id, hidden: false })));
      }
      return;
    }

    const normalizedFocusedNodeId = normalizeGraphId(focusedNodeId);
    const visibleNodeIds = new Set<string>();
    const visibleEdgeIds = new Set<string>();

    if (normalizedFocusedNodeId !== null) {
      visibleNodeIds.add(normalizedFocusedNodeId);
    }

    allEdges.forEach(edge => {
      const normalizedSource = normalizeGraphId(edge.from);
      const normalizedTarget = normalizeGraphId(edge.to);

      if (normalizedSource === normalizedFocusedNodeId || normalizedTarget === normalizedFocusedNodeId) {
        if (normalizedSource !== null) visibleNodeIds.add(normalizedSource);
        if (normalizedTarget !== null) visibleNodeIds.add(normalizedTarget);
        if (edge.id !== undefined && edge.id !== null) {
          visibleEdgeIds.add(String(edge.id));
        }
      }
    });

    const nodesToUpdate = allNodes
      .filter(node => Boolean(node.hidden) !== !visibleNodeIds.has(String(node.id)))
      .map(node => ({ id: node.id, hidden: !visibleNodeIds.has(String(node.id)) }));

    const edgesToUpdate = allEdges
      .filter(edge => {
        const isHidden = edge.id === undefined || edge.id === null ? true : !visibleEdgeIds.has(String(edge.id));
        return Boolean(edge.hidden) !== isHidden;
      })
      .map(edge => ({
        id: edge.id,
        hidden: edge.id === undefined || edge.id === null ? true : !visibleEdgeIds.has(String(edge.id))
      }));

    if (nodesToUpdate.length > 0) nodesDatasetRef.current.update(nodesToUpdate);
    if (edgesToUpdate.length > 0) edgesDatasetRef.current.update(edgesToUpdate);
  }, [focusedNodeId]);

  useImperativeHandle(ref, () => ({
    fitView: () => {
      if (networkRef.current) {
        networkRef.current.fit();
      }
    },
    focusNode: (nodeId: string | number) => {
      const resolvedNodeId = resolveDatasetNodeId(nodeId);
      if (networkRef.current && resolvedNodeId !== null) {
        networkRef.current.focus(resolvedNodeId, {
          scale: 1.1,
          animation: {
            duration: 400,
            easingFunction: 'easeInOutQuad'
          }
        });
      }
    }
  }));

  useEffect(() => {
    if (focusedNodeId === null || !networkRef.current || !nodesDatasetRef.current) {
      lastFocusedNodeIdRef.current = focusedNodeId;
      return;
    }

    if (lastFocusedNodeIdRef.current === focusedNodeId) {
      return; // Prevenir enfoque repetido en el mismo nodo cuando hay re-renders
    }
    lastFocusedNodeIdRef.current = focusedNodeId;

    const resolvedNodeId = resolveDatasetNodeId(focusedNodeId);
    if (resolvedNodeId === null) {
      return;
    }

    networkRef.current.selectNodes([resolvedNodeId]);
    networkRef.current.focus(resolvedNodeId, {
      scale: 1.1,
      animation: {
        duration: 400,
        easingFunction: 'easeInOutQuad'
      }
    });
  }, [focusedNodeId, resolveDatasetNodeId]);

  // Cleanup effect
  useEffect(() => {
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
        nodesDatasetRef.current = null;
        edgesDatasetRef.current = null;
      }
    };
  }, []);

  if (isLoading) {
    return <div className="flex justify-center items-center h-full">Cargando grafo...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center h-full text-red-500">{error}</div>;
  }

  return (
    <div className="w-full h-full relative">
      <div ref={visJsContainer} className="absolute inset-0 w-full h-full" />
      {metadata && <GraphLegend metadata={metadata} getNodeColor={getNodeColor} />}
    </div>
  );
});

GraphVisualization.displayName = 'GraphVisualization';
