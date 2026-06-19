---
name: secure-email-recovery
description: |
  Skill robusta y moderna para recuperación segura de correos electrónicos.
  Soporta múltiples proveedores (Gmail, Outlook, Yahoo, IMAP personalizado)
  con autenticación OAuth2, manejo de errores avanzado, cache y optimización.
  Cumple con estándares de seguridad empresarial y mejores prácticas 2024.
version: 1.0.0
author: KognitoAI Team
category: communication
tags:
  - email
  - imap
  - oauth2
  - recovery
  - security
  - gmail
  - outlook
  - productivity
---

# Secure Email Recovery Skill

## 🎯 Objetivo

Proporcionar una **solución empresarial completa** para recuperación segura de correos electrónicos que:

- ✅ Soporta **múltiples proveedores** (Gmail, Outlook, Yahoo, IMAP personalizado)
- ✅ Utiliza **OAuth 2.0** como método de autenticación principal (sin contraseñas)
- ✅ Implementa **cache inteligente** para reducir llamadas a API
- ✅ Maneja **errores de forma elegante** con reintentos automáticos
- ✅ Cumple con **estándares de seguridad** empresariales
- ✅ Proporciona **API limpia y documentada**

---

## 🏗️ Arquitectura

```
secure-email-recovery/
├── SKILL.md                    # Esta documentación
├── __init__.py
└── scripts/
    ├── __init__.py
    ├── email_providers.py      # Configuraciones por proveedor
    ├── auth_manager.py         # Gestión OAuth2 y tokens
    ├── imap_client.py          # Cliente IMAP robusto
    ├── email_parser.py         # Parseo de emails (HTML/Plain)
    ├── cache_manager.py        # Cache con TTL
    ├── error_handler.py        # Manejo de errores estructurado
    ├── rate_limiter.py         # Control de tasa
    └── cli.py                  # Interfaz de línea de comandos
```

---

## 🔐 Seguridad

### Métodos de Autenticación (por orden de preferencia)

1. **OAuth 2.0 (Recomendado)**
   - Sin contraseñas almacenadas
   - Tokens de acceso de corta duración
   - Tokens de refresco de larga duración (encriptados)
   - Permisos granulares (scope: `https://mail.google.com/`)

2. **App Passwords (Solo cuando OAuth2 no esté disponible)**
   - Contraseñas específicas de aplicación
   - Generadas por el proveedor
   - Rotación automática recomendada

3. **Contraseñas de cuenta (NO recomendado)**
   - Solo para desarrollo/testing
   - Nunca en producción

### Almacenamiento de Credenciales

```python
# ✅ CORRECTO: Variables de entorno
import os
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")

# ❌ INCORRECTO: Hardcodeado
CLIENT_SECRET = "mi_cliente_secreto_123"
```

### Estándares Cumplidos

- **RFC 3501**: IMAP4rev1
- **RFC 7519**: JSON Web Tokens (JWT)
- **RFC 6749**: OAuth 2.0
- **OWASP**: Top 10 Security Principles
- **SOC 2**: Trust Services Criteria

---

## 📦 Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### requirements.txt

```
imaplib2>=3.6
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
msal>=1.24.0
oauthlib>=3.2.2
requests>=2.31.0
python-dotenv>=1.0.0
cachetools>=5.3.2
tenacity>=8.2.3
python-json-logger>=2.0.7
pydantic>=2.5.3
email-validator>=2.1.0
beautifulsoup4>=4.12.2
html2text>=2024.2.26
lxml>=4.9.3
```

---

## 🚀 Uso Rápido

### Ejemplo 1: Recuperar últimos 10 emails de Gmail

```python
from scripts.email_recovery import EmailRecovery

# Inicializar cliente
client = EmailRecovery(provider="gmail")

# Obtener emails
emails = client.get_recent_emails(limit=10, folder="INBOX")

for email in emails:
    print(f"De: {email.from_}")
    print(f"Asunto: {email.subject}")
    print(f"Fecha: {email.date}")
    print(f"Preview: {email.snippet[:200]}")
```

### Ejemplo 2: Buscar emails con filtros avanzados

```python
from scripts.email_recovery import EmailRecovery, EmailFilter

client = EmailRecovery(provider="outlook")

# Crear filtro
filtro = EmailFilter(
    from_="cliente@empresa.com",
    subject_contains="factura",
    date_after="2024-01-01",
    has_attachment=True
)

# Aplicar búsqueda
emails = client.search_emails(filtro, limit=50)

print(f"Encontrados: {len(emails)} emails")
```

### Ejemplo 3: Obtener email completo con adjuntos

```python
from scripts.email_recovery import EmailRecovery

client = EmailRecovery(provider="gmail")

# Obtener email con cuerpo completo y adjuntos
email_detallado = client.get_email_by_id(
    uid="17",
    include_body=True,
    include_attachments=True,
    attachment_dir="/tmp/adjuntos"
)

print(email_detallado.body_html)
print(f"Adjuntos: {email_detallado.attachments}")
```

---

## 🔧 API Completa

### EmailRecovery (Cliente Principal)

```python
class EmailRecovery:
    def __init__(
        self,
        provider: str,  # 'gmail', 'outlook', 'yahoo', 'custom'
        account_id: str = None,
        config: dict = None,
        cache_enabled: bool = True,
        cache_ttl: int = 300  # segundos
    ):
        """Inicializa el cliente de recuperación de emails."""
    
    def get_recent_emails(
        self,
        limit: int = 10,
        folder: str = "INBOX",
        offset: int = 0
    ) -> list[Email]:
        """Obtiene los emails más recientes."""
    
    def search_emails(
        self,
        filter: EmailFilter,
        limit: int = 100,
        sort_by: str = "date",  # 'date', 'from', 'subject'
        ascending: bool = False
    ) -> list[Email]:
        """Busca emails con filtros avanzados."""
    
    def get_email_by_id(
        self,
        uid: str,
        include_body: bool = False,
        include_attachments: bool = False,
        attachment_dir: str = None
    ) -> Email:
        """Obtiene un email específico por UID."""
    
    def get_folders(self) -> list[Folder]:
        """Lista todas las carpetas/carpetas IMAP."""
    
    def get_folder_stats(self, folder: str) -> FolderStats:
        """Obtiene estadísticas de una carpeta."""
    
    def mark_as_read(self, uid: str) -> bool:
        """Marca un email como leído."""
    
    def mark_as_unread(self, uid: str) -> bool:
        """Marca un email como no leído."""
```

### EmailFilter (Filtros de Búsqueda)

```python
class EmailFilter(BaseModel):
    from_: str = None                    # Remitente
    to: str = None                       # Destinatario
    cc: str = None                       # Con copia
    bcc: str = None                      # Con copia oculta
    subject_contains: str = None         #Texto en asunto
    body_contains: str = None            # Texto en cuerpo
    date_after: datetime = None          # Después de fecha
    date_before: datetime = None         # Antes de fecha
    has_attachment: bool = None          # Tiene adjuntos
    attachment_name: str = None          # Nombre de adjunto
    is_read: bool = None                 # Estado de lectura
    is_flagged: bool = None              # Marcado como importante
    size_min: int = None                 # Tamaño mínimo (bytes)
    size_max: int = None                 # Tamaño máximo (bytes)
    uid_range: str = None               # Rango de UIDs
```

### Email (Modelo de Email)

```python
class Email(BaseModel):
    uid: str                             # UID único IMAP
    message_id: str                      # Message-ID header
    thread_id: str                       # Thread-ID para conversaciones
    from_: str                           # Remitente
    to: list[str]                        # Lista de destinatarios
    cc: list[str]                        # Lista CC
    bcc: list[str]                       # Lista BCC
    subject: str                         # Asunto
    date: datetime                       # Fecha de envío
    snippet: str                         # Vista previa del cuerpo
    body_plain: str = None               # Cuerpo texto plano
    body_html: str = None                # Cuerpo HTML
    attachments: list[Attachment] = []   # Lista de adjuntos
    labels: list[str] = []               # Etiquetas/Gmail labels
    flags: list[str] = []                # Banderas IMAP
    size: int                            # Tamaño en bytes
    is_read: bool                        # Estado lectura
    is_flagged: bool                     # Marcado como importante
    headers: dict                        # Headers completos
```

---

## 🛡️ Manejo de Errores

La skill implementa un sistema de manejo de errores estructurado:

```python
from scripts.error_handler import EmailRecoveryError, RetryableError

try:
    emails = client.get_recent_emails(limit=10)
except EmailRecoveryError as e:
    if e.retryable:
        print(f"Error recuperable: {e}. Reintentando...")
        # El sistema reintentará automáticamente
    else:
        print(f"Error permanente: {e}")
        # Requiere intervención humana (credenciales, etc.)
```

### Códigos de Error

| Código | Significado | Acción |
|--------|-------------|--------|
| `AUTH_FAILED` | Credenciales inválidas | Verificar OAuth2/App Password |
| `RATE_LIMITED` | Límite de API excedido | Esperar y reintentar |
| `CONNECTION_TIMEOUT` | Timeout de conexión | Reintentar con backoff |
| `MAILBOX_LOCKED` | Buzón bloqueado | Esperar o contactar admin |
| `INVALID_UID` | UID no existe | Verificar rango |
| `STORAGE_FULL` | Almacenamiento lleno | Liberar espacio |

---

## ⚡ Optimizaciones

### Cache Inteligente

```python
# Cache de metadatos (TTL: 5 minutos)
emails_metadata = client.get_recent_emails(limit=100)

# Cache de cuerpos (TTL: 1 hora)
email_body = client.get_email_by_id(uid, include_body=True)

# Invalidación manual
client.cache.invalidate(pattern="email:*")
```

### Rate Limiting

- **Gmail**: 10,000 unidades/día (por usuario)
- **Outlook**: 10,000,000 llamadas/mes (por tenant)
- **Yahoo**: 1,000 llamadas/día (por app)

La skill implementa **token bucket** para respetar límites automáticamente.

### Conexiones Persistentes

- Reutilización de conexiones IMAP
- Keep-alive automático
- Reconexión inteligente

---

## 🧪 Testing

```bash
# Ejecutar tests unitarios
pytest tests/

# Tests de integración con credenciales de prueba
pytest tests/integration/ -v

# Coverage report
pytest --cov=scripts tests/
```

### Tests Incluidos

- ✅ Autenticación OAuth2
- ✅ Conexión IMAP
- ✅ Parseo de emails
- ✅ Manejo de errores
- ✅ Cache
- ✅ Rate limiting

---

## 🔍 Monitoreo y Logs

```python
import logging
from scripts.logger import setup_logger

# Configurar logging estructurado
logger = setup_logger(
    name="email_recovery",
    level=logging.INFO,
    json_format=True  # Formato JSON para ELK/Splunk
)

# Los logs incluyen:
# - Timestamp
# - Nivel (INFO, WARNING, ERROR)
# - Operación
# - Duración
# - Proveedor
# - Cuenta
```

### Métricas Exportadas

- `emails_fetched_total`: Total de emails recuperados
- `api_calls_total`: Llamadas a API por proveedor
- `cache_hits_total`: Aciertos de cache
- `errors_total`: Errores por tipo
- `latency_seconds`: Latencia de operaciones

---

## 📚 Ejemplos Avanzados

### Webhook para Notificaciones

```python
from scripts.webhooks import EmailWebhook

webhook = EmailWebhook(
    callback_url="https://tu-api.com/email-webhook",
    secret="tu_secreto_webhook"
)

# Suscribirse a nuevos emails
subscription = webhook.subscribe_to_new_emails(
    provider="gmail",
    folder="INBOX"
)
```

### Recuperación Masiva

```python
# Recuperar todos los emails de un período
emails = client.bulk_recovery(
    date_from="2024-01-01",
    date_to="2024-12-31",
    batch_size=100,        # Tamaño de lote
    concurrency=3,          # Peticiones paralelas
    progress_callback=lambda p: print(f"Progreso: {p}%")
)
```

### Exportación a Formatos

```python
# Exportar a JSON
client.export_emails(
    emails=emails,
    format="json",
    output_file="emails.json"
)

# Exportar a CSV
client.export_emails(
    emails=emails,
    format="csv",
    output_file="emails.csv"
)

# Exportar a PDF
client.export_emails(
    emails=emails,
    format="pdf",
    output_file="emails.pdf"
)
```

---

## 🚀 Despliegue

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY .env.example .env

CMD ["python", "scripts/cli.py"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: email-recovery
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: email-recovery
        image: email-recovery:1.0.0
        env:
        - name: GOOGLE_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: email-secrets
              key: google-client-id
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

## 📖 Referencias

- [RFC 3501 - IMAP4rev1](https://tools.ietf.org/html/rfc3501)
- [RFC 6749 - OAuth 2.0](https://tools.ietf.org/html/rfc6749)
- [Google Gmail API](https://developers.google.com/gmail/api)
- [Microsoft Graph API](https://docs.microsoft.com/graph/api/overview)
- [IMAPClient Documentation](https://imapclient.readthedocs.io/)

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Add nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

## 🆘 Soporte

- 📧 Email: support@kognitoai.com
- 💬 Discord: [KognitoAI Community](https://discord.gg/kognitoai)
- 📚 Docs: [docs.kognitoai.com/email-recovery](https://docs.kognitoai.com/email-recovery)

---

**Versión:** 1.0.0
**Última actualización:** Mayo 2024
**Estado:** ✅ Producción Ready