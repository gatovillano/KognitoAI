'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface WorkspaceTitleContextType {
  title: string;
  setTitle: (title: string) => void;
}

const WorkspaceTitleContext = createContext<WorkspaceTitleContextType | undefined>(undefined);

export const WorkspaceTitleProvider = ({ children }: { children: ReactNode }) => {
  const [title, setTitle] = useState<string>('');
  return (
    <WorkspaceTitleContext.Provider value={{ title, setTitle }}>
      {children}
    </WorkspaceTitleContext.Provider>
  );
};

export const useWorkspaceTitle = () => {
  const context = useContext(WorkspaceTitleContext);
  if (context === undefined) {
    throw new Error('useWorkspaceTitle must be used within a WorkspaceTitleProvider');
  }
  return context;
};
