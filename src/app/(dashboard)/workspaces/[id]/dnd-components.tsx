
'use client';

import { useDrag, useDrop } from 'react-dnd';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { MoreVertical, Notebook, Trash2, Edit } from 'lucide-react';
import { Note } from '../../notes/page';

export const ItemTypes = {
  NOTE: 'note',
};

interface DraggableNoteCardProps {
  note: Note;
  handleNoteClick: (note: Note) => void;
  handleDeleteNote: (noteId: number) => void;
  setSelectedNote: (note: Note) => void;
  setIsNoteDialogOpen: (isOpen: boolean) => void;
}

export const DraggableNoteCard = ({ note, handleNoteClick, handleDeleteNote, setSelectedNote, setIsNoteDialogOpen }: DraggableNoteCardProps) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: ItemTypes.NOTE,
    item: { id: note.id, category: note.category },
    collect: (monitor) => ({
      isDragging: !!monitor.isDragging(),
    }),
  }));

  return (
    <div ref={drag as any} style={{ opacity: isDragging ? 0.5 : 1 }}>
      <Card
        className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20"
        onClick={() => handleNoteClick(note)}
      >
        <CardHeader className="pb-3">
          <CardTitle className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center flex-shrink-0">
                <Notebook className="h-5 w-5 text-yellow-600" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-sm line-clamp-2">
                  {note.title || 'Nota sin título'}
                </div>
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={(e) => {
                  e.stopPropagation();
                  setSelectedNote(note); // Set the note for editing
                  setIsNoteDialogOpen(true); // Open the edit dialog
                }}>
                  <Edit className="mr-2 h-4 w-4" />
                  Editar Nota
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleNoteClick(note); }}>
                  <Notebook className="mr-2 h-4 w-4" />
                  Ver Nota
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeleteNote(note.id); }} className="text-destructive">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Eliminar Nota
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
            {note.content}
          </p>
          <div className="flex items-center justify-between pt-2 border-t border-border/50">
            <span className="text-xs text-muted-foreground">
              {note.category}
            </span>
            <span className="text-xs text-muted-foreground">
              {new Date(note.created_at).toLocaleDateString()}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

interface CategoryColumnProps {
  category: string;
  children: React.ReactNode;
  onDropNote: (noteId: number, newCategory: string) => void;
}

export const CategoryColumn = ({ category, children, onDropNote }: CategoryColumnProps) => {
  const [{ isOver }, drop] = useDrop(() => ({
    accept: ItemTypes.NOTE,
    drop: (item: { id: number; category: string }) => {
      if (item.category !== category) {
        onDropNote(item.id, category);
      }
    },
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
    }),
  }));

  return (
    <div
      ref={drop as any}
      className="p-4 rounded-lg min-h-[200px]"
      style={{ backgroundColor: isOver ? 'rgba(147, 112, 219, 0.1)' : 'transparent' }}
    >
      <h2 className="text-xl font-semibold mb-4 px-2">{category}</h2>
      <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-1 xl:grid-cols-1">
        {children}
      </div>
    </div>
  );
};
