// En: src/app/login/page.tsx (versión refactorizada y completa)
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import Image from 'next/image';
import Script from 'next/script';

// --- Sub-componente para el botón de Telegram Widget ---
const TelegramLoginWidget = ({ onLogin, isProcessing }: { onLogin: (token: string) => void; isProcessing: boolean }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Función que se ejecuta cuando el usuario se autentica con Telegram
    (window as any).onTelegramAuth = async (user: any) => {
      try {
        setError('');
        const response = await apiClient.post('/api/auth/telegram/callback', user);
        onLogin(response.data.access_token);
      } catch (err: any) {
        console.error('Error en autenticación de Telegram:', err);
        setError(err.response?.data?.detail || err.message || 'Error en la autenticación de Telegram');
      }
    };

    return () => {
      delete (window as any).onTelegramAuth;
    };
  }, [onLogin]);

  useEffect(() => {
    // Cargar el script de Telegram y crear el widget dinámicamente
    if (typeof window !== 'undefined') {
      const script = document.createElement('script');
      script.src = 'https://telegram.org/js/telegram-widget.js?22';
      script.async = true;
      script.onload = () => {
        setIsLoaded(true);
        // Crear el widget dinámicamente después de que el script se haya cargado
        setTimeout(() => {
          const widgetContainer = document.getElementById('telegram-widget-container');
          if (widgetContainer) {
            widgetContainer.innerHTML = '';
            const widget = document.createElement('script');
            widget.async = true;
            widget.src = 'https://telegram.org/js/telegram-widget.js?22';
            widget.setAttribute('data-telegram-login', 'KognitoAIBot');
            widget.setAttribute('data-size', 'large');
            widget.setAttribute('data-onauth', 'onTelegramAuth(user)');
            widget.setAttribute('data-request-access', 'write');
            widgetContainer.appendChild(widget);
          }
        }, 100);
      };
      document.head.appendChild(script);

      return () => {
        if (document.head.contains(script)) {
          document.head.removeChild(script);
        }
      };
    }
  }, []);

  return (
    <div className="space-y-2">
      <div id="telegram-widget-container" className="flex justify-center">
        {!isLoaded && (
          <Button
            disabled
            className="w-full h-12 rounded-2xl bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium shadow-lg"
          >
            Cargando Telegram...
          </Button>
        )}
      </div>
      {error && <p className="text-sm text-destructive text-center">{error}</p>}
    </div>
  );
};

// --- Sub-componente para el formulario de Email/Password ---
const EmailLoginForm = ({ onLogin, setParentError }: { onLogin: (token: string) => void; setParentError: (error: string) => void }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false); // Manejar el estado de envío internamente

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true); // Iniciar el envío
    setParentError(''); // Limpiar errores previos
    try {
      const response = await apiClient.post('/api/auth/login', { email, password });
      onLogin(response.data.access_token);
    } catch (err: any) {
      setParentError(err.response?.data?.detail || 'Email o contraseña incorrectos.');
      console.error(err);
    } finally {
      setIsSubmitting(false); // Finalizar el envío, independientemente del resultado
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="bg-muted/30 border-0 rounded-2xl h-12 focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all placeholder:text-muted-foreground/50" placeholder="tu@email.com" autoComplete="off" required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Contraseña</Label>
        <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="bg-muted/30 border-0 rounded-2xl h-12 focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all placeholder:text-muted-foreground/50" placeholder="••••••••" autoComplete="new-password" required />
      </div>
      <Button type="submit" className="w-full h-12 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200" disabled={isSubmitting}>
        {isSubmitting ? 'Ingresando...' : 'Iniciar Sesión con Email'}
      </Button>
    </form>
  );
};




// --- Componente Principal de la Página de Login ---
export default function LoginPage() {
  const [view, setView] = useState<{ type: string; identifier?: string }>({ type: 'login', identifier: '' });
  const [isProcessing, setIsProcessing] = useState(false);
  const [globalError, setGlobalError] = useState('');
  const router = useRouter();
  const { login } = useAuth();

  const handleSuccessfulLogin = async (token: string) => {
    setIsProcessing(true);
    setGlobalError('');
    try {
      await login(token);
      router.push('/chat');
    } catch (err: any) {
      setGlobalError(err.message || 'Error al iniciar sesión.');
      console.error('Error en handleSuccessfulLogin:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <main className="flex items-center justify-center min-h-screen bg-background p-4">
      <div className="w-full max-w-md">
        <Card className="backdrop-blur-xl bg-card/80 border-0 shadow-2xl rounded-3xl overflow-hidden">
          <CardHeader className="text-center space-y-6 pt-8 pb-6">
            <Image src="/logo-completo-dark2.png" alt="Kognito AI Labs" width={320} height={110} className="mx-auto" />
          </CardHeader>
          <CardContent className="px-8 pb-8">
            {isProcessing ? (
              <div className="flex flex-col items-center justify-center space-y-2 py-12">
                <p className="text-lg font-medium text-primary animate-pulse">Ingresando...</p>
                <p className="text-sm text-muted-foreground">Por favor, espera un momento.</p>
              </div>
            ) : (
              <>
                {globalError && <p className="text-sm text-destructive text-center mb-4">{globalError}</p>}

                {view.type === 'login' && (
                  <div className="space-y-4">
                    {/* Botón de Telegram Widget */}
                    <TelegramLoginWidget onLogin={handleSuccessfulLogin} isProcessing={isProcessing} />

                    <div className="relative">
                      <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-muted/30" /></div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-card px-4 py-1 text-muted-foreground rounded-full">O con Email</span>
                      </div>
                    </div>
                    <EmailLoginForm onLogin={handleSuccessfulLogin} setParentError={setGlobalError} />
                    <div className="text-center text-sm text-muted-foreground">
                      ¿No tienes una cuenta?{' '}
                      <a href="/register" className="text-primary hover:text-primary/80 font-medium transition-colors">
                        Regístrate
                      </a>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
