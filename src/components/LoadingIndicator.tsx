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
          <div className="flex items-center space-x-3">
            <div className="relative">
              {/* Outer glow ring */}
              <motion.div
                className="absolute inset-0 w-8 h-8 rounded-full bg-gradient-to-r from-primary/30 via-primary/60 to-primary/30 blur-sm"
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              />
              {/* Main spinner */}
              <motion.div
                className="relative w-8 h-8 rounded-full bg-gradient-to-r from-primary via-primary/80 to-transparent"
                animate={{ rotate: 360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                style={{
                  background: 'conic-gradient(from 0deg, transparent, hsl(var(--primary)), transparent)',
                }}
              />
              {/* Inner core */}
              <motion.div
                className="absolute top-1/2 left-1/2 w-2 h-2 bg-primary rounded-full transform -translate-x-1/2 -translate-y-1/2"
                animate={{ scale: [0.8, 1.2, 0.8], opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
              />
              {/* Orbiting dots */}
              <motion.div
                className="absolute top-0 left-1/2 w-1 h-1 bg-primary/60 rounded-full transform -translate-x-1/2"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                style={{ transformOrigin: '50% 16px' }}
              />
              <motion.div
                className="absolute top-0 left-1/2 w-1 h-1 bg-primary/40 rounded-full transform -translate-x-1/2"
                animate={{ rotate: -360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                style={{ transformOrigin: '50% 16px' }}
              />
            </div>
            <motion.span 
              className="text-sm text-muted-foreground font-medium"
              animate={{ opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            >
              Procesando...
            </motion.span>
          </div>
        </div>
      )}
    </>
  );
};
