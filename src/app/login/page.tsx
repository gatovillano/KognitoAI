// En: src/app/login/page.tsx (versión refactorizada y completa)
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import Image from 'next/image';

// --- Sub-componente para el formulario de Email/Password ---
const EmailLoginForm = ({ onLogin, isSubmitting, setParentError }: { onLogin: (token: string) => void; isSubmitting: boolean; setParentError: (error: string) => void }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await apiClient.post('/api/auth/login', { email, password });
      onLogin(response.data.access_token);
    } catch (err) {
      setParentError('Email o contraseña incorrectos.');
      console.error(err);
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Contraseña</Label>
        <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </div>
      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Ingresando...' : 'Iniciar Sesión con Email'}
      </Button>
    </form>
  );
};

// --- Sub-componente para el formulario de Código de Telegram ---
const TelegramCodeForm = ({ setView }: { setView: (view: { type: string; identifier?: string }) => void }) => {
  const [identifier, setIdentifier] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim()) {
      setError('Por favor, introduce tu ID o @usuario de Telegram.');
      return;
    }
    setError('');
    setIsSubmitting(true);
    try {
      await apiClient.post('/api/auth/request-code', { identifier });
      setView({ type: 'verifyCode', identifier }); // Pasa a la siguiente vista con el identificador
    } catch (err: any) {
      setError(err.response?.data?.detail || 'No se pudo enviar el código.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleRequestCode} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="telegram-id">ID o @usuario de Telegram</Label>
        <Input id="telegram-id" value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="@tu_usuario" />
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" variant="secondary" disabled={isSubmitting}>
        {isSubmitting ? 'Enviando...' : 'Enviar Código a Telegram'}
      </Button>
    </form>
  );
};

// --- Sub-componente para el formulario de Verificación de Código ---
const VerifyCodeForm = ({ identifier, onVerify, setView }: { identifier: string; onVerify: (token: string) => void; setView: (view: { type: string; identifier?: string }) => void }) => {
    const [code, setCode] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');

    const handleVerifyCode = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!code.trim()) {
          setError('Por favor, introduce el código de 6 dígitos.');
          return;
        }
        setError('');
        setIsSubmitting(true);
        try {
          const response = await apiClient.post('/api/auth/verify-code', { identifier, code });
          onVerify(response.data.access_token);
        } catch (err: any) {
          setError(err.response?.data?.detail || 'Código incorrecto o expirado.');
        } finally {
            setIsSubmitting(false);
        }
      };

    return (
        <form onSubmit={handleVerifyCode} className="space-y-4">
          <p className="text-sm text-center text-muted-foreground">
            Enviamos un código a <strong>{identifier}</strong>. Revisa tu chat de Telegram.
          </p>
          <div className="space-y-2">
            <Label htmlFor="code">Código de Verificación</Label>
            <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" maxLength={6} autoFocus />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Verificando...' : 'Verificar e Ingresar'}
          </Button>
          <Button variant="link" onClick={() => setView({ type: 'login' })} className="w-full h-auto p-1">
            Volver
          </Button>
        </form>
    );
}

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
    await login(token);
    router.push('/');
  };

  return (
    <main className="flex items-center justify-center min-h-screen bg-background p-4">
      <Card className="w-full max-w-sm border-primary/20">
        <CardHeader className="text-center space-y-2">
          <Image src="/logo-completo.png" alt="Kognito AI Labs" width={120} height={120} className="mx-auto" />
          <CardTitle className="text-2xl">Bienvenido</CardTitle>
          <CardDescription>
            {view.type === 'login' ? 'Ingresa a tu exocerebro digital' : 'Introduce el código que recibiste'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {globalError && <p className="text-sm text-destructive text-center mb-4">{globalError}</p>}

          {view.type === 'login' && (
            <div className="space-y-4">
              {/* Aquí iría el botón de Telegram Widget si se reactiva */}
              
              <div className="relative">
                <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">Login con Telegram</span>
                </div>
              </div>
              <TelegramCodeForm setView={setView} />
              
              <div className="relative">
                <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">O con Email</span>
                </div>
              </div>
              <EmailLoginForm onLogin={handleSuccessfulLogin} isSubmitting={isProcessing} setParentError={setGlobalError} />
              <div className="text-center text-sm text-muted-foreground">
                ¿No tienes una cuenta?{' '}
                <a href="/register" className="text-primary hover:underline">
                  Regístrate
                </a>
              </div>
            </div>
          )}

          {view.type === 'verifyCode' && view.identifier && (
            <VerifyCodeForm
              identifier={view.identifier}
              onVerify={handleSuccessfulLogin}
              setView={setView}
            />
          )}
        </CardContent>
      </Card>
    </main>
  );
}
