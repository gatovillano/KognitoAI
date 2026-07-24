// src/components/MoreActionsMenu.tsx
import React from 'react';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Plus, Upload, Loader2, Image as ImageIcon } from 'lucide-react';

interface MoreActionsMenuProps {
  isWebSearchActive?: boolean;
  isComprehensiveAnalysisActive?: boolean;
  isDeepResearchActive?: boolean;
  isKnowledgeAnalysisForced?: boolean;
  isWebSearchForced?: boolean;
  isComprehensiveAnalysisForced?: boolean;
  isDeepResearchForced?: boolean;
  isUploadingFile: boolean;
  isUploadingImage?: boolean;
  onToggleWebSearch?: () => void;
  onToggleComprehensiveAnalysis?: () => void;
  onToggleDeepResearch?: () => void;
  onToggleKnowledgeAnalysisForced?: () => void;
  onToggleWebSearchForced?: () => void;
  onToggleComprehensiveAnalysisForced?: () => void;
  onToggleDeepResearchForced?: () => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onImageUpload: (e: React.ChangeEvent<HTMLInputElement> | { target: { files: FileList | File[] | null } }) => void;
}

export function MoreActionsMenu({
  isUploadingFile,
  isUploadingImage,
  onFileUpload,
  onImageUpload,
}: MoreActionsMenuProps) {

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="rounded-xl text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-all">
            <Plus className="h-5 w-5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {/* Action Buttons */}
          <DropdownMenuItem asChild>
            <label htmlFor="file-upload-menu" className="cursor-pointer">
              {isUploadingFile ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              Subir Documentos
            </label>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <label htmlFor="image-upload-menu" className="cursor-pointer">
              {isUploadingImage ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ImageIcon className="mr-2 h-4 w-4" />
              )}
              Subir Imagen
            </label>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      {/* Hidden file input for documents */}
      <input
        id="file-upload-menu"
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.md"
        className="hidden"
        onChange={(e) => {
          onFileUpload(e);
          if (e.target) e.target.value = '';
        }}
        disabled={isUploadingFile}
      />
      {/* Hidden file input for images - unlimited size support */}
      <input
        id="image-upload-menu"
        type="file"
        accept="image/*"
        className="hidden"
        data-unlimited-size="true"
        onChange={(e) => {
          onImageUpload(e);
          if (e.target) e.target.value = '';
        }}
        disabled={isUploadingImage}
      />
    </>
  );
}