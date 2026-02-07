// src/hooks/useAudioRecorder.ts
import { useState, useRef, useCallback, useEffect } from 'react'; // Añadir useEffect
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext'; // Importar useAuth para obtener el userId

interface AudioRecorderHook {
  isRecording: boolean;
  isProcessingAudio: boolean;
  transcript: string;
  startRecording: () => void;
  stopRecording: () => void;
  clearTranscript: () => void;
}

export const useAudioRecorder = (): AudioRecorderHook => {
  const { user } = useAuth(); // Obtener el usuario autenticado
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  const [transcript, setTranscript] = useState('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const wsRef = useRef<WebSocket | null>(null); // Referencia al WebSocket
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const isIntentionalClosure = useRef(false);

  const startRecording = useCallback(async () => {
    if (!user?.id) {
      toast.error('No se pudo iniciar la grabación: usuario no autenticado.');
      return;
    }
    isIntentionalClosure.current = false;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = { mimeType: 'audio/webm;codecs=opus' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        console.warn(`${options.mimeType} no soportado, intentando con audio/webm`);
        options.mimeType = 'audio/webm';
      }
      mediaRecorderRef.current = new MediaRecorder(stream, options);

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

      const token = localStorage.getItem('authToken'); // Obtener el token de autenticación
      if (!token) {
        toast.error('No se encontró el token de autenticación. Por favor, inicia sesión.');
        return;
      }

      // --- INICIO DE LOS CONSOLE.LOG AÑADIDOS ---
      console.log('DEBUG WS Transcribe Frontend: user.id from useAuth:', user.id);
      console.log('DEBUG WS Transcribe Frontend: authToken from localStorage:', token ? token.substring(0, 30) + '...' : 'No token');
      // --- FIN DE LOS CONSOLE.LOG AÑADIDOS ---

      const wsUrl = `${wsProtocol}://${wsHost}/ws/audio/transcribe/${user.id}?token=${encodeURIComponent(token)}`; // Añadir el token a la URL
      console.log('DEBUG WS Transcribe Frontend: Constructed WebSocket URL:', wsUrl); // Añadir log de la URL completa
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WS Transcribe: Conectado.');
        setIsRecording(true);
        setTranscript('');
        toast.info('Grabación iniciada...');
        reconnectAttempts.current = 0; // Resetear intentos de reconexión
        mediaRecorderRef.current?.start(500); // Enviar fragmentos cada 500ms
      };

      wsRef.current.onmessage = (event) => {
        const msgStr = event.data as string;
        if (!msgStr) return;

        if (msgStr === 'ping') {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send('pong');
          }
          return;
        }

        if (msgStr === 'pong') {
          return;
        }

        try {
          const message = JSON.parse(msgStr);
          if (message.type === 'transcript_chunk') {
            setTranscript(prev => prev + message.text); // Acumular transcripciones parciales
          } else if (message.type === 'final_transcript') {
            setTranscript(prev => prev + message.text); // Añadir el fragmento final
            toast.success('Transcripción finalizada.');
          } else if (message.type === 'error') {
            toast.error(`Error de transcripción: ${message.message}`);
            console.error('WS Transcribe Error:', message.message);
          }
        } catch (error) {
          console.error('WS Transcribe: ❌ ERROR CRÍTICO al parsear mensaje WebSocket:', error, 'Mensaje RAW recibido:', msgStr);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log(`WS Transcribe: Desconectado. Código: ${event.code}, Razón: "${event.reason}", Limpio: ${event.wasClean}.`);
        setIsRecording(false);
        setIsProcessingAudio(false);

        if (isIntentionalClosure.current) {
          console.log('WS Transcribe: Cierre intencional, no se reconectará.');
          isIntentionalClosure.current = false; // Reset for next time
          return;
        }

        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`WS Transcribe: 🔄 Reintentando conexión en ${delay}ms (intento ${reconnectAttempts.current + 1}/${maxReconnectAttempts}).`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            startRecording(); // Reintentar la grabación
          }, delay) as unknown as NodeJS.Timeout;
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          const errorMessage = 'No se pudo reconectar al servidor de transcripción después de varios intentos.';
          console.error(`WS Transcribe: ${errorMessage}`);
          toast.error(errorMessage);
        }
      };

      wsRef.current.onerror = (event) => {
        console.error('WS Transcribe Error:', event);
        // Intentar obtener más detalles si el evento lo permite
        if (event instanceof ErrorEvent) {
          console.error('WS Transcribe Error Message:', event.message);
        }
        toast.error('Error en la conexión de transcripción. Revisa la consola para más detalles.');
        setIsRecording(false);
        setIsProcessingAudio(false);
      };

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(event.data); // Enviar fragmento de audio por WebSocket
        }
      };

      mediaRecorderRef.current.onstop = () => {
        console.log('MediaRecorder: Detenido.');
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.close(); // Cerrar el WebSocket cuando la grabación se detiene
        }
        setIsProcessingAudio(true); // Indicar que se está esperando la transcripción final
      };

    } catch (error) {
      console.error('Error al acceder al micrófono o iniciar WebSocket:', error);
      toast.error('No se pudo acceder al micrófono o iniciar la transcripción. Asegúrate de dar permisos.');
    }
  }, [user?.id]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      isIntentionalClosure.current = true;
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      toast.info('Grabación detenida. Esperando transcripción final...');
    }
  }, [isRecording]);

  const clearTranscript = useCallback(() => {
    setTranscript('');
  }, []);

  // Limpiar recursos al desmontar el componente
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isRecording,
    isProcessingAudio,
    transcript,
    startRecording,
    stopRecording,
    clearTranscript,
  };
};
