// BackgroundTaskIndicator.tsx
import React from 'react';
import { motion } from 'framer-motion';

interface BackgroundTaskIndicatorProps {
  task: { taskId: string; type: string };
}

export const BackgroundTaskIndicator: React.FC<BackgroundTaskIndicatorProps> = ({ task }) => {
  return (
    <div key={task.taskId} className="flex justify-center w-full py-4">
      <div className="flex flex-col items-center">
        <motion.div
          className="h-12 w-12 border-4 border-t-blue-500 border-b-blue-500 border-l-transparent border-r-transparent rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        <span className="mt-2 text-sm text-muted-foreground">
          Procesando {task.type === 'mindmap' ? 'Mapa Mental' : 'Tarea'}...
        </span>
      </div>
    </div>
  );
};
