'use client';

import { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, Clock, Plus, Settings, Trash2, Edit, Play, Pause } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface ScheduledTool {
  job_name: string;
  tool_name: string;
  schedule_type: string;
  account_id?: string;
  schedule_info: string;
  next_run?: string;
  is_active: boolean;
}

interface User {
  id: string;
  name: string;
}

interface ScheduledToolsStatus {
  total_scheduled: number;
  active_jobs: number;
  system_initialized: boolean;
  available_tools: string[];
}

interface AutonomousHeartbeatConfig {
  enabled: boolean;
  interval_hours: number;
  lookback_days: number;
  max_insights: number;
  instructions: string;
  scheduled_jobs: number;
}

interface CreateToolForm {
  tool_name: string;
  schedule_type: string;
  hour: number;
  minute: number;
  day_of_week?: number;
  interval_hours?: number;
  account_id?: string;
}

const TOOL_NAMES = {
  daily_analysis: 'Análisis Diario',
  daily_insights: 'Insights Diarios',
  weekly_cleanup: 'Limpieza Semanal',
  autonomous_heartbeat: 'Heartbeat Autónomo'
};

const SCHEDULE_TYPES = {
  daily: 'Diario',
  weekly: 'Semanal',
  interval: 'Por Intervalo'
};

const DAYS_OF_WEEK = [
  'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'
];

export default function ScheduledToolsAdminPage() {
  const [scheduledTools, setScheduledTools] = useState<ScheduledTool[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [status, setStatus] = useState<ScheduledToolsStatus | null>(null);
  const [heartbeatConfig, setHeartbeatConfig] = useState<AutonomousHeartbeatConfig | null>(null);
  const [savingHeartbeatConfig, setSavingHeartbeatConfig] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isTriggerHeartbeatDialogOpen, setIsTriggerHeartbeatDialogOpen] = useState(false);
  const [selectedAccountForHeartbeat, setSelectedAccountForHeartbeat] = useState<string>('');
  const [triggeringHeartbeat, setTriggeringHeartbeat] = useState(false);
  const [availableHeartbeatTools, setAvailableHeartbeatTools] = useState<{name: string; description: string}[]>([]);
  const [selectedHeartbeatTools, setSelectedHeartbeatTools] = useState<string[]>([]);
  const [loadingHeartbeatTools, setLoadingHeartbeatTools] = useState(false);
  const [selectedTool, setSelectedTool] = useState<ScheduledTool | null>(null);
  const [createForm, setCreateForm] = useState<CreateToolForm>({
    tool_name: '',
    schedule_type: '',
    hour: 8,
    minute: 0
  });
  const [editForm, setEditForm] = useState<CreateToolForm>({
    tool_name: '',
    schedule_type: '',
    hour: 8,
    minute: 0
  });
  const { toast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [toolsResponse, statusResponse, usersResponse] = await Promise.all([
        apiClient.get('/api/admin/scheduled-tools'),
        apiClient.get('/api/admin/scheduled-tools/status'),
        apiClient.get('/api/admin/users')
      ]);
      const heartbeatConfigResponse = await apiClient.get('/api/admin/scheduled-tools/heartbeat-config');
      setScheduledTools(toolsResponse.data);
      setStatus(statusResponse.data);
      setUsers(usersResponse.data);
      setHeartbeatConfig(heartbeatConfigResponse.data);
    } catch (error: any) {
      console.error('Error fetching scheduled tools:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudieron cargar las herramientas programadas',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]); // Add dependencies for fetchData here if any
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateTool = async () => {
    try {
      await apiClient.post('/api/admin/scheduled-tools', createForm);
      toast({
        title: 'Éxito',
        description: 'Herramienta programada creada exitosamente',
      });
      setIsCreateDialogOpen(false);
      setCreateForm({
        tool_name: '',
        schedule_type: '',
        hour: 8,
        minute: 0
      });
      fetchData();
    } catch (error: any) {
      console.error('Error creating scheduled tool:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al crear la herramienta programada',
        variant: 'destructive',
      });
    }
  };

  const handleSaveHeartbeatConfig = async () => {
    if (!heartbeatConfig) return;

    try {
      setSavingHeartbeatConfig(true);
      await apiClient.put('/api/admin/scheduled-tools/heartbeat-config', heartbeatConfig);
      toast({
        title: 'Éxito',
        description: 'Configuración del heartbeat autónomo actualizada',
      });
      await fetchData();
    } catch (error: any) {
      console.error('Error updating heartbeat config:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudo guardar la configuración del heartbeat',
        variant: 'destructive',
      });
    } finally {
      setSavingHeartbeatConfig(false);
    }
  };

  const fetchAvailableHeartbeatTools = async (accountId: string) => {
    if (!accountId) return;
    try {
      setLoadingHeartbeatTools(true);
      const response = await apiClient.get(`/api/admin/scheduled-tools/available-tools?account_id=${accountId}`);
      setAvailableHeartbeatTools(response.data?.tools || []);
    } catch (error) {
      console.error('Error fetching available tools:', error);
      setAvailableHeartbeatTools([]);
    } finally {
      setLoadingHeartbeatTools(false);
    }
  };

  const handleAccountForHeartbeatChange = (accountId: string) => {
    setSelectedAccountForHeartbeat(accountId);
    setSelectedHeartbeatTools([]);
    fetchAvailableHeartbeatTools(accountId);
  };

  const toggleHeartbeatTool = (toolName: string) => {
    setSelectedHeartbeatTools(prev =>
      prev.includes(toolName) ? prev.filter(t => t !== toolName) : [...prev, toolName]
    );
  };

  const handleTriggerHeartbeat = async () => {
    if (!selectedAccountForHeartbeat) {
      toast({
        title: 'Error',
        description: 'Por favor selecciona una cuenta',
        variant: 'destructive',
      });
      return;
    }

    try {
      setTriggeringHeartbeat(true);
      const payload: any = { account_id: selectedAccountForHeartbeat };
      if (selectedHeartbeatTools.length > 0) {
        payload.allowed_tools = selectedHeartbeatTools;
      }
      const response = await apiClient.post('/api/admin/scheduled-tools/trigger-heartbeat', payload);
      
      toast({
        title: 'Éxito',
        description: response.data?.message || 'Heartbeat autónomo disparado exitosamente',
      });
      
      setIsTriggerHeartbeatDialogOpen(false);
      setSelectedAccountForHeartbeat('');
      setSelectedHeartbeatTools([]);
    } catch (error: any) {
      console.error('Error triggering heartbeat:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al disparar el heartbeat autónomo',
        variant: 'destructive',
      });
    } finally {
      setTriggeringHeartbeat(false);
    }
  };

  const handleToggleActive = async (jobName: string, currentStatus: boolean) => {
    try {
      await apiClient.put(`/api/admin/scheduled-tools/${jobName}`, { is_active: !currentStatus });
      toast({
        title: 'Éxito',
        description: `Herramienta programada ${currentStatus ? 'desactivada' : 'activada'} exitosamente.`,
      });
      fetchData();
    } catch (error: any) {
      console.error('Error toggling scheduled tool status:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al cambiar el estado de la herramienta programada',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteTool = async (jobName: string) => {
    if (!confirm('¿Estás seguro de que quieres eliminar esta herramienta programada? Esta acción es irreversible.')) {
      return;
    }

    try {
      await apiClient.delete(`/api/admin/scheduled-tools/${jobName}`);
      toast({
        title: 'Éxito',
        description: 'Herramienta programada eliminada exitosamente',
      });
      fetchData();
    } catch (error: any) {
      console.error('Error deleting scheduled tool:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al eliminar la herramienta programada',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateTool = async () => {
    if (!selectedTool) return;

    try {
      await apiClient.put(`/api/admin/scheduled-tools/${selectedTool.job_name}`, editForm);
      toast({
        title: 'Éxito',
        description: 'Herramienta programada actualizada exitosamente',
      });
      setIsEditDialogOpen(false);
      fetchData();
    } catch (error: any) {
      console.error('Error updating scheduled tool:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Error al actualizar la herramienta programada',
        variant: 'destructive',
      });
    }
  };

  const handleEditTool = (tool: ScheduledTool) => {
    setSelectedTool(tool);
    // Parse schedule_info to populate editForm. This is a simplified example.
    // A more robust solution would involve receiving structured schedule data from the API.
    let hour = 0;
    let minute = 0;
    let day_of_week: number | undefined = undefined;
    let interval_hours: number | undefined = undefined;

    // Regex para extraer la hora y el minuto
    const timeMatch = tool.schedule_info.match(/(\d{2}):(\d{2})/);
    if (timeMatch) {
      hour = parseInt(timeMatch[1]);
      minute = parseInt(timeMatch[2]);
    }

    if (tool.schedule_type === 'weekly') {
      // Regex para extraer el día de la semana
      const dayMatch = tool.schedule_info.match(/\(([^)]+)\)/);
      if (dayMatch && dayMatch[1]) {
        day_of_week = DAYS_OF_WEEK.indexOf(dayMatch[1]);
      }
    } else if (tool.schedule_type === 'interval') {
      // Regex para extraer el intervalo en horas
      const intervalMatch = tool.schedule_info.match(/cada (\d+) horas/);
      if (intervalMatch && intervalMatch[1]) {
        interval_hours = parseInt(intervalMatch[1]);
      }
    }

    setEditForm({
      tool_name: tool.tool_name,
      schedule_type: tool.schedule_type,
      hour: hour,
      minute: minute,
      day_of_week: day_of_week,
      interval_hours: interval_hours,
      account_id: tool.account_id,
    });
    setIsEditDialogOpen(true);
  };

  const formatNextRun = (nextRun?: string) => {
    if (!nextRun) return 'No disponible';
    try {
      const date = new Date(nextRun);
      return date.toLocaleString('es-ES');
    } catch {
      return nextRun;
    }
  };

  const getToolDisplayName = (toolName: string) => {
    return TOOL_NAMES[toolName as keyof typeof TOOL_NAMES] || toolName;
  };

  const getScheduleTypeDisplayName = (scheduleType: string) => {
    return SCHEDULE_TYPES[scheduleType as keyof typeof SCHEDULE_TYPES] || scheduleType;
  };

  const getUserName = (accountId?: string) => {
    if (!accountId) return 'Global';
    const user = users.find(u => u.id === accountId);
    return user ? user.name : accountId;
  };

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
            <p>Cargando herramientas programadas...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <Settings className="mr-3 h-8 w-8 text-primary" />
            Administración de Herramientas Programadas
          </h1>
          <p className="text-muted-foreground mt-2">
            Gestiona las herramientas automáticas del sistema
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-primary hover:bg-primary/90">
              <Plus className="mr-2 h-4 w-4" />
              Nueva Herramienta
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Crear Nueva Herramienta Programada</DialogTitle>
              <DialogDescription>
                Configura una nueva herramienta para ejecutarse automáticamente
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="tool_name">Herramienta</Label>
                <Select value={createForm.tool_name} onValueChange={(value) => 
                  setCreateForm(prev => ({ ...prev, tool_name: value }))
                }>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona una herramienta" />
                  </SelectTrigger>
                  <SelectContent>
                    {status?.available_tools.map(tool => (
                      <SelectItem key={tool} value={tool}>
                        {getToolDisplayName(tool)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="schedule_type">Tipo de Programación</Label>
                <Select value={createForm.schedule_type} onValueChange={(value) => 
                  setCreateForm(prev => ({ ...prev, schedule_type: value }))
                }>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona el tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Diario</SelectItem>
                    <SelectItem value="weekly">Semanal</SelectItem>
                    <SelectItem value="interval">Por Intervalo</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="hour">Hora</Label>
                  <Input
                    id="hour"
                    type="number"
                    min="0"
                    max="23"
                    value={createForm.hour}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, hour: parseInt(e.target.value) || 0 }))}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="minute">Minuto</Label>
                  <Input
                    id="minute"
                    type="number"
                    min="0"
                    max="59"
                    value={createForm.minute}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, minute: parseInt(e.target.value) || 0 }))}
                  />
                </div>
              </div>

              {createForm.schedule_type === 'weekly' && (
                <div className="grid gap-2">
                  <Label htmlFor="day_of_week">Día de la Semana</Label>
                  <Select value={createForm.day_of_week?.toString()} onValueChange={(value) => 
                    setCreateForm(prev => ({ ...prev, day_of_week: parseInt(value) }))
                  }>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona el día" />
                    </SelectTrigger>
                    <SelectContent>
                      {DAYS_OF_WEEK.map((day, index) => (
                        <SelectItem key={index} value={index.toString()}>
                          {day}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {createForm.schedule_type === 'interval' && (
                <div className="grid gap-2">
                  <Label htmlFor="interval_hours">Intervalo (horas)</Label>
                  <Input
                    id="interval_hours"
                    type="number"
                    min="1"
                    value={createForm.interval_hours || ''}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, interval_hours: parseInt(e.target.value) || undefined }))}
                  />
                </div>
              )}

              <div className="grid gap-2">
                <Label htmlFor="account_id">ID de Cuenta (opcional)</Label>
                <Input
                  id="account_id"
                  placeholder="Dejar vacío para aplicar globalmente"
                  value={createForm.account_id || ''}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, account_id: e.target.value || undefined }))}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleCreateTool} disabled={!createForm.tool_name || !createForm.schedule_type}>
                Crear Herramienta
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Estado del Sistema */}
      {status && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Programadas</CardTitle>
              <Settings className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status.total_scheduled}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Trabajos Activos</CardTitle>
              <Play className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status.active_jobs}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Sistema</CardTitle>
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {status.system_initialized ? (
                  <Badge variant="default" className="bg-green-500">Activo</Badge>
                ) : (
                  <Badge variant="destructive">Inactivo</Badge>
                )}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Herramientas Disponibles</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status.available_tools.length}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {!status?.system_initialized && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            El sistema de herramientas programadas no está inicializado. Algunas funciones pueden no estar disponibles.
          </AlertDescription>
        </Alert>
      )}

      {heartbeatConfig && (
        <Card>
          <CardHeader>
            <CardTitle>Configuración del Heartbeat Autónomo</CardTitle>
            <CardDescription>
              Define la frecuencia y el comportamiento de generación proactiva de alertas e insights profesionales.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <p className="font-medium">Heartbeat habilitado</p>
                <p className="text-sm text-muted-foreground">Activa o pausa la ejecución automática para todas las cuentas activas.</p>
              </div>
              <Switch
                checked={heartbeatConfig.enabled}
                onCheckedChange={(checked) => setHeartbeatConfig(prev => prev ? ({ ...prev, enabled: checked }) : prev)}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="hb_interval_hours">Intervalo (horas)</Label>
                <Input
                  id="hb_interval_hours"
                  type="number"
                  min="1"
                  max="168"
                  value={heartbeatConfig.interval_hours}
                  onChange={(e) => setHeartbeatConfig(prev => prev ? ({ ...prev, interval_hours: Math.max(1, parseInt(e.target.value) || 1) }) : prev)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="hb_lookback_days">Ventana histórica (días)</Label>
                <Input
                  id="hb_lookback_days"
                  type="number"
                  min="1"
                  max="90"
                  value={heartbeatConfig.lookback_days}
                  onChange={(e) => setHeartbeatConfig(prev => prev ? ({ ...prev, lookback_days: Math.max(1, parseInt(e.target.value) || 1) }) : prev)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="hb_max_insights">Máximo insights por corrida</Label>
                <Input
                  id="hb_max_insights"
                  type="number"
                  min="1"
                  max="20"
                  value={heartbeatConfig.max_insights}
                  onChange={(e) => setHeartbeatConfig(prev => prev ? ({ ...prev, max_insights: Math.max(1, parseInt(e.target.value) || 1) }) : prev)}
                />
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="hb_instructions">Instrucciones operativas del heartbeat</Label>
              <Textarea
                id="hb_instructions"
                rows={5}
                value={heartbeatConfig.instructions}
                onChange={(e) => setHeartbeatConfig(prev => prev ? ({ ...prev, instructions: e.target.value }) : prev)}
              />
            </div>

            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">Jobs programados actualmente: {heartbeatConfig.scheduled_jobs}</p>
              <div className="flex gap-2">
                <Dialog open={isTriggerHeartbeatDialogOpen} onOpenChange={setIsTriggerHeartbeatDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" className="border-blue-500 text-blue-500 hover:bg-blue-50">
                      <Play className="mr-2 h-4 w-4" />
                      Disparar Ahora
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                      <DialogTitle>Ejecutar Heartbeat Manualmente</DialogTitle>
                      <DialogDescription>
                        Selecciona la cuenta y opcionalmente las herramientas que el heartbeat puede usar para enriquecer su análisis.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid gap-2">
                        <Label htmlFor="account_select">Cuenta</Label>
                        <Select value={selectedAccountForHeartbeat} onValueChange={handleAccountForHeartbeatChange}>
                          <SelectTrigger id="account_select">
                            <SelectValue placeholder="Selecciona una cuenta" />
                          </SelectTrigger>
                          <SelectContent>
                            {users.map(user => (
                              <SelectItem key={user.id} value={user.id}>
                                {user.name} ({user.email})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      {selectedAccountForHeartbeat && (
                        <div className="grid gap-2">
                          <Label>Herramientas permitidas <span className="text-xs text-muted-foreground">(opcional)</span></Label>
                          {loadingHeartbeatTools ? (
                            <p className="text-sm text-muted-foreground">Cargando herramientas...</p>
                          ) : availableHeartbeatTools.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No hay herramientas disponibles</p>
                          ) : (
                            <div className="max-h-48 overflow-y-auto border rounded-md p-2 space-y-1">
                              {availableHeartbeatTools.map(tool => (
                                <div
                                  key={tool.name}
                                  className={`flex items-start gap-2 p-2 rounded cursor-pointer hover:bg-accent transition-colors ${selectedHeartbeatTools.includes(tool.name) ? 'bg-accent' : ''}`}
                                  onClick={() => toggleHeartbeatTool(tool.name)}
                                >
                                  <input
                                    type="checkbox"
                                    className="mt-0.5 cursor-pointer"
                                    checked={selectedHeartbeatTools.includes(tool.name)}
                                    onChange={() => toggleHeartbeatTool(tool.name)}
                                    onClick={e => e.stopPropagation()}
                                  />
                                  <div>
                                    <p className="text-sm font-medium">{tool.name}</p>
                                    {tool.description && (
                                      <p className="text-xs text-muted-foreground line-clamp-1">{tool.description}</p>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          {selectedHeartbeatTools.length > 0 && (
                            <p className="text-xs text-muted-foreground">{selectedHeartbeatTools.length} herramienta(s) seleccionada(s)</p>
                          )}
                        </div>
                      )}
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => {
                        setIsTriggerHeartbeatDialogOpen(false);
                        setSelectedAccountForHeartbeat('');
                        setSelectedHeartbeatTools([]);
                      }}>
                        Cancelar
                      </Button>
                      <Button onClick={handleTriggerHeartbeat} disabled={triggeringHeartbeat || !selectedAccountForHeartbeat}>
                        {triggeringHeartbeat ? 'Ejecutando...' : 'Ejecutar'}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
                <Button onClick={handleSaveHeartbeatConfig} disabled={savingHeartbeatConfig}>
                  {savingHeartbeatConfig ? 'Guardando...' : 'Guardar configuración'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabla de Herramientas Programadas */}
      <Card>
        <CardHeader>
          <CardTitle>Herramientas Programadas</CardTitle>
          <CardDescription>
            Lista de todas las herramientas configuradas para ejecutarse automáticamente
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Herramienta</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Programación</TableHead>
                  <TableHead>Usuario</TableHead>
                  <TableHead>Próxima Ejecución</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {scheduledTools.map((tool) => (
                  <TableRow key={tool.job_name}>
                    <TableCell className="font-medium">
                      {getToolDisplayName(tool.tool_name)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {getScheduleTypeDisplayName(tool.schedule_type)}
                      </Badge>
                    </TableCell>
                    <TableCell>{tool.schedule_info}</TableCell>
                    <TableCell>
                      {getUserName(tool.account_id)}
                    </TableCell>
                    <TableCell>{formatNextRun(tool.next_run)}</TableCell>
                    <TableCell>
                      {tool.is_active ? (
                        <Badge variant="default" className="bg-green-500">Activo</Badge>
                      ) : (
                        <Badge variant="secondary">Inactivo</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleActive(tool.job_name, tool.is_active)}
                          title={tool.is_active ? 'Desactivar' : 'Activar'}
                        >
                          {tool.is_active ? (
                            <Pause className="h-4 w-4 text-orange-500" />
                          ) : (
                            <Play className="h-4 w-4 text-green-500" />
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditTool(tool)}
                          title="Editar"
                        >
                          <Edit className="h-4 w-4 text-blue-500" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteTool(tool.job_name)}
                          title="Eliminar"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {scheduledTools.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No hay herramientas programadas configuradas
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Editar Herramienta Programada</DialogTitle>
            <DialogDescription>
              {`Modifica la configuración de la herramienta programada "${selectedTool?.job_name}"`}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit_tool_name">Herramienta</Label>
              <Select value={editForm.tool_name} onValueChange={(value) =>
                setEditForm(prev => ({ ...prev, tool_name: value }))
              } disabled> {/* Tool name usually not editable */}
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona una herramienta" />
                </SelectTrigger>
                <SelectContent>
                  {status?.available_tools.map(tool => (
                    <SelectItem key={tool} value={tool}>
                      {getToolDisplayName(tool)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="edit_schedule_type">Tipo de Programación</Label>
              <Select value={editForm.schedule_type} onValueChange={(value) =>
                setEditForm(prev => ({ ...prev, schedule_type: value }))
              }>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona el tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Diario</SelectItem>
                  <SelectItem value="weekly">Semanal</SelectItem>
                  <SelectItem value="interval">Por Intervalo</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="edit_hour">Hora</Label>
                <Input
                  id="edit_hour"
                  type="number"
                  min="0"
                  max="23"
                  value={editForm.hour}
                  onChange={(e) => setEditForm(prev => ({ ...prev, hour: parseInt(e.target.value) || 0 }))}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit_minute">Minuto</Label>
                <Input
                  id="edit_minute"
                  type="number"
                  min="0"
                  max="59"
                  value={editForm.minute}
                  onChange={(e) => setEditForm(prev => ({ ...prev, minute: parseInt(e.target.value) || 0 }))}
                />
              </div>
            </div>

            {editForm.schedule_type === 'weekly' && (
              <div className="grid gap-2">
                <Label htmlFor="edit_day_of_week">Día de la Semana</Label>
                <Select value={editForm.day_of_week?.toString()} onValueChange={(value) =>
                  setEditForm(prev => ({ ...prev, day_of_week: parseInt(value) }))
                }>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecciona el día" />
                  </SelectTrigger>
                  <SelectContent>
                    {DAYS_OF_WEEK.map((day, index) => (
                      <SelectItem key={index} value={index.toString()}>
                        {day}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {editForm.schedule_type === 'interval' && (
              <div className="grid gap-2">
                <Label htmlFor="edit_interval_hours">Intervalo (horas)</Label>
                <Input
                  id="edit_interval_hours"
                  type="number"
                  min="1"
                  value={editForm.interval_hours || ''}
                  onChange={(e) => setEditForm(prev => ({ ...prev, interval_hours: parseInt(e.target.value) || undefined }))}
                />
              </div>
            )}

            <div className="grid gap-2">
              <Label htmlFor="edit_account_id">ID de Cuenta (opcional)</Label>
              <Input
                id="edit_account_id"
                placeholder="Dejar vacío para aplicar globalmente"
                value={editForm.account_id || ''}
                onChange={(e) => setEditForm(prev => ({ ...prev, account_id: e.target.value || undefined }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={() => handleUpdateTool()} disabled={!editForm.tool_name || !editForm.schedule_type}>
              Guardar Cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}