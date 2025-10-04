import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { LinkedFormResponse } from '@/types/form'; // Importa la interfaz

interface FormResponseDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  formResponse: LinkedFormResponse;
}

export function FormResponseDialog({ isOpen, onOpenChange, formResponse }: FormResponseDialogProps) {
  if (!formResponse) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Detalles de la Respuesta de Formulario</DialogTitle>
          <DialogDescription>
            Información detallada de la respuesta #{formResponse.id.slice(-6)}
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="flex-grow p-4 -mx-4">
          <div className="space-y-4 pr-4"> {/* Añadir padding a la derecha para el scrollbar */}
            <Card>
              <CardHeader>
                <CardTitle>Respuesta General</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-2">
                  Enviado el: {new Date(formResponse.submitted_at).toLocaleString()}
                </p>
                <div className="space-y-3">
                  {Object.entries(formResponse.answers).map(([key, value]) => (
                    <div key={key} className="p-3 bg-muted/50 rounded-md">
                      <p className="font-semibold text-sm text-primary-foreground mb-1">{key}:</p>
                      <p className="text-sm mt-1 break-words whitespace-pre-wrap">
                        {typeof value === 'object' && value !== null
                          ? Array.isArray(value)
                            ? value.map(item => typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item)).join(', ')
                            : Object.entries(value).map(([k, v]) =>
                                `${k}: ${typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)}`
                              ).join(', ')
                          : String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
