'use client';

import React, { useState } from 'react';
import { useMediaQuery } from '@uidotdev/usehooks';
import { Sidebar } from './Sidebar';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import Image from 'next/image';
import { ThemeToggle } from './ThemeToggle'; // Importamos el botón de tema
import { LoadingProvider } from '@/contexts/LoadingContext';
import { useArtifactPanel } from '@/contexts/ArtifactPanelContext';
import { PanelRightOpen, PanelRightClose } from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  return (
    <LoadingProvider>
      {isDesktop ? (
        <div className="h-screen max-h-screen overflow-hidden flex bg-background">
          <div
            className={`bg-card transition-all duration-300 ease-in-out rounded-tr-lg ${isSidebarCollapsed ? 'w-20' : 'w-80'}`}
          >
            <Sidebar isCollapsed={isSidebarCollapsed} />
          </div>

          <div className="flex-grow flex flex-col">
            <header className="flex h-14 items-center gap-4 bg-card px-4 shrink-0 rounded-none">
              <Button variant="ghost" size="icon" onClick={toggleSidebar}>
                {isSidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
              </Button>
              <div className="ml-auto flex gap-2">
                <ThemeToggle />
                <ArtifactPanelToggleButton />
              </div>
            </header>
            <main className="flex-grow overflow-y-auto bg-background">
              {children}
            </main>
          </div>
        </div>
      ) : (
        <div className="min-h-screen flex flex-col bg-background">
          <header className="flex h-14 items-center gap-4 bg-card px-4 sticky top-0 z-10 rounded-none">
            <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon">
                  <PanelLeftOpen className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="flex flex-col p-0 w-72 border-r-0">
                <Sidebar isCollapsed={false} onLinkClick={() => setIsMobileMenuOpen(false)} />
              </SheetContent>
            </Sheet>
            <div className="w-full flex-1 flex items-center"> {/* Añadido flex y items-center para centrado vertical */}
              <Image src="/logo-simple.png" alt="Kognito Logo" width={50} height={50} className="mr-2" /> {/* Aumentado tamaño y añadido margen derecho */}
              {/* El texto que sigue al logo se beneficiaría de estar aquí o en un span para control de espaciado */}
            </div>
            <div className="ml-auto flex gap-2">
              <ThemeToggle />
              <ArtifactPanelToggleButton />
            </div>
          </header>
          <main className="flex-grow">
            {children}
          </main>
        </div>
      )}
    </LoadingProvider>
  );
}

function ArtifactPanelToggleButton() {
  const { isVisible, toggleVisibility } = useArtifactPanel();
  return (
    <Button variant="outline" size="icon" onClick={toggleVisibility}>
      {isVisible ? <PanelRightClose className="h-5 w-5" /> : <PanelRightOpen className="h-5 w-5" />}
    </Button>
  );
}
