// src/app/(dashboard)/agenda/ReminderDialog.tsx
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
import { Bell, Clock, MessageSquare, Activity, X } from 'lucide-react';
import apiClient from '@/lib/api';

const formSchema = z.object({
  time_before: z.number().min(0, "El tiempo antes debe ser un número positivo."),
  time_unit: z.enum(['minutes', 'hours', 'days']),
  message: z.string().optional(),
});

interface ReminderDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  eventId: number;
  onSaveSuccess: () => void;
}

export function ReminderDialog({ isOpen, onOpenChange, eventId, onSaveSuccess }: ReminderDialogProps) {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      time_before: 30,
      time_unit: 'minutes',
      message: '',
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const toastId = toast.loading('Configurando recordatorio...');
    try {
      console.log("Valores del recordatorio a guardar:", values);
      console.log("ID del evento asociado:", eventId);

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
      <DialogContent className="sm:max-w-[450px] bg-white/80 dark:bg-card/40 backdrop-blur-2xl border-white/20 dark:border-border/40 rounded-[2.5rem] shadow-2xl overflow-hidden p-0">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

        <DialogHeader className="p-8 pb-4 relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-primary/10 text-primary shadow-inner">
              <Bell className="h-6 w-6" />
            </div>
            <DialogTitle className="text-3xl font-black tracking-tighter bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              Recordatorio
            </DialogTitle>
          </div>
          <DialogDescription className="text-muted-foreground font-medium">
            Configura una alerta para no perderte nada importante.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="p-8 pt-0 space-y-6 relative z-10">
            <div className="grid grid-cols-2 gap-6">
              <FormField
                control={form.control}
                name="time_before"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                      <Clock className="h-3.5 w-3.5 text-primary" /> Tiempo
                    </FormLabel>
                    <FormControl>
                      <Input type="number" {...field} onChange={e => field.onChange(Number(e.target.value))} className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all font-bold" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="time_unit"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                      <Activity className="h-3.5 w-3.5 text-primary" /> Unidad
                    </FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all">
                          <SelectValue placeholder="Unidad" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent className="rounded-2xl bg-card/95 backdrop-blur-xl border-border/40">
                        <SelectItem value="minutes" className="rounded-xl">Minutos</SelectItem>
                        <SelectItem value="hours" className="rounded-xl">Horas</SelectItem>
                        <SelectItem value="days" className="rounded-xl">Días</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="message"
              render={({ field }) => (
                <FormItem className="space-y-2">
                  <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                    <MessageSquare className="h-3.5 w-3.5 text-primary" /> Mensaje (Opcional)
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="No olvides la reunión..." {...field} className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all font-medium" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter className="pt-4">
              <Button type="submit" disabled={form.formState.isSubmitting} className="w-full h-14 rounded-2xl bg-primary shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all font-black uppercase tracking-widest text-xs gap-3">
                {form.formState.isSubmitting ? (
                  <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Bell className="h-5 w-5" />
                )}
                {form.formState.isSubmitting ? 'Guardando...' : 'Configurar Alerta'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}