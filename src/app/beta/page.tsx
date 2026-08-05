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
  Copy, 
  CheckCircle, 
  Building, 
  User, 
  Send,
  Globe,
  Users
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { CircuitBrainLogo } from "@/components/CircuitBrainLogo";

export default function BetaTesterPage() {
  const [formData, setFormData] = useState({
    nombre: "",
    organizacion: "",
    email: "",
    mensaje: "",
    categoria: "beta_tester"
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.nombre || !formData.email || !formData.mensaje) {
      toast.error("Por favor completa los campos requeridos.");
      return;
    }
    
    setIsSubmitting(true);
    try {
      const res = await fetch("/api/contacto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setSubmitted(true);
        toast.success("¡Solicitud de Beta Tester enviada con éxito!");
      } else {
        toast.error("Hubo un problema procesando tu solicitud.");
      }
    } catch (error) {
      console.error("Error al enviar solicitud beta:", error);
      toast.error("Error de conexión al enviar el formulario.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyEmail = () => {
    navigator.clipboard.writeText("contacto@kognitoai.cloud");
    setCopied(true);
    toast.success("Email oficial copiado al portapapeles.");
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="min-h-screen bg-[#020408] text-slate-100 relative overflow-hidden flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200 py-12 px-4 sm:px-6 lg:px-8">
      {/* Background Cyber-Space Neón */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[140px]" />
        <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-purple-600/15 rounded-full blur-[150px]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:50px_50px] opacity-70" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto w-full flex flex-col gap-10">
        
        {/* Navigation & Header */}
        <div className="flex flex-col gap-6">
          <Link 
            href="/presentacion" 
            className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-cyan-400 w-fit transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
            Volver a la Presentación
          </Link>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-800/80">
            <div className="flex items-center gap-4">
              <CircuitBrainLogo size={64} />
              <div className="flex flex-col">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 text-[10px] font-extrabold uppercase tracking-widest w-fit mb-1">
                  <Sparkles size={12} />
                  Programa Beta Testers
                </span>
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight text-white">
                  Se <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-400 bg-clip-text text-transparent">Beta Tester</span>
                </h1>
              </div>
            </div>

            <div className="flex flex-col gap-1 text-slate-400 text-xs font-mono">
              <div className="flex items-center gap-2 text-cyan-400">
                <Globe size={14} />
                <span>kognitoai.cloud/beta</span>
              </div>
              <span>Ayúdanos a construir la IA que realmente necesitamos</span>
            </div>
          </div>
        </div>

        {/* Content & Form Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          
          {/* Left Info Panel */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800/90 shadow-xl flex flex-col gap-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-cyan-400" />
                Acceso Anticipado Exclusivo
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Forma parte de la primera cohorte de usuarios que exploran el Exocerebro digital de KognitoAI. 
                Recibe soporte directo de nuestros ingenieros y co-diseña las funciones clave del sistema.
              </p>
            </div>

            {/* Email Direct Channel Card */}
            <div 
              onClick={copyEmail}
              className="flex items-center justify-between p-5 rounded-2xl bg-slate-950/80 border border-slate-800 hover:border-cyan-500/40 transition-all duration-300 cursor-pointer shadow-sm group"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 text-cyan-400">
                  <Mail className="w-5 h-5" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Correo Directo</span>
                  <span className="text-xs font-bold text-white group-hover:text-cyan-400 transition-colors">contacto@kognitoai.cloud</span>
                </div>
              </div>
              {copied ? (
                <CheckCircle className="w-4 h-4 text-emerald-400" />
              ) : (
                <Copy className="w-4 h-4 text-slate-500 group-hover:text-slate-200 transition-colors" />
              )}
            </div>

            <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-400">
                <Cpu className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Soporte Técnico</span>
                <span className="text-xs font-bold text-slate-200">Canal directo con ingenieros</span>
              </div>
            </div>
          </div>

          {/* Right Form Card */}
          <div className="lg:col-span-7 p-8 rounded-3xl bg-slate-950/90 border border-slate-800/90 shadow-2xl relative overflow-hidden">
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
                  <div className="flex flex-col gap-1.5 border-b border-slate-800 pb-4 mb-1">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-cyan-400" />
                      Formulario de Registro Beta
                    </h3>
                    <p className="text-slate-400 text-xs">Déjanos tus datos y nos pondremos en contacto contigo de inmediato.</p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <User className="w-3 h-3 text-cyan-400" />
                        Nombre Completo *
                      </label>
                      <Input
                        type="text"
                        name="nombre"
                        value={formData.nombre}
                        onChange={handleInputChange}
                        placeholder="Ej. María González"
                        required
                        className="h-11 rounded-xl bg-slate-900 border-slate-800 focus:ring-cyan-500/30 text-xs text-white"
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                        <Building className="w-3 h-3 text-purple-400" />
                        Empresa / Proyecto
                      </label>
                      <Input
                        type="text"
                        name="organizacion"
                        value={formData.organizacion}
                        onChange={handleInputChange}
                        placeholder="Ej. Acme Research"
                        className="h-11 rounded-xl bg-slate-900 border-slate-800 focus:ring-cyan-500/30 text-xs text-white"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <Mail className="w-3 h-3 text-cyan-400" />
                      Correo Electrónico *
                    </label>
                    <Input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="ejemplo@organizacion.cloud"
                      required
                      className="h-11 rounded-xl bg-slate-900 border-slate-800 focus:ring-cyan-500/30 text-xs text-white"
                    />
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Perfil de Caso de Uso
                    </label>
                    <select
                      name="categoria"
                      value={formData.categoria}
                      onChange={handleInputChange}
                      className="h-11 px-3 rounded-xl bg-slate-900 border border-slate-800 text-xs focus:ring-cyan-500/30 text-slate-100"
                    >
                      <option value="beta_tester">Programa Beta Tester / Exocerebro</option>
                      <option value="personas">Uso Personal / Profesional</option>
                      <option value="equipos">Equipos / Empresas</option>
                      <option value="investigadores">Investigadores / Ciencia</option>
                      <option value="instituciones">Sector Público / Instituciones</option>
                    </select>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <MessageSquare className="w-3 h-3 text-purple-400" />
                      Detalles / Caso de Uso *
                    </label>
                    <textarea
                      name="mensaje"
                      value={formData.mensaje}
                      onChange={handleInputChange}
                      rows={4}
                      placeholder="Cuéntanos brevemente en qué tipo de proyectos te gustaría probar KognitoAI..."
                      required
                      className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 focus:ring-cyan-500/30 text-xs text-white focus:outline-none resize-none"
                    />
                  </div>

                  <button 
                    type="submit"
                    disabled={isSubmitting}
                    className="rounded-xl h-12 bg-slate-950 hover:bg-slate-900 border border-purple-500/70 hover:border-cyan-400 text-white font-bold shadow-[0_0_20px_rgba(168,85,247,0.25)] hover:shadow-[0_0_25px_rgba(6,182,212,0.4)] transition-all mt-2 w-full flex items-center justify-center gap-2 text-xs"
                  >
                    {isSubmitting ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Procesando Registro...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4 text-cyan-400" />
                        Enviar Solicitud a contacto@kognitoai.cloud
                      </>
                    )}
                  </button>
                </motion.form>
              ) : (
                <motion.div 
                  key="success"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex flex-col items-center text-center py-10 gap-6 relative z-10"
                >
                  <div className="w-16 h-16 rounded-full bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 animate-bounce">
                    <CheckCircle className="w-8 h-8" />
                  </div>
                  <div className="flex flex-col gap-2">
                    <h3 className="text-2xl font-black text-white">¡Solicitud recibida!</h3>
                    <p className="text-slate-300 text-xs max-w-sm leading-relaxed">
                      Hemos recibido tu postulación al programa Beta Tester. Te contactaremos en <b>{formData.email}</b> en breve.
                    </p>
                  </div>
                  <Button 
                    onClick={() => setSubmitted(false)}
                    variant="outline" 
                    className="rounded-xl px-6 h-11 border-slate-800 font-semibold text-xs text-slate-200"
                  >
                    Enviar otra solicitud
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

        </div>

      </div>
    </div>
  );
}
