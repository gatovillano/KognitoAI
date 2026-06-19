import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { UserSettingsProvider } from "@/contexts/UserSettingsContext";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Toaster } from "@/components/ui/sonner"; // Importar Toaster de sonner
import AnalyticsTracker from "@/components/AnalyticsTracker";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                var reloadKey = 'next_chunk_reload_count';
                function checkError(msg) {
                  if (msg && (
                    msg.indexOf('ChunkLoadError') !== -1 ||
                    msg.indexOf('Loading chunk') !== -1 ||
                    msg.indexOf('Failed to fetch dynamically imported module') !== -1 ||
                    msg.indexOf('error loading dynamically imported module') !== -1
                  )) {
                    var reloadCount = parseInt(sessionStorage.getItem(reloadKey) || '0', 10);
                    if (reloadCount < 2) {
                      sessionStorage.setItem(reloadKey, (reloadCount + 1).toString());
                      console.warn('ChunkLoadError detectado. Recargando la página para obtener los assets más recientes...');
                      window.location.reload();
                    }
                  }
                }
                // Capturar errores de carga en fase de captura (importante para scripts)
                window.addEventListener('error', function(e) {
                  checkError(e.message || (e.target && e.target.src) || '');
                }, true);
                // Capturar promesas rechazadas (fallos de dynamic import)
                window.addEventListener('unhandledrejection', function(e) {
                  var reason = e.reason && (e.reason.message || e.reason.toString()) || '';
                  checkError(reason);
                });
                // Limpiar el contador tras 5 segundos de carga exitosa
                window.addEventListener('load', function() {
                  setTimeout(function() {
                    sessionStorage.removeItem(reloadKey);
                  }, 5000);
                });
              })();
            `
          }}
        />
      </head>
      <body className={inter.className}>
        <AuthProvider>
          <UserSettingsProvider>
            <ThemeProvider
              attribute="class"
              defaultTheme="system"
              enableSystem
              disableTransitionOnChange
            >
              <Suspense fallback={null}>
                <AnalyticsTracker />
              </Suspense>
              {children}
            </ThemeProvider>
          </UserSettingsProvider>
          <Toaster richColors position="top-right" /> {/* Configurar Toaster de sonner */}
        </AuthProvider>
      </body>
    </html>
  );
}