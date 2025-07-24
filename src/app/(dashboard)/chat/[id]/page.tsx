'use client';

import { useParams } from 'next/navigation';
import { CommonChat } from '@/components/CommonChat';

export default function ChatPage() {
  const params = useParams();
  const threadId = (params?.id as string) || '';

  return <CommonChat threadId={threadId} />;
}
