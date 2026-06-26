import React from "react";
import Image from "next/image";
import Link from "next/link";

interface PresentationLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  showLogo?: boolean;
  showNav?: boolean;
}

export default function PresentationLayout({
  children,
  title,
  subtitle,
  showLogo = true,
  showNav = true,
}: PresentationLayoutProps) {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-cyan-50 via-white to-blue-100 p-0 md:p-8 relative overflow-hidden">
      {/* Fondo decorativo */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute -top-32 -left-32 w-[600px] h-[600px] bg-gradient-to-br from-cyan-400/30 to-blue-300/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-gradient-to-tr from-blue-400/20 to-cyan-200/10 rounded-full blur-2xl" />
      </div>
      
      <div className="relative z-10 max-w-5xl w-full flex flex-col items-center gap-8">
        <div className="w-full flex flex-col items-center bg-white/70 backdrop-blur-2xl rounded-[2.5rem] shadow-2xl border border-border/40 p-12 md:p-16 mt-8">
          {showLogo && (
            <Image 
              src="/logo-simple.png" 
              alt="Kognito AI Logo" 
              width={120} 
              height={120} 
              className="mb-6 drop-shadow-xl hover:scale-105 transition-transform duration-300" 
            />
          )}
          <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 mb-2 text-center tracking-tight leading-tight">
            {title}
          </h1>
          {subtitle && (
            <span className="inline-block bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-lg font-semibold px-6 py-2 rounded-full shadow-lg mb-6">
              {subtitle}
            </span>
          )}
          {children}
        </div>
      </div>
    </main>
  );
}
