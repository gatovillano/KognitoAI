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
            <motion.div
              className="h-12 w-12 border-4 border-t-primary border-b-primary border-l-transparent border-r-transparent rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            <span className="mt-2 text-sm text-muted-foreground">
              {isComprehensiveAnalysisActive ? 'Buscando y analizando...' : 'Analizando conocimientos...'}
            </span>
          </div>
        </div>
      ) : (
        <div className="flex justify-center w-full py-2">
          <div className="flex items-center space-x-2">
            <motion.div
              className="h-3 w-3 bg-primary rounded-full"
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            />
            <motion.div
              className="h-3 w-3 bg-primary rounded-full"
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
            />
            <motion.div
              className="h-3 w-3 bg-primary rounded-full"
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.6 }}
            />
          </div>
          <span className="ml-2 text-sm text-muted-foreground">Procesando...</span>
        </div>
      )}
    </>
  );
};
