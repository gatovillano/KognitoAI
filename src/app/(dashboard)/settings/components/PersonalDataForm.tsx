"use client";

import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useUserSettings } from '@/contexts/UserSettingsContext';

interface PersonalDataFormProps {
  loading: boolean;
}

export const PersonalDataForm: React.FC<PersonalDataFormProps> = ({ loading }) => {
  const { settings, updateSettings } = useUserSettings();
  const [localSettings, setLocalSettings] = React.useState(settings);

  React.useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { id, value } = e.target;
    setLocalSettings(prev => prev ? { ...prev, [id]: value } : null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
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

  if (!localSettings) return <div>Cargando configuración...</div>;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-semibold mb-3">Datos Personales</h2>
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
  );
};
