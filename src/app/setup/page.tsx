'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import apiClient from '@/lib/api';
import { User, Folder, Brain, CheckCircle2, ArrowRight, ArrowLeft, ShieldCheck, Zap, Image as ImageIcon, Globe, KeyRound } from 'lucide-react';

const LLM_PROVIDERS = [
  { id: 'gemini', name: 'Google AI Studio', env_key: 'GOOGLE_API_KEY' },
  { id: 'openai', name: 'OpenAI (GPT)', env_key: 'OPENAI_API_KEY' },
  { id: 'anthropic', name: 'Anthropic (Claude)', env_key: 'ANTHROPIC_API_KEY' },
  { id: 'openrouter', name: 'OpenRouter', env_key: 'OPENROUTER_API_KEY' },
  { id: 'ollama', name: 'Ollama (Local)', env_key: null },
  { id: 'ollama-cloud', name: '☁️ Ollama Cloud', env_key: 'OLLAMA_API_KEY' },
  { id: 'openai-compatible', name: '🖥️ Local AI / OpenAI Compatible', env_key: null },
  { id: 'mistral', name: 'Mistral AI', env_key: 'MISTRAL_API_KEY' },
  { id: 'nvidia', name: '🟢 NVIDIA AI Catalog', env_key: 'NVIDIA_API_KEY' },
];

const MODELS_BY_PROVIDER: Record<string, string[]> = {
  gemini: ['gemini/gemini-2.0-flash', 'gemini/gemini-1.5-flash', 'gemini/gemini-1.5-pro'],
  openai: ['openai/gpt-4o', 'openai/gpt-4o-mini', 'openai/gpt-4-turbo'],
  anthropic: ['anthropic/claude-3-5-sonnet-20240620', 'anthropic/claude-3-haiku-20240307'],
  openrouter: ['openrouter/google/gemini-2.5-flash-preview', 'openrouter/openai/gpt-4.1-mini'],
  ollama: ['ollama/llama3.1', 'ollama/mistral'],
  'ollama-cloud': ['ollama_chat/llama3.1', 'ollama_chat/mistral'],
  'openai-compatible': [],
  mistral: ['mistral/mistral-large-latest', 'mistral/mistral-small-latest'],
  nvidia: [
    'nvidia/meta/llama-3.3-70b-instruct',
    'nvidia/nvidia/llama-3.1-nemotron-70b-instruct',
    'nvidia/mistralai/mistral-large-2-instruct',
    'nvidia/deepseek-ai/deepseek-r1',
  ],
};

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  // Step 1: Admin user data
  const [adminData, setAdminData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  // Step 2: Storage path
  const [storageData, setStorageData] = useState({
    cloud_storage_path: '~/.kognito',
  });

  // Step 3: LLM & AI config
  const [llmData, setLlmData] = useState({
    llm_provider: 'gemini',
    llm_model: 'gemini/gemini-2.0-flash',
    fast_llm_provider: 'gemini',
    fast_llm_model: 'gemini/gemini-2.0-flash',
    vision_llm_provider: 'gemini',
    vision_llm_model: 'gemini/gemini-2.0-flash',
    llm_api_base: '',
    apiKey: '',
  });

  // Check if already initialized
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await apiClient.get('/api/auth/setup-status');
        if (res.data && res.data.is_initialized) {
          router.replace('/login');
        }
      } catch (err) {
        console.error('Error al verificar estado de inicialización:', err);
      }
    };
    checkStatus();
  }, [router]);

  const handleNextStep1 = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!adminData.name.trim() || !adminData.email.trim() || !adminData.password) {
      setError('Por favor completa todos los campos requeridos.');
      return;
    }
    if (adminData.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    if (adminData.password !== adminData.confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }
    setStep(2);
  };

  const handleNextStep2 = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!storageData.cloud_storage_path.trim()) {
      setError('Por favor especifica una ruta válida de almacenamiento.');
      return;
    }
    setStep(3);
  };

  const handleFinishSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Create initial admin account
      const payload = {
        name: adminData.name,
        email: adminData.email,
        password: adminData.password,
        cloud_storage_path: storageData.cloud_storage_path,
        llm_provider: llmData.llm_provider,
        llm_model: llmData.llm_model,
        fast_llm_provider: llmData.fast_llm_provider,
        fast_llm_model: llmData.fast_llm_model,
        vision_llm_provider: llmData.vision_llm_provider,
        vision_llm_model: llmData.vision_llm_model,
        llm_api_base: llmData.llm_api_base || undefined,
      };

      const res = await apiClient.post('/api/auth/setup-initial-admin', payload);
      const token = res.data.access_token;

      // If API key was provided for the selected provider, save secret
      if (llmData.apiKey && token) {
        const providerObj = LLM_PROVIDERS.find(p => p.id === llmData.llm_provider);
        if (providerObj && providerObj.env_key) {
          try {
            await apiClient.post(
              '/api/users/me/secrets',
              {
                key_name: providerObj.env_key,
                value: llmData.apiKey,
                description: `API Key inicial para ${providerObj.name}`,
              },
              { headers: { Authorization: `Bearer ${token}` } }
            );
          } catch (secretErr) {
            console.error('Error guardando API Key inicial:', secretErr);
          }
        }
      }

      setStep(4);
    } catch (err: any) {
      console.error('Error completando configuración inicial:', err);
      setError(err.response?.data?.detail || 'Error al completar la configuración inicial.');
    } finally {
      setLoading(false);
    }
  };

  const progressPercentage = (step / 4) * 100;

  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-muted/30 to-background p-4 md:p-8">
      <div className="w-full max-w-2xl space-y-6">
        {/* Header Branding */}
        <div className="text-center space-y-3">
          <Image src="/logo-completo-dark2.png" alt="Kognito AI Labs" width={280} height={90} className="mx-auto" priority />
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold uppercase tracking-wider">
            <ShieldCheck className="w-3.5 h-3.5" /> Asistente de Configuración Inicial
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground font-medium px-1">
            <span>Paso {step} de 4</span>
            <span>{step === 1 ? 'Administrador' : step === 2 ? 'Almacenamiento' : step === 3 ? 'Modelos IA' : 'Finalización'}</span>
          </div>
          <Progress value={progressPercentage} className="h-2 bg-muted/50 rounded-full overflow-hidden" />
        </div>

        {/* Wizard Card Container */}
        <Card className="backdrop-blur-xl bg-card/90 border-0 shadow-2xl rounded-3xl overflow-hidden transition-all duration-300">
          {error && (
            <div className="bg-destructive/10 border-l-4 border-destructive text-destructive text-sm p-4 mx-6 mt-6 rounded-r-xl font-medium">
              {error}
            </div>
          )}

          {/* STEP 1: ADMINISTRADOR */}
          {step === 1 && (
            <form onSubmit={handleNextStep1}>
              <CardHeader className="space-y-2 pt-8">
                <CardTitle className="text-2xl font-bold flex items-center gap-2">
                  <User className="w-6 h-6 text-primary" /> Crear Usuario Administrador
                </CardTitle>
                <CardDescription>
                  Este será el usuario principal con permisos totales para administrar la plataforma Kognito AI.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Nombre Completo / Usuario</Label>
                  <Input
                    id="name"
                    placeholder="Ej. Administrador Principal"
                    value={adminData.name}
                    onChange={(e) => setAdminData({ ...adminData, name: e.target.value })}
                    className="bg-muted/30 border-0 rounded-2xl h-12"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Correo Electrónico</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="admin@kognito.ai"
                    value={adminData.email}
                    onChange={(e) => setAdminData({ ...adminData, email: e.target.value })}
                    className="bg-muted/30 border-0 rounded-2xl h-12"
                    required
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="password">Contraseña</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={adminData.password}
                      onChange={(e) => setAdminData({ ...adminData, password: e.target.value })}
                      className="bg-muted/30 border-0 rounded-2xl h-12"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirmar Contraseña</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      placeholder="••••••••"
                      value={adminData.confirmPassword}
                      onChange={(e) => setAdminData({ ...adminData, confirmPassword: e.target.value })}
                      className="bg-muted/30 border-0 rounded-2xl h-12"
                      required
                    />
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-end pb-8 pt-4">
                <Button type="submit" className="h-12 px-8 rounded-2xl bg-primary hover:bg-primary/90 text-white font-medium gap-2">
                  Siguiente <ArrowRight className="w-4 h-4" />
                </Button>
              </CardFooter>
            </form>
          )}

          {/* STEP 2: ALMACENAMIENTO */}
          {step === 2 && (
            <form onSubmit={handleNextStep2}>
              <CardHeader className="space-y-2 pt-8">
                <CardTitle className="text-2xl font-bold flex items-center gap-2">
                  <Folder className="w-6 h-6 text-primary" /> Directorio de Almacenamiento Local (Nube)
                </CardTitle>
                <CardDescription>
                  Especifica la carpeta local del sistema donde se almacenarán y sincronizarán tus fotos, galerías y documentos de OnlyOffice.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="cloud_storage_path">Ruta del Directorio Local</Label>
                  <Input
                    id="cloud_storage_path"
                    placeholder="Ej. ~/.kognito o /home/usuario/MiNube"
                    value={storageData.cloud_storage_path}
                    onChange={(e) => setStorageData({ cloud_storage_path: e.target.value })}
                    className="bg-muted/30 border-0 rounded-2xl h-12 font-mono text-sm"
                    required
                  />
                </div>
                <div className="p-4 rounded-2xl bg-muted/20 border border-muted-foreground/10 space-y-2 text-xs text-muted-foreground leading-relaxed">
                  <p className="font-semibold text-foreground flex items-center gap-1.5">
                    💡 ¿Por qué es importante?
                  </p>
                  <p>
                    Esta configuración aísla completamente tus archivos del código fuente de la aplicación, garantizando que tus fotos y documentos permanezcan seguros en tu directorio de usuario o unidad de almacenamiento externa.
                  </p>
                </div>
              </CardContent>
              <CardFooter className="flex justify-between pb-8 pt-4">
                <Button type="button" variant="outline" onClick={() => setStep(1)} className="h-12 px-6 rounded-2xl gap-2">
                  <ArrowLeft className="w-4 h-4" /> Anterior
                </Button>
                <Button type="submit" className="h-12 px-8 rounded-2xl bg-primary hover:bg-primary/90 text-white font-medium gap-2">
                  Siguiente <ArrowRight className="w-4 h-4" />
                </Button>
              </CardFooter>
            </form>
          )}

          {/* STEP 3: MODELOS LLM */}
          {step === 3 && (
            <form onSubmit={handleFinishSetup}>
              <CardHeader className="space-y-2 pt-8">
                <CardTitle className="text-2xl font-bold flex items-center gap-2">
                  <Brain className="w-6 h-6 text-primary" /> Configuración de Inteligencia Artificial
                </CardTitle>
                <CardDescription>
                  Selecciona el proveedor y los modelos de lenguaje que utilizará el agente inteligente.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Proveedor Principal */}
                <div className="space-y-4 p-4 rounded-2xl bg-muted/30 border border-border/50">
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-primary" />
                    <Label className="font-bold text-xs uppercase tracking-wider">Proveedor y Modelo Principal</Label>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Proveedor LLM</Label>
                      <Select
                        value={llmData.llm_provider}
                        onValueChange={(v) => {
                          const defaultMod = MODELS_BY_PROVIDER[v]?.[0] || '';
                          setLlmData(prev => ({
                            ...prev,
                            llm_provider: v,
                            llm_model: defaultMod,
                            fast_llm_provider: v,
                            fast_llm_model: defaultMod,
                            vision_llm_provider: v,
                            vision_llm_model: defaultMod,
                          }));
                        }}
                      >
                        <SelectTrigger className="bg-background border-0 rounded-xl h-11">
                          <SelectValue placeholder="Proveedor" />
                        </SelectTrigger>
                        <SelectContent>
                          {LLM_PROVIDERS.map(p => (
                            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">Modelo Principal</Label>
                      <Input
                        value={llmData.llm_model}
                        onChange={(e) => setLlmData({ ...llmData, llm_model: e.target.value })}
                        placeholder="ej. gemini/gemini-2.0-flash"
                        className="bg-background border-0 rounded-xl h-11 font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>

                {/* API Key opcional si aplica */}
                {LLM_PROVIDERS.find(p => p.id === llmData.llm_provider)?.env_key && (
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2 text-xs font-semibold">
                      <KeyRound className="w-3.5 h-3.5 text-primary" /> Clave API ({LLM_PROVIDERS.find(p => p.id === llmData.llm_provider)?.env_key})
                    </Label>
                    <Input
                      type="password"
                      placeholder="Ingresa tu API Key para activar el modelo"
                      value={llmData.apiKey}
                      onChange={(e) => setLlmData({ ...llmData, apiKey: e.target.value })}
                      className="bg-muted/30 border-0 rounded-2xl h-12 font-mono text-sm"
                    />
                  </div>
                )}

                {/* API Base URL para compatibles / Ollama */}
                {['openai-compatible', 'ollama', 'ollama-cloud'].includes(llmData.llm_provider) && (
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2 text-xs font-semibold">
                      <Globe className="w-3.5 h-3.5 text-primary" /> API Base URL
                    </Label>
                    <Input
                      placeholder={
                        llmData.llm_provider === 'ollama' ? 'http://host.docker.internal:11434' : 'http://localhost:8080/v1'
                      }
                      value={llmData.llm_api_base}
                      onChange={(e) => setLlmData({ ...llmData, llm_api_base: e.target.value })}
                      className="bg-muted/30 border-0 rounded-2xl h-12 font-mono text-sm"
                    />
                  </div>
                )}
              </CardContent>
              <CardFooter className="flex justify-between pb-8 pt-4">
                <Button type="button" variant="outline" onClick={() => setStep(2)} className="h-12 px-6 rounded-2xl gap-2" disabled={loading}>
                  <ArrowLeft className="w-4 h-4" /> Anterior
                </Button>
                <Button type="submit" className="h-12 px-8 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-medium gap-2" disabled={loading}>
                  {loading ? 'Inicializando...' : 'Completar Instalación'} <ArrowRight className="w-4 h-4" />
                </Button>
              </CardFooter>
            </form>
          )}

          {/* STEP 4: FINALIZACIÓN */}
          {step === 4 && (
            <div className="text-center space-y-6 p-8 py-12">
              <div className="w-20 h-20 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center mx-auto animate-bounce">
                <CheckCircle2 className="w-12 h-12" />
              </div>
              <div className="space-y-2">
                <h2 className="text-3xl font-extrabold tracking-tight">¡Instalación Completada!</h2>
                <p className="text-muted-foreground max-w-md mx-auto text-sm leading-relaxed">
                  Kognito AI ha sido configurado exitosamente. Tu cuenta de usuario administrador está lista para usarse y tus preferencias de almacenamiento e IA han sido guardadas.
                </p>
              </div>
              <div className="pt-4">
                <Button
                  onClick={() => router.push('/login')}
                  className="h-14 px-10 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-base shadow-xl hover:shadow-2xl transition-all duration-200 gap-3"
                >
                  Iniciar Sesión <ArrowRight className="w-5 h-5" />
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </main>
  );
}
