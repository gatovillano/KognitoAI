'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { toast as sonnerToast } from 'sonner';
import { Loader2, CheckCircle } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import apiClient from '@/lib/api';
import { Form as BaseForm, FormFieldData, FormSectionData, FormElement } from '@/types/form';
import Image from 'next/image';

interface Form extends BaseForm {}

function isFormField(element: FormElement): element is FormFieldData {
  return (element as FormFieldData).type !== undefined;
}

function isFormSection(element: FormElement): element is FormSectionData {
  return (element as FormSectionData).elements !== undefined;
}

export default function PublicFormPage() {
  const params = useParams();
  const formId = params?.formId as string;

  const [form, setForm] = useState<Form | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const fetchForm = async () => {
      if (!formId) return;
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get(`/api/forms/${formId}`);
        setForm(response.data);
      } catch (err) {
        setError('No se pudo cargar el formulario. Puede que no exista o que el enlace sea incorrecto.');
        sonnerToast.error('Error al cargar el formulario.');
      } finally {
        setLoading(false);
      }
    };

    fetchForm();
  }, [formId]);

  const handleInputChange = (fieldId: string, value: any) => {
    setAnswers(prev => ({ ...prev, [fieldId]: value }));
  };

  const validateFields = (elements: FormElement[]): boolean => {
    for (const element of elements) {
      if (isFormField(element)) {
        if (element.is_required && !answers[element.id]) {
          sonnerToast.error(`El campo "${element.label}" es obligatorio.`);
          return false;
        }
      } else if (isFormSection(element)) {
        if (!validateFields(element.elements)) {
          return false;
        }
      }
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;

    if (!validateFields(form.elements)) {
      return;
    }

    setIsSubmitting(true);
    try {
      const submissionData = {
        id: uuidv4(),
        form_id: formId,
        answers: Object.entries(answers).map(([field_id, value]) => ({ field_id, value })),
      };

      await apiClient.post(`/api/forms/${formId}/responses`, submissionData);
      setSubmitted(true);

    } catch (error) {
      console.error('Failed to submit response:', error);
      sonnerToast.error('Error al enviar la respuesta. Por favor, inténtalo de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderField = (field: FormFieldData) => {
    switch (field.type) {
      case 'text':
        return <Input required={field.is_required} onChange={(e) => handleInputChange(field.id, e.target.value)} className="bg-background/50" />;
      case 'textarea':
        return <Textarea required={field.is_required} onChange={(e) => handleInputChange(field.id, e.target.value)} className="bg-background/50" />;
      case 'radio':
        return (
          <RadioGroup onValueChange={(value) => handleInputChange(field.id, value)} required={field.is_required} className="space-y-2">
            {field.options?.map(option => (
              <div key={option} className="flex items-center space-x-3 p-3 rounded-md border bg-background/50 hover:bg-accent/50 transition-colors">
                <RadioGroupItem value={option} id={`${field.id}-${option}`} />
                <label htmlFor={`${field.id}-${option}`} className="font-normal cursor-pointer flex-grow">{option}</label>
              </div>
            ))}
          </RadioGroup>
        );
      case 'checkbox':
        return (
            <div className="space-y-2">
                {field.options?.map(option => (
                    <div key={option} className="flex items-center space-x-3 p-3 rounded-md border bg-background/50 hover:bg-accent/50 transition-colors">
                        <Checkbox 
                            id={`${field.id}-${option}`}
                            onCheckedChange={(checked) => {
                                const current = answers[field.id] || [];
                                const newAnswers = checked ? [...current, option] : current.filter((item: string) => item !== option);
                                handleInputChange(field.id, newAnswers);
                            }}
                        />
                        <label htmlFor={`${field.id}-${option}`} className="font-normal cursor-pointer flex-grow">{option}</label>
                    </div>
                ))}
            </div>
        );
      case 'select':
        return (
          <Select onValueChange={(value) => handleInputChange(field.id, value)} required={field.is_required}>
            <SelectTrigger className="bg-background/50"><SelectValue placeholder="Selecciona una opción" /></SelectTrigger>
            <SelectContent>
              {field.options?.map(option => <SelectItem key={option} value={option}>{option}</SelectItem>)}
            </SelectContent>
          </Select>
        );
      default:
        return null;
    }
  };

  const renderFormElement = (element: FormElement): React.ReactNode => {
    if (isFormField(element)) {
      return (
        <div key={element.id} className="py-6 border-b border-border/50">
          <label className="font-semibold text-lg">
            {element.label}
            {element.is_required && <span className="text-destructive ml-1">*</span>}
          </label>
          {element.description && <p className="text-sm text-muted-foreground mt-1 mb-4">{element.description}</p>}
          <div className="mt-4">
            {renderField(element)}
          </div>
        </div>
      );
    } else if (isFormSection(element)) {
      return (
        <div key={element.id} className="pt-8 pb-4 mt-8 border-t-2 border-primary/20">
          <h2 className="text-2xl font-bold text-primary">{element.title}</h2>
          {element.description && <p className="text-muted-foreground mt-2 mb-6">{element.description}</p>}
          <div className="space-y-6">
            {element.elements.map(subElement => renderFormElement(subElement))}
          </div>
        </div>
      );
    }
    return null;
  };

  const renderState = (content: React.ReactNode) => (
    <div className="flex items-center justify-center min-h-screen bg-background text-foreground p-4">
        <div className="w-full max-w-2xl mx-auto">
            {content}
        </div>
    </div>
  );

  if (loading) {
    return renderState(
        <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto" />
            <p className="mt-4 text-muted-foreground">Cargando formulario...</p>
        </div>
    );
  }

  if (error) {
    return renderState(<p className="text-center text-destructive">{error}</p>);
  }

  if (!form) {
    return renderState(<p className="text-center">Formulario no encontrado.</p>);
  }

  if (submitted) {
    return renderState(
        <div className="text-center p-8 border border-border rounded-lg bg-card">
            <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
            <h1 className="text-2xl font-bold mb-2">¡Gracias!</h1>
            <p className="text-muted-foreground">Tu respuesta ha sido enviada con éxito.</p>
        </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-4 sm:p-6 md:p-8">
        <div className="w-full max-w-2xl mx-auto">
            <header className="text-center py-12 border-b border-border/50 mb-8">
                <h1 className="text-4xl font-bold tracking-tight">{form.title}</h1>
                {form.description && <p className="mt-4 text-lg text-muted-foreground max-w-xl mx-auto">{form.description}</p>}
            </header>
            
            <form onSubmit={handleSubmit} className="space-y-6">
                {form.elements.map(element => renderFormElement(element))}
                
                <div className="pt-8">
                    <Button type="submit" className="w-full h-12 text-lg" disabled={isSubmitting}>
                        {isSubmitting ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : null}
                        {isSubmitting ? 'Enviando...' : 'Enviar Respuesta'}
                    </Button>
                </div>
            </form>

            <footer className="text-center py-12 mt-8">
                <a href="https://kognito.gatoslibres.art" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                    Powered by 
                    <Image src="/logo-simple.png" alt="Kognito Logo" width={20} height={20} />
                    <span className="font-semibold">Kognito AI</span>
                </a>
            </footer>
        </div>
    </div>
  );
}
