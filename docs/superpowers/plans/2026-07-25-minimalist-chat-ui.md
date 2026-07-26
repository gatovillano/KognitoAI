# Rediseño Minimalista de Interfaz de Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar la vista vacía de chat (`EmptyChat.tsx`) y la barra de entrada (`ChatInputBar.tsx`) con una estética ultra minimalista inspirada en la imagen de referencia (estilo Qwen), manteniendo el esquema de colores y la paleta actual.

**Architecture:** Modificación de componentes React de Next.js utilizando Tailwind CSS con variables CSS existentes (`--card`, `--background`, `--border`, `--primary`, `--muted-foreground`).

**Tech Stack:** React, Next.js, Tailwind CSS, Lucide Icons, Framer Motion.

## Global Constraints

- Preservar la paleta de colores existente en `globals.css` (cyan/blue primary, neutral cards).
- Preservar toda la funcionalidad previa de `ChatInputBar` (autocompletado `@`, `#`, `/`, adjuntos, selector de modelo, grabación de audio).

---

### Task 1: Rediseño de EmptyChat.tsx con Header de Modelo y Sugerencias de 2 Líneas

**Files:**
- Modify: `src/components/EmptyChat.tsx`

- [ ] **Step 1: Modificar la estructura de EmptyChat para incluir el Header de Modelo y tarjetas de sugerencias estilo Qwen**

Modificar `src/components/EmptyChat.tsx` para incorporar:
1. Indicador superior central de modelo con icono circular y texto limpio.
2. Contenedor de `ChatInputBar` con clases de elevación suave y redondeado amplio.
3. Sección `⚡ Sugerido` con elementos estructurados en título (negrita) + subtítulo (muted).

---

### Task 2: Rediseño Estético de ChatInputBar.tsx

**Files:**
- Modify: `src/components/ChatInputBar.tsx`

- [ ] **Step 1: Ajustar bordes y distribución interna en ChatInputBar**

Actualizar las clases del contenedor en `ChatInputBar.tsx` a `rounded-[2rem]` o `rounded-[2.25rem]`, mejorando el espaciado interior del textarea y la barra de herramientas flotante inferior.

- [ ] **Step 2: Verificar la integración visual y funcional**

Probar la interfaz y asegurar que no haya errores de renderizado.
