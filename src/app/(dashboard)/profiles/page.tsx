/* eslint-disable react/jsx-no-undef */
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input'; // Importar Input
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, User, Edit, Trash2, MoreHorizontal, Info, Mail, Phone, Search, ExternalLink, Bot } from 'lucide-react'; // Importar Search, ExternalLink y Bot
import { motion, AnimatePresence } from 'framer-motion';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'; // Importar Sheet
import { useDrag, useDrop } from 'react-dnd';

import { useRouter } from 'next/navigation';
import { ProfileDialog } from './profile-dialog';
import { ProfileDetailDialog } from './profile-detail-dialog';

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

export default function ProfilesPage({ isEmbedded = false }: { isEmbedded?: boolean }) {
  const [profiles, setProfiles] = useState<ContactProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [categoryView, setCategoryView] = useState(false); // NEW
  const [editingProfile, setEditingProfile] = useState<ContactProfile | null>(null);
  const [deletingProfile, setDeletingProfile] = useState<ContactProfile | null>(null);
  const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Nuevo estado para controlar la visibilidad del Sheet
  const [searchTerm, setSearchTerm] = useState(''); // Estado para el término de búsqueda
  const [viewingProfileId, setViewingProfileId] = useState<string | null>(null);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);

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
          className="cursor-pointer flex flex-col h-full min-h-[200px] hover:border-primary/20"
          style={{ opacity: isDragging ? 0.5 : 1 }}
          onClick={() => {
            setViewingProfileId(profile.id);
            setIsDetailDialogOpen(true);
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
                  className="h-8 w-8 p-0 hover:bg-primary hover:text-primary-foreground"
                  onClick={(e) => { e.stopPropagation(); router.push(`/profiles/${profile.id}`); }}
                  title="Ver página completa"
                >
                  <ExternalLink className="h-4 w-4" />
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
      return <p className="text-center py-10">Cargando contactos...</p>;
    }

    if (profiles.length === 0) {
      return (
        <div className="text-center py-16">
          <User className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No tienes contactos aún</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Crea contactos y organiza su información de manera inteligente.
          </p>
          <Button onClick={() => { setEditingProfile(null); setIsProfileDialogOpen(true); }} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            Crear tu primer Contacto
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
      <div className={isEmbedded ? "space-y-6" : "p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden"}>
        {!isEmbedded ? (
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold flex items-center">
                <User className="mr-3 h-8 w-8 text-primary" />
                Mis Contactos
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
                    Nuevo Contacto
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => setCategoryView(!categoryView)}> {/* NEW */}
                    {categoryView ? "Vista General" : "Vista por Categoría"}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black uppercase tracking-widest text-muted-foreground/70">Mis Contactos</h2>
              <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
                <Info className="h-4 w-4" />
              </Button>
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
                    Nuevo Contacto
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => setCategoryView(!categoryView)}> {/* NEW */}
                    {categoryView ? "Vista General" : "Vista por Categoría"}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        )}
        <div className="mb-8 relative">
          <Input
            type="text"
            placeholder="Buscar contactos por nombre, email, teléfono o etiquetas..."
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

        <ProfileDetailDialog
          isOpen={isDetailDialogOpen}
          onOpenChange={setIsDetailDialogOpen}
          profileId={viewingProfileId}
          onEdit={(profile) => {
            setIsDetailDialogOpen(false);
            setEditingProfile(profile);
            setIsProfileDialogOpen(true);
          }}
        />

        <AlertDialog open={!!deletingProfile} onOpenChange={(open) => !open && setDeletingProfile(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
              <AlertDialogDescription>
                {`Esta acción es irreversible y eliminará el perfil permanentemente.`}
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
        <SheetContent side="right" className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="pb-6 border-b">
            <SheetTitle className="text-2xl font-bold flex items-center gap-2">
              <User className="h-6 w-6 text-primary" />
              Guía de Perfiles
            </SheetTitle>
            <SheetDescription>
              Gestión estratégica de relaciones y contactos.
            </SheetDescription>
          </SheetHeader>
          
          <div className="py-6 space-y-8">
            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">CRM Inteligente</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Organiza tu red de contactos mediante <strong>Categorías</strong> y <strong>Etiquetas</strong> personalizadas. El módulo de perfiles está diseñado para ofrecerte una visión completa de cada persona con la que interactúas.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Inteligencia de Relaciones (IA)</h3>
              <div className="bg-primary/5 rounded-2xl p-4 border border-primary/10 space-y-3">
                <p className="text-xs font-medium text-primary flex items-center gap-2">
                  <Bot className="h-4 w-4" /> El Agente puede ayudarte a:
                </p>
                <ul className="text-xs space-y-2 text-muted-foreground list-disc pl-4">
                  <li><strong>Resumir interacciones</strong> antes de una reunión importante.</li>
                  <li><strong>Recordar detalles clave</strong> mencionados en notas o chats previos vinculados al perfil.</li>
                  <li><strong>Sugerir seguimientos</strong> basados en la fecha de la última actualización.</li>
                  <li><strong>Extraer información de contacto</strong> automáticamente desde correos o documentos.</li>
                </ul>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Vinculación Contextual</h3>
              <div className="grid grid-cols-1 gap-2 text-[11px]">
                <div className="flex items-center gap-2 p-3 rounded-xl bg-blue-500/5 text-blue-600 border border-blue-500/10">
                  <span className="font-bold">NOTES</span> Accede a todas las notas asociadas a este contacto desde su perfil.
                </div>
                <div className="flex items-center gap-2 p-3 rounded-xl bg-green-500/5 text-green-600 border border-green-500/10">
                  <span className="font-bold">EVENTS</span> Consulta próximas reuniones y el historial de encuentros.
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Personalización</h3>
              <p className="text-sm text-muted-foreground leading-relaxed italic">
                "Usa los campos personalizados para guardar datos específicos como cumpleaños, preferencias de comunicación o roles corporativos."
              </p>
            </section>
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
