'use client';

import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { CommonChat } from '@/components/CommonChat';
import { useEffect, useState } from 'react';

export default function ChatPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const threadId = (params?.id as string) || '';
  const [initialMessage, setInitialMessage] = useState<string | null>(null);
  const [initialRagContext, setInitialRagContext] = useState<string | null>(null);

  useEffect(() => {
    if (!searchParams) return; // Add null check for searchParams

    const message = searchParams.get('initialMessage');
    const ragContext = searchParams.get('initialRagContext');

    setInitialMessage(message);
    setInitialRagContext(ragContext);

    if (message || ragContext) {
      const newSearchParams = new URLSearchParams(searchParams.toString());
      if (message) {
        newSearchParams.delete('initialMessage');
      }
      if (ragContext) {
        newSearchParams.delete('initialRagContext');
      }
      const path = `/chat/${threadId}`;
      router.replace(`${path}?${newSearchParams.toString()}`, { scroll: false });
    }
  }, [searchParams, router, threadId]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <CommonChat
        threadId={threadId}
        initialMessage={initialMessage || undefined}
        initialRagContext={initialRagContext || undefined}
      />
    </div>
  );
}
