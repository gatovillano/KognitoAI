"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Brain, Zap, Image as ImageIcon, RefreshCw, Key, Shield, Trash2, ArrowLeft, Plus } from 'lucide-react';

const LLM_PROVIDERS = [
  { id: 'gemini', name: 'Google AI Studio', env_key: 'GOOGLE_API_KEY' },
  { id: 'openai', name: 'OpenAI (GPT)', env_key: 'OPENAI_API_KEY' },
  { id: 'anthropic', name: 'Anthropic (Claude)', env_key: 'ANTHROPIC_API_KEY' },
  { id: 'openrouter', name: 'OpenRouter', env_key: 'OPENROUTER_API_KEY' },
  { id: 'ollama', name: 'Ollama (Local)', env_key: null },
  { id: 'ollama-cloud', name: '☁️ Ollama Cloud', env_key: 'OLLAMA_API_KEY' },
  { id: 'openai-compatible', name: '🖥️ Local AI / OpenAI Compatible', env_key: null },
  { id: 'mistral', name: 'Mistral AI', env_key: 'MISTRAL_API_KEY' },
  { id: 'kilocode', name: '🚀 Kilocode Gateway', env_key: 'KILOCODE_API_KEY' },
];

const MODELS_BY_PROVIDER: Record<string, string[]> = {
  gemini: ['gemini/gemini-2.0-flash', 'gemini/gemini-1.5-flash', 'gemini/gemini-1.5-pro', 'gemini/gemini-2.0-flash-exp'],
  openai: ['openai/gpt-4o', 'openai/gpt-4o-mini', 'openai/gpt-4-turbo'],
  anthropic: ['anthropic/claude-3-5-sonnet-20240620', 'anthropic/claude-3-opus-20240229', 'anthropic/claude-3-haiku-20240307'],
  openrouter: [
    'openrouter/google/gemini-2.5-flash-preview',
    'openrouter/anthropic/claude-sonnet-4',
    'openrouter/openai/gpt-4.1-mini',
    'openrouter/google/gemini-2.5-pro-preview',
    'openrouter/mistralai/mistral-small-3.1-24b-instruct:free',
  ],
  ollama: ['ollama/llama3.1', 'ollama/mistral', 'ollama/phi3', 'ollama/gemma2'],
  'ollama-cloud': ['ollama_chat/llama3.1', 'ollama_chat/mistral', 'ollama_chat/phi3', 'ollama_chat/gemma2', 'ollama_chat/qwen2.5'],
  'openai-compatible': [],
  mistral: ['mistral/mistral-large-latest', 'mistral/mistral-small-latest'],
  kilocode: [],
};

interface GlobalSecret {
  key_name: string;
  description?: string;
  masked_value: string;
  created_at: string;
  updated_at: string;
}

export default function AdminSettingsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [loadingSecrets, setLoadingSecrets] = useState(false);
  const [secrets, setSecrets] = useState<GlobalSecret[]>([]);
  const [newKey, setNewKey] = useState({ provider: '', value: '' });

  const [localLLM, setLocalLLM] = useState({
    llm_provider: 'gemini',
    llm_model: 'gemini/gemini-2.0-flash',
    llm_temperature: 0.7,
    llm_api_base: '',
    fast_llm_model: 'gemini/gemini-2.0-flash',
    fast_llm_provider: 'gemini',
    vision_llm_model: 'gemini/gemini-2.0-flash',
    vision_llm_provider: 'gemini',
    use_prompt_tooling: false,
    image_generation_model: 'imagen-3.0-generate-002',
  });

  const [mainModels, setMainModels] = useState<any[]>([]);
  const [fastModels, setFastModels] = useState<any[]>([]);
  const [visionModels, setVisionModels] = useState<any[]>([]);
  const [imageModels, setImageModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState({ main: false, fast: false, vision: false, image: false });

  const fetchGlobalSettings = async () => {
    setLoading(true);
    try {
      const resp = await apiClient.get('/api/admin/llm-settings');
      if (resp.data) {
        setLocalLLM({
          llm_provider: resp.data.llm_provider || 'gemini',
          llm_model: resp.data.llm_model || '',
          llm_temperature: resp.data.llm_temperature !== undefined ? resp.data.llm_temperature : 0.7,
          llm_api_base: resp.data.llm_api_base || '',
          fast_llm_model: resp.data.fast_llm_model || '',
          fast_llm_provider: resp.data.fast_llm_provider || 'gemini',
          vision_llm_model: resp.data.vision_llm_model || '',
          vision_llm_provider: resp.data.vision_llm_provider || 'gemini',
          use_prompt_tooling: !!resp.data.use_prompt_tooling,
          image_generation_model: resp.data.image_generation_model || 'imagen-3.0-generate-002',
        });
      }
    } catch (e) {
      console.error('Error fetching global settings:', e);
      toast.error('No se pudo cargar la configuración global.');
    } finally {
      setLoading(false);
    }
  };

  const fetchGlobalSecrets = async () => {
    setLoadingSecrets(true);
    try {
      const resp = await apiClient.get('/api/admin/llm-settings/secrets');
      setSecrets(resp.data || []);
    } catch (e) {
      console.error('Error fetching global secrets:', e);
      toast.error('No se pudieron cargar las API Keys globales.');
    } finally {
      setLoadingSecrets(false);
    }
  };

  const fetchModels = async (provider: string, type: 'main' | 'fast' | 'vision' | 'image', options: { apiBase?: string; refresh?: boolean } = {}) => {
    setLoadingModels(prev => ({ ...prev, [type]: true }));
    try {
      const { apiBase, refresh } = options;
      let url = `/api/llm/models/${provider}`;
      const params = new URLSearchParams();
      if (apiBase) params.append('api_base', apiBase);
      if (refresh) params.append('refresh', 'true');

      const queryString = params.toString();
      if (queryString) url += `?${queryString}`;

      const resp = await apiClient.get(url);
      const fetchedModels = resp?.data || [];
      
      if (type === 'image') {
        const filtered = fetchedModels.filter((m: any) => {
          const id = typeof m === 'string' ? m : (m.id || '');
          return id.toLowerCase().includes('imagen');
        });
        setImageModels(filtered);
      } else {
        const filtered = fetchedModels.filter((m: any) => {
          const id = typeof m === 'string' ? m : (m.id || '');
          return !id.toLowerCase().includes('imagen');
        });
        if (type === 'main') setMainModels(filtered);
        else if (type === 'fast') setFastModels(filtered);
        else if (type === 'vision') setVisionModels(filtered);
      }
    } catch (e) {
      console.error(`Error fetching ${type} models for ${provider}:`, e);
    } finally {
      setLoadingModels(prev => ({ ...prev, [type]: false }));
    }
  };

  const renderModelItem = (m: any, currentProvider: string) => {
    const isString = typeof m === 'string';
    const id = isString ? m : m.id;
    const name = isString ? m : (m.name || m.id);
    const isGemini = currentProvider === 'gemini' || id.startsWith('gemini/');
    const isOpenRouter = currentProvider === 'openrouter' || id.startsWith('openrouter/');
    const isKilocode = currentProvider === 'kilocode' || id.startsWith('kilocode/');

    if (isOpenRouter || isGemini || isKilocode) {
      let badgeColor = "bg-blue-500/10 text-blue-500 border-blue-500/20";
      let badgeText = isKilocode ? "KiloCode" : "OpenRouter";
      let borderColor = "border-blue-500";
      let bgColor = "bg-blue-500/5";

      if (isGemini) {
        badgeText = "Google";
        badgeColor = "bg-red-500/10 text-red-500 border-red-500/20";
        borderColor = "border-red-500";
        bgColor = "bg-red-500/5";
      } else if (id.toLowerCase().includes('free')) {
        badgeText = "FREE";
        badgeColor = "bg-green-500/10 text-green-500 border-green-500/20";
        borderColor = "border-green-500";
        bgColor = "bg-green-500/5";
      } else if (id.toLowerCase().includes('claude') || id.toLowerCase().includes('anthropic')) {
        badgeText = "Anthropic";
        badgeColor = "bg-orange-500/10 text-orange-500 border-orange-500/20";
        borderColor = "border-orange-500";
        bgColor = "bg-orange-500/5";
      } else if (id.toLowerCase().includes('gemini') || id.toLowerCase().includes('google')) {
        badgeText = "Google";
        badgeColor = "bg-red-500/10 text-red-500 border-red-500/20";
        borderColor = "border-red-500";
        bgColor = "bg-red-500/5";
      } else if (id.toLowerCase().includes('mistral')) {
        badgeText = "Mistral";
        badgeColor = "bg-purple-500/10 text-purple-500 border-purple-500/20";
        borderColor = "border-purple-500";
        bgColor = "bg-purple-500/5";
      } else if (isKilocode && id.toLowerCase().includes('kilo')) {
        badgeText = "KiloCode";
        badgeColor = "bg-blue-600/10 text-blue-600 border-blue-600/20";
        borderColor = "border-blue-600";
        bgColor = "bg-blue-600/5";
      }

      return (
        <SelectItem
          key={id}
          value={id}
          className={`mb-2 border-l-4 ${borderColor} ${bgColor} hover:bg-accent focus:bg-accent transition-all duration-200 cursor-pointer rounded-r-md mx-1`}
        >
          <div className="flex flex-col py-1.5 w-full">
            <div className="flex items-center justify-between w-full gap-4">
              <span className="font-bold text-sm tracking-tight">{name}</span>
              <Badge variant="outline" className={`text-[9px] px-1.5 py-0 h-4 uppercase font-extrabold tracking-wider ${badgeColor}`}>
                {badgeText}
              </Badge>
            </div>
            {(m.context_length || m.pricing) && (
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] text-muted-foreground/70 font-medium">
                  {m.context_length ? `${(m.context_length / 1024).toFixed(0)}k contexto` : ''}
                </span>
                {id.toLowerCase().includes('free') && (
                  <span className="text-[10px] text-green-600 font-bold">Sin costo</span>
                )}
              </div>
            )}
          </div>
        </SelectItem>
      );
    }

    return (
      <SelectItem key={id} value={id}>
        {name}
      </SelectItem>
    );
  };

  useEffect(() => {
    fetchGlobalSettings();
    fetchGlobalSecrets();
    fetchModels('gemini', 'image');
  }, []);

  useEffect(() => {
    const handler = setTimeout(() => {
      if (localLLM.llm_provider) {
        fetchModels(localLLM.llm_provider, 'main', { apiBase: localLLM.llm_api_base });
      }
    }, 500);
    return () => clearTimeout(handler);
  }, [localLLM.llm_provider, localLLM.llm_api_base]);

  useEffect(() => {
    const handler = setTimeout(() => {
      if (localLLM.fast_llm_provider) {
        fetchModels(localLLM.fast_llm_provider, 'fast', { apiBase: localLLM.llm_api_base });
      }
    }, 500);
    return () => clearTimeout(handler);
  }, [localLLM.fast_llm_provider, localLLM.llm_api_base]);

  useEffect(() => {
    const handler = setTimeout(() => {
      if (localLLM.vision_llm_provider) {
        fetchModels(localLLM.vision_llm_provider, 'vision', { apiBase: localLLM.llm_api_base });
      }
    }, 500);
    return () => clearTimeout(handler);
  }, [localLLM.vision_llm_provider, localLLM.llm_api_base]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.put('/api/admin/llm-settings', localLLM);
      toast.success('Configuración global de IA guardada y LLMs reinicializados.');
    } catch (e: any) {
      console.error('Error saving global settings:', e);
      toast.error(e.response?.data?.detail || 'Error al guardar la configuración global.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveKey = async () => {
    if (!newKey.provider || !newKey.value) {
      toast.error('Por favor selecciona un proveedor y proporciona una API Key.');
      return;
    }

    const llmProvider = LLM_PROVIDERS.find(p => p.id === newKey.provider);
    if (!llmProvider || !llmProvider.env_key) {
      toast.error('Proveedor no válido o no requiere API Key.');
      return;
    }

    try {
      await apiClient.post('/api/admin/llm-settings/secrets', {
        key_name: llmProvider.env_key,
        value: newKey.value,
        description: `API Key Global para ${llmProvider.name}`
      });
      toast.success(`API Key global de ${llmProvider.name} guardada correctamente.`);
      setNewKey({ provider: '', value: '' });
      fetchGlobalSecrets();
    } catch (e: any) {
      console.error('Error saving global key:', e);
      toast.error(e.response?.data?.detail || 'Error al guardar la API Key global.');
    }
  };

  const handleDeleteSecret = async (keyName: string) => {
    if (!confirm(`¿Estás seguro de que deseas eliminar el secreto global "${keyName}"?`)) {
      return;
    }

    try {
      await apiClient.delete(`/api/admin/llm-settings/secrets/${keyName}`);
      toast.success(`Secreto global "${keyName}" eliminado.`);
      fetchGlobalSecrets();
    } catch (e: any) {
      console.error('Error deleting secret:', e);
      toast.error(e.response?.data?.detail || 'Error al eliminar el secreto.');
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/admin">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            Configuración Global de IA
          </h1>
          <p className="text-muted-foreground mt-1">
            Define los modelos predeterminados y las credenciales globales del sistema.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: Form */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={handleSaveSettings}>
            <Card className="border border-primary/20 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5 text-primary" />
                  Modelos Predeterminados
                </CardTitle>
                <CardDescription>
                  Estos modelos se usarán como fallback cuando los usuarios no tengan su propia configuración.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                
                {/* Main LLM */}
                <div className="p-4 rounded-xl bg-primary/5 border border-primary/10 space-y-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Brain className="h-5 w-5 text-primary" />
                    <h3 className="font-bold text-sm uppercase tracking-wider text-primary">Modelo Principal (Razonamiento)</h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-[11px] font-bold uppercase text-muted-foreground">Proveedor</Label>
                      <Select
                        value={localLLM.llm_provider}
                        onValueChange={(v) => {
                          setLocalLLM(prev => ({
                            ...prev,
                            llm_provider: v,
                            llm_model: '',
                            llm_api_base: v === 'ollama-cloud' ? '' : prev.llm_api_base
                          }));
                        }}
                      >
                        <SelectTrigger className="bg-background/50 border-primary/20">
                          <SelectValue placeholder="Seleccionar Proveedor" />
                        </SelectTrigger>
                        <SelectContent>
                          {LLM_PROVIDERS.map(p => (
                            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-4 w-4"
                          onClick={() => fetchModels(localLLM.llm_provider, 'main', { apiBase: localLLM.llm_api_base, refresh: true })}
                        >
                          <RefreshCw className={`h-3 w-3 ${loadingModels.main ? 'animate-spin' : ''}`} />
                        </Button>
                      </div>
                      <Select
                        value={localLLM.llm_model}
                        onValueChange={(v) => setLocalLLM(prev => ({ ...prev, llm_model: v }))}
                      >
                        <SelectTrigger className="bg-background/50 border-primary/20">
                          <SelectValue placeholder="Seleccionar Modelo" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[250px]">
                          {loadingModels.main ? (
                            <SelectItem value="loading" disabled>Cargando modelos...</SelectItem>
                          ) : mainModels.length > 0 ? (
                            mainModels.map(m => renderModelItem(m, localLLM.llm_provider))
                          ) : (
                            (MODELS_BY_PROVIDER[localLLM.llm_provider] || []).map(m => renderModelItem(m, localLLM.llm_provider))
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Fast LLM */}
                <div className="p-4 rounded-xl bg-orange-500/5 border border-orange-500/10 space-y-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Zap className="h-5 w-5 text-orange-500" />
                    <h3 className="font-bold text-sm uppercase tracking-wider text-orange-500">Modelo Rápido (Sumarización / Tareas sencillas)</h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-[11px] font-bold uppercase text-muted-foreground">Proveedor</Label>
                      <Select
                        value={localLLM.fast_llm_provider}
                        onValueChange={(v) => {
                          setLocalLLM(prev => ({
                            ...prev,
                            fast_llm_provider: v,
                            fast_llm_model: ''
                          }));
                        }}
                      >
                        <SelectTrigger className="bg-background/50 border-orange-500/20">
                          <SelectValue placeholder="Seleccionar Proveedor" />
                        </SelectTrigger>
                        <SelectContent>
                          {LLM_PROVIDERS.map(p => (
                            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-4 w-4"
                          onClick={() => fetchModels(localLLM.fast_llm_provider, 'fast', { apiBase: localLLM.llm_api_base, refresh: true })}
                        >
                          <RefreshCw className={`h-3 w-3 ${loadingModels.fast ? 'animate-spin' : ''}`} />
                        </Button>
                      </div>
                      <Select
                        value={localLLM.fast_llm_model}
                        onValueChange={(v) => setLocalLLM(prev => ({ ...prev, fast_llm_model: v }))}
                      >
                        <SelectTrigger className="bg-background/50 border-orange-500/20">
                          <SelectValue placeholder="Seleccionar Modelo" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[250px]">
                          {loadingModels.fast ? (
                            <SelectItem value="loading" disabled>Cargando modelos...</SelectItem>
                          ) : fastModels.length > 0 ? (
                            fastModels.map(m => renderModelItem(m, localLLM.fast_llm_provider))
                          ) : (
                            (MODELS_BY_PROVIDER[localLLM.fast_llm_provider] || []).map(m => renderModelItem(m, localLLM.fast_llm_provider))
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Vision LLM */}
                <div className="p-4 rounded-xl bg-purple-500/5 border border-purple-500/10 space-y-4">
                  <div className="flex items-center gap-2 mb-1">
                    <ImageIcon className="h-5 w-5 text-purple-500" />
                    <h3 className="font-bold text-sm uppercase tracking-wider text-purple-500">Modelo de Visión (Análisis de imágenes)</h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-[11px] font-bold uppercase text-muted-foreground">Proveedor</Label>
                      <Select
                        value={localLLM.vision_llm_provider}
                        onValueChange={(v) => {
                          setLocalLLM(prev => ({
                            ...prev,
                            vision_llm_provider: v,
                            vision_llm_model: ''
                          }));
                        }}
                      >
                        <SelectTrigger className="bg-background/50 border-purple-500/20">
                          <SelectValue placeholder="Seleccionar Proveedor" />
                        </SelectTrigger>
                        <SelectContent>
                          {LLM_PROVIDERS.map(p => (
                            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-4 w-4"
                          onClick={() => fetchModels(localLLM.vision_llm_provider, 'vision', { apiBase: localLLM.llm_api_base, refresh: true })}
                        >
                          <RefreshCw className={`h-3 w-3 ${loadingModels.vision ? 'animate-spin' : ''}`} />
                        </Button>
                      </div>
                      <Select
                        value={localLLM.vision_llm_model}
                        onValueChange={(v) => setLocalLLM(prev => ({ ...prev, vision_llm_model: v }))}
                      >
                        <SelectTrigger className="bg-background/50 border-purple-500/20">
                          <SelectValue placeholder="Seleccionar Modelo" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[250px]">
                          {loadingModels.vision ? (
                            <SelectItem value="loading" disabled>Cargando modelos...</SelectItem>
                          ) : visionModels.length > 0 ? (
                            visionModels.map(m => renderModelItem(m, localLLM.vision_llm_provider))
                          ) : (
                            (MODELS_BY_PROVIDER[localLLM.vision_llm_provider] || []).map(m => renderModelItem(m, localLLM.vision_llm_provider))
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Image Generation Model */}
                <div className="p-4 rounded-xl bg-teal-500/5 border border-teal-500/10 space-y-4">
                  <div className="flex items-center gap-2 mb-1">
                    <ImageIcon className="h-5 w-5 text-teal-500" />
                    <h3 className="font-bold text-sm uppercase tracking-wider text-teal-500">Generación de Imágenes (Google AI Studio)</h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                      <Select
                        value={localLLM.image_generation_model}
                        onValueChange={(v) => setLocalLLM(prev => ({ ...prev, image_generation_model: v }))}
                      >
                        <SelectTrigger className="bg-background/50 border-teal-500/20">
                          <SelectValue placeholder="Seleccionar Modelo de Imagen" />
                        </SelectTrigger>
                        <SelectContent>
                          {loadingModels.image ? (
                            <SelectItem value="loading" disabled>Cargando modelos...</SelectItem>
                          ) : imageModels.length > 0 ? (
                            imageModels.map(m => renderModelItem(m, 'gemini'))
                          ) : (
                            <>
                              <SelectItem value="imagen-3.0-generate-002">imagen-3.0-generate-002 (Alta Calidad)</SelectItem>
                              <SelectItem value="imagen-3.0-fast-generate-002">imagen-3.0-fast-generate-002 (Fast)</SelectItem>
                            </>
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Additional Settings */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-border">
                  <div className="space-y-2">
                    <Label className="text-xs font-bold uppercase text-muted-foreground">Temperatura Predeterminada</Label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={localLLM.llm_temperature}
                        onChange={(e) => setLocalLLM(prev => ({ ...prev, llm_temperature: parseFloat(e.target.value) }))}
                        className="w-full accent-primary"
                      />
                      <span className="font-mono text-sm font-bold w-12 px-2 py-1 rounded bg-secondary text-center">
                        {localLLM.llm_temperature.toFixed(1)}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-bold">Use Prompt Tooling</Label>
                      <p className="text-xs text-muted-foreground">Permite la optimización dinámica de prompts.</p>
                    </div>
                    <Switch
                      checked={localLLM.use_prompt_tooling}
                      onCheckedChange={(checked) => setLocalLLM(prev => ({ ...prev, use_prompt_tooling: checked }))}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-xs font-bold uppercase text-muted-foreground">API Base URL (Opcional)</Label>
                  <Input
                    placeholder="https://api.openai.com/v1"
                    value={localLLM.llm_api_base}
                    onChange={(e) => setLocalLLM(prev => ({ ...prev, llm_api_base: e.target.value }))}
                  />
                  <p className="text-[11px] text-muted-foreground">Necesario para proveedores OpenAI-Compatible locales u otros endpoints personalizados.</p>
                </div>

              </CardContent>
              <div className="p-6 bg-secondary/10 border-t flex justify-end">
                <Button type="submit" disabled={loading}>
                  {loading ? 'Guardando...' : 'Guardar Ajustes Globales'}
                </Button>
              </div>
            </Card>
          </form>
        </div>

        {/* Right Side: Credentials */}
        <div className="space-y-6">
          <Card className="border border-primary/20 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" />
                API Keys Globales
              </CardTitle>
              <CardDescription>
                Credenciales del sistema que utilizarán los modelos globales.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Add Credential Form */}
              <div className="p-4 rounded-lg bg-secondary/30 space-y-4">
                <h4 className="font-bold text-xs uppercase tracking-wider text-foreground flex items-center gap-1">
                  <Plus className="h-3 w-3" /> Agregar Credencial Global
                </h4>
                <div className="space-y-2">
                  <Label className="text-[11px] font-medium text-muted-foreground">Proveedor</Label>
                  <Select
                    value={newKey.provider}
                    onValueChange={(v) => setNewKey(prev => ({ ...prev, provider: v }))}
                  >
                    <SelectTrigger className="bg-background">
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      {LLM_PROVIDERS.filter(p => p.env_key).map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-[11px] font-medium text-muted-foreground">Valor (API Key)</Label>
                  <Input
                    type="password"
                    placeholder="sk-..."
                    value={newKey.value}
                    onChange={(e) => setNewKey(prev => ({ ...prev, value: e.target.value }))}
                  />
                </div>
                <Button onClick={handleSaveKey} size="sm" className="w-full">
                  Guardar API Key
                </Button>
              </div>

              {/* Secrets Table */}
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase text-muted-foreground">Credenciales Activas</Label>
                {loadingSecrets ? (
                  <p className="text-sm text-muted-foreground">Cargando llaves...</p>
                ) : secrets.length > 0 ? (
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader className="bg-secondary/40">
                        <TableRow>
                          <TableHead className="py-2 text-[10px] font-bold">Clave</TableHead>
                          <TableHead className="py-2 text-[10px] font-bold">Valor</TableHead>
                          <TableHead className="py-2 text-[10px] font-bold text-right">Acción</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {secrets.map((sec) => (
                          <TableRow key={sec.key_name} className="hover:bg-secondary/20">
                            <TableCell className="py-2.5 font-mono text-[10px] max-w-[120px] truncate" title={sec.key_name}>
                              {sec.key_name}
                            </TableCell>
                            <TableCell className="py-2.5 font-mono text-[10px] text-muted-foreground">
                              {sec.masked_value}
                            </TableCell>
                            <TableCell className="py-2.5 text-right">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-destructive hover:bg-destructive/10"
                                onClick={() => handleDeleteSecret(sec.key_name)}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground bg-secondary/10 p-4 rounded text-center">
                    No hay credenciales globales configuradas. Se usarán las variables de entorno.
                  </p>
                )}
              </div>

            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
