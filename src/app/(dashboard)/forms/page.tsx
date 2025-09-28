'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { PlusCircle, FileText } from 'lucide-react';
import FormCard from '@/components/forms/FormCard';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Form as BaseForm } from '@/types/form';

interface Form extends BaseForm {
  responseCount: number;
}

export default function FormsPage() {
  const router = useRouter();
  const [forms, setForms] = useState<Form[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          </h1>
          <p className="text-muted-foreground mt-1">Crea y gestiona tus formularios para recopilar información.</p>
        </div>
        <Button size="lg" onClick={handleCreateNew} className="bg-primary hover:bg-primary/90">
          <PlusCircle className="mr-2 h-5 w-5" />
          Crear Nuevo
        </Button>
      </div>
      {renderContent()}
    </div>
  );
}
