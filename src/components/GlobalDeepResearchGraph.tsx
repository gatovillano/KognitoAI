'use client';

import React, { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { GraphVisualization } from './KnowledgeGraph/GraphVisualization';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Minimize2, Maximize2, Sparkles, Database } from 'lucide-react';
import { Button } from './ui/button';

export function GlobalDeepResearchGraph() {
  const { registerMessageHandler } = useWebSocketContext();
  const [isActive, setIsActive] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [researchTitle, setResearchTitle] = useState("Investigación Profunda");
  const processedMessages = useRef<Set<string>>(new Set());
  const hideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeTaskIdRef = useRef<string | null>(null);

  const clearHideTimeout = useCallback(() => {
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  }, []);

  const resetOverlay = useCallback(() => {
    clearHideTimeout();
    setIsActive(false);
    setNodes([]);
    setEdges([]);
    setResearchTitle("Investigación Profunda");
    processedMessages.current.clear();
    activeTaskIdRef.current = null;
  }, [clearHideTimeout]);

  const pushResearchNode = useCallback((label?: string) => {
    const normalizedLabel = (label || 'Procesando...').trim();

    setNodes(prev => {
      const nextNodes = [...prev];

      if (nextNodes.length === 0) {
        nextNodes.push({
          id: 'root',
          label: 'Investigación\nProfunda',
          type: 'Topic',
          properties: { description: 'Núcleo de la investigación en curso.' }
        });
      }

      if (processedMessages.current.has(normalizedLabel)) {
        return nextNodes;
      }

      processedMessages.current.add(normalizedLabel);
      const newNodeId = `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      nextNodes.push({
        id: newNodeId,
        label: normalizedLabel.substring(0, 30) + (normalizedLabel.length > 30 ? '...' : ''),
        type: 'Process',
        properties: { description: normalizedLabel }
      });

      return nextNodes;
    });
  }, []);

  const scheduleHide = useCallback(() => {
    clearHideTimeout();
    hideTimeoutRef.current = setTimeout(() => {
      resetOverlay();
    }, 15000);
  }, [clearHideTimeout, resetOverlay]);

  useEffect(() => {
    const unregister = registerMessageHandler((message: any) => {
      const messageTaskId = message.taskId || message.task_id || null;
      const isActiveTask = !messageTaskId || !activeTaskIdRef.current || messageTaskId === activeTaskIdRef.current;
      const isLegacyDeepResearch =
        (message.type === 'gap_development_update' && message.mode === 'research') ||
        (message.type === 'tool_execution' && message.tool_name === 'deep_research') ||
        (message.type === 'agent_progress' && typeof message.message === 'string' &&
         (message.message.includes('Investigando') || message.message.includes('Deep Research') || message.message.includes('Generando')));
      const isDeepResearchStart = message.type === 'tool_start' && message.tool_name === 'deep_research';
      const isDeepResearchProgress = message.type === 'progress' && !!activeTaskIdRef.current && isActiveTask;
      const isDeepResearchEnd =
        ((message.type === 'tool_end' || message.type === 'tool_error') && message.tool_name === 'deep_research' && isActiveTask) ||
        ((message.status === 'completed' || message.status === 'failed') && isLegacyDeepResearch);

      if ((isLegacyDeepResearch && message.status !== 'completed' && message.status !== 'failed') || isDeepResearchStart || isDeepResearchProgress) {
        clearHideTimeout();
        setIsActive(true);

        if (isDeepResearchStart || isLegacyDeepResearch) {
          activeTaskIdRef.current = messageTaskId || '__deep_research__';
        }

        if (message.question) {
          setResearchTitle(message.question);
        }

        const messageLabel =
          message.message ||
          (typeof message.progress === 'number' ? `Progreso ${Math.round(message.progress)}%` : undefined) ||
          (isDeepResearchStart ? 'Investigación iniciada' : 'Procesando...');

        pushResearchNode(messageLabel);
      }

      if (isDeepResearchEnd) {
        pushResearchNode(
          message.type === 'tool_error' || message.status === 'failed'
            ? (message.error || message.message || 'Investigación finalizada con errores')
            : (message.message || 'Investigación completada')
        );
        scheduleHide();
      }
    });

    return () => unregister();
  }, [registerMessageHandler, clearHideTimeout, pushResearchNode, scheduleHide]);

  useEffect(() => {
    return () => {
      clearHideTimeout();
      processedMessages.current.clear();
      activeTaskIdRef.current = null;
    };
  }, [clearHideTimeout]);

  // Actualizar aristas cuando los nodos cambian
  useEffect(() => {
    setEdges(prev => {
      let newEdges = [...prev];
      // Conectar cada nuevo nodo (a partir del índice 1)
      for (let i = 1; i < nodes.length; i++) {
        const nodeId = nodes[i].id;
        // Si no existe ya una arista apuntando a este nodo
        if (!newEdges.some(e => e.to === nodeId)) {
          // Conectar al root o al nodo anterior para formar una red
          const fromId = i > 1 && Math.random() > 0.4 ? nodes[i-1].id : 'root';
          newEdges.push({ 
            id: `edge_${fromId}_${nodeId}`,
            from: fromId, 
            to: nodeId, 
            type: 'RELATED_TO' 
          });
        }
      }
      return newEdges;
    });
  }, [nodes]);

  const graphData = useMemo(() => ({ nodes, edges }), [nodes, edges]);

  if (!isActive) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 50, x: 50, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, x: 0, scale: 1 }}
        exit={{ opacity: 0, y: 50, x: 50, scale: 0.9 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className={`fixed z-50 transition-all duration-500 ease-in-out ${isMinimized ? 'bottom-6 right-6 w-auto h-auto' : 'bottom-6 right-6 w-[90vw] md:w-[600px] h-[450px]'}`}
      >
        <div className="w-full h-full bg-card/95 backdrop-blur-3xl border border-primary/20 shadow-[0_20px_50px_rgba(0,0,0,0.5)] rounded-[2rem] overflow-hidden flex flex-col relative group">
          {/* Decorative background glow */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
             <div className="absolute top-[-20%] left-[-10%] w-64 h-64 bg-primary/20 rounded-full blur-[80px] animate-pulse" />
          </div>

          <div className="flex items-center justify-between p-4 bg-muted/40 border-b border-border/20 relative z-10 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 border border-primary/20 shadow-inner">
                <Database className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h4 className="font-bold text-sm text-foreground flex items-center gap-2">
                  Topología de Investigación <Sparkles className="w-3 h-3 text-amber-400" />
                </h4>
                <p className="text-xs text-muted-foreground truncate max-w-[280px]">
                  {researchTitle}
                </p>
                <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold flex items-center gap-1">
                   <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                   </span>
                   {nodes.length - 1} descubrimientos
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" size="icon" className="w-8 h-8 rounded-full hover:bg-primary/10 transition-colors" onClick={() => setIsMinimized(!isMinimized)}>
                {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
              </Button>
              <Button variant="ghost" size="icon" className="w-8 h-8 rounded-full text-destructive hover:bg-destructive/10 transition-colors" onClick={() => setIsActive(false)}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          {!isMinimized && (
            <div className="flex-1 relative bg-background/50 rounded-b-[2rem] overflow-hidden">
              <GraphVisualization graphData={graphData} />
              
              {/* Overlay pulse when analyzing */}
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-center pointer-events-none">
                <div className="px-5 py-2.5 rounded-full bg-background/80 border border-primary/30 backdrop-blur-xl shadow-lg flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-primary animate-ping" />
                  <span className="text-[10px] font-black text-primary tracking-[0.2em] uppercase">Mapeando base de conocimiento...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
