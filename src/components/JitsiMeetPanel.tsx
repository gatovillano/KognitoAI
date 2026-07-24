'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import NextImage from 'next/image';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import {
  Video,
  Plus,
  Trash2,
  ExternalLink,
  Copy,
  CheckCircle2,
  Clock,
  Shield,
  Users,
  X,
} from 'lucide-react';

const JITSI_DOMAIN = process.env.NEXT_PUBLIC_JITSI_DOMAIN || 'meet.kognitoai.cloud';
const JITSI_DOMAIN_CLEAN = JITSI_DOMAIN.replace(/^(https?:\/\/)/, '');
const JITSI_PROTOCOL = JITSI_DOMAIN.startsWith('http://')
  ? 'http'
  : (JITSI_DOMAIN.startsWith('https://')
      ? 'https'
      : (typeof window !== 'undefined' ? window.location.protocol.replace(':', '') : 'https')
    );

interface JitsiRoom {
  id: string;
  album_id: string | null;
  account_id: string;
  room_name: string;
  display_name: string | null;
  has_password: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  album: {
    id: string;
    name: string;
    description: string;
    created_at: string;
    updated_at: string;
  } | null;
}

export const JitsiMeetPanel: React.FC = () => {
  const [rooms, setRooms] = useState<JitsiRoom[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [roomPassword, setRoomPassword] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeRoom, setActiveRoom] = useState<JitsiRoom | null>(null);
  const [jitsiApi, setJitsiApi] = useState<any>(null);

  const handleCloseRoom = useCallback(() => {
    if (jitsiApi) {
      jitsiApi.dispose();
      setJitsiApi(null);
    }
    setActiveRoom(null);
  }, [jitsiApi]);

  useEffect(() => {
    if (!activeRoom) return;

    let apiInstance: any = null;

    const initJitsi = () => {
      const domain = JITSI_DOMAIN_CLEAN;
      const options = {
        roomName: activeRoom.room_name,
        width: '100%',
        height: '100%',
        parentNode: document.querySelector('#jitsi-iframe-container'),
        configOverwrite: {
          startWithAudioMuted: true,
          startWithVideoMuted: true,
        },
        interfaceConfigOverwrite: {},
      };
      
      // @ts-ignore
      if (window.JitsiMeetExternalAPI) {
        // @ts-ignore
        apiInstance = new window.JitsiMeetExternalAPI(domain, options);
        setJitsiApi(apiInstance);
      } else {
        toast.error('No se pudo inicializar la API de Jitsi Meet.');
      }
    };

    const scriptId = 'jitsi-external-api-script';
    const existingScript = document.getElementById(scriptId);

    if (!existingScript) {
      const script = document.createElement('script');
      script.id = scriptId;
      script.src = `${JITSI_PROTOCOL}://${JITSI_DOMAIN_CLEAN}/external_api.js`;
      script.async = true;
      script.onload = initJitsi;
      script.onerror = () => {
        toast.error('Error al cargar la librería de Jitsi Meet.');
      };
      document.body.appendChild(script);
    } else {
      // @ts-ignore
      if (window.JitsiMeetExternalAPI) {
        initJitsi();
      } else {
        existingScript.addEventListener('load', initJitsi);
      }
    }

    return () => {
      if (apiInstance) {
        apiInstance.dispose();
      }
    };
  }, [activeRoom]);

  const fetchRooms = useCallback(async () => {
    try {
      const res = await apiClient.get<JitsiRoom[]>('/api/meet/rooms');
      setRooms(res.data);
    } catch (e) {
      console.error(e);
      toast.error('Error al cargar las salas de Jitsi Meet.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRooms();
  }, [fetchRooms]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim()) {
      toast.error('Por favor, ingresa un título para la reunión.');
      return;
    }
    setCreating(true);
    try {
      const payload: any = {
        is_active: true,
        display_name: displayName.trim(),
      };
      if (roomPassword.trim()) payload.password = roomPassword.trim();

      const res = await apiClient.post<JitsiRoom>('/api/meet/rooms', payload);
      toast.success('Sala de Jitsi Meet creada.');
      setRooms((prev) => [res.data, ...prev]);
      setDisplayName('');
      setRoomPassword('');
    } catch (e) {
      console.error(e);
      toast.error('No se pudo crear la sala.');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('¿Eliminar esta sala de Jitsi Meet?')) return;
    try {
      await apiClient.delete(`/api/meet/rooms/${id}`);
      toast.success('Sala eliminada.');
      setRooms((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      console.error(e);
      toast.error('Error al eliminar la sala.');
    }
  };

  const copyRoomLink = async (room: JitsiRoom) => {
    const link = `${JITSI_PROTOCOL}://${JITSI_DOMAIN_CLEAN}/${room.room_name}`;
    try {
      await navigator.clipboard.writeText(link);
      setCopiedId(room.id);
      toast.success('Enlace copiado al portapapeles.');
      setTimeout(() => setCopiedId(null), 2000);
    } catch (e) {
      console.error(e);
      toast.error('No se pudo copiar el enlace.');
    }
  };

  const openRoom = (room: JitsiRoom) => {
    setActiveRoom(room);
  };

  return (
    <div className="space-y-6">
      {activeRoom && (
        <Card className="border-2 border-primary/30 shadow-xl overflow-hidden bg-background/95 backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between py-3 border-b">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
              <CardTitle className="text-base font-semibold">
                Reunión Activa: {activeRoom.display_name || activeRoom.room_name}
              </CardTitle>
            </div>
            <Button variant="ghost" size="icon" onClick={handleCloseRoom} className="h-8 w-8 rounded-full">
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="p-0 h-[600px] bg-black">
            <div id="jitsi-iframe-container" className="w-full h-full" />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Video className="h-5 w-5" />
            Módulo Jitsi Meet
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Crea y administra salas de videoconferencia en tiempo real. Las salas usan tu propio
            servidor Jitsi configurado en KognitoAI.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="grid gap-4 md:grid-cols-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Título de la reunión</label>
              <input
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                placeholder="Ej. Reunión Semanal"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Contraseña</label>
              <input
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                placeholder="Opcional"
                value={roomPassword}
                onChange={(e) => setRoomPassword(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={creating} className="w-full gap-2">
                <Plus className="h-4 w-4" />
                {creating ? 'Creando...' : 'Crear sala'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-muted-foreground">Salas creadas</h3>
          <Button variant="outline" size="sm" onClick={fetchRooms} className="gap-2">
            <Clock className="h-4 w-4" />
            Actualizar
          </Button>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando salas...</p>
        ) : rooms.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay salas creadas aún.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence>
              {rooms.map((room) => (
                <motion.div
                  key={room.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 8 }}
                  className="rounded-xl border bg-background/60 p-4 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">{room.display_name || 'Sala sin nombre'}</p>
                      <p className="text-xs text-muted-foreground font-mono break-all">{room.room_name}</p>
                      {room.album && (
                        <p className="text-xs text-muted-foreground">
                          Álbum: {room.album.name || room.album.id}
                        </p>
                      )}
                    </div>
                    <Badge variant={room.is_active ? 'default' : 'secondary'} className="text-[11px]">
                      {room.is_active ? 'Activa' : 'Inactiva'}
                    </Badge>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openRoom(room)}
                      className="gap-2"
                    >
                      <ExternalLink className="h-4 w-4" />
                      Abrir sala
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyRoomLink(room)}
                      className="gap-2"
                    >
                      {copiedId === room.id ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Copiado
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4" />
                          Copiar link
                        </>
                      )}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDelete(room.id)}
                      className="gap-2"
                    >
                      <Trash2 className="h-4 w-4" />
                      Eliminar
                    </Button>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Shield className="h-3 w-3" />
                      {room.has_password ? 'Con contraseña' : 'Sin contraseña'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      Jitsi Meet
                    </span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};
