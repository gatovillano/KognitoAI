# Guía de Implementación Técnica de KognitoAI

## 1. Introducción

Esta guía está diseñada para equipos técnicos que buscan implementar y operar KognitoAI. Cubre los requisitos técnicos, los pasos de instalación, la arquitectura del sistema y ejemplos de código para facilitar una integración y despliegue exitosos.

## 2. Requisitos Técnicos

Aquí se detallarán los requisitos de hardware, software y red necesarios para una implementación óptima de KognitoAI.

### 2.1. Requisitos de Hardware
Para un rendimiento óptimo, especialmente con modelos de lenguaje grandes (LLMs) y procesamiento de grafos, se recomienda la siguiente configuración de hardware:

*   **CPU**: Múltiples núcleos (ej. 8+ núcleos) para manejar la concurrencia de la API y las operaciones de procesamiento.
*   **RAM**: Mínimo 16 GB, preferiblemente 32 GB o más, especialmente si se ejecutan varios componentes o modelos grandes en el mismo servidor. Neo4j y los modelos de embeddings pueden consumir bastante memoria.
*   **GPU**: Una GPU compatible con CUDA (NVIDIA) es **altamente recomendada** para acelerar el procesamiento de embeddings y ciertas operaciones de LLMs (si se utilizan modelos locales o se delega a la GPU). La configuración de `docker-compose.yml` ya incluye soporte para GPU de NVIDIA.
*   **Almacenamiento**: SSD de alta velocidad (NVMe recomendado) para el sistema operativo, las bases de datos (PostgreSQL, Neo4j) y el almacenamiento de modelos, para asegurar un acceso rápido a los datos. Espacio disponible de al menos 100 GB para el sistema y datos.

### 2.2. Requisitos de Software
KognitoAI se basa en una arquitectura de microservicios contenerizada.

*   **Sistema Operativo**: Linux (Ubuntu 20.04+, Debian 11+, etc.) es el entorno de desarrollo y despliegue preferido.
*   **Docker y Docker Compose**: Versión 20.10.0+ y 1.29.0+ respectivamente. Son esenciales para la orquestación de los servicios.
*   **Python**: Versión 3.9+ para el desarrollo de la API y los servicios del bot.
*   **Node.js y npm/yarn**: Para el desarrollo y construcción del frontend (Next.js).

### 2.3. Requisitos de Red
*   **Puertos Abiertos**:
    *   `5432` (TCP): PostgreSQL
    *   `7474` (TCP): Neo4j Browser (interfaz web)
    *   `7687` (TCP): Neo4j Bolt (conexión de la API)
    *   `6379` (TCP): Redis
    *   `8889` (TCP, configurable): API de KognitoAI
    *   `8880` (TCP, configurable): Frontend de la WebApp
    *   `9094` (TCP, configurable): Cliente de Telegram (interno)
*   **Conectividad a Internet**: Requerida para acceder a APIs externas (Google Gemini, OpenAI, Anthropic, Brave Search, Tavily, etc.) y para la descarga de imágenes de Docker y paquetes de Python/Node.js.
*   **DNS**: Configuración adecuada de DNS si se utilizan dominios personalizados para la API o el frontend.
*   **Proxy Inverso**: Se recomienda un proxy inverso como Nginx (ejemplo `nginx.conf` provisto) para manejar SSL/TLS, balanceo de carga y enrutamiento de solicitudes a los servicios de Docker.

## 3. Pasos de Instalación

Esta sección proporcionará instrucciones detalladas paso a paso para la instalación de KognitoAI.

### 3.1. Preparación del Entorno

1.  **Instalar Docker y Docker Compose**: Asegúrate de tener Docker Engine (versión 20.10.0+) y Docker Compose (versión 1.29.0+) instalados en tu sistema. Puedes seguir las guías oficiales de Docker para tu sistema operativo.
2.  **Instalar Git**: Necesario para clonar el repositorio de KognitoAI.
3.  **Configurar GPU (Opcional pero Recomendado)**: Si planeas usar la GPU, asegúrate de tener los drivers de NVIDIA y Docker con soporte para CUDA instalados. El `docker-compose.yml` ya está configurado para utilizar `nvidia-container-toolkit`.

### 3.2. Clonar el Repositorio

Clona el repositorio de KognitoAI a tu máquina local:

```bash
git clone https://github.com/tu-organizacion/KognitoAI.git # Reemplaza con la URL real del repositorio
cd KognitoAI
```

### 3.3. Configuración de Variables de Entorno

KognitoAI utiliza un archivo `.env` para gestionar sus configuraciones.

1.  **Crear el archivo `.env`**: Copia el archivo de ejemplo y nómbralo `.env` en la raíz del proyecto:
    ```bash
    cp .env.example .env
    ```
2.  **Editar `.env`**: Abre el archivo `.env` y configura las variables según tus necesidades. Las más críticas incluyen:
    *   **Variables de Base de Datos (PostgreSQL)**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
    *   **Variables de Neo4j**: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (aunque `NEO4J_AUTH: none` en `docker-compose.yml` puede simplificar esto para desarrollo).
    *   **Tokens y Claves de API**: `TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`, `GOOGLE_PROJECT_ID`, `GOOGLE_PROJECT_LOCATION`, `BRAVE_SEARCH_API_KEY`, `TAVILY_API_KEY`, etc.
    *   **Modelos de LLM**: `LLM_MODEL`, `FAST_LLM_MODEL`, `GOOGLE_EMBEDDING_MODEL_NAME`, `OPENAI_MODEL_NAME`, etc.
    *   **URLs de Servicios**: `API_SERVER_URL` (la URL pública de tu API), `TELEGRAM_WEBAPP_URL`.
    *   **Puertos**: `API_PORT`, `FRONTEND_PORT` si necesitas cambiarlos de los valores por defecto (8889 y 8880 respectivamente).

### 3.4. Despliegue con Docker Compose

Una vez configurado el archivo `.env`, puedes construir y levantar todos los servicios:

1.  **Construir las imágenes de Docker**:
    ```bash
    docker compose build
    ```
    Este paso puede tardar un tiempo, ya que descarga las dependencias y construye las imágenes de `core`, `telegram_client` y `frontend`.

2.  **Iniciar los servicios**:
    ```bash
    docker compose up -d
    ```
    El flag `-d` ejecuta los contenedores en segundo plano. Docker Compose se encargará de iniciar PostgreSQL, Neo4j, Redis, el servicio `core` (API), el `telegram_client` y el `frontend`.

### 3.5. Verificación de la Instalación

Una vez que los servicios estén en ejecución, puedes verificar su estado:

*   **API de KognitoAI**: Accede a la documentación de la API en `http://localhost:8889/docs` (o el puerto que hayas configurado en `API_PORT`).
*   **Frontend de la WebApp**: Abre tu navegador y ve a `http://localhost:8880` (o el puerto que hayas configurado en `FRONTEND_PORT`).
*   **Neo4j Browser**: Accede a la interfaz web de Neo4j en `http://localhost:7474`. Puedes usar las credenciales que configuraste o las por defecto si `NEO4J_AUTH` está deshabilitado.
*   **Logs**: Para ver los logs de los servicios y verificar que todo esté funcionando correctamente:
    ```bash
    docker compose logs -f
    ```
    Presiona `Ctrl+C` para salir de los logs.

### 3.6. Migraciones de Base de Datos y Creación de Índices

El servicio `core` está configurado para esperar a que las bases de datos estén listas. Las migraciones de PostgreSQL se gestionan con Alembic, y los índices de Neo4j se inicializan automáticamente a través del servicio `init_neo4j` definido en `docker-compose.yml`.

## 4. Arquitectura del Sistema

Se presentará un diagrama de arquitectura general de KognitoAI, junto con una descripción de sus componentes principales y cómo interactúan entre sí.

### 4.1. Diagrama de Arquitectura

El siguiente diagrama ilustra la arquitectura de alto nivel de KognitoAI, mostrando cómo interactúan los diferentes servicios contenerizados.

```mermaid
graph TD
    User[Usuario Final] -->|HTTPS| Nginx[Proxy Inverso (Nginx)]
    Nginx -->|HTTP| Frontend[Frontend (Next.js)]
    Nginx -->|HTTP| API[Core API (FastAPI)]
    
    subgraph "KognitoAI Core Services"
        API -->|SQL| Postgres[(PostgreSQL + pgvector)]
        API -->|Bolt| Neo4j[(Neo4j Graph DB)]
        API -->|Cache| Redis[(Redis)]
        API <-->|Internal HTTP| TelegramClient[Cliente Telegram]
    end
    
    TelegramClient -->|Telegram API| TelegramServers[Servidores de Telegram]
    Frontend -->|API Calls| API
```

### 4.2. Componentes Clave

*   **Core API (FastAPI)**: El cerebro del sistema. Maneja la lógica de negocio, la orquestación de LLMs, la gestión de memoria (RAG y Grafos), y expone los endpoints REST y WebSocket.
*   **Frontend (Next.js)**: La interfaz de usuario web para interactuar con el sistema, visualizar datos y gestionar configuraciones.
*   **PostgreSQL + pgvector**: Base de datos relacional principal que almacena usuarios, sesiones, documentos y vectores (embeddings) para la búsqueda semántica.
*   **Neo4j**: Base de datos de grafos utilizada para modelar relaciones complejas entre entidades, conceptos y documentos, potenciando el "Knowledge Graph".
*   **Redis**: Sistema de caché en memoria para sesiones, colas de tareas y almacenamiento temporal de alta velocidad.
*   **Cliente Telegram**: Servicio dedicado a gestionar la interacción con la API de Telegram, permitiendo que el bot responda mensajes y ejecute comandos.

## 5. Ejemplos de Código

A continuación, se presentan ejemplos de cómo interactuar con la API de KognitoAI.

### 5.1. Integración con APIs

Ejemplo de cómo realizar una petición para generar un archivo HTML a través de la API, utilizando Python y la librería `requests`.

```python
import requests

# Configuración
API_URL = "http://localhost:8889/api/generate-html"
TOKEN = "tu_token_de_acceso_jwt" # Obtener mediante autenticación

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "content": "# Reporte Mensual\n\nEste es un reporte generado automáticamente...",
    "title": "Reporte Enero 2024",
    "include_css": True
}

# Realizar la petición
response = requests.post(API_URL, json=data, headers=headers)

if response.status_code == 200:
    # Guardar el archivo recibido
    filename = response.headers.get("Content-Disposition").split("filename=")[1]
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"Archivo generado exitosamente: {filename}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### 5.2. Definición de Esquemas (Pydantic)

Si estás desarrollando extensiones o herramientas para KognitoAI, utilizarás Pydantic para definir la estructura de tus datos, asegurando validación y tipado fuerte.

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserSettingsUpdate(BaseModel):
    """
    Modelo para actualizar las preferencias del usuario.
    """
    name: Optional[str] = Field(None, description="Nombre completo del usuario")
    email: Optional[EmailStr] = Field(None, description="Dirección de correo electrónico")
    language: Optional[str] = Field("es", description="Código de idioma preferido (ej. 'es', 'en')")
    notifications_enabled: Optional[bool] = Field(True, description="Activar o desactivar notificaciones")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Ana García",
                "email": "ana@ejemplo.com",
                "language": "es",
                "notifications_enabled": False
            }
        }
```

## 6. Mantenimiento y Operación

Para garantizar la estabilidad y el rendimiento de KognitoAI a largo plazo, se recomiendan las siguientes prácticas de mantenimiento.

### 6.1. Gestión de Logs
El monitoreo de logs es esencial para detectar anomalías. Puedes ver los logs en tiempo real de todos los servicios o de uno específico:

```bash
# Ver logs de todos los servicios
docker compose logs -f --tail=100

# Ver logs solo del servicio API (core)
docker compose logs -f core
```

### 6.2. Actualizaciones del Sistema
Para actualizar KognitoAI a la última versión del código fuente:

1.  **Descargar cambios**: `git pull origin main`
2.  **Reconstruir imágenes**: `docker compose build` (necesario si hubo cambios en dependencias).
3.  **Reiniciar servicios**: `docker compose up -d` (recreará solo los contenedores necesarios).
4.  **Verificar migraciones**: El servicio `core` aplicará automáticamente las migraciones de Alembic al iniciarse.

### 6.3. Respaldos (Backups)
Los datos críticos residen en los volúmenes de Docker. Se recomienda configurar respaldos automáticos de:
*   **PostgreSQL (`db_data`)**: Contiene usuarios, historial de chat y embeddings.
*   **Neo4j (`neo4j_data`)**: Contiene el Grafo de Conocimiento.
*   **Carpeta `media/`**: Si se almacenan archivos generados o subidos por usuarios.

### 6.4. Limpieza de Archivos Temporales
El sistema genera archivos temporales (HTML, audios, etc.). Existe un endpoint de administración para limpieza manual si el espacio en disco es un problema:
*   `POST /api/admin/cleanup-files` (Requiere autenticación de admin).

## 7. Solución de Problemas (Troubleshooting)

Aquí listamos los problemas más frecuentes y sus soluciones.

### 7.1. El servicio 'core' no inicia o se reinicia constantemente
*   **Causa probable**: Falta de conexión a la base de datos o variables de entorno faltantes.
*   **Solución**: Revisa los logs con `docker compose logs core`. Verifica que `DATABASE_URL` en el `.env` sea correcta y que el contenedor `db` esté en estado `healthy`.

### 7.2. Errores de Autenticación en Neo4j
*   **Síntoma**: Logs indicando `Neo.ClientError.Security.Unauthorized`.
*   **Solución**: Verifica que las credenciales `NEO4J_USER` y `NEO4J_PASSWORD` en tu `.env` coincidan con la configuración del contenedor. Si es un entorno de desarrollo nuevo, intenta borrar el volumen `neo4j_data` para reiniciar la contraseña.

### 7.3. La GPU no es detectada
*   **Síntoma**: El procesamiento de embeddings es lento o los logs muestran advertencias sobre CPU.
*   **Solución**:
    1.  Asegúrate de tener instalado `nvidia-container-toolkit` en el host.
    2.  Verifica dentro del contenedor: `docker compose exec core nvidia-smi`.
    3.  Si falla, revisa la sección `deploy` -> `resources` en `docker-compose.yml`.

### 7.4. Errores 429 (Rate Limit) en LLMs
*   **Síntoma**: La IA no responde o devuelve errores de cuota.
*   **Solución**: Revisa tus cuotas en Google Cloud Console o OpenAI Platform. Considera configurar `RATE_LIMIT_ENABLED=True` en el `.env` para controlar el flujo de peticiones desde KognitoAI.