'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { motion, Variants, Transition } from 'framer-motion';
import ChatInputBar from '@/components/ChatInputBar';
import { Send } from 'lucide-react';
import { SelectedContextItem } from '@/types/context';

interface EmptyChatProps {
  onSendMessage: (e?: React.FormEvent) => void;
  newMessage: string;
  setNewMessage: (value: string) => void;
  isResponding: boolean;
  isRecording: boolean;
  isProcessingAudio: boolean;
  isUploadingFile: boolean;
  isVectorizingFile: boolean; // Nueva prop
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
  selectedContext: SelectedContextItem[]; // Added
  onContextSelected: (context: SelectedContextItem[]) => void; // Added
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
  isVectorizingFile, // Nueva prop
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
  selectedContext, // Added
  onContextSelected, // Added
  isUploadingImages,
  uploadedImagePreviews,
  onRemoveImage,
  onImageUpload,
}: EmptyChatProps) {
  const examplePrompts = [
    "Analiza los documentos recientes y genera un resumen ejecutivo.",
    "¿Cuáles son las últimas tendencias en inteligencia artificial generativa?",
    "Crea un plan de proyecto para una nueva aplicación de gestión de tareas.",
    "Compara las ventajas y desventajas de React vs. Vue para un proyecto a gran escala."
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.3,
      } as Transition,
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        stiffness: 100,
      } as Transition,
    },
  };

  return (
    <div className="relative flex flex-col h-full items-center justify-center text-center px-4 py-8 md:py-16 overflow-y-auto custom-scrollbar">
      {/* Subtle ambient radial gradient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[30rem] h-[30rem] bg-primary/5 blur-3xl rounded-full pointer-events-none -z-10" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="flex flex-col items-center mb-10 md:mb-12 max-w-2xl mx-auto"
      >
        <div className="relative mb-6 group">
          <div className="absolute -inset-4 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition duration-1000" />
          <Image
            src="/logo-simple.png"
            alt="Kognito AI"
            width={88}
            height={88}
            className="relative drop-shadow-2xl group-hover:scale-105 transition-transform duration-500"
          />
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-3 text-foreground flex items-center justify-center gap-3">
          ¡Hola! <span className="text-2xl md:text-3xl inline-block animate-bounce">👋</span>
        </h1>
        <p className="text-lg md:text-xl font-medium text-muted-foreground/80 max-w-lg leading-relaxed">
          ¿En qué puedo colaborar con tu inteligencia hoy?
        </p>
      </motion.div>

      <div className="w-full max-w-3xl space-y-8">
        <div className="bg-card/40 backdrop-blur-2xl p-2 rounded-[2.5rem] border border-border/40 shadow-2xl shadow-primary/5">
          <ChatInputBar
            newMessage={newMessage}
            setNewMessage={setNewMessage}
            onSendMessage={onSendMessage}
            onStopResponding={onStopResponding}
            isResponding={isResponding}
            inputPlaceholder="Escribe tu consulta aquí..."
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

        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 gap-3"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {examplePrompts.map((prompt, index) => (
            <motion.button
              key={index}
              onClick={() => setNewMessage(prompt)}
              className="minimal-card rounded-xl p-3 border border-border/20 text-sm hover:border-primary/30 transition-all cursor-pointer text-left flex items-center justify-between group"
              variants={itemVariants}
              whileHover={{ y: -2, scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              <span className="text-muted-foreground group-hover:text-foreground transition-colors leading-snug line-clamp-2">
                {prompt}
              </span>
              <Send className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-primary transition-colors flex-shrink-0 ml-2 opacity-0 group-hover:opacity-100" />
            </motion.button>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
