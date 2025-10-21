'use client';

import React from 'react';
import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ArrowLeft, Edit, Share2, Loader2, FileText, Table as TableIcon, Link, Download } from 'lucide-react';
import ResponseCard from '@/components/forms/ResponseCard';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/lib/api';
import { toast as sonnerToast } from 'sonner';
import { Form as BaseForm, FormFieldData, FormSectionData, FormElement, FormResponse, FormResponseAnswer } from '@/types/form';
import { ContactProfile } from '../../profiles/page';
import { ManageLinkedProfilesDialog } from '@/app/(dashboard)/notes/ManageLinkedProfilesDialog';



interface Form extends BaseForm {
  responses: FormResponse[];
}

function isFormField(element: FormElement): element is FormFieldData {
  return (element as FormFieldData).type !== undefined;
}

function isFormSection(element: FormElement): element is FormSectionData {
  return (element as FormSectionData).elements !== undefined;
}

function renderFormElement(element: FormElement): React.ReactNode {
  if (isFormField(element)) {
    return (
      <div key={element.id} className="py-4 border-b last:border-b-0">
        <p className="font-semibold">{element.label} {element.is_required && <span className="text-destructive">*</span>}</p>
        {element.description && <p className="text-sm text-muted-foreground mt-1">{element.description}</p>}
        <p className="text-xs text-muted-foreground mt-2">Tipo: {element.type}</p>
        {element.options && element.options.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-muted-foreground">Opciones:</p>
            <ul className="list-disc list-inside text-xs text-muted-foreground pl-4">
              {element.options.map((option, idx) => (
                <li key={idx}>{option}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  } else if (isFormSection(element)) {
    return (
      <div key={element.id} className="pt-6 pb-2 mt-6 border-t">
        <h3 className="text-lg font-semibold text-primary">{element.title}</h3>
        {element.description && <p className="text-sm text-muted-foreground mt-1 mb-4">{element.description}</p>}
        <div className="space-y-2 ml-4 border-l pl-4">
          {element.elements.map(subElement => renderFormElement(subElement))}
        </div>
      </div>
    );
  }
  return null;
}

function extractAllFormFields(elements: FormElement[]): FormFieldData[] {
  let allFields: FormFieldData[] = [];
  elements.forEach(element => {
    if (isFormField(element)) {
      allFields.push(element);
    } else if (isFormSection(element)) {
      allFields = allFields.concat(extractAllFormFields(element.elements));
    }
  });
  return allFields;
}

export default function FormViewPage() {
  const router = useRouter();
  const params = useParams();
  const formId = params?.formId as string;
  const { toast } = useToast();

  const [form, setForm] = useState<Form | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLinkProfileDialog, setShowLinkProfileDialog] = useState(false);
  const [currentResponseToLink, setCurrentResponseToLink] = useState<FormResponse | null>(null);

  const handleOpenLinkProfileDialog = (response: FormResponse) => {
    setCurrentResponseToLink(response);
    setShowLinkProfileDialog(true);
  };

  useEffect(() => {
    const fetchFormData = async () => {
      if (!formId) return;
      setLoading(true);
      setError(null);
      try {
        const [formDetailsRes, formResponsesRes] = await Promise.all([
          apiClient.get(`/api/forms/${formId}`),
          apiClient.get(`/api/forms/${formId}/responses`)
        ]);

        const responsesWithProfileNames = await Promise.all(formResponsesRes.data.map(async (response: FormResponse) => {
          if (response.contact_profile_id) {
            try {
              const profileRes = await apiClient.get(`/api/contact-profiles/${response.contact_profile_id}`);
              return { ...response, contact_profile_name: profileRes.data.name };
            } catch (profileErr) {
              console.error(`Error fetching profile for response ${response.id}:`, profileErr);
              return { ...response, contact_profile_name: 'Perfil no encontrado' };
            }
          }
          return response;
        }));

        setForm({ ...formDetailsRes.data, responses: responsesWithProfileNames });
      } catch (err) {
        setError('No se pudo cargar el formulario. Puede que no exista o haya ocurrido un error.');
        sonnerToast.error('Error al cargar los datos del formulario.');
      } finally {
        setLoading(false);
      }
    };
    fetchFormData();
  }, [formId]);

  const handleShare = async () => {
    const shareUrl = `${window.location.origin}/forms/fill/${formId}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast({ title: "¡Enlace copiado!", description: "El enlace para rellenar el formulario ha sido copiado a tu portapapeles." });
    } catch (err) {
      toast({ title: "Error al copiar", description: "No se pudo copiar el enlace. Cópialo manualmente: " + shareUrl, variant: "destructive" });
    }
  };

  const handleDownloadReport = async () => {
    try {
      const response = await apiClient.get(`/api/forms/${formId}/responses/pdf`, {
        responseType: 'blob', // Important: receive as a blob
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `reporte_formulario_${formId.substring(0, 8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      sonnerToast.success('Reporte PDF del formulario descargado exitosamente.');
    } catch (error) {
      console.error('Error al descargar el reporte PDF del formulario:', error);
      sonnerToast.error('Error al descargar el reporte PDF del formulario.');
    }
  };

  const handleDeleteResponse = async (responseId: string) => {
    try {
      await apiClient.delete(`/api/form-responses/${responseId}`);
      sonnerToast.success('Respuesta eliminada exitosamente.');
      // Update the UI by filtering out the deleted response
      setForm(prevForm => {
        if (!prevForm) return null;
        return {
          ...prevForm,
          responses: prevForm.responses.filter(response => response.id !== responseId),
        };
      });
    } catch (error) {
      console.error('Error deleting response:', error);
      sonnerToast.error('Error al eliminar la respuesta.');
      throw error; // Re-throw to be caught by the card component if needed
    }
  };

  if (loading) {
    return <div className="p-4 sm:p-8 max-w-7xl mx-auto flex justify-center items-center"><Loader2 className="h-8 w-8 animate-spin" /><span className="ml-4">Cargando...</span></div>;
  }

  if (error) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto text-center text-destructive">
        <h2 className="text-xl font-bold mb-4">Error</h2>
        <p>{error}</p>
        <Button onClick={() => router.push('/forms')} className="mt-4">Volver a Formularios</Button>
      </div>
    );
  }

  if (!form) {
    return <div className="p-4 sm:p-8 max-w-7xl mx-auto">Formulario no encontrado.</div>;
  }

  const allFormFields = extractAllFormFields(form.elements);

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">{form.title}</h1>
            <p className="text-muted-foreground">{form.description || 'Visualización del formulario y sus respuestas'}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/forms')}><ArrowLeft className="mr-2 h-4 w-4" />Volver</Button>
          <Button variant="outline" onClick={handleShare}><Share2 className="mr-2 h-4 w-4" />Compartir</Button>
          <Button variant="outline" onClick={handleDownloadReport}><Download className="mr-2 h-4 w-4" />Descargar Reporte PDF</Button>
          <Button variant="outline" onClick={() => router.push(`/forms/${formId}/responses`)}><TableIcon className="mr-2 h-4 w-4" />Ver Respuestas</Button>
          <Button onClick={() => router.push(`/forms/${formId}/edit`)}><Edit className="mr-2 h-4 w-4" />Editar</Button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <Card className="bg-card/50 border-dashed">
            <CardHeader>
              <CardTitle>Estructura del Formulario</CardTitle>
              <CardDescription>Así es como se ven las preguntas y secciones.</CardDescription>
            </CardHeader>
            <CardContent>
              {form.elements.map(element => renderFormElement(element))}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-7">
            <h2 className="text-2xl font-semibold mb-4">Respuestas ({form.responses.length})</h2>
            <div className="space-y-4">
                {form.responses.length > 0 ? (
                    form.responses.map((response) => (
                    <ResponseCard key={response.id} response={response} formFields={allFormFields} onOpenLinkProfileDialog={handleOpenLinkProfileDialog} onDelete={handleDeleteResponse} />
                    ))
                ) : (
                    <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
                        <p className="text-muted-foreground">Aún no hay respuestas para este formulario.</p>
                    </div>
                )}
            </div>
        </div>
      </div>

      {currentResponseToLink && (
        <ManageLinkedProfilesDialog
          itemType="form-response"
          item={{ id: currentResponseToLink.id, title: `Respuesta #${currentResponseToLink.id.slice(-6)}` }}
          isOpen={showLinkProfileDialog}
          onOpenChange={(open) => {
            setShowLinkProfileDialog(open);
            if (!open) {
              setCurrentResponseToLink(null);
            }
          }}
          onLinkedProfilesUpdated={() => router.refresh()} // Añadir esta prop
          onLink={async (profileId, itemId) => {
            try {
              await apiClient.post(`/api/contact-profiles/${profileId}/link-form-response`, { form_response_id: itemId });
              sonnerToast.success('Respuesta vinculada exitosamente.');
              router.refresh();
            } catch (error) {
              sonnerToast.error('Error al vincular la respuesta.');
              console.error('Error linking form response:', error);
            }
          }}
          onUnlink={async (profileId, itemId) => {
            try {
              await apiClient.post(`/api/contact-profiles/${profileId}/unlink-form-response`, { form_response_id: itemId });
              sonnerToast.success('Respuesta desvinculada exitosamente.');
              router.refresh();
            } catch (error) {
              sonnerToast.error('Error al desvincular la respuesta.');
              console.error('Error unlinking form response:', error);
            }
          }}
        />
      )}
    </div>
  );
}
