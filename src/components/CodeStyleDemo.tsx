'use client';

import { MarkdownRenderer } from './MarkdownRenderer';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function CodeStyleDemo() {
  const codeExamples = {
    javascript: `\`\`\`javascript
// Ejemplo de JavaScript moderno con ES6+
const fetchUserData = async (userId) => {
  try {
    const response = await fetch(\`/api/users/\${userId}\`);
    const userData = await response.json();
    
    return {
      ...userData,
      isActive: userData.lastLogin > Date.now() - 86400000,
      displayName: userData.firstName + ' ' + userData.lastName
    };
  } catch (error) {
    console.error('Error fetching user data:', error);
    throw new Error('Failed to load user information');
  }
};

// Uso de destructuring y arrow functions
const users = [
  { id: 1, name: 'Ana García', role: 'admin' },
  { id: 2, name: 'Carlos López', role: 'user' },
  { id: 3, name: 'María Rodríguez', role: 'moderator' }
];

const activeAdmins = users
  .filter(({ role }) => role === 'admin')
  .map(user => ({ ...user, isOnline: true }));
\`\`\``,

    python: `\`\`\`python
# Ejemplo de Python con análisis de datos
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class UserAnalytics:
    user_id: int
    sessions: List[Dict]
    total_time: float
    
    def calculate_engagement_score(self) -> float:
        """Calcula el score de engagement basado en sesiones."""
        if not self.sessions:
            return 0.0
            
        avg_session_time = np.mean([s['duration'] for s in self.sessions])
        session_frequency = len(self.sessions) / 30  # por mes
        
        return min(avg_session_time * session_frequency * 0.1, 10.0)

def process_user_data(df: pd.DataFrame) -> pd.DataFrame:
    """Procesa datos de usuarios y calcula métricas."""
    # Limpieza de datos
    df_clean = df.dropna(subset=['user_id', 'session_start'])
    
    # Cálculo de métricas agregadas
    user_metrics = df_clean.groupby('user_id').agg({
        'session_duration': ['mean', 'sum', 'count'],
        'pages_visited': 'sum',
        'conversion_events': 'sum'
    }).round(2)
    
    return user_metrics

# Ejemplo de uso con list comprehension
active_users = [
    UserAnalytics(uid, sessions, total)
    for uid, sessions, total in user_data
    if total > 3600  # más de 1 hora total
]
\`\`\``,

    typescript: `\`\`\`typescript
// Ejemplo de TypeScript con tipos avanzados
interface ApiResponse<T> {
  data: T;
  status: 'success' | 'error';
  message?: string;
  timestamp: Date;
}

type UserRole = 'admin' | 'moderator' | 'user' | 'guest';

interface User {
  id: number;
  email: string;
  profile: {
    firstName: string;
    lastName: string;
    avatar?: string;
  };
  roles: UserRole[];
  preferences: Record<string, unknown>;
  createdAt: Date;
  lastActive: Date | null;
}

// Generic service class con error handling
class ApiService<T> {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  async get<R = T>(endpoint: string): Promise<ApiResponse<R>> {
    try {
      const response = await fetch(\`\${this.baseUrl}\${endpoint}\`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': \`Bearer \${this.getToken()}\`
        }
      });
      
      if (!response.ok) {
        throw new Error(\`HTTP \${response.status}: \${response.statusText}\`);
      }
      
      const data = await response.json();
      return {
        data,
        status: 'success',
        timestamp: new Date()
      };
    } catch (error) {
      return {
        data: null as unknown as R,
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date()
      };
    }
  }
  
  private getToken(): string {
    return localStorage.getItem('authToken') ?? '';
  }
}

// Uso con tipos específicos
const userService = new ApiService<User>('/api');
const usersResponse = await userService.get<User[]>('/users');
\`\`\``,

    css: `\`\`\`css
/* Ejemplo de CSS moderno con Grid y Flexbox */
:root {
  --primary-color: #3b82f6;
  --secondary-color: #8b5cf6;
  --accent-color: #f59e0b;
  --text-color: #1f2937;
  --bg-color: #ffffff;
  --border-radius: 0.75rem;
  --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.dashboard-layout {
  display: grid;
  grid-template-areas: 
    "header header header"
    "sidebar main aside"
    "footer footer footer";
  grid-template-columns: 250px 1fr 300px;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
  gap: 1rem;
  padding: 1rem;
}

.card {
  background: linear-gradient(135deg, 
    var(--bg-color) 0%, 
    rgba(59, 130, 246, 0.05) 100%);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  padding: 1.5rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(59, 130, 246, 0.1);
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  border-color: var(--primary-color);
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: white;
  border: none;
  border-radius: var(--border-radius);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.button:hover::before {
  left: 100%;
}

@media (max-width: 768px) {
  .dashboard-layout {
    grid-template-areas: 
      "header"
      "main"
      "sidebar"
      "aside"
      "footer";
    grid-template-columns: 1fr;
  }
}
\`\`\``,

    json: `\`\`\`json
{
  "name": "kognito-ai-demo",
  "version": "2.1.0",
  "description": "Demostración de estilos de código mejorados",
  "main": "index.js",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint . --ext .ts,.tsx,.js,.jsx",
    "test": "jest --watch",
    "test:ci": "jest --ci --coverage",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "@radix-ui/react-dialog": "^1.1.14",
    "@radix-ui/react-tabs": "^1.1.12",
    "framer-motion": "^12.19.1",
    "next": "^15.3.4",
    "react": "^19.1.0",
    "tailwindcss": "^3.4.17"
  },
  "devDependencies": {
    "@types/node": "^24.0.3",
    "@types/react": "^19.1.8",
    "eslint": "^9.29.0",
    "typescript": "^5.8.3"
  },
  "keywords": [
    "nextjs",
    "react",
    "typescript",
    "tailwindcss",
    "ai",
    "chat",
    "markdown"
  ],
  "author": {
    "name": "KognitoAI Team",
    "email": "team@kognito.ai",
    "url": "https://kognito.ai"
  },
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/gatovillano/KognitoAI.git"
  },
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  }
}
\`\`\``,

    bash: `\`\`\`bash
#!/bin/bash
# Script de despliegue automatizado para KognitoAI

set -euo pipefail  # Salir en caso de error

# Configuración
PROJECT_NAME="kognito-ai"
DOCKER_IMAGE="kognito-ai:latest"
BACKUP_DIR="/backups/\$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/var/log/deploy.log"

# Colores para output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Función de logging
log() {
    echo -e "\$(date '+%Y-%m-%d %H:%M:%S') - \$1" | tee -a "\$LOG_FILE"
}

# Función de error
error_exit() {
    log "\${RED}ERROR: \$1\${NC}"
    exit 1
}

# Verificar dependencias
check_dependencies() {
    log "\${YELLOW}Verificando dependencias...\${NC}"
    
    command -v docker >/dev/null 2>&1 || error_exit "Docker no está instalado"
    command -v git >/dev/null 2>&1 || error_exit "Git no está instalado"
    command -v npm >/dev/null 2>&1 || error_exit "npm no está instalado"
    
    log "\${GREEN}✓ Todas las dependencias están disponibles\${NC}"
}

# Crear backup
create_backup() {
    log "\${YELLOW}Creando backup...\${NC}"
    
    mkdir -p "\$BACKUP_DIR"
    
    # Backup de la base de datos
    docker exec postgres pg_dump -U postgres kognito_db > "\$BACKUP_DIR/database.sql"
    
    # Backup de archivos de configuración
    cp -r ./config "\$BACKUP_DIR/"
    cp .env "\$BACKUP_DIR/"
    
    log "\${GREEN}✓ Backup creado en \$BACKUP_DIR\${NC}"
}

# Desplegar aplicación
deploy() {
    log "\${YELLOW}Iniciando despliegue...\${NC}"
    
    # Pull del código más reciente
    git pull origin main || error_exit "Error al actualizar código"
    
    # Instalar dependencias
    npm ci || error_exit "Error al instalar dependencias"
    
    # Build de la aplicación
    npm run build || error_exit "Error en el build"
    
    # Construir imagen Docker
    docker build -t "\$DOCKER_IMAGE" . || error_exit "Error al construir imagen Docker"
    
    # Detener contenedor anterior
    docker stop "\$PROJECT_NAME" 2>/dev/null || true
    docker rm "\$PROJECT_NAME" 2>/dev/null || true
    
    # Ejecutar nuevo contenedor
    docker run -d \\
        --name "\$PROJECT_NAME" \\
        --restart unless-stopped \\
        -p 3000:3000 \\
        --env-file .env \\
        "\$DOCKER_IMAGE" || error_exit "Error al ejecutar contenedor"
    
    log "\${GREEN}✓ Despliegue completado exitosamente\${NC}"
}

# Función principal
main() {
    log "\${GREEN}=== Iniciando despliegue de \$PROJECT_NAME ===\${NC}"
    
    check_dependencies
    create_backup
    deploy
    
    log "\${GREEN}=== Despliegue completado ===\${NC}"
}

# Ejecutar función principal
main "\$@"
\`\`\``
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Demostración de Estilos de Código Mejorados
        </h1>
        <p className="text-muted-foreground">
          Nuevas fuentes, colores y efectos visuales para una mejor experiencia de lectura
        </p>
      </div>

      <Tabs defaultValue="javascript" className="w-full">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="javascript">JavaScript</TabsTrigger>
          <TabsTrigger value="python">Python</TabsTrigger>
          <TabsTrigger value="typescript">TypeScript</TabsTrigger>
          <TabsTrigger value="css">CSS</TabsTrigger>
          <TabsTrigger value="json">JSON</TabsTrigger>
          <TabsTrigger value="bash">Bash</TabsTrigger>
        </TabsList>

        {Object.entries(codeExamples).map(([language, code]) => (
          <TabsContent key={language} value={language}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="text-2xl">
                    {language === 'javascript' && '🟨'}
                    {language === 'python' && '🐍'}
                    {language === 'typescript' && '🔷'}
                    {language === 'css' && '🎨'}
                    {language === 'json' && '📋'}
                    {language === 'bash' && '⚡'}
                  </span>
                  Ejemplo de {language.charAt(0).toUpperCase() + language.slice(1)}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <MarkdownRenderer content={code} />
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Características Mejoradas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h3 className="font-semibold text-lg">🎨 Tipografía</h3>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Fuente JetBrains Mono con ligaduras</li>
                <li>• Mejor espaciado entre líneas</li>
                <li>• Tamaño optimizado para legibilidad</li>
                <li>• Fallbacks a Fira Code y otras fuentes</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-lg">🌈 Colores</h3>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Esquema inspirado en VS Code Dark+</li>
                <li>• Mejor contraste y legibilidad</li>
                <li>• Colores específicos por lenguaje</li>
                <li>• Soporte para modo claro y oscuro</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-lg">✨ Efectos Visuales</h3>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Gradientes sutiles en fondos</li>
                <li>• Animaciones suaves al hacer hover</li>
                <li>• Sombras y efectos de profundidad</li>
                <li>• Scrollbar personalizada</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-lg">🔧 Funcionalidad</h3>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Indicador de lenguaje automático</li>
                <li>• Botones de copia mejorados</li>
                <li>• Responsive design</li>
                <li>• Accesibilidad mejorada</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
