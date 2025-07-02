// En: src/app/(dashboard)/rag/create-collection-dialog.tsx
'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface CreateCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateSuccess: (newTopic: string) => void;
}

export function CreateCollectionDialog({ isOpen, onOpenChange, onCreateSuccess }: CreateCollectionDialogProps) {
  const [topicName, setTopicName] = useState('');
  const [teamId, setTeamId] = useState('');
  const [teams, setTeams] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingTeams, setLoadingTeams] = useState(false);

  useEffect(() => {
    const fetchTeams = async () => {
      setLoadingTeams(true);
      try {
        const response = await apiClient.get('/api/teams');
        setTeams(response.data);
      } catch (error) {
        console.error("Error fetching teams:", error);
        toast.error('Error al cargar los equipos.');
      } finally {
        setLoadingTeams(false);
      }
    };
    if (isOpen) {
      fetchTeams();
    }
  }, [isOpen]);

  const handleCreate = async () => {
    if (!topicName.trim() || topicName.trim().length < 3) {
      toast.error("El nombre de la colección debe tener al menos 3 caracteres.");
      return;
    }
    setIsLoading(true);
    try {
      await apiClient.post('/api/create-collection', { topic: topicName, teamId: teamId || undefined });
      toast.success(`Colección "${topicName}" creada.`);
      onCreateSuccess(topicName);
      onOpenChange(false);
      setTopicName('');
      setTeamId('');
    } catch (error) {
      console.error("Error al crear la colección:", error);
      toast.error('Error al crear la colección.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Crear Nueva Colección</DialogTitle>
          <DialogDescription>
            Dale un nombre a tu nueva base de conocimiento. Podrás añadir documentos después.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="topic-name">Nombre de la Colección</Label>
            <Input 
              id="topic-name" 
              value={topicName}
              onChange={(e) => setTopicName(e.target.value)}
              placeholder="Ej: Proyectos 2025"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="team-select">Compartir con Equipo</Label>
            <select 
              id="team-select"
              className="w-full border rounded-md p-2"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              disabled={loadingTeams}
            >
              <option value="">{loadingTeams ? "Cargando equipos..." : "Seleccionar equipo (opcional)"}</option>
              {teams.map(team => (
                <option key={team.id} value={team.id.toString()}>
                  {team.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleCreate} disabled={isLoading}>
            {isLoading ? 'Creando...' : 'Crear'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
