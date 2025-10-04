'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { FormResponse, FormFieldData } from '@/types/form';
import { useEffect, useState } from 'react';
import apiClient from '@/lib/api';
import { Loader2 } from 'lucide-react';

interface FormResponseDialogProps {
  response: FormResponse | null;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

export function FormResponseDialog({ response, isOpen, onOpenChange }: FormResponseDialogProps) {
  const [formFields, setFormFields] = useState<FormFieldData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchFormFields = async () => {
      if (response?.form_id) {
        setLoading(true);
        try {
          const formRes = await apiClient.get(`/api/forms/${response.form_id}`);
          // La API devuelve un objeto de formulario que contiene 'elements'.
          // Necesitamos aplanar esta estructura para obtener una lista de campos.
          const fields: FormFieldData[] = [];
          const extractFields = (elements: any[]) => {
            for (const element of elements) {
              if (element.type) { // Es un FormField
                fields.push(element);
              } else if (element.elements) { // Es un FormSection
                extractFields(element.elements);
              }
            }
          };
          extractFields(formRes.data.elements || []);
          setFormFields(fields);
        } catch (error) {
          console.error("Failed to fetch form fields for response details", error);
        } finally {
          setLoading(false);
        }
      }
    };

    if (isOpen) {
      fetchFormFields();
    }
  }, [response, isOpen]);

  const getFieldLabel = (field_id: string) => {
    const field = formFields.find(f => f.id === field_id);
    return field ? field.label : 'Pregunta no encontrada';
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Detalles de la Respuesta</DialogTitle>
          {response && (
            <DialogDescription>
              Respuesta #{response.id.slice(-6)} enviada el {new Date(response.submitted_at).toLocaleString()}
            </DialogDescription>
          )}
        </DialogHeader>
        <div className="py-4 space-y-4">
          {loading ? (
            <div className="flex justify-center items-center h-24">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : response ? (
            response.answers.map(({ field_id, value }) => (
              <div key={field_id} className="grid grid-cols-3 gap-4 items-start">
                <p className="font-semibold col-span-1">{getFieldLabel(field_id)}</p>
                <p className="col-span-2 text-muted-foreground break-words">
                  {Array.isArray(value) ? value.join(', ') : String(value)}
                </p>
              </div>
            ))
          ) : (
            <p>No hay respuesta para mostrar.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}