'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { useEffect, useState, useCallback } from 'react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContactProfile } from '../profiles/Profiles';

interface LinkedProfileDisplay extends ContactProfile {
  linked: boolean;
}

interface ManageLinkedProfilesDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  item: { id: string; name?: string; title?: string; } | null;
  itemType: 'note' | 'document' | 'form' | 'form-response' | 'album';
  onLinkedProfilesUpdated: () => void;
  onLink: (profileId: string, itemId: string) => Promise<void>;
  onUnlink: (profileId: string, itemId: string) => Promise<void>;
}

export function ManageLinkedProfilesDialog({
  isOpen, onOpenChange, item, itemType, onLinkedProfilesUpdated, onLink, onUnlink
}: ManageLinkedProfilesDialogProps) {
  const [availableProfiles, setAvailableProfiles] = useState<LinkedProfileDisplay[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const getEndpointPrefix = (type: string) => {
    if (type === 'note') return 'notes';
    if (type === 'document') return 'documents';
    if (type === 'form') return 'forms';
    if (type === 'form-response') return 'form-responses';
    return 'galleries/albums';
  };

  const fetchAvailableProfiles = useCallback(async () => {
    setIsLoading(true);
    try {
      const allProfilesResponse = await apiClient.get('/api/contact-profiles');
      const allProfiles: ContactProfile[] = allProfilesResponse.data;

      const linkedProfilesResponse = await apiClient.get(`/api/${getEndpointPrefix(itemType)}/${item?.id}/linked-profiles`);
      const linkedProfilesIds: string[] = linkedProfilesResponse.data.map((p: any) => p.id.toString());

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
  }, [item?.id, itemType]);

  useEffect(() => {
    if (isOpen && item?.id) {
      fetchAvailableProfiles();
    } else if (!isOpen) {
      setAvailableProfiles([]);
      setSearchTerm('');
    }
  }, [isOpen, item?.id, fetchAvailableProfiles]);

  const handleToggleLink = async (profileToToggle: LinkedProfileDisplay) => {
    if (!item?.id) return;

    try {
      if (profileToToggle.linked) {
        await onUnlink(profileToToggle.id, item.id);
      } else {
        await onLink(profileToToggle.id, item.id);
      }
      toast.success(`${profileToToggle.name} ${profileToToggle.linked ? 'desvinculado' : 'vinculado'} correctamente.`);
      setAvailableProfiles(prevProfiles =>
        prevProfiles.map(p =>
          p.id === profileToToggle.id ? { ...p, linked: !p.linked } : p
        )
      );
      onLinkedProfilesUpdated();
    } catch (error) {
      toast.error(`Error al ${profileToToggle.linked ? 'desvincular' : 'vincular'} ${profileToToggle.name}.`);
      console.error(`Error toggling link for profile ${profileToToggle.id}:`, error);
    }
  };

  const filterProfiles = (profiles: LinkedProfileDisplay[]) => {
    return profiles.filter(profile =>
      (profile.name || '').toLowerCase().includes(searchTerm.toLowerCase())
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

  if (!item) return null;

  const itemDisplayName = item.name || item.title || 'elemento sin nombre';

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Vincular Perfiles a {itemType === 'note' ? 'Nota' : itemType === 'form' ? 'Formulario' : itemType === 'form-response' ? 'Respuesta de Formulario' : 'Álbum'}: {itemDisplayName}</DialogTitle>
          <DialogDescription>
            Selecciona los perfiles que deseas vincular o desvincular de este {itemType === 'note' ? 'nota' : itemType === 'form' ? 'formulario' : itemType === 'form-response' ? 'respuesta de formulario' : 'álbum'}.
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