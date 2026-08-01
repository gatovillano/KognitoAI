'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { Brain, RefreshCw, ChevronDown, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import apiClient from '@/lib/api';

const LLM_PROVIDERS = [
  { id: 'gemini', name: 'Google AI Studio', icon: '✨' },
  { id: 'openai', name: 'OpenAI (GPT)', icon: '🤖' },
  { id: 'anthropic', name: 'Anthropic (Claude)', icon: '🧠' },
  { id: 'openrouter', name: 'OpenRouter', icon: '🌐' },
  { id: 'ollama', name: 'Ollama (Local)', icon: '💻' },
  { id: 'ollama-cloud', name: '☁️ Ollama Cloud', icon: '☁️' },
  { id: 'openai-compatible', name: '🖥️ Local AI / Compatible', icon: '🖥️' },
  { id: 'mistral', name: 'Mistral AI', icon: '🌪️' },
  { id: 'kilocode', name: '🚀 Kilocode Gateway', icon: '🚀' },
  { id: 'nvidia', name: 'NVIDIA AI Catalog', icon: '🟢' },
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

export const LLMSelectorMenu: React.FC = () => {
  const { settings, updateSettings } = useUserSettings();
  const [isOpen, setIsOpen] = useState(false);
  const [fetchedModels, setFetchedModels] = useState<any[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  const currentProvider = settings?.llm_provider || 'gemini';
  const currentModel = settings?.llm_model || 'gemini/gemini-2.0-flash';
  const apiBase = settings?.llm_api_base || '';

  const fetchModelsForProvider = useCallback(async (provider: string, forceRefresh = false) => {
    setLoadingModels(true);
    try {
      let url = `/api/llm/models/${provider}`;
      const params = new URLSearchParams();
      if (apiBase) params.append('api_base', apiBase);
      if (forceRefresh) params.append('refresh', 'true');
      const queryString = params.toString();
      if (queryString) url += `?${queryString}`;

      const resp = await apiClient.get(url);
      const models = resp?.data || [];
      setFetchedModels(models);
      return models;
    } catch (e) {
      console.error(`Error fetching models for ${provider}:`, e);
      setFetchedModels([]);
      return [];
    } finally {
      setLoadingModels(false);
    }
  }, [apiBase]);

  useEffect(() => {
    if (isOpen && currentProvider) {
      fetchModelsForProvider(currentProvider);
    }
  }, [isOpen, currentProvider, fetchModelsForProvider]);

  const handleProviderChange = async (newProvider: string) => {
    try {
      const models = await fetchModelsForProvider(newProvider, true);
      let nextModel = '';
      if (models.length > 0) {
        const first = models[0];
        nextModel = typeof first === 'string' ? first : first.id;
      } else if (MODELS_BY_PROVIDER[newProvider]?.length) {
        nextModel = MODELS_BY_PROVIDER[newProvider][0];
      }

      await updateSettings({
        llm_provider: newProvider,
        llm_model: nextModel,
      });

      const providerObj = LLM_PROVIDERS.find(p => p.id === newProvider);
      toast.success(`Proveedor actualizado: ${providerObj?.name || newProvider}`);
    } catch (err) {
      toast.error('Error al cambiar de proveedor');
    }
  };

  const handleModelChange = async (newModel: string) => {
    try {
      await updateSettings({
        llm_model: newModel,
      });
      toast.success(`Modelo actualizado: ${getFormattedModelName(newModel)}`);
    } catch (err) {
      toast.error('Error al cambiar de modelo');
    }
  };

  const getFormattedModelName = (modelId: string) => {
    if (!modelId) return 'Seleccionar modelo';
    const parts = modelId.split('/');
    return parts.length > 1 ? parts[parts.length - 1] : modelId;
  };

  const currentProviderObj = LLM_PROVIDERS.find(p => p.id === currentProvider) || {
    id: currentProvider,
    name: currentProvider,
    icon: '🤖',
  };

  const renderModelItem = (m: any) => {
    const isString = typeof m === 'string';
    const id = isString ? m : m.id;
    const name = isString ? m : (m.name || m.id);
    const isGemini = currentProvider === 'gemini' || id.startsWith('gemini/');
    const isOpenRouter = currentProvider === 'openrouter' || id.startsWith('openrouter/');
    const isKilocode = currentProvider === 'kilocode' || id.startsWith('kilocode/');
    const isNVIDIA = currentProvider === 'nvidia' || id.startsWith('nvidia/');

    let badgeColor = "bg-blue-500/10 text-blue-500 border-blue-500/20";
    let badgeText = isKilocode ? "KiloCode" : isNVIDIA ? "NVIDIA" : isOpenRouter ? "OpenRouter" : "";

    if (isNVIDIA) {
      badgeText = "NVIDIA";
      badgeColor = "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
    } else if (isGemini) {
      badgeText = "Google";
      badgeColor = "bg-red-500/10 text-red-500 border-red-500/20";
    } else if (id.toLowerCase().includes('free')) {
      badgeText = "FREE";
      badgeColor = "bg-green-500/10 text-green-500 border-green-500/20";
    } else if (id.toLowerCase().includes('claude') || id.toLowerCase().includes('anthropic')) {
      badgeText = "Anthropic";
      badgeColor = "bg-orange-500/10 text-orange-500 border-orange-500/20";
    }

    return (
      <SelectItem key={id} value={id} className="cursor-pointer py-2">
        <div className="flex items-center justify-between w-full gap-2">
          <span className="font-medium text-xs truncate max-w-[200px]">{name}</span>
          {badgeText && (
            <Badge variant="outline" className={`text-[9px] px-1.5 py-0 h-4 uppercase font-bold tracking-wider shrink-0 ${badgeColor}`}>
              {badgeText}
            </Badge>
          )}
        </div>
      </SelectItem>
    );
  };

  const availableModelOptions = fetchedModels.length > 0 
    ? fetchedModels 
    : (MODELS_BY_PROVIDER[currentProvider] || []);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2.5 text-xs font-medium rounded-xl flex items-center gap-1.5 bg-muted/40 hover:bg-accent/50 border border-border/50 text-muted-foreground hover:text-foreground transition-all shrink-0 max-w-[220px]"
          title="Configurar Proveedor y Modelo de IA"
        >
          <Brain className="h-3.5 w-3.5 text-primary shrink-0" />
          <span className="truncate max-w-[130px]">
            {getFormattedModelName(currentModel)}
          </span>
          <ChevronDown className="h-3 w-3 opacity-60 shrink-0" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 p-4 shadow-xl rounded-2xl border border-border/80 backdrop-blur-md bg-popover/95 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border/50">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h4 className="font-semibold text-xs uppercase tracking-wider text-foreground">Motor de Inteligencia</h4>
          </div>
          <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20 font-mono">
            {currentProviderObj.name}
          </Badge>
        </div>

        {/* Menú 1: Proveedor de LLM */}
        <div className="space-y-1.5">
          <Label className="text-[11px] font-bold uppercase text-muted-foreground tracking-wider">
            1. Proveedor (API)
          </Label>
          <Select value={currentProvider} onValueChange={handleProviderChange}>
            <SelectTrigger className="w-full bg-background/60 border-border/60 text-xs h-9">
              <SelectValue placeholder="Seleccionar Proveedor" />
            </SelectTrigger>
            <SelectContent className="max-h-[240px]">
              {LLM_PROVIDERS.map(p => (
                <SelectItem key={p.id} value={p.id} className="text-xs py-2">
                  <div className="flex items-center gap-2">
                    <span>{p.icon}</span>
                    <span className="font-medium">{p.name}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Menú 2: Modelo de LLM */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label className="text-[11px] font-bold uppercase text-muted-foreground tracking-wider">
              2. Modelo
            </Label>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 hover:bg-muted rounded-full"
              onClick={() => fetchModelsForProvider(currentProvider, true)}
              title="Recargar modelos desde API"
            >
              <RefreshCw className={`h-3 w-3 text-muted-foreground ${loadingModels ? 'animate-spin text-primary' : ''}`} />
            </Button>
          </div>
          <Select value={currentModel} onValueChange={handleModelChange}>
            <SelectTrigger className="w-full bg-background/60 border-border/60 text-xs h-9">
              <SelectValue placeholder={loadingModels ? "Cargando modelos..." : "Seleccionar Modelo"} />
            </SelectTrigger>
            <SelectContent className="max-h-[260px]">
              {loadingModels ? (
                <SelectItem value="loading" disabled className="text-xs">
                  Cargando desde API...
                </SelectItem>
              ) : availableModelOptions.length > 0 ? (
                availableModelOptions.map(m => renderModelItem(m))
              ) : (
                <SelectItem value="empty" disabled className="text-xs">
                  Sin modelos disponibles
                </SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>
      </PopoverContent>
    </Popover>
  );
};
