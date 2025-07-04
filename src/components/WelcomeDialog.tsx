'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { HelpCarousel } from './HelpCarousel';

interface WelcomeDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

export function WelcomeDialog({ isOpen, onOpenChange }: WelcomeDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[525px] h-[450px] flex flex-col">
        <DialogHeader className="text-center">
          <DialogTitle className="text-2xl font-bold">¡Bienvenido a KAI!</DialogTitle>
          <DialogDescription>
            Aquí tienes un resumen rápido de todo lo que puedes hacer.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-grow min-h-0">
          <HelpCarousel />
        </div>
      </DialogContent>
    </Dialog>
  );
}
