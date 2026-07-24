'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { SelectionPublicPage } from '@/components/SelectionPublicPage';

export default function PublicSelectionRoute() {
  const params = useParams();
  const token = (params?.token as string) || '';
  return <SelectionPublicPage token={token} />;
}
