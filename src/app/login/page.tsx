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
        <Input id="telegram-id" value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="@tu_usuario" className="bg-muted/30 border-0 rounded-2xl h-12 focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all placeholder:text-muted-foreground/50" autoComplete="off" />
      </div>
      {error && <p className="text-sm text-accent">{error}</p>}
      <Button type="submit" className="w-full h-12 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200" disabled={isSubmitting}>
        {isSubmitting ? 'Enviando...' : 'Enviar Código a Telegram'}
      </Button>
    </form>
  );
};

// --- Sub-componente para el formulario de Verificación de Código ---
const VerifyCodeForm = ({ identifier, onVerify, setView, isProcessing }: { identifier: string; onVerify: (token: string) => void; setView: (view: { type: string; identifier?: string }) => void; isProcessing: boolean }) => {
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
            <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" maxLength={6} autoFocus className="bg-muted/30 border-0 rounded-2xl h-12 focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all placeholder:text-muted-foreground/50 text-center text-lg tracking-widest" autoComplete="off" />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full h-12 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-200" disabled={isSubmitting || isProcessing}>
            {isSubmitting ? 'Verificando...' : isProcessing ? 'Ingresando...' : 'Verificar e Ingresar'}
          </Button>
          <Button variant="ghost" onClick={() => setView({ type: 'login' })} className="w-full h-12 rounded-2xl hover:bg-muted/50 transition-all duration-200">
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
    router.push('/chat');
  };

  return (
    <main className="flex items-center justify-center min-h-screen bg-background p-4">
      <div className="w-full max-w-md">
        <Card className="backdrop-blur-xl bg-card/80 border-0 shadow-2xl rounded-3xl overflow-hidden">
          <CardHeader className="text-center space-y-6 pt-8 pb-6">
            <Image src="/logo-completo-dark2.png" alt="Kognito AI Labs" width={320} height={110} className="mx-auto" />
          </CardHeader>
          <CardContent className="px-8 pb-8">
          {globalError && <p className="text-sm text-destructive text-center mb-4">{globalError}</p>}

          {view.type === 'login' && (
            <div className="space-y-4">
              {/* Aquí iría el botón de Telegram Widget si se reactiva */}
              
              <div className="relative">
                <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-muted/30" /></div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-4 py-1 text-muted-foreground rounded-full">Login con Telegram</span>
                </div>
              </div>
              <TelegramCodeForm setView={setView} />
              
              <div className="relative">
                <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-muted/30" /></div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-4 py-1 text-muted-foreground rounded-full">O con Email</span>
                </div>
              </div>
              <EmailLoginForm onLogin={handleSuccessfulLogin} isSubmitting={isProcessing} setParentError={setGlobalError} />
              <div className="text-center text-sm text-muted-foreground">
                ¿No tienes una cuenta?{' '}
                <a href="/register" className="text-primary hover:text-primary/80 font-medium transition-colors">
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
              isProcessing={isProcessing}
            />
          )}
        </CardContent>
        </Card>
      </div>
    </main>
  );
}
