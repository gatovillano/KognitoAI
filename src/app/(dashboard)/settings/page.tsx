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
import { Plus, Edit, Trash2, Eye, Calendar, User, Sparkles, Brain, Zap, Image as ImageIcon, Wrench, Puzzle, Info, RefreshCw, Globe, Github, Slack, ShieldCheck, Menu, X, Server } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MCPSettings } from '@/components/settings/MCPSettings';

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
    'openrouter/mistralai/mistral-small-3.1-24b-instruct:free',
    'openrouter/google/gemini-2.0-flash-001',
    'openrouter/anthropic/claude-3.5-sonnet'
  ],
  ollama: ['ollama/llama3.1', 'ollama/mistral', 'ollama/phi3', 'ollama/gemma2'],
  'ollama-cloud': ['ollama_chat/llama3.1', 'ollama_chat/mistral', 'ollama_chat/phi3', 'ollama_chat/gemma2', 'ollama_chat/qwen2.5'],
  'openai-compatible': [],
  mistral: ['mistral/mistral-large-latest', 'mistral/mistral-small-latest'],
  kilocode: [],

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

interface UserSecret {
  key_name: string;
  description?: string;
  masked_value: string;
}

interface SkillMetadata {
  id: string;
  description: string;
}

const SkillsSettings: React.FC = () => {
  const { settings, updateSettings } = useUserSettings();
  const [availableSkills, setAvailableSkills] = useState<SkillMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSkills = async () => {
      try {
        const response = await apiClient.get<{ skills: SkillMetadata[] }>('/api/skills/available');
        setAvailableSkills(response.data.skills);
      } catch (error) {
        console.error('Error fetching skills:', error);
        toast.error('Error al cargar las habilidades disponibles.');
      } finally {
        setLoading(false);
      }
    };
    fetchSkills();
  }, []);

  const toggleSkill = async (skillId: string) => {
    if (!settings) return;

    const isDisabled = settings.disabled_skills?.includes(skillId);
    const newDisabledSkills = isDisabled
      ? settings.disabled_skills.filter(id => id !== skillId)
      : [...(settings.disabled_skills || []), skillId];

    try {
      await updateSettings({ disabled_skills: newDisabledSkills });
      toast.success(`Habilidad ${isDisabled ? 'activada' : 'desactivada'} correctamente.`);
    } catch (error) {
      toast.error('Error al actualizar el estado de la habilidad.');
    }
  };

  const [selectedSkill, setSelectedSkill] = useState<SkillMetadata | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const openSkillDialog = (skill: SkillMetadata) => {
    setSelectedSkill(skill);
    setIsDialogOpen(true);
  };

  if (loading) return <div className="p-8 text-center">Cargando habilidades...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {availableSkills.map((skill: SkillMetadata) => {
        const isEnabled = !settings?.disabled_skills?.includes(skill.id);
        return (
          <Card 
            key={skill.id} 
            className={`overflow-hidden transition-all duration-300 relative group cursor-pointer hover:shadow-lg ${isEnabled ? 'border-primary/20 bg-primary/5' : 'opacity-70 grayscale border-muted-foreground/20'}`}
            onClick={() => openSkillDialog(skill)}
          >
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <div className={`p-2 rounded-lg ${isEnabled ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
                    <Wrench className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-sm font-bold uppercase tracking-tight">{skill.id.replace(/_/g, ' ')}</CardTitle>
                </div>
                <div onClick={(e) => e.stopPropagation()}>
                  <Switch
                    checked={isEnabled}
                    onCheckedChange={() => toggleSkill(skill.id)}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                {skill.description || 'Sin descripción disponible.'}
              </p>
              <div className="mt-4 flex items-center justify-between">
                <Badge variant={isEnabled ? 'default' : 'secondary'} className="text-[10px] uppercase font-bold px-2 py-0">
                  {isEnabled ? 'Activo' : 'Desactivado'}
                </Badge>
                <div className="text-primary opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[10px] font-medium">
                  <Info className="h-3 w-3" /> Ver detalles
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-2xl">
              <Wrench className="h-6 w-6 text-primary" />
              {selectedSkill?.id.replace(/_/g, ' ').toUpperCase()}
            </DialogTitle>
          </DialogHeader>
          <div className="prose prose-sm dark:prose-invert max-w-none mt-4">
            {selectedSkill?.description ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {selectedSkill.description}
              </ReactMarkdown>
            ) : (
              <p className="text-muted-foreground italic">No hay una descripción detallada para esta habilidad.</p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const IntegrationsSettings: React.FC = () => {
  const [loading, setLoading] = useState<Record<string, boolean>>({ github: false, slack: false, notion: false });
  const [status, setStatus] = useState<Record<string, { is_configured: boolean, updated_at: string | null }>>({
    github: { is_configured: false, updated_at: null },
    slack: { is_configured: false, updated_at: null },
    notion: { is_configured: false, updated_at: null }
  });
  const [tokens, setTokens] = useState<Record<string, string>>({ github: '', slack: '', notion: '' });

  const fetchStatus = async () => {
    try {
      const [gh, sl, nt] = await Promise.all([
        apiClient.get('/api/github/status'),
        apiClient.get('/api/slack/status'),
        apiClient.get('/api/notion/status')
      ]);
      setStatus({ github: gh.data, slack: sl.data, notion: nt.data });
    } catch (error) {
      console.error('Error fetching integrations status:', error);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleSave = async (platform: string) => {
    setLoading(prev => ({ ...prev, [platform]: true }));
    try {
      const endpoint = `/api/${platform}/credentials`;
      let payload = {};
      if (platform === 'github') payload = { github_token: tokens[platform] };
      else if (platform === 'slack') payload = { bot_token: tokens[platform] };
      else if (platform === 'notion') payload = { api_key: tokens[platform] };

      await apiClient.post(endpoint, payload);
      toast.success(`Configuración de ${platform.toUpperCase()} guardada correctamente.`);
      setTokens(prev => ({ ...prev, [platform]: '' }));
      fetchStatus();
    } catch (error) {
      toast.error(`Error al guardar configuración de ${platform.toUpperCase()}.`);
    } finally {
      setLoading(prev => ({ ...prev, [platform]: false }));
    }
  };

  const handleDelete = async (platform: string) => {
    if (!confirm(`¿Estás seguro de que quieres eliminar la integración con ${platform.toUpperCase()}?`)) return;
    try {
      await apiClient.delete(`/api/${platform}/credentials`);
      toast.success(`Integración con ${platform.toUpperCase()} eliminada.`);
      fetchStatus();
    } catch (error) {
      toast.error(`Error al eliminar integración de ${platform.toUpperCase()}.`);
    }
  };

  const platforms = [
    { id: 'github', name: 'GitHub', icon: <Github className="h-5 w-5" />, placeholder: 'ghp_xxxxxxxxxxxx' },
    { id: 'slack', name: 'Slack', icon: <Slack className="h-5 w-5" />, placeholder: 'xoxb-xxxxxxxxxxxx' },
    { id: 'notion', name: 'Notion', icon: <Puzzle className="h-5 w-5" />, placeholder: 'secret_xxxxxxxxxxxx' }
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {platforms.map(p => (
          <Card key={p.id} className="border-primary/10 bg-card/50">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    {p.icon}
                  </div>
                  <CardTitle className="text-lg">{p.name}</CardTitle>
                </div>
                <Badge variant={status[p.id].is_configured ? "default" : "secondary"}>
                  {status[p.id].is_configured ? "Conectado" : "No configurado"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor={`${p.id}-token`}>
                  {p.id === 'github' ? 'Personal Access Token' : p.id === 'slack' ? 'Bot User OAuth Token' : 'Internal Integration Secret'}
                </Label>
                <div className="flex gap-2">
                  <Input
                    id={`${p.id}-token`}
                    type="password"
                    placeholder={p.placeholder}
                    value={tokens[p.id]}
                    onChange={(e) => setTokens(prev => ({ ...prev, [p.id]: e.target.value }))}
                  />
                  <Button 
                    size="sm" 
                    onClick={() => handleSave(p.id)} 
                    disabled={loading[p.id] || !tokens[p.id]}
                  >
                    {loading[p.id] ? <RefreshCw className="h-4 w-4 animate-spin" /> : "Guardar"}
                  </Button>
                </div>
              </div>
              {status[p.id].is_configured && (
                <div className="flex justify-between items-center pt-2 border-t border-primary/5">
                  <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                    Configurado el {status[p.id].updated_at ? new Date(status[p.id].updated_at!).toLocaleDateString() : 'N/A'}
                  </span>
                  <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8" onClick={() => handleDelete(p.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

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
    tts_api_base: settings?.tts_api_base || '', // Nuevo campo para API TTS local
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
    const handler = setTimeout(() => {
      if (localLLM.llm_provider) {
        fetchModels(localLLM.llm_provider, 'main', { apiBase: localLLM.llm_api_base });
      }
    }, 500); // 500ms debounce
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

              {(localTTS.tts_provider === 'openai-compatible' || localTTS.tts_provider === 'openai' || localTTS.tts_provider === 'kokoro' || localTTS.tts_provider === 'coquitts') && (
                <div className="space-y-2">
                  <Label>API Base URL (Opcional)</Label>
                  <Input
                    placeholder={
                      localTTS.tts_provider === 'kokoro' ? 'http://localhost:8011' :
                      localTTS.tts_provider === 'coquitts' ? 'http://localhost:8006' :
                      localTTS.tts_provider === 'openai-compatible' ? 'http://localhost:8080/v1' :
                      'https://api.openai.com/v1'
                    }
                    value={localTTS.tts_api_base || ''}
                    onChange={(e) => setLocalTTS(prev => ({ ...prev, tts_api_base: e.target.value }))}
                    className="bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors font-mono text-sm"
                  />
                  <p className="text-[10px] text-muted-foreground italic mt-1 leading-relaxed">
                    {localTTS.tts_provider === 'kokoro' ?
                      "Para Kokoro TTS local (ej. http://localhost:8011)" :
                      localTTS.tts_provider === 'coquitts' ?
                      "Para Coqui TTS / XTTS v2 local (ej. http://localhost:8006)" :
                      "Para servicios TTS locales o compatibles con OpenAI."}
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Voz</Label>
                  {loadingModels.voices && <RefreshCw className="h-3 w-3 animate-spin text-primary" />}
                </div>
                <Select
                  value={localTTS.tts_voice}
                  onValueChange={(v) => setLocalTTS(prev => ({ ...prev, tts_voice: v }))}
                >
                  <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20 hover:border-primary/50 transition-colors">
                    <SelectValue placeholder="Selecciona una voz" />
                  </SelectTrigger>
                  <SelectContent className="max-h-[300px]">
                    {/* Combinar voces estáticas y dinámicas, evitando duplicados */}
                    {Array.from(new Set([
                      ...(ttsVoices.length > 0 ? ttsVoices : []),
                      ...(TTS_VOICES_BY_PROVIDER[localTTS.tts_provider] || [])
                    ])).map(v => (
                      <SelectItem key={v} value={v}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {ttsVoices.length > 0 && (
                  <p className="text-[11px] text-muted-foreground italic">
                    Voces detectadas automáticamente de la API.
                  </p>
                )}
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
              {(localTTS.tts_provider === 'openai' || localTTS.tts_provider === 'openai-compatible') && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Modelo de TTS</Label>
                    {loadingModels.tts && <RefreshCw className="h-3 w-3 animate-spin text-primary" />}
                  </div>
                  {ttsModels.length > 0 ? (
                    <Select
                      value={localTTS.tts_model}
                      onValueChange={(v) => setLocalTTS(prev => ({ ...prev, tts_model: v }))}
                    >
                      <SelectTrigger className="w-full bg-background/50 backdrop-blur-sm border-primary/20">
                        <SelectValue placeholder="Selecciona un modelo" />
                      </SelectTrigger>
                      <SelectContent>
                        {ttsModels.map(m => (
                          <SelectItem key={m} value={m}>{m}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      placeholder="Ej: tts-1 o kokoro"
                      value={localTTS.tts_model || ''}
                      onChange={(e) => setLocalTTS(prev => ({ ...prev, tts_model: e.target.value }))}
                      className="bg-background/50 backdrop-blur-sm border-primary/20"
                    />
                  )}
                  <p className="text-[11px] text-muted-foreground italic">
                    {ttsModels.length > 0 
                      ? "Modelos detectados automáticamente de la API." 
                      : "Ingresa el nombre del modelo si no se detectó automáticamente."}
                  </p>
                </div>
              )}
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
                    const provider = EMBEDDING_PROVIDERS.find(p => p.id === v);
                    setLocalEmbedding(prev => ({ 
                      ...prev, 
                      embedding_provider: v, 
                      embedding_model: firstModel,
                      embedding_api_key_name: provider?.env_key || prev.embedding_api_key_name
                    }));
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
                  placeholder={localEmbedding.embedding_provider === 'ollama-cloud' ? 'https://ollama.com' : 'http://localhost:11434'}
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
                  {Array.from(new Map(
                    [...LLM_PROVIDERS, ...TTS_PROVIDERS, ...EMBEDDING_PROVIDERS, ...SEARCH_PROVIDERS]
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

const SETTINGS_MENU = [
  { id: 'personal-data', label: 'Datos Personales', icon: User },
  { id: 'ai-profile', label: 'Perfil de IA', icon: Brain },
  { id: 'llm-config', label: 'Modelos e IA', icon: Sparkles },
  { id: 'modules-preferences', label: 'Módulos y Preferencias', icon: Wrench },
  { id: 'memories', label: 'Memorias', icon: Brain },
  { id: 'skills', label: 'Skills', icon: Puzzle },
  { id: 'mcp', label: 'Servidores MCP', icon: Server },
  { id: 'heartbeat', label: 'Heartbeat Autónomo', icon: Zap },
  { id: 'security', label: 'Seguridad', icon: ShieldCheck },
  { id: 'remote', label: 'Acceso Remoto / SSH', icon: Globe },
  { id: 'sync', label: 'Sincronización', icon: RefreshCw },
  { id: 'integrations', label: 'Integraciones', icon: Puzzle },
];

const SettingsPage: React.FC = () => {
  const { settings, loading, error, getSettings, updateSettings } = useUserSettings();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('personal-data');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [localSettings, setLocalSettings] = useState(settings);

  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [showAddMemory, setShowAddMemory] = useState(false);
  const [newKey, setNewKey] = useState({ provider: '', value: '' });
  const [newMemory, setNewMemory] = useState({
    title: '',
    content: '',
    type: 'general'
  });
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [availableTools, setAvailableTools] = useState<{name: string, description: string}[]>([]);
  const [heartbeatTriggering, setHeartbeatTriggering] = useState(false);
  
  // States for multiple custom heartbeats
  const [customHeartbeats, setCustomHeartbeats] = useState<any[]>([]);
  const [heartbeatsLoading, setHeartbeatsLoading] = useState(false);
  const [isHeartbeatModalOpen, setIsHeartbeatModalOpen] = useState(false);
  const [isEditingHeartbeat, setIsEditingHeartbeat] = useState(false);
  const [editingHeartbeatId, setEditingHeartbeatId] = useState<string | null>(null);
  const [heartbeatTriggeringIds, setHeartbeatTriggeringIds] = useState<Record<string, boolean>>({});
  const [heartbeatForm, setHeartbeatForm] = useState({
    name: '',
    instructions: '',
    schedule_type: 'interval',
    interval_minutes: 60,
    hour: 8,
    minute: 0,
    day_of_week: 1,
    allowed_tools: [] as string[],
    is_active: true,
  });

  const [profileData, setProfileData] = useState({
    nombre: '',
    gustos: '',
    intereses: '',
    otros_datos: '',
    system_prompt: ''
  });
  const [profileLoading, setProfileLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);

  useEffect(() => {
    getSettings();
  }, []);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  // Fetch functions for custom heartbeats
  const fetchCustomHeartbeats = async () => {
    setHeartbeatsLoading(true);
    try {
      const response = await apiClient.get('/api/scheduled-tools/custom-heartbeats');
      setCustomHeartbeats(response.data || []);
    } catch (error) {
      console.error('Error fetching custom heartbeats:', error);
      toast.error('No se pudieron cargar los heartbeats personalizados');
    } finally {
      setHeartbeatsLoading(false);
    }
  };

  const handleSaveHeartbeat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!heartbeatForm.name || !heartbeatForm.instructions) {
      toast.error('El nombre y las instrucciones son requeridos');
      return;
    }

    const payload: any = {
      name: heartbeatForm.name,
      instructions: heartbeatForm.instructions,
      schedule_type: heartbeatForm.schedule_type,
      allowed_tools: heartbeatForm.allowed_tools,
      is_active: heartbeatForm.is_active,
    };

    if (heartbeatForm.schedule_type === 'interval') {
      payload.interval_minutes = Number(heartbeatForm.interval_minutes) || 60;
    } else if (heartbeatForm.schedule_type === 'daily') {
      payload.hour = Number(heartbeatForm.hour) || 0;
      payload.minute = Number(heartbeatForm.minute) || 0;
    } else if (heartbeatForm.schedule_type === 'weekly') {
      payload.hour = Number(heartbeatForm.hour) || 0;
      payload.minute = Number(heartbeatForm.minute) || 0;
      payload.day_of_week = Number(heartbeatForm.day_of_week) || 0;
    }

    try {
      if (isEditingHeartbeat && editingHeartbeatId) {
        await apiClient.put(`/api/scheduled-tools/custom-heartbeats/${editingHeartbeatId}`, payload);
        toast.success('Heartbeat actualizado exitosamente');
      } else {
        await apiClient.post('/api/scheduled-tools/custom-heartbeats', payload);
        toast.success('Heartbeat creado exitosamente');
      }
      setIsHeartbeatModalOpen(false);
      fetchCustomHeartbeats();
    } catch (error: any) {
      console.error('Error saving heartbeat:', error);
      toast.error(error.response?.data?.detail || 'Error al guardar el heartbeat');
    }
  };

  const handleDeleteHeartbeat = async (id: string) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este heartbeat?')) {
      return;
    }
    try {
      await apiClient.delete(`/api/scheduled-tools/custom-heartbeats/${id}`);
      toast.success('Heartbeat eliminado exitosamente');
      fetchCustomHeartbeats();
    } catch (error: any) {
      console.error('Error deleting heartbeat:', error);
      toast.error('Error al eliminar el heartbeat');
    }
  };

  const handleTriggerHeartbeat = async (id: string) => {
    setHeartbeatTriggeringIds(prev => ({ ...prev, [id]: true }));
    try {
      await apiClient.post(`/api/scheduled-tools/custom-heartbeats/${id}/trigger`);
      toast.success('Heartbeat lanzado manualmente con éxito');
    } catch (error: any) {
      console.error('Error triggering heartbeat:', error);
      toast.error(error.response?.data?.detail || 'Error al lanzar heartbeat');
    } finally {
      setHeartbeatTriggeringIds(prev => ({ ...prev, [id]: false }));
    }
  };

  const openCreateHeartbeatModal = () => {
    setHeartbeatForm({
      name: '',
      instructions: '',
      schedule_type: 'interval',
      interval_minutes: 60,
      hour: 8,
      minute: 0,
      day_of_week: 1,
      allowed_tools: [],
      is_active: true,
    });
    setIsEditingHeartbeat(false);
    setEditingHeartbeatId(null);
    setIsHeartbeatModalOpen(true);
  };

  const openEditHeartbeatModal = (hb: any) => {
    setHeartbeatForm({
      name: hb.name,
      instructions: hb.instructions,
      schedule_type: hb.schedule_type,
      interval_minutes: hb.interval_minutes || 60,
      hour: hb.hour !== null ? hb.hour : 8,
      minute: hb.minute !== null ? hb.minute : 0,
      day_of_week: hb.day_of_week !== null ? hb.day_of_week : 1,
      allowed_tools: hb.allowed_tools || [],
      is_active: hb.is_active,
    });
    setIsEditingHeartbeat(true);
    setEditingHeartbeatId(hb.id);
    setIsHeartbeatModalOpen(true);
  };

  useEffect(() => {
    if (activeTab === 'memories' && !memories.length) {
      fetchMemories();
    }
    if (activeTab === 'sync' && !workspaces.length) {
      fetchWorkspaces();
    }
    if (activeTab === 'heartbeat') {
      if (!availableTools.length) {
        fetchAvailableTools();
      }
      fetchCustomHeartbeats();
    }
    if (activeTab === 'ai-profile') {
      fetchProfile();
    }
  }, [activeTab]);

  const fetchProfile = async () => {
    setProfileLoading(true);
    try {
      const response = await apiClient.get('/api/users/me/profile');
      setProfileData({
        nombre: response.data.nombre || '',
        gustos: response.data.gustos || '',
        intereses: response.data.intereses || '',
        otros_datos: response.data.otros_datos || '',
        system_prompt: response.data.system_prompt || ''
      });
    } catch (error) {
      console.error('Error fetching profile:', error);
      toast.error('Error al cargar el perfil de IA.');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await apiClient.put('/api/users/me/profile', profileData);
      toast.success('Perfil de IA guardado exitosamente.');
      fetchProfile();
    } catch (error) {
      console.error('Error saving profile:', error);
      toast.error('Error al guardar el perfil de IA.');
    } finally {
      setSavingProfile(false);
    }
  };

  const fetchWorkspaces = async () => {
    try {
      const response = await apiClient.get('/api/workspaces', { params: { limit: 100 } });
      setWorkspaces(response.data.workspaces || response.data || []);
    } catch (error) {
      console.error('Error fetching workspaces:', error);
    }
  };

  const fetchAvailableTools = async () => {
    try {
      const response = await apiClient.get('/api/scheduled-tools/available-tools');
      setAvailableTools(response.data.tools || []);
    } catch (error) {
      console.error('Error fetching available tools:', error);
    }
  };

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
    if (!confirm('¿Estás seguro de que deseas eliminar esta memoria? Esta acción no se puede deshacer.')) {
      return;
    }
    try {
      await apiClient.delete(`/api/memories/${memoryId}`);
      toast.success('Memoria eliminada exitosamente');
      fetchMemories();
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

  const handleSelectChange = (id: string, value: any) => {
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
        custom_heartbeat_instructions: localSettings.custom_heartbeat_instructions,
        custom_heartbeat_interval_minutes: localSettings.custom_heartbeat_interval_minutes,
        custom_heartbeat_allowed_tools: localSettings.custom_heartbeat_allowed_tools,
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

  const activeMenuItem = SETTINGS_MENU.find(item => item.id === activeTab);

  return (
    <div className="flex h-full min-h-screen bg-background">
      {/* ── SIDEBAR DESKTOP (lg+) ── */}
      <aside className="hidden lg:flex flex-col w-64 shrink-0 border-r border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 h-screen overflow-y-auto">
        {/* Sidebar Header */}
        <div className="px-5 py-6 border-b border-border/30">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10 text-primary">
              <Wrench className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-foreground tracking-tight">Configuración</h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Panel de ajustes</p>
            </div>
          </div>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {SETTINGS_MENU.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm font-medium transition-all duration-200 group relative ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/60'
                }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-full" />
                )}
                <Icon className={`h-4 w-4 shrink-0 transition-colors ${isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}`} />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="px-4 py-4 border-t border-border/30">
          <p className="text-[10px] text-muted-foreground/60 text-center">KognitoAI · Ajustes</p>
        </div>
      </aside>

      {/* ── MOBILE MENU OVERLAY ── */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* ── MOBILE DRAWER ── */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-card border-r border-border/40 shadow-2xl flex flex-col transition-transform duration-300 ease-in-out lg:hidden ${
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border/30">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
              <Wrench className="h-4 w-4" />
            </div>
            <span className="text-sm font-bold">Configuración</span>
          </div>
          <button
            onClick={() => setIsMobileMenuOpen(false)}
            className="p-1.5 rounded-lg hover:bg-accent transition-colors text-muted-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Drawer Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
          {SETTINGS_MENU.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setIsMobileMenuOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/60'
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? 'text-primary' : ''}`} />
                <span>{item.label}</span>
                {isActive && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ── MAIN CONTENT ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-auto">
        {/* Mobile Top Bar */}
        <div className="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-background/80 backdrop-blur-sm border-b border-border/30">
          <button
            onClick={() => setIsMobileMenuOpen(true)}
            className="p-2 rounded-lg hover:bg-accent transition-colors text-muted-foreground"
            aria-label="Abrir menú de configuración"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-bold truncate">
              {activeMenuItem?.label || 'Configuración'}
            </h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Configuración</p>
          </div>
        </div>

        {/* Desktop Page Header */}
        <div className="hidden lg:block px-8 pt-8 pb-2">
          <div className="flex items-center gap-3 mb-1">
            {activeMenuItem && (
              <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                {React.createElement(activeMenuItem.icon, { className: 'h-4 w-4' })}
              </div>
            )}
            <h1 className="text-xl font-bold text-foreground">{activeMenuItem?.label || 'Configuración'}</h1>
          </div>
          <div className="h-px bg-gradient-to-r from-primary/30 via-primary/10 to-transparent mt-4" />
        </div>

        {/* Content Area */}
        <main className="flex-1 px-4 py-4 lg:px-8 lg:py-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4 sr-only">
          <TabsTrigger value="personal-data">Datos Personales</TabsTrigger>
          <TabsTrigger value="ai-profile">Perfil de IA</TabsTrigger>
          <TabsTrigger value="llm-config">Modelos e IA</TabsTrigger>
          <TabsTrigger value="modules-preferences">Módulos y Preferencias</TabsTrigger>
          <TabsTrigger value="memories">Memorias</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="mcp">Servidores MCP</TabsTrigger>
          <TabsTrigger value="heartbeat">Heartbeat Autónomo</TabsTrigger>
          <TabsTrigger value="security">Seguridad</TabsTrigger>
          <TabsTrigger value="remote">Acceso Remoto / SSH</TabsTrigger>
          <TabsTrigger value="sync">Sincronización</TabsTrigger>
          <TabsTrigger value="integrations">Integraciones</TabsTrigger>
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
        <TabsContent value="ai-profile">
          <Card className="border-primary/20 bg-background/50 backdrop-blur-md shadow-xl transition-all duration-300">
            <CardHeader className="border-b border-primary/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <Brain className="h-6 w-6 animate-pulse" />
                </div>
                <div>
                  <CardTitle className="text-xl font-bold flex items-center gap-2">
                    Perfil de IA (Memoria Estructurada)
                    <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 animate-pulse">
                      Dinámico & Autónomo
                    </Badge>
                  </CardTitle>
                  <CardDescription className="mt-1">
                    Esta es la memoria estructurada y el prompt de sistema personalizado que tu agente de IA (Kognito/Fito) mantiene sobre ti de forma autónoma a lo largo de las conversaciones. Puedes modificarla manualmente aquí.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              {profileLoading ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm text-muted-foreground animate-pulse">Cargando perfil y recuerdos de IA...</p>
                </div>
              ) : (
                <form onSubmit={handleProfileSubmit} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="profile-nombre" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                          <User className="h-4 w-4 text-primary" />
                          Cómo te llamas (Nombre del Perfil)
                        </Label>
                        <Input
                          id="profile-nombre"
                          placeholder="Tu nombre o apodo para el Agente"
                          value={profileData.nombre}
                          onChange={(e) => setProfileData({ ...profileData, nombre: e.target.value })}
                          className="bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                        />
                        <p className="text-[11px] text-muted-foreground">El nombre por el cual el agente se dirigirá a ti.</p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="profile-gustos" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                          <Sparkles className="h-4 w-4 text-primary" />
                          Gustos y Preferencias
                        </Label>
                        <Textarea
                          id="profile-gustos"
                          placeholder="Tus gustos culinarios, temas favoritos, pasatiempos, estilo de comunicación preferido..."
                          value={profileData.gustos}
                          onChange={(e) => setProfileData({ ...profileData, gustos: e.target.value })}
                          className="min-h-[120px] bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                        />
                        <p className="text-[11px] text-muted-foreground">Cosas que te agradan o prefieres en tu día a día.</p>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="profile-intereses" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                          <Globe className="h-4 w-4 text-primary" />
                          Intereses y Foco de Estudio/Trabajo
                        </Label>
                        <Textarea
                          id="profile-intereses"
                          placeholder="Tecnologías que estás aprendiendo, proyectos en los que trabajas, temas que investigas..."
                          value={profileData.intereses}
                          onChange={(e) => setProfileData({ ...profileData, intereses: e.target.value })}
                          className="min-h-[120px] bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                        />
                        <p className="text-[11px] text-muted-foreground">Temas en los que estás enfocado actualmente o deseas aprender.</p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="profile-otros" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                          <Info className="h-4 w-4 text-primary" />
                          Otros Datos Persistentes
                        </Label>
                        <Textarea
                          id="profile-otros"
                          placeholder="Cualquier otra información relevante, contexto familiar, metas a largo plazo, etc."
                          value={profileData.otros_datos}
                          onChange={(e) => setProfileData({ ...profileData, otros_datos: e.target.value })}
                          className="min-h-[120px] bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                        />
                        <p className="text-[11px] text-muted-foreground">Notas adicionales que el Agente debería recordar permanentemente.</p>
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-primary/10 pt-6 space-y-2">
                    <Label htmlFor="profile-prompt" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                      <Wrench className="h-4 w-4 text-primary" />
                      Prompt de Sistema Personalizado (Instrucciones Directas)
                    </Label>
                    <Textarea
                      id="profile-prompt"
                      placeholder="Escribe instrucciones de comportamiento explícitas para tu IA. Ej: 'Háblame de forma concisa', 'Prioriza siempre dar ejemplos de código', 'Sé sumamente empático'..."
                      value={profileData.system_prompt}
                      onChange={(e) => setProfileData({ ...profileData, system_prompt: e.target.value })}
                      className="min-h-[120px] bg-background/80 font-mono text-xs border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                    />
                    <p className="text-[11px] text-muted-foreground">
                      Estas directrices se inyectan en el prompt del sistema del agente en cada interacción y guían directamente su personalidad y comportamiento.
                    </p>
                  </div>

                  <div className="flex justify-end gap-3 border-t border-primary/10 pt-4">
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={fetchProfile}
                      disabled={savingProfile || profileLoading}
                      className="border-primary/20 text-primary hover:bg-primary/5 transition-all duration-300"
                    >
                      Descartar Cambios
                    </Button>
                    <Button 
                      type="submit" 
                      disabled={savingProfile || profileLoading}
                      className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-md shadow-primary/20 transition-all duration-300"
                    >
                      {savingProfile ? 'Guardando...' : 'Guardar Perfil de IA'}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
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
        <TabsContent value="mcp">
          <MCPSettings />
        </TabsContent>
        <TabsContent value="skills">
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-1">Habilidades (Skills)</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Activa o desactiva las capacidades de la IA. Las habilidades desactivadas no estarán disponibles para el agente.
              </p>
            </div>
            <SkillsSettings />
          </div>
        </TabsContent>
        <TabsContent value="heartbeat">
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold mb-1">Heartbeats Autónomos Personalizados</h2>
                <p className="text-sm text-muted-foreground">
                  Configura múltiples tareas recurrentes para que tus agentes las realicen en segundo plano.
                </p>
              </div>
              <Button onClick={openCreateHeartbeatModal} className="flex items-center gap-2 self-start sm:self-auto">
                <Plus className="h-4 w-4" />
                Nuevo Heartbeat
              </Button>
            </div>

            {heartbeatsLoading ? (
              <div className="flex justify-center p-8">
                <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : customHeartbeats.length === 0 ? (
              <Card className="border border-dashed border-border/60 bg-secondary/5">
                <CardContent className="flex flex-col items-center justify-center p-8 text-center space-y-4">
                  <div className="p-4 bg-primary/10 rounded-full text-primary">
                    <Brain className="h-8 w-8" />
                  </div>
                  <div>
                    <CardTitle className="text-base mb-1">No hay heartbeats personalizados</CardTitle>
                    <CardDescription className="max-w-md">
                      Crea tu primera tarea automatizada para que el agente ejecute tus instrucciones de forma periódica usando herramientas permitidas.
                    </CardDescription>
                  </div>
                  <Button onClick={openCreateHeartbeatModal} variant="outline" size="sm">
                    Crear mi primer heartbeat
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {customHeartbeats.map((hb) => {
                  const isTriggering = !!heartbeatTriggeringIds[hb.id];
                  return (
                    <Card key={hb.id} className="border-none shadow-md bg-secondary/5 hover:bg-secondary/10 transition-colors flex flex-col justify-between">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-center gap-2">
                            <div className="p-2 bg-primary/10 rounded-lg text-primary">
                              <Zap className="h-4 w-4" />
                            </div>
                            <div>
                              <CardTitle className="text-base font-bold line-clamp-1">{hb.name}</CardTitle>
                              <CardDescription className="text-xs flex items-center gap-1.5 mt-0.5">
                                <span className={`h-2 w-2 rounded-full ${hb.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                                {hb.is_active ? 'Activo' : 'Pausado'}
                              </CardDescription>
                            </div>
                          </div>
                          <Badge variant="outline" className="bg-background/40">
                            {hb.schedule_type === 'interval' && 'Intervalo'}
                            {hb.schedule_type === 'daily' && 'Diario'}
                            {hb.schedule_type === 'weekly' && 'Semanal'}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4 flex-grow">
                        <div>
                          <Label className="text-xs text-muted-foreground font-semibold">Instrucciones</Label>
                          <p className="text-xs text-gray-700 dark:text-gray-300 line-clamp-3 bg-background/30 p-2 rounded-md border border-border/30 mt-1 whitespace-pre-wrap">
                            {hb.instructions}
                          </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4 text-xs">
                          <div>
                            <span className="text-muted-foreground font-semibold block">Frecuencia</span>
                            <span className="font-medium mt-0.5 block">
                              {hb.schedule_type === 'interval' && `Cada ${hb.interval_minutes} minutos`}
                              {hb.schedule_type === 'daily' && `Todos los días a las ${String(hb.hour).padStart(2, '0')}:${String(hb.minute).padStart(2, '0')}`}
                              {hb.schedule_type === 'weekly' && (
                                <>
                                  {['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][hb.day_of_week] || 'Día'} a las {String(hb.hour).padStart(2, '0')}:${String(hb.minute).padStart(2, '0')}
                                </>
                              )}
                            </span>
                          </div>
                          <div>
                            <span className="text-muted-foreground font-semibold block">Siguiente Ejecución</span>
                            <span className="font-medium mt-0.5 block line-clamp-1 text-primary">
                              {hb.next_run ? new Date(hb.next_run).toLocaleString() : 'No programada'}
                            </span>
                          </div>
                        </div>

                        {hb.allowed_tools && hb.allowed_tools.length > 0 && (
                          <div>
                            <Label className="text-xs text-muted-foreground font-semibold">Herramientas</Label>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {hb.allowed_tools.map((tool: string) => (
                                <Badge key={tool} variant="secondary" className="text-[10px] px-1.5 py-0.5">
                                  {tool}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                      <CardContent className="pt-0 pb-4 flex gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          className="flex-1 text-xs"
                          disabled={isTriggering}
                          onClick={() => handleTriggerHeartbeat(hb.id)}
                        >
                          <RefreshCw className={`h-3 w-3 mr-1.5 ${isTriggering ? 'animate-spin' : ''}`} />
                          Lanzar
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 text-xs"
                          onClick={() => openEditHeartbeatModal(hb)}
                        >
                          <Edit className="h-3 w-3 mr-1.5" />
                          Editar
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10 text-xs px-2"
                          onClick={() => handleDeleteHeartbeat(hb.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* Dialog Modal for Creating/Editing Heartbeats */}
          <Dialog open={isHeartbeatModalOpen} onOpenChange={setIsHeartbeatModalOpen}>
            <DialogContent className="max-w-2xl bg-card border border-border/40 shadow-2xl">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 text-lg">
                  <Brain className="h-5 w-5 text-primary" />
                  {isEditingHeartbeat ? 'Editar Heartbeat Autónomo' : 'Nuevo Heartbeat Autónomo'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSaveHeartbeat} className="space-y-4 mt-2">
                <div className="grid w-full gap-1.5">
                  <Label htmlFor="hb_name">Nombre de la Configuración</Label>
                  <Input
                    id="hb_name"
                    required
                    placeholder="Ej. Resumen Diario de Noticias, Escáner de Emails..."
                    value={heartbeatForm.name}
                    onChange={(e) => setHeartbeatForm(prev => ({ ...prev, name: e.target.value }))}
                    className="bg-background/50 border-border/40 focus:border-primary/50"
                  />
                </div>

                <div className="grid w-full gap-1.5">
                  <Label htmlFor="hb_instructions">Instrucciones Ejecutivas</Label>
                  <Textarea
                    id="hb_instructions"
                    required
                    placeholder="Describe detalladamente qué debe hacer el agente en cada ejecución..."
                    value={heartbeatForm.instructions}
                    onChange={(e) => setHeartbeatForm(prev => ({ ...prev, instructions: e.target.value }))}
                    rows={4}
                    className="bg-background/50 border-border/40 focus:border-primary/50"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="grid w-full gap-1.5">
                    <Label htmlFor="hb_schedule_type">Tipo de Programación</Label>
                    <Select
                      value={heartbeatForm.schedule_type}
                      onValueChange={(value) => setHeartbeatForm(prev => ({ ...prev, schedule_type: value }))}
                    >
                      <SelectTrigger className="bg-background/50 border-border/40">
                        <SelectValue placeholder="Selecciona tipo" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="interval">Intervalo de tiempo</SelectItem>
                        <SelectItem value="daily">Diario (Hora fija)</SelectItem>
                        <SelectItem value="weekly">Semanal (Día y hora fijos)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {heartbeatForm.schedule_type === 'interval' && (
                    <div className="grid w-full gap-1.5">
                      <Label htmlFor="hb_interval">Intervalo de ejecución (minutos)</Label>
                      <Input
                        id="hb_interval"
                        type="number"
                        min={5}
                        required
                        value={heartbeatForm.interval_minutes}
                        onChange={(e) => setHeartbeatForm(prev => ({ ...prev, interval_minutes: parseInt(e.target.value) || 60 }))}
                        className="bg-background/50 border-border/40"
                      />
                    </div>
                  )}

                  {heartbeatForm.schedule_type === 'daily' && (
                    <div className="grid grid-cols-2 gap-2">
                      <div className="grid gap-1.5">
                        <Label>Hora (0-23)</Label>
                        <Input
                          type="number"
                          min={0}
                          max={23}
                          required
                          value={heartbeatForm.hour}
                          onChange={(e) => setHeartbeatForm(prev => ({ ...prev, hour: parseInt(e.target.value) || 0 }))}
                          className="bg-background/50 border-border/40"
                        />
                      </div>
                      <div className="grid gap-1.5">
                        <Label>Minuto (0-59)</Label>
                        <Input
                          type="number"
                          min={0}
                          max={59}
                          required
                          value={heartbeatForm.minute}
                          onChange={(e) => setHeartbeatForm(prev => ({ ...prev, minute: parseInt(e.target.value) || 0 }))}
                          className="bg-background/50 border-border/40"
                        />
                      </div>
                    </div>
                  )}

                  {heartbeatForm.schedule_type === 'weekly' && (
                    <div className="grid grid-cols-2 gap-2 col-span-2 md:col-span-1">
                      <div className="grid gap-1.5">
                        <Label>Día de la semana</Label>
                        <Select
                          value={String(heartbeatForm.day_of_week)}
                          onValueChange={(value) => setHeartbeatForm(prev => ({ ...prev, day_of_week: parseInt(value) }))}
                        >
                          <SelectTrigger className="bg-background/50 border-border/40">
                            <SelectValue placeholder="Día" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="0">Lunes</SelectItem>
                            <SelectItem value="1">Martes</SelectItem>
                            <SelectItem value="2">Miércoles</SelectItem>
                            <SelectItem value="3">Jueves</SelectItem>
                            <SelectItem value="4">Viernes</SelectItem>
                            <SelectItem value="5">Sábado</SelectItem>
                            <SelectItem value="6">Domingo</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid grid-cols-2 gap-1">
                        <div className="grid gap-1.5">
                          <Label>Hora</Label>
                          <Input
                            type="number"
                            min={0}
                            max={23}
                            required
                            value={heartbeatForm.hour}
                            onChange={(e) => setHeartbeatForm(prev => ({ ...prev, hour: parseInt(e.target.value) || 0 }))}
                            className="bg-background/50 border-border/40"
                          />
                        </div>
                        <div className="grid gap-1.5">
                          <Label>Min</Label>
                          <Input
                            type="number"
                            min={0}
                            max={59}
                            required
                            value={heartbeatForm.minute}
                            onChange={(e) => setHeartbeatForm(prev => ({ ...prev, minute: parseInt(e.target.value) || 0 }))}
                            className="bg-background/50 border-border/40"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Wrench className="h-4 w-4" />
                    Herramientas Permitidas
                  </Label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-40 overflow-y-auto p-3 border rounded-xl bg-background/40 border-border/50">
                    {availableTools.map((tool) => (
                      <div key={tool.name} className="flex items-center space-x-2 p-1 hover:bg-primary/5 rounded-lg transition-colors">
                        <Switch
                          id={`modal-tool-${tool.name}`}
                          checked={heartbeatForm.allowed_tools.includes(tool.name)}
                          onCheckedChange={(checked) => {
                            const currentTools = heartbeatForm.allowed_tools;
                            const newTools = checked
                              ? [...currentTools, tool.name]
                              : currentTools.filter(t => t !== tool.name);
                            setHeartbeatForm(prev => ({ ...prev, allowed_tools: newTools }));
                          }}
                        />
                        <Label htmlFor={`modal-tool-${tool.name}`} className="text-xs cursor-pointer flex flex-col">
                          <span className="font-bold">{tool.name}</span>
                          <span className="text-[9px] text-muted-foreground line-clamp-1">{tool.description}</span>
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center space-x-2 py-2">
                  <Switch
                    id="hb_active"
                    checked={heartbeatForm.is_active}
                    onCheckedChange={(checked) => setHeartbeatForm(prev => ({ ...prev, is_active: checked }))}
                  />
                  <Label htmlFor="hb_active" className="cursor-pointer">Programación Activa (Ejecutar de forma recurrente)</Label>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-border/20">
                  <Button type="button" variant="outline" onClick={() => setIsHeartbeatModalOpen(false)}>
                    Cancelar
                  </Button>
                  <Button type="submit">
                    {isEditingHeartbeat ? 'Guardar Cambios' : 'Crear Heartbeat'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
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

        <TabsContent value="remote">
          <Card className="border-none shadow-md bg-gradient-to-br from-card to-secondary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5 text-primary" />
                Acceso a Archivos Locales (SSH)
              </CardTitle>
              <CardDescription>
                Configura una conexión SSH para permitir al agente explorar y leer directamente archivos de tu máquina o de un servidor remoto.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="ssh_host">Servidor / Host SSH</Label>
                    <Input id="ssh_host" placeholder="Ej: 192.168.1.100 o localhost" value={settings?.ssh_host || ''} onChange={(e) => updateSettings({ ssh_host: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ssh_port">Puerto SSH</Label>
                    <Input id="ssh_port" placeholder="22" value={settings?.ssh_port || ''} onChange={(e) => updateSettings({ ssh_port: e.target.value })} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="ssh_user">Usuario SSH</Label>
                    <Input id="ssh_user" placeholder="gato" value={settings?.ssh_user || ''} onChange={(e) => updateSettings({ ssh_user: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="local_base_path">Directorio Raíz Permitido</Label>
                    <Input id="local_base_path" placeholder="/home/gato/Proyectos" value={settings?.local_base_path || ''} onChange={(e) => updateSettings({ local_base_path: e.target.value })} />
                  </div>
                  </div>

                  <div className="flex justify-end pt-2">
                  <Button 
                    onClick={async () => {
                      try {
                        await updateSettings({
                          ssh_host: settings?.ssh_host,
                          ssh_port: settings?.ssh_port,
                          ssh_user: settings?.ssh_user,
                          local_base_path: settings?.local_base_path
                        });
                        toast.success("Configuración SSH guardada correctamente");
                      } catch (err) {
                        toast.error("Error al guardar la configuración SSH");
                      }
                    }}
                  >
                    Guardar Configuración General
                  </Button>
                  </div>

                  <div className="mt-8 border-t border-border pt-4">                  <h4 className="text-sm font-bold mb-2">Credenciales (Guardado Seguro)</h4>
                  <p className="text-xs text-muted-foreground mb-4">La contraseña o llave privada de SSH se guarda encriptada en la bóveda de secretos de tu cuenta.</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="ssh_password">Contraseña SSH (si usa)</Label>
                      <div className="flex gap-2">
                        <Input id="ssh_password" type="password" placeholder="••••••••" onChange={(e) => setNewKey(prev => ({...prev, provider: 'ssh_password', value: e.target.value}))} />
                        <Button variant="secondary" onClick={async () => {
                          if(!newKey.value) return;
                          try {
                            await apiClient.post('/api/users/me/secrets', {
                                key_name: 'SSH_PASSWORD',
                                value: newKey.value,
                                description: 'Contraseña para File Navigator SSH'
                            });
                            toast.success("Contraseña guardada segura");
                          } catch(err) { 
                            console.error("Error saving secret:", err);
                            toast.error("Error guardando contraseña");
                          }
                        }}>Guardar</Button>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="ssh_key">Llave Privada (RSA/ED25519)</Label>
                      <div className="flex gap-2">
                        <Input id="ssh_key" type="password" placeholder="-----BEGIN OPENSSH PRIVATE KEY-----..." onChange={(e) => setNewKey(prev => ({...prev, provider: 'ssh_key', value: e.target.value}))} />
                        <Button variant="secondary" onClick={async () => {
                          if(!newKey.value) return;
                          try {
                            await apiClient.post('/api/users/me/secrets', {
                                key_name: 'SSH_PRIVATE_KEY',
                                value: newKey.value,
                                description: 'Llave privada SSH'
                            });
                            toast.success("Llave guardada segura");
                          } catch(err) {
                            console.error("Error saving secret:", err);
                            toast.error("Error guardando llave");
                          }
                        }}>Guardar</Button>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
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
              <div className="space-y-6">
                <div>
                  <Label className="text-sm font-bold uppercase tracking-widest text-primary/70">Calendario Personal</Label>
                  <p className="text-xs text-muted-foreground mb-2">Eventos y tareas fuera de workspaces.</p>
                  <div className="flex items-center space-x-2">
                    <Input
                      readOnly
                      className="bg-muted/50 font-mono text-xs"
                      value={typeof window !== "undefined" ? `${window.location.origin}/api/caldav/calendars/${user?.account_id}/default/` : ""}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (typeof window !== "undefined") {
                          navigator.clipboard.writeText(`${window.location.origin}/api/caldav/calendars/${user?.account_id}/default/`);
                          toast.success('URL copiada');
                        }
                      }}
                    >
                      Copiar
                    </Button>
                  </div>
                </div>

                {workspaces.length > 0 && (
                  <div className="space-y-4 pt-4 border-t border-border/40">
                    <Label className="text-sm font-bold uppercase tracking-widest text-primary/70">Workspaces</Label>
                    <p className="text-xs text-muted-foreground mb-4">Cada workspace actúa como un calendario independiente.</p>
                    {workspaces.map((ws) => (
                      <div key={ws.id} className="space-y-2 p-4 rounded-2xl bg-muted/30 border border-border/40">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: ws.color || 'var(--primary)' }} />
                          <span className="text-xs font-black uppercase tracking-tight">{ws.name}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Input
                            readOnly
                            className="bg-background/50 font-mono text-[10px] h-8"
                            value={typeof window !== "undefined" ? `${window.location.origin}/api/caldav/calendars/${user?.account_id}/${ws.id}/` : ""}
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-3 text-[10px] font-bold"
                            onClick={() => {
                              if (typeof window !== "undefined") {
                                navigator.clipboard.writeText(`${window.location.origin}/api/caldav/calendars/${user?.account_id}/${ws.id}/`);
                                toast.success(`URL de ${ws.name} copiada`);
                              }
                            }}
                          >
                            Copiar
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
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

        <TabsContent value="integrations">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Puzzle className="h-5 w-5 text-primary" />
                Integraciones Externas
              </CardTitle>
              <CardDescription>
                Conecta KognitoAI con tus herramientas favoritas para ampliar sus capacidades.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <IntegrationsSettings />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
        </main>
      </div>
    </div>
  );
};

export default SettingsPage;