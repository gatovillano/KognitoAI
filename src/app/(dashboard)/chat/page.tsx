'use client';

import { useState, useEffect } from 'react';
import { useWorkspace } from '@/contexts/WorkspaceContext';
import { CommonChat } from '@/components/CommonChat';
import dynamic from 'next/dynamic';

const WelcomeDialog = dynamic(() => import('@/components/WelcomeDialog').then(mod => mod.WelcomeDialog), { ssr: false });

export default function NewChatPage() {
  const { currentWorkspace } = useWorkspace();
  const workspaceId = currentWorkspace?.id;
  const [isWelcomeDialogOpen, setIsWelcomeDialogOpen] = useState(false);

  useEffect(() => {
    const hasVisitedChat = localStorage.getItem('hasVisitedChat');
    if (!hasVisitedChat) {
      setIsWelcomeDialogOpen(true);
      localStorage.setItem('hasVisitedChat', 'true');
    }
  }, []);

  return (
    <>
      <CommonChat workspaceId={workspaceId} />
      <WelcomeDialog isOpen={isWelcomeDialogOpen} onOpenChange={setIsWelcomeDialogOpen} />
    </>
  );
}

