'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useMediaQuery } from '@uidotdev/usehooks';
import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { PanelLeftOpen } from 'lucide-react';
import { LoadingProvider } from '@/contexts/LoadingContext';
import { SearchProvider } from '@/contexts/SearchContext';
import { useTaskContext } from '@/contexts/TaskContext';
import UploadProgressIndicator from './UploadProgressIndicator';
import GraphProgressIndicator from './GraphProgressIndicator';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { uploadTasks, analysisTasks, removeAnalysisTask } = useTaskContext();
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const pathname = usePathname();
  const isChatContext = pathname?.includes('/chat/');

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Resizable sidebar
  const SIDEBAR_MIN = 180;
  const SIDEBAR_MAX = 480;
  const SIDEBAR_DEFAULT = 288; // 72 * 4 = w-72 equivalent
  const SIDEBAR_COLLAPSED_WIDTH = 64; // w-16 equivalent (64px)
  const COLLAPSE_THRESHOLD = 140;
  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT);
  const isDraggingSidebar = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(SIDEBAR_DEFAULT);
  const [isDraggingActive, setIsDraggingActive] = useState(false);

  const toggleSidebar = () => {
    if (isSidebarCollapsed) {
      setIsSidebarCollapsed(false);
      setSidebarWidth(SIDEBAR_DEFAULT);
    } else {
      setIsSidebarCollapsed(true);
    }
  };

  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingSidebar.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = isSidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : sidebarWidth;
    setIsDraggingActive(true);
  }, [isSidebarCollapsed, sidebarWidth]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingSidebar.current) return;
      const delta = e.clientX - dragStartX.current;
      const newWidth = dragStartWidth.current + delta;

      if (newWidth < COLLAPSE_THRESHOLD) {
        setIsSidebarCollapsed(true);
      } else {
        setIsSidebarCollapsed(false);
        const clampedWidth = Math.min(Math.max(newWidth, SIDEBAR_MIN), SIDEBAR_MAX);
        setSidebarWidth(clampedWidth);
      }
    };

    const handleMouseUp = () => {
      if (isDraggingSidebar.current) {
        isDraggingSidebar.current = false;
        setIsDraggingActive(false);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  return (
    <LoadingProvider>
      <SearchProvider>
        <div className="h-screen bg-background overflow-hidden flex font-sans selection:bg-primary/20 selection:text-primary relative">
          {/* Gradiente de fondo sutil para profundidad - ahora cubre toda la pantalla */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 pointer-events-none z-0" />

          {/* Sidebar para desktop (fijo en md y superior) */}
          <aside
            className="hidden md:flex h-full flex-shrink-0 z-10 items-stretch border-r border-border/30 bg-card/30 backdrop-blur-xl"
            style={{
              width: isSidebarCollapsed ? `${SIDEBAR_COLLAPSED_WIDTH}px` : `${sidebarWidth}px`,
              transition: isDraggingActive ? 'none' : 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          >
            <div className="h-full flex-1 overflow-hidden">
              <Sidebar
                isCollapsed={isSidebarCollapsed}
                showToolText={!isSidebarCollapsed}
                onToggleCollapse={toggleSidebar}
              />
            </div>
            {/* Resize handle */}
            <div
              onMouseDown={handleResizeMouseDown}
              className="group relative flex items-center justify-center w-2 flex-shrink-0 cursor-col-resize select-none border-r border-border/20 hover:border-primary/40 transition-colors"
              title="Arrastrar para redimensionar"
            >
              <div
                className={`absolute inset-y-6 w-[2px] rounded-full transition-all duration-200 ${
                  isDraggingActive
                    ? 'bg-primary scale-y-100 opacity-100'
                    : 'bg-border/50 opacity-0 group-hover:opacity-100 group-hover:bg-primary/40'
                }`}
              />
            </div>
          </aside>

          {/* Botón de menú flotante para móvil (visible en pantallas < md) */}
          <div className="md:hidden fixed top-3 left-3 z-40">
            <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-9 w-9 rounded-xl bg-background/80 backdrop-blur-md border-border/40 shadow-sm hover:bg-primary/10 hover:text-primary transition-all"
                  title="Abrir menú"
                >
                  <PanelLeftOpen className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="flex flex-col p-0 w-72 border-r border-border/30 bg-background/95 backdrop-blur-2xl">
                <div className="h-full w-full overflow-hidden">
                  <Sidebar
                    isCollapsed={false}
                    showToolText={true}
                    onLinkClick={() => setIsMobileMenuOpen(false)}
                    onToggleCollapse={() => setIsMobileMenuOpen(false)}
                  />
                </div>
              </SheetContent>
            </Sheet>
          </div>

          {/* Contenido principal sin barra superior */}
          <div className="flex-1 flex flex-col min-w-0 h-full relative z-10 transition-all duration-300">
            <main className={`flex-1 relative z-0 h-full ${isChatContext ? 'overflow-hidden p-0' : 'p-2 md:p-6 lg:p-8 overflow-y-auto custom-scrollbar'}`}>
              <div className={isChatContext ? 'h-full w-full' : 'w-full mx-auto h-full'}>
                {children}
              </div>
            </main>
          </div>
        </div>

        {/* Global Task Progress Indicators */}
        {(uploadTasks.length > 0 || analysisTasks.length > 0) && (
          <div className="fixed bottom-6 right-6 z-[100] w-80 space-y-4">
            {uploadTasks.length > 0 && <UploadProgressIndicator tasks={uploadTasks} />}
            {analysisTasks.length > 0 && (
              <GraphProgressIndicator 
                tasks={analysisTasks} 
                onDismiss={(taskId) => removeAnalysisTask(taskId)} 
              />
            )}
          </div>
        )}

        {/* <GlobalDeepResearchGraph /> */}
      </SearchProvider>
    </LoadingProvider>
  );
}
