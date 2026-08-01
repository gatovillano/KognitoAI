'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, Calendar, TrendingUp, Globe, AppWindow, 
  Eye, Users, MousePointer, Share2, Compass, Laptop, Info, RefreshCw, BarChart2,
  Search, Shield, Activity, Clock, UserCheck, Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, 
  CartesianGrid, Tooltip as RechartsTooltip, Legend, BarChart, Bar, Cell, PieChart, Pie
} from 'recharts';

interface AnalyticsMetric {
  pageviews: number;
  visitors: number;
  active_users?: number;
}

interface AnalyticsData {
  summary: {
    presentation: AnalyticsMetric;
    app: AnalyticsMetric;
    total: AnalyticsMetric;
  };
  charts: {
    timeline: Array<{
      time: string;
      presentation_pageviews: number;
      presentation_visitors: number;
      app_pageviews: number;
      app_visitors: number;
    }>;
    top_pages: Array<{
      path: string;
      views: number;
      unique_visitors: number;
      is_presentation: boolean;
    }>;
    event_types: Array<{
      event: string;
      count: number;
    }>;
    top_referrers: Array<{
      referrer: string;
      count: number;
    }>;
    browsers: Array<{
      name: string;
      value: number;
    }>;
    operating_systems: Array<{
      name: string;
      value: number;
    }>;
  };
}

interface UserActivityStat {
  account_id: string;
  name: string;
  email: string;
  username: string;
  is_admin: boolean;
  last_login_at: string | null;
  last_active_at: string | null;
  total_events: number;
  status: 'online' | 'active' | 'inactive' | 'never';
  top_features: Array<{
    name: string;
    count: number;
    percentage: number;
  }>;
}

const COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b'];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Sin datos';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 'Sin datos';

    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Hace un momento';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours} h`;
    if (diffDays < 7) return `Hace ${diffDays} d`;

    return d.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Sin datos';
  }
}

export default function AnalyticsDashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'traffic' | 'users'>('traffic');
  const [period, setPeriod] = useState<string>('7d');
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // User analytics state
  const [userStats, setUserStats] = useState<UserActivityStat[]>([]);
  const [userLoading, setUserLoading] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/admin/analytics/summary?period=${period}`);
      setData(response.data);
    } catch (error: any) {
      console.error('Error fetching analytics summary:', error);
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las analíticas de tráfico.');
    } finally {
      setLoading(false);
    }
  }, [period]);

  const fetchUserAnalytics = useCallback(async () => {
    try {
      setUserLoading(true);
      const response = await apiClient.get('/api/admin/analytics/users');
      setUserStats(response.data.users || []);
    } catch (error: any) {
      console.error('Error fetching user analytics:', error);
      toast.error(error.response?.data?.detail || 'No se pudieron cargar las analíticas de usuarios.');
    } finally {
      setUserLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'users') {
      fetchUserAnalytics();
    } else {
      fetchAnalytics();
    }
  }, [activeTab, fetchAnalytics, fetchUserAnalytics]);

  const handleRefresh = () => {
    if (activeTab === 'users') {
      fetchUserAnalytics();
    } else {
      fetchAnalytics();
    }
  };

  // Generador de tráfico simulado para pruebas
  const handleGenerateTestData = async () => {
    if (isGenerating) return;
    setIsGenerating(true);
    toast.info('Generando tráfico de prueba simulado...');

    const paths = [
      '/presentacion', 
      '/presentacion/funcionamiento', 
      '/presentacion/casos', 
      '/presentacion/faq', 
      '/presentacion/contacto',
      '/chat', 
      '/documents', 
      '/admin', 
      '/notes', 
      '/settings'
    ];
    
    const referrers = ['https://google.com', 'https://github.com', 'https://linkedin.com', '', 'https://t.co'];
    const browsers = [
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
      'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0'
    ];
    
    const events = ['pageview', 'pageview', 'pageview', 'click', 'form_submit'];

    try {
      const promises = [];
      const totalEvents = 35;

      for (let i = 0; i < totalEvents; i++) {
        const path = paths[Math.floor(Math.random() * paths.length)];
        const referrer = referrers[Math.floor(Math.random() * referrers.length)];
        const userAgent = browsers[Math.floor(Math.random() * browsers.length)];
        const eventType = events[Math.floor(Math.random() * events.length)];
        
        const mockSessionId = 'sess_mock_' + Math.floor(Math.random() * 8 + 1);

        const apiRequest = fetch(`${apiClient.defaults.baseURL}/api/analytics/track`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: mockSessionId,
            event_type: eventType,
            path: path,
            referrer: referrer || null,
            event_metadata: {
              simulated: true,
              timestamp_offset_hours: Math.floor(Math.random() * 72)
            }
          }),
        });
        promises.push(apiRequest);
      }

      await Promise.all(promises);
      toast.success('Se ha generado tráfico de prueba exitosamente. Recargando...');
      setTimeout(() => {
        handleRefresh();
        setIsGenerating(false);
      }, 1500);
    } catch (error) {
      console.error('Error generating mock traffic:', error);
      toast.error('Ocurrió un error al simular tráfico.');
      setIsGenerating(false);
    }
  };

  const hasData = data && data.charts.timeline && data.charts.timeline.length > 0;

  const filteredUsers = userStats.filter((u) => {
    const term = searchTerm.toLowerCase();
    return (
      u.name.toLowerCase().includes(term) ||
      u.email.toLowerCase().includes(term) ||
      (u.username && u.username.toLowerCase().includes(term))
    );
  });

  const totalUsersCount = userStats.length;
  const onlineUsersCount = userStats.filter((u) => u.status === 'online').length;
  const totalUserActivities = userStats.reduce((acc, u) => acc + u.total_events, 0);

  const renderStatusBadge = (status: UserActivityStat['status']) => {
    switch (status) {
      case 'online':
        return (
          <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20 gap-1.5 font-medium">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            En Línea
          </Badge>
        );
      case 'active':
        return (
          <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 hover:bg-amber-500/20 gap-1.5 font-medium">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            Activo Hoy
          </Badge>
        );
      case 'inactive':
        return (
          <Badge className="bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20 hover:bg-slate-500/20 gap-1.5 font-medium">
            <span className="h-2 w-2 rounded-full bg-slate-400" />
            Inactivo
          </Badge>
        );
      case 'never':
      default:
        return (
          <Badge className="bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/20 hover:bg-slate-500/20 gap-1.5 font-medium">
            <span className="h-2 w-2 rounded-full bg-slate-300" />
            Sin Datos
          </Badge>
        );
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
            <Link href="/admin" className="hover:text-foreground flex items-center gap-1">
              <ArrowLeft size={14} /> Volver al Panel de Admin
            </Link>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-cyan-500 to-blue-600 dark:from-cyan-400 dark:to-blue-400 flex items-center gap-3">
            <BarChart2 className="h-8 w-8 text-cyan-500" />
            Tráfico y Uso del Sistema
          </h1>
          <p className="text-muted-foreground">
            Métricas integradas de la landing page, software y actividad de usuarios.
          </p>
        </div>

        {/* Acciones */}
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleGenerateTestData}
            disabled={isGenerating}
            className="border-dashed border-cyan-500/40 hover:border-cyan-500 hover:bg-cyan-500/5 text-xs text-cyan-600 dark:text-cyan-400 gap-1.5"
          >
            <RefreshCw size={13} className={isGenerating ? "animate-spin" : ""} />
            Simular Tráfico de Prueba
          </Button>

          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleRefresh}
            disabled={loading || userLoading}
            className="text-xs gap-1.5"
          >
            <RefreshCw size={13} className={loading || userLoading ? "animate-spin" : ""} />
            Refrescar
          </Button>
        </div>
      </div>

      {/* Tabs Selector & Período */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/40 pb-3">
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === 'traffic' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('traffic')}
            className="gap-2 text-xs font-semibold"
          >
            <TrendingUp size={15} />
            Tráfico General
          </Button>
          <Button
            variant={activeTab === 'users' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('users')}
            className="gap-2 text-xs font-semibold"
          >
            <Users size={15} />
            Usuarios y Funciones
          </Button>
        </div>

        {/* Selector de Período (Solo para Tráfico) */}
        {activeTab === 'traffic' && (
          <div className="flex items-center gap-1.5 bg-muted/40 p-1 rounded-lg border border-border/40 w-fit">
            {[
              { key: '24h', label: '24 Horas' },
              { key: '7d', label: '7 Días' },
              { key: '30d', label: '30 Días' },
              { key: 'all', label: 'Histórico' }
            ].map((p) => (
              <button
                key={p.key}
                onClick={() => setPeriod(p.key)}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                  period === p.key 
                    ? 'bg-background shadow-sm text-foreground border border-border/30' 
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Vista 1: Tráfico General */}
      {activeTab === 'traffic' && (
        <>
          {loading && !data ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-4">
              <RefreshCw size={36} className="text-primary animate-spin" />
              <p className="text-muted-foreground text-sm">Cargando métricas de tráfico y uso...</p>
            </div>
          ) : (
            <>
              {/* Tarjetas de Métricas Resumen */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Landing Page Card */}
                <Card className="border-cyan-500/10 dark:border-cyan-500/5 bg-gradient-to-tr from-background to-cyan-500/[0.02] shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.05] pointer-events-none">
                    <Globe size={100} className="text-cyan-500" />
                  </div>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 flex items-center gap-1.5">
                        <Globe size={12} /> Web de Presentación
                      </span>
                    </div>
                    <CardTitle className="text-sm text-muted-foreground">Tráfico en la Landing Page</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-baseline gap-6">
                      <div>
                        <span className="text-3xl font-extrabold">
                          {data?.summary.presentation.pageviews.toLocaleString() || 0}
                        </span>
                        <span className="text-xs text-muted-foreground block">Vistas de Página</span>
                      </div>
                      <div>
                        <span className="text-3xl font-extrabold">
                          {data?.summary.presentation.visitors.toLocaleString() || 0}
                        </span>
                        <span className="text-xs text-muted-foreground block">Sesiones Únicas</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Software App Card */}
                <Card className="border-blue-500/10 dark:border-blue-500/5 bg-gradient-to-tr from-background to-blue-500/[0.02] shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.05] pointer-events-none">
                    <AppWindow size={100} className="text-blue-500" />
                  </div>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
                        <AppWindow size={12} /> Software Central (App)
                      </span>
                    </div>
                    <CardTitle className="text-sm text-muted-foreground">Uso de la Aplicación</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-baseline justify-between gap-2">
                      <div>
                        <span className="text-3xl font-extrabold">
                          {data?.summary.app.pageviews.toLocaleString() || 0}
                        </span>
                        <span className="text-xs text-muted-foreground block">Vistas de Página</span>
                      </div>
                      <div>
                        <span className="text-3xl font-extrabold">
                          {data?.summary.app.visitors.toLocaleString() || 0}
                        </span>
                        <span className="text-xs text-muted-foreground block">Sesiones Únicas</span>
                      </div>
                      <div>
                        <span className="text-3xl font-extrabold text-blue-500 dark:text-blue-400">
                          {data?.summary.app.active_users?.toLocaleString() || 0}
                        </span>
                        <span className="text-xs text-muted-foreground block">Usuarios Activos</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Consolidated Total Card */}
                <Card className="border-purple-500/10 dark:border-purple-500/5 bg-gradient-to-tr from-background to-purple-500/[0.02] shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.05] pointer-events-none">
                    <TrendingUp size={100} className="text-purple-500" />
                  </div>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                        <TrendingUp size={12} /> Total Consolidado
                      </span>
                    </div>
                    <CardTitle className="text-sm text-muted-foreground">Tráfico y Uso Combinado</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-baseline gap-6">
                      <div>
                        <span className="text-3xl font-extrabold">
                          {data?.summary.total.pageviews.toLocaleString() || 0}
                        </span>
                        <span className="text-xs text-muted-foreground block">Vistas Totales</span>
                      </div>
                      <div>
                        <span className="text-3xl font-extrabold">
                          {data?.summary.total.visitors.toLocaleString() || 0}
                        </span>
                        <span className="text-xs text-muted-foreground block">Visitantes Totales</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Sin datos aún */}
              {!hasData ? (
                <Card className="border-dashed border-border/80">
                  <CardContent className="flex flex-col items-center justify-center py-16 text-center space-y-4">
                    <div className="w-12 h-12 rounded-full bg-cyan-500/10 flex items-center justify-center text-cyan-600 dark:text-cyan-400">
                      <Info size={24} />
                    </div>
                    <div className="max-w-md">
                      <CardTitle className="mb-1">No hay datos de tráfico aún</CardTitle>
                      <CardDescription>
                        La tabla de analíticas ha sido creada pero aún no se han registrado eventos. Haz clic en "Simular Tráfico de Prueba" arriba para poblar los gráficos de inmediato.
                      </CardDescription>
                    </div>
                    <Button onClick={handleGenerateTestData} disabled={isGenerating}>
                      Generar Tráfico Inicial
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <>
                  {/* Gráfico de Línea de Tiempo Principal */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <TrendingUp size={18} className="text-cyan-500" />
                        Histórico de Visitas y Vistas de Página
                      </CardTitle>
                      <CardDescription>
                        Distribución temporal del tráfico entre la web de presentación (Landing) y el software (Exocerebro).
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="h-[350px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={data.charts.timeline}
                          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                        >
                          <defs>
                            <linearGradient id="colorPresentation" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                            </linearGradient>
                            <linearGradient id="colorApp" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                          <XAxis 
                            dataKey="time" 
                            stroke="#888888" 
                            fontSize={11} 
                            tickLine={false} 
                            axisLine={false} 
                          />
                          <YAxis 
                            stroke="#888888" 
                            fontSize={11} 
                            tickLine={false} 
                            axisLine={false} 
                          />
                          <RechartsTooltip 
                            contentStyle={{ 
                              backgroundColor: 'rgba(30, 41, 59, 0.9)', 
                              borderRadius: '8px', 
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              color: '#ffffff'
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                          <Area 
                            name="Landing (Vistas)" 
                            type="monotone" 
                            dataKey="presentation_pageviews" 
                            stroke="#06b6d4" 
                            strokeWidth={2}
                            fillOpacity={1} 
                            fill="url(#colorPresentation)" 
                          />
                          <Area 
                            name="Software (Vistas)" 
                            type="monotone" 
                            dataKey="app_pageviews" 
                            stroke="#3b82f6" 
                            strokeWidth={2}
                            fillOpacity={1} 
                            fill="url(#colorApp)" 
                          />
                          <Area 
                            name="Landing (Visitas)" 
                            type="monotone" 
                            dataKey="presentation_visitors" 
                            stroke="#22c55e" 
                            strokeWidth={1.5}
                            strokeDasharray="4 4"
                            fill="none" 
                          />
                          <Area 
                            name="Software (Visitas)" 
                            type="monotone" 
                            dataKey="app_visitors" 
                            stroke="#a855f7" 
                            strokeWidth={1.5}
                            strokeDasharray="4 4"
                            fill="none" 
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  {/* Grid Secundario */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    
                    {/* Top Páginas */}
                    <Card className="flex flex-col">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Eye size={18} className="text-cyan-500" />
                          Páginas Más Visitadas
                        </CardTitle>
                        <CardDescription>
                          Las 10 rutas más accedidas en la plataforma.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="flex-grow">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Ruta</TableHead>
                              <TableHead className="text-right">Vistas</TableHead>
                              <TableHead className="text-right">Sesiones</TableHead>
                              <TableHead className="text-right">Sección</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {data.charts.top_pages.map((p, idx) => (
                              <TableRow key={idx}>
                                <TableCell className="font-mono text-xs max-w-[220px] truncate" title={p.path}>
                                  {p.path}
                                </TableCell>
                                <TableCell className="text-right font-medium">{p.views}</TableCell>
                                <TableCell className="text-right">{p.unique_visitors}</TableCell>
                                <TableCell className="text-right">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                    p.is_presentation 
                                      ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400' 
                                      : 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                                  }`}>
                                    {p.is_presentation ? 'Landing' : 'App'}
                                  </span>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>

                    {/* Fuentes de Tráfico (Referrers) */}
                    <Card className="flex flex-col">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Share2 size={18} className="text-cyan-500" />
                          Fuentes de Tráfico (Referidores)
                        </CardTitle>
                        <CardDescription>
                          Sitios de procedencia y backlinks que traen usuarios.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="flex-grow flex flex-col justify-between">
                        {data.charts.top_referrers.length === 0 ? (
                          <p className="text-center text-muted-foreground text-sm py-10">Sin datos de referidores externos.</p>
                        ) : (
                          <div className="space-y-4 py-2">
                            {data.charts.top_referrers.map((r, idx) => {
                              const maxCount = data.charts.top_referrers[0]?.count || 1;
                              const percent = Math.round((r.count / maxCount) * 100);
                              return (
                                <div key={idx} className="space-y-1">
                                  <div className="flex justify-between text-xs font-semibold">
                                    <span className="flex items-center gap-1.5">
                                      <Compass size={12} className="text-muted-foreground" />
                                      {r.referrer}
                                    </span>
                                    <span>{r.count} visitas</span>
                                  </div>
                                  <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                                    <div 
                                      className="bg-cyan-500 h-full rounded-full" 
                                      style={{ width: `${percent}%` }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>

                  {/* Tercer Fila: Interacciones y Sistemas Operativos */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    
                    {/* Event Types */}
                    <Card className="flex flex-col">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <MousePointer size={18} className="text-cyan-500" />
                          Interacciones
                        </CardTitle>
                        <CardDescription>Acciones de usuario registradas.</CardDescription>
                      </CardHeader>
                      <CardContent className="flex-grow flex items-center justify-center h-[200px]">
                        {data.charts.event_types.length === 0 ? (
                          <p className="text-muted-foreground text-sm">Sin interacciones.</p>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.charts.event_types} layout="vertical">
                              <CartesianGrid strokeDasharray="3 3" horizontal={false} opacity={0.1} />
                              <XAxis type="number" fontSize={10} tickLine={false} axisLine={false} />
                              <YAxis dataKey="event" type="category" fontSize={10} width={75} tickLine={false} axisLine={false} />
                              <RechartsTooltip />
                              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                                {data.charts.event_types.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        )}
                      </CardContent>
                    </Card>

                    {/* Navegadores (Pie Chart) */}
                    <Card className="flex flex-col">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Laptop size={18} className="text-cyan-500" />
                          Navegadores
                        </CardTitle>
                        <CardDescription>Navegadores más usados.</CardDescription>
                      </CardHeader>
                      <CardContent className="flex-grow flex items-center justify-center h-[200px]">
                        {data.charts.browsers.length === 0 ? (
                          <p className="text-muted-foreground text-sm">Sin datos de agentes.</p>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={data.charts.browsers}
                                cx="50%"
                                cy="50%"
                                innerRadius={50}
                                outerRadius={70}
                                paddingAngle={2}
                                dataKey="value"
                              >
                                {data.charts.browsers.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                              </Pie>
                              <RechartsTooltip />
                              <Legend wrapperStyle={{ fontSize: 10 }} />
                            </PieChart>
                          </ResponsiveContainer>
                        )}
                      </CardContent>
                    </Card>

                    {/* Sistemas Operativos (Pie Chart) */}
                    <Card className="flex flex-col">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Laptop size={18} className="text-cyan-500" />
                          Sistemas Operativos
                        </CardTitle>
                        <CardDescription>Sistemas operativos de origen.</CardDescription>
                      </CardHeader>
                      <CardContent className="flex-grow flex items-center justify-center h-[200px]">
                        {data.charts.operating_systems.length === 0 ? (
                          <p className="text-muted-foreground text-sm">Sin datos de SO.</p>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={data.charts.operating_systems}
                                cx="50%"
                                cy="50%"
                                innerRadius={50}
                                outerRadius={70}
                                paddingAngle={2}
                                dataKey="value"
                              >
                                {data.charts.operating_systems.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={COLORS[(index + 2) % COLORS.length]} />
                                ))}
                              </Pie>
                              <RechartsTooltip />
                              <Legend wrapperStyle={{ fontSize: 10 }} />
                            </PieChart>
                          </ResponsiveContainer>
                        )}
                      </CardContent>
                    </Card>

                  </div>
                </>
              )}
            </>
          )}
        </>
      )}

      {/* Vista 2: Usuarios y Funciones */}
      {activeTab === 'users' && (
        <>
          {userLoading && userStats.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-4">
              <RefreshCw size={36} className="text-primary animate-spin" />
              <p className="text-muted-foreground text-sm">Cargando actividad de usuarios...</p>
            </div>
          ) : (
            <>
              {/* Tarjetas de Resumen de Usuarios */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Total Usuarios */}
                <Card className="border-cyan-500/10 dark:border-cyan-500/5 bg-gradient-to-tr from-background to-cyan-500/[0.02] shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.05] pointer-events-none">
                    <Users size={100} className="text-cyan-500" />
                  </div>
                  <CardHeader className="pb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 flex items-center gap-1.5">
                      <Users size={12} /> Cuentas Registradas
                    </span>
                    <CardTitle className="text-sm text-muted-foreground">Total Usuarios</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-extrabold">{totalUsersCount}</div>
                  </CardContent>
                </Card>

                {/* Usuarios En Línea */}
                <Card className="border-emerald-500/10 dark:border-emerald-500/5 bg-gradient-to-tr from-background to-emerald-500/[0.02] shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.05] pointer-events-none">
                    <UserCheck size={100} className="text-emerald-500" />
                  </div>
                  <CardHeader className="pb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                      <UserCheck size={12} /> Activos (últimos 15 min)
                    </span>
                    <CardTitle className="text-sm text-muted-foreground">Usuarios En Línea</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-extrabold text-emerald-500">{onlineUsersCount}</div>
                  </CardContent>
                </Card>

                {/* Total Actividades */}
                <Card className="border-purple-500/10 dark:border-purple-500/5 bg-gradient-to-tr from-background to-purple-500/[0.02] shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-8 opacity-[0.05] pointer-events-none">
                    <Zap size={100} className="text-purple-500" />
                  </div>
                  <CardHeader className="pb-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                      <Zap size={12} /> Eventos Registrados
                    </span>
                    <CardTitle className="text-sm text-muted-foreground">Total Actividades</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-extrabold">{totalUserActivities.toLocaleString()}</div>
                  </CardContent>
                </Card>
              </div>

              {/* Filtro y Tabla de Actividad de Usuarios */}
              <Card>
                <CardHeader>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Activity size={18} className="text-cyan-500" />
                        Actividad Detallada de Usuarios
                      </CardTitle>
                      <CardDescription>
                        Desglose individual de inicios de sesión, última actividad y funciones más utilizadas.
                      </CardDescription>
                    </div>

                    {/* Buscador */}
                    <div className="relative w-full sm:w-72">
                      <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        type="text"
                        placeholder="Buscar por nombre o email..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-9 text-xs"
                      />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {filteredUsers.length === 0 ? (
                    <div className="text-center text-muted-foreground py-12 text-sm">
                      {searchTerm ? 'No se encontraron usuarios que coincidan con la búsqueda.' : 'No hay usuarios registrados en el sistema.'}
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Usuario</TableHead>
                          <TableHead>Estado</TableHead>
                          <TableHead>Última Conexión</TableHead>
                          <TableHead>Última Actividad</TableHead>
                          <TableHead className="text-center">Acciones</TableHead>
                          <TableHead>Funciones Más Utilizadas</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredUsers.map((u) => (
                          <TableRow key={u.account_id}>
                            {/* Usuario */}
                            <TableCell>
                              <div className="flex items-center gap-3">
                                <Avatar className="h-9 w-9 border border-border/60">
                                  <AvatarFallback className="bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 font-bold text-xs">
                                    {u.name ? u.name.charAt(0).toUpperCase() : 'U'}
                                  </AvatarFallback>
                                </Avatar>
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-1.5">
                                    <span className="font-semibold text-xs">{u.name}</span>
                                    {u.is_admin && (
                                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20 font-bold">
                                        <Shield size={10} className="mr-0.5" /> Admin
                                      </Badge>
                                    )}
                                  </div>
                                  <span className="text-[11px] text-muted-foreground block">{u.email}</span>
                                </div>
                              </div>
                            </TableCell>

                            {/* Estado */}
                            <TableCell>
                              {renderStatusBadge(u.status)}
                            </TableCell>

                            {/* Última Conexión */}
                            <TableCell className="text-xs text-muted-foreground">
                              <div className="flex items-center gap-1.5">
                                <Clock size={12} className="text-muted-foreground/70" />
                                {formatDate(u.last_login_at)}
                              </div>
                            </TableCell>

                            {/* Última Actividad */}
                            <TableCell className="text-xs text-muted-foreground">
                              <div className="flex items-center gap-1.5">
                                <Activity size={12} className="text-muted-foreground/70" />
                                {formatDate(u.last_active_at)}
                              </div>
                            </TableCell>

                            {/* Acciones Totales */}
                            <TableCell className="text-center font-bold text-xs font-mono">
                              {u.total_events}
                            </TableCell>

                            {/* Funciones Más Utilizadas */}
                            <TableCell>
                              {u.top_features && u.top_features.length > 0 ? (
                                <div className="space-y-1.5 max-w-[280px]">
                                  {u.top_features.map((feat, i) => (
                                    <div key={i} className="text-xs space-y-0.5">
                                      <div className="flex justify-between items-center text-[11px]">
                                        <span className="font-medium truncate max-w-[170px]" title={feat.name}>
                                          {feat.name}
                                        </span>
                                        <span className="text-muted-foreground font-mono">
                                          {feat.count} ({feat.percentage}%)
                                        </span>
                                      </div>
                                      <div className="w-full bg-muted/60 rounded-full h-1.5 overflow-hidden">
                                        <div
                                          className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full transition-all"
                                          style={{ width: `${Math.max(feat.percentage, 4)}%` }}
                                        />
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-xs text-muted-foreground italic">Sin actividad registrada</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  );
}
