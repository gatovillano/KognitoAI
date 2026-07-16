"use client";

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  User, Brain, Sparkles, Wrench,
  Puzzle, Zap, ShieldCheck, Globe,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUserSettings } from '@/contexts/UserSettingsContext';

export const SETTINGS_MENU = [
  { id: 'personal-data', label: 'Datos Personales', icon: User },
  { id: 'ai-profile', label: 'Perfil de IA', icon: Brain },
  { id: 'llm-config', label: 'Modelos e IA', icon: Sparkles },
  { id: 'modules-preferences', label: 'Módulos y Preferencias', icon: Wrench },
  { id: 'memories', label: 'Memorias', icon: Brain },
  { id: 'skills', label: 'Skills', icon: Puzzle },
  { id: 'heartbeat', label: 'Heartbeat Autónomo', icon: Zap },
  { id: 'security', label: 'Seguridad', icon: ShieldCheck },
  { id: 'remote', label: 'Acceso Remoto / SSH', icon: Globe },
  { id: 'sync', label: 'Sincronización', icon: RefreshCw },
  { id: 'integrations', label: 'Integraciones', icon: Puzzle },
];

interface SettingsNavProps {
  activeTab: string;
  setActiveTab: (value: string) => void;
  isMobile?: boolean;
}

export const SettingsNav: React.FC<SettingsNavProps> = ({ activeTab, setActiveTab, isMobile }) => {
  return (
    <div className={cn(
      "flex flex-col gap-1 p-2",
      isMobile && "w-full"
    )}>
      {SETTINGS_MENU.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;

        return (
          <Button
            key={item.id}
            variant="ghost"
            className={cn(
              "justify-start gap-3 px-3 py-6 rounded-lg transition-all duration-200",
              isActive
                ? "bg-primary/10 text-primary font-medium hover:bg-primary/15"
                : "text-muted-foreground hover:text-foreground hover:bg-accent"
            )}
            onClick={() => setActiveTab(item.id)}
          >
            <Icon className={cn("h-5 w-5", isActive ? "text-primary" : "text-muted-foreground")} />
            <span className="text-sm">{item.label}</span>
          </Button>
        );
      })}
    </div>
  );
};
