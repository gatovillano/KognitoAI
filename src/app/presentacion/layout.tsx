'use client';

import React, { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, ArrowRight, Shield, Cpu, Mail, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function PresentacionLayout({
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
    <div className="min-h-screen bg-background text-foreground relative overflow-hidden flex flex-col font-sans transition-colors duration-300">
      
      {/* Fondo de alta tecnología decorativo */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Luces de fondo (Glow Orbs) */}
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-500/10 dark:bg-cyan-500/5 rounded-full blur-[120px]" />
        <div className="absolute top-1/3 right-1/4 w-[600px] h-[600px] bg-blue-600/10 dark:bg-blue-600/5 rounded-full blur-[140px]" />
        <div className="absolute bottom-10 left-1/3 w-[400px] h-[400px] bg-purple-500/10 dark:bg-purple-500/5 rounded-full blur-[100px]" />
        
        {/* Rejilla de fondo Cyberpunk */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(128,128,128,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(128,128,128,0.03)_1px,transparent_1px)] bg-[size:4rem_4rem] dark:bg-[linear-gradient(to_right,rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.015)_1px,transparent_1px)]" />
      </div>

      {/* Floating Header */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          isScrolled
            ? "py-3 bg-background/80 backdrop-blur-xl border-b border-border/40 shadow-lg shadow-black/5 dark:shadow-black/20"
            : "py-6 bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          {/* Logo */}
          <Link href="/presentacion" className="flex items-center gap-3 group relative z-50">
            <div className="relative overflow-hidden w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-400 to-blue-600 p-0.5 shadow-md group-hover:scale-105 transition-transform duration-300">
              <div className="w-full h-full bg-slate-900 rounded-[10px] flex items-center justify-center overflow-hidden">
                <Image
                  src="/logo-simple.png"
                  alt="Kognito AI Logo"
                  width={32}
                  height={32}
                  className="object-contain"
                />
              </div>
            </div>
            <span className="font-extrabold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 dark:from-cyan-400 dark:via-blue-400 dark:to-cyan-300">
              KognitoAI
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 bg-muted/40 p-1.5 rounded-full border border-border/20 backdrop-blur-sm">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.name}
                  href={link.href}
                  className={`relative px-5 py-2 rounded-full text-sm font-semibold transition-all duration-300 ${
                    isActive
                      ? "text-foreground font-bold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      className="absolute inset-0 bg-background shadow-sm border border-border/40 rounded-full z-0"
                    />
                  )}
                  <span className="relative z-10">{link.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Actions Panel */}
          <div className="hidden md:flex items-center gap-4">
            <ThemeToggle />
            <Link href="/login">
              <Button className="rounded-full font-bold px-6 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white shadow-md shadow-cyan-500/10 hover:shadow-lg hover:shadow-cyan-500/20 hover:scale-[1.02] transition-all duration-200">
                Iniciar sesión
              </Button>
            </Link>
          </div>

          {/* Mobile menu trigger */}
          <div className="flex md:hidden items-center gap-3">
            <ThemeToggle />
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-foreground focus:outline-none z-50"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile drawer menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-40 bg-background/95 backdrop-blur-2xl md:hidden pt-28 px-6 pb-10 flex flex-col justify-between"
          >
            <div className="flex flex-col gap-6">
              {navLinks.map((link, idx) => {
                const isActive = pathname === link.href;
                return (
                  <motion.div
                    key={link.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <Link
                      href={link.href}
                      className={`text-2xl font-bold flex items-center justify-between py-2 border-b border-border/30 ${
                        isActive
                          ? "text-primary border-primary/30"
                          : "text-foreground/80 hover:text-foreground"
                      }`}
                    >
                      <span>{link.name}</span>
                      <ArrowRight size={18} className="opacity-50" />
                    </Link>
                  </motion.div>
                );
              })}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex flex-col gap-4 mt-8"
            >
              <Link href="/login" className="w-full">
                <Button className="w-full h-12 rounded-full font-bold text-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg">
                  Iniciar sesión
                </Button>
              </Link>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Space with Page Transition */}
      <main className="flex-grow z-10 pt-28 pb-16 px-4 md:px-8">
        <div className="max-w-7xl mx-auto w-full">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* High-Fidelity Premium Footer */}
      <footer className="z-10 border-t border-border/40 bg-card/30 backdrop-blur-md transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-6 py-12 md:py-16">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
            
            {/* Brand Block */}
            <div className="flex flex-col gap-4 md:col-span-2">
              <Link href="/presentacion" className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-400 to-blue-600 p-0.5">
                  <div className="w-full h-full bg-slate-900 rounded-[7px] flex items-center justify-center overflow-hidden">
                    <Image
                      src="/logo-simple.png"
                      alt="Kognito AI Logo"
                      width={24}
                      height={24}
                    />
                  </div>
                </div>
                <span className="font-extrabold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-cyan-500 to-blue-600 dark:from-cyan-400 dark:to-blue-400">
                  KognitoAI
                </span>
              </Link>
              <p className="text-muted-foreground text-sm max-w-sm leading-relaxed">
                El Exocerebro Digital y ecosistema de Inteligencia Aumentada diseñado para replicar tu razonamiento y proteger tu soberanía cognitiva.
              </p>
              <div className="flex items-center gap-2 text-xs text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full w-fit">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                Todos los sistemas operando al 100%
              </div>
            </div>

            {/* Links Block 1 */}
            <div className="flex flex-col gap-4">
              <h4 className="font-bold text-sm tracking-wider uppercase text-foreground/80">
                Navegación
              </h4>
              <ul className="flex flex-col gap-2.5 text-sm">
                <li>
                  <Link href="/presentacion/funcionamiento" className="text-muted-foreground hover:text-primary transition-colors">
                    Cómo funciona
                  </Link>
                </li>
                <li>
                  <Link href="/presentacion/casos" className="text-muted-foreground hover:text-primary transition-colors">
                    Casos de Uso
                  </Link>
                </li>
                <li>
                  <Link href="/presentacion/faq" className="text-muted-foreground hover:text-primary transition-colors">
                    Preguntas Frecuentes
                  </Link>
                </li>
                <li>
                  <Link href="/presentacion/contacto" className="text-muted-foreground hover:text-primary transition-colors">
                    Solicitar Demo
                  </Link>
                </li>
              </ul>
            </div>

            {/* Support Block */}
            <div className="flex flex-col gap-4">
              <h4 className="font-bold text-sm tracking-wider uppercase text-foreground/80">
                Contacto & Soporte
              </h4>
              <ul className="flex flex-col gap-3.5 text-sm text-muted-foreground">
                <li className="flex items-center gap-2">
                  <Mail size={16} className="text-cyan-500" />
                  <a href="mailto:contacto@kognitoai.com" className="hover:text-primary transition-colors">
                    contacto@kognitoai.com
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
