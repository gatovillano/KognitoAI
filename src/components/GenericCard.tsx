'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { MoreHorizontal, Edit, Trash2, Link as LinkIcon } from 'lucide-react';

interface GenericCardProps {
  href?: string;
  icon?: React.ElementType;
  title: string;
  description?: string;
  footerContent?: React.ReactNode;
  actions?: {
    label: string;
    icon: React.ElementType;
    onClick: (e: React.MouseEvent) => void;
  }[];
  className?: string;
  onClick?: () => void;
}

export const GenericCard = ({
  href,
  icon: Icon,
  title,
  description,
  footerContent,
  actions = [],
  className,
  onClick,
}: GenericCardProps) => {
  const cardContent = (
    <Card
      className={`h-full hover:bg-card/60 ${className || ''}`}
      onClick={onClick}
    >
      {/* Efecto de resplandor en el hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      <CardHeader className="pb-3 relative z-10">
        <CardTitle className="flex items-start gap-3 flex-wrap overflow-hidden">
          <div className="flex items-center gap-3 min-w-0">
            {Icon && (
              <div className="p-3 rounded-2xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500 flex-shrink-0">
                <Icon className="h-5 w-5 text-primary" />
              </div>
            )}
            <span className="font-bold text-lg whitespace-normal break-words flex-shrink min-w-0 text-wrap group-hover:text-primary transition-colors leading-tight tracking-tight">
              {title}
            </span>
          </div>
          {actions.length > 0 && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 p-0 hover:bg-muted"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                  {actions.map((action, index) => (
                    <DropdownMenuItem key={index} onClick={action.onClick}>
                      <action.icon className="mr-2 h-4 w-4" />
                      <span>{action.label}</span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 flex-grow relative z-10">
        {description && (
          <p className="text-xs text-muted-foreground/80 line-clamp-3 leading-relaxed font-medium">
            {description}
          </p>
        )}
      </CardContent>
      {footerContent && (
        <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50 relative z-10">
          {footerContent}
        </CardFooter>
      )}
    </Card>
  );

  return href ? (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.3 }}
      className="h-full w-full"
    >
      <Link href={href} className="h-full block">
        {cardContent}
      </Link>
    </motion.div>
  ) : (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.3 }}
      className="h-full w-full"
    >
      {cardContent}
    </motion.div>
  );
};
