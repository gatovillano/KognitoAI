'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  TrendingUp,
  Search,
  PenTool,
  Send,
  Rocket,
  DollarSign,
  Users,
  Sparkles,
  Copy,
  Check,
  History,
  RefreshCw,
  Zap,
  ArrowRight,
  Bot
} from 'lucide-react';

interface Agent {
  agent_id: string;
  name: string;
  description: string;
  category: string;
  capabilities: string[];
  system_prompt: string;
  metadata: {
    emoji?: string;
    category?: string;
  };
}

interface ExecutionHistory {
  id: string;
  agent_id: string;
  agent_name: string;
  prompt: string;
  response_text: string;
  created_at: string;
  success: boolean;
}

const AGENT_ICONS: Record<string, any> = {
  'growth-researcher': Search,
  'growth-copywriter': PenTool,
  'growth-outreach': Send,
  'growth-launch-director': Rocket,
  'growth-finance': DollarSign,
  'growth-customer-success': Users
};

const AGENT_PRESETS: Record<string, string[]> = {
  'growth-researcher': [
    'Analiza los principales competidores en el mercado de software CRM en español.',
    'Identifica 3 nichos de mercado desatendidos en e-commerce sostenible.',
    'Crea el buyer persona detallado para una app de productividad personal.'
  ],
  'growth-copywriter': [
    'Escribe un titular y subtitular persuasivo con fórmula PAS para una Landing Page B2B.',
    'Redacta una secuencia de 3 emails fríos para ofrecer servicios de desarrollo web.',
    'Crea 3 variantes de anuncios para Meta Ads promocionando un curso online.'
  ],
  'growth-outreach': [
    'Escribe un mensaje frío personalizado en LinkedIn para conectar con un VP de Marketing.',
    'Diseña una plantilla de email de propuesta de alianza estratégica entre dos SaaS.',
    'Crea una secuencia de follow-up de 2 pasos para prospectos no respondidos.'
  ],
  'growth-launch-director': [
    'Diseña un plan de lanzamiento de 30 días para una nueva aplicación móvil de finanzas.',
    'Crea un checklist para el Launch Day de un producto SaaS.',
    'Estructura la estrategia de pre-lanzamiento para generar lista de espera.'
  ],
  'growth-finance': [
    'Calcula el LTV estimado sabiendo que el ARPU es $50/mes y el Churn Mensual es 5%.',
    'Explica cómo optimizar el CAC en campañas de adquisición pagada.',
    'Proyecta el MRR a 12 meses partiendo de $2,000 con un crecimiento del 15% mensual.'
  ],
  'growth-customer-success': [
    'Diseña un playbook de onboarding de 14 días para nuevos usuarios de un SaaS.',
    'Crea una lista de señales de alerta de Churn temprano para clientes B2B.',
    'Estructura un programa de referidos para incentivar el voz a voz.'
  ]
};

export default function GrowthPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('growth-researcher');
  const [prompt, setPrompt] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [currentResponse, setCurrentResponse] = useState<string>('');
  const [history, setHistory] = useState<ExecutionHistory[]>([]);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    fetchAgents();
    fetchHistory();
  }, []);

  const fetchAgents = async () => {
    try {
      const resp = await apiClient.get('/api/v1/growth/agents');
      if (resp.data.success) {
        setAgents(resp.data.agents);
      }
    } catch (err) {
      toast.error('Error al cargar la lista de agentes de Growth');
    }
  };

  const fetchHistory = async () => {
    try {
      const resp = await apiClient.get('/api/v1/growth/history');
      if (resp.data.success) {
        setHistory(resp.data.history);
      }
    } catch (err) {
      // Opcional: ignorar silenciosamente si es primera carga
    }
  };

  const selectedAgent = agents.find(a => a.agent_id === selectedAgentId) || agents[0];

  const handleInvoke = async (textToSubmit?: string) => {
    const message = textToSubmit || prompt;
    if (!message.trim()) {
      toast.error('Por favor escribe una instrucción para el agente.');
      return;
    }

    setLoading(true);
    setCurrentResponse('');

    try {
      const resp = await apiClient.post('/api/v1/growth/invoke', {
        agent_id: selectedAgentId,
        message: message
      });

      if (resp.data.success) {
        setCurrentResponse(resp.data.message);
        toast.success(`Respuesta generada por ${resp.data.agent_name}`);
        fetchHistory();
      } else {
        toast.error(resp.data.error || 'Error ejecutando el agente');
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Error de conexión con el agente');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!currentResponse) return;
    navigator.clipboard.writeText(currentResponse);
    setCopied(true);
    toast.success('Respuesta copiada al portapapeles');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 space-y-6 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-emerald-500/20 to-teal-500/20 text-emerald-500 border border-emerald-500/30">
              <TrendingUp className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                KogniGrowth Suite
              </h1>
              <p className="text-sm text-muted-foreground">
                6 Agentes IA especializados en Estrategia de Crecimiento, Copywriting, Marketing y Finanzas.
              </p>
            </div>
          </div>
        </div>
        <Badge variant="outline" className="w-fit gap-1.5 py-1 px-3 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5">
          <Sparkles className="h-3.5 w-3.5" /> Multi-Agent Suite
        </Badge>
      </div>

      {/* Grid de Agentes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
        {agents.map((agent) => {
          const IconComponent = AGENT_ICONS[agent.agent_id] || Bot;
          const isSelected = selectedAgentId === agent.agent_id;
          const emoji = agent.metadata?.emoji || '🤖';

          return (
            <Card
              key={agent.agent_id}
              onClick={() => setSelectedAgentId(agent.agent_id)}
              className={`cursor-pointer transition-all duration-200 hover:scale-[1.02] border ${
                isSelected
                  ? 'border-emerald-500/60 bg-emerald-500/5 shadow-md shadow-emerald-500/10'
                  : 'hover:border-border/80 bg-card/60'
              }`}
            >
              <CardContent className="p-3.5 text-center flex flex-col items-center space-y-2">
                <div className={`p-2 rounded-xl transition-colors ${isSelected ? 'bg-emerald-500 text-white' : 'bg-muted text-muted-foreground'}`}>
                  <IconComponent className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-xs font-semibold truncate max-w-[120px]">{agent.name}</h3>
                  <span className="text-[10px] text-muted-foreground capitalize">{agent.metadata?.category || 'Growth'}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Panel Principal de Ejecución */}
      {selectedAgent && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Lado Izquierdo: Entrada de Instrucciones & Presets */}
          <div className="lg:col-span-5 space-y-4">
            <Card className="border-border/60 shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{selectedAgent.metadata?.emoji || '🚀'}</span>
                    <CardTitle className="text-lg">{selectedAgent.name}</CardTitle>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {selectedAgent.agent_id}
                  </Badge>
                </div>
                <CardDescription className="text-xs mt-1">
                  {selectedAgent.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Presets sugeridos */}
                {AGENT_PRESETS[selectedAgent.agent_id] && (
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                      <Zap className="h-3 w-3 text-amber-500" /> Prompts sugeridos:
                    </label>
                    <div className="space-y-1">
                      {AGENT_PRESETS[selectedAgent.agent_id].map((preset, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setPrompt(preset);
                            handleInvoke(preset);
                          }}
                          className="w-full text-left text-xs p-2 rounded-lg bg-muted/40 hover:bg-muted/80 transition-colors flex items-center justify-between group"
                        >
                          <span className="truncate pr-2">{preset}</span>
                          <ArrowRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Textarea de entrada */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Tu consulta o requerimiento:</label>
                  <Textarea
                    placeholder={`Ingresa tu requerimiento para el ${selectedAgent.name}...`}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={6}
                    className="resize-none text-sm bg-background/50 focus:bg-background"
                  />
                </div>

                <Button
                  onClick={() => handleInvoke()}
                  disabled={loading || !prompt.trim()}
                  className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white shadow-md shadow-emerald-500/20"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> Procesando con IA...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" /> Consultar Agente
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Lado Derecho: Respuesta y Formato Markdown */}
          <div className="lg:col-span-7 space-y-4">
            <Card className="border-border/60 shadow-sm min-h-[460px] flex flex-col">
              <CardHeader className="pb-3 border-b border-border/40 flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Bot className="h-4 w-4 text-emerald-500" />
                    Respuesta del Agente
                  </CardTitle>
                </div>
                {currentResponse && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopy}
                    className="h-8 gap-1.5 text-xs"
                  >
                    {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                    {copied ? 'Copiado' : 'Copiar'}
                  </Button>
                )}
              </CardHeader>
              <CardContent className="flex-1 p-5 overflow-y-auto max-h-[550px]">
                {loading ? (
                  <div className="h-full flex flex-col items-center justify-center space-y-3 py-16 text-muted-foreground">
                    <RefreshCw className="h-8 w-8 animate-spin text-emerald-500" />
                    <p className="text-sm font-medium">El agente está analizando y redactando la respuesta...</p>
                  </div>
                ) : currentResponse ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none space-y-3">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {currentResponse}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center space-y-2 py-20 text-muted-foreground text-center">
                    <TrendingUp className="h-10 w-10 text-muted-foreground/30" />
                    <p className="text-sm font-medium">Selecciona una plantilla o escribe una instrucción para comenzar.</p>
                    <p className="text-xs text-muted-foreground/70 max-w-xs">
                      Los resultados de la consulta aparecerán aquí formateados en Markdown.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Historial de Ejecuciones Recientes */}
      {history.length > 0 && (
        <Card className="border-border/60 shadow-sm mt-6">
          <CardHeader className="pb-3 border-b border-border/40">
            <CardTitle className="text-base flex items-center gap-2">
              <History className="h-4 w-4 text-emerald-500" />
              Historial de Reportes Generados
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 divide-y divide-border/40">
            {history.slice(0, 5).map((item) => (
              <div key={item.id} className="p-4 hover:bg-muted/20 transition-colors space-y-1.5">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <Badge variant="outline" className="text-[10px] py-0">{item.agent_name}</Badge>
                    {item.prompt}
                  </span>
                  <span>{new Date(item.created_at).toLocaleString()}</span>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2 pl-2 border-l-2 border-emerald-500/40">
                  {item.response_text}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
