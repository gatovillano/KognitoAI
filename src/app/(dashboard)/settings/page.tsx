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

const SettingsPage: React.FC = () => {
  const { settings, loading, error, getSettings, updateSettings } = useUserSettings();
  const [activeTab, setActiveTab] = useState('personal-data');
  const [localSettings, setLocalSettings] = useState(settings);

  useEffect(() => {
    getSettings();
  }, []);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

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
      </Tabs>
    </div>
  );
};

export default SettingsPage;