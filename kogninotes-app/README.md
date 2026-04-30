# KognitoMóvil 📱

Tu exocerebro digital de alta fidelidad. La aplicación móvil oficial de **Kognito AI** para Android.

## ✨ Características

- 🔐 **Acceso Seguro**: Login con cuenta Kognito o vía Telegram.
- 🤖 **Chat con KAI Intelligence**: Asistente AI con respuestas en streaming, bloques de razonamiento y citas de fuentes RAG.
- 📝 **Notas con Markdown**: Crea, edita y busca tus notas con editor WYSIWYG y guardado automático.
- 📅 **Calendario y Tareas**: Gestiona eventos y tareas con vista unificada por fecha.
- 🗂️ **Workspaces**: Organiza notas, chats y eventos por espacios de trabajo.
- 🎨 **Tema Claro/Oscuro**: Interfaz moderna con soporte de tema dinámico.

## 🚀 Cómo empezar

### 1. Requisitos previos

- Tener instalado [Node.js](https://nodejs.org/)
- Tener instalado [Expo Go](https://play.google.com/store/apps/details?id=host.exp.exponent) en tu dispositivo Android.

### 2. Instalación

```bash
cd kogninotes-app
npm install
```

### 3. Configuración de la API

Edita el archivo `src/api/config.ts` y asegúrate de que `API_URL` apunte a tu servidor de Kognito:

```typescript
export const API_URL = 'https://apibase.cuerpolibre.cl/api';
```

### 4. Ejecución

Para lanzar la app y ver el código QR de Expo:

```bash
npm run android
```

Escanea el código QR con la app **Expo Go** en tu móvil y ¡listo! 🎉

---
Desarrollado con ❤️ para el ecosistema Kognito AI.
