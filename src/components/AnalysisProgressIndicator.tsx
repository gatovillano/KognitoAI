'use client';

import { Loader2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface AnalysisProgressIndicatorProps {
  progress: number | null;
  text: string;
}

export default function AnalysisProgressIndicator({ progress, text }: AnalysisProgressIndicatorProps) {
  return (
    <div className="bg-muted text-muted-foreground p-3 rounded-md mb-4 text-sm">
      <div className="flex items-center gap-2 mb-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>{text}</span>
      </div>
      {progress !== null ? (
        <Progress value={progress} className="w-full h-2" />
      ) : (
        <Progress value={100} className="w-full h-2 opacity-75 animate-pulse" />
      )}
    </div>
  );
}
