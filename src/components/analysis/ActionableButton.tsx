import React from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { HelpCircle, Zap, ArrowRight, Sparkles } from 'lucide-react';

interface ActionableButtonProps {
    title: string;
    description: string;
    count?: number;
    onClick: () => void;
    variant?: 'gap' | 'question';
    className?: string;
}

export const ActionableButton: React.FC<ActionableButtonProps> = ({
    title,
    description,
    count,
    onClick,
    variant = 'gap',
    className
}) => {
    const isGap = variant === 'gap';

    return (
        <Button
            onClick={onClick}
            variant="outline"
            className={cn(
                "group relative w-full h-auto p-6 flex flex-col items-start gap-2 overflow-hidden transition-all duration-500 rounded-2xl border-2",
                isGap
                    ? "bg-gradient-to-br from-fuchsia-50/50 to-purple-50/50 border-fuchsia-100 hover:border-fuchsia-300 dark:from-fuchsia-900/10 dark:to-purple-900/10 dark:border-fuchsia-900/30 dark:hover:border-fuchsia-700"
                    : "bg-gradient-to-br from-cyan-50/50 to-blue-50/50 border-cyan-100 hover:border-cyan-300 dark:from-cyan-900/10 dark:to-blue-900/10 dark:border-cyan-900/30 dark:hover:border-cyan-700",
                "hover:shadow-xl hover:-translate-y-1 active:scale-[0.98]",
                className
            )}
        >
            {/* Background decoration */}
            <div className={cn(
                "absolute -right-4 -top-4 w-24 h-24 rounded-full opacity-10 blur-2xl transition-all duration-700 group-hover:scale-150",
                isGap ? "bg-fuchsia-500" : "bg-cyan-500"
            )} />

            <div className="flex items-center justify-between w-full relative z-10">
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "p-2.5 rounded-xl shadow-sm transition-transform duration-500 group-hover:rotate-12",
                        isGap ? "bg-fuchsia-100 text-fuchsia-600 dark:bg-fuchsia-900/50 dark:text-fuchsia-400" : "bg-cyan-100 text-cyan-600 dark:bg-cyan-900/50 dark:text-cyan-400"
                    )}>
                        {isGap ? <Zap className="w-5 h-5" /> : <HelpCircle className="w-5 h-5" />}
                    </div>
                    <div className="text-left">
                        <h4 className="font-bold text-lg tracking-tight flex items-center gap-2">
                            {title}
                            {count !== undefined && (
                                <span className={cn(
                                    "text-xs px-2 py-0.5 rounded-full font-black uppercase tracking-tighter",
                                    isGap ? "bg-fuchsia-500 text-white" : "bg-cyan-500 text-white"
                                )}>
                                    {count}
                                </span>
                            )}
                        </h4>
                        <p className="text-sm text-muted-foreground/80 font-medium">
                            {description}
                        </p>
                    </div>
                </div>

                <div className={cn(
                    "p-2 rounded-full transition-all duration-300 opacity-0 group-hover:opacity-100 group-hover:translate-x-1",
                    isGap ? "bg-fuchsia-500 text-white" : "bg-cyan-500 text-white"
                )}>
                    <ArrowRight className="w-4 h-4" />
                </div>
            </div>

            <div className="mt-4 flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 group-hover:text-foreground transition-colors relative z-10">
                <Sparkles className={cn("w-3 h-3", isGap ? "text-fuchsia-400" : "text-cyan-400")} />
                Haz clic para explorar y desarrollar
            </div>
        </Button>
    );
};
