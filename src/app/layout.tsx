import type { Metadata } from "next";
import { Lato } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { UserSettingsProvider } from "@/contexts/UserSettingsContext";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Toaster } from "@/components/ui/sonner"; // Importar Toaster de sonner

const lato = Lato({ 
  subsets: ["latin"], 
  variable: "--font-sans",
  weight: ["400", "700", "900"] 
});

export const metadata: Metadata = {
  title: "Kognito AI",
  description: "Plataforma de IA para productividad y colaboración",
  icons: {
    icon: "/logo-simple.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode; }>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={lato.className}>
        <AuthProvider>
          <UserSettingsProvider>
            <ThemeProvider
              attribute="class"
              defaultTheme="system"
              enableSystem
              disableTransitionOnChange
            >
              {children}
            </ThemeProvider>
          </UserSettingsProvider>
          <Toaster richColors position="top-right" /> {/* Configurar Toaster de sonner */}
        </AuthProvider>
      </body>
    </html>
  );
}