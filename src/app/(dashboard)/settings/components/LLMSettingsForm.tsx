"use client";

import React, { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import apiClient from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Brain, Zap, Image as ImageIcon, RefreshCw, Globe, Trash2 } from 'lucide-react';

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
  { id: 'nvidia', name: '🟢 NVIDIA AI Catalog', env_key: 'NVIDIA_API_KEY' },
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
  nvidia: [
    'nvidia/meta/llama-3.3-70b-instruct',
    'nvidia/nvidia/llama-3.1-nemotron-70b-instruct',
    'nvidia/mistralai/mistral-large-2-instruct',
    'nvidia/deepseek-ai/deepseek-r1',
    'nvidia/qwen/qwen2.5-72b-instruct',
  ],
};

const TTS_PROVIDERS = [
  { id: 'google', name: 'Google Cloud TTS', env_key: 'GOOGLE_APPLICATION_CREDENTIALS' },
  { id: 'openai', name: 'OpenAI TTS', env_key: 'OPENAI_API_KEY' },
  { id: 'openai-compatible', name: '🖥️ Local / OpenAI Compatible (TTS)', env_key: null },
  { id: 'kokoro', name: '🚀 Kokoro TTS (Local/Docker)', env_key: null },
  { id: 'coquitts', name: '🐸 Coqui TTS / XTTS v2 (Local)', env_key: null },
  { id: 'azure', name: 'Azure TTS', env_key: 'AZURE_TTS_KEY' },
];

const TTS_VOICES_BY_PROVIDER: Record<string, string[]> = {
  google: [
    'es-MX-DaliaNeural', 'es-MX-JorgeNeural', 'es-MX-AndresNeural', 'es-MX-FernandaNeural',
    'es-ES-ElviraNeural', 'es-ES-AlvaroNeural',
    'en-US-Neural2-A', 'en-US-Neural2-C', 'en-US-Neural2-D', 'en-US-Neural2-E',
  ],
  openai: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
  'openai-compatible': ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
  coquitts: ['Ana Maria', 'Luis', 'Claribel Dervla', 'Daisy Milana', 'Badrani Sade', 'Eugenio Matthias', 'Adia Sayo', 'Abrahan Mack'],
  azure: [
    'es-MX-DaliaNeural', 'es-MX-JorgeNeural', 'es-MX-CandelaNeural', 'es-MX-GerardoNeural',
    'es-ES-ElviraNeural', 'es-ES-AlvaroNeural', 'es-ES-LaiaNeural', 'es-ES-ArnauNeural',
    'en-US-JennyNeural', 'en-US-GuyNeural', 'en-US-AriaNeural', 'en-US-DavisNeural',
  ],
};

const EMBEDDING_PROVIDERS = [
  { id: 'kognito-internal', name: 'Kognito Interno', env_key: null },
  { id: 'ollama', name: 'Ollama (Local)', env_key: null },
  { id: 'ollama-cloud', name: '☁️ Ollama Cloud', env_key: 'OLLAMA_API_KEY' },
  { id: 'openai', name: 'OpenAI Embeddings', env_key: 'OPENAI_API_KEY' },
  { id: 'google', name: 'Google Embeddings', env_key: 'GOOGLE_API_KEY' },
];

const SEARCH_PROVIDERS = [
  { id: 'tavily', name: 'Tavily Search', env_key: 'TAVILY_API_KEY' },
];

const EMBEDDING_MODELS_BY_PROVIDER: Record<string, string[]> = {
  'kognito-internal': ['paraphrase-multilingual-mpnet-base-v2'],
  ollama: ['nomic-embed-text', 'llama3', 'mistral'],
  'ollama-cloud': ['nomic-embed-text', 'llama3', 'mistral'],
  openai: ['text-embedding-ada-002', 'text-embedding-3-small', 'text-embedding-3-large'],
  google: ['text-embedding-004', 'text-embedding-gecko'],
};

const RERANKER_PROVIDERS = [
  { id: 'local', name: 'Local (HuggingFace)', env_key: null },
  { id: 'openrouter', name: 'OpenRouter (Nvidia Llama / Cohere)', env_key: 'OPENROUTER_API_KEY' },
  { id: 'cohere', name: 'Cohere Rerank', env_key: 'COHERE_API_KEY' },
];

const RERANKER_MODELS_BY_PROVIDER: Record<string, string[]> = {
  local: ['BAAI/bge-reranker-base', 'BAAI/bge-reranker-large'],
  openrouter: ['nvidia/llama-nemotron-rerank-vl-1b-v2:free', 'cohere/rerank-v3.0'],
  cohere: ['rerank-english-v3.0', 'rerank-multilingual-v3.0'],
};


interface UserSecret {
  key_name: string;
  description?: string;
  masked_value: string;
}

export const LLMSettingsForm: React.FC = () => {
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
    tts_model: settings?.tts_model || 'tts-1',
    tts_voice: settings?.tts_voice || 'es-MX-DaliaNeural',
    tts_speed: settings?.tts_speed || 1.0,
    tts_region: settings?.tts_region || '',
    tts_api_base: settings?.tts_api_base || '',
  });

  const [localEmbedding, setLocalEmbedding] = useState({
    embedding_provider: settings?.embedding_provider || 'kognito-internal',
    embedding_model: settings?.embedding_model || 'paraphrase-multilingual-mpnet-base-v2',
    embedding_api_key_name: settings?.embedding_api_key_name || '',
    embedding_api_base: settings?.embedding_api_base || '',
  });

  const [localReranker, setLocalReranker] = useState({
    reranker_provider: settings?.reranker_provider || 'local',
    reranker_model: settings?.reranker_model || 'BAAI/bge-reranker-base',
    reranker_api_base: settings?.reranker_api_base || '',
  });

  const [mainModels, setMainModels] = useState<any[]>([]);
  const [fastModels, setFastModels] = useState<any[]>([]);
  const [visionModels, setVisionModels] = useState<any[]>([]);
  const [ttsModels, setTtsModels] = useState<string[]>([]);
  const [ttsVoices, setTtsVoices] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState({ main: false, fast: false, vision: false, tts: false, voices: false });

  const fetchModels = async (provider: string, type: 'main' | 'fast' | 'vision', options: { apiBase?: string; refresh?: boolean } = {}) => {
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
      const models = resp?.data || [];
      if (type === 'main') setMainModels(models);
      else if (type === 'fast') setFastModels((prev: any[]) => [...models]);
      else if (type === 'vision') setVisionModels(models);
    } catch (e) {
      console.error(`Error fetching ${type} models for ${provider}:`, e);
    } finally {
      setLoadingModels(prev => ({ ...prev, [type]: false }));
    }
  };

  const fetchTTSModels = async (provider: string, apiBase?: string) => {
    if (!['openai', 'openai-compatible', 'kokoro', 'coquitts'].includes(provider)) {
      setTtsModels([]);
      return;
    }

    setLoadingModels(prev => ({ ...prev, tts: true }));
    try {
      const url = `/api/text-to-speech/models?provider=${provider}${apiBase ? `&api_base=${encodeURIComponent(apiBase)}` : ''}`;
      const resp = await apiClient.get(url);
      setTtsModels(resp.data.models || []);
    } catch (e) {
      console.error(`Error fetching TTS models for ${provider}:`, e);
      setTtsModels([]);
    } finally {
      setLoadingModels(prev => ({ ...prev, tts: false }));
    }
  };

  const fetchTTSVoices = async (provider: string, apiBase?: string) => {
    if (!['openai', 'openai-compatible', 'kokoro', 'coquitts'].includes(provider)) {
      setTtsVoices([]);
      return;
    }

    setLoadingModels(prev => ({ ...prev, voices: true }));
    try {
      const url = `/api/text-to-speech/voices?provider=${provider}${apiBase ? `&api_base=${encodeURIComponent(apiBase)}` : ''}`;
      const resp = await apiClient.get(url);
      setTtsVoices(resp.data.voices || []);
    } catch (e) {
      console.error(`Error fetching TTS voices for ${provider}:`, e);
      setTtsVoices([]);
    } finally {
      setLoadingModels(prev => ({ ...prev, voices: false }));
    }
  };

  useEffect(() => {
    if (['openai', 'openai-compatible', 'kokoro', 'coquitts'].includes(localTTS.tts_provider)) {
      fetchTTSModels(localTTS.tts_provider, localTTS.tts_api_base);
      fetchTTSVoices(localTTS.tts_provider, localTTS.tts_api_base);
    }
  }, [localTTS.tts_provider, localTTS.tts_api_base]);

  const renderModelItem = (m: any, currentProvider: string) => {
    const isString = typeof m === 'string';
    const id = isString ? m : m.id;
    const name = isString ? m : (m.name || m.id);
    const isGemini = currentProvider === 'gemini' || id.startsWith('gemini/');
    const isOpenRouter = currentProvider === 'openrouter' || id.startsWith('openrouter/');
    const isKilocode = currentProvider === 'kilocode' || id.startsWith('kilocode/');
    const isNVIDIA = currentProvider === 'nvidia' || id.startsWith('nvidia/');

    if (isOpenRouter || isGemini || isKilocode || isNVIDIA) {
      let badgeColor = "bg-blue-500/10 text-blue-500 border-blue-500/20";
      let badgeText = isKilocode ? "KiloCode" : isNVIDIA ? "NVIDIA" : "OpenRouter";
      let borderColor = isNVIDIA ? "border-emerald-500" : "border-blue-500";
      let bgColor = isNVIDIA ? "bg-emerald-500/5" : "bg-blue-500/5";

      if (isNVIDIA) {
        badgeText = "NVIDIA";
        badgeColor = "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      } else if (isGemini) {
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
        tts_api_base: settings.tts_api_base || '',
      });
      setLocalEmbedding({
        embedding_provider: settings.embedding_provider || 'kognito-internal',
        embedding_model: settings.embedding_model || 'paraphrase-multilingual-mpnet-base-v2',
        embedding_api_key_name: settings.embedding_api_key_name || '',
        embedding_api_base: settings.embedding_api_base || '',
      });
      setLocalReranker({
        reranker_provider: settings.reranker_provider || 'local',
        reranker_model: settings.reranker_model || 'BAAI/bge-reranker-base',
        reranker_api_base: settings.reranker_api_base || '',
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
        ...localReranker,
        tts_region: localTTS.tts_provider === 'azure' ? localTTS.tts_region : undefined,
      });
      toast.success('Configuración de IA, TTS, Embeddings y Reranker guardada');
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
    const rerankerProvider = RERANKER_PROVIDERS.find(p => p.id === newKey.provider);

    if (llmProvider) envKey = llmProvider.env_key;
    else if (ttsProvider) {
      if (newKey.provider === 'azure') {
        envKey = 'AZURE_TTS_KEY';
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
    else if (rerankerProvider) {
      envKey = rerankerProvider.env_key;
      description = `API Key para ${rerankerProvider.name}`;
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
                       setLocalLLM(prev => ({
                         ...prev,
                         llm_provider: v,
                         llm_model: '',
                         llm_api_base: v === 'ollama-cloud' ? '' : prev.llm_api_base
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
                  <div className="flex items-center justify-between">
                    <Label className="text-[11px] font-bold uppercase text-muted-foreground">Modelo</Label>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-4 w-4"
                      onClick={() => fetchModels(localLLM.llm_provider, 'main', { apiBase: localLLM.llm_api_base, refresh: true })}
                      title="Refrescar modelos"
                    >
                      <RefreshCw className={`h-3 w-3 ${loadingModels.main ? 'animate-spin' : ''}`} />
                    </Button>
                  </div>
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
                       setLocalLLM(prev => ({
                         ...prev,
                         fast_llm_provider: v,
                         fast_llm_model: ''
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
                       setLocalLLM(prev => ({
                         ...prev,
                         vision_llm_provider: v,
                         vision_llm_model: ''
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
                <Label className="flex items-center gap-1.5 mb-2">
                  <Globe className="h-4 w-4 text-muted-foreground" />
                  <span>API Base URL {localLLM.llm_provider === 'openai-compatible' ? <span className="text-red-500">*</span> : '(Opcional)'}</span>
                </Label>
                <Input
                  placeholder={
                    localLLM.llm_provider === 'openai-compatible' ? 'http://host.docker.internal:8080/v1' :
                    localLLM.llm_provider === 'ollama' ? 'http://host.docker.internal:11434' :
                    localLLM.llm_provider === 'ollama-cloud' ? 'https://ollama.com' :
                    'https://api.openai.com/v1'
                  }
                  value={localLLM.llm_api_base}
                  onChange={(e) => setLocalLLM(prev => ({ ...prev, llm_api_base: e.target.value }))}
                  className="bg-background/50 backdrop-blur-sm border-primary/20 focus:border-primary/50 transition-all font-mono text-sm"
                />
                <div className="mt-1.5 p-2 rounded-lg bg-muted/30 border border-muted-foreground/10">
                  <p className="text-[11px] text-muted-foreground leading-relaxed italic">
                    {localLLM.llm_provider === 'openai-compatible' ? (
                      <>
                        <strong>Local AI / LM Studio:</strong> Escribe la URL de tu servidor local.<br/>
                        Ej. Docker: <code className="bg-primary/10 px-1 rounded">http://host.docker.internal:8080/v1</code><br/>
                        Ej. Sin Docker: <code className="bg-primary/10 px-1 rounded">http://localhost:8080/v1</code>
                      </>
                    ) : localLLM.llm_provider === 'ollama' ? (
                      <>
                        <strong>Protip Ollama:</strong> Si usas Docker, prueba con <code className="bg-primary/10 px-1 rounded">http://host.docker.internal:11434</code>. Si es local fuera de docker, usa <code className="bg-primary/10 px-1 rounded">http://localhost:11434</code>.
                      </>
                    ) : localLLM.llm_provider === 'ollama-cloud' ? (
                      <>
                        <strong>Ollama Cloud:</strong> Ingresa la URL de tu instancia de Ollama en la nube y tu API Key.
                      </>
                    ) : (
                      "Útil para proveedores compatibles con OpenAI, Ollama local o proxies personalizados."
                    )}
                  </p>
                </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuración de Reranker */}
      <Card className="border-none shadow-md bg-gradient-to-br from-card to-secondary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Badge variant="outline" className="bg-orange-500/10 text-orange-500 border-orange-500/20">Reranker</Badge>
            Reordenamiento de Resultados (Reranker)
          </CardTitle>
          <CardDescription>
            Configura el modelo que optimiza la relevancia de los documentos recuperados de memoria o búsqueda web.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Proveedor del Reranker</Label>
                <Select
                  value={localReranker.reranker_provider}
                  onValueChange={(v) => {
                    const firstModel = RERANKER_MODELS_BY_PROVIDER[v]?.[0] || '';
                    setLocalReranker(prev => ({ 
                      ...prev, 
                      reranker_provider: v, 
                      reranker_model: firstModel 
                    }));
                  }}
                >
                  <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="Selecciona un proveedor" />
                  </SelectTrigger>
                  <SelectContent>
                    {RERANKER_PROVIDERS.map(p => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Modelo Reranker</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Escribe o selecciona un modelo (ej. nvidia/llama-nemotron-rerank-vl-1b-v2:free)"
                    value={localReranker.reranker_model}
                    onChange={(e) => setLocalReranker(prev => ({ ...prev, reranker_model: e.target.value }))}
                    className="bg-background/50 backdrop-blur-sm border-primary/20"
                  />
                  {RERANKER_MODELS_BY_PROVIDER[localReranker.reranker_provider] && (
                    <Select
                      value={localReranker.reranker_model}
                      onValueChange={(v) => setLocalReranker(prev => ({ ...prev, reranker_model: v }))}
                    >
                      <SelectTrigger className="w-[180px] bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors">
                        <SelectValue placeholder="Sugeridos" />
                      </SelectTrigger>
                      <SelectContent>
                        {RERANKER_MODELS_BY_PROVIDER[localReranker.reranker_provider].map(m => (
                          <SelectItem key={m} value={m}>{m.split('/').pop() || m}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>API Base URL (Opcional)</Label>
                <Input
                  placeholder={
                    localReranker.reranker_provider === 'openrouter' ? 'https://openrouter.ai/api/v1' :
                    localReranker.reranker_provider === 'cohere' ? 'https://api.cohere.ai/v1' :
                    'http://localhost:8000/v1'
                  }
                  value={localReranker.reranker_api_base}
                  onChange={(e) => setLocalReranker(prev => ({ ...prev, reranker_api_base: e.target.value }))}
                  className="bg-background/50 backdrop-blur-sm border-primary/20 font-mono text-sm"
                />
                <p className="text-[11px] text-muted-foreground italic">
                  URL base personalizada para llamadas HTTP. Útil si usas proxies o instancias privadas.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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
                  {Array.from(new Map(
                    [...LLM_PROVIDERS, ...TTS_PROVIDERS, ...EMBEDDING_PROVIDERS, ...SEARCH_PROVIDERS, ...RERANKER_PROVIDERS]
                      .filter(p => p.env_key)
                      .map(p => [p.id, p])
                  ).values()).map(p => (
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
      <div className="pt-4">
        <Button onClick={handleSaveAllSettings} disabled={loading} className="w-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20">
          {loading ? 'Guardando...' : 'Guardar Todas las Configuraciones de IA'}
        </Button>
      </div>
    </div>
  );
};
