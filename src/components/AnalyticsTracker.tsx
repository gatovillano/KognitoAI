'use client';

import { useEffect, useRef } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';

export default function AnalyticsTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const lastPathRef = useRef<string | null>(null);

  useEffect(() => {
    // Generar o recuperar session ID para la sesión actual del navegador
    let sessionId = sessionStorage.getItem('kai_analytics_session_id');
    if (!sessionId) {
      sessionId = 'sess_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
      sessionStorage.setItem('kai_analytics_session_id', sessionId);
    }

    // Ruta base de la API
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://apibase.cuerpolibre.cl';
    
    // Obtener token del almacenamiento local
    const token = typeof window !== 'undefined' ? localStorage.getItem('authToken') : null;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const currentPath = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : '');
    
    // Evitar peticiones duplicadas de la misma página en renders consecutivos
    if (lastPathRef.current === currentPath) {
      return;
    }
    lastPathRef.current = currentPath;

    const referrer = typeof document !== 'undefined' ? document.referrer : '';

    const trackPageView = async () => {
      try {
        await fetch(`${apiUrl}/api/analytics/track`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            session_id: sessionId,
            event_type: 'pageview',
            path: pathname, // Guardamos el pathname limpio para mejor agregación
            referrer: referrer || null,
            event_metadata: {
              full_path: currentPath,
              search_params: searchParams?.toString() || null
            }
          }),
        });
      } catch (error) {
        // Fallar silenciosamente para no interferir con la navegación del usuario
        console.debug('Failed to send analytics pageview:', error);
      }
    };

    // Agregar un pequeño delay para asegurar de que el título e historial se actualicen
    const timer = setTimeout(trackPageView, 300);
    return () => clearTimeout(timer);
  }, [pathname, searchParams]);

  return null; // Este componente es puramente lógico y no renderiza nada
}
