# KogniNotes 📱

La aplicación móvil oficial para visualizar y gestionar tus notas de **Kognito AI** en dispositivos Android.

## ✨ Características

- 🔐 **Acceso Seguro**: Login con tu cuenta de Kognito.
- 📝 **Lista de Notas**: Visualiza todas tus notas con búsqueda y refresco.
- 📖 **Lector Markdown**: Soporte completo para formato Markdown, tablas y código.
- 🎨 **Diseño Premium**: Interfaz moderna basada en la estética de Kognito AI.

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
export const API_URL = 'https://tu-servidor.com/api';
```

### 4. Ejecución

Para lanzar la app y ver el código QR de Expo:

```bash
npm run android
```

Escanea el código QR con la app **Expo Go** en tu móvil y ¡listo! 🎉

---
Desarrollado con ❤️ para el ecosistema Kognito AI.
