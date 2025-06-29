// En: src/app/(dashboard)/rag/share-document-dialog.tsx

'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

import type { Document } from './columns';

type Team = {
  id: string;
  name: string;
  created_at: string;
};

interface ShareDocumentDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onShareSuccess: () => void;
  document: Document | null;
}

export function ShareDocumentDialog({ isOpen, onOpenChange, onShareSuccess, document }: ShareDocumentDialogProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [isLoadingTeams, setIsLoadingTeams] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchTeams();
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
    if (!document || !selectedTeam) return;

    setIsSharing(true);
    try {
      await apiClient.post(`/api/teams/${selectedTeam}/share/documents`, {
        documentIds: [document.file_name],
      });
      toast.success(`Documento compartido con el equipo.`);
      onShareSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al compartir el documento.');
    } finally {
      setIsSharing(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Compartir Documento</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p>Seleccione un equipo para compartir el documento: <strong>{document?.file_name}</strong></p>
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
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button
            onClick={handleShare}
            disabled={!selectedTeam || isSharing || isLoadingTeams}
          >
            {isSharing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Compartir
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
