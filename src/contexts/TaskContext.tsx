'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useWebSocketContext } from './WebSocketContext';
import { WebSocketMessage } from '@/hooks/useWebSocket';
import { toast } from 'sonner';

export interface UploadTask {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_names: string[];
  topic: string;
  progress?: number;
  error_message?: string;
  created_at: string;
}

export interface AnalysisTask {
  task_id: string;
  phase: string;
  message: string;
  progress_percent: number;
  is_complete: boolean;
  has_error: boolean;
  error?: string;
  metrics?: {
    entities_count: number;
    relationships_count: number;
    documents_processed: number;
    quotes_extracted: number;
  };
  processing_mode?: string;
  topic?: string;
  file_name?: string;
  analysis_type?: string;
  type?: 'graph' | 'analysis' | 'collection' | 'document';
}

interface TaskContextType {
  uploadTasks: UploadTask[];
  analysisTasks: AnalysisTask[];
  addUploadTask: (task: UploadTask) => void;
  addAnalysisTask: (task: AnalysisTask) => void;
  removeAnalysisTask: (taskId: string) => void;
  updateAnalysisTask: (taskId: string, updates: Partial<AnalysisTask>) => void;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export function TaskProvider({ children }: { children: React.ReactNode }) {
  const [uploadTasks, setUploadTasks] = useState<UploadTask[]>([]);
  const [analysisTasks, setAnalysisTasks] = useState<AnalysisTask[]>([]);
  const { registerMessageHandler } = useWebSocketContext();

  const addUploadTask = useCallback((task: UploadTask) => {
    setUploadTasks(prev => [...prev, task]);
  }, []);

  const addAnalysisTask = useCallback((task: AnalysisTask) => {
    setAnalysisTasks(prev => {
        const exists = prev.some(t => t.task_id === task.task_id);
        if (exists) return prev;
        return [...prev, task];
    });
  }, []);

  const removeAnalysisTask = useCallback((taskId: string) => {
    setAnalysisTasks(prev => prev.filter(t => t.task_id !== taskId));
  }, []);

  const updateAnalysisTask = useCallback((taskId: string, updates: Partial<AnalysisTask>) => {
    setAnalysisTasks(prev => prev.map(t => t.task_id === taskId ? { ...t, ...updates } : t));
  }, []);

  useEffect(() => {
    const handleWebSocketMessage = (message: WebSocketMessage) => {
      if (!message) return;

      switch (message.type) {
        case 'upload_started':
          setUploadTasks(prev => {
            const exists = prev.some(t => t.id === message.task_id);
            if (exists) return prev;
            return [...prev, { 
                id: message.task_id, 
                status: 'processing', 
                file_names: message.file_names || [], 
                topic: message.topic || '', 
                created_at: message.created_at || new Date().toISOString() 
            }];
          });
          break;

        case 'upload_progress':
          const progressData = message.data || message;
          setUploadTasks(prev => prev.map(task => 
            task.id === progressData.task_id ? { ...task, progress: progressData.progress } : task
          ));
          break;

        case 'upload_completed':
          const completeData = message.data || message;
          toast.success(completeData.message || 'Subida completada.');
          setUploadTasks(prev => prev.filter(task => task.id !== completeData.task_id));
          break;

        case 'upload_failed':
          const failData = message.data || message;
          toast.error(failData.error_message || 'Falló la subida de archivos.');
          setUploadTasks(prev => prev.filter(task => task.id !== failData.task_id));
          break;

        case 'knowledge_graph_progress':
        case 'analysis_progress':
          const taskData = (message.data || message) as AnalysisTask;
          if (taskData && taskData.task_id) {
            setAnalysisTasks(prev => {
              const exists = prev.some(t => t.task_id === taskData.task_id);
              if (exists) {
                return prev.map(t => t.task_id === taskData.task_id ? { ...t, ...taskData } : t);
              }

              // Intentar vincular con tarea temporal
              const tempIndex = prev.findIndex(t => t.task_id.startsWith('temp-') && t.topic === taskData.topic);
              if (tempIndex !== -1) {
                const updated = [...prev];
                updated[tempIndex] = { ...updated[tempIndex], ...taskData };
                return updated;
              }

              return [...prev, { ...taskData, type: message.type === 'knowledge_graph_progress' ? 'graph' : 'analysis' }];
            });
          }
          break;
        
        case 'collection_analysis_completed':
          if (message.task_id) {
            toast.success("Análisis de colección completado");
            setAnalysisTasks(prev => prev.map(t => t.task_id === message.task_id ? { ...t, is_complete: true, progress_percent: 100 } : t));
          }
          break;
        
        case 'collection_analysis_failed':
          if (message.task_id) {
             toast.error("Error en el análisis de la colección");
             setAnalysisTasks(prev => prev.map(t => t.task_id === message.task_id ? { ...t, has_error: true, error: message.error } : t));
          }
          break;
      }
    };

    const unregister = registerMessageHandler(handleWebSocketMessage);
    return unregister;
  }, [registerMessageHandler]);

  return (
    <TaskContext.Provider value={{ 
        uploadTasks, 
        analysisTasks, 
        addUploadTask, 
        addAnalysisTask, 
        removeAnalysisTask,
        updateAnalysisTask
    }}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTaskContext() {
  const context = useContext(TaskContext);
  if (context === undefined) {
    throw new Error('useTaskContext must be used within a TaskProvider');
  }
  return context;
}
