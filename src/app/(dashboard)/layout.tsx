// En: src/app/(dashboard)/layout.tsx
'use client';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { useAuth } from "@/contexts/AuthContext";
import { Toaster } from '@/components/ui/sonner';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  // Mientras carga, o si no hay usuario, muestra un loader o nada
  if (isLoading || !user) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <p>Cargando...</p> {/* O un spinner bonito */}
      </div>
    );
  }

  return (
    <ResizablePanelGroup
      direction="horizontal"
      className="min-h-screen w-full"
    >
      <ResizablePanel defaultSize={20} minSize={15} maxSize={25}>
        <Sidebar />
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={80}>
      <main className="h-full p-6">
        {children}
      </main>
      <Toaster richColors />
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
