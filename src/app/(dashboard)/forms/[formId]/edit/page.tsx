'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardFooter, CardDescription } from '@/components/ui/card';
import { PlusCircle, Save, ArrowLeft, Loader2, Edit, GripVertical, Trash2 } from 'lucide-react';
import FormField from '@/components/forms/FormField';
import { ManageLinkedProfilesDialog } from '@/app/(dashboard)/notes/ManageLinkedProfilesDialog';
// import { Tag } from '@/components/ui/tag'; // Asumiendo que existe un componente Tag
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid';
import { Form, FormFieldData, FormSectionData, FormElement } from '@/types/form';
import { ContactProfile } from '@/app/(dashboard)/profiles/page';
import { Badge } from '@/components/ui/badge';
import { Tag } from '@/components/ui/tag'; // Asumiendo que existe un componente Tag

function isFormField(element: FormElement): element is FormFieldData {
  return (element as FormFieldData).type !== undefined;
}

function SortableFormElement({ element, onUpdate, onDelete }: { element: FormElement; onUpdate: (element: FormElement) => void; onDelete: () => void; }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: element.id });
  const style = { transform: CSS.Transform.toString(transform), transition };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      {isFormField(element) ? (
        <FormField
          field={element}
          onUpdate={onUpdate as (field: FormFieldData) => void}
          onDelete={onDelete}
          dragHandleProps={listeners}
        />
      ) : (
        <FormSection
          section={element as FormSectionData}
          onUpdate={onUpdate as (section: FormSectionData) => void}
          onDelete={onDelete}
          dragHandleProps={listeners}
        />
      )}
    </div>
  );
}

export default function FormEditorPage() {
  const router = useRouter();
  const params = useParams();
  const formId = params?.formId as string;

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [elements, setElements] = useState<FormElement[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showManageProfilesDialog, setShowManageProfilesDialog] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<ContactProfile[]>([]);

  const fetchLinkedProfiles = useCallback(async () => {
    if (!formId) return;
    try {
      const response = await apiClient.get(`/api/forms/${formId}/linked-profiles`);
      setLinkedProfiles(response.data);
    } catch (error) {
      console.error('Error fetching linked profiles:', error);
      toast.error('Error al cargar los perfiles vinculados.');
    }
  }, [formId]);

  useEffect(() => {
    fetchLinkedProfiles();
  }, [fetchLinkedProfiles]);

  useEffect(() => {
    const fetchForm = async () => {
      if (!formId) return;
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get(`/api/forms/${formId}`);
        const form = response.data;
        setTitle(form.title || '');
        setDescription(form.description || '');
        setElements(form.elements || []);
      } catch (err) {
        setError('No se pudo cargar el formulario. Es posible que no exista o haya ocurrido un error.');
        toast.error('Error al cargar el formulario.');
      } finally {
        setLoading(false);
      }
    };
    fetchForm();
  }, [formId]);

  const sensors = useSensors(useSensor(PointerSensor));

  const addField = () => {
    const newField: FormFieldData = { id: uuidv4(), label: 'Nueva Pregunta', description: '', type: 'text', is_required: false, options: [] };
    setElements((prev) => [...prev, newField]);
  };

  const addSection = () => {
    const newSection: FormSectionData = { id: uuidv4(), title: 'Nueva Sección', description: '', elements: [] };
    setElements((prev) => [...prev, newSection]);
  };

  const updateElement = (id: string, updatedElement: FormElement) => {
    setElements((prev) => prev.map(element => (element.id === id ? updatedElement : element)));
  };

  const deleteElement = (id: string) => {
    setElements((prev) => prev.filter(element => element.id !== id));
  };

  const handleDragEnd = (event: any) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      setElements((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const handleSave = async () => {
    if (!title.trim()) {
      toast.error('El título del formulario no puede estar vacío.');
      return;
    }
    setIsSaving(true);
    try {
      const updatedForm: Partial<Form> = { id: formId, title, description, elements, user_id: 'c3a2f8f0-4e9e-4b8a-b1e2-0c1d2e3f4a5b' };
      await apiClient.put(`/api/forms/${formId}`, updatedForm);
      toast.success('¡Formulario actualizado con éxito!');
      router.refresh(); // Force a re-fetch of data for the current route
      // router.push(`/forms/${formId}`); // No longer needed with router.refresh()
    } catch (error) {
      console.error('Failed to update form:', error);
      toast.error('Error al actualizar el formulario. Por favor, inténtalo de nuevo.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLinkProfile = useCallback(async (profileId: string, itemId: string) => {
    try {
      await apiClient.post(`/api/forms/${itemId}/link-profile`, { profile_id: profileId });
      toast.success('Perfil vinculado correctamente.');
      fetchLinkedProfiles(); // Refresh linked profiles after linking
    } catch (error) {
      console.error('Error linking profile:', error);
      toast.error('Error al vincular el perfil.');
      throw error; // Re-throw to allow dialog to handle error state
    }
  }, [fetchLinkedProfiles]);

  const handleUnlinkProfile = useCallback(async (profileId: string, itemId: string) => {
    try {
      await apiClient.delete(`/api/forms/${itemId}/unlink-profile`, { data: { profile_id: profileId } });
      toast.success('Perfil desvinculado correctamente.');
      fetchLinkedProfiles(); // Refresh linked profiles after unlinking
    } catch (error) {
      console.error('Error unlinking profile:', error);
      toast.error('Error al desvincular el perfil.');
      throw error; // Re-throw to allow dialog to handle error state
    }
  }, [fetchLinkedProfiles]);


  if (loading) {
    return <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden flex justify-center items-center"><Loader2 className="h-8 w-8 animate-spin" /><span className="ml-4">Cargando editor...</span></div>;
  }

  if (error) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden text-center text-red-500">
        <h2 className="text-xl font-bold mb-4">Error</h2>
        <p>{error}</p>
        <Button onClick={() => router.push('/forms')} className="mt-4">Volver a Formularios</Button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-4xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Edit className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Editor de Formulario</h1>
            <p className="text-muted-foreground">Construye y personaliza tu formulario.</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.back()} disabled={isSaving}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            {isSaving ? 'Guardando...' : 'Guardar Cambios'}
          </Button>
        </div>
      </div>

      <div className="space-y-8">
        <div className="space-y-4 p-6 border rounded-lg bg-card">
            <Input id="form-title" placeholder="Título del Formulario" value={title} onChange={(e) => setTitle(e.target.value)} className="text-3xl font-bold border-none focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto bg-transparent" />
            <Input id="form-description" placeholder="Descripción del formulario (opcional)" value={description} onChange={(e) => setDescription(e.target.value)} className="text-base text-muted-foreground border-none focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto bg-transparent" />
        </div>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={elements} strategy={verticalListSortingStrategy}>
              <div className="space-y-4">
                {elements.map((element) => (
                  <SortableFormElement key={element.id} element={element} onUpdate={(updated) => updateElement(element.id, updated)} onDelete={() => deleteElement(element.id)} />
                ))}
              </div>
            </SortableContext>
        </DndContext>

        <div className="flex justify-center gap-4 p-4 border-2 border-dashed border-border rounded-lg">
          <Button onClick={addField} variant="outline">
            <PlusCircle className="mr-2 h-4 w-4" />
            Añadir Pregunta
          </Button>
          <Button onClick={addSection} variant="outline">
            <PlusCircle className="mr-2 h-4 w-4" />
            Añadir Sección
          </Button>
        </div>

        <div className="space-y-4 p-6 border rounded-lg bg-card">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Perfiles Vinculados</h2>
            <Button variant="outline" onClick={() => setShowManageProfilesDialog(true)}>
              <PlusCircle className="mr-2 h-4 w-4" />
              Vincular Perfiles
            </Button>
          </div>
          {linkedProfiles.length === 0 ? (
            <p className="text-muted-foreground">No hay perfiles vinculados a este formulario.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {linkedProfiles.map(profile => (
                <Badge key={profile.id} variant="secondary" className="text-sm">
                  {profile.name}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>

      <ManageLinkedProfilesDialog
        isOpen={showManageProfilesDialog}
        onOpenChange={setShowManageProfilesDialog}
        item={{ id: formId, name: title }}
        itemType="form"
        onLinkedProfilesUpdated={fetchLinkedProfiles}
        onLink={handleLinkProfile}
        onUnlink={handleUnlinkProfile}
      />
    </div>
  );
}

function FormSection({ section, onUpdate, onDelete, dragHandleProps }: { section: FormSectionData; onUpdate: (section: FormSectionData) => void; onDelete: () => void; dragHandleProps?: any; }) {
  const addFieldToSection = () => {
    const newField: FormFieldData = { id: uuidv4(), label: 'Nueva Pregunta', description: '', type: 'text', is_required: false, options: [] };
    onUpdate({ ...section, elements: [...section.elements, newField] });
  };

  const updateSectionElement = (id: string, updatedElement: FormElement) => {
    onUpdate({ ...section, elements: section.elements.map(element => (element.id === id ? updatedElement : element)) });
  };

  const deleteSectionElement = (id: string) => {
    onUpdate({ ...section, elements: section.elements.filter(element => element.id !== id) });
  };

  const handleSectionDragEnd = (event: any) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldIndex = section.elements.findIndex((item) => item.id === active.id);
      const newIndex = section.elements.findIndex((item) => item.id === over.id);
      onUpdate({ ...section, elements: arrayMove(section.elements, oldIndex, newIndex) });
    }
  };

  return (
    <div className="p-4 rounded-lg border bg-card/50">
        <div className="flex items-center gap-2 mb-4 pb-4 border-b">
            <div {...dragHandleProps} className="cursor-grab text-muted-foreground/50 hover:text-muted-foreground transition-colors">
                <GripVertical className="h-5 w-5" />
            </div>
            <Input value={section.title} onChange={(e) => onUpdate({ ...section, title: e.target.value })} className="text-xl font-bold border-none focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto bg-transparent" placeholder="Título de la Sección" />
            <Button variant="ghost" size="icon" onClick={onDelete} className="text-muted-foreground hover:text-destructive">
                <Trash2 className="h-4 w-4" />
            </Button>
        </div>
        <div className="space-y-4 ml-8">
            <Textarea value={section.description || ''} onChange={(e) => onUpdate({ ...section, description: e.target.value })} placeholder="Descripción de la sección (opcional)" className="text-sm text-muted-foreground border-none focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto bg-transparent resize-none mb-4" rows={2} />
            <DndContext sensors={useSensors(useSensor(PointerSensor))} collisionDetection={closestCenter} onDragEnd={handleSectionDragEnd}>
                <SortableContext items={section.elements} strategy={verticalListSortingStrategy}>
                    <div className="space-y-4">
                    {section.elements.map((element) => (
                        <SortableFormElement key={element.id} element={element} onUpdate={(updated) => updateSectionElement(element.id, updated)} onDelete={() => deleteSectionElement(element.id)} />
                    ))}
                    </div>
                </SortableContext>
            </DndContext>
            <Button onClick={addFieldToSection} variant="outline" className="w-full border-dashed mt-4">
                <PlusCircle className="mr-2 h-4 w-4" />
                Añadir Pregunta a la Sección
            </Button>
        </div>
    </div>
  );
}
