'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { AppShell } from '@/components/AppShell';
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
      <AppShell>{children}</AppShell>
      <Toaster richColors position="top-right" />
    </>
  );
}
