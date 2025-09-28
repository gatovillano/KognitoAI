"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { PlusCircle, Save, ArrowLeft, Loader2, GripVertical, Trash2 } from 'lucide-react';
import FormField from '@/components/forms/FormField';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid';
import { Form, FormFieldData, FormSectionData, FormElement } from '@/types/form';

function isFormField(element: FormElement): element is FormFieldData {
  return (element as FormFieldData).type !== undefined;
}

function isFormSection(element: FormElement): element is FormSectionData {
  return (element as FormSectionData).elements !== undefined;
}

function SortableFormElement({ element, onUpdate, onDelete }: { element: FormElement; onUpdate: (element: FormElement) => void; onDelete: () => void; }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: element.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

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
  const [title, setTitle] = useState('Formulario sin título');
  const [elements, setElements] = useState<FormElement[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor)
  );

  const addField = () => {
    const newField: FormFieldData = {
      id: uuidv4(),
      label: 'Nueva Pregunta',
      description: '',
      type: 'text',
      is_required: false,
    };
    setElements((prev) => [...prev, newField]);
  };

  const addSection = () => {
    const newSection: FormSectionData = {
      id: uuidv4(),
      title: 'Nueva Sección',
      description: '',
      elements: [],
    };
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
      const newForm: Partial<Form> = {
        id: uuidv4(),
        title,
        user_id: 'c3a2f8f0-4e9e-4b8a-b1e2-0c1d2e3f4a5b', // TODO: Replace with actual user ID
        elements,
      };

      const response = await apiClient.post('/api/forms', newForm);
      
      toast.success('¡Formulario guardado con éxito!');
      router.push(`/forms/${response.data.id}/edit`);
    } catch (error) {
      console.error('Failed to save form:', error);
      toast.error('Error al guardar el formulario. Por favor, inténtalo de nuevo.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl p-4 md:p-6">
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" onClick={() => router.back()} disabled={isSaving}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">Crear Nuevo Formulario</h1>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          {isSaving ? 'Guardando...' : 'Guardar Formulario'}
        </Button>
      </header>
      
      <main className="space-y-6">
        <Input
          id="form-title"
          placeholder="Título del Formulario"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="text-3xl font-bold border-none shadow-none p-0 h-auto focus-visible:ring-0"
        />

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={elements} strategy={verticalListSortingStrategy}>
            <div className="space-y-4">
              {elements.map((element) => (
                <SortableFormElement
                  key={element.id}
                  element={element}
                  onUpdate={(updated) => updateElement(element.id, updated)}
                  onDelete={() => deleteElement(element.id)}
                />
              ))}
              {elements.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  <p>Aún no hay campos en tu formulario.</p>
                  <p>¡Añade una pregunta o una sección para empezar!</p>
                </div>
              )}
            </div>
          </SortableContext>
        </DndContext>

        <div className="flex justify-start gap-2 pt-4">
          <Button onClick={addField} variant="outline">
            <PlusCircle className="mr-2 h-4 w-4" />
            Añadir Pregunta
          </Button>
          <Button onClick={addSection} variant="outline">
            <PlusCircle className="mr-2 h-4 w-4" />
            Añadir Sección
          </Button>
        </div>
      </main>
    </div>
  );
}

function FormSection({ section, onUpdate, onDelete, dragHandleProps }: { section: FormSectionData; onUpdate: (section: FormSectionData) => void; onDelete: () => void; dragHandleProps?: any; }) {
  const addFieldToSection = () => {
    const newField: FormFieldData = {
      id: uuidv4(),
      label: 'Nueva Pregunta',
      description: '',
      type: 'text',
      is_required: false,
    };
    onUpdate({ ...section, elements: [...section.elements, newField] });
  };

  const updateSectionElement = (id: string, updatedElement: FormElement) => {
    onUpdate({
      ...section,
      elements: section.elements.map(element => (element.id === id ? updatedElement : element))
    });
  };

  const deleteSectionElement = (id: string) => {
    onUpdate({
      ...section,
      elements: section.elements.filter(element => element.id !== id)
    });
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
    <Card className="bg-muted/40">
      <CardHeader className="flex flex-row items-center justify-between p-4">
        <div className="flex items-center gap-2 flex-grow">
          <span {...dragHandleProps} className="cursor-grab text-muted-foreground">
            <GripVertical className="h-5 w-5" />
          </span>
          <Input
            value={section.title}
            onChange={(e) => onUpdate({ ...section, title: e.target.value })}
            className="text-lg font-semibold border-none bg-transparent focus-visible:ring-0 p-0 h-auto"
            placeholder="Título de la Sección"
          />
        </div>
        <Button variant="ghost" size="icon" onClick={onDelete}>
          <Trash2 className="h-4 w-4 text-muted-foreground" />
        </Button>
      </CardHeader>
      <CardContent className="p-4 pt-0 space-y-4">
        <Input
          value={section.description || ''}
          onChange={(e) => onUpdate({ ...section, description: e.target.value })}
          placeholder="Descripción de la sección (opcional)"
          className="text-sm text-muted-foreground border-none bg-transparent focus-visible:ring-0 p-0 h-auto"
        />
        <DndContext sensors={useSensors(useSensor(PointerSensor))} collisionDetection={closestCenter} onDragEnd={handleSectionDragEnd}>
          <SortableContext items={section.elements} strategy={verticalListSortingStrategy}>
            <div className="space-y-4">
              {section.elements.map((element) => (
                <SortableFormElement
                  key={element.id}
                  element={element}
                  onUpdate={(updated) => updateSectionElement(element.id, updated)}
                  onDelete={() => deleteSectionElement(element.id)}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
        <Button onClick={addFieldToSection} variant="outline" className="w-full border-dashed">
          <PlusCircle className="mr-2 h-4 w-4" />
          Añadir Pregunta a Sección
        </Button>
      </CardContent>
    </Card>
  );
}
