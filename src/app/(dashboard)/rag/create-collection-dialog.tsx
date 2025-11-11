'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface CreateCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateSuccess: (newTopic: string) => void;
}

export function CreateCollectionDialog({ isOpen, onOpenChange, onCreateSuccess }: CreateCollectionDialogProps) {
  const params = useParams();
  const workspaceId = params.id as string | undefined;

  const [topicName, setTopicName] = useState('');
  const [description, setDescription] = useState('');
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
      await apiClient.post('/api/collections', { 
                topic: topicName,
                description: description,
                workspaceId: workspaceId,      });
      toast.success(`Colección "${topicName}" creada.`);
      onCreateSuccess(topicName);
      onOpenChange(false);
      setTopicName('');
      setDescription('');
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
      <DialogContent className="max-w-md w-full p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Crear Nueva Colección</DialogTitle>
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
            <Label htmlFor="description">Descripción (Opcional)</Label>
            <Textarea 
              id="description" 
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe el propósito de esta colección..."
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="team-select">Compartir con Equipo</Label>
            <select
              id="team-select"
              className="w-full border rounded-md p-2 text-sm"
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
        <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
          <Button onClick={handleCreate} disabled={isLoading} className="w-full sm:w-auto">
            {isLoading ? 'Creando...' : 'Crear'}
          </Button>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
            Cancelar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
