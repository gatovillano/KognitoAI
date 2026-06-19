// src/app/(dashboard)/admin/page.tsx
'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Users, Settings, Clock, ArrowRight, Plus, Edit, Trash2, Network, BarChart2, FlaskConical, RefreshCw, CheckCircle, AlertTriangle, Zap } from 'lucide-react';
import apiClient from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface User {
  id: string;
  name: string;
  email: string;
  username: string;
  telegram_id?: number;
  is_admin: boolean;
}

interface AdminMetricsResponse {
  total_users: number;
  total_scheduled_tools: number;
  active_scheduled_tools: number;
}

interface PipelineMetric {
  metric: string;
  value: number;
  reference: number;
  status: 'OK' | 'WARNING';
  unit?: string;
}

interface PipelineHistoryEntry {
  filename: string;
  timestamp: string;
  metrics: PipelineMetric[];
  summary: { total_metrics: number; warnings: number };
  is_real?: boolean;
  execution_time_seconds?: number;
}

interface PipelineStatus {
  is_running: boolean;
  last_run_time: string | null;
  error: string | null;
}

interface PipelineResults {
  latest: {
    timestamp: string;
    metrics: PipelineMetric[];
    summary: { total_metrics: number; warnings: number };
    is_real?: boolean;
    execution_time_seconds?: number;
  } | null;
  history: PipelineHistoryEntry[];
  status: PipelineStatus;
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AdminPage({ params }: PageProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const router = useRouter();

  // Type assertion to treat params as a synchronous object
  const syncParams = params as unknown as { id: string };
  const { id: adminId } = syncParams; // Using adminId to avoid conflict if 'id' is used elsewhere

  const [metrics, setMetrics] = useState<AdminMetricsResponse | null>(null);
  const [pipelineResults, setPipelineResults] = useState<PipelineResults | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  const [isCreateUserDialogOpen, setIsCreateUserDialogOpen] = useState(false);
  const [isEditUserDialogOpen, setIsEditUserDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [newUserData, setNewUserData] = useState({
    name: '',
    email: '',
    username: '',
    password: '',
    is_admin: false,
  });
  const [editingUserData, setEditingUserData] = useState({
    name: '',
    email: '',
    username: '',
    is_admin: false,
  });

  const handleCreateUser = async () => {
    try {
      await apiClient.post('/api/admin/users', newUserData);
      toast({
        title: 'Éxito',
        description: 'Usuario creado exitosamente.',
      });
      setIsCreateUserDialogOpen(false);
      setNewUserData({
        name: '',
        email: '',
        username: '',
        password: '',
        is_admin: false,
      });
      fetchUsers();
    } catch (error: any) {
      console.error('Error creating user:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudo crear el usuario.',
        variant: 'destructive',
      });
    }
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setEditingUserData({
      name: user.name,
      email: user.email,
      username: user.username,
      is_admin: user.is_admin,
    });
    setIsEditUserDialogOpen(true);
  };

  const handleUpdateUser = async () => {
    if (!editingUser) return;

    try {
      await apiClient.put(`/api/admin/users/${editingUser.id}`, editingUserData);
      toast({
        title: 'Éxito',
        description: 'Usuario actualizado exitosamente.',
      });
      setIsEditUserDialogOpen(false);
      setEditingUser(null);
      fetchUsers();
    } catch (error: any) {
      console.error('Error updating user:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudo actualizar el usuario.',
        variant: 'destructive',
      });
    }
  };



  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/admin/users');
      setUsers(response.data);
      setLoading(false);
    } catch (error: any) {
      console.error('Error fetching users:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudieron cargar los usuarios. ¿Tienes permisos de administrador?',
        variant: 'destructive',
      });
      setLoading(false);
      // Opcional: redirigir si no tiene permisos
      // if (error.response?.status === 403) {
      //   router.push('/dashboard'); 
      // }
    }
  }, [toast]); // Add dependencies for fetchUsers here if any

  const fetchMetrics = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/admin/metrics');
      setMetrics(response.data);
    } catch (error: any) {
      console.error('Error fetching metrics:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudieron cargar las métricas.',
        variant: 'destructive',
      });
    }
  }, [toast]);

  const fetchPipelineResults = useCallback(async () => {
    try {
      setPipelineLoading(true);
      const response = await apiClient.get('/api/admin/pipeline/results');
      setPipelineResults(response.data);
      setPipelineRunning(response.data?.status?.is_running ?? false);
    } catch (error: any) {
      console.error('Error fetching pipeline results:', error);
    } finally {
      setPipelineLoading(false);
    }
  }, []);

  const handleRunPipeline = async () => {
    try {
      setPipelineRunning(true);
      await apiClient.post('/api/admin/pipeline/run');
      toast({
        title: 'Pipeline iniciado',
        description: 'Enviando queries reales al LLM. Puede tardar 1-5 minutos. Los resultados aparecerán automáticamente.',
      });
      // Poll every 8 seconds while running
      const poll = setInterval(async () => {
        const res = await apiClient.get('/api/admin/pipeline/results').catch(() => null);
        if (res) {
          setPipelineResults(res.data);
          if (!res.data?.status?.is_running) {
            setPipelineRunning(false);
            clearInterval(poll);
          }
        }
      }, 8000);
      // Safety: stop polling after 12 minutes
      setTimeout(() => { clearInterval(poll); setPipelineRunning(false); }, 720000);
    } catch (error: any) {
      setPipelineRunning(false);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudo iniciar el pipeline.',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchMetrics();
    fetchPipelineResults();
  }, [fetchUsers, fetchMetrics, fetchPipelineResults]);

  const handleSelectUser = (userId: string, isSelected: boolean) => {
    setSelectedUsers((prevSelected) => {
      const newSelected = new Set(prevSelected);
      if (isSelected) {
        newSelected.add(userId);
      } else {
        newSelected.delete(userId);
      }
      return newSelected;
    });
  };

  const handleDeleteSelected = async () => {
    if (selectedUsers.size === 0) {
      toast({
        title: 'Advertencia',
        description: 'Selecciona al menos un usuario para eliminar.',
        variant: 'default', // Cambiado de 'warning' a 'default'
      });
      return;
    }

    if (!confirm(`¿Estás seguro de que quieres eliminar a ${selectedUsers.size} usuario(s)? Esta acción es irreversible.`)) {
      return;
    }

    try {
      await apiClient.post('/api/admin/users/delete', {
        account_ids: Array.from(selectedUsers),
      });
      toast({
        title: 'Éxito',
        description: 'Usuario(s) eliminado(s) correctamente.',
      });
      setSelectedUsers(new Set()); // Limpiar selección
      fetchUsers(); // Volver a cargar la lista de usuarios
    } catch (error: any) {
      console.error('Error deleting users:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudieron eliminar los usuarios.',
        variant: 'destructive',
      });
    }
  };

  const handleCleanup = async () => {
    if (!confirm('¿Estás seguro de que quieres limpiar los archivos temporales con más de 24 horas?')) {
      return;
    }

    try {
      const response = await apiClient.post('/api/admin/cleanup-files');
      toast({
        title: 'Limpieza Completada',
        description: `Se han eliminado ${response.data.files_deleted} archivos.`,
      });
    } catch (error: any) {
      console.error('Error cleaning up files:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'No se pudo realizar la limpieza.',
        variant: 'destructive',
      });
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-full">Cargando usuarios...</div>;
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <Users className="mr-3 h-8 w-8 text-primary" />
            Panel de Administración
          </h1>
          <p className="text-muted-foreground mt-2">
            Gestiona usuarios y configuraciones del sistema
          </p>
        </div>
      </div>

      <Tabs defaultValue="users" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="users">Gestión de Usuarios</TabsTrigger>
          <TabsTrigger value="tools">Herramientas del Sistema</TabsTrigger>
          <TabsTrigger value="metrics">Métricas del Sistema</TabsTrigger>
          <TabsTrigger value="ai-quality" className="flex items-center gap-1.5">
            <FlaskConical className="h-3.5 w-3.5" />
            Calidad IA
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Administración de Usuarios</CardTitle>
              <CardDescription>
                Gestiona las cuentas de usuario del sistema
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center space-x-2">
                  <Button
                    onClick={handleDeleteSelected}
                    disabled={selectedUsers.size === 0}
                    variant="destructive"
                  >
                    Eliminar Seleccionados ({selectedUsers.size})
                  </Button>
                  <Dialog open={isCreateUserDialogOpen} onOpenChange={setIsCreateUserDialogOpen}>
                    <DialogTrigger asChild>
                      <Button>
                        <Plus className="mr-2 h-4 w-4" />
                        Crear Usuario
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px]">
                      <DialogHeader>
                        <DialogTitle>Crear Nuevo Usuario</DialogTitle>
                        <DialogDescription>
                          Ingresa los detalles para crear una nueva cuenta de usuario.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                          <Label htmlFor="name" className="text-right">
                            Nombre
                          </Label>
                          <Input
                            id="name"
                            value={newUserData.name}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, name: e.target.value }))}
                            className="col-span-3"
                          />
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                          <Label htmlFor="email" className="text-right">
                            Email
                          </Label>
                          <Input
                            id="email"
                            type="email"
                            value={newUserData.email}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, email: e.target.value }))}
                            className="col-span-3"
                          />
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                          <Label htmlFor="username" className="text-right">
                            Username
                          </Label>
                          <Input
                            id="username"
                            value={newUserData.username}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, username: e.target.value }))}
                            className="col-span-3"
                          />
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                          <Label htmlFor="password" className="text-right">
                            Contraseña
                          </Label>
                          <Input
                            id="password"
                            type="password"
                            value={newUserData.password}
                            onChange={(e) => setNewUserData(prev => ({ ...prev, password: e.target.value }))}
                            className="col-span-3"
                          />
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                          <Label htmlFor="is_admin" className="text-right">
                            Admin
                          </Label>
                          <Checkbox
                            id="is_admin"
                            checked={newUserData.is_admin}
                            onCheckedChange={(checked: boolean) => setNewUserData(prev => ({ ...prev, is_admin: checked }))}
                            className="col-span-3"
                          />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setIsCreateUserDialogOpen(false)}>
                          Cancelar
                        </Button>
                        <Button onClick={handleCreateUser} disabled={!newUserData.name || !newUserData.email || !newUserData.username || !newUserData.password}>
                          Crear Usuario
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
                <Button onClick={fetchUsers}>Recargar Usuarios</Button>
              </div>

              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        <Checkbox
                          checked={selectedUsers.size === users.length && users.length > 0}
                          onCheckedChange={(checked: boolean) => { // Tipificado como boolean
                            if (checked) {
                              setSelectedUsers(new Set(users.map(user => user.id)));
                            } else {
                              setSelectedUsers(new Set());
                            }
                          }}
                        />
                      </TableHead>
                      <TableHead>ID de Cuenta</TableHead>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Username</TableHead>
                      <TableHead>Telegram ID</TableHead>
                      <TableHead>Admin</TableHead>
                      <TableHead>Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedUsers.has(user.id)}
                            onCheckedChange={(checked: boolean) => handleSelectUser(user.id, checked)} // Tipificado como boolean y simplificado
                            disabled={user.is_admin} // No permitir eliminar cuentas admin desde aquí
                          />
                        </TableCell>
                        <TableCell className="font-mono text-xs">{user.id}</TableCell>
                        <TableCell>{user.name}</TableCell>
                        <TableCell>{user.email || '-'}</TableCell>
                        <TableCell>{user.username || '-'}</TableCell>
                        <TableCell>{user.telegram_id || '-'}</TableCell>
                        <TableCell>{user.is_admin ? 'Sí' : 'No'}</TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEditUser(user)}
                            className="mr-2"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {users.length === 0 && !loading && (
                <p className="text-center text-muted-foreground mt-4">No se encontraron usuarios.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Edit User Dialog */}
        <Dialog open={isEditUserDialogOpen} onOpenChange={setIsEditUserDialogOpen}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Editar Usuario</DialogTitle>
              <DialogDescription>
                {`Modifica los detalles del usuario "${editingUser?.name}".`}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="edit_name" className="text-right">
                  Nombre
                </Label>
                <Input
                  id="edit_name"
                  value={editingUserData.name}
                  onChange={(e) => setEditingUserData(prev => ({ ...prev, name: e.target.value }))}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="edit_email" className="text-right">
                  Email
                </Label>
                <Input
                  id="edit_email"
                  type="email"
                  value={editingUserData.email}
                  onChange={(e) => setEditingUserData(prev => ({ ...prev, email: e.target.value }))}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="edit_username" className="text-right">
                  Username
                </Label>
                <Input
                  id="edit_username"
                  value={editingUserData.username}
                  onChange={(e) => setEditingUserData(prev => ({ ...prev, username: e.target.value }))}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="edit_is_admin" className="text-right">
                  Admin
                </Label>
                <Checkbox
                  id="edit_is_admin"
                  checked={editingUserData.is_admin}
                  onCheckedChange={(checked: boolean) => setEditingUserData(prev => ({ ...prev, is_admin: checked }))}
                  className="col-span-3"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsEditUserDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={handleUpdateUser} disabled={!editingUserData.name || !editingUserData.email || !editingUserData.username}>
                Guardar Cambios
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <TabsContent value="tools" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <Link href="/admin/scheduled-tools">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center">
                      <Clock className="mr-2 h-5 w-5 text-primary" />
                      Herramientas Programadas
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </CardTitle>
                  <CardDescription>
                    Administra las herramientas automáticas del sistema como análisis diarios, insights y limpieza
                  </CardDescription>
                </CardHeader>
              </Link>
            </Card>

            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <Link href="/admin/knowledge-graph">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center">
                      <Network className="mr-2 h-5 w-5 text-primary" />
                      Administración del Grafo
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </CardTitle>
                  <CardDescription>
                    Revisa calidad, detecta duplicados y administra la salud del grafo de conocimiento global.
                  </CardDescription>
                </CardHeader>
              </Link>
            </Card>

            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <Link href="/admin/settings">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center">
                      <Settings className="mr-2 h-5 w-5 text-primary" />
                      Configuración del Sistema
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </CardTitle>
                  <CardDescription>
                    Configura el motor de IA global y administra credenciales del sistema
                  </CardDescription>
                </CardHeader>
              </Link>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle>Métricas del Sistema</CardTitle>
                <CardDescription>
                  Información clave sobre el estado y uso del sistema.
                </CardDescription>
              </div>
              <Link href="/admin/analytics">
                <Button className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-bold gap-2 text-xs">
                  <BarChart2 size={14} />
                  Ver Analíticas de Tráfico y Uso
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {metrics ? (
                <div className="grid gap-4 md:grid-cols-3">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Total de Usuarios</CardTitle>
                      <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{metrics.total_users}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Herramientas Programadas</CardTitle>
                      <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{metrics.total_scheduled_tools}</div>
                      <p className="text-xs text-muted-foreground">
                        {metrics.active_scheduled_tools} activas
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Limpieza de Archivos</CardTitle>
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="text-xs text-muted-foreground">
                        Elimina archivos generados (PDF, CSV, etc.) con más de 24 horas.
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleCleanup}
                        className="w-full"
                      >
                        Ejecutar Limpieza Manual
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <p className="text-center text-muted-foreground mt-4">Cargando métricas...</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── AI Quality Metrics Tab ─── */}
        <TabsContent value="ai-quality" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <FlaskConical className="h-5 w-5 text-purple-500" />
                  Pipeline de Calidad IA
                </CardTitle>
                <CardDescription>
                  Métricas de alucinaciones, recall y éxito de herramientas en tiempo real.
                  {pipelineResults?.latest?.timestamp && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      Última ejecución: {pipelineResults.latest.timestamp}
                    </span>
                  )}
                </CardDescription>
              </div>
              <Button
                onClick={handleRunPipeline}
                disabled={pipelineRunning}
                className="bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white font-bold gap-2 text-xs"
              >
                {pipelineRunning ? (
                  <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Ejecutando...</>
                ) : (
                  <><FlaskConical className="h-3.5 w-3.5" /> Ejecutar Pipeline</>
                )}
              </Button>
            </CardHeader>
            <CardContent>
              {pipelineLoading ? (
                <p className="text-center text-muted-foreground py-8">Cargando resultados del pipeline...</p>
              ) : pipelineResults?.latest ? (
                <div className="space-y-6">
                  {/* KPI Cards */}
                  <div className="grid gap-4 md:grid-cols-3">
                    {pipelineResults.latest.metrics.map((m) => {
                      const isOk = m.status === 'OK';
                      const metricLabels: Record<string, string> = {
                        hallucination_rate: 'Tasa de Alucinaciones',
                        recall_at_5: 'Recall@5',
                        tool_success_rate: 'Éxito de Herramientas',
                      };
                      const metricIcons: Record<string, React.ReactNode> = {
                        hallucination_rate: <AlertTriangle className="h-4 w-4" />,
                        recall_at_5: <BarChart2 className="h-4 w-4" />,
                        tool_success_rate: <Zap className="h-4 w-4" />,
                      };
                      return (
                        <Card
                          key={m.metric}
                          className={`border-l-4 ${
                            isOk ? 'border-l-green-500' : 'border-l-amber-500'
                          }`}
                        >
                          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">
                              {metricLabels[m.metric] ?? m.metric}
                            </CardTitle>
                            <span className={isOk ? 'text-green-500' : 'text-amber-500'}>
                              {metricIcons[m.metric]}
                            </span>
                          </CardHeader>
                          <CardContent>
                            <div className="text-2xl font-bold">
                              {m.value}{m.unit ?? ''}
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">
                              Meta: {m.reference}{m.unit ?? ''} &mdash;{' '}
                              <span className={isOk ? 'text-green-600 font-semibold' : 'text-amber-600 font-semibold'}>
                                {isOk ? '✓ OK' : '⚠ Atención'}
                              </span>
                            </p>
                            {/* Progress bar */}
                            <div className="mt-3 h-1.5 w-full bg-muted rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  isOk ? 'bg-green-500' : 'bg-amber-500'
                                }`}
                                style={{
                                  width: `${
                                    m.metric === 'hallucination_rate'
                                      ? Math.max(0, 100 - (m.value / 20) * 100)
                                      : m.metric === 'recall_at_5'
                                      ? m.value * 100
                                      : m.value
                                  }%`,
                                }}
                              />
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>

                  {/* Summary Banner */}
                  <div
                    className={`rounded-lg p-4 flex items-center gap-3 ${
                      (pipelineResults.latest.summary?.warnings ?? 0) === 0
                        ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                        : 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800'
                    }`}
                  >
                    {(pipelineResults.latest.summary?.warnings ?? 0) === 0 ? (
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
                    )}
                    <div>
                      <p className="text-sm font-semibold">
                        {(pipelineResults.latest.summary?.warnings ?? 0) === 0
                          ? 'Todas las métricas están dentro del objetivo'
                          : `${pipelineResults.latest.summary.warnings} métrica(s) requieren atención`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {pipelineResults.latest.summary?.total_metrics} métricas evaluadas
                      </p>
                    </div>
                  </div>

                  {/* History Table */}
                  {pipelineResults.history.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wide">
                        Historial de Ejecuciones
                      </h3>
                      <div className="rounded-md border overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Timestamp</TableHead>
                              <TableHead className="text-center">Alucinaciones</TableHead>
                              <TableHead className="text-center">Recall@5</TableHead>
                              <TableHead className="text-center">Éxito Tools</TableHead>
                              <TableHead className="text-center">Estado</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {pipelineResults.history.map((entry) => {
                              const h = entry.metrics?.find((m) => m.metric === 'hallucination_rate');
                              const r = entry.metrics?.find((m) => m.metric === 'recall_at_5');
                              const t = entry.metrics?.find((m) => m.metric === 'tool_success_rate');
                              return (
                                <TableRow key={entry.filename}>
                                  <TableCell className="text-xs font-mono">{entry.timestamp}</TableCell>
                                  <TableCell className="text-center text-xs">
                                    <span className={h?.status === 'OK' ? 'text-green-600' : 'text-amber-600'}>
                                      {h?.value ?? '—'}{h?.unit ?? ''}
                                    </span>
                                  </TableCell>
                                  <TableCell className="text-center text-xs">
                                    <span className={r?.status === 'OK' ? 'text-green-600' : 'text-amber-600'}>
                                      {r?.value ?? '—'}
                                    </span>
                                  </TableCell>
                                  <TableCell className="text-center text-xs">
                                    <span className={t?.status === 'OK' ? 'text-green-600' : 'text-amber-600'}>
                                      {t?.value ?? '—'}{t?.unit ?? ''}
                                    </span>
                                  </TableCell>
                                  <TableCell className="text-center">
                                    {(entry.summary?.warnings ?? 0) === 0 ? (
                                      <CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
                                    ) : (
                                      <AlertTriangle className="h-4 w-4 text-amber-500 mx-auto" />
                                    )}
                                  </TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <FlaskConical className="h-12 w-12 mx-auto mb-4 opacity-30" />
                  <p className="font-medium">No hay resultados disponibles</p>
                  <p className="text-sm mt-1">Ejecuta el pipeline para obtener métricas de calidad IA.</p>
                </div>
              )}

              {pipelineResults?.status?.error && (
                <div className="mt-4 rounded-lg p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
                  <strong>Error:</strong> {pipelineResults.status.error}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
