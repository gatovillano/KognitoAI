'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { DashboardHelpCarousel } from './DashboardHelpCarousel';

interface WelcomeDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

export function WelcomeDialog({ isOpen, onOpenChange }: WelcomeDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] md:max-w-[700px] lg:max-w-[800px] max-h-[90vh] flex flex-col">
        <DialogHeader className="text-center">
          <DialogTitle className="text-2xl font-bold">¡Bienvenido a Kognito!</DialogTitle>
          <DialogDescription>
            Un tour rápido por tus nuevas capacidades.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-grow min-h-0 -mx-6 -mb-6">
            <DashboardHelpCarousel />
        </div>
      </DialogContent>
    </Dialog>
  );
}
