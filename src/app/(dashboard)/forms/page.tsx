'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, FileText, Info, Plus, MoreHorizontal, Search, Lightbulb, Edit, MessageSquare, ExternalLink } from 'lucide-react'; 
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import FormCard from '@/components/forms/FormCard';
import { Form as BaseForm } from '@/types/form';
import { motion, AnimatePresence } from 'framer-motion';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

interface Form extends BaseForm {
  responseCount: number;
}

export default function FormsPage() {
  const router = useRouter();
  const [forms, setForms] = useState<Form[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false);

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
      return (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="h-12 w-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-muted-foreground animate-pulse font-medium">Cargando tus formularios...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="text-center py-12 text-red-500 bg-red-500/5 rounded-3xl border border-red-500/10">
          <h3 className="text-lg font-semibold">Error</h3>
          <p>{error}</p>
        </div>
      );
    }

    if (forms.length === 0) {
      return (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-20 px-4 border-2 border-dashed border-border/60 rounded-[2.5rem] bg-muted/5 backdrop-blur-sm"
        >
          <div className="p-6 rounded-3xl bg-background shadow-inner w-fit mx-auto mb-6">
            <FileText className="h-16 w-16 text-muted-foreground/40" />
          </div>
          <h3 className="text-2xl font-bold mb-3 tracking-tight">No hay formularios todavía</h3>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto text-lg leading-relaxed">
            ¡Empieza creando tu primer formulario para recopilar información de manera inteligente y organizada!
          </p>
          <Button onClick={handleCreateNew} size="lg" className="rounded-2xl h-14 px-8 text-lg font-semibold shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 transition-all active:scale-95">
            <Plus className="mr-2 h-6 w-6" />
            Crear Formulario
          </Button>
        </motion.div>
      );
    }

    return (
      <motion.div 
        layout
        className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3"
      >
        <AnimatePresence mode="popLayout">
          {forms.map((form) => (
            <FormCard key={form.id} form={form} />
          ))}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden min-h-screen">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-10 gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-3 rounded-2xl bg-primary/10 border border-primary/20 text-primary">
              <FileText className="h-8 w-8" />
            </div>
            <h1 className="text-4xl font-black tracking-tight flex items-center">
              Formularios
              <Button variant="ghost" size="icon" className="ml-2 h-8 w-8 text-muted-foreground/60 hover:text-primary transition-colors" onClick={() => setIsInfoSheetOpen(true)}>
                <Info className="h-5 w-5" />
              </Button>
            </h1>
          </div>
          <p className="text-muted-foreground/80 font-medium ml-1">Diseña, gestiona y analiza la recopilación de datos.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="lg" className="h-12 rounded-2xl px-6 border-border/60 hover:bg-muted font-bold transition-all shadow-sm">
                Acciones <MoreHorizontal className="ml-2 h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[220px] rounded-2xl border-border/40 bg-card/95 backdrop-blur-xl p-2">
              <DropdownMenuItem onClick={handleCreateNew} className="rounded-xl h-11">
                <Plus className="mr-3 h-5 w-5 text-primary" />
                Nuevo Formulario
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-border/40" />
              <DropdownMenuItem onClick={() => toast.info('Funcionalidad de análisis global en desarrollo')} className="rounded-xl h-11">
                <Lightbulb className="mr-3 h-5 w-5 text-amber-500" />
                Analizar Todo
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          
          <Button size="lg" onClick={handleCreateNew} className="h-12 rounded-2xl px-6 bg-primary hover:bg-primary/90 font-bold shadow-lg shadow-primary/20 transition-all active:scale-95">
            <PlusCircle className="mr-2 h-5 w-5" />
            Crear Nuevo
          </Button>
        </div>
      </div>

      <div className="mb-10 relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-muted-foreground/50" />
        </div>
        <input 
          type="text" 
          placeholder="Buscar formularios por título o descripción..." 
          className="w-full h-14 pl-12 pr-4 rounded-2xl bg-card border border-border/40 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all outline-none font-medium shadow-sm"
          onChange={(e) => {
            // Logic for filtering could be added here
          }}
        />
      </div>

      {renderContent()}

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto border-l-border/40">
          <SheetHeader className="mb-8">
            <div className="p-4 rounded-3xl bg-primary/10 border border-primary/20 w-fit mb-4">
              <FileText className="h-10 w-10 text-primary" />
            </div>
            <SheetTitle className="text-3xl font-black text-primary tracking-tight">Módulo de Formularios</SheetTitle>
            <SheetDescription className="text-base font-medium text-muted-foreground/80">
              Crea, gestiona y recopila respuestas a formularios personalizados para diversas necesidades.
            </SheetDescription>
          </SheetHeader>
          
          <div className="space-y-8 text-sm leading-relaxed">
            <section className="bg-muted/30 p-6 rounded-[2rem] border border-border/20">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-primary" />
                Capacidades Principales
              </h3>
              <ul className="space-y-4 font-medium text-muted-foreground/90">
                <li className="flex gap-3">
                  <div className="h-6 w-6 rounded-lg bg-background flex items-center justify-center border border-border/40 flex-shrink-0">
                    <Edit className="h-3.5 w-3.5" />
                  </div>
                  <span><strong>Diseño Flexible:</strong> Crea formularios con secciones y diversos tipos de campos.</span>
                </li>
                <li className="flex gap-3">
                  <div className="h-6 w-6 rounded-lg bg-background flex items-center justify-center border border-border/40 flex-shrink-0">
                    <MessageSquare className="h-3.5 w-3.5" />
                  </div>
                  <span><strong>Gestión de Respuestas:</strong> Visualiza y organiza los datos recibidos en tiempo real.</span>
                </li>
                <li className="flex gap-3">
                  <div className="h-6 w-6 rounded-lg bg-background flex items-center justify-center border border-border/40 flex-shrink-0">
                    <ExternalLink className="h-3.5 w-3.5" />
                  </div>
                  <span><strong>Enlaces Públicos:</strong> Comparte formularios fácilmente mediante URLs únicas.</span>
                </li>
              </ul>
            </section>

            <section className="p-2">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-amber-500" />
                Interacción con IA
              </h3>
              <p className="mb-4 font-medium text-muted-foreground/80">
                La IA no solo ayuda a gestionar, sino que potencia el valor de tus datos:
              </p>
              <div className="grid grid-cols-1 gap-3">
                {[
                  "Generación automática de estructuras basadas en lenguaje natural.",
                  "Análisis profundo de tendencias en las respuestas recibidas.",
                  "Extracción de insights y resúmenes ejecutivos.",
                  "Búsqueda semántica sobre el contenido de los formularios."
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-2xl bg-amber-500/5 border border-amber-500/10 text-amber-900 dark:text-amber-200 font-semibold">
                    <Lightbulb className="h-4 w-4 text-amber-500 flex-shrink-0" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

