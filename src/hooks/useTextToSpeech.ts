// En: src/hooks/useTextToSpeech.ts
'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

import { useUserSettings } from '@/contexts/UserSettingsContext';

export const useTextToSpeech = () => {
  const { settings } = useUserSettings();
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [activeText, setActiveText] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stopPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsLoading(false);
    setIsPlaying(false);
    setIsPaused(false);
    setActiveText(null);
  }, []);

  const play = useCallback(async (text: string) => {
    if (!text.trim()) {
      toast.info("No hay texto para leer.");
      return;
    }

    // Si es el mismo texto y está pausado, simplemente reanudar.
    if (activeText === text && isPaused && audioRef.current) {
      audioRef.current.play();
      setIsPlaying(true);
      setIsPaused(false);
      return;
    }

    // Si es el mismo texto y se está reproduciendo, pausarlo.
    if (activeText === text && isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      setIsPaused(true);
      return;
    }

    // Si hay otro audio reproduciéndose, detenerlo primero.
    if (audioRef.current) {
      stopPlayback();
    }

    setActiveText(text);
    setIsLoading(true);
    setIsPlaying(false);
    setIsPaused(false);

    try {
      // Construir payload con configuración TTS del usuario
      const ttsPayload: any = { text };

      // Si el usuario tiene configuración TTS personalizada, usarla
      if (settings) {
        if (settings.tts_provider) {
          ttsPayload.provider = settings.tts_provider;
        }
        if (settings.tts_voice) {
          ttsPayload.voice = settings.tts_voice;
        }
        if (settings.tts_speed) {
          ttsPayload.speed = settings.tts_speed;
        }
        if (settings.tts_region) {
          ttsPayload.region = settings.tts_region;
        }
      }

      const response = await apiClient.post('/api/text-to-speech', ttsPayload, {
        responseType: 'blob',
      });
      const audioBlob = new Blob([response.data], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);

      audioRef.current = new Audio(audioUrl);
      audioRef.current.play();

      setIsLoading(false);
      setIsPlaying(true);

      audioRef.current.onended = () => {
        stopPlayback();
        URL.revokeObjectURL(audioUrl);
      };
    } catch (error) {
      toast.error('No se pudo generar el audio.');
      console.error('Error en TTS:', error);
      stopPlayback();
    }
  }, [activeText, isPlaying, isPaused, stopPlayback, settings]);

  useEffect(() => {
    // Limpieza al desmontar el componente
    return () => {
      stopPlayback();
    };
  }, [stopPlayback]);

  return { play, stop: stopPlayback, isLoading, isPlaying, isPaused, activeText };
};