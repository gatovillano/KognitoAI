// src/components/KnowledgeGraph/GraphVisualization.tsx
'use client';

import React, { useRef, useEffect } from 'react';
import { Network, DataSet } from 'vis-network/standalone';

// Interfaces locales para mayor claridad y control
interface VisGraphNode {
  id: string | number;
  label: string;
  title?: string;
  color?: string;
  size?: number;
  type?: string;
  properties?: any; // Mantenemos properties por si acaso
}

interface VisGraphEdge {
  id?: string | number;
  source: string | number;
  target: string | number;
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
  isLoading?: boolean;
  error?: string | null;
  onNodeClick?: (node: VisGraphNode) => void;
  // onEdgeClick?: (edge: GraphEdge) => void; // Puedes añadir si necesitas interactividad con aristas
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  graphData,
  isLoading = false,
  error = null,
  onNodeClick,
}) => {
  const nodes = React.useMemo(() => graphData?.nodes || [], [graphData?.nodes]);
  const edges = React.useMemo(() => graphData?.edges || [], [graphData?.edges]);
  const visJsContainer = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!visJsContainer.current || isLoading || error) return;

    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    // Adaptar los datos del backend al formato de vis.js
    const visNodes = new DataSet<VisGraphNode>(nodes.map(node => ({
        id: node.id,
        label: node.label,
        title: node.properties?.description || node.label, // Tooltip
        properties: node.properties,
        type: node.type,
        // Puedes añadir aquí lógica de coloración/forma basada en node.properties.type o node.properties.category
        color: node.properties?.category === 'Desafío' ? '#EF4444' : (node.type === 'CONCEPTUAL_QUOTE' ? '#22C55E' : '#3B82F6')
    })));
    
    const visEdges = new DataSet<VisGraphEdge>(edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        title: edge.properties?.description || edge.label, // Tooltip
        properties: edge.properties,
        type: edge.type,
        arrows: 'to', // Flecha hacia el destino
        color: '#cccccc' // Color por defecto
    })));

    const data = { nodes: visNodes, edges: visEdges };

    const options = {
      nodes: {
        shape: 'dot',
        size: 15,
        font: { size: 14, color: '#000000' }, // Color de fuente oscuro para contraste
        borderWidth: 2,
        // Los colores se pueden definir en el mapeo de nodos o aquí con una función
      },
      edges: {
        width: 2,
        color: { color: '#cccccc', highlight: '#999999', hover: '#999999', inherit: false, opacity: 1.0 },
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
          avoidOverlap: 0.5
        },
        solver: 'barnesHut'
      },
      interaction: { navigationButtons: true, keyboard: true, hover: true },
      // Añadir una animación inicial para que los nodos no se superpongan al cargar
      layout: { improvedLayout: true }
    };

    networkRef.current = new Network(visJsContainer.current, data, options);

    // Evento de clic en nodo
    if (onNodeClick) {
      networkRef.current.on("click", (properties) => {
        if (properties.nodes.length > 0) {
          const nodeId = properties.nodes[0];
          const clickedNode = nodes.find(n => n.id === nodeId);
          if (clickedNode) onNodeClick(clickedNode);
        }
      });
    }

    // Deshabilitar la física una vez que la red se estabilice
    networkRef.current.on("stabilizationIterationsDone", function () {
      if (networkRef.current) {
        networkRef.current.setOptions({ physics: false });
      }
    });

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [nodes, edges, isLoading, error, onNodeClick]); // Dependencias ahora son las props

  if (isLoading) {
    return <div className="flex justify-center items-center h-full">Cargando grafo...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center h-full text-red-500">{error}</div>;
  }

  return (
    <div className="w-full h-full">
      <div ref={visJsContainer} style={{ height: '600px', width: '100%' }} />
    </div>
  );
};