import React from "react";
import Link from "next/link";

interface PresentationNavProps {
  currentPage?: string;
}

export default function PresentationNav({ currentPage }: PresentationNavProps) {
  const navItems = [
    { href: "/presentacion", label: "Inicio", id: "inicio" },
    { href: "/presentacion/funcionamiento", label: "Cómo funciona", id: "funcionamiento" },
    { href: "/presentacion/casos", label: "Casos de uso", id: "casos" },
    { href: "/presentacion/faq", label: "FAQ", id: "faq" },
    { href: "/presentacion/contacto", label: "Contacto", id: "contacto" },
  ];

  return (
    <nav className="flex flex-wrap justify-center gap-2 mb-8">
      {navItems.map((item) => {
        const isActive = currentPage === item.id;
        return (
          <Link
            key={item.id}
            href={item.href}
            className={`px-6 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
              isActive
                ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg"
                : "bg-white/50 hover:bg-white/70 text-gray-700 border border-border/30"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
