'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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

interface ScheduledToolsStatus {
  total_scheduled: number;
  active_jobs: number;
  system_initialized: boolean;
  available_tools: string[];
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
  weekly_cleanup: 'Limpieza Semanal'
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
  const [status, setStatus] = useState<ScheduledToolsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState<ScheduledTool | null>(null);
  const [createForm, setCreateForm] = useState<CreateToolForm>({
    tool_name: '',
    schedule_type: '',
    hour: 8,
    minute: 0
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [toolsResponse, statusResponse] = await Promise.all([
        apiClient.get('/api/admin/scheduled-tools'),
        apiClient.get('/api/admin/scheduled-tools/status')
      ]);
      setScheduledTools(toolsResponse.data);
      setStatus(statusResponse.data);
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
  };

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

  const handleDeleteTool = async (jobName: string) => {
    if (!confirm('¿Estás seguro de que quieres eliminar esta herramienta programada?')) {
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
    <div className="container mx-auto p-4 space-y-6">
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
                  <TableHead>Cuenta</TableHead>
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
                      {tool.account_id ? (
                        <span className="font-mono text-xs">{tool.account_id}</span>
                      ) : (
                        <Badge variant="secondary">Global</Badge>
                      )}
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
                          onClick={() => handleDeleteTool(tool.job_name)}
                        >
                          <Trash2 className="h-4 w-4" />
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
    </div>
  );
}
