'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, FileText, Info } from 'lucide-react'; // Importar Info
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'; // Importar Sheet
import FormCard from '@/components/forms/FormCard';
import { Form as BaseForm } from '@/types/form';

interface Form extends BaseForm {
  responseCount: number;
}

export default function FormsPage() {
  const router = useRouter();
  const [forms, setForms] = useState<Form[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Nuevo estado para controlar la visibilidad del Sheet

  useEffect(() => {
    const fetchForms = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get('/api/forms');
        const formsWithResponseCounts = await Promise.all(
          response.data.map(async (form: any) => {
            try {
              const responsesRes = await apiClient.get(`/api/forms/${form.id}/responses`);
              return { ...form, responseCount: responsesRes.data.length };
            } catch (err) {
              console.error(`Failed to fetch responses for form ${form.id}`, err);
              return { ...form, responseCount: 0 };
            }
          })
        );
        setForms(formsWithResponseCounts);
      } catch (err: any) {
        setError('No se pudieron cargar los formularios. Inténtalo de nuevo más tarde.');
        toast.error('Error al cargar formularios');
      } finally {
        setLoading(false);
      }
    };

    fetchForms();
  }, []);

  const handleCreateNew = () => {
    router.push('/forms/new');
  };

  const renderContent = () => {
    if (loading) {
      return <p className="text-center py-10">Cargando formularios...</p>;
    }

    if (error) {
      return (
        <div className="text-center py-12 text-red-500">
          <h3 className="text-lg font-semibold">Error</h3>
          <p>{error}</p>
        </div>
      );
    }

    if (forms.length === 0) {
      return (
        <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
          <FileText className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No hay formularios todavía</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            ¡Empieza creando tu primer formulario para recopilar información!
          </p>
          <Button onClick={handleCreateNew} size="lg">
            <PlusCircle className="mr-2 h-5 w-5" />
            Crear Formulario
          </Button>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {forms.map((form) => (
          <FormCard key={form.id} form={form} />
        ))}
      </div>
    );
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <FileText className="mr-3 h-8 w-8 text-primary" />
            Mis Formularios
            <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
              <Info className="h-4 w-4" />
            </Button>
          </h1>
          <p className="text-muted-foreground mt-1">Crea y gestiona tus formularios para recopilar información.</p>
        </div>
        <Button size="lg" onClick={handleCreateNew} className="bg-primary hover:bg-primary/90">
          <PlusCircle className="mr-2 h-5 w-5" />
          Crear Nuevo
        </Button>
      </div>
      {renderContent()}

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Módulo de Formularios</SheetTitle>
            <SheetDescription className="text-sm text-muted-foreground">
              Crea, gestiona y recopila respuestas a formularios personalizados para diversas necesidades.
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué puedes hacer en tus Formularios?</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Crear Formularios Personalizados:</strong> Diseña formularios con diferentes tipos de campos (texto, selección, etc.) para recopilar la información que necesites.</li>
              <li><strong>Gestionar Formularios:</strong> Edita, visualiza y elimina tus formularios de forma sencilla.</li>
              <li><strong>Recopilar Respuestas:</strong> Recibe y organiza las respuestas de tus usuarios directamente en el sistema.</li>
              <li><strong>Compartir Formularios:</strong> Comparte enlaces públicos para que otros puedan responder a tus formularios.</li>
            </ul>

            <p><strong>Interacción con IA:</strong></p>
            <p>Además de la gestión manual, puedes interactuar con tus formularios y sus respuestas a través del chat de IA. La IA dispone de herramientas especializadas para:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Generar nuevos formularios o sugerir campos basados en una descripción.</li>
              <li>Analizar las respuestas de los formularios para extraer tendencias, resúmenes y estadísticas.</li>
              <li>Responder preguntas sobre el contenido de las respuestas de los formularios.</li>
              <li>Resumir el propósito y uso de un formulario específico.</li>
            </ul>

            <p><strong>Beneficios Clave:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Recopilación de Datos Eficiente:</strong> Obtén la información que necesitas de manera estructurada.</li>
              <li><strong>Análisis Automatizado:</strong> Deja que la IA te ayude a entender tus datos.</li>
              <li><strong>Versatilidad:</strong> Utiliza formularios para encuestas, registros, feedback y más.</li>
            </ul>

            <p>¡Simplifica la recopilación y análisis de información con el Módulo de Formularios!</p>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
