'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RefreshCcw } from 'lucide-react';

interface DashboardSliderCardProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  data: any[];
  emptyMessage: string;
  lastUpdate: Date;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function DashboardSliderCard({
  title,
  icon,
  children,
  data,
  emptyMessage,
  lastUpdate,
  onRefresh,
  isRefreshing,
}: DashboardSliderCardProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {icon}
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-3">{emptyMessage}</p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              Última actualización: {lastUpdate.toLocaleTimeString()}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              <RefreshCcw className={`h-3 w-3 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return <>{children}</>;
}