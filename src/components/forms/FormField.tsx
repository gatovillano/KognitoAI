'use client';

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Trash2, GripVertical, PlusCircle } from "lucide-react";
import { FieldType, FormFieldData } from '@/types/form';

interface FormFieldProps {
  field: FormFieldData;
  onUpdate: (field: FormFieldData) => void;
  onDelete: () => void;
  dragHandleProps?: any;
}

export default function FormField({ field, onUpdate, onDelete, dragHandleProps }: FormFieldProps) {
  const handleUpdate = (key: keyof FormFieldData, value: any) => {
    onUpdate({ ...field, [key]: value });
  };

  return (
    <div className="p-4 rounded-lg border bg-card/50 hover:bg-card/90 transition-colors group">
      <div className="flex items-start gap-4">
        <div {...dragHandleProps} className="cursor-grab py-8 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors">
          <GripVertical className="h-5 w-5" />
        </div>
        
        <div className="flex-grow space-y-3">
          <Input
            placeholder="Escribe tu pregunta aquí"
            value={field.label}
            onChange={(e) => handleUpdate('label', e.target.value)}
            className="text-lg font-semibold border-none focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto bg-transparent"
          />
          <Textarea
            placeholder="Descripción (opcional)"
            value={field.description || ''}
            onChange={(e) => handleUpdate('description', e.target.value)}
            className="text-sm text-muted-foreground border-none focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-auto bg-transparent resize-none"
            rows={2} // Establecer un número inicial de filas
          />

          {['radio', 'select', 'checkbox'].includes(field.type) && (
            <div className="space-y-2 pt-2">
              {field.options?.map((option, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    value={option}
                    onChange={(e) => {
                      const newOptions = [...(field.options || [])];
                      newOptions[index] = e.target.value;
                      handleUpdate('options', newOptions);
                    }}
                    placeholder={`Opción ${index + 1}`}
                    className="h-9"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 shrink-0"
                    onClick={() => {
                      const newOptions = (field.options || []).filter((_, i) => i !== index);
                      handleUpdate('options', newOptions);
                    }}
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                  </Button>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                className="mt-2 border-dashed"
                onClick={() => {
                  handleUpdate('options', [...(field.options || []), `Opción ${ (field.options?.length || 0) + 1}`]);
                }}
              >
                <PlusCircle className="mr-2 h-4 w-4" />
                Añadir Opción
              </Button>
            </div>
          )}
        </div>

        <div className="flex flex-col items-end justify-between h-full gap-4 min-w-[200px]">
          <Select value={field.type} onValueChange={(value: FieldType) => handleUpdate('type', value)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Tipo de campo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="text">Texto corto</SelectItem>
              <SelectItem value="textarea">Párrafo</SelectItem>
              <SelectItem value="checkbox">Casillas</SelectItem>
              <SelectItem value="radio">Opción múltiple</SelectItem>
              <SelectItem value="select">Menú desplegable</SelectItem>
            </SelectContent>
          </Select>
          
          <div className="flex items-center gap-4 self-end">
            <div className="flex items-center space-x-2">
              <Switch id={`required-${field.id}`} checked={field.is_required} onCheckedChange={(checked) => handleUpdate('is_required', checked)} />
              <label htmlFor={`required-${field.id}`} className="text-sm font-medium text-muted-foreground">Obligatorio</label>
            </div>
            <Button variant="ghost" size="icon" onClick={onDelete} className="text-muted-foreground hover:text-destructive">
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
