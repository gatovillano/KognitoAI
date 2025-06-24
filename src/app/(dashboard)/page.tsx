// En: src/app/(dashboard)/page.tsx
import Image from 'next/image';

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center h-full">
      <Image src="/logo-completo.png" alt="Kognito AI Labs" width={200} height={200} />
      <h1 className="text-4xl font-bold mt-4 tracking-tight">Bienvenido a Kognito AI</h1>
      <p className="text-muted-foreground mt-2">Selecciona una conversación o crea una nueva para comenzar.</p>
    </div>
  );
}