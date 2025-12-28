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
import apiClient from '@/lib/api'; // Importar apiClient
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Edit, Trash2, Eye, Calendar, User } from 'lucide-react';

interface Memory {
  id: string;
  title: string;
  content: string;
  type: string;
  created_at: string;
  updated_at: string;
  user_id: string;
}

const SettingsPage: React.FC = () => {
  const { settings, loading, error, getSettings, updateSettings } = useUserSettings();
  const [activeTab, setActiveTab] = useState('personal-data');
  const [localSettings, setLocalSettings] = useState(settings);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [showAddMemory, setShowAddMemory] = useState(false);
  const [newMemory, setNewMemory] = useState({
    title: '',
    content: '',
    type: 'general'
  });

  useEffect(() => {
    getSettings();
  }, []);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  useEffect(() => {
    if (activeTab === 'memories' && !memories.length) {
      fetchMemories();
    }
  }, [activeTab]);

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
    try {
      // Necesitaremos un endpoint DELETE para memorias si queremos esta funcionalidad
      // Por ahora, solo loguearemos que no está implementado
      toast.info('La eliminación de memorias aún no está implementada.');
      console.warn(`Intento de eliminar memoria con ID: ${memoryId}. Funcionalidad no implementada.`);
      // const response = await fetch(`/api/memories/${memoryId}`, { // Esto sería el futuro endpoint
      //   method: 'DELETE',
      // });

      // if (response.ok) {
      //   toast.success('Memoria eliminada exitosamente');
      //   fetchMemories();
      // } else {
      //   throw new Error('Error al eliminar memoria');
      // }
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

  const handleSelectChange = (id: string, value: string) => {
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

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Configuración de Usuario</h1>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="personal-data">Datos Personales</TabsTrigger>
          <TabsTrigger value="modules-preferences">Módulos y Preferencias</TabsTrigger>
          <TabsTrigger value="memories">Memorias</TabsTrigger>
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
                      onChange={(e) => setNewMemory({...newMemory, title: e.target.value})}
                    />
                  </div>
                  <div className="grid w-full max-w-sm items-center gap-1.5">
                    <Label htmlFor="memory-type">Tipo</Label>
                    <Select value={newMemory.type} onValueChange={(value) => setNewMemory({...newMemory, type: value})}>
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
                      onChange={(e) => setNewMemory({...newMemory, content: e.target.value})}
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
      </Tabs>
    </div>
  );
};

export default SettingsPage;