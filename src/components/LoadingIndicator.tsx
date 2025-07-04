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
        <div className="flex justify-start w-full py-3">
          <div className="space-y-3 w-full max-w-md">
            {/* Línea 1 - larga */}
            <motion.div
              className="h-4 bg-muted rounded-lg"
              style={{ width: '75%' }}
              animate={{ opacity: [0.4, 0.8, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0 }}
            />
            {/* Línea 2 - muy larga */}
            <motion.div
              className="h-4 bg-muted rounded-lg"
              style={{ width: '90%' }}
              animate={{ opacity: [0.4, 0.8, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
            />
            {/* Línea 3 - mediana */}
            <motion.div
              className="h-4 bg-muted rounded-lg"
              style={{ width: '60%' }}
              animate={{ opacity: [0.4, 0.8, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.6 }}
            />
          </div>
        </div>
      )}
    </>
  );
};
