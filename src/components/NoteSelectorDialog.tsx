'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, FileText } from 'lucide-react';
import { toast } from 'sonner';

interface Note {
  id: number;
  title?: string;
  content: string;
  category?: string;
  created_at: string;
  updated_at: string;
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string;
}

interface NoteSelectorDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectNote: (note: Note) => void;
  workspaceId?: string;
}

const NoteSelectorDialog: React.FC<NoteSelectorDialogProps> = ({
  isOpen,
  onClose,
  onSelectNote,
  workspaceId,
}) => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const fetchNotes = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/notes/list-notes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
        },
        body: JSON.stringify({
          search_term: searchTerm,
          workspace_id: workspaceId,
          skip: 0,
          limit: 100, // Adjust limit as needed
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setNotes(data.notes);
    } catch (error) {
      console.error('Error fetching notes:', error);
      toast.error('Error al cargar las notas.');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, workspaceId]);

  useEffect(() => {
    if (isOpen) {
      fetchNotes();
    }
  }, [isOpen, fetchNotes]);

  const handleSelect = (note: Note) => {
    onSelectNote(note);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Seleccionar Nota</DialogTitle>
          <DialogDescription>
            Busca y selecciona una nota para adjuntarla a tu mensaje.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <Input
            placeholder="Buscar notas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                fetchNotes();
              }
            }}
          />
          {loading ? (
            <div className="flex justify-center items-center h-32">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <ScrollArea className="h-72 w-full rounded-md border">
              {notes.length === 0 ? (
                <p className="p-4 text-center text-muted-foreground">No se encontraron notas.</p>
              ) : (
                <div className="p-2">
                  {notes.map((note) => (
                    <Button
                      key={note.id}
                      variant="ghost"
                      className="w-full justify-start text-left h-auto py-2 px-3 mb-1"
                      onClick={() => handleSelect(note)}
                    >
                      <FileText className="mr-2 h-4 w-4 text-muted-foreground" />
                      <div className="flex flex-col items-start">
                        <span className="font-medium">{note.title || 'Sin título'}</span>
                        <span className="text-xs text-muted-foreground truncate w-full">
                          {note.content.substring(0, 100)}...
                        </span>
                      </div>
                    </Button>
                  ))}
                </div>
              )}
            </ScrollArea>
          )}
        </div>
        <div className="flex justify-end">
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default NoteSelectorDialog;