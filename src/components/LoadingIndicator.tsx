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
        <div className="flex justify-center w-full">
          <div className="w-full max-w-3xl mx-auto">
            <div className="flex items-start gap-4">
              <Avatar className="h-12 w-12 border">
                <AvatarImage src="/logo-simple.png" alt="Kognito" />
                <AvatarFallback>K</AvatarFallback>
              </Avatar>
              <div className="rounded-lg p-3 bg-secondary flex justify-center items-center">
                <motion.div
                  className="flex space-x-1"
                  animate={{
                    opacity: [1, 0.5, 1],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                >
                  <motion.div className="h-2 w-6 bg-gray-600 rounded-full" style={{ borderRadius: '10px' }} />
                  <motion.div
                    className="h-2 w-6 bg-gray-600 rounded-full"
                    style={{ borderRadius: '10px' }}
                    animate={{ y: [0, -2, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
                  />
                  <motion.div
                    className="h-2 w-6 bg-gray-600 rounded-full"
                    style={{ borderRadius: '10px' }}
                    animate={{ y: [0, -2, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.6 }}
                  />
                </motion.div>
                <span className="ml-2 text-sm text-muted-foreground"></span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
