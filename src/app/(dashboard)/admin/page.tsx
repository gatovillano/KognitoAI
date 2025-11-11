// src/app/(dashboard)/admin/page.tsx
'use client';

import { useEffect, useState, useCallback } from 'react';
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
import { Users, Settings, Clock, ArrowRight, Plus, Edit } from 'lucide-react';
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

interface AdminMetricsResponse {
  total_users: number;
  total_scheduled_tools: number;
  active_scheduled_tools: number;
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

  useEffect(() => {
    fetchUsers();
    fetchMetrics();
  }, [fetchUsers, fetchMetrics]);

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
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="users">Gestión de Usuarios</TabsTrigger>
          <TabsTrigger value="tools">Herramientas del Sistema</TabsTrigger>
          <TabsTrigger value="metrics">Métricas del Sistema</TabsTrigger>
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
                Modifica los detalles del usuario "{editingUser?.name}".
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

            <Card className="hover:shadow-md transition-shadow cursor-pointer opacity-50">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Settings className="mr-2 h-5 w-5 text-muted-foreground" />
                    Configuración del Sistema
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </CardTitle>
                <CardDescription>
                  Configuraciones generales del sistema (Próximamente)
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Métricas del Sistema</CardTitle>
              <CardDescription>
                Información clave sobre el estado y uso del sistema.
              </CardDescription>
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
                </div>
              ) : (
                <p className="text-center text-muted-foreground mt-4">Cargando métricas...</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
