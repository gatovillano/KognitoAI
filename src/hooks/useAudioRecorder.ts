// src/hooks/useAudioRecorder.ts
import { useState, useRef, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export interface AudioRecorderOptions {
  onTranscriptChunk?: (chunk: string) => void;
  onFinalTranscript?: () => void;
  language?: string;
}

export interface AudioRecorderHook {
  isRecording: boolean;
  isProcessingAudio: boolean;
  transcript: string;
  startRecording: () => void;
  stopRecording: () => void;
  clearTranscript: () => void;
}

export const useAudioRecorder = (options?: AudioRecorderOptions): AudioRecorderHook => {
  const { user } = useAuth();
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  const [transcript, setTranscript] = useState('');
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const finishTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3;
  const isIntentionalClosure = useRef(false);

  // Mantener referencia fresca a los callbacks
  const optionsRef = useRef(options);
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const cleanupAudioTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        try {
          track.stop();
        } catch (e) {
          // ignore
        }
      });
      streamRef.current = null;
    }
  }, []);

  const startRecording = useCallback(async () => {
    if (!user?.id) {
      toast.error('No se pudo iniciar la grabación: usuario no autenticado.');
      return;
    }
    isIntentionalClosure.current = false;

    if (finishTimeoutRef.current) {
      clearTimeout(finishTimeoutRef.current);
      finishTimeoutRef.current = null;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      streamRef.current = stream;

      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg',
      ];
      let selectedMimeType = 'audio/webm';
      for (const mt of mimeTypes) {
        if (MediaRecorder.isTypeSupported(mt)) {
          selectedMimeType = mt;
          break;
        }
      }

      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: selectedMimeType });

      // Establecer conexión WebSocket
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || window.location.origin;
      let wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      let wsHost = window.location.host;

      try {
        const url = new URL(apiBaseUrl);
        wsProtocol = url.protocol === 'https:' ? 'wss' : 'ws';
        wsHost = url.host;
      } catch (e) {
        console.error("WS: Error parsing API_BASE_URL, falling back to window.location.origin", e);
      }

      const token = localStorage.getItem('authToken');
      if (!token) {
        cleanupAudioTracks();
        toast.error('No se encontró el token de autenticación. Por favor, inicia sesión.');
        return;
      }

      const lang = optionsRef.current?.language || 'es';
      const wsUrl = `${wsProtocol}://${wsHost}/ws/audio/transcribe/${user.id}?token=${encodeURIComponent(token)}&language=${encodeURIComponent(lang)}`;
      
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        setIsRecording(true);
        setIsProcessingAudio(false);
        setTranscript('');
        reconnectAttempts.current = 0;
        // Iniciar captura enviando fragmentos cada 400ms para mantener el streaming fluido
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
          mediaRecorderRef.current.start(400);
        }
      };

      socket.onmessage = (event) => {
        const msgStr = event.data as string;
        if (!msgStr) return;

        if (msgStr === 'ping') {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send('pong');
          }
          return;
        }

        if (msgStr === 'pong') {
          return;
        }

        try {
          const message = JSON.parse(msgStr);
          if (message.type === 'transcript_chunk') {
            const chunkText = message.text || '';
            setTranscript(prev => prev + chunkText);
            optionsRef.current?.onTranscriptChunk?.(chunkText);
          } else if (message.type === 'final_transcript') {
            if (message.text) {
              setTranscript(prev => prev + message.text);
              optionsRef.current?.onTranscriptChunk?.(message.text);
            }
            setIsProcessingAudio(false);
            optionsRef.current?.onFinalTranscript?.();
            if (socket.readyState === WebSocket.OPEN) {
              socket.close(1000, 'Transcripción completada');
            }
          } else if (message.type === 'error') {
            toast.error(`Error de transcripción: ${message.message}`);
            setIsProcessingAudio(false);
            setIsRecording(false);
          }
        } catch (error) {
          console.error('WS Transcribe: Error al parsear mensaje:', error, msgStr);
        }
      };

      socket.onclose = (event) => {
        setIsRecording(false);
        setIsProcessingAudio(false);
        cleanupAudioTracks();

        if (isIntentionalClosure.current) {
          return;
        }

        if (reconnectAttempts.current < maxReconnectAttempts && !isIntentionalClosure.current) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 5000);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            startRecording();
          }, delay) as unknown as NodeJS.Timeout;
        }
      };

      socket.onerror = (event) => {
        console.error('WS Transcribe Error:', event);
        setIsRecording(false);
        setIsProcessingAudio(false);
        cleanupAudioTracks();
      };

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
          socket.send(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        cleanupAudioTracks();
      };

    } catch (error) {
      console.error('Error al acceder al micrófono o iniciar WebSocket:', error);
      toast.error('No se pudo acceder al micrófono o iniciar la transcripción. Asegúrate de otorgar permisos.');
      cleanupAudioTracks();
      setIsRecording(false);
      setIsProcessingAudio(false);
    }
  }, [user?.id, cleanupAudioTracks]);

  const stopRecording = useCallback(() => {
    isIntentionalClosure.current = true;
    setIsRecording(false);

    // Detener MediaRecorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        // ignore
      }
    }
    cleanupAudioTracks();

    // Notificar al servidor que se detuvo la entrada para que transcriba el remanente
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setIsProcessingAudio(true);
      try {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
      } catch (e) {
        console.error('Error enviando stop al WebSocket:', e);
      }

      // Timeout de seguridad en caso de que el backend no responda final_transcript
      finishTimeoutRef.current = setTimeout(() => {
        setIsProcessingAudio(false);
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close(1000, 'Timeout cierre seguro');
        }
      }, 4000);
    } else {
      setIsProcessingAudio(false);
    }
  }, [cleanupAudioTracks]);

  const clearTranscript = useCallback(() => {
    setTranscript('');
  }, []);

  // Limpiar recursos al desmontar el componente
  useEffect(() => {
    return () => {
      isIntentionalClosure.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (finishTimeoutRef.current) {
        clearTimeout(finishTimeoutRef.current);
        finishTimeoutRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch (e) {
          // ignore
        }
      }
      cleanupAudioTracks();
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [cleanupAudioTracks]);

  return {
    isRecording,
    isProcessingAudio,
    transcript,
    startRecording,
    stopRecording,
    clearTranscript,
  };
};
