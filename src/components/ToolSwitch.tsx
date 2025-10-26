import React from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

interface ToolSwitchProps {
  label?: string; // Hacemos la etiqueta opcional
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
}

export const ToolSwitch: React.FC<ToolSwitchProps> = ({ label, checked, onCheckedChange, disabled }) => {
  const id = `tool-switch-${label ? label.replace(/\s+/g, '-').toLowerCase() : 'unlabeled'}`;
  return (
    <div className="flex items-center justify-between space-x-2 py-2 px-3">
      {label && ( // Solo renderizamos la etiqueta si existe
        <Label htmlFor={id} className="flex-grow text-sm font-medium cursor-pointer">
          {label}
        </Label>
      )}
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        disabled={disabled}
      />
    </div>
  );
};