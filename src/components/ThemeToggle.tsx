'use client';

import * as React from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  // Evitar hydration mismatch en Next.js SSR / Prerendering
  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button variant="outline" size="icon" className="h-[2.2rem] w-[2.2rem] rounded-xl border-border/40 bg-transparent">
        <span className="sr-only">Toggle theme</span>
      </Button>
    );
  }

  const currentTheme = theme === 'system' ? resolvedTheme : theme;

  return (
    <Button
      variant="outline"
      size="icon"
      className="h-[2.2rem] w-[2.2rem] rounded-xl border-border/40 hover:bg-muted/50 transition-colors bg-transparent shrink-0"
      onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
    >
      {currentTheme === 'dark' ? (
        <Sun className="h-[1.1rem] w-[1.1rem] text-amber-500 transition-all rotate-0 scale-100" />
      ) : (
        <Moon className="h-[1.1rem] w-[1.1rem] text-slate-700 dark:text-slate-350 transition-all rotate-0 scale-100" />
      )}
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
