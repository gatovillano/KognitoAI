import React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface InteractiveTagProps {
    label: string;
    type: 'theme' | 'concept';
    onClick?: () => void;
    className?: string;
}

export const InteractiveTag: React.FC<InteractiveTagProps> = ({
    label,
    type,
    onClick,
    className
}) => {
    const isTheme = type === 'theme';

    return (
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger asChild>
                    <Badge
                        variant="outline"
                        onClick={onClick}
                        className={cn(
                            "cursor-pointer transition-all duration-300 py-1.5 px-3 border-2",
                            "hover:scale-105 active:scale-95 shadow-sm hover:shadow-md",
                            isTheme
                                ? "bg-indigo-50/50 border-indigo-200 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/20 dark:border-indigo-800 dark:text-indigo-300"
                                : "bg-emerald-50/50 border-emerald-200 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-300",
                            className
                        )}
                    >
                        <span className="flex items-center gap-1.5">
                            <span className={cn(
                                "w-1.5 h-1.5 rounded-full animate-pulse",
                                isTheme ? "bg-indigo-500" : "bg-emerald-500"
                            )} />
                            {label}
                        </span>
                    </Badge>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="bg-popover/95 backdrop-blur-sm border shadow-xl">
                    <p className="text-xs font-medium">Click para ver detalles y citas</p>
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
};
