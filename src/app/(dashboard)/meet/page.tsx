'use client';

import React from 'react';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { JitsiMeetPanel } from '@/components/JitsiMeetPanel';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Video, Puzzle, Settings } from 'lucide-react';
import Link from 'next/link';

export default function MeetPage() {
  const { settings, loading } = useUserSettings();

  if (loading) {
    return (
      <div className="flex h-[60vh] w-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Cargando...</p>
        </div>
      </div>
    );
  }

  const isInstalled = settings?.installed_extensions?.includes('jitsi_meet');

  if (!isInstalled) {
    return (
      <div className="flex h-[70vh] w-full items-center justify-center px-4">
        <Card className="max-w-md w-full border border-primary/20 bg-card/60 backdrop-blur-xl shadow-2xl rounded-3xl overflow-hidden relative group">
          {/* Top aesthetic gradient bar */}
          <div className="h-2 w-full bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500" />
          
          <CardHeader className="text-center pt-8">
            <div className="mx-auto p-4 rounded-2xl bg-primary/10 text-primary w-fit mb-4 transition-transform group-hover:scale-110 duration-300">
              <Video className="h-10 w-10" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight text-foreground">
              Jitsi Meet no está activo
            </CardTitle>
            <CardDescription className="text-sm text-muted-foreground mt-2">
              Jitsi Meet es una extensión de videollamadas que te permite crear salas de reuniones y colaborar en tiempo real de forma segura.
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6 pb-8 pt-2">
            <div className="rounded-2xl bg-accent/40 p-4 border border-border/50 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                <Puzzle className="h-3.5 w-3.5" /> Características
              </h4>
              <ul className="text-xs text-muted-foreground space-y-1.5 list-disc list-inside">
                <li>Videoconferencias integradas de alta definición.</li>
                <li>Generación instantánea de salas de reunión.</li>
                <li>Protección por contraseña y control de accesos.</li>
                <li>Vinculación directa de salas a tus álbumes de fotos.</li>
              </ul>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link href="/settings?tab=extensions" passHref className="w-full">
                <Button className="w-full rounded-2xl bg-primary hover:bg-primary/95 text-primary-foreground font-medium flex items-center justify-center gap-2 py-5 shadow-lg shadow-primary/25 hover:shadow-primary/35 transition-all">
                  <Settings className="h-4 w-4" /> Ir a la Tienda de Extensiones
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Meet</h1>
        <p className="text-muted-foreground">
          Administra tus salas de Jitsi Meet y colabora en tiempo real.
        </p>
      </div>
      <JitsiMeetPanel />
    </div>
  );
}
