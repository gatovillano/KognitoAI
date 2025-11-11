/* eslint-disable react/jsx-no-undef */
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input'; // Importar Input
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, User, Edit, Trash2, MoreHorizontal, Info, Mail, Phone, Search } from 'lucide-react'; // Importar Search
import { motion, AnimatePresence } from 'framer-motion';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'; // Importar Sheet
import { useDrag, useDrop } from 'react-dnd';

import { useRouter } from 'next/navigation';
import { ProfileDialog } from './profile-dialog';

export interface ContactProfile {
  id: string;
  account_id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  tags: string[] | null;
  category: string | null;
  custom_fields: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<ContactProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [categoryView, setCategoryView] = useState(false); // NEW
  const [editingProfile, setEditingProfile] = useState<ContactProfile | null>(null);
  const [deletingProfile, setDeletingProfile] = useState<ContactProfile | null>(null);
  const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Nuevo estado para controlar la visibilidad del Sheet
  const [searchTerm, setSearchTerm] = useState(''); // Estado para el término de búsqueda

  const fetchProfiles = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/list-contact-profiles', {});
      setProfiles(response.data.sort((a: ContactProfile, b: ContactProfile) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (error) {
      toast.error('Error al cargar los perfiles.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfiles();
  }, []);

  const handleSaveSuccess = () => {
    fetchProfiles();
  };

  const handleDeleteConfirm = async () => {
    if (!deletingProfile) return;
    const toastId = toast.loading(`Eliminando perfil...`);
    try {
      await apiClient.post('/api/delete-contact-profile', { profile_id: deletingProfile.id });
      toast.success('Perfil eliminado', { id: toastId });
      setDeletingProfile(null);
      fetchProfiles();
    } catch (error) {
      toast.error('Error al eliminar el perfil', { id: toastId });
    }
  };

  const updateProfileCategory = async (profileId: string, newCategory: string) => { // NEW
    try {
      const toastId = toast.loading(`Moviendo perfil...`);
      await apiClient.post(`/api/update-contact-profile/${profileId}`, {
        category: newCategory
      });
      setProfiles(prevProfiles => prevProfiles.map(profile => profile.id === profileId ? { ...profile, category: newCategory } : profile));
      toast.success('Perfil movido a otra categoría', { id: toastId });
    } catch (error) {
      toast.error('Error al mover el perfil');
      console.error(error);
    }
  };

  const ProfileCard = ({ profile }: { profile: ContactProfile }) => {
    const router = useRouter();
    console.log('Router in ProfileCard:', router); // Añadir este console.log
    const [{ isDragging }, drag] = useDrag({
      type: 'PROFILE',
      item: { id: profile.id, category: profile.category },
      collect: monitor => ({
        isDragging: !!monitor.isDragging(),
      }),
    });

    return (
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        ref={drag as any}
        className="h-full"
      >
        <Card
          className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full min-h-[200px]"
          style={{ opacity: isDragging ? 0.5 : 1 }}
          onClick={() => {
            console.log(`Navigating to /profiles/${profile.id}`);
            router.push(`/profiles/${profile.id}`);
          }}
        >
          <CardHeader className="pb-3">
            <CardTitle className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <User className="h-5 w-5 text-primary" />
                </div>
                <span className="font-semibold text-lg">{profile.name || 'Perfil sin nombre'}</span>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 hover:bg-muted"
                  onClick={(e) => { e.stopPropagation(); setEditingProfile(profile); setIsProfileDialogOpen(true); }}
                  title="Editar perfil"
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 hover:bg-destructive hover:text-destructive-foreground"
                  onClick={(e) => { e.stopPropagation(); setDeletingProfile(profile); }}
                  title="Eliminar perfil"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-grow">
            <div className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
              {profile.email && (
                <p className="flex items-center gap-2"><Mail className="h-4 w-4" /> {profile.email}</p>
              )}
              {profile.phone && (
                <p className="flex items-center gap-2"><Phone className="h-4 w-4" /> {profile.phone}</p>
              )}
              {profile.tags && profile.tags.length > 0 && (
                <div className="mt-2">
                  <p className="font-semibold mb-1">Etiquetas:</p>
                  <div className="flex flex-wrap gap-2">
                    {profile.tags.map((tag, index) => {
                      const colors = ['bg-blue-100 text-blue-800', 'bg-green-100 text-green-800', 'bg-yellow-100 text-yellow-800', 'bg-purple-100 text-purple-800', 'bg-pink-100 text-pink-800'];
                      const colorClass = colors[index % colors.length];
                      return (
                        <span key={tag} className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
                          {tag}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
              {!profile.email && !profile.phone && (!profile.tags || profile.tags.length === 0) && (!profile.custom_fields || Object.keys(profile.custom_fields).length === 0) && (
                <p>Sin detalles de contacto.</p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50">
            <span>{profile.category || 'Sin Categoría'}</span> {/* Display category */}
            <div className="flex items-center gap-2">
              <span>Creado: {new Date(profile.created_at).toLocaleDateString()}</span>
              <span>Actualizado: {new Date(profile.updated_at).toLocaleDateString()}</span>
            </div>
          </CardFooter>
        </Card>
      </motion.div>
    );
  };

  const renderProfiles = () => {
    if (isLoading) {
      return <p className="text-center py-10">Cargando perfiles...</p>;
    }

    if (profiles.length === 0) {
      return (
        <div className="text-center py-16">
          <User className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No tienes perfiles de contacto aún</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Crea perfiles para tus contactos y organiza su información.
          </p>
          <Button onClick={() => { setEditingProfile(null); setIsProfileDialogOpen(true); }} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            Crear tu primer Perfil
          </Button>
        </div>
      );
    }

    if (categoryView) {
      const filteredProfiles = profiles.filter(profile =>
        profile.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        profile.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        profile.phone?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        profile.tags?.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      );

      const groupedProfiles = filteredProfiles.reduce((groups, profile) => {
        const key = profile.category || 'Sin Categoría';
        if (!groups[key]) {
          groups[key] = [];
        }
        groups[key].push(profile);
        return groups;
      }, {} as Record<string, ContactProfile[]>);

      return (
        <AnimatePresence>
          <motion.div layout className="space-y-8">
            {Object.entries(groupedProfiles).map(([category, categoryProfiles]) => (
              <CategoryDropZone key={category} category={category} updateProfileCategory={updateProfileCategory}>
                {categoryProfiles.map((profile) => (
                  <ProfileCard key={profile.id} profile={profile} />
                ))}
              </CategoryDropZone>
            ))}
          </motion.div>
        </AnimatePresence>
      );
    }

    const filteredProfiles = profiles.filter(profile =>
      profile.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      profile.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      profile.phone?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      profile.tags?.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    return (
      <motion.div layout className="grid gap-6 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3">
        <AnimatePresence>
          {filteredProfiles.map((profile) => (
            <ProfileCard key={profile.id} profile={profile} />
          ))}
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <>
      <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <User className="mr-3 h-8 w-8 text-primary" />
              Mis Perfiles
              <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
                <Info className="h-4 w-4" />
              </Button>
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 px-2 md:px-4">
                  <span className="hidden md:inline">Acciones</span> <MoreHorizontal className="md:ml-2 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[180px]">
                <DropdownMenuItem onClick={() => { setEditingProfile(null); setIsProfileDialogOpen(true); }}>
                  <Plus className="mr-2 h-4 w-4" />
                  Nuevo Perfil
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setCategoryView(!categoryView)}> {/* NEW */}
                  {categoryView ? "Vista General" : "Vista por Categoría"}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <div className="mb-8 relative">
          <Input
            type="text"
            placeholder="Buscar perfiles por nombre, email, teléfono o etiquetas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2 border rounded-md w-full"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        </div>

        {renderProfiles()}

        <ProfileDialog
          isOpen={isProfileDialogOpen}
          onOpenChange={setIsProfileDialogOpen}
          profile={editingProfile}
          onSaveSuccess={handleSaveSuccess}
        />
        
        <AlertDialog open={!!deletingProfile} onOpenChange={(open) => !open && setDeletingProfile(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
              <AlertDialogDescription>
                Esta acción es irreversible y eliminará el perfil permanentemente.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={handleDeleteConfirm} className="bg-destructive hover:bg-destructive/90">Sí, eliminar</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Módulo de Perfiles</SheetTitle>
            <SheetDescription className="text-sm text-muted-foreground">
              Gestiona y organiza la información de tus contactos y las interacciones que tienes con ellos.
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué puedes hacer en tus Perfiles?</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Crear y Editar Perfiles:</strong> Registra y actualiza la información de tus contactos, incluyendo nombre, email, teléfono, etiquetas y campos personalizados.</li>
              <li><strong>Categorizar Perfiles:</strong> Organiza tus contactos por categorías para una gestión más sencilla.</li>
              <li><strong>Vinculación Inteligente:</strong> Conecta perfiles con notas, eventos y otros elementos para tener una visión 360 de tus interacciones.</li>
              <li><strong>Gestión de Perfiles:</strong> Edita, elimina y visualiza tus perfiles de contacto fácilmente.</li>
            </ul>

            <p><strong>Interacción con IA:</strong></p>
            <p>Además de la gestión manual, puedes interactuar con tus perfiles a través del chat de IA. Los perfiles se integran a la "memoria" de Kognito, enriqueciendo sus respuestas por relevancia con la consulta. La IA dispone de herramientas especializadas para:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Buscar y recuperar información de contactos.</li>
              <li>Crear y actualizar perfiles de contacto.</li>
              <li>Vincular eventos y notas a perfiles específicos.</li>
              <li>Generar resúmenes de interacciones con un contacto.</li>
            </ul>

            <p><strong>Beneficios Clave:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Centralización de Contactos:</strong> Toda la información de tus contactos en un solo lugar.</li>
              <li><strong>Contexto Completo:</strong> Accede rápidamente a notas, eventos y otras interacciones relacionadas con cada perfil.</li>
              <li><strong>Organización Eficiente:</strong> Categoriza y filtra tus contactos para una búsqueda rápida.</li>
              <li><strong>Potenciado por IA:</strong> Utiliza la IA para gestionar y analizar tus relaciones de forma proactiva.</li>
            </ul>

            <p>¡Optimiza tus relaciones y la gestión de tus contactos con el Módulo de Perfiles!</p>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}

const CategoryDropZone = ({ category, children, updateProfileCategory }: { category: string; children: React.ReactNode; updateProfileCategory: (profileId: string, newCategory: string) => void }) => { // NEW COMPONENT
  const [{ isOver }, drop] = useDrop({
    accept: 'PROFILE',
    drop: (item: { id: string; category: string | null }) => {
      if (item.category !== category) {
        updateProfileCategory(item.id, category);
      }
    },
    collect: monitor => ({
      isOver: !!monitor.isOver(),
    }),
  });

  return (
    <div ref={drop as any} className="p-4 rounded-lg" style={{ backgroundColor: isOver ? 'rgba(147, 112, 219, 0.1)' : 'transparent' }}>
      <h2 className="text-xl font-semibold mb-4 px-2">{category}</h2>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
        {children}
      </div>
    </div>
  );
};
