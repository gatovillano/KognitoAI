'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { useEffect, useState, useCallback } from 'react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { FileText, Calendar, User, Loader2, CheckSquare } from 'lucide-react';

export interface TaggedObject {
  id: string | number;
  title: string;
  type: 'note' | 'event' | 'profile' | 'task';
}

interface ObjectTagSelectorDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  initialSelected?: TaggedObject[];
  onSave: (selected: TaggedObject[]) => void;
}

export function ObjectTagSelectorDialog({
  isOpen,
  onOpenChange,
  initialSelected = [],
  onSave,
}: ObjectTagSelectorDialogProps) {
  const [activeTab, setActiveTab] = useState('profiles');
  const [selected, setSelected] = useState<TaggedObject[]>([]);
  const [availableNotes, setAvailableNotes] = useState<TaggedObject[]>([]);
  const [availableEvents, setAvailableEvents] = useState<TaggedObject[]>([]);
  const [availableProfiles, setAvailableProfiles] = useState<TaggedObject[]>([]);
  const [availableTasks, setAvailableTasks] = useState<TaggedObject[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchAvailableObjects = useCallback(async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Notes
      const notesResponse = await apiClient.post('/api/notes/list-notes', { search_term: '' });
      const notesData: TaggedObject[] = (notesResponse.data.notes || []).map((note: any) => ({
        id: note.id,
        title: note.title || note.content.substring(0, 50) + '...',
        type: 'note' as const,
      }));
      setAvailableNotes(notesData);

      // 2. Fetch Events
      const eventsResponse = await apiClient.post('/api/list-events', {});
      const eventsData: TaggedObject[] = (eventsResponse.data || []).map((event: any) => ({
        id: event.id,
        title: event.summary || 'Evento sin título',
        type: 'event' as const,
      }));
      setAvailableEvents(eventsData);

      // 3. Fetch Profiles
      const profilesResponse = await apiClient.get('/api/contact-profiles');
      const profilesData: TaggedObject[] = (profilesResponse.data || []).map((profile: any) => ({
        id: profile.id,
        title: profile.name || 'Contacto sin nombre',
        type: 'profile' as const,
      }));
      setAvailableProfiles(profilesData);

      // 4. Fetch Tasks
      const tasksResponse = await apiClient.get('/api/tasks');
      const tasksData: TaggedObject[] = (tasksResponse.data || []).map((task: any) => ({
        id: task.id,
        title: task.description || 'Tarea sin descripción',
        type: 'task' as const,
      }));
      setAvailableTasks(tasksData);
    } catch (error) {
      toast.error('Error al cargar los objetos disponibles.');
      console.error('Error fetching available objects:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      setSelected(Array.isArray(initialSelected) ? initialSelected : []);
      fetchAvailableObjects();
    } else {
      setAvailableNotes([]);
      setAvailableEvents([]);
      setAvailableProfiles([]);
      setAvailableTasks([]);
      setSearchTerm('');
    }
  }, [isOpen, initialSelected, fetchAvailableObjects]);

  const isSelected = (id: string | number, type: 'note' | 'event' | 'profile' | 'task') => {
    return selected.some(item => item.id === id && item.type === type);
  };

  const handleToggle = (id: string | number, title: string, type: 'note' | 'event' | 'profile' | 'task') => {
    setSelected(prev => {
      if (isSelected(id, type)) {
        return prev.filter(item => !(item.id === id && item.type === type));
      } else {
        return [...prev, { id, title, type }];
      }
    });
  };

  const handleConfirmSelection = () => {
    onSave(selected);
    onOpenChange(false);
  };

  const filterItems = (items: TaggedObject[]) => {
    return items.filter(item =>
      item.title && item.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const renderItemList = (items: TaggedObject[], icon: React.ReactNode) => (
    <ScrollArea className="h-[300px] w-full rounded-md border p-4">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center h-48">
          <Loader2 className="h-6 w-6 animate-spin text-primary mb-2" />
          <p className="text-sm text-muted-foreground">Cargando...</p>
        </div>
      ) : filterItems(items).length === 0 ? (
        <p className="text-center text-muted-foreground py-10">No se encontraron elementos.</p>
      ) : (
        <div className="space-y-2">
          {filterItems(items).map((item) => {
            const checked = isSelected(item.id, item.type);
            return (
              <div key={`${item.type}-${item.id}`} className="flex items-center justify-between p-1.5 rounded hover:bg-muted/50 transition-colors">
                <label
                  htmlFor={`item-${item.type}-${item.id}`}
                  className="flex items-center space-x-3 cursor-pointer w-full select-none"
                >
                  <Checkbox
                    id={`item-${item.type}-${item.id}`}
                    checked={checked}
                    onCheckedChange={() => handleToggle(item.id, item.title, item.type)}
                  />
                  <span className="text-muted-foreground flex-shrink-0">{icon}</span>
                  <span className="text-sm font-medium leading-none">{item.title}</span>
                </label>
              </div>
            );
          })}
        </div>
      )}
    </ScrollArea>
  );

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[95vh] flex flex-col gap-4">
        <DialogHeader>
          <DialogTitle>Vincular Objetos</DialogTitle>
          <DialogDescription>
            Busca y selecciona los perfiles, notas y eventos que deseas etiquetar en esta casilla.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 flex-1 overflow-hidden">
          <Input
            placeholder="Buscar..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full"
          />

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full flex-1 flex flex-col">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="profiles" className="gap-2">
                <User className="h-4 w-4" /> Perfiles
              </TabsTrigger>
              <TabsTrigger value="notes" className="gap-2">
                <FileText className="h-4 w-4" /> Notas
              </TabsTrigger>
              <TabsTrigger value="events" className="gap-2">
                <Calendar className="h-4 w-4" /> Eventos
              </TabsTrigger>
              <TabsTrigger value="tasks" className="gap-2">
                <CheckSquare className="h-4 w-4" /> Tareas
              </TabsTrigger>
            </TabsList>
            
            <div className="mt-4 flex-1">
              <TabsContent value="profiles" className="m-0">
                {renderItemList(availableProfiles, <User className="h-4 w-4 text-purple-500" />)}
              </TabsContent>
              <TabsContent value="notes" className="m-0">
                {renderItemList(availableNotes, <FileText className="h-4 w-4 text-blue-500" />)}
              </TabsContent>
              <TabsContent value="events" className="m-0">
                {renderItemList(availableEvents, <Calendar className="h-4 w-4 text-emerald-500" />)}
              </TabsContent>
              <TabsContent value="tasks" className="m-0">
                {renderItemList(availableTasks, <CheckSquare className="h-4 w-4 text-orange-500" />)}
              </TabsContent>
            </div>
          </Tabs>
        </div>

        <DialogFooter className="border-t pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleConfirmSelection}>
            Aceptar ({selected.length})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
