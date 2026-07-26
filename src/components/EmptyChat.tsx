'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { motion, Variants, Transition } from 'framer-motion';
import ChatInputBar from '@/components/ChatInputBar';
import { Zap, ArrowUpRight } from 'lucide-react';
import { SelectedContextItem } from '@/types/context';

interface EmptyChatProps {
  onSendMessage: (e?: React.FormEvent) => void;
  newMessage: string;
  setNewMessage: (value: string) => void;
  isResponding: boolean;
  isRecording: boolean;
  isProcessingAudio: boolean;
  isUploadingFile: boolean;
  isVectorizingFile: boolean;
  isKnowledgeAnalysisActive: boolean;
  isWebSearchActive: boolean;
  isComprehensiveAnalysisActive: boolean;
  isDeepResearchActive: boolean;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onToggleKnowledgeAnalysis: () => void;
  onToggleWebSearch: () => void;
  onToggleComprehensiveAnalysis: () => void;
  onToggleDeepResearch: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onStopResponding?: () => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveContextItem: (item: any) => void;
  onPaste: (e: ClipboardEvent) => void;
  workspaceId?: string;
  selectedContext: SelectedContextItem[];
  onContextSelected: (context: SelectedContextItem[]) => void;
  isUploadingImages: boolean;
  uploadedImagePreviews: string[];
  onRemoveImage: () => void;
  onImageUpload: (e: React.ChangeEvent<HTMLInputElement> | { target: { files: FileList | File[] | null } }) => void;
}

export function EmptyChat({
  onSendMessage,
  newMessage,
  setNewMessage,
  isResponding,
  isRecording,
  isProcessingAudio,
  isUploadingFile,
  isVectorizingFile,
  isKnowledgeAnalysisActive,
  isWebSearchActive,
  isComprehensiveAnalysisActive,
  isDeepResearchActive,
  onKeyDown,
  onToggleKnowledgeAnalysis,
  onToggleWebSearch,
  onToggleComprehensiveAnalysis,
  onToggleDeepResearch,
  onStartRecording,
  onStopRecording,
  onStopResponding,
  onFileUpload,
  onRemoveContextItem,
  onPaste,
  workspaceId,
  selectedContext,
  onContextSelected,
  isUploadingImages,
  uploadedImagePreviews,
  onRemoveImage,
  onImageUpload,
}: EmptyChatProps) {
  const examplePrompts = [
    {
      title: "Analizar documentos",
      subtitle: "Genera un resumen ejecutivo de tus archivos y proyectos recientes",
      prompt: "Analiza los documentos recientes y genera un resumen ejecutivo."
    },
    {
      title: "Tendencias en IA",
      subtitle: "Explora las últimas novedades en inteligencia artificial generativa",
      prompt: "¿Cuáles son las últimas tendencias en inteligencia artificial generativa?"
    },
    {
      title: "Plan de proyecto",
      subtitle: "Crea una hoja de ruta para una nueva aplicación de gestión",
      prompt: "Crea un plan de proyecto para una nueva aplicación de gestión de tareas."
    },
    {
      title: "Comparativa técnica",
      subtitle: "Evalúa ventajas y contras entre React y Vue a gran escala",
      prompt: "Compara las ventajas y desventajas de React vs. Vue para un proyecto a gran escala."
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.2,
      } as Transition,
    },
  };

  const itemVariants = {
    hidden: { y: 12, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        stiffness: 120,
        damping: 15,
      } as Transition,
    },
  };

  return (
    <div className="relative flex flex-col h-full items-center justify-center text-center px-4 py-8 md:py-16 overflow-y-auto custom-scrollbar">
      {/* Glow radial sutil de fondo */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[34rem] h-[34rem] bg-primary/5 blur-3xl rounded-full pointer-events-none -z-10" />

      {/* Header minimalista con logo e indicador de modelo estilo Qwen */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="flex items-center justify-center gap-3 mb-8"
      >
        <div className="flex items-center justify-center w-10 h-10 rounded-full border border-border/50 bg-card/80 backdrop-blur-md shadow-sm">
          <Image
            src="/logo-simple.png"
            alt="Kognito AI"
            width={24}
            height={24}
            className="object-contain"
          />
        </div>
        <span className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground/90">
          kognito.ai
        </span>
      </motion.div>

      <div className="w-full max-w-2xl mx-auto space-y-6">
        {/* Input Bar Flotante Minimalista */}
        <div className="bg-card/70 backdrop-blur-2xl p-1 rounded-[2.25rem] border border-border/40 shadow-xl shadow-foreground/[0.02] dark:shadow-black/20">
          <ChatInputBar
            newMessage={newMessage}
            setNewMessage={setNewMessage}
            onSendMessage={onSendMessage}
            onStopResponding={onStopResponding}
            isResponding={isResponding}
            inputPlaceholder="¿Cómo puedo ayudarte hoy?"
            isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
            isWebSearchActive={isWebSearchActive}
            isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
            isDeepResearchActive={isDeepResearchActive}
            isRecording={isRecording}
            isProcessingAudio={isProcessingAudio}
            isUploadingFile={isUploadingFile}
            isVectorizingFile={isVectorizingFile}
            isUploadingImages={isUploadingImages}
            uploadedImagePreviews={uploadedImagePreviews}
            onRemoveImage={onRemoveImage}
            onImageUpload={onImageUpload}
            onKeyDown={onKeyDown}
            onToggleKnowledgeAnalysis={onToggleKnowledgeAnalysis}
            onToggleWebSearch={onToggleWebSearch}
            onToggleComprehensiveAnalysis={onToggleComprehensiveAnalysis}
            onToggleDeepResearch={onToggleDeepResearch}
            onStartRecording={onStartRecording}
            onStopRecording={onStopRecording}
            onFileUpload={onFileUpload}
            onRemoveContextItem={onRemoveContextItem}
            onPaste={onPaste}
            currentContext={selectedContext}
            isFixedPosition={false}
            workspaceId={workspaceId}
            onContextSelected={onContextSelected}
          />
        </div>

        {/* Sección de Sugerencias minimalistas */}
        <div className="text-left px-1">
          <div className="flex items-center gap-1.5 text-[11px] font-medium tracking-wider text-muted-foreground/60 uppercase mb-3 px-1">
            <Zap className="h-3.5 w-3.5 text-primary/70" />
            <span>Sugerido</span>
          </div>

          <motion.div
            className="flex flex-col gap-2.5"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {examplePrompts.map((item, index) => (
              <motion.button
                key={index}
                onClick={() => setNewMessage(item.prompt)}
                className="group relative w-full text-left p-3.5 px-4 rounded-2xl border border-border/30 bg-card/30 hover:bg-card/80 hover:border-border/60 transition-all duration-200 shadow-none hover:shadow-sm cursor-pointer flex items-center justify-between"
                variants={itemVariants}
                whileHover={{ x: 3 }}
                whileTap={{ scale: 0.995 }}
              >
                <div className="flex flex-col gap-0.5 pr-4">
                  <span className="text-sm font-semibold text-foreground/90 group-hover:text-primary transition-colors">
                    {item.title}
                  </span>
                  <span className="text-xs text-muted-foreground/75 font-normal line-clamp-1">
                    {item.subtitle}
                  </span>
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100" />
              </motion.button>
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
}

