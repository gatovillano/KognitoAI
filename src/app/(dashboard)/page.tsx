// En: src/app/(dashboard)/page.tsx
'use client';

import Image from 'next/image';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';

export default function HomePage() {
  const [chatInput, setChatInput] = useState('');
  const router = useRouter();

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    try {
      const response = await apiClient.post('/api/threads');
      const newThread = response.data;
      // Here you would typically send the first message to the thread
      router.push(`/chat/${newThread.id}`);
    } catch (error) {
      console.error('Error creating new chat thread:', error);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full">
      <Image src="/logo-completo.png" alt="Kognito AI Labs" width={200} height={200} />
      <h1 className="text-4xl font-bold mt-4 tracking-tight">Bienvenido a Kognito AI</h1>
      <p className="text-muted-foreground mt-2">¿Cómo te puedo ayudar hoy?</p>
      <form onSubmit={handleChatSubmit} className="mt-6 w-full max-w-md flex gap-2">
        <Input
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder="Escribe tu mensaje aquí..."
          className="flex-grow"
        />
        <Button type="submit">Enviar</Button>
      </form>
    </div>
  );
}
