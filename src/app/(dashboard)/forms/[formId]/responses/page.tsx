'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { ArrowLeft, Loader2, Table as TableIcon, BarChart, Link, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import apiClient from '@/lib/api';
import { toast as sonnerToast } from 'sonner';
import { Form as BaseForm, FormFieldData, FormSectionData, FormElement } from '@/types/form';
import { ContactProfile } from '@/types/contact-profile';
import { ManageLinkedProfilesDialog } from '@/app/(dashboard)/notes/ManageLinkedProfilesDialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";

interface FormResponseAnswer {
  field_id: string;
  value: any;
}

interface FormResponse {
  id: string;
  form_id: string;
  submitted_at: string;
  answers: FormResponseAnswer[];
  contact_profile_id?: string; // Añadir esta propiedad
  contact_profile_name?: string; // Añadir esta propiedad
}

interface Form extends BaseForm {
  responses: FormResponse[];
}

function isFormField(element: FormElement): element is FormFieldData {
  return (element as FormFieldData).type !== undefined;
}

function isFormSection(element: FormElement): element is FormSectionData {
  return (element as FormSectionData).elements !== undefined;
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

export default function FormResponsesPage() {
  const router = useRouter();
  const params = useParams();
  const formId = params?.formId as string;
  const { toast } = useToast();

  const [form, setForm] = useState<Form | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [showLinkProfileDialog, setShowLinkProfileDialog] = useState(false);
  const [currentResponseToLink, setCurrentResponseToLink] = useState<FormResponse | null>(null);

  const handleDeleteResponse = async (responseId: string) => {
    try {
      await apiClient.delete(`/api/form-responses/${responseId}`);
      sonnerToast.success('Respuesta eliminada exitosamente.');
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
    }
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
        setError('No se pudo cargar el formulario o sus respuestas. Puede que no exista o haya ocurrido un error.');
        sonnerToast.error('Error al cargar los datos del formulario.');
      } finally {
        setLoading(false);
      }
    };
    fetchFormData();
  }, [formId]);

  const allFormFields = useMemo(() => {
    if (!form) return [];
    return extractAllFormFields(form.elements);
  }, [form]);

  const fieldIdToLabelMap = useMemo(() => {
    return allFormFields.reduce((acc, field) => {
      acc[field.id] = field.label;
      return acc;
    }, {} as Record<string, string>);
  }, [allFormFields]);

  // Función para calcular estadísticas
  const calculateStatistics = useMemo(() => {
    if (!form || form.responses.length === 0) return {};

    const stats: Record<string, any> = {};

    allFormFields.forEach(field => {
      if (field.type === 'radio' || field.type === 'select') {
        const counts: Record<string, number> = {};
        form.responses.forEach(response => {
          const answer = response.answers.find(ans => ans.field_id === field.id);
          if (answer && answer.value) {
            counts[String(answer.value)] = (counts[String(answer.value)] || 0) + 1;
          }
        });
        stats[field.id] = { label: field.label, type: field.type, counts };
      } else if (field.type === 'checkbox') {
        const counts: Record<string, number> = {};
        form.responses.forEach(response => {
          const answer = response.answers.find(ans => ans.field_id === field.id);
          if (answer && Array.isArray(answer.value)) {
            answer.value.forEach(option => {
              counts[String(option)] = (counts[String(option)] || 0) + 1;
            });
          }
        });
        stats[field.id] = { label: field.label, type: field.type, counts };
      } else {
        // Para otros tipos, simplemente contamos cuántas respuestas hay
        const responseCount = form.responses.filter(response => 
          response.answers.some(ans => ans.field_id === field.id && ans.value !== null && ans.value !== '')
        ).length;
        stats[field.id] = { label: field.label, type: field.type, responseCount };
      }
    });

    return stats;
  }, [form, allFormFields]);

  if (loading) {
    return <div className="p-4 sm:p-8 max-w-7xl mx-auto flex justify-center items-center"><Loader2 className="h-8 w-8 animate-spin" /><span className="ml-4">Cargando respuestas...</span></div>;
  }

  if (error) {
    return (
      <div className="p-4 sm:p-8 max-w-7xl mx-auto text-center text-destructive">
        <h2 className="text-xl font-bold mb-4">Error</h2>
        <p>{error}</p>
        <Button onClick={() => router.push(`/forms/${formId}`)} className="mt-4">Volver al Formulario</Button>
      </div>
    );
  }

  if (!form) {
    return <div className="p-4 sm:p-8 max-w-7xl mx-auto">Formulario no encontrado.</div>;
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
            <TableIcon className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Respuestas de &quot;{form.title}&quot;</h1>
            <p className="text-muted-foreground">Visualización de todas las respuestas en formato de tabla.</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push(`/forms/${formId}`)}><ArrowLeft className="mr-2 h-4 w-4" />Volver al Formulario</Button>
          <Dialog open={showStatsModal} onOpenChange={setShowStatsModal}>
            <DialogTrigger asChild>
              <Button variant="outline"><BarChart className="mr-2 h-4 w-4" />Ver Estadísticas</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[800px]">
              <React.Fragment>
                <DialogHeader>
                  <DialogTitle>Estadísticas del Formulario</DialogTitle>
                  <DialogDescription>
                    Análisis de las respuestas para &quot;{form.title}&quot;.
                  </DialogDescription>
                </DialogHeader>
                <div className="py-4">
                  {Object.keys(calculateStatistics).length > 0 ? (
                    Object.entries(calculateStatistics).map(([fieldId, stat]) => {
                      return (
                      <Card key={fieldId} className="mb-4">
                        <CardHeader>
                          <CardTitle>{stat.label}</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {stat.type === 'radio' || stat.type === 'select' || stat.type === 'checkbox' ? (
                            <div>
                              {Object.entries(stat.counts).map(([option, count]) => (
                                <div key={option} className="flex justify-between items-center mb-2">
                                  <span>{String(option)}</span>
                                  <span className="font-semibold">{String(count)}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p>Total de respuestas: <span className="font-semibold">{stat.responseCount}</span></p>
                          )}
                        </CardContent>
                      </Card>
                    )}) 
                  ) : (
                    <p className="text-muted-foreground">No hay datos suficientes para generar estadísticas.</p>
                  )}
                </div>
              </React.Fragment>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card className="bg-card/50 border-dashed">
        <CardHeader>
          <CardTitle>Tabla de Respuestas</CardTitle>
          <CardDescription>Cada fila es una respuesta enviada, y cada columna es una pregunta del formulario.</CardDescription>
        </CardHeader>
        <CardContent>
          {form.responses.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID Respuesta</TableHead>
                    <TableHead>Fecha Envío</TableHead>
                                        <TableHead>Perfil Vinculado</TableHead>
                                        {allFormFields.map(field => (
                                          <TableHead key={field.id}>{field.label}</TableHead>
                                        ))}
                                        <TableHead>Acciones</TableHead>
                                      </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                      {form.responses.map(response => {
                                        return (
                                          <TableRow key={response.id}>
                                            <TableCell className="font-medium">{response.id.substring(0, 8)}...</TableCell>
                                            <TableCell>{new Date(response.submitted_at).toLocaleString()}</TableCell>
                                            <TableCell>
                                              {response.contact_profile_id ? (
                                                <div className="flex items-center gap-2">
                                                  <span>{response.contact_profile_name || 'Perfil desconocido'}</span>
                                                  <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => {
                                                      setCurrentResponseToLink(response);
                                                      setShowLinkProfileDialog(true);
                                                    }}
                                                  >
                                                    <Link className="h-4 w-4" />
                                                  </Button>
                                                </div>
                                              ) : (
                                                <Button
                                                  variant="outline"
                                                  size="sm"
                                                  onClick={() => {
                                                    setCurrentResponseToLink(response);
                                                    setShowLinkProfileDialog(true);
                                                  }}
                                                >
                                                  Vincular Perfil
                                                </Button>
                                              )}
                                            </TableCell>
                                            {allFormFields.map(field => {
                                              const answer = response.answers.find(ans => ans.field_id === field.id);
                                              return (
                                                <TableCell key={field.id}>
                                                  {answer ? (typeof answer.value === 'object' ? JSON.stringify(answer.value) : String(answer.value)) : '-'}
                                                </TableCell>
                                              );
                                            })}
                                            <TableCell>
                                              <Dialog>
                                                <DialogTrigger asChild>
                                                  <Button variant="destructive" size="icon">
                                                    <Trash2 className="h-4 w-4" />
                                                  </Button>
                                                </DialogTrigger>
                                                <DialogContent>
                                                  <DialogHeader>
                                                    <DialogTitle>¿Estás seguro?</DialogTitle>
                                                    <DialogDescription>
                                                      Esta acción no se puede deshacer. Se eliminará permanentemente la respuesta #{response.id.slice(-6)}.
                                                    </DialogDescription>
                                                  </DialogHeader>
                                                  <DialogFooter>
                                                    <Button variant="outline" onClick={(e) => e.stopPropagation()}>
                                                      Cancelar
                                                    </Button>
                                                    <Button variant="destructive" onClick={() => handleDeleteResponse(response.id)}>
                                                      Eliminar
                                                    </Button>
                                                  </DialogFooter>
                                                </DialogContent>
                                              </Dialog>
                                            </TableCell>
                                          </TableRow>
                                        );
                                      })}
                                    </TableBody>              </Table>
            </div>
          ) : (
            <div className="text-center py-16">
              <p className="text-muted-foreground">Aún no hay respuestas para este formulario.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {currentResponseToLink && (
        <ManageLinkedProfilesDialog
          itemType="form-response"
          itemId={currentResponseToLink.id}
          linkedProfiles={currentResponseToLink.contact_profile_id ? [{ id: currentResponseToLink.contact_profile_id, name: currentResponseToLink.contact_profile_name || 'Perfil desconocido' }] : []}
          isOpen={showLinkProfileDialog}
          onClose={() => {
            setShowLinkProfileDialog(false);
            setCurrentResponseToLink(null);
          }}
          onLink={async (profileId, itemId) => {
            try {
              await apiClient.post(`/api/contact-profiles/${profileId}/link-form-response`, { form_response_id: itemId });
              sonnerToast.success('Respuesta vinculada exitosamente.');
              // Recargar los datos del formulario para actualizar la UI
              // Esto es un poco brusco, se podría optimizar actualizando solo la respuesta afectada
              router.refresh(); // O llamar a fetchFormData() de nuevo
            } catch (error) {
              sonnerToast.error('Error al vincular la respuesta.');
              console.error('Error linking form response:', error);
            }
          }}
          onUnlink={async (profileId, itemId) => {
            try {
              await apiClient.post(`/api/contact-profiles/${profileId}/unlink-form-response`, { form_response_id: itemId });
              sonnerToast.success('Respuesta desvinculada exitosamente.');
              // Recargar los datos del formulario para actualizar la UI
              router.refresh(); // O llamar a fetchFormData() de nuevo
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
