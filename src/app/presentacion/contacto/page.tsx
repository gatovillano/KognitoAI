'use client';

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Mail, 
  MessageSquare, 
  ArrowLeft, 
  Cpu, 
  ShieldCheck, 
  Sparkles,
  ChevronRight,
  Copy,
  CheckCircle,
  Building,
  User,
  Send
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export default function ContactoPage() {
  const [formData, setFormData] = useState({
    nombre: "",
    organizacion: "",
    email: "",
    mensaje: "",
    categoria: "demo"
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.nombre || !formData.email || !formData.mensaje) {
      toast.error("Por favor completa los campos requeridos.");
      return;
    }
    
    setIsSubmitting(true);
    // Simular guardado o envío
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmitted(true);
      toast.success("¡Mensaje enviado exitosamente!");
    }, 2000);
  };

  const copyEmail = () => {
    navigator.clipboard.writeText("contacto@kognitoai.com");
    setCopied(true);
    toast.success("Email copiado al portapapeles.");
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="flex flex-col gap-16">
      
      {/* Back navigation & Title */}
      <div className="flex flex-col gap-4">
        <Link 
          href="/presentacion" 
          className="inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-foreground w-fit transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Volver al Inicio
        </Link>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="flex flex-col gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-600 dark:text-cyan-400 text-xs font-extrabold uppercase tracking-widest w-fit">
              Hablemos de tu proyecto
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground">
              Contacto y Demostración
            </h1>
          </div>
          <p className="text-muted-foreground text-sm max-w-md leading-relaxed">
            Programa una demostración del ecosistema con un ingeniero de software o hablemos de integraciones de infraestructura.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start max-w-6xl mx-auto w-full">
        {/* Contact info channels cards */}
        <div className="lg:col-span-5 flex flex-col gap-6 w-full">
          
          <div className="flex flex-col gap-4">
            <h3 className="text-lg font-bold text-foreground">Canales Directos</h3>
            <p className="text-muted-foreground text-xs leading-relaxed">¿Deseas una respuesta ultra rápida? Haz click en nuestro correo oficial para copiarlo o envíanos tu formulario en la derecha.</p>
          </div>

          <div 
            onClick={copyEmail}
            className="flex items-center justify-between p-5 rounded-2xl bg-card border border-border/40 hover:border-cyan-500/30 transition-all duration-300 cursor-pointer shadow-sm group"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 text-cyan-500">
                <Mail className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Correo Oficial</span>
                <span className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">contacto@kognitoai.com</span>
              </div>
            </div>
            {copied ? (
              <CheckCircle className="w-4 h-4 text-emerald-500" />
            ) : (
              <Copy className="w-4 h-4 text-muted-foreground opacity-50 group-hover:opacity-100 transition-opacity" />
            )}
          </div>

          <div className="flex items-center gap-4 p-5 rounded-2xl bg-card border border-border/40 shadow-sm">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-500">
              <Cpu className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Soporte Corporativo</span>
              <span className="text-sm font-bold text-foreground">24/7 Ingenieros Disponibles</span>
            </div>
          </div>

          <div className="flex items-center gap-4 p-5 rounded-2xl bg-card border border-border/40 shadow-sm">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 text-emerald-500">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Soberanía de Datos</span>
              <span className="text-sm font-bold text-foreground">Alineado con normativas GDPR</span>
            </div>
          </div>

        </div>

        {/* Interactive Form Panel */}
        <div className="lg:col-span-7 glass-card rounded-[2.5rem] border border-border/40 p-8 md:p-10 shadow-2xl relative w-full overflow-hidden bg-background/40">
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
          
          <AnimatePresence mode="wait">
            {!submitted ? (
              <motion.form 
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handleFormSubmit}
                className="flex flex-col gap-5 relative z-10"
              >
                <div className="flex flex-col gap-2 border-b border-border/40 pb-4 mb-2">
                  <h3 className="text-xl font-bold text-foreground flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-cyan-500" />
                    Enviar mensaje de contacto
                  </h3>
                  <p className="text-muted-foreground text-xs leading-relaxed">Completa el formulario y te responderemos en menos de 12 horas hábiles.</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <User className="w-3 h-3" />
                      Nombre Completo *
                    </label>
                    <Input
                      type="text"
                      name="nombre"
                      value={formData.nombre}
                      onChange={handleInputChange}
                      placeholder="Ej. Juan Pérez"
                      required
                      className="h-11 rounded-xl bg-card border-border/40 focus:ring-primary/20 text-xs"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Building className="w-3 h-3" />
                      Organización / Empresa
                    </label>
                    <Input
                      type="text"
                      name="organizacion"
                      value={formData.organizacion}
                      onChange={handleInputChange}
                      placeholder="Ej. Acme Inc."
                      className="h-11 rounded-xl bg-card border-border/40 focus:ring-primary/20 text-xs"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Mail className="w-3 h-3" />
                    Correo Electrónico *
                  </label>
                  <Input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="ejemplo@organizacion.com"
                    required
                    className="h-11 rounded-xl bg-card border-border/40 focus:ring-primary/20 text-xs"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    Tema de Interés
                  </label>
                  <select
                    name="categoria"
                    value={formData.categoria}
                    onChange={handleInputChange}
                    className="h-11 px-3 rounded-xl bg-card border border-border/40 text-xs focus:ring-primary/20 text-foreground"
                  >
                    <option value="demo">Demo Personalizada del Exocerebro</option>
                    <option value="alianza">Alianza Estratégica</option>
                    <option value="integracion">Integración Técnica / Self-Hosted</option>
                    <option value="otros">Otros Asuntos</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <MessageSquare className="w-3 h-3" />
                    Mensaje / Detalles *
                  </label>
                  <textarea
                    name="mensaje"
                    value={formData.mensaje}
                    onChange={handleInputChange}
                    rows={4}
                    placeholder="Cuéntanos un poco sobre tus necesidades e infraestructura actual..."
                    required
                    className="p-3.5 rounded-xl bg-card border border-border/40 focus:ring-primary/20 text-xs text-foreground focus:outline-none resize-none"
                  />
                </div>

                <Button 
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl h-11 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-bold shadow-md shadow-cyan-500/10 hover:shadow-lg mt-3 w-full flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Procesando mensaje...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Enviar Mensaje
                    </>
                  )}
                </Button>
              </motion.form>
            ) : (
              <motion.div 
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="flex flex-col items-center text-center py-10 gap-6 relative z-10"
              >
                <div className="w-16 h-16 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500 animate-bounce">
                  <CheckCircle className="w-8 h-8" />
                </div>
                <div className="flex flex-col gap-2">
                  <h3 className="text-2xl font-black text-foreground">¡Solicitud recibida!</h3>
                  <p className="text-muted-foreground text-sm max-w-sm leading-relaxed">
                    Hemos recibido tus datos con éxito. Un ingeniero se pondrá en contacto contigo en tu correo <b>{formData.email}</b> en un plazo máximo de 12 horas hábiles.
                  </p>
                </div>
                <Button 
                  onClick={() => setSubmitted(false)}
                  variant="outline" 
                  className="rounded-xl px-6 h-11 border-border/60 font-semibold"
                >
                  Enviar otro mensaje
                </Button>
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </div>

    </div>
  );
}
