'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, Loader2, CheckCircle, XCircle, Clock, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

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
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
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
      return `Procesando${task && typeof task.progress === 'number' ? ` (${Math.round(task.progress)}%)` : ''}`;
    case 'completed':
      return 'Completado';
    case 'failed':
      return 'Error';
    default:
      return 'Desconocido';
  }
};

export default function UploadProgressIndicator({ tasks }: { tasks: UploadTask[] }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (tasks.length > 0) {
      setIsVisible(true);
    } else {
      // Ocultar después de un breve retraso si todas las tareas se han ido
      const timer = setTimeout(() => setIsVisible(false), 500);
      return () => clearTimeout(timer);
    }
  }, [tasks]);

  if (!isVisible) return null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 100 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 100 }}
      transition={{ duration: 0.3 }}
      className="mb-6"
    >
      <Card className="border-l-4 border-l-blue-500 bg-blue-50/50 dark:bg-blue-950/20">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Upload className="h-5 w-5 text-blue-600" />
            Procesando Documentos
          </CardTitle>
          <Button variant="ghost" size="icon" onClick={() => setIsVisible(false)}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          <AnimatePresence>
            {tasks.map((task) => (
              <motion.div
                key={task.id}
                layout
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="p-3 bg-white dark:bg-gray-800 rounded-lg border"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {getStatusIcon(task.status)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">
                        {task.file_names.length === 1
                          ? task.file_names[0]
                          : `${task.file_names.length} archivos`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Colección: {task.topic}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-medium px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700">
                    {getStatusText(task.status, task)}
                  </span>
                </div>
                {task.status === 'processing' && typeof task.progress === 'number' && (
                  <div className="w-full bg-gray-200 rounded-full h-1.5 dark:bg-gray-700 mt-1">
                    <div className="bg-blue-600 h-1.5 rounded-full" style={{ width: `${task.progress}%`, transition: 'width 0.5s ease-in-out' }}></div>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}