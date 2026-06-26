"use client";

import React, { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Brain, User, Sparkles, Globe, Info, Wrench, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface AIProfileFormProps {
  // We could pass some props here if needed
}

export const AIProfileForm: React.FC<AIProfileFormProps> = () => {
  const [profileLoading, setProfileLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileData, setProfileData] = useState({
    nombre: '',
    gustos: '',
    intereses: '',
    otros_datos: '',
    system_prompt: ''
  });

  const fetchProfile = async () => {
    setProfileLoading(true);
    try {
      const response = await apiClient.get('/api/users/me/profile');
      setProfileData({
        nombre: response.data.nombre || '',
        gustos: response.data.gustos || '',
        intereses: response.data.intereses || '',
        otros_datos: response.data.otros_datos || '',
        system_prompt: response.data.system_prompt || ''
      });
    } catch (error) {
      console.error('Error fetching profile:', error);
      toast.error('Error al cargar el perfil de IA.');
    } finally {
      setProfileLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await apiClient.put('/api/users/me/profile', profileData);
      toast.success('Perfil de IA guardado exitosamente.');
      fetchProfile();
    } catch (error) {
      console.error('Error saving profile:', error);
      toast.error('Error al guardar el perfil de IA.');
    } finally {
      setSavingProfile(false);
    }
  };

  return (
    <Card className="border-primary/20 bg-background/50 backdrop-blur-md shadow-xl transition-all duration-300">
      <CardHeader className="border-b border-primary/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Brain className="h-6 w-6 animate-pulse" />
          </div>
          <div className="flex-1">
            <CardTitle className="text-xl font-bold flex items-center gap-2">
              Perfil de IA (Memoria Estructurada)
              <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20 animate-pulse">
                Dinámico & Autónomo
              </Badge>
            </CardTitle>
            <CardDescription className="mt-1">
              Esta es la memoria estructurada y el prompt de sistema personalizado que tu agente de IA (Kognito/Fito) mantiene sobre ti de forma autónoma a lo largo de las conversaciones. Puedes modificarla manualmente aquí.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        {profileLoading ? (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <RefreshCw className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground animate-pulse">Cargando perfil y recuerdos de IA...</p>
          </div>
        ) : (
          <form onSubmit={handleProfileSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="profile-nombre" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                    <User className="h-4 w-4 text-primary" />
                    Cómo te llamas (Nombre del Perfil)
                  </Label>
                  <Input
                    id="profile-nombre"
                    placeholder="Tu nombre o apodo para el Agente"
                    value={profileData.nombre}
                    onChange={(e) => setProfileData({ ...profileData, nombre: e.target.value })}
                    className="bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                  />
                  <p className="text-[11px] text-muted-foreground">El nombre por el cual el agente se dirigirá a ti.</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profile-gustos" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                    <Sparkles className="h-4 w-4 text-primary" />
                    Gustos y Preferencias
                  </Label>
                  <Textarea
                    id="profile-gustos"
                    placeholder="Tus gustos culinarios, temas favoritos, pasatiempos, estilo de comunicación preferido..."
                    value={profileData.gustos}
                    onChange={(e) => setProfileData({ ...profileData, gustos: e.target.value })}
                    className="min-h-[120px] bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                  />
                  <p className="text-[11px] text-muted-foreground">Cosas que te agradan o prefieres en tu día a día.</p>
                </div>
              </div>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="profile-intereses" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                    <Globe className="h-4 w-4 text-primary" />
                    Intereses y Foco de Estudio/Trabajo
                  </Label>
                  <Textarea
                    id="profile-intereses"
                    placeholder="Tecnologías que estás aprendiendo, proyectos en los que trabajas, temas que investigas..."
                    value={profileData.intereses}
                    onChange={(e) => setProfileData({ ...profileData, intereses: e.target.value })}
                    className="min-h-[120px] bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                  />
                  <p className="text-[11px] text-muted-foreground">Temas en los que estás enfocado actualmente o deseas aprender.</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profile-otros" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                    <Info className="h-4 w-4 text-primary" />
                    Otros Datos Persistentes
                  </Label>
                  <Textarea
                    id="profile-otros"
                    placeholder="Cualquier otra información relevante, contexto familiar, metas a largo plazo, etc."
                    value={profileData.otros_datos}
                    onChange={(e) => setProfileData({ ...profileData, otros_datos: e.target.value })}
                    className="min-h-[120px] bg-background/80 border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
                  />
                  <p className="text-[11px] text-muted-foreground">Notas adicionales que el Agente debería recordar permanentemente.</p>
                </div>
              </div>
            </div>
            <div className="border-t border-primary/10 pt-6 space-y-2">
              <Label htmlFor="profile-prompt" className="text-sm font-semibold flex items-center gap-1.5 text-foreground/90">
                <Wrench className="h-4 w-4 text-primary" />
                Prompt de Sistema Personalizado (Instrucciones Directas)
              </Label>
              <Textarea
                id="profile-prompt"
                placeholder="Escribe instrucciones de comportamiento explícitas para tu IA. Ej: 'Háblame de forma concisa', 'Prioriza siempre dar ejemplos de código', 'Sé sumamente empático'..."
                value={profileData.system_prompt}
                onChange={(e) => setProfileData({ ...profileData, system_prompt: e.target.value })}
                className="min-h-[120px] bg-background/80 font-mono text-xs border-primary/10 focus:border-primary focus:ring-1 focus:ring-primary transition-all duration-300"
              />
              <p className="text-[11px] text-muted-foreground">
                Estas directrices se inyectan en el prompt del sistema del agente en cada interacción y guían directamente su personalidad y comportamiento.
              </p>
            </div>
            <div className="flex justify-end gap-3 border-t border-primary/10 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={fetchProfile}
                disabled={savingProfile || profileLoading}
                className="border-primary/20 text-primary hover:bg-primary/5 transition-all duration-300"
              >
                Descartar Cambios
              </Button>
              <Button
                type="submit"
                disabled={savingProfile || profileLoading}
                className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-md shadow-primary/20 transition-all duration-300"
              >
                {savingProfile ? 'Guardando...' : 'Guardar Perfil de IA'}
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
};
