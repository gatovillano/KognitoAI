'use client';

import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { PlusCircle, XCircle } from 'lucide-react'; // Importar iconos
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContactProfile } from './page';

interface ProfileDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  profile: ContactProfile | null;
  onSaveSuccess: () => void;
}

interface CustomField {
  id: number; // Usar un ID único para React keys
  key: string;
  value: string;
}

export function ProfileDialog({ isOpen, onOpenChange, profile, onSaveSuccess }: ProfileDialogProps) {
  const [name, setName] = useState(profile?.name || '');
  const [email, setEmail] = useState(profile?.email || '');
  const [phone, setPhone] = useState(profile?.phone || '');
  const [tagsInput, setTagsInput] = useState('');
  const [categoryInput, setCategoryInput] = useState('');
  const [customFields, setCustomFields] = useState<CustomField[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (profile) {
      setName(profile.name || '');
      setEmail(profile.email || '');
      setPhone(profile.phone || '');
      setTagsInput(profile.tags ? profile.tags.join(', ') : '');
      setCategoryInput(profile.category || '');
      // Convertir el objeto custom_fields a un array de CustomField
      const initialCustomFields: CustomField[] = profile.custom_fields
        ? Object.entries(profile.custom_fields).map(([key, value], index) => ({
            id: index, // Usar índice como ID inicial, se puede mejorar con un UUID si es necesario
            key: key,
            value: String(value),
          }))
        : [];
      setCustomFields(initialCustomFields);
    } else {
      setName('');
      setEmail('');
      setPhone('');
      setTagsInput('');
      setCategoryInput('');
      setCustomFields([]);
    }
  }, [profile, isOpen]);

  const handleAddCustomField = () => {
    setCustomFields((prevFields) => [
      ...prevFields,
      { id: Date.now(), key: '', value: '' }, // Usar Date.now() como ID simple
    ]);
  };

  const handleRemoveCustomField = (id: number) => {
    setCustomFields((prevFields) => prevFields.filter((field) => field.id !== id));
  };

  const handleCustomFieldChange = (id: number, fieldName: 'key' | 'value', newValue: string) => {
    setCustomFields((prevFields) =>
      prevFields.map((field) =>
        field.id === id ? { ...field, [fieldName]: newValue } : field
      )
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // Convertir el array de customFields a un objeto JSON
    const customFieldsObject = customFields.reduce((acc, field) => {
      if (field.key.trim() !== '') {
        acc[field.key.trim()] = field.value;
      }
      return acc;
    }, {} as Record<string, string>);

    const tagsArray = tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag !== '');

    const profileData = {
      name,
      email,
      phone,
      tags: tagsArray,
      category: categoryInput,
      custom_fields: customFieldsObject,
    };

    try {
      if (profile) {
        // Update existing profile
        await apiClient.post(`/api/update-contact-profile/${profile.id}`, profileData);
        toast.success('Perfil actualizado exitosamente.');
      } else {
        // Create new profile
        await apiClient.post('/api/create-contact-profile', profileData);
        toast.success('Perfil creado exitosamente.');
      }
      onSaveSuccess();
      onOpenChange(false);
    } catch (error: any) {
      toast.error('Error al guardar el perfil.');
      console.error('Detalle del error 422 (response data):', error.response ? error.response.data : 'No response data');
      console.error('Estado del error:', error.response?.status);
      console.error('Error completo (Axios object):', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{profile ? 'Editar Perfil' : 'Crear Nuevo Perfil'}</DialogTitle>
          <DialogDescription>
            {profile ? 'Realiza cambios en el perfil aquí.' : 'Crea un nuevo perfil de contacto.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="name">
                Nombre
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="email">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="phone">
                Teléfono
              </Label>
              <Input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="tags">
                Etiquetas (separadas por coma)
              </Label>
              <Input
                id="tags"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="ej: cliente, vip, potencial"
              />
            </div>
            <div>
              <Label htmlFor="category">
                Categoría
              </Label>
              <Input
                id="category"
                value={categoryInput}
                onChange={(e) => setCategoryInput(e.target.value)}
                placeholder="ej: personal, trabajo, familia"
              />
            </div>

            {/* Campos Personalizados Dinámicos */}
            <div className="col-span-4 space-y-2">
              <Label className="text-left">Campos Personalizados</Label>
              {customFields.map((field) => (
                <div key={field.id} className="grid grid-cols-4 items-center gap-2">
                  <Input
                    placeholder="Clave"
                    value={field.key}
                    onChange={(e) => handleCustomFieldChange(field.id, 'key', e.target.value)}
                    className="col-span-1"
                  />
                  <Input
                    placeholder="Valor"
                    value={field.value}
                    onChange={(e) => handleCustomFieldChange(field.id, 'value', e.target.value)}
                    className="col-span-2"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveCustomField(field.id)}
                    className="col-span-1 justify-self-end"
                  >
                    <XCircle className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))}
              <Button type="button" variant="outline" size="sm" onClick={handleAddCustomField} className="w-full">
                <PlusCircle className="mr-2 h-4 w-4" /> Añadir Campo
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Guardando...' : 'Guardar cambios'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
