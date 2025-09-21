import Image from 'next/image';

interface LoadingSpinnerProps {
  text?: string;
}

export function LoadingSpinner({ text = "Cargando..." }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      <div className="relative w-24 h-24 mb-4">
        <Image
          src="/logo-simple.png"
          alt="Cargando..."
          layout="fill"
          objectFit="contain"
          className="animate-pulse" // Animación suave de pulsación
        />
      </div>
      {text && <p className="text-muted-foreground mt-4">{text}</p>}
    </div>
  );
}