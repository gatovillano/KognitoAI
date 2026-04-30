// src/components/KnowledgeGraph/GraphVisualization.tsx
'use client';

import React, { useRef, useEffect, useImperativeHandle, forwardRef, useCallback } from 'react';
import { Network, DataSet } from 'vis-network/standalone';
import { getNodeColor } from '@/utils/graphUtils';
import { GraphLegend } from './GraphLegend';
import { GraphMetadata } from '@/types/graph';

export interface GraphVisualizationRef {
  fitView: () => void;
}

// Interfaces locales para mayor claridad y control
interface VisGraphNode {
  id: string | number;
  label: string;
  title?: string;
  color?: string | {
    background?: string;
    border?: string;
    highlight?: string | { background?: string; border?: string };
    hover?: string | { background?: string; border?: string };
  };
  size?: number;
  type?: string;
  properties?: any; // Mantenemos properties por si acaso
}

interface VisGraphEdge {
  id?: string | number;
  from: string | number;
  to: string | number;
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
}, ref) => {
  const nodes = React.useMemo(() => graphData?.nodes || [], [graphData?.nodes]);
  const edges = React.useMemo(() => graphData?.edges || [], [graphData?.edges]);
  const visJsContainer = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const nodesDatasetRef = useRef<DataSet<VisGraphNode> | null>(null);
  const edgesDatasetRef = useRef<DataSet<VisGraphEdge> | null>(null);

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

      console.log(`Node ID: ${node.id}, Type: ${nodeType}, Label: ${fullLabel}, Assigned Color: ${nodeColor}`);

      return {
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
          barnesHut: {
            gravitationalConstant: -2000,
            centralGravity: 0.3,
            springLength: 95,
            springConstant: 0.04,
            damping: 0.09,
            avoidOverlap: 0.1
          },
          stabilization: {
            enabled: true,
            iterations: 1000,
            updateInterval: 100,
            onlyDynamicEdges: false,
            fit: true
          }
        },
        layout: {
          randomSeed: 2,
          improvedLayout: true
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

      // Disable physics after stabilization to keep graph static (redundant when physics disabled,
      // but kept for backward compatibility if physics is ever re-enabled)
      networkRef.current.on("stabilizationIterationsDone", () => {
        networkRef.current?.setOptions({ physics: { enabled: false } });
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

      // Nodos a actualizar
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

      // Re-habilitar la física al actualizar datos para permitir el re-layout
      networkRef.current?.setOptions({ physics: { enabled: true } });

      // Para cambios significativos (como filtros), reorganización ultra-rápida
      // Eliminado: networkRef.current.fit(); // Ajustar la vista para que todos los nodos sean visibles
      // La llamada a fit() se realizará explícitamente a través del botón "Vista Completa".
      // Si se necesita un ajuste inicial, se puede considerar añadirlo solo en la primera carga.
    }

  }, [nodes, edges, isLoading, error, onNodeClick, onNodeDoubleClick, onEdgeClick, convertNodesToVis]);

  useImperativeHandle(ref, () => ({
    fitView: () => {
      if (networkRef.current) {
        networkRef.current.fit();
      }
    }
  }));

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