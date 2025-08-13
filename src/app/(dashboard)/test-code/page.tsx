'use client';

import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TestCodePage() {
  const testCode = `
# Prueba de Estilos de Código

Aquí tienes algunos ejemplos de código para probar los nuevos estilos:

## JavaScript
\`\`\`javascript
// Función de ejemplo con colores
const fetchData = async (url) => {
  try {
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
    throw new Error('Failed to fetch data');
  }
};

// Array con objetos
const users = [
  { id: 1, name: 'Ana', active: true },
  { id: 2, name: 'Carlos', active: false }
];
\`\`\`

## Python
\`\`\`python
# Función de Python con tipos
def calculate_total(items: list[dict]) -> float:
    """Calcula el total de una lista de items."""
    total = 0.0
    for item in items:
        if item.get('active', False):
            total += item.get('price', 0.0)
    return total

# Lista de comprensión
active_items = [item for item in items if item['active']]
\`\`\`

## CSS
\`\`\`css
/* Estilos modernos */
.container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.button {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.button:hover {
  background-color: #2563eb;
  transform: translateY(-2px);
}
\`\`\`

## JSON
\`\`\`json
{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0",
    "typescript": "^5.0.0"
  },
  "scripts": {
    "dev": "next dev",
    "build": "next build"
  },
  "keywords": ["react", "nextjs", "typescript"],
  "author": "KognitoAI",
  "license": "MIT"
}
\`\`\`

## Código inline
Aquí hay algunos ejemplos de código inline: \`const x = 42;\`, \`npm install\`, y \`console.log('Hello');\`.
`;

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">
            🎨 Prueba de Estilos de Código
          </CardTitle>
        </CardHeader>
        <CardContent>
          <MarkdownRenderer content={testCode} />
        </CardContent>
      </Card>
    </div>
  );
}
