'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await apiClient.post('/api/auth/register', {
        name,
        email,
        password,
      });

      if (response.data.token) {
        // No almacenamos el token aquí, el usuario debe iniciar sesión
        toast.success('Cuenta creada con éxito', {
          description: 'Ahora puedes iniciar sesión.',
          action: {
            label: 'Iniciar Sesión',
            onClick: () => router.push('/login'),
          },
          duration: 5000, // Duración para que el usuario pueda leer el mensaje y hacer clic
        });
        // No redirigimos automáticamente, el usuario debe iniciar sesión
      } else {
        toast.error('Error en el registro', {
          description: 'No se recibió un token de autenticación.',
        });
      }
    } catch (error: any) {
      console.error('Registration error:', error);
      if (error.response?.status === 409) {
        toast.error('Correo ya registrado', {
          description: 'Ya existe una cuenta con este correo. ¿Quieres iniciar sesión?',
          action: {
            label: 'Iniciar Sesión',
            onClick: () => router.push('/login'),
          },
        });
      } else {
        toast.error('Error en el registro', {
          description: error.response?.data?.error || 'Hubo un problema al crear tu cuenta.',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center py-2 bg-background">
      <Card className="w-full max-w-md backdrop-blur-xl bg-card/80 border-0 shadow-2xl rounded-3xl overflow-hidden">
        <CardHeader>
          <CardTitle>Crear una cuenta</CardTitle>
          <CardDescription>Regístrate para acceder a la plataforma</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nombre</Label>
              <Input
                id="name"
                type="text"
                placeholder="Tu nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-muted/30 border-0 rounded-2xl h-12 focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all placeholder:text-muted-foreground/50"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Correo electrónico</Label>
              <Input
                id="email"
                type="email"
                placeholder="tu@ejemplo.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-muted/30 border-0 rounded-2xl h-12 focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all placeholder:text-muted-foreground/50"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-muted/30 border-0 rounded-2xl h-12 focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all placeholder:text-muted-foreground/50"
                required
                minLength={6}
              />
            </div>
            <Button type="submit" className="w-full h-12 rounded-2xl" disabled={isLoading}>
              {isLoading ? 'Registrando...' : 'Registrarse'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-muted-foreground">
            ¿Ya tienes una cuenta?{' '}
            <a href="/login" className="text-primary hover:underline">
              Inicia sesión
            </a>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
