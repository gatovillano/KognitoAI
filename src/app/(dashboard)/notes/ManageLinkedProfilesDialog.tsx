'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { useEffect, useState } from 'react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContactProfile } from '../profiles/page'; // Importar la interfaz ContactProfile
import { Note } from './page'; // Importar la interfaz Note

interface ManageLinkedProfilesDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  note: Note | null;
  onLinkedProfilesUpdated: () => void; // Callback para refrescar las notas o perfiles si es necesario
}

interface LinkedProfileDisplay extends ContactProfile {
  linked: boolean;
}

export function ManageLinkedProfilesDialog({ isOpen, onOpenChange, note, onLinkedProfilesUpdated }: ManageLinkedProfilesDialogProps) {
  const [availableProfiles, setAvailableProfiles] = useState<LinkedProfileDisplay[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen && note?.id) {
      fetchAvailableProfiles();
    } else if (!isOpen) {
      // Limpiar estados al cerrar el diálogo
      setAvailableProfiles([]);
      setSearchTerm('');
    }
  }, [isOpen, note?.id]);

  const fetchAvailableProfiles = async () => {
    setIsLoading(true);
    try {
      // Obtener todos los perfiles
      const allProfilesResponse = await apiClient.get('/api/contact-profiles');
      const allProfiles: ContactProfile[] = allProfilesResponse.data;

      // Obtener los perfiles ya vinculados a esta nota
      // Asumo que hay un endpoint para esto, por ejemplo: /api/notes/{note_id}/linked-profiles
      // Si no existe, se necesitará crear en el backend.
      const linkedProfilesResponse = await apiClient.get(`/api/notes/${note?.id}/linked-profiles`);
      const linkedProfilesIds: number[] = linkedProfilesResponse.data.map((p: any) => p.id);

      const profilesWithLinkStatus: LinkedProfileDisplay[] = allProfiles.map(profile => ({
        ...profile,
        linked: linkedProfilesIds.includes(profile.id),
      }));
      setAvailableProfiles(profilesWithLinkStatus);

    } catch (error) {
      toast.error('Error al cargar perfiles disponibles.');
      console.error('Error fetching available profiles:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleLink = async (profileToToggle: LinkedProfileDisplay) => {
    if (!note?.id) return;

    const endpoint = profileToToggle.linked
      ? `/api/notes/${note.id}/unlink-profile/${profileToToggle.id}`
      : `/api/notes/${note.id}/link-profile/${profileToToggle.id}`;

    try {
      await apiClient.post(endpoint);
      toast.success(`${profileToToggle.name} ${profileToToggle.linked ? 'desvinculado' : 'vinculado'} correctamente.`);
      // Actualizar el estado local para reflejar el cambio inmediatamente
      setAvailableProfiles(prevProfiles =>
        prevProfiles.map(p =>
          p.id === profileToToggle.id ? { ...p, linked: !p.linked } : p
        )
      );
      onLinkedProfilesUpdated(); // Notificar al componente padre para refrescar si es necesario
    } catch (error) {
      toast.error(`Error al ${profileToToggle.linked ? 'desvincular' : 'vincular'} ${profileToToggle.name}.`);
      console.error(`Error toggling link for profile ${profileToToggle.id}:`, error);
    }
  };

  const filterProfiles = (profiles: LinkedProfileDisplay[]) => {
    return profiles.filter(profile =>
      profile.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const renderProfileList = (profiles: LinkedProfileDisplay[]) => (
    <ScrollArea className="h-[300px] w-full rounded-md border p-4">
      {isLoading ? (
        <p className="text-center text-muted-foreground">Cargando...</p>
      ) : filterProfiles(profiles).length === 0 ? (
        <p className="text-center text-muted-foreground">No se encontraron perfiles.</p>
      ) : (
        <div className="space-y-2">
          {filterProfiles(profiles).map((profile) => (
            <div key={profile.id} className="flex items-center justify-between">
              <label htmlFor={`profile-${profile.id}`} className="flex items-center space-x-2 cursor-pointer">
                <Checkbox
                  id={`profile-${profile.id}`}
                  checked={profile.linked}
                  onCheckedChange={() => handleToggleLink(profile)}
                />
                <span>{profile.name}</span>
              </label>
            </div>
          ))}
        </div>
      )}
    </ScrollArea>
  );

  if (!note) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Vincular Perfiles a Nota: {note.title || 'Nota sin título'}</DialogTitle>
          <DialogDescription>
            Selecciona los perfiles que deseas vincular o desvincular de esta nota.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <Input
            placeholder="Buscar perfiles..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full"
          />
          {renderProfileList(availableProfiles)}
        </div>

        <div className="flex justify-end">
          <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
