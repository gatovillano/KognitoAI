'use client';

import React from 'react';
import { Form as BaseForm, FormFieldData, FormSectionData, FormElement } from '@/types/form';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useRouter } from 'next/navigation'; // Importar useRouter
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, FileText, ArrowLeft } from 'lucide-react'; // Importar ArrowLeft
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface FormViewerHeaderProps {
  form: BaseForm;
  renderFormElement: (element: FormElement) => React.ReactNode;
  onShare: () => void;
  onDownloadReport: () => void;
  onViewResponses: () => void;
  onEditForm: () => void;
}

export function FormViewerHeader({
  form,
  renderFormElement,
  onShare,
  onDownloadReport,
  onViewResponses,
  onEditForm,
}: FormViewerHeaderProps) {
  const router = useRouter(); // Initialize useRouter
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mb-8 overflow-hidden">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 p-4 sm:p-6">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <CardTitle className="text-xl sm:text-2xl font-bold">{form.title}</CardTitle>
              <CardDescription className="text-sm sm:text-base">{form.description || 'Visualización del formulario y sus respuestas'}</CardDescription>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => router.push('/forms')}><ArrowLeft className="mr-2 h-4 w-4" />Volver</Button> {/* Botón de volver */}
            <Button variant="outline" size="sm" onClick={onShare} className="h-8">Compartir</Button>
            <Button variant="outline" size="sm" onClick={onDownloadReport} className="h-8">Reporte PDF</Button>
            <Button variant="outline" size="sm" onClick={onViewResponses} className="h-8">Ver Respuestas</Button>
            <Button size="sm" onClick={onEditForm} className="h-8">Editar</Button>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
          </div>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="border-t p-4 sm:p-6">
            <h3 className="text-lg font-semibold mb-4">Estructura del Formulario</h3>
            <div className="space-y-4">
              {form.elements.map(element => renderFormElement(element))}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}