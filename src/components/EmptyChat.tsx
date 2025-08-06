'use client';

import { useState } from 'react';
import Image from 'next/image';
import { motion, Variants, Transition } from 'framer-motion';
import ChatInputBar from '@/components/ChatInputBar';
import { ContextSelectorButton } from '@/components/ContextSelectorButton';

interface EmptyChatProps {
  onSendMessage: (e?: React.FormEvent) => void;
  newMessage: string;
  setNewMessage: (value: string) => void;
  isResponding: boolean;
}

export function EmptyChat({ onSendMessage, newMessage, setNewMessage, isResponding }: EmptyChatProps) {
  const [selectedContext, setSelectedContext] = useState<any[]>([]); // Estado para el contexto seleccionado

  const handleContextSelected = (context: any[]) => {
    setSelectedContext(context);
    // Aquí podrías hacer algo con el contexto seleccionado si fuera necesario en EmptyChat
  };
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
    <div className="flex flex-col h-full items-center justify-center text-center">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="flex flex-col items-center"
      >
        <Image src="/logo-simple.png" alt="Kognito AI" width={80} height={80} className="mb-4" />
        <h1 className="text-2xl font-semibold text-foreground mb-2">¡Hola! 👋</h1>
        <p className="text-lg text-muted-foreground mb-8">¿En que puedo colaborar hoy?</p>
      </motion.div>

      <div className="w-full max-w-2xl px-4">
        <ChatInputBar
          newMessage={newMessage}
          onMessageChange={setNewMessage}
          onSendMessage={onSendMessage}
          isResponding={isResponding}
          inputPlaceholder="¿En que puedo colaborar hoy?"
          isKnowledgeAnalysisActive={false}
          isWebSearchActive={false}
          isComprehensiveAnalysisActive={false}
          files={[]}
          onFileUpload={() => {}}
          onRemoveFile={() => {}}
          currentContext={selectedContext} // Pasar el contexto seleccionado
        >
          <ContextSelectorButton
            onContextSelected={handleContextSelected}
            currentContext={selectedContext}
            // No pasamos workspaceId aquí, ya que EmptyChat es para chats generales
          />
        </ChatInputBar>
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {examplePrompts.map((prompt, index) => (
            <motion.button
              key={index}
              onClick={() => setNewMessage(prompt)}
              className="p-3 text-left rounded-lg bg-card/50 hover:bg-card border border-border/50 hover:border-border transition-all duration-200 text-sm text-muted-foreground hover:text-foreground"
              variants={itemVariants}
            >
              {prompt}
            </motion.button>
          ))}
        </motion.div>
      </div>
    </div>
  );
}

