"use client";

import dynamic from "next/dynamic";

// Importar Toaster de sonner solo en el cliente para evitar errores durante prerendering/SSG
const Toaster = dynamic(
  () => import("@/components/ui/sonner").then((mod) => mod.Toaster),
  {
    ssr: false,
    loading: () => null,
  }
);

interface ToasterWrapperProps {
  richColors?: boolean;
  position?: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "top-center" | "bottom-center";
}

export default function ToasterWrapper({ richColors, position = "top-right" }: ToasterWrapperProps) {
  return <Toaster richColors={richColors} position={position} />;
}