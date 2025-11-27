'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, Loader2, CheckCircle, XCircle, Clock, X, FileText, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

export interface UploadTask {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_names: string[];
  topic: string;
  progress?: number;
  error_message?: string;
  created_at: string;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'pending':
      return <Clock className="h-4 w-4 text-amber-500" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-emerald-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Upload className="h-4 w-4 text-gray-500" />;
  }
};

const getStatusText = (status: string, task?: UploadTask) => {
  switch (status) {
    case 'pending':
      return 'En cola';
    case 'processing':
      return `Procesando${task && typeof task.progress === 'number' ? ` • ${Math.round(task.progress)}%` : ''}`;
    case 'completed':
      return 'Completado';
    case 'failed':
      return 'Error';
    default:
      return 'Desconocido';
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'pending':
      return 'from-amber-500/20 to-orange-500/20 border-amber-500/30';
    case 'processing':
      return 'from-blue-500/20 to-cyan-500/20 border-blue-500/30';
    case 'completed':
      return 'from-emerald-500/20 to-green-500/20 border-emerald-500/30';
    case 'failed':
      return 'from-red-500/20 to-rose-500/20 border-red-500/30';
    default:
      return 'from-gray-500/20 to-slate-500/20 border-gray-500/30';
  }
};

export default function UploadProgressIndicator({ tasks }: { tasks: UploadTask[] }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (tasks.length > 0) {
      setIsVisible(true);
    } else {
      const timer = setTimeout(() => setIsVisible(false), 500);
      return () => clearTimeout(timer);
    }
  }, [tasks]);

  if (!isVisible) return null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
      className="mb-6"
    >
      <Card className="relative overflow-hidden border-2 bg-gradient-to-br from-blue-50/80 via-white to-cyan-50/80 dark:from-blue-950/30 dark:via-gray-900 dark:to-cyan-950/30 shadow-lg backdrop-blur-sm">
        {/* Efecto de brillo sutil en el fondo */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/5 to-transparent animate-shimmer" />

        <CardHeader className="pb-4 relative">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-3 text-lg font-semibold">
              <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 shadow-md">
                <Upload className="h-5 w-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  Procesando Documentos
                  <Sparkles className="h-4 w-4 text-blue-500 animate-pulse" />
                </div>
                <p className="text-xs font-normal text-muted-foreground mt-0.5">
                  {tasks.length} {tasks.length === 1 ? 'tarea activa' : 'tareas activas'}
                </p>
              </div>
            </CardTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsVisible(false)}
              className="hover:bg-red-100 dark:hover:bg-red-950/30 transition-colors"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-3 relative">
          <AnimatePresence mode="popLayout">
            {tasks.map((task) => (
              <motion.div
                key={task.id}
                layout
                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: -20, scale: 0.95 }}
                transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                className={`relative p-4 rounded-xl border-2 bg-gradient-to-br ${getStatusColor(task.status)} backdrop-blur-sm overflow-hidden shadow-sm hover:shadow-md transition-shadow`}
              >
                {/* Efecto de brillo para tareas en procesamiento */}
                {task.status === 'processing' && (
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
                )}

                <div className="relative space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div className="mt-0.5">
                        {getStatusIcon(task.status)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                          <p className="font-semibold text-sm truncate">
                            {task.file_names.length === 1
                              ? task.file_names[0]
                              : `${task.file_names.length} archivos`}
                          </p>
                        </div>
                        <p className="text-xs text-muted-foreground/80 flex items-center gap-1.5">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500" />
                          Colección: <span className="font-medium">{task.topic}</span>
                        </p>
                      </div>
                    </div>
                    <span className={`text-xs font-semibold px-3 py-1.5 rounded-full whitespace-nowrap ${task.status === 'completed'
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400'
                        : task.status === 'failed'
                          ? 'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400'
                          : task.status === 'processing'
                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400'
                      }`}>
                      {getStatusText(task.status, task)}
                    </span>
                  </div>

                  {/* Barra de progreso mejorada */}
                  {task.status === 'processing' && typeof task.progress === 'number' && (
                    <div className="space-y-1.5">
                      <div className="relative h-2.5 w-full bg-gray-200/50 dark:bg-gray-700/50 rounded-full overflow-hidden shadow-inner">
                        <motion.div
                          className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 via-cyan-500 to-blue-500 rounded-full shadow-lg"
                          initial={{ width: 0 }}
                          animate={{ width: `${task.progress}%` }}
                          transition={{ duration: 0.5, ease: "easeOut" }}
                        >
                          {/* Efecto de brillo animado en la barra */}
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
                        </motion.div>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-muted-foreground font-medium">
                          Progreso
                        </span>
                        <span className="font-bold text-blue-600 dark:text-blue-400">
                          {Math.round(task.progress)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Mensaje de error */}
                  {task.status === 'failed' && task.error_message && (
                    <div className="mt-2 p-2 bg-red-50 dark:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-800">
                      <p className="text-xs text-red-700 dark:text-red-400">
                        {task.error_message}
                      </p>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}