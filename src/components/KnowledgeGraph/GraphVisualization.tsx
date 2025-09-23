'use client';

import React, { useRef, useEffect, useState } from 'react';
import { Network, DataSet } from 'vis-network/standalone';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface GraphNode {
  id: string | number;
  label: string;
  title?: string;
}

interface GraphEdge {
  id?: string | number;
  from: string | number;
  to: string | number;
  arrows?: string;
  label?: string;
}

interface GraphVisualizationProps {
  workspaceId?: string | null;
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({ workspaceId }) => {
  const visJsContainer = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGraphData = async (forceRefresh = false) => {
      setIsLoading(true);
      setError(null);

      const cacheKey = `graph-data-${workspaceId || 'global'}`;
      if (!forceRefresh) {
        const cachedData = localStorage.getItem(cacheKey);
        if (cachedData) {
          const { nodes, edges, timestamp } = JSON.parse(cachedData);
          // Opcional: invalidar caché después de un tiempo (ej. 1 hora)
          if (Date.now() - timestamp < 3600000) {
            setNodes(nodes);
            setEdges(edges);
            setIsLoading(false);
            toast.info("Datos del grafo cargados desde caché.");
            return;
          }
        }
      }

      try {
        const params: { workspace_id?: string } = {};
        if (workspaceId !== undefined && workspaceId !== null) {
          params.workspace_id = workspaceId;
        }
        const response = await apiClient.get('/api/knowledge-graph/data', { params });
        const data = response.data.data;
        if (data && data.nodes && data.edges) {
          setNodes(data.nodes);
          setEdges(data.edges);
          // Guardar en caché
          const cachePayload = {
            nodes: data.nodes,
            edges: data.edges,
            timestamp: Date.now(),
          };
          localStorage.setItem(cacheKey, JSON.stringify(cachePayload));
        } else {
          setNodes([]);
          setEdges([]);
          toast.info("No se encontraron datos de grafo para este workspace.");
        }
      } catch (err) {
        console.error("Error fetching graph data:", err);
        setError("Error al cargar los datos del grafo.");
        toast.error("Error al cargar los datos del grafo.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchGraphData();
  }, [workspaceId]);

  useEffect(() => {
    if (!visJsContainer.current || isLoading || error) return;

    // Destruye la instancia de la red existente antes de crear una nueva
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    const visNodes = new DataSet<GraphNode>(nodes);
    const visEdges = new DataSet<GraphEdge>(edges);

    const data = { nodes: visNodes, edges: visEdges };

    const options = {
      nodes: {
        shape: 'dot',
        size: 15,
        font: {
          size: 14,
          color: '#ffffff'
        },
        borderWidth: 2,
        color: {
          background: '#6a0dad', // Púrpura
          border: '#4a0080',
          highlight: {
            background: '#8a2be2',
            border: '#6a0dad'
          },
          hover: {
            background: '#8a2be2',
            border: '#6a0dad'
          }
        }
      },
      edges: {
        width: 2,
        color: {
          color: '#cccccc',
          highlight: '#999999',
          hover: '#999999',
          inherit: false,
          opacity: 1.0
        },
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 0.5
          }
        },
        font: {
          size: 10,
          color: '#ffffff',
          align: 'middle'
        }
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
      interaction: {
        navigationButtons: true,
        keyboard: true
      }
    };

    networkRef.current = new Network(visJsContainer.current, data, options);

    // Desactivar físicas después de la estabilización
    networkRef.current.on("stabilizationIterationsDone", function () {
      networkRef.current.setOptions({
        physics: false
      });
    });

    // Limpia la instancia de la red cuando el componente se desmonta
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [nodes, edges, isLoading, error]); // Vuelve a renderizar si los datos cambian

  if (isLoading) {
    return <div className="flex justify-center items-center h-full">Cargando grafo...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center h-full text-red-500">{error}</div>;
  }

  const handleRefresh = () => {
    const fetchGraphData = async (forceRefresh = true) => {
        setIsLoading(true);
        setError(null);

        const cacheKey = `graph-data-${workspaceId || 'global'}`;
        if (!forceRefresh) {
            const cachedData = localStorage.getItem(cacheKey);
            if (cachedData) {
                const { nodes, edges, timestamp } = JSON.parse(cachedData);
                // Opcional: invalidar caché después de un tiempo (ej. 1 hora)
                if (Date.now() - timestamp < 3600000) {
                    setNodes(nodes);
                    setEdges(edges);
                    setIsLoading(false);
                    toast.info("Datos del grafo cargados desde caché.");
                    return;
                }
            }
        }

        try {
            const params: { workspace_id?: string } = {};
            if (workspaceId !== undefined && workspaceId !== null) {
                params.workspace_id = workspaceId;
            }
            const response = await apiClient.get('/api/knowledge-graph/data', { params });
            const data = response.data.data;
            if (data && data.nodes && data.edges) {
                setNodes(data.nodes);
                setEdges(data.edges);
                // Guardar en caché
                const cachePayload = {
                    nodes: data.nodes,
                    edges: data.edges,
                    timestamp: Date.now(),
                };
                localStorage.setItem(cacheKey, JSON.stringify(cachePayload));
            } else {
                setNodes([]);
                setEdges([]);
                toast.info("No se encontraron datos de grafo para este workspace.");
            }
        } catch (err) {
            console.error("Error fetching graph data:", err);
            setError("Error al cargar los datos del grafo.");
            toast.error("Error al cargar los datos del grafo.");
        } finally {
            setIsLoading(false);
        }
    };
    fetchGraphData(true);
  };

  return (
    <div className="w-full h-full">
      <button onClick={handleRefresh} className="absolute top-4 right-4 z-10 bg-primary text-primary-foreground px-4 py-2 rounded">
        Refrescar Grafo
      </button>
      <div ref={visJsContainer} style={{ height: '600px', width: '100%' }} />
    </div>
  );
};