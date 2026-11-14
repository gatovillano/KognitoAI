'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Loader2, MessageCircle, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import apiClient from '@/lib/api';

interface RoomPublicInfo {
  id: string;
  name: string | null;
  room_type: string;
  is_group: boolean;
}

/**
 * Página pública de invitación a una sala de KognitoChat.
 * No requiere cuenta: el invitado solo ingresa su nombre y se crea
 * una cuenta temporal de invitado (endpoint guest-join).
 */
export default function JoinRoomPage() {
  const params = useParams();
  const roomId = params?.roomId as string;

  const [room, setRoom] = useState<RoomPublicInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!roomId) return;
    // Si ya hay sesión (usuario real o invitado previo), entrar directamente.
    if (localStorage.getItem('authToken')) {
      apiClient
        .post(`/api/kognito-chat/rooms/${roomId}/join`)
        .then(() => {
          window.location.href = `/kognito-chat?room=${roomId}`;
        })
        .catch(() => {
          // Token inválido/expirado: continuar como invitado nuevo
          localStorage.removeItem('authToken');
          loadRoom();
        });
    } else {
      loadRoom();
    }

    function loadRoom() {
      apiClient
        .get<RoomPublicInfo>(`/api/kognito-chat/rooms/${roomId}/public`)
        .then((res) => setRoom(res.data))
        .catch(() => setError('La sala no existe o el enlace no es válido.'))
        .finally(() => setLoading(false));
    }
  }, [roomId]);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setJoining(true);
    try {
      const res = await apiClient.post(`/api/kognito-chat/rooms/${roomId}/guest-join`, {
        name: name.trim(),
      });
      localStorage.setItem('authToken', res.data.access_token);
      window.location.href = `/kognito-chat?room=${roomId}`;
    } catch {
      setError('No se pudo unir a la sala. Intenta nuevamente.');
      setJoining(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            {error && !room ? (
              <AlertTriangle className="h-6 w-6 text-destructive" />
            ) : (
              <MessageCircle className="h-6 w-6 text-primary" />
            )}
          </div>
          <CardTitle>{room ? room.name || 'Sala de KognitoChat' : 'Enlace no válido'}</CardTitle>
          <CardDescription>
            {room ? 'Ingresa tu nombre para unirte. No necesitas una cuenta.' : error}
          </CardDescription>
        </CardHeader>
        {room && (
          <CardContent>
            <form onSubmit={handleJoin} className="space-y-3">
              <Input
                autoFocus
                placeholder="Tu nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={60}
              />
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={joining || !name.trim()}>
                {joining ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Unirme como invitado'}
              </Button>
            </form>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
