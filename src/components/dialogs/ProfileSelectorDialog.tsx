'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { useEffect, useState } from 'react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

// Interfaz para el perfil de contacto (simplificada para el selector)
interface ContactProfile {
  id: string;
  name: string;
  email?: string;
  phone?: string;
}

interface ProfileSelectorDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectProfiles: (selectedProfiles: ContactProfile[]) => void;
  multiselect?: boolean;
  preSelectedProfileIds?: string[];
}

export function ProfileSelectorDialog({
  isOpen,
  onOpenChange,
  onSelectProfiles,
  multiselect = false,
  preSelectedProfileIds = [],
}: ProfileSelectorDialogProps) {
  const [availableProfiles, setAvailableProfiles] = useState<ContactProfile[]>([]);
  const [selectedProfiles, setSelectedProfiles] = useState<ContactProfile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchProfiles();
    } else {
      // Limpiar estados al cerrar el diálogo
      setAvailableProfiles([]);
      setSelectedProfiles([]);
      setSearchTerm('');
    }
  }, [isOpen]);

  useEffect(() => {
    if (availableProfiles.length > 0 && preSelectedProfileIds.length > 0) {
      const preSelected = availableProfiles.filter(profile =>
        preSelectedProfileIds.includes(profile.id)
      );
      setSelectedProfiles(preSelected);
    }
  }, [availableProfiles, preSelectedProfileIds]);

  const fetchProfiles = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/contact-profiles');
      setAvailableProfiles(response.data.map((p: any) => ({
        id: p.id,
        name: p.name,
        email: p.email,
        phone: p.phone,
      })));
    } catch (error) {
      toast.error('Error al cargar los perfiles de contacto.');
      console.error('Error fetching profiles:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleProfileToggle = (profile: ContactProfile) => {
    setSelectedProfiles(prevSelected => {
      if (multiselect) {
        if (prevSelected.some(p => p.id === profile.id)) {
          return prevSelected.filter(p => p.id !== profile.id);
        } else {
          return [...prevSelected, profile];
        }
      } else {
        // Si no es multiselección, solo permite uno
        return prevSelected.some(p => p.id === profile.id) ? [] : [profile];
      }
    });
  };

  const handleConfirmSelection = () => {
    onSelectProfiles(selectedProfiles);
    onOpenChange(false);
  };

  const filteredProfiles = availableProfiles.filter(profile =>
    profile.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    profile.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    profile.phone?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{multiselect ? 'Seleccionar Perfiles' : 'Seleccionar Perfil'}</DialogTitle>
          <DialogDescription>
            Busca y selecciona {multiselect ? 'los perfiles' : 'un perfil'} de contacto.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <Input
            placeholder="Buscar perfiles..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full"
          />

          <ScrollArea className="h-[300px] w-full rounded-md border p-4">
            {isLoading ? (
              <p className="text-center text-muted-foreground">Cargando perfiles...</p>
            ) : filteredProfiles.length === 0 ? (
              <p className="text-center text-muted-foreground">No se encontraron perfiles.</p>
            ) : (
              <div className="space-y-2">
                {filteredProfiles.map((profile) => (
                  <div key={profile.id} className="flex items-center justify-between">
                    <label htmlFor={`profile-${profile.id}`} className="flex items-center space-x-2 cursor-pointer">
                      <Checkbox
                        id={`profile-${profile.id}`}
                        checked={selectedProfiles.some(p => p.id === profile.id)}
                        onCheckedChange={() => handleProfileToggle(profile)}
                      />
                      <span>{profile.name}</span>
                      {profile.email && <span className="text-sm text-muted-foreground">({profile.email})</span>}
                    </label>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleConfirmSelection} disabled={selectedProfiles.length === 0}>
            {multiselect ? `Seleccionar (${selectedProfiles.length})` : 'Seleccionar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
