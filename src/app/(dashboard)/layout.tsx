'use client';

import React, { useEffect } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { AppShell } from '@/components/AppShell';
import { WorkspaceTitleProvider } from '@/contexts/WorkspaceTitleContext';
import { Toaster } from '@/components/ui/sonner';
import Image from 'next/image';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  if (isLoading || !user) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-2">
            <Image src="/logo-simple.png" alt="Kognito" width={40} height={40} className="animate-pulse" />
            <p className="text-muted-foreground">Cargando Kognito...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <DndProvider backend={HTML5Backend}>
        <WorkspaceTitleProvider>
          <AppShell>
            {React.isValidElement(children) ? children : null}
          </AppShell>
        </WorkspaceTitleProvider>
      </DndProvider>
      <Toaster richColors position="top-right" />
    </>
  );
}
