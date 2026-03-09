"use client";

import React, { useState, useEffect } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api'; // Importar apiClient
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Edit, Trash2, Eye, Calendar, User, Sparkles, Brain, Zap, Image as ImageIcon } from 'lucide-react';

interface Memory {
  id: string;
  title: string;
  content: string;
  type: string;
  created_at: string;
  updated_at: string;
  user_id: string;
}



const LLM_PROVIDERS = [
  { id: 'gemini', name: 'Google AI Studio', env_key: 'GOOGLE_API_KEY' },
  { id: 'openai', name: 'OpenAI (GPT)', env_key: 'OPENAI_API_KEY' },
  { id: 'anthropic', name: 'Anthropic (Claude)', env_key: 'ANTHROPIC_API_KEY' },
  { id: 'openrouter', name: 'OpenRouter', env_key: 'OPENROUTER_API_KEY' },
  { id: 'ollama', name: 'Ollama (Local)', env_key: null },
  { id: 'mistral', name: 'Mistral AI', env_key: 'MISTRAL_API_KEY' },
];

const MODELS_BY_PROVIDER: Record<string, string[]> = {
  gemini: ['gemini/gemini-2.0-flash', 'gemini/gemini-1.5-flash', 'gemini/gemini-1.5-pro', 'gemini/gemini-2.0-flash-exp'],
  openai: ['openai/gpt-4o', 'openai/gpt-4o-mini', 'openai/gpt-4-turbo'],
  anthropic: ['anthropic/claude-3-5-sonnet-20240620', 'anthropic/claude-3-opus-20240229', 'anthropic/claude-3-haiku-20240307'],
  openrouter: [
    'openrouter/mistralai/mistral-small-3.1-24b-instruct:free',
    'openrouter/google/gemini-2.0-flash-001',
    'openrouter/anthropic/claude-3.5-sonnet'
  ],
  ollama: ['ollama/llama3.1', 'ollama/mistral', 'ollama/phi3', 'ollama/gemma2'],
  mistral: ['mistral/mistral-large-latest', 'mistral/mistral-small-latest'],
};

const TTS_PROVIDERS = [
  { id: 'google', name: 'Google Cloud TTS', env_key: 'GOOGLE_APPLICATION_CREDENTIALS' },
  { id: 'openai', name: 'OpenAI TTS', env_key: 'OPENAI_API_KEY' },
  { id: 'azure', name: 'Azure TTS', env_key: 'AZURE_TTS_KEY' },
];

const TTS_VOICES_BY_PROVIDER: Record<string, string[]> = {
  google: [
    'es-MX-DaliaNeural', 'es-MX-JorgeNeural', 'es-MX-AndresNeural', 'es-MX-FernandaNeural',
    'es-ES-ElviraNeural', 'es-ES-AlvaroNeural',
    'en-US-Neural2-A', 'en-US-Neural2-C', 'en-US-Neural2-D', 'en-US-Neural2-E',
  ],
  openai: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
  azure: [
    'es-MX-DaliaNeural', 'es-MX-JorgeNeural', 'es-MX-CandelaNeural', 'es-MX-GerardoNeural',
    'es-ES-ElviraNeural', 'es-ES-AlvaroNeural', 'es-ES-LaiaNeural', 'es-ES-ArnauNeural',
    'en-US-JennyNeural', 'en-US-GuyNeural', 'en-US-AriaNeural', 'en-US-DavisNeural',
  ],
};

const EMBEDDING_PROVIDERS = [
  { id: 'kognito-internal', name: 'Kognito Interno', env_key: null },
  { id: 'ollama', name: 'Ollama (Local)', env_key: null },
  { id: 'openai', name: 'OpenAI Embeddings', env_key: 'OPENAI_API_KEY' },
  { id: 'google', name: 'Google Embeddings', env_key: 'GOOGLE_API_KEY' },
];

const SEARCH_PROVIDERS = [
  { id: 'tavily', name: 'Tavily Search', env_key: 'TAVILY_API_KEY' },
];

const EMBEDDING_MODELS_BY_PROVIDER: Record<string, string[]> = {
  'kognito-internal': ['paraphrase-multilingual-mpnet-base-v2'],
  ollama: ['nomic-embed-text', 'llama3', 'mistral'],
  openai: ['text-embedding-ada-002', 'text-embedding-3-small', 'text-embedding-3-large'],
  google: ['text-embedding-004', 'text-embedding-gecko'],
};

interface UserSecret {
  key_name: string;
  description?: string;
  masked_value: string;
}

const LLMSettingsForm: React.FC = () => {
  const { settings, updateSettings } = useUserSettings();
  const [loading, setLoading] = useState(false);
  const [secrets, setSecrets] = useState<UserSecret[]>([]);
  const [newKey, setNewKey] = useState({ provider: '', value: '' });

  const [localLLM, setLocalLLM] = useState({
    llm_provider: settings?.llm_provider || 'gemini',
    llm_model: settings?.llm_model || 'gemini/gemini-2.0-flash',
    llm_temperature: settings?.llm_temperature || 0.7,
    llm_api_base: settings?.llm_api_base || '',
    fast_llm_model: settings?.fast_llm_model || 'gemini/gemini-2.0-flash',
    fast_llm_provider: settings?.fast_llm_provider || 'gemini',
    vision_llm_model: settings?.vision_llm_model || 'gemini/gemini-2.0-flash',
    vision_llm_provider: settings?.vision_llm_provider || 'gemini',
    use_prompt_tooling: settings?.use_prompt_tooling || false,
  });

  const [localTTS, setLocalTTS] = useState({
    tts_provider: settings?.tts_provider || 'google',
    tts_model: settings?.tts_model || 'tts-1', // OpenAI default
    tts_voice: settings?.tts_voice || 'es-MX-DaliaNeural', // Google default
    tts_speed: settings?.tts_speed || 1.0,
    tts_region: settings?.tts_region || '', // Nuevo campo para Azure
  });

  const [localEmbedding, setLocalEmbedding] = useState({
    embedding_provider: settings?.embedding_provider || 'kognito-internal',
    embedding_model: settings?.embedding_model || 'paraphrase-multilingual-mpnet-base-v2',
    embedding_api_key_name: settings?.embedding_api_key_name || '',
    embedding_api_base: settings?.embedding_api_base || '',
  });

  const [mainModels, setMainModels] = useState<any[]>([]);
  const [fastModels, setFastModels] = useState<any[]>([]);
  const [visionModels, setVisionModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState({ main: false, fast: false, vision: false });

  const fetchModels = async (provider: string, type: 'main' | 'fast' | 'vision') => {
    setLoadingModels(prev => ({ ...prev, [type]: true }));
    try {
      const resp = await apiClient.get(`/api/llm/models/${provider}`);
      const models = resp?.data || [];
      if (type === 'main') setMainModels(models);
      else if (type === 'fast') setFastModels(models);
      else if (type === 'vision') setVisionModels(models);
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

    if (isOpenRouter || isGemini) {
      let badgeColor = "bg-blue-500/10 text-blue-500 border-blue-500/20";
      let badgeText = "OpenRouter";
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
    if (localLLM.llm_provider) fetchModels(localLLM.llm_provider, 'main');
  }, [localLLM.llm_provider]);

  useEffect(() => {
    if (localLLM.fast_llm_provider) fetchModels(localLLM.fast_llm_provider, 'fast');
  }, [localLLM.fast_llm_provider]);

  useEffect(() => {
    if (localLLM.vision_llm_provider) fetchModels(localLLM.vision_llm_provider, 'vision');
  }, [localLLM.vision_llm_provider]);

  useEffect(() => {
    if (settings) {
      setLocalLLM({
        llm_provider: settings.llm_provider || 'gemini',
        llm_model: settings.llm_model || 'gemini/gemini-2.0-flash',
        llm_temperature: settings.llm_temperature || 0.7,
        llm_api_base: settings.llm_api_base || '',
        fast_llm_model: settings.fast_llm_model || 'gemini/gemini-2.0-flash',
        fast_llm_provider: settings.fast_llm_provider || 'gemini',
        vision_llm_model: settings.vision_llm_model || 'gemini/gemini-2.0-flash',
        vision_llm_provider: settings.vision_llm_provider || 'gemini',
        use_prompt_tooling: settings.use_prompt_tooling || false,
      });
      setLocalTTS({
        tts_provider: settings.tts_provider || 'google',
        tts_model: settings.tts_model || 'tts-1',
        tts_voice: settings.tts_voice || 'es-MX-DaliaNeural',
        tts_speed: settings.tts_speed || 1.0,
        tts_region: settings.tts_region || '',
      });
      setLocalEmbedding({
        embedding_provider: settings.embedding_provider || 'kognito-internal',
        embedding_model: settings.embedding_model || 'paraphrase-multilingual-mpnet-base-v2',
        embedding_api_key_name: settings.embedding_api_key_name || '',
        embedding_api_base: settings.embedding_api_base || '',
      });
    }
  }, [settings]);

  const fetchSecrets = async () => {
    try {
      const resp = await apiClient.get('/api/users/me/secrets');
      setSecrets(resp.data);
    } catch (e) {
      console.error('Error fetching secrets:', e);
    }
  };

  useEffect(() => {
    fetchSecrets();
  }, []);

  const handleSaveAllSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await updateSettings({
        ...localLLM,
        ...localTTS,
        ...localEmbedding,
        tts_region: localTTS.tts_provider === 'azure' ? localTTS.tts_region : undefined, // Solo enviar si es Azure
      });
      toast.success('Configuración de IA, TTS y Embeddings guardada');
    } catch (e) {
      toast.error('Error al guardar configuración');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveKey = async () => {
    if (!newKey.provider || !newKey.value) return;

    let envKey: string | null = null;
    let description: string = `API Key para ${newKey.provider}`;

    const llmProvider = LLM_PROVIDERS.find(p => p.id === newKey.provider);
    const ttsProvider = TTS_PROVIDERS.find(p => p.id === newKey.provider);
    const embeddingProvider = EMBEDDING_PROVIDERS.find(p => p.id === newKey.provider);
    const searchProvider = SEARCH_PROVIDERS.find(p => p.id === newKey.provider);

    if (llmProvider) envKey = llmProvider.env_key;
    else if (ttsProvider) {
      if (newKey.provider === 'azure') {
        // Para Azure, necesitamos guardar la clave y la región por separado si es necesario
        // Aquí asumimos que newKey.provider es 'azure' y newKey.value es la clave
        // La región se manejará como parte de la configuración de usuario, no como un secreto separado
        envKey = 'AZURE_TTS_KEY'; // Nombre de la clave para Azure
        description = `API Key para Azure TTS`;
      } else {
        envKey = ttsProvider.env_key;
        description = `API Key para ${ttsProvider.name}`;
      }
    }
    else if (embeddingProvider) envKey = embeddingProvider.env_key;
    else if (searchProvider) {
      envKey = searchProvider.env_key;
      description = `API Key para ${searchProvider.name}`;
    }

    if (!envKey) {
      toast.error('Proveedor no válido o sin clave de entorno asociada.');
      return;
    }

    try {
      await apiClient.post('/api/users/me/secrets', {
        key_name: envKey,
        value: newKey.value,
        description: description
      });
      toast.success(`API Key de ${newKey.provider} guardada`);
      setNewKey({ provider: '', value: '' });
      fetchSecrets();
    } catch (e) {
      toast.error('Error al guardar la API Key');
    }
  };

  return (
    <div className="space-y-8">
      <Card className="border-none shadow-md bg-gradient-to-br from-card to-secondary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">IA</Badge>
            Modelo y Proveedor (LLM)
          </CardTitle>
          <CardDescription>
            Configura el motor de inteligencia artificial que potenciará tus interacciones.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* SECCIÓN MODELO PRINCIPAL */}
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/10 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="h-5 w-5 text-primary" />
                <h3 className="font-bold text-sm uppercase tracking-wider text-primary">Modelo Principal (Razonamiento)</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-[11px] font-bold uppercase text-muted-foreground">Proveedor</Label>
                  <Select
                    value={localLLM.llm_provider}
                    onValueChange={(v) => {
                      const firstModel = MODELS_BY_PROVIDER[v]?.[0] || '';
                      setLocalLLM(prev => ({
                        ...prev,
                        llm_provider: v,
                        llm_model: firstModel
                      }));
                    }}
                  >
                    <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20">
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
                  <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                  <Select
                    value={localLLM.llm_model}
                    onValueChange={(v) => setLocalLLM(prev => ({ ...prev, llm_model: v }))}
                  >
                    <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20">
                      <SelectValue placeholder="Modelo" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[300px] p-2">
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

            {/* SECCIÓN MODELO RÁPIDO */}
            <div className="p-4 rounded-xl bg-orange-500/5 border border-orange-500/10 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-5 w-5 text-orange-500" />
                <h3 className="font-bold text-sm uppercase tracking-wider text-orange-500">Modelo Rápido (Sumarización)</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-[11px] font-bold uppercase text-muted-foreground">Proveedor</Label>
                  <Select
                    value={localLLM.fast_llm_provider}
                    onValueChange={(v) => {
                      const firstModel = MODELS_BY_PROVIDER[v]?.[0] || '';
                      setLocalLLM(prev => ({
                        ...prev,
                        fast_llm_provider: v,
                        fast_llm_model: firstModel
                      }));
                    }}
                  >
                    <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-orange-500/20">
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
                  <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                  <Select
                    value={localLLM.fast_llm_model}
                    onValueChange={(v) => setLocalLLM(prev => ({ ...prev, fast_llm_model: v }))}
                  >
                    <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-orange-500/20">
                      <SelectValue placeholder="Modelo" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[300px] p-2">
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

            {/* SECCIÓN MODELO DE VISIÓN */}
            <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/10 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <ImageIcon className="h-5 w-5 text-blue-500" />
                <h3 className="font-bold text-sm uppercase tracking-wider text-blue-500">Modelo de Visión (Imágenes)</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-[11px] font-bold uppercase text-muted-foreground">Proveedor</Label>
                  <Select
                    value={localLLM.vision_llm_provider}
                    onValueChange={(v) => {
                      const firstModel = MODELS_BY_PROVIDER[v]?.[0] || '';
                      setLocalLLM(prev => ({
                        ...prev,
                        vision_llm_provider: v,
                        vision_llm_model: firstModel
                      }));
                    }}
                  >
                    <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-blue-500/20">
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
                  <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                  <Select
                    value={localLLM.vision_llm_model}
                    onValueChange={(v) => setLocalLLM(prev => ({ ...prev, vision_llm_model: v }))}
                  >
                    <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-blue-500/20">
                      <SelectValue placeholder="Modelo" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[300px] p-2">
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

            <div className="pt-4 border-t border-border/50 space-y-4">
              <div className="space-y-2">
                <Label className="flex justify-between">
                  <span>Creatividad (Temperatura)</span>
                  <span className="text-primary font-mono">{localLLM.llm_temperature}</span>
                </Label>
                <input
                  type="range"
                  min="0" max="1" step="0.1"
                  value={localLLM.llm_temperature}
                  onChange={(e) => setLocalLLM(prev => ({ ...prev, llm_temperature: parseFloat(e.target.value) }))}
                  className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="use_prompt_tooling"
                  checked={localLLM.use_prompt_tooling}
                  onCheckedChange={(checked) => setLocalLLM(prev => ({ ...prev, use_prompt_tooling: checked }))}
                />
                <Label htmlFor="use_prompt_tooling">Forzar Tooling por Prompt (Experimental)</Label>
              </div>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label>API Base URL (Opcional)</Label>
                <Input
                  placeholder="https://api.openai.com/v1"
                  value={localLLM.llm_api_base}
                  onChange={(e) => setLocalLLM(prev => ({ ...prev, llm_api_base: e.target.value }))}
                  className="bg-background/50 backdrop-blur-sm border-primary/20"
                />
                <p className="text-[11px] text-muted-foreground italic">
                  Útil para Ollama local o proxies personalizados.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuración de TTS */}
      <Card className="border-none shadow-md bg-gradient-to-br from-card to-secondary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">TTS</Badge>
            Text-to-Speech (Voz)
          </CardTitle>
          <CardDescription>
            Configura el servicio de conversión de texto a voz.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Proveedor de TTS</Label>
                <Select
                  value={localTTS.tts_provider}
                  onValueChange={(v) => {
                    const firstVoice = TTS_VOICES_BY_PROVIDER[v]?.[0] || '';
                    setLocalTTS(prev => ({ ...prev, tts_provider: v, tts_voice: firstVoice }));
                  }}
                >
                  <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="Selecciona un proveedor" />
                  </SelectTrigger>
                  <SelectContent>
                    {TTS_PROVIDERS.map(p => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {localTTS.tts_provider === 'azure' && (
                <div className="space-y-2">
                  <Label>Región de Azure</Label>
                  <Input
                    placeholder="eastus"
                    value={localTTS.tts_region || ''}
                    onChange={(e) => setLocalTTS(prev => ({ ...prev, tts_region: e.target.value }))}
                    className="bg-background/50 backdrop-blur-sm border-primary/20"
                  />
                  <p className="text-[11px] text-muted-foreground italic">
                    Ej: eastus, westus2, southeastasia.
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <Label>Voz</Label>
                <Select
                  value={localTTS.tts_voice}
                  onValueChange={(v) => setLocalTTS(prev => ({ ...prev, tts_voice: v }))}
                >
                  <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="Selecciona una voz" />
                  </SelectTrigger>
                  <SelectContent className="max-h-[300px]">
                    {(TTS_VOICES_BY_PROVIDER[localTTS.tts_provider] || []).map(v => (
                      <SelectItem key={v} value={v}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="flex justify-between">
                  <span>Velocidad de Habla</span>
                  <span className="text-green-500 font-mono">{localTTS.tts_speed}x</span>
                </Label>
                <input
                  type="range"
                  min="0.5" max="2.0" step="0.1"
                  value={localTTS.tts_speed}
                  onChange={(e) => setLocalTTS(prev => ({ ...prev, tts_speed: parseFloat(e.target.value) }))}
                  className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-green-500"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground uppercase tracking-widest">
                  <span>Lento</span>
                  <span>Rápido</span>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              {/* Aquí se podría añadir un campo para tts_model si los proveedores lo soportan */}
              {/* <div className="space-y-2">
                <Label>Modelo TTS</Label>
                <Input
                  placeholder="tts-1"
                  value={localTTS.tts_model}
                  onChange={(e) => setLocalTTS(prev => ({ ...prev, tts_model: e.target.value }))}
                  className="bg-background/50 backdrop-blur-sm border-primary/20"
                />
              </div> */}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuración de Embeddings */}
      <Card className="border-none shadow-md bg-gradient-to-br from-card to-secondary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Badge variant="outline" className="bg-purple-500/10 text-purple-500 border-purple-500/20">Embeddings</Badge>
            Generación de Embeddings
          </CardTitle>
          <CardDescription>
            Configura el servicio para generar representaciones vectoriales de texto.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Proveedor de Embeddings</Label>
                <Select
                  value={localEmbedding.embedding_provider}
                  onValueChange={(v) => {
                    const firstModel = EMBEDDING_MODELS_BY_PROVIDER[v]?.[0] || '';
                    setLocalEmbedding(prev => ({ ...prev, embedding_provider: v, embedding_model: firstModel }));
                  }}
                >
                  <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="Selecciona un proveedor" />
                  </SelectTrigger>
                  <SelectContent>
                    {EMBEDDING_PROVIDERS.map(p => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Modelo de Embeddings</Label>
                <Select
                  value={localEmbedding.embedding_model}
                  onValueChange={(v) => setLocalEmbedding(prev => ({ ...prev, embedding_model: v }))}
                >
                  <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="Selecciona un modelo" />
                  </SelectTrigger>
                  <SelectContent className="max-h-[300px]">
                    {(EMBEDDING_MODELS_BY_PROVIDER[localEmbedding.embedding_provider] || []).map(m => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>API Key Name (Opcional)</Label>
                <Input
                  placeholder="OPENAI_API_KEY"
                  value={localEmbedding.embedding_api_key_name}
                  onChange={(e) => setLocalEmbedding(prev => ({ ...prev, embedding_api_key_name: e.target.value }))}
                  className="bg-background/50 backdrop-blur-sm border-primary/20"
                />
                <p className="text-[11px] text-muted-foreground italic">
                  Nombre de la clave API guardada en tus secretos (ej. OPENAI_API_KEY).
                </p>
              </div>
              <div className="space-y-2">
                <Label>API Base URL (Opcional)</Label>
                <Input
                  placeholder="http://localhost:11434"
                  value={localEmbedding.embedding_api_base}
                  onChange={(e) => setLocalEmbedding(prev => ({ ...prev, embedding_api_base: e.target.value }))}
                  className="bg-background/50 backdrop-blur-sm border-primary/20"
                />
                <p className="text-[11px] text-muted-foreground italic">
                  Útil para Ollama local o proxies personalizados.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="pt-4">
        <Button onClick={handleSaveAllSettings} disabled={loading} className="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20">
          {loading ? 'Guardando...' : 'Guardar Todas las Configuraciones de IA'}
        </Button>
      </div>

      <Card className="border-none shadow-md bg-secondary/5">
        <CardHeader>
          <CardTitle className="text-lg">Llaves de API (Secrets)</CardTitle>
          <CardDescription>Gestiona tus credenciales de forma segura. Se almacenan cifradas en el servidor.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col md:flex-row gap-4 items-end bg-background/40 p-4 rounded-xl border border-border/50">
            <div className="grid w-full gap-2">
              <Label>Proveedor</Label>
              <Select value={newKey.provider} onValueChange={(v) => setNewKey(prev => ({ ...prev, provider: v }))}>
                <SelectTrigger><SelectValue placeholder="Proveedor" /></SelectTrigger>
                <SelectContent>
                  {[...LLM_PROVIDERS, ...TTS_PROVIDERS, ...EMBEDDING_PROVIDERS, ...SEARCH_PROVIDERS].filter(p => p.env_key).map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid w-full gap-2">
              <Label>API Key</Label>
              <Input
                type="password"
                placeholder="sk-..."
                value={newKey.value}
                onChange={(e) => setNewKey(prev => ({ ...prev, value: e.target.value }))}
              />
            </div>
            <Button onClick={handleSaveKey} variant="secondary" className="w-full md:w-auto">Guardar</Button>
          </div>

          <div className="space-y-2">
            {secrets.map((s) => (
              <div key={s.key_name} className="flex items-center justify-between p-3 rounded-lg bg-background/60 border border-border/40 group hover:border-primary/30 transition-all">
                <div>
                  <div className="text-sm font-medium flex items-center gap-2">
                    {s.key_name}
                    <Badge variant="outline" className="text-[10px] py-0 h-4">Active</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground font-mono mt-1">{s.masked_value}</div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={async () => {
                    if (confirm(`¿Eliminar ${s.key_name}?`)) {
                      await apiClient.delete(`/api/users/me/secrets/${s.key_name}`);
                      toast.success('Secreto eliminado');
                      fetchSecrets();
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
const PasswordUpdateForm: React.FC = () => {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      toast.error('Las nuevas contraseñas no coinciden.');
      return;
    }

    if (newPassword.length < 8) {
      toast.error('La contraseña debe tener al menos 8 caracteres.');
      return;
    }

    setLoading(true);
    try {
      await apiClient.put('/api/users/me/password', {
        current_password: user?.has_password ? currentPassword : null,
        new_password: newPassword
      });

      toast.success('Contraseña actualizada exitosamente.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      console.error('Error updating password:', error);
      toast.error(error.response?.data?.detail || 'Error al actualizar la contraseña.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      {user?.has_password && (
        <div className="grid w-full gap-1.5">
          <Label htmlFor="current-password">Contraseña Actual</Label>
          <Input
            type="password"
            id="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
          />
        </div>
      )}
      <div className="grid w-full gap-1.5">
        <Label htmlFor="new-password">Nueva Contraseña</Label>
        <Input
          type="password"
          id="new-password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
          minLength={8}
        />
      </div>
      <div className="grid w-full gap-1.5">
        <Label htmlFor="confirm-password">Confirmar Nueva Contraseña</Label>
        <Input
          type="password"
          id="confirm-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          minLength={8}
        />
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? 'Actualizando...' : 'Actualizar Contraseña'}
      </Button>
    </form>
  );
};

const SettingsPage: React.FC = () => {
  const { settings, loading, error, getSettings, updateSettings } = useUserSettings();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('personal-data');
  const [localSettings, setLocalSettings] = useState(settings);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [showAddMemory, setShowAddMemory] = useState(false);
  const [newMemory, setNewMemory] = useState({
    title: '',
    content: '',
    type: 'general'
  });

  useEffect(() => {
    getSettings();
  }, []);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  useEffect(() => {
    if (activeTab === 'memories' && !memories.length) {
      fetchMemories();
    }
  }, [activeTab]);

  const fetchMemories = async () => {
    setMemoryLoading(true);
    try {
      const response = await apiClient.get('/api/memories'); // Usar apiClient
      setMemories(response.data || []); // El endpoint devuelve directamente la lista de memorias
    } catch (error) {
      toast.error('No se pudieron cargar las memorias');
    } finally {
      setMemoryLoading(false);
    }
  };

  const addMemory = async () => {
    if (!newMemory.title || !newMemory.content) {
      toast.error('Por favor, completa el título y el contenido');
      return;
    }

    try {
      await apiClient.post('/api/memories', { // Usar apiClient
        title: newMemory.title,
        content: newMemory.content,
        type: newMemory.type
      });

      toast.success('Memoria añadida exitosamente');
      setNewMemory({ title: '', content: '', type: 'general' });
      setShowAddMemory(false);
      fetchMemories();
    } catch (error) {
      toast.error('No se pudo añadir la memoria');
    }
  };

  const deleteMemory = async (memoryId: string) => {
    try {
      // Necesitaremos un endpoint DELETE para memorias si queremos esta funcionalidad
      // Por ahora, solo loguearemos que no está implementado
      toast.info('La eliminación de memorias aún no está implementada.');
      console.warn(`Intento de eliminar memoria con ID: ${memoryId}. Funcionalidad no implementada.`);
      // const response = await fetch(`/api/memories/${memoryId}`, { // Esto sería el futuro endpoint
      //   method: 'DELETE',
      // });

      // if (response.ok) {
      //   toast.success('Memoria eliminada exitosamente');
      //   fetchMemories();
      // } else {
      //   throw new Error('Error al eliminar memoria');
      // }
    } catch (error) {
      toast.error('No se pudo eliminar la memoria');
    }
  };

  if (error) {
    toast.error(error);
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { id, value } = e.target;
    setLocalSettings(prev => prev ? { ...prev, [id]: value } : null);
  };

  const handleSwitchChange = (id: string, checked: boolean) => {
    setLocalSettings(prev => prev ? { ...prev, [id]: checked } : null);
  };

  const handleSelectChange = (id: string, value: string) => {
    setLocalSettings(prev => prev ? { ...prev, [id]: value } : null);
  };

  const handlePersonalDataSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localSettings?.name || !localSettings?.email) {
      toast.error('El nombre y el email son campos obligatorios.');
      return;
    }
    try {
      await updateSettings({
        name: localSettings.name,
        email: localSettings.email,
        phone: localSettings.phone,
        bio: localSettings.bio,
      });
      toast.success('Datos personales actualizados exitosamente.');
    } catch (err) {
      toast.error('Error al actualizar los datos personales.');
    }
  };

  const handleModulePreferenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localSettings) return;
    try {
      await updateSettings({
        profiles_enabled: localSettings.profiles_enabled,
        galleries_enabled: localSettings.galleries_enabled,
        forms_enabled: localSettings.forms_enabled,
        theme: localSettings.theme,
        notifications_email: localSettings.notifications_email,
        notifications_push: localSettings.notifications_push,
        language: localSettings.language,
        privacy_data_sharing: localSettings.privacy_data_sharing,
      });
      toast.success('Módulos y preferencias actualizados exitosamente.');
    } catch (err) {
      toast.error('Error al actualizar módulos y preferencias.');
    }
  };

  if (loading && !settings) {
    return <div>Cargando...</div>;
  }

  if (!localSettings) {
    return <div>No se pudo cargar la configuración.</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Configuración de Usuario</h1>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="personal-data">Datos Personales</TabsTrigger>
          <TabsTrigger value="llm-config">Modelos e IA</TabsTrigger>
          <TabsTrigger value="modules-preferences">Módulos y Preferencias</TabsTrigger>
          <TabsTrigger value="memories">Memorias</TabsTrigger>
          <TabsTrigger value="security">Seguridad</TabsTrigger>
          <TabsTrigger value="sync">Sincronización</TabsTrigger>
        </TabsList>
        <TabsContent value="personal-data">
          <h2 className="text-xl font-semibold mb-3">Datos Personales</h2>
          <form onSubmit={handlePersonalDataSubmit} className="space-y-4">
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="name">Nombre</Label>
              <Input type="text" id="name" placeholder="Tu Nombre" value={localSettings.name || ''} onChange={handleChange} />
            </div>
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input type="email" id="email" placeholder="tu@email.com" value={localSettings.email || ''} onChange={handleChange} />
            </div>
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <Label htmlFor="phone">Teléfono</Label>
              <Input type="tel" id="phone" placeholder="+1234567890" value={localSettings.phone || ''} onChange={handleChange} />
            </div>
            <div className="grid w-full gap-1.5">
              <Label htmlFor="bio">Biografía</Label>
              <Textarea id="bio" placeholder="Cuéntanos sobre ti..." value={localSettings.bio || ''} onChange={handleChange} />
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? 'Guardando...' : 'Guardar Cambios'}
            </Button>
          </form>
        </TabsContent>
        <TabsContent value="llm-config">
          <LLMSettingsForm />
        </TabsContent>
        <TabsContent value="modules-preferences">
          <h2 className="text-xl font-semibold mb-3">Módulos y Preferencias</h2>
          <form onSubmit={handleModulePreferenceSubmit} className="space-y-4">
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Módulos</h3>
              <div className="flex items-center space-x-2">
                <Switch
                  id="profiles_enabled"
                  checked={localSettings.profiles_enabled}
                  onCheckedChange={(checked) => handleSwitchChange('profiles_enabled', checked)}
                  disabled={loading}
                />
                <Label htmlFor="profiles_enabled">Módulo de Perfiles</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="galleries_enabled"
                  checked={localSettings.galleries_enabled}
                  onCheckedChange={(checked) => handleSwitchChange('galleries_enabled', checked)}
                  disabled={loading}
                />
                <Label htmlFor="galleries_enabled">Módulo de Galerías</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="forms_enabled"
                  checked={localSettings.forms_enabled}
                  onCheckedChange={(checked) => handleSwitchChange('forms_enabled', checked)}
                  disabled={loading}
                />
                <Label htmlFor="forms_enabled">Módulo de Formularios</Label>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-medium">Preferencias Adicionales</h3>
              <div className="grid w-full max-w-sm items-center gap-1.5">
                <Label htmlFor="theme">Tema</Label>
                <Select value={localSettings.theme} onValueChange={(value) => handleSelectChange('theme', value)} disabled={loading}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Selecciona un tema" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Claro</SelectItem>
                    <SelectItem value="dark">Oscuro</SelectItem>
                    <SelectItem value="system">Sistema</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="notifications_email"
                  checked={localSettings.notifications_email}
                  onCheckedChange={(checked) => handleSwitchChange('notifications_email', checked)}
                  disabled={loading}
                />
                <Label htmlFor="notifications_email">Notificaciones por Email</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="notifications_push"
                  checked={localSettings.notifications_push}
                  onCheckedChange={(checked) => handleSwitchChange('notifications_push', checked)}
                  disabled={loading}
                />
                <Label htmlFor="notifications_push">Notificaciones Push</Label>
              </div>
              <div className="grid w-full max-w-sm items-center gap-1.5">
                <Label htmlFor="language">Idioma</Label>
                <Select value={localSettings.language} onValueChange={(value) => handleSelectChange('language', value)} disabled={loading}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Selecciona un idioma" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="es">Español</SelectItem>
                    <SelectItem value="en">Inglés</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="privacy_data_sharing"
                  checked={localSettings.privacy_data_sharing}
                  onCheckedChange={(checked) => handleSwitchChange('privacy_data_sharing', checked)}
                  disabled={loading}
                />
                <Label htmlFor="privacy_data_sharing">Compartir Datos para Mejoras</Label>
              </div>
            </div>
            <Button type="submit" disabled={loading}>
              {loading ? 'Guardando...' : 'Guardar Preferencias'}
            </Button>
          </form>
        </TabsContent>
        <TabsContent value="memories">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold mb-3">Memorias Guardadas</h2>
              <Button onClick={() => setShowAddMemory(true)} className="flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Añadir Memoria
              </Button>
            </div>

            {showAddMemory && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Añadir Nueva Memoria</CardTitle>
                  <CardDescription>Registra una nueva memoria manualmente</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid w-full max-w-sm items-center gap-1.5">
                    <Label htmlFor="memory-title">Título</Label>
                    <Input
                      id="memory-title"
                      placeholder="Título de la memoria"
                      value={newMemory.title}
                      onChange={(e) => setNewMemory({ ...newMemory, title: e.target.value })}
                    />
                  </div>
                  <div className="grid w-full max-w-sm items-center gap-1.5">
                    <Label htmlFor="memory-type">Tipo</Label>
                    <Select value={newMemory.type} onValueChange={(value) => setNewMemory({ ...newMemory, type: value })}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general">General</SelectItem>
                        <SelectItem value="personal">Personal</SelectItem>
                        <SelectItem value="work">Trabajo</SelectItem>
                        <SelectItem value="study">Estudio</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid w-full gap-1.5">
                    <Label htmlFor="memory-content">Contenido</Label>
                    <Textarea
                      id="memory-content"
                      placeholder="Escribe el contenido de tu memoria..."
                      value={newMemory.content}
                      onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
                      rows={6}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={addMemory}>Guardar Memoria</Button>
                    <Button variant="outline" onClick={() => setShowAddMemory(false)}>Cancelar</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {memoryLoading ? (
              <div>Cargando memorias...</div>
            ) : memories.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No tienes memorias guardadas aún. ¡Comienza añadiendo tu primera memoria!
              </div>
            ) : (
              <div className="grid gap-4">
                {memories.map((memory) => (
                  <Card key={memory.id}>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            {memory.title}
                            <Badge variant="secondary">{memory.type}</Badge>
                          </CardTitle>
                          <CardDescription className="flex items-center gap-4 text-sm">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-4 w-4" />
                              Creada: {new Date(memory.created_at).toLocaleDateString()}
                            </span>
                            <span className="flex items-center gap-1">
                              <User className="h-4 w-4" />
                              Actualizada: {new Date(memory.updated_at).toLocaleDateString()}
                            </span>
                          </CardDescription>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" className="flex items-center gap-2">
                            <Eye className="h-4 w-4" />
                            Ver
                          </Button>
                          <Button variant="outline" size="sm" className="flex items-center gap-2">
                            <Edit className="h-4 w-4" />
                            Editar
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            className="flex items-center gap-2"
                            onClick={() => deleteMemory(memory.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                            Eliminar
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-700 whitespace-pre-wrap">{memory.content}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Seguridad de la Cuenta</CardTitle>
              <CardDescription>
                Gestiona tu contraseña y la seguridad de tu cuenta.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PasswordUpdateForm />
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="sync">
          <Card>
            <CardHeader>
              <CardTitle>Sincronización CalDAV</CardTitle>
              <CardDescription>
                Sincroniza tus eventos y tareas con cualquier cliente de calendario compatible con CalDAV.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="caldav-url">URL de Sincronización CalDAV</Label>
                <div className="flex items-center space-x-2 mt-1">
                  <Input
                    id="caldav-url"
                    readOnly
                    value={`${window.location.origin}/api/caldav/calendars/${user?.account_id}/default/`}
                  />
                  <Button
                    onClick={() => {
                      if (typeof window !== "undefined") {
                        navigator.clipboard.writeText(`${window.location.origin}/api/caldav/calendars/${user?.account_id}/default/`);
                        toast.success('URL copiada al portapapeles');
                      }
                    }}
                  >
                    Copiar
                  </Button>
                </div>
              </div>
              <div>
                <h3 className="font-semibold">Instrucciones</h3>
                <ol className="list-decimal list-inside text-sm text-gray-600 mt-2 space-y-1">
                  <li>Copia la URL de sincronización de arriba.</li>
                  <li>
                    **Para Android, recomendamos la aplicación DAVx⁵:**
                    <ul className="list-disc list-inside ml-4">
                      <li>Instala DAVx⁵ desde Google Play Store o F-Droid.</li>
                      <li>Abre DAVx⁵ y crea una nueva cuenta de "Login con URL y nombre de usuario".</li>
                      <li>Pega la URL de sincronización de arriba.</li>
                      <li>Introduce tu nombre de usuario (tu email) y tu contraseña de KognitoAI.</li>
                      <li>Sigue las instrucciones en pantalla para configurar la sincronización de calendarios y tareas.</li>
                    </ul>
                  </li>
                  <li>**Para otras aplicaciones de calendario (ej. Google Calendar, Apple Calendar, Thunderbird):**
                    <ul className="list-disc list-inside ml-4">
                      <li>Abre la configuración de tu aplicación de calendario.</li>
                      <li>Busca la opción para añadir una nueva cuenta de calendario "desde URL" o "CalDAV".</li>
                      <li>Pega la URL y proporciona tu nombre de usuario (tu email) y tu contraseña de KognitoAI.</li>
                    </ul>
                  </li>
                  <li>¡Tus eventos y tareas se sincronizarán automáticamente!</li>
                </ol>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SettingsPage;