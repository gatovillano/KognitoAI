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
  onImageUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
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
    <div className="flex flex-col h-full items-center justify-center text-center px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="flex flex-col items-center mb-12"
      >
        <div className="relative mb-8 group">
          <div className="absolute -inset-4 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition duration-1000" />
          <Image
            src="/logo-simple.png"
            alt="Kognito AI"
            width={100}
            height={100}
            className="relative drop-shadow-2xl group-hover:scale-110 transition-transform duration-500"
          />
        </div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tighter mb-4 bg-gradient-to-br from-foreground via-foreground/90 to-foreground/70 bg-clip-text text-transparent flex items-center gap-3">
          ¡Hola! <span className="text-2xl md:text-3xl animate-bounce">👋</span>
        </h1>
        <p className="text-xl md:text-2xl font-medium text-muted-foreground/80 max-w-lg leading-relaxed">
          ¿En qué puedo colaborar con tu inteligencia hoy?
        </p>
      </motion.div>

      <div className="w-full max-w-3xl">
        <div className="bg-card/40 backdrop-blur-2xl p-2 rounded-[2.5rem] border border-border/40 shadow-2xl shadow-primary/5 mb-8">
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
          className="grid grid-cols-1 sm:grid-cols-2 gap-4"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {examplePrompts.map((prompt, index) => (
            <motion.button
              key={index}
              onClick={() => setNewMessage(prompt)}
              className="group relative p-5 text-left rounded-3xl bg-card/30 backdrop-blur-md border border-border/40 hover:border-primary/30 transition-all duration-300 overflow-hidden"
              variants={itemVariants}
              whileHover={{ y: -4, scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <p className="relative text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors leading-relaxed">
                {prompt}
              </p>
              <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0">
                <Send className="h-4 w-4 text-primary" />
              </div>
            </motion.button>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
