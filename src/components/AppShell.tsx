'use client';

import React, { useState } from 'react';
import { useMediaQuery } from '@uidotdev/usehooks';
import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import Image from 'next/image';
import { ThemeToggle } from './ThemeToggle'; // Importamos el botón de tema
import { LoadingProvider } from '@/contexts/LoadingContext';
import { SearchProvider, useSearch } from '@/contexts/SearchContext';
import { useArtifactPanel } from '@/contexts/ArtifactPanelContext';
import { PanelRightOpen, PanelRightClose } from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const pathname = usePathname();
  const isChatContext = pathname.includes('/chat/');
  
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  return (
    <LoadingProvider>
      <SearchProvider>
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
              <div className="ml-auto flex gap-2 items-center">
                {isChatContext && (
                  <div className="relative">
                    <SearchInput />
                  </div>
                )}
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
              {isChatContext && (
                <div className="relative">
                  <SearchInput />
                </div>
              )}
            </div>
            <div className="ml-auto flex gap-2 items-center">
              <ThemeToggle />
              <ArtifactPanelToggleButton />
            </div>
          </header>
          <main className="flex-grow">
            {children}
          </main>
        </div>
      )}
    </SearchProvider>
    </LoadingProvider>
  );
}

function SearchInput() {
  const { searchTerm, setSearchTerm } = useSearch();
  return (
    <>
      <input
        type="text"
        placeholder="Buscar en el chat..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="pl-8 pr-2 py-1 border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
      />
      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    </>
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
