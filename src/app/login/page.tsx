// En: src/app/login/page.tsx
'use client';

import { useState, useEffect, useRef } from 'react';
import Script from 'next/script';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import Image from 'next/image';

// Definimos una interfaz para los datos que esperamos de Telegram
interface TelegramUserData {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

// Extendemos la interfaz de Window para incluir la propiedad Telegram
interface Window {
  Telegram?: {
    Login?: {
      auth: (options: { bot_id: string; widget_version: string; request_access: string; onauth: (user: TelegramUserData) => void }, element: HTMLElement) => void;
    };
  };
}

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();
  const { login } = useAuth();
  const telegramLoginButtonRef = useRef<HTMLDivElement>(null); // Ref para el div del botón de Telegram

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      // Llamamos al endpoint de login del backend
      const response = await apiClient.post('/api/auth/login', { email, password });
      // Si tiene éxito, el AuthContext se encarga de todo
      await login(response.data.access_token);
      // Y redirigimos a la página principal
      router.push('/');
    } catch (err) {
      setError('Email o contraseña incorrectos. Por favor, inténtalo de nuevo.');
      console.error(err);
      setIsSubmitting(false);
    }
  };

  // Esta función se llamará cuando el script de Telegram nos devuelva los datos del usuario
  const handleTelegramLogin = async (user: TelegramUserData) => {
    setIsSubmitting(true);
    setError('');
    try {
      // Llamamos a nuestro endpoint de backend para verificar los datos y obtener el token JWT
      const response = await apiClient.post('/api/auth/telegram/callback', user);
      await login(response.data.access_token);
      router.push('/');
    } catch (err: any) {
      console.error('Telegram login failed', err);
      setError(err.response?.data?.detail || 'El login con Telegram falló.');
      setIsSubmitting(false);
    }
  };
  
  // Esto es para adjuntar la función de callback global que el script de Telegram espera
  useEffect(() => {
    (window as any).onTelegramAuth = handleTelegramLogin;
    
    // Limpieza al desmontar el componente
    return () => {
      delete (window as any).onTelegramAuth;
    };
  }, []);

  return (
    <>
      {/* NUEVO SCRIPT */}
      <Script
        src="https://telegram.org/js/telegram-widget.js?22"
        strategy="afterInteractive"
        onLoad={() => {
          // Esta función se ejecuta cuando el script ha cargado
          const telegramWindow = window as any;
          if (telegramWindow.Telegram && telegramLoginButtonRef.current) {
            telegramWindow.Telegram.Login.auth(
              {
                bot_id: '7308374590',
                widget_version: '22',
                request_access: 'write',
                onauth: (user: TelegramUserData) => (window as any).onTelegramAuth(user),
              },
              telegramLoginButtonRef.current
            );
          }
        }}
      />
      <main className="flex items-center justify-center min-h-screen bg-background p-4">
        <Card className="w-full max-w-sm border-primary/20">
          <CardHeader className="text-center space-y-2">
            <Image src="/logo-completo.png" alt="Kognito AI Labs" width={120} height={120} className="mx-auto" />
            <CardTitle className="text-2xl">Bienvenido</CardTitle>
            <CardDescription>Ingresa a tu exocerebro digital</CardDescription>
          </CardHeader>
          <CardContent>
            {/* NUEVO BOTÓN DE TELEGRAM */}
            <div ref={telegramLoginButtonRef} className="mb-4 min-h-[50px]">
              {/* El script de Telegram reemplazará este div con el botón */}
              <p className="text-sm text-muted-foreground">Iniciar sesión con Telegram</p>
            </div>
            
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">O continúa con</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Contraseña</Label>
                <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Ingresando...' : 'Iniciar Sesión'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
