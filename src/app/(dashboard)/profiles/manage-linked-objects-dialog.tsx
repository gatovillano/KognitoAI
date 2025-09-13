'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { useEffect, useState } from 'react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContactProfile } from './page'; // Importar la interfaz ContactProfile

interface ManageLinkedObjectsDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  profile: ContactProfile | null;
  onLinkedObjectsUpdated: () => void; // Callback para refrescar los objetos vinculados en el ViewProfileDialog
}

interface LinkedObjectDisplay {
  id: string | number;
  title: string;
  type: 'note' | 'event' | 'task' | 'collection';
  linked: boolean;
}

export function ManageLinkedObjectsDialog({ isOpen, onOpenChange, profile, onLinkedObjectsUpdated }: ManageLinkedObjectsDialogProps) {
  const [activeTab, setActiveTab] = useState('notes');
  const [availableNotes, setAvailableNotes] = useState<LinkedObjectDisplay[]>([]);
  const [availableEvents, setAvailableEvents] = useState<LinkedObjectDisplay[]>([]);
  const [availableTasks, setAvailableTasks] = useState<LinkedObjectDisplay[]>([]);
  const [availableCollections, setAvailableCollections] = useState<LinkedObjectDisplay[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen && profile?.id) {
      fetchAvailableObjects();
    } else if (!isOpen) {
      // Limpiar estados al cerrar el diálogo
      setAvailableNotes([]);
      setAvailableEvents([]);
      setAvailableTasks([]);
      setAvailableCollections([]);
      setSearchTerm('');
    }
  }, [isOpen, profile?.id]);

  const fetchAvailableObjects = async () => {
    setIsLoading(true);
    try {
      // Fetch linked objects first to mark them as linked
      const linkedResponse = await apiClient.get(`/api/contact-profiles/${profile?.id}/linked-objects`);
      const linkedData = linkedResponse.data;

      // Fetch all notes
      const notesResponse = await apiClient.post('/api/list-notes', { search_term: '' });
      const allNotes: LinkedObjectDisplay[] = notesResponse.data.map((note: any) => ({
        id: note.id,
        title: note.title || note.content.substring(0, 50) + '...',
        type: 'note',
        linked: linkedData.notes.some((linkedNote: any) => linkedNote.id === note.id),
      }));
      setAvailableNotes(allNotes);

      // Fetch all events
      const eventsResponse = await apiClient.post('/api/list-events');
      const allEvents: LinkedObjectDisplay[] = eventsResponse.data.map((event: any) => ({
        id: event.id,
        title: event.description,
        type: 'event',
        linked: linkedData.agenda_events.some((linkedEvent: any) => linkedEvent.id === event.id),
      }));
      setAvailableEvents(allEvents);

      // Fetch all tasks
      const tasksResponse = await apiClient.get('/api/tasks');
      const allTasks: LinkedObjectDisplay[] = tasksResponse.data.map((task: any) => ({
        id: task.id,
        title: task.description,
        type: 'task',
        linked: linkedData.tasks.some((linkedTask: any) => linkedTask.id === task.id),
      }));
      setAvailableTasks(allTasks);

      // Fetch all collections
      const collectionsResponse = await apiClient.get('/api/collections');
      const allCollections: LinkedObjectDisplay[] = collectionsResponse.data.map((collection: any) => ({
        id: collection.id,
        title: collection.name,
        type: 'collection',
        linked: linkedData.user_document_topics.some((linkedCollection: any) => linkedCollection.id === collection.id),
      }));
      setAvailableCollections(allCollections);

    } catch (error) {
      toast.error('Error al cargar objetos disponibles.');
      console.error('Error fetching available objects:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleLink = async (item: LinkedObjectDisplay) => {
    if (!profile?.id) return;

    const endpointMap = {
      note: { link: '/api/notes/{id}/link-profile', unlink: '/api/notes/{id}/unlink-profile' },
      event: { link: '/api/agenda/events/{id}/link-profile', unlink: '/api/agenda/events/{id}/unlink-profile' },
      task: { link: '/api/tasks/{id}/link-profile', unlink: '/api/tasks/{id}/unlink-profile' },
      collection: { link: '/api/collections/{id}/link-profile', unlink: '/api/collections/{id}/unlink-profile' },
    };

    const currentEndpoint = endpointMap[item.type];
    const url = item.linked
      ? currentEndpoint.unlink.replace('{id}', String(item.id))
      : currentEndpoint.link.replace('{id}', String(item.id));

    try {
      await apiClient.post(url, { profile_id: profile.id });
      toast.success(`${item.title} ${item.linked ? 'desvinculado' : 'vinculado'} correctamente.`);
      // Refrescar la lista de objetos disponibles y los objetos vinculados en el ViewProfileDialog
      fetchAvailableObjects();
      onLinkedObjectsUpdated();
    } catch (error) {
      toast.error(`Error al ${item.linked ? 'desvincular' : 'vincular'} ${item.title}.`);
      console.error(`Error toggling link for ${item.type} ${item.id}:`, error);
    }
  };

  const filterItems = (items: LinkedObjectDisplay[]) => {
    return items.filter(item =>
      item.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const renderItemList = (items: LinkedObjectDisplay[]) => (
    <ScrollArea className="h-[300px] w-full rounded-md border p-4">
      {isLoading ? (
        <p className="text-center text-muted-foreground">Cargando...</p>
      ) : filterItems(items).length === 0 ? (
        <p className="text-center text-muted-foreground">No se encontraron elementos.</p>
      ) : (
        <div className="space-y-2">
          {filterItems(items).map((item) => (
            <div key={item.id} className="flex items-center justify-between">
              <label htmlFor={`item-${item.id}`} className="flex items-center space-x-2 cursor-pointer">
                <Checkbox
                  id={`item-${item.id}`}
                  checked={item.linked}
                  onCheckedChange={() => handleToggleLink(item)}
                />
                <span>{item.title}</span>
              </label>
            </div>
          ))}
        </div>
      )}
    </ScrollArea>
  );

  if (!profile) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Gestionar Vinculaciones para {profile.name || 'Perfil sin nombre'}</DialogTitle>
          <DialogDescription>
            Vincula o desvincula notas, eventos, tareas y colecciones a este perfil.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <Input
            placeholder="Buscar elementos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full"
          />

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="notes">Notas</TabsTrigger>
              <TabsTrigger value="events">Eventos</TabsTrigger>
              <TabsTrigger value="tasks">Tareas</TabsTrigger>
              <TabsTrigger value="collections">Colecciones</TabsTrigger>
            </TabsList>
            <TabsContent value="notes">{renderItemList(availableNotes)}</TabsContent>
            <TabsContent value="events">{renderItemList(availableEvents)}</TabsContent>
            <TabsContent value="tasks">{renderItemList(availableTasks)}</TabsContent>
            <TabsContent value="collections">{renderItemList(availableCollections)}</TabsContent>
          </Tabs>
        </div>

        <div className="flex justify-end">
          <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
