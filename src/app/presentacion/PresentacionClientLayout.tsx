'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, ArrowRight, Shield, Cpu, Mail, Sparkles, Users, Globe } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { CircuitBrainLogo } from "@/components/CircuitBrainLogo";

export default function PresentacionClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Detectar scroll para cambiar apariencia del header
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Cerrar menú móvil al cambiar de ruta
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  const navLinks = [
    { name: "Inicio", href: "/presentacion" },
    { name: "Tecnología", href: "/presentacion/funcionamiento" },
    { name: "Casos de Uso", href: "/presentacion/casos" },
    { name: "Preguntas", href: "/presentacion/faq" },
    { name: "Contacto", href: "/presentacion/contacto" },
  ];

  return (
    <div className="min-h-screen bg-[#020408] text-slate-100 relative overflow-hidden flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Fondo Cyber-Space Neón */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Glow Orbs Neón */}
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[140px]" />
        <div className="absolute top-1/3 right-1/4 w-[500px] h-[500px] bg-purple-600/15 rounded-full blur-[150px]" />
        <div className="absolute bottom-1/4 left-1/3 w-[450px] h-[450px] bg-blue-600/10 rounded-full blur-[130px]" />
        {/* Grid pattern cyber */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:50px_50px] opacity-70" />
      </div>

      {/* Header / Navbar */}
      <header className={`relative z-50 sticky top-0 transition-all duration-300 ${
        isScrolled 
          ? "bg-[#020408]/90 backdrop-blur-xl border-b border-slate-800/80 shadow-2xl shadow-cyan-500/5" 
          : "bg-transparent"
      }`}>
        <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" aria-label="Navegación principal">
          <div className="flex h-20 items-center justify-between">
            {/* Logo & Brand KOGNITO AI LABS */}
            <div className="flex items-center gap-3">
              <Link href="/presentacion" className="flex items-center gap-3 group" aria-label="KognitoAI Inicio">
                <CircuitBrainLogo size={42} variant="brain" />
                <div className="flex flex-col">
                  <span className="font-black text-xl tracking-wider text-white uppercase group-hover:text-cyan-400 transition-colors flex items-center gap-1">
                    KOGNITO <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">AI</span>
                  </span>
                  <span className="text-[9px] font-bold tracking-[0.25em] text-slate-400 uppercase -mt-1">
                    AI LABS
                  </span>
                </div>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-8">
              <ul className="flex items-center gap-6">
                {navLinks.map((link) => (
                  <li key={link.name}>
                    <Link
                      href={link.href}
                      className={`relative text-xs uppercase font-bold tracking-wider transition-colors ${
                        pathname === link.href
                          ? "text-cyan-400"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {link.name}
                      {pathname === link.href && (
                        <motion.div
                          layoutId="navIndicator"
                          className="absolute bottom-[-6px] left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-400 to-purple-500 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.8)]"
                          transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        />
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
              
              <div className="flex items-center gap-3 ml-4">
                <Link href="/beta">
                  <button className="rounded-full px-5 py-2.5 bg-slate-950/80 hover:bg-slate-900 border border-purple-500/50 hover:border-cyan-400 text-white font-bold text-xs tracking-wide shadow-[0_0_15px_rgba(168,85,247,0.25)] hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all flex items-center gap-2.5 group">
                    <span className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center border border-purple-400/40 text-cyan-400 group-hover:scale-110 transition-transform">
                      <Users size={12} />
                    </span>
                    <span className="text-slate-200 group-hover:text-white">Se <span className="text-purple-400 group-hover:text-cyan-300">Beta Tester</span></span>
                    <ArrowRight size={14} className="text-cyan-400 group-hover:translate-x-1 transition-transform" />
                  </button>
                </Link>
              </div>
            </div>

            {/* Mobile Menu Button */}
            <div className="md:hidden flex items-center gap-3">
              <ThemeToggle />
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                aria-label={mobileMenuOpen ? "Cerrar menú" : "Abrir menú"}
                aria-expanded={mobileMenuOpen}
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>

          {/* Mobile Menu */}
          <AnimatePresence>
            {mobileMenuOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="md:hidden overflow-hidden border-t border-border/40 py-4"
              >
                <div className="flex flex-col gap-4">
                  <ul className="flex flex-col gap-2">
                    {navLinks.map((link) => (
                      <li key={link.name}>
                        <Link
                          href={link.href}
                          className={`px-3 py-2 rounded-lg text-base font-medium transition-colors ${
                            pathname === link.href
                              ? "bg-cyan-500/10 text-cyan-400 dark:text-cyan-300"
                              : "text-muted-foreground hover:text-primary hover:bg-accent"
                          }`}
                        >
                          {link.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <div className="pt-2 border-t border-border/40 flex flex-col gap-3">
                    <Link href="/beta">
                      <Button className="w-full rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-bold shadow-md shadow-cyan-500/10 hover:shadow-lg px-5 h-11 flex items-center justify-center gap-2">
                        <Sparkles className="w-4 h-4" />
                        Hazte Beta Tester
                      </Button>
                    </Link>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 relative z-10">
        {children}
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-border/40 bg-background/50 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
            {/* Brand Column */}
            <div className="lg:col-span-1">
              <Link href="/presentacion" className="flex items-center gap-2 mb-6" aria-label="KognitoAI Inicio">
                <CircuitBrainLogo size={32} />
                <span className="font-black text-xl tracking-tight bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 bg-clip-text text-transparent">
                  KognitoAI
                </span>
              </Link>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
                Exocerebro digital para equipos que buscan soberanía, memoria persistente y autonomía real.
              </p>
              <div className="mt-6 flex gap-4">
                <a href="#" className="text-muted-foreground hover:text-primary transition-colors" aria-label="Twitter">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"/></svg>
                </a>
                <a href="#" className="text-muted-foreground hover:text-primary transition-colors" aria-label="GitHub">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
                </a>
                <a href="#" className="text-muted-foreground hover:text-primary transition-colors" aria-label="LinkedIn">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                </a>
              </div>
            </div>

            {/* Product Links */}
            <div>
              <h4 className="font-bold text-sm tracking-wider uppercase text-foreground/80 mb-4">
                Producto
              </h4>
              <ul className="flex flex-col gap-3 text-sm text-muted-foreground">
                <li>
                  <Link href="/presentacion/funcionamiento" className="hover:text-primary transition-colors">
                    Cómo funciona
                  </Link>
                </li>
                <li>
                  <Link href="/presentacion/casos" className="hover:text-primary transition-colors">
                    Casos de uso
                  </Link>
                </li>
                <li>
                  <Link href="/presentacion/faq" className="hover:text-primary transition-colors">
                    Preguntas frecuentes
                  </Link>
                </li>
                <li>
                  <Link href="/presentacion/contacto" className="hover:text-primary transition-colors">
                    Hazte Beta Tester
                  </Link>
                </li>
              </ul>
            </div>

            {/* Company Links */}
            <div>
              <h4 className="font-bold text-sm tracking-wider uppercase text-foreground/80 mb-4">
                Empresa
              </h4>
              <ul className="flex flex-col gap-3 text-sm text-muted-foreground">
                <li>
                  <a href="#" className="hover:text-primary transition-colors">
                    Sobre nosotros
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-primary transition-colors">
                    Blog
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-primary transition-colors">
                    Carreras
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-primary transition-colors">
                    Prensa
                  </a>
                </li>
              </ul>
            </div>

            {/* Contact & Support */}
            <div>
              <h4 className="font-bold text-sm tracking-wider uppercase text-foreground/80 mb-4">
                Contacto & Soporte
              </h4>
              <ul className="flex flex-col gap-3.5 text-sm text-muted-foreground">
                <li className="flex items-center gap-2">
                  <Mail size={16} className="text-cyan-500" />
                  <a href="mailto:contacto@kognitoai.cloud" className="hover:text-primary transition-colors">
                    contacto@kognitoai.cloud
                  </a>
                </li>
                <li className="flex items-center gap-2">
                  <Shield size={16} className="text-cyan-500" />
                  <span>Privacidad y Soberanía</span>
                </li>
                <li className="flex items-center gap-2">
                  <Cpu size={16} className="text-cyan-500" />
                  <span>Soporte Integración 24/7</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-border/40 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
            <p>© {new Date().getFullYear()} KognitoAI. Todos los derechos reservados.</p>
            <div className="flex gap-6">
              <a href="#" className="hover:text-primary transition-colors">Términos de servicio</a>
              <a href="#" className="hover:text-primary transition-colors">Política de privacidad</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}