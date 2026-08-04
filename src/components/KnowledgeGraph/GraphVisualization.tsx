// src/components/KnowledgeGraph/GraphVisualization.tsx (3D WebGL Version with full interactivity & normalized IDs)
'use client';

import React, { useRef, useEffect, useImperativeHandle, forwardRef, useCallback, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import * as THREE from 'three';
import { getNodeColor } from '@/utils/graphUtils';
import { GraphMetadata } from '@/types/graph';
import { Button } from '@/components/ui/button';
import { RotateCw, Maximize2, Sparkles, FilterX } from 'lucide-react';

// Dynamic import of ForceGraph3D to prevent SSR window/document issues in Next.js
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), {
  ssr: false,
  loading: () => (
    <div className="flex justify-center items-center h-full min-h-[500px] text-muted-foreground">
      Cargando visor 3D WebGL...
    </div>
  ),
});

export interface GraphVisualizationRef {
  fitView: () => void;
  focusNode: (nodeId: string | number) => void;
}

export interface VisGraphNode {
  id: string | number;
  label: string;
  title?: string;
  color?: string | any;
  size?: number;
  type?: string;
  properties?: any;
  x?: number;
  y?: number;
  z?: number;
}

export interface VisGraphEdge {
  id?: string | number;
  from: string | number;
  to: string | number;
  source?: string | number;
  target?: string | number;
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
  onNodeDoubleClick?: (nodeId: string | number) => void;
  onEdgeClick?: (edge: VisGraphEdge) => void;
  savedNodeIds?: Set<string | number>;
  focusedNodeId?: string | number | null;
}

export const GraphVisualization = forwardRef<GraphVisualizationRef, GraphVisualizationProps>(({
  graphData,
  metadata,
  isLoading = false,
  error = null,
  onNodeClick,
  onNodeDoubleClick,
  onEdgeClick,
  savedNodeIds = new Set(),
  focusedNodeId = null,
}, ref) => {
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [enableRotation, setEnableRotation] = useState(false);
  const [showParticles, setShowParticles] = useState(true);
  const lastClickTimeRef = useRef<{ id: string | number; time: number } | null>(null);

  // Resize handler for responsive 3D Canvas
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || 800,
          height: containerRef.current.clientHeight || 600,
        });
      }
    };
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const truncateText = (text: string, maxLength: number = 30) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Format 3D Node objects & Normalize IDs to strings to prevent Quadtree hit failures
  const formattedData = useMemo(() => {
    if (!graphData || !graphData.nodes) {
      return { nodes: [], links: [] };
    }

    const nodeMap = new Map<string, any>();
    const nodes: any[] = [];

    graphData.nodes.forEach(node => {
      if (!node || node.id === undefined || node.id === null) return;
      const strId = String(node.id);
      if (nodeMap.has(strId)) return; // Deduplicate

      const fullLabel = node.properties?.name || node.properties?.title || node.label || strId;
      const truncatedLabel = truncateText(fullLabel);
      const description = node.properties?.description || node.properties?.text || fullLabel;
      const nodeType = node.type || 'Desconocido';

      const formattedNode = {
        ...node,
        id: strId,
        rawId: node.id,
        label: truncatedLabel,
        fullLabel: fullLabel,
        title: description,
        type: nodeType,
        size: 12,
        properties: node.properties || {},
      };

      nodeMap.set(strId, formattedNode);
      nodes.push(formattedNode);
    });

    const links = (graphData.edges || [])
      .map(edge => {
        if (!edge) return null;
        const rawSource = edge.from !== undefined ? edge.from : edge.source;
        const rawTarget = edge.to !== undefined ? edge.to : edge.target;

        if (rawSource === undefined || rawSource === null || rawTarget === undefined || rawTarget === null) return null;

        const sourceId = String(rawSource);
        const targetId = String(rawTarget);

        // Ensure both endpoints exist in nodeMap
        if (!nodeMap.has(sourceId) || !nodeMap.has(targetId)) {
          return null;
        }

        return {
          id: String(edge.id || `${sourceId}-${targetId}`),
          source: sourceId,
          target: targetId,
          from: sourceId,
          to: targetId,
          label: edge.label || edge.type || '',
          title: edge.properties?.description || edge.title || edge.label || edge.type || '',
          type: edge.type,
          properties: edge.properties || {},
        };
      })
      .filter((link): link is NonNullable<typeof link> => link !== null);

    return { nodes, links };
  }, [graphData]);

  // Set of connected node IDs when focusedNodeId is set (for double click isolation)
  const connectedNodeIds = useMemo(() => {
    if (focusedNodeId === null || focusedNodeId === undefined) return null;
    const set = new Set<string>();
    const focusedStr = String(focusedNodeId);
    set.add(focusedStr);

    formattedData.links.forEach((link: any) => {
      const sId = String(link.source?.id !== undefined ? link.source.id : link.source);
      const tId = String(link.target?.id !== undefined ? link.target.id : link.target);
      if (sId === focusedStr) set.add(tId);
      if (tId === focusedStr) set.add(sId);
    });
    return set;
  }, [focusedNodeId, formattedData.links]);

  // Configure 3D physics forces for greater node separation (only reheat when graph nodes count changes)
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge')?.strength(-320);
      fgRef.current.d3Force('link')?.distance(130);
      fgRef.current.d3ReheatSimulation();
    }
  }, [graphData?.nodes?.length]);

  // Handle auto-rotation
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.controls().autoRotate = enableRotation;
      fgRef.current.controls().autoRotateSpeed = 0.8;
    }
  }, [enableRotation]);

  // Expose fitView & focusNode imperative methods
  useImperativeHandle(ref, () => ({
    fitView: () => {
      if (fgRef.current) {
        fgRef.current.zoomToFit(800, 40);
      }
    },
    focusNode: (nodeId: string | number) => {
      if (fgRef.current) {
        const node = formattedData.nodes.find(n => String(n.id) === String(nodeId));
        if (node && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
          const distance = 120;
          const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);

          fgRef.current.cameraPosition(
            { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
            { x: node.x, y: node.y, z: node.z },
            1000
          );
        }
      }
    }
  }));

  // Create 3D Mesh Object per Node (Sphere with dynamic isolation opacity)
  const nodeThreeObject = useCallback((node: any) => {
    const group = new THREE.Group();
    const isSaved = savedNodeIds.has(node.id) || savedNodeIds.has(node.rawId) || savedNodeIds.has(String(node.id));
    const isFocused = focusedNodeId !== null && String(node.id) === String(focusedNodeId);
    const isIsolated = connectedNodeIds !== null && !connectedNodeIds.has(String(node.id));

    const colorVal = getNodeColor(node.type || 'Desconocido');
    const colorHex = isSaved ? '#FACC15' : (typeof colorVal === 'string' ? colorVal : '#DDA0DD');

    // Sphere geometry
    const radius = isSaved ? 9 : (isFocused ? 10 : 6.5);
    const geometry = new THREE.SphereGeometry(radius, 16, 16);
    const material = new THREE.MeshLambertMaterial({
      color: isIsolated ? '#334155' : colorHex,
      transparent: true,
      opacity: isIsolated ? 0.25 : 0.9,
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // Glowing border for saved or focused nodes
    if ((isSaved || isFocused) && !isIsolated) {
      const ringGeometry = new THREE.RingGeometry(radius + 1, radius + 3, 32);
      const ringMaterial = new THREE.MeshBasicMaterial({
        color: isSaved ? 0xfacc15 : 0x3b82f6,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.8,
      });
      const ring = new THREE.Mesh(ringGeometry, ringMaterial);
      group.add(ring);
    }

    return group;
  }, [savedNodeIds, focusedNodeId, connectedNodeIds]);

  // Click & Double Click handler (Instant execution without camera jumps)
  const handleNodeClick = useCallback((node: any) => {
    if (!node) return;
    console.log("🔍 Clic en nodo 3D registrado:", node.id);

    const now = Date.now();
    if (lastClickTimeRef.current && lastClickTimeRef.current.id === node.id && (now - lastClickTimeRef.current.time) < 450) {
      // Double Click: Isolate relationships
      console.log("🔍 Doble clic en nodo 3D - aislar relaciones:", node.id);
      if (onNodeDoubleClick) {
        onNodeDoubleClick(node.id);
      }
      lastClickTimeRef.current = null;
      return;
    }

    lastClickTimeRef.current = { id: node.id, time: now };
    if (onNodeClick) {
      onNodeClick(node);
    }
  }, [onNodeClick, onNodeDoubleClick]);

  const handleNodeRightClick = useCallback((node: any) => {
    if (node && onNodeDoubleClick) {
      console.log("🔍 Clic derecho en nodo 3D - aislar relaciones:", node.id);
      onNodeDoubleClick(node.id);
    }
  }, [onNodeDoubleClick]);

  const handleLinkClick = useCallback((link: any) => {
    if (!link) return;
    console.log("🔍 Clic en arista 3D:", link.id);
    if (onEdgeClick) {
      onEdgeClick({
        id: link.id,
        from: link.source?.id !== undefined ? link.source.id : link.source,
        to: link.target?.id !== undefined ? link.target.id : link.target,
        label: link.label,
        title: link.title,
        properties: link.properties,
        type: link.type,
      });
    }
  }, [onEdgeClick]);

  if (isLoading) {
    return <div className="flex justify-center items-center h-full text-muted-foreground">Cargando grafo 3D...</div>;
  }

  if (error) {
    return <div className="flex justify-center items-center h-full text-red-500">{error}</div>;
  }

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden bg-slate-950 rounded-lg min-h-[500px]">
      {/* 3D Canvas Controls Toolbar */}
      <div className="absolute top-4 right-4 z-10 flex gap-2 bg-slate-900/80 backdrop-blur-md p-1.5 rounded-lg border border-slate-800 shadow-lg">
        {focusedNodeId && onNodeDoubleClick && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => onNodeDoubleClick(focusedNodeId)}
            title="Quitar aislamiento de relaciones"
            className="h-8 px-2 text-xs gap-1.5"
          >
            <FilterX className="h-3.5 w-3.5" />
            Ver todo
          </Button>
        )}
        <Button
          size="sm"
          variant={enableRotation ? "default" : "outline"}
          onClick={() => setEnableRotation(!enableRotation)}
          title="Alternar rotación automática 3D"
          className="h-8 px-2 text-xs gap-1.5 text-slate-200 border-slate-700"
        >
          <RotateCw className={`h-3.5 w-3.5 ${enableRotation ? 'animate-spin' : ''}`} />
          {enableRotation ? 'Rotando' : 'Girar'}
        </Button>
        <Button
          size="sm"
          variant={showParticles ? "default" : "outline"}
          onClick={() => setShowParticles(!showParticles)}
          title="Alternar flujo de partículas en aristas"
          className="h-8 px-2 text-xs gap-1.5 text-slate-200 border-slate-700"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {showParticles ? 'Partículas' : 'Estático'}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => fgRef.current?.zoomToFit(800, 40)}
          title="Centrar vista 3D"
          className="h-8 px-2 text-xs gap-1.5 text-slate-200 border-slate-700"
        >
          <Maximize2 className="h-3.5 w-3.5" />
          Centrar
        </Button>
      </div>

      {/* Force Graph 3D Component */}
      <ForceGraph3D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={formattedData}
        nodeThreeObject={nodeThreeObject}
        onNodeHover={(node: any) => {
          if (containerRef.current) {
            containerRef.current.style.cursor = node ? 'pointer' : 'default';
          }
        }}
        onLinkHover={(link: any) => {
          if (containerRef.current) {
            containerRef.current.style.cursor = link ? 'pointer' : 'default';
          }
        }}
        nodeLabel={(node: any) => `
          <div style="background: rgba(15,23,42,0.95); color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 12px; border: 1px solid #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
            <strong>${node.fullLabel || node.label || node.id}</strong>
            ${node.type ? `<br/><span style="color: #38bdf8; font-size: 11px; font-weight: 500;">Tipo: ${node.type}</span>` : ''}
            ${node.title && node.title !== node.fullLabel ? `<br/><span style="color: #94a3b8; font-size: 11px;">${node.title}</span>` : ''}
          </div>
        `}
        linkLabel={(link: any) => `
          <div style="background: rgba(15,23,42,0.95); color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 12px; border: 1px solid #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
            <strong style="color: #38bdf8;">${link.type || link.label || 'Relación'}</strong>
            ${link.title ? `<br/><span style="color: #94a3b8; font-size: 11px;">${link.title}</span>` : ''}
          </div>
        `}
        onNodeClick={handleNodeClick}
        onNodeRightClick={handleNodeRightClick}
        onLinkClick={handleLinkClick}
        linkWidth={(link: any) => {
          if (focusedNodeId !== null && focusedNodeId !== undefined) {
            const sId = String(link.source?.id !== undefined ? link.source.id : link.source);
            const tId = String(link.target?.id !== undefined ? link.target.id : link.target);
            const focusedStr = String(focusedNodeId);
            return (sId === focusedStr || tId === focusedStr) ? 3.5 : 0.4;
          }
          return 1.5;
        }}
        linkColor={(link: any) => {
          if (focusedNodeId !== null && focusedNodeId !== undefined) {
            const sId = String(link.source?.id !== undefined ? link.source.id : link.source);
            const tId = String(link.target?.id !== undefined ? link.target.id : link.target);
            const focusedStr = String(focusedNodeId);
            if (sId === focusedStr || tId === focusedStr) {
              return '#38bdf8';
            }
            return 'rgba(30, 41, 59, 0.15)';
          }
          return '#475569';
        }}
        linkDirectionalParticles={(link: any) => {
          if (focusedNodeId !== null && focusedNodeId !== undefined) {
            const sId = String(link.source?.id !== undefined ? link.source.id : link.source);
            const tId = String(link.target?.id !== undefined ? link.target.id : link.target);
            const focusedStr = String(focusedNodeId);
            return (sId === focusedStr || tId === focusedStr) ? 4 : 0;
          }
          return showParticles ? 3 : 0;
        }}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.006}
        linkDirectionalParticleColor={() => '#60A5FA'}
        backgroundColor="#090d16"
        showNavInfo={false}
      />
    </div>
  );
});

GraphVisualization.displayName = 'GraphVisualization';
