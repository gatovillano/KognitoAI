// LoadingIndicator.tsx
import React from 'react';
import { motion } from 'framer-motion';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface LoadingIndicatorProps {
  isComprehensiveAnalysisActive: boolean;
  isKnowledgeAnalysisActive: boolean;
}

export const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  isComprehensiveAnalysisActive,
  isKnowledgeAnalysisActive,
}) => {
  return (
    <>
      {(isComprehensiveAnalysisActive || isKnowledgeAnalysisActive) ? (
        <div className="flex justify-center w-full py-4">
          <div className="flex flex-col items-center">
            <div className="relative h-12 w-12">
              <motion.div
                className="absolute inset-0 border-4 border-t-primary border-b-primary border-l-transparent border-r-transparent rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
              />
              <motion.div
                className="absolute inset-2 border-2 border-t-primary/50 border-b-primary/50 border-l-transparent border-r-transparent rounded-full"
                animate={{ rotate: -360 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
              />
            </div>
            <span className="mt-2 text-sm text-muted-foreground">
              {isComprehensiveAnalysisActive ? 'Buscando y analizando...' : 'Analizando conocimientos...'}
            </span>
          </div>
        </div>
      ) : (
        <div className="flex justify-center w-full py-2">
          <div className="flex items-center space-x-1">
            <motion.div
              className="h-4 w-4 bg-primary rounded-full"
              animate={{ scale: [1, 1.3, 1], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            />
            <motion.div
              className="h-4 w-4 bg-primary rounded-full"
              animate={{ scale: [1, 1.3, 1], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
            />
            <motion.div
              className="h-4 w-4 bg-primary rounded-full"
              animate={{ scale: [1, 1.3, 1], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.6 }}
            />
          </div>
          <span className="ml-2 text-sm text-muted-foreground">Procesando...</span>
        </div>
      )}
    </>
  );
};
