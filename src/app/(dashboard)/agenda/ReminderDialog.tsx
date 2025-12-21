// En: src/app/(dashboard)/agenda/ReminderDialog.tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import apiClient from '@/lib/api';

const formSchema = z.object({
  time_before: z.number().min(0, "El tiempo antes debe ser un número positivo."),
  time_unit: z.enum(['minutes', 'hours', 'days']),
  message: z.string().optional(),
});

interface ReminderDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  eventId: number; // El ID del evento al que se asociará el recordatorio
  onSaveSuccess: () => void;
}

export function ReminderDialog({ isOpen, onOpenChange, eventId, onSaveSuccess }: ReminderDialogProps) {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      time_before: 30, // 30 minutos por defecto
      time_unit: 'minutes',
      message: '',
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const toastId = toast.loading('Configurando recordatorio...');
    try {
      // Aquí deberías llamar a tu API para guardar el recordatorio
      // Aún no hemos creado el endpoint, así que esto es un placeholder
      console.log("Valores del recordatorio a guardar:", values);
      console.log("ID del evento asociado:", eventId);

      // Simular llamada a API
      await new Promise(resolve => setTimeout(resolve, 1000)); 

      toast.success('¡Recordatorio configurado!', { id: toastId });
      onSaveSuccess();
      onOpenChange(false);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Error al configurar el recordatorio.';
      toast.error(errorMessage, { id: toastId });
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Configurar Recordatorio</DialogTitle>
          <DialogDescription>
            Configura un recordatorio para este evento.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="time_before"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Recordar antes</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} onChange={e => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="time_unit"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Unidad de tiempo</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona una unidad" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="minutes">Minutos</SelectItem>
                      <SelectItem value="hours">Horas</SelectItem>
                      <SelectItem value="days">Días</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Mensaje del recordatorio (opcional)</FormLabel>
                  <FormControl>
                    <Input placeholder="No olvides la reunión..." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? 'Guardando...' : 'Guardar Recordatorio'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}