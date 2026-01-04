'use client';

import React, { useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Eye, GitMerge } from 'lucide-react';

interface NodeContextMenuProps {
  x: number;
  y: number;
  onDetails: () => void;
  onIsolate: () => void;
  onClose: () => void;
}

export const NodeContextMenu: React.FC<NodeContextMenuProps> = ({ x, y, onDetails, onIsolate, onClose }) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  return (
    <Card
      ref={menuRef}
      className="absolute z-50 w-48 p-1 animate-in fade-in zoom-in-95"
      style={{ top: y, left: x }}
    >
      <Button
        variant="ghost"
        className="w-full justify-start px-2 py-1.5 text-sm h-auto"
        onClick={() => { onDetails(); onClose(); }}
      >
        <Eye className="mr-2 h-4 w-4" />
        Ver Detalles
      </Button>
      <Separator />
      <Button
        variant="ghost"
        className="w-full justify-start px-2 py-1.5 text-sm h-auto"
        onClick={() => { onIsolate(); onClose(); }}
      >
        <GitMerge className="mr-2 h-4 w-4" />
        Aislar Relaciones
      </Button>
    </Card>
  );
};
