// src/app/(dashboard)/admin/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Users, Settings, Clock, ArrowRight } from 'lucide-react';
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

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const router = useRouter();

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
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
  };

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
    <div className="container mx-auto p-4 space-y-6">
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
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="users">Gestión de Usuarios</TabsTrigger>
          <TabsTrigger value="tools">Herramientas del Sistema</TabsTrigger>
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
                <Button
                  onClick={handleDeleteSelected}
                  disabled={selectedUsers.size === 0}
                  variant="destructive"
                >
                  Eliminar Seleccionados ({selectedUsers.size})
                </Button>
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
      </Tabs>
    </div>
  );
}
