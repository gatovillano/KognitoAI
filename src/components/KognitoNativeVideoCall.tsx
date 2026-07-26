'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import apiClient from '@/lib/api';
import {
  Mic,
  MicOff,
  Video as VideoIcon,
  VideoOff,
  PhoneOff,
  Monitor,
  Maximize2,
  Minimize2,
  PhoneCall,
  Volume2,
  FileText,
  Presentation as PresentationIcon,
  Radio,
  Users,
  X,
  CheckCircle2,
  Copy,
  Check,
} from 'lucide-react';

interface OnlyOfficeDoc {
  id: string;
  name: string;
  file_type: string;
  size: number;
  updated_at: string;
}

interface KognitoNativeVideoCallProps {
  roomId: string;
  roomName: string;
  roomType?: string; // 'default' | 'webinar' | 'presentation' | 'voice_room'
  activeDocumentId?: string | null;
  currentUserId: string;
  currentUserName: string;
  ws: WebSocket | null;
  onClose: () => void;
  incomingCallData?: {
    callerName: string;
    senderAccountId: string;
  } | null;
}

const ICE_SERVERS: RTCConfiguration = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
    { urls: 'stun:stun2.l.google.com:19302' },
    { urls: 'stun:stun3.l.google.com:19302' },
  ],
};

export const KognitoNativeVideoCall: React.FC<KognitoNativeVideoCallProps> = ({
  roomId,
  roomName,
  roomType = 'default',
  activeDocumentId = null,
  currentUserId,
  currentUserName,
  ws,
  onClose,
  incomingCallData = null,
}) => {
  const [callState, setCallState] = useState<'ringing' | 'connected' | 'ended'>(
    incomingCallData ? 'ringing' : 'connected'
  );
  const [isMicOn, setIsMicOn] = useState(true);
  const [isVideoOn, setIsVideoOn] = useState(roomType !== 'voice_room');
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [peerConnected, setPeerConnected] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [remoteUserName, setRemoteUserName] = useState<string>(
    incomingCallData?.callerName || 'Participante'
  );

  // Estado para proyección de OnlyOffice
  const [projectedDocId, setProjectedDocId] = useState<string | null>(activeDocumentId);
  const [showDocPicker, setShowDocPicker] = useState<boolean>(false);
  const [userDocs, setUserDocs] = useState<OnlyOfficeDoc[]>([]);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(false);

  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const mainLocalVideoRef = useRef<HTMLVideoElement | null>(null);
  const remoteVideoRef = useRef<HTMLVideoElement | null>(null);

  const localStreamRef = useRef<MediaStream | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const iceCandidatesQueue = useRef<RTCIceCandidateInit[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const ringOscillatorRef = useRef<NodeJS.Timeout | null>(null);

  // --- Sincronización continua de referencias de Video en el DOM ---
  useEffect(() => {
    if (localStreamRef.current) {
      if (localVideoRef.current && localVideoRef.current.srcObject !== localStreamRef.current) {
        localVideoRef.current.srcObject = localStreamRef.current;
      }
      if (mainLocalVideoRef.current && mainLocalVideoRef.current.srcObject !== localStreamRef.current) {
        mainLocalVideoRef.current.srcObject = localStreamRef.current;
      }
    }
    if (remoteStreamRef.current && remoteVideoRef.current) {
      if (remoteVideoRef.current.srcObject !== remoteStreamRef.current) {
        remoteVideoRef.current.srcObject = remoteStreamRef.current;
      }
    }
  });

  // --- Tono de llamada sintetizado ---
  const startRingtone = useCallback(() => {
    try {
      if (typeof window === 'undefined') return;
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;

      const playTone = () => {
        if (ctx.state === 'closed') return;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, ctx.currentTime);
        gain.gain.setValueAtTime(0.08, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 1.2);
      };

      playTone();
      ringOscillatorRef.current = setInterval(playTone, 2500);
    } catch (e) {
      console.warn('AudioContext no soportado aún:', e);
    }
  }, []);

  const stopRingtone = useCallback(() => {
    if (ringOscillatorRef.current) {
      clearInterval(ringOscillatorRef.current);
      ringOscillatorRef.current = null;
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
  }, []);

  // --- Agregar pistas locales a RTCPeerConnection ---
  const attachLocalTracks = useCallback((pc: RTCPeerConnection, stream: MediaStream) => {
    const existingSenders = pc.getSenders();
    stream.getTracks().forEach((track) => {
      const alreadyAdded = existingSenders.some((s) => s.track === track);
      if (!alreadyAdded) {
        pc.addTrack(track, stream);
      }
    });
  }, []);

  // --- Procesar cola de candidatos ICE pendientes ---
  const flushIceCandidates = useCallback(async (pc: RTCPeerConnection) => {
    while (iceCandidatesQueue.current.length > 0) {
      const candidate = iceCandidatesQueue.current.shift();
      if (candidate) {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (err) {
          console.error('Error agregando candidato ICE en cola:', err);
        }
      }
    }
  }, []);

  // --- Crear y Configurar RTCPeerConnection ---
  const createPeerConnection = useCallback(() => {
    if (pcRef.current) return pcRef.current;

    const pc = new RTCPeerConnection(ICE_SERVERS);

    if (localStreamRef.current) {
      attachLocalTracks(pc, localStreamRef.current);
    }

    pc.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        remoteStreamRef.current = event.streams[0];
        setPeerConnected(true);

        if (remoteVideoRef.current) {
          remoteVideoRef.current.srcObject = event.streams[0];
        }
      }
    };

    pc.onicecandidate = (event) => {
      if (event.candidate && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: 'webrtc_signal',
            room_id: roomId,
            signal_type: 'ice_candidate',
            candidate: event.candidate,
          })
        );
      }
    };

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'connected') {
        setPeerConnected(true);
      } else if (
        pc.connectionState === 'disconnected' ||
        pc.connectionState === 'failed' ||
        pc.connectionState === 'closed'
      ) {
        setPeerConnected(false);
      }
    };

    pcRef.current = pc;
    return pc;
  }, [attachLocalTracks, roomId, ws]);

  // --- Configurar Dispositivos Locales ---
  const setupLocalMedia = useCallback(async () => {
    const wantVideo = roomType !== 'voice_room';
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: wantVideo ? { width: { ideal: 1280 }, height: { ideal: 720 } } : false,
        audio: true,
      });
      localStreamRef.current = stream;

      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
      if (mainLocalVideoRef.current) {
        mainLocalVideoRef.current.srcObject = stream;
      }

      setIsVideoOn(wantVideo);
      return stream;
    } catch (err) {
      console.warn('Error accediendo a cámara o micrófono, reintentando solo audio:', err);
      try {
        const audioOnly = await navigator.mediaDevices.getUserMedia({
          video: false,
          audio: true,
        });
        localStreamRef.current = audioOnly;
        setIsVideoOn(false);
        return audioOnly;
      } catch (audioErr) {
        console.error('Error crítico accediendo a micrófono:', audioErr);
        return null;
      }
    }
  }, [roomType]);

  // --- Enviar Oferta WebRTC ---
  const sendOffer = useCallback(async () => {
    const stream = localStreamRef.current || (await setupLocalMedia());
    const pc = createPeerConnection();
    if (stream) attachLocalTracks(pc, stream);

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: 'webrtc_signal',
          room_id: roomId,
          signal_type: 'offer',
          sdp: offer,
          caller_name: currentUserName,
        })
      );
    }
  }, [attachLocalTracks, createPeerConnection, currentUserName, roomId, setupLocalMedia, ws]);

  // --- Iniciar Llamada ---
  const initiateCall = useCallback(async () => {
    await setupLocalMedia();
    createPeerConnection();

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: 'call_initiate',
          room_id: roomId,
          caller_name: currentUserName,
        })
      );
    }

    await sendOffer();
  }, [createPeerConnection, currentUserName, roomId, sendOffer, setupLocalMedia, ws]);

  // --- Aceptar Llamada Entrante ---
  const acceptCall = useCallback(async () => {
    stopRingtone();
    setCallState('connected');
    const stream = await setupLocalMedia();
    const pc = createPeerConnection();
    if (stream) attachLocalTracks(pc, stream);

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: 'call_accept',
          room_id: roomId,
          responder_name: currentUserName,
        })
      );
    }

    await sendOffer();
  }, [attachLocalTracks, createPeerConnection, currentUserName, roomId, sendOffer, setupLocalMedia, stopRingtone, ws]);

  // --- Finalizar Llamada ---
  const handleEndCall = useCallback(() => {
    stopRingtone();
    setCallState('ended');

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    }
    if (remoteStreamRef.current) {
      remoteStreamRef.current.getTracks().forEach((track) => track.stop());
      remoteStreamRef.current = null;
    }

    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: 'call_end',
          room_id: roomId,
        })
      );
    }

    onClose();
  }, [onClose, roomId, stopRingtone, ws]);

  // --- Copiar Enlace ---
  const handleCopyLink = () => {
    const url = `${window.location.origin}/kognito-chat?join=${roomId}`;
    navigator.clipboard.writeText(url);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  // --- Toggle Micrófono ---
  const toggleMic = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMicOn(audioTrack.enabled);
      }
    }
  };

  // --- Toggle Cámara ---
  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoOn(videoTrack.enabled);
      }
    }
  };

  // --- Compartir Pantalla ---
  const toggleScreenShare = async () => {
    if (!isScreenSharing) {
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        const screenTrack = screenStream.getVideoTracks()[0];

        if (pcRef.current) {
          const sender = pcRef.current.getSenders().find((s) => s.track?.kind === 'video');
          if (sender) sender.replaceTrack(screenTrack);
        }

        if (localVideoRef.current) {
          localVideoRef.current.srcObject = screenStream;
        }

        screenTrack.onended = () => stopScreenShare();
        setIsScreenSharing(true);
      } catch (err) {
        console.error('Error al compartir pantalla:', err);
      }
    } else {
      stopScreenShare();
    }
  };

  const stopScreenShare = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (pcRef.current && videoTrack) {
        const sender = pcRef.current.getSenders().find((s) => s.track?.kind === 'video');
        if (sender) sender.replaceTrack(videoTrack);
      }
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = localStreamRef.current;
      }
    }
    setIsScreenSharing(false);
  };

  // --- Cargar Documentos de OnlyOffice ---
  const fetchOnlyOfficeDocs = async () => {
    setLoadingDocs(true);
    try {
      const res = await apiClient.get<OnlyOfficeDoc[]>('/api/documents/list');
      setUserDocs(res.data || []);
    } catch (e) {
      console.error('Error cargando documentos OnlyOffice:', e);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleOpenDocPicker = () => {
    fetchOnlyOfficeDocs();
    setShowDocPicker(true);
  };

  const handleSelectPresentationDoc = async (docId: string | null) => {
    setProjectedDocId(docId);
    setShowDocPicker(false);
    try {
      await apiClient.post(`/api/kognito-chat/rooms/${roomId}/presentation-doc`, {
        document_id: docId,
      });
    } catch (e) {
      console.error('Error proyectando documento OnlyOffice:', e);
    }
  };

  // --- Escuchar WebSocket para Señalización WebRTC ---
  useEffect(() => {
    if (!ws) return;

    const handleMessage = async (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.room_id !== roomId) return;

        if (data.type === 'presentation_doc_updated') {
          setProjectedDocId(data.document_id);
        } else if (data.type === 'call_initiate' && data.sender_account_id !== currentUserId) {
          setRemoteUserName(data.caller_name || 'Participante');
          setCallState('ringing');
          startRingtone();
        } else if (data.type === 'call_accept' && data.sender_account_id !== currentUserId) {
          stopRingtone();
          setCallState('connected');
          if (data.responder_name) setRemoteUserName(data.responder_name);
          await sendOffer();
        } else if (data.type === 'call_end') {
          handleEndCall();
        } else if (data.type === 'webrtc_signal' && data.sender_account_id !== currentUserId) {
          const pc = pcRef.current || createPeerConnection();

          if (data.signal_type === 'offer' && data.sdp) {
            if (data.caller_name) setRemoteUserName(data.caller_name);

            const stream = localStreamRef.current || (await setupLocalMedia());
            if (stream) attachLocalTracks(pc, stream);

            await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
            await flushIceCandidates(pc);

            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);

            if (ws.readyState === WebSocket.OPEN) {
              ws.send(
                JSON.stringify({
                  type: 'webrtc_signal',
                  room_id: roomId,
                  signal_type: 'answer',
                  sdp: answer,
                })
              );
            }
          } else if (data.signal_type === 'answer' && data.sdp) {
            await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
            await flushIceCandidates(pc);
            setPeerConnected(true);
          } else if (data.signal_type === 'ice_candidate' && data.candidate) {
            if (pc.remoteDescription && pc.remoteDescription.type) {
              await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
            } else {
              iceCandidatesQueue.current.push(data.candidate);
            }
          }
        }
      } catch (err) {
        console.error('Error procesando señalización WebRTC:', err);
      }
    };

    ws.addEventListener('message', handleMessage);
    return () => {
      ws.removeEventListener('message', handleMessage);
    };
  }, [attachLocalTracks, createPeerConnection, currentUserId, flushIceCandidates, handleEndCall, roomId, sendOffer, setupLocalMedia, startRingtone, stopRingtone, ws]);

  // Iniciar llamada al montar
  useEffect(() => {
    if (!incomingCallData) {
      initiateCall();
    } else {
      startRingtone();
    }

    return () => {
      stopRingtone();
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (remoteStreamRef.current) {
        remoteStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (pcRef.current) pcRef.current.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const getModeLabel = () => {
    switch (roomType) {
      case 'webinar':
        return { label: 'Webinar', color: 'bg-purple-600', icon: Radio };
      case 'presentation':
        return { label: 'Presentación', color: 'bg-blue-600', icon: PresentationIcon };
      case 'voice_room':
        return { label: 'Voice Room', color: 'bg-emerald-600', icon: Volume2 };
      default:
        return { label: 'Predeterminado', color: 'bg-indigo-600', icon: Users };
    }
  };

  const ModeIcon = getModeLabel().icon;

  // --- RENDER LLAMADA ENTRANTE ---
  if (callState === 'ringing') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
        <div className="w-full max-w-md bg-card border border-border rounded-2xl p-6 text-center shadow-2xl space-y-6">
          <div className="relative mx-auto w-24 h-24 flex items-center justify-center rounded-full bg-primary/10 text-primary animate-pulse">
            <PhoneCall className="w-12 h-12" />
          </div>
          <div>
            <Badge className={`${getModeLabel().color} text-white mb-2 uppercase text-[10px] tracking-wider px-2 py-0.5`}>
              <ModeIcon className="w-3 h-3 mr-1 inline" /> {getModeLabel().label}
            </Badge>
            <h3 className="text-xl font-bold">{remoteUserName}</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Invitación a llamada en <strong>{roomName}</strong>
            </p>
          </div>
          <div className="flex items-center justify-center gap-4 pt-2">
            <Button variant="destructive" size="lg" onClick={handleEndCall} className="rounded-full px-6 gap-2">
              <PhoneOff className="w-5 h-5" />
              Rechazar
            </Button>
            <Button variant="default" size="lg" onClick={acceptCall} className="rounded-full px-6 gap-2 bg-emerald-600 hover:bg-emerald-700 text-white">
              <VideoIcon className="w-5 h-5" />
              Aceptar
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // --- RENDER MINIMIZADO ---
  if (isMinimized) {
    return (
      <div className="fixed bottom-6 right-6 z-50 w-80 bg-card/95 border border-border rounded-2xl shadow-2xl overflow-hidden backdrop-blur-md animate-in slide-in-from-bottom duration-300">
        <div className="relative aspect-video bg-black flex items-center justify-center">
          {projectedDocId ? (
            <iframe
              src={`/api/documents/${projectedDocId}/embed`}
              className="w-full h-full border-none"
              title="Proyección OnlyOffice"
            />
          ) : (
            <video ref={peerConnected ? remoteVideoRef : mainLocalVideoRef} autoPlay playsInline className="w-full h-full object-cover" />
          )}
          <video ref={localVideoRef} autoPlay playsInline muted className="absolute bottom-2 right-2 w-20 aspect-video object-cover rounded-lg border border-white/20 shadow-md" />
        </div>
        <div className="p-3 flex items-center justify-between bg-muted/30">
          <span className="text-xs font-semibold truncate max-w-[140px] flex items-center gap-1.5">
            <ModeIcon className="w-3.5 h-3.5 text-primary" />
            {roomName}
          </span>
          <div className="flex items-center gap-1.5">
            <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full" onClick={() => setIsMinimized(false)}>
              <Maximize2 className="w-3.5 h-3.5" />
            </Button>
            <Button variant="destructive" size="icon" className="h-7 w-7 rounded-full" onClick={handleEndCall}>
              <PhoneOff className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // --- RENDER PANTALLA COMPLETA ---
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background/95 backdrop-blur-xl animate-in fade-in duration-200">
      {/* CABECERA */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-border/50 bg-muted/20">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-ping" />
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              <span>{roomName}</span>
              <Badge className={`${getModeLabel().color} text-white text-[10px] uppercase font-mono px-2 py-0.5 flex items-center gap-1`}>
                <ModeIcon className="w-3 h-3" /> {getModeLabel().label}
              </Badge>
            </h2>
            <p className="text-xs text-muted-foreground">
              {peerConnected ? `En llamada activa con ${remoteUserName}` : `Llamada activa • Esperando a ${remoteUserName}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Botón de Copiar Enlace */}
          <Button variant="outline" size="sm" onClick={handleCopyLink} className="text-xs gap-1.5">
            {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedLink ? '¡Enlace Copiado!' : 'Copiar Enlace'}</span>
          </Button>

          {/* Botón de Cargar Presentación OnlyOffice (para modo Presentación o Default) */}
          {(roomType === 'presentation' || roomType === 'default') && (
            <Button
              variant={projectedDocId ? 'secondary' : 'outline'}
              size="sm"
              onClick={handleOpenDocPicker}
              className="text-xs gap-1.5 border-blue-400/40 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/60"
            >
              <PresentationIcon className="w-3.5 h-3.5 text-blue-500" />
              <span>{projectedDocId ? 'Cambiar Presentación OnlyOffice' : 'Proyectar OnlyOffice'}</span>
            </Button>
          )}

          <Button variant="outline" size="icon" className="rounded-full" onClick={() => setIsMinimized(true)} title="Minimizar">
            <Minimize2 className="w-4 h-4" />
          </Button>
          <Button variant="destructive" size="sm" onClick={handleEndCall} className="rounded-full gap-2 px-4">
            <PhoneOff className="w-4 h-4" />
            <span>Colgar</span>
          </Button>
        </div>
      </div>

      {/* ÁREA PRINCIPAL */}
      <div className="flex-1 relative bg-black/90 flex items-center justify-center p-4 overflow-hidden">
        {/* PROYECCIÓN DE DOCUMENTO ONLYOFFICE */}
        {projectedDocId ? (
          <div className="relative w-full h-full max-w-6xl max-h-[82vh] rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-card flex flex-col">
            <div className="bg-muted px-4 py-2 flex items-center justify-between border-b border-border text-xs">
              <span className="font-semibold flex items-center gap-1.5 text-primary">
                <PresentationIcon className="w-4 h-4 text-blue-500" /> Presentación OnlyOffice Proyectada
              </span>
              <Button variant="ghost" size="sm" onClick={() => handleSelectPresentationDoc(null)} className="h-6 text-[10px] text-destructive hover:bg-destructive/10">
                <X className="w-3 h-3 mr-1" /> Dejar de proyectar
              </Button>
            </div>
            <iframe
              src={`/api/documents/${projectedDocId}/embed`}
              className="w-full flex-1 border-none bg-white"
              title="Presentación OnlyOffice"
            />
          </div>
        ) : roomType === 'voice_room' ? (
          /* MODO VOICE ROOM (SOLO VOZ) */
          <div className="flex flex-col items-center justify-center gap-6 text-center text-white p-8">
            <div className="relative w-32 h-32 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center animate-pulse">
              <Volume2 className="w-16 h-16 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-2xl font-bold">{remoteUserName}</h3>
              <p className="text-sm text-emerald-400 font-mono mt-1">Sala de Voz Activa • Baja Latencia</p>
            </div>
          </div>
        ) : (
          /* VIDEO REMOTO / VISTA LOCAL DE RESPALDO */
          <div className="relative w-full h-full max-w-5xl max-h-[80vh] flex items-center justify-center rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-black">
            {peerConnected ? (
              <video ref={remoteVideoRef} autoPlay playsInline className="w-full h-full object-contain" />
            ) : (
              <div className="relative w-full h-full flex items-center justify-center">
                <video ref={mainLocalVideoRef} autoPlay playsInline muted className="w-full h-full object-cover transform -scale-x-100" />
                <div className="absolute inset-0 bg-black/40 backdrop-blur-sm flex flex-col items-center justify-center text-white gap-3 p-6 text-center">
                  <div className="w-16 h-16 rounded-full bg-indigo-500/20 border-2 border-indigo-400 flex items-center justify-center animate-pulse">
                    <Users className="w-8 h-8 text-indigo-400" />
                  </div>
                  <div>
                    <h4 className="text-xl font-bold">Llamada iniciada en {roomName}</h4>
                    <p className="text-sm text-gray-200 mt-1">
                      Esperando que otros participantes se unan a la llamada...
                    </p>
                  </div>
                  <Button variant="secondary" onClick={handleCopyLink} className="bg-white/20 hover:bg-white/30 text-white border border-white/30 text-xs gap-1.5">
                    {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedLink ? '¡Enlace Copiado!' : 'Copiar Enlace de Invitación'}</span>
                  </Button>
                </div>
              </div>
            )}

            <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 text-white text-xs font-medium flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${peerConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400 animate-pulse'}`} />
              {peerConnected ? remoteUserName : `Esperando participantes...`}
            </div>
          </div>
        )}

        {/* OVERLAY DE VIDEO LOCAL EN PIP (CUANDO HAY PEER CONECTADO) */}
        {roomType !== 'voice_room' && peerConnected && (
          <div className="absolute bottom-6 right-6 w-44 sm:w-56 aspect-video rounded-2xl overflow-hidden border-2 border-white/20 shadow-2xl bg-black transition-all duration-200 hover:scale-105">
            <video ref={localVideoRef} autoPlay playsInline muted className="w-full h-full object-cover transform -scale-x-100" />
            {!isVideoOn && (
              <div className="absolute inset-0 bg-zinc-900 flex items-center justify-center text-muted-foreground text-xs">
                Cámara apagada
              </div>
            )}
            <div className="absolute bottom-2 left-2 bg-black/70 backdrop-blur-sm px-2 py-0.5 rounded-lg text-[10px] text-white">
              Tú ({currentUserName})
            </div>
          </div>
        )}
      </div>

      {/* CONTROLES DE LA LLAMADA */}
      <div className="py-4 px-6 flex items-center justify-center gap-4 bg-muted/30 border-t border-border/50 backdrop-blur-md">
        <Button variant={isMicOn ? 'outline' : 'destructive'} size="icon" className="w-12 h-12 rounded-full" onClick={toggleMic} title={isMicOn ? 'Silenciar Micrófono' : 'Activar Micrófono'}>
          {isMicOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
        </Button>

        {roomType !== 'voice_room' && (
          <Button variant={isVideoOn ? 'outline' : 'destructive'} size="icon" className="w-12 h-12 rounded-full" onClick={toggleVideo} title={isVideoOn ? 'Apagar Cámara' : 'Encender Cámara'}>
            {isVideoOn ? <VideoIcon className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
          </Button>
        )}

        <Button variant={isScreenSharing ? 'secondary' : 'outline'} size="icon" className={`w-12 h-12 rounded-full ${isScreenSharing ? 'bg-primary text-primary-foreground font-bold' : ''}`} onClick={toggleScreenShare} title={isScreenSharing ? 'Detener Compartir Pantalla' : 'Compartir Pantalla'}>
          <Monitor className="w-5 h-5" />
        </Button>

        <div className="w-px h-8 bg-border mx-2" />

        <Button variant="destructive" size="lg" className="rounded-full px-8 gap-2 bg-red-600 hover:bg-red-700 text-white font-semibold shadow-lg shadow-red-600/20" onClick={handleEndCall}>
          <PhoneOff className="w-5 h-5" />
          <span>Finalizar</span>
        </Button>
      </div>

      {/* MODAL DE SELECCIÓN DE PRESENTACIÓN ONLYOFFICE */}
      <Dialog open={showDocPicker} onOpenChange={setShowDocPicker}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <PresentationIcon className="w-5 h-5 text-blue-500" />
              <span>Seleccionar Presentación de OnlyOffice</span>
            </DialogTitle>
            <DialogDescription>
              Elige un documento de tu biblioteca local para proyectarlo en vivo a todos los participantes de la llamada.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 max-h-80 overflow-y-auto py-2">
            {loadingDocs ? (
              <p className="text-center text-sm text-muted-foreground py-6 animate-pulse">Cargando biblioteca de documentos OnlyOffice...</p>
            ) : userDocs.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-6">No se encontraron documentos en OnlyOffice.</p>
            ) : (
              userDocs.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => handleSelectPresentationDoc(doc.id)}
                  className={`p-3 border rounded-xl flex items-center justify-between cursor-pointer transition-all ${
                    projectedDocId === doc.id ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/40' : 'hover:bg-muted/50 border-border'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-blue-500" />
                    <div>
                      <h4 className="text-sm font-semibold text-foreground">{doc.name}</h4>
                      <p className="text-[10px] text-muted-foreground uppercase font-mono">{doc.file_type} • {(doc.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                  {projectedDocId === doc.id && <CheckCircle2 className="w-5 h-5 text-blue-600" />}
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
