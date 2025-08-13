'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface Collection {
  topic: string;
  description?: string;
  document_count: number;
}

type Team = {
  id: string;
  name: string;
  created_at: string;
};

interface ShareCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onShareSuccess: () => void;
  collection: Collection | null;
}

export function ShareCollectionDialog({ isOpen, onOpenChange, onShareSuccess, collection }: ShareCollectionDialogProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [isLoadingTeams, setIsLoadingTeams] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchTeams();
      setSelectedTeam(null);
    }
  }, [isOpen]);

  const fetchTeams = async () => {
    setIsLoadingTeams(true);
    try {
      const response = await apiClient.get('/api/teams');
      setTeams(response.data);
    } catch (error) {
      toast.error('Error al cargar los equipos.');
    } finally {
      setIsLoadingTeams(false);
    }
  };

  const handleShare = async () => {
    if (!collection || !selectedTeam) return;

    setIsSharing(true);
    try {
      await apiClient.post(`/api/teams/${selectedTeam}/share/collections`, {
        collection_topic: collection.topic,
      });
      toast.success(`Colección "${collection.topic}" compartida con el equipo.`);
      onShareSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al compartir la colección.');
    } finally {
      setIsSharing(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md w-full p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Compartir Colección</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p>
            Seleccione un equipo para compartir la colección: <strong>{collection?.topic}</strong>
          </p>
          <p className="text-sm text-muted-foreground">
            Se compartirán todos los documentos de esta colección ({collection?.document_count || 0} documentos) con el equipo seleccionado.
          </p>
          {isLoadingTeams ? (
            <div className="flex justify-center items-center p-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : teams.length > 0 ? (
            <Select value={selectedTeam || undefined} onValueChange={setSelectedTeam}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccione un equipo" />
              </SelectTrigger>
              <SelectContent>
                {teams.map((team) => (
                  <SelectItem key={team.id} value={team.id}>
                    {team.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <p className="text-muted-foreground">No se encontraron equipos para compartir.</p>
          )}
        </div>
        <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
            Cancelar
          </Button>
          <Button
            onClick={handleShare}
            disabled={!selectedTeam || isSharing || isLoadingTeams}
            className="w-full sm:w-auto"
          >
            {isSharing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Compartir Colección
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
