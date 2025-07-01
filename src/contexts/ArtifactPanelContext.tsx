'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface ArtifactPanelContextType {
  isVisible: boolean;
  toggleVisibility: () => void;
}

const ArtifactPanelContext = createContext<ArtifactPanelContextType | undefined>(undefined);

export const ArtifactPanelProvider = ({ children }: { children: ReactNode }) => {
  const [isVisible, setIsVisible] = useState(false);

  const toggleVisibility = () => {
    setIsVisible(prev => !prev);
  };

  return (
    <ArtifactPanelContext.Provider value={{ isVisible, toggleVisibility }}>
      {children}
    </ArtifactPanelContext.Provider>
  );
};

export const useArtifactPanel = () => {
  const context = useContext(ArtifactPanelContext);
  if (context === undefined) {
    throw new Error('useArtifactPanel must be used within an ArtifactPanelProvider');
  }
  return context;
};
