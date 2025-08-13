// src/components/MoreActionsMenu.tsx
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { Plus, Search, Lightbulb, BrainCircuit, Upload, Mic, Loader2 } from 'lucide-react';
import { Switch } from '@/components/ui/switch';

interface MoreActionsMenuProps {
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  isDeepResearchActive: boolean;
  isRecording: boolean;
  isUploadingFile: boolean;
  onToggleWebSearch: () => void;
  onToggleComprehensiveAnalysis: () => void;
  onToggleDeepResearch: () => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
}

export function MoreActionsMenu({
  isWebSearchActive,
  isComprehensiveAnalysisActive,
  isDeepResearchActive,
  isRecording,
  isUploadingFile,
  onToggleWebSearch,
  onToggleComprehensiveAnalysis,
  onToggleDeepResearch,
  onFileUpload,
  onStartRecording,
  onStopRecording,
}: MoreActionsMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full">
          <Plus className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {/* Mode Buttons */}
        <DropdownMenuItem onClick={onToggleWebSearch}>
          <Search className="mr-2 h-4 w-4" /> Búsqueda Web {isWebSearchActive && '✅'}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onToggleComprehensiveAnalysis}>
          <Lightbulb className="mr-2 h-4 w-4" /> Búsqueda Analítica {isComprehensiveAnalysisActive && '✅'}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onToggleDeepResearch}>
          <BrainCircuit className="mr-2 h-4 w-4" /> Investigación Profunda {isDeepResearchActive && '✅'}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {/* Action Buttons */}
        <DropdownMenuItem>
          <input
            id="file-upload-menu" // Unique ID for this input
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.gif"
            className="hidden"
            onChange={(e) => {
              onFileUpload(e);
              e.target.value = '';
            }}
            disabled={isUploadingFile}
          />
          <label htmlFor="file-upload-menu" className="flex items-center cursor-pointer w-full">
            {isUploadingFile ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Upload className="mr-2 h-4 w-4" />
            )}
            Subir Documentos
          </label>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={isRecording ? onStopRecording : onStartRecording}>
          <Mic className="mr-2 h-4 w-4" /> {isRecording ? 'Detener Grabación' : 'Grabar Audio'}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
