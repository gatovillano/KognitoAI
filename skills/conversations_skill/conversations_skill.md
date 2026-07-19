---
name: conversations_skill
description: Permite al agente buscar, listar y leer el historial de mensajes de conversaciones pasadas almacenadas en la base de datos de KAI.
---

# CONVERSATIONS_SKILL: Historial de Conversaciones de KAI

Este skill proporciona al agente las herramientas necesarias para acceder y leer el historial de conversaciones pasadas del usuario directamente desde la base de datos.

## Cuándo usar
- El usuario te pide: "Lee la última conversación y continuemos" o "Resume lo que hablamos sobre X tema".
- El usuario te pregunta: "¿De qué hablamos en nuestra última sesión?" o "¿Cuáles fueron los puntos clave de nuestra última charla?".
- Necesitas buscar contexto histórico sobre un tema en chats anteriores.

## Herramientas Disponibles
1. `list_conversations_tool` — Lista las conversaciones recientes (ChatThreads) filtrando por el ID de cuenta de usuario y por términos de búsqueda.
2. `read_conversation_tool` — Lee y formatea el intercambio de mensajes completos para un ID de conversación específico.
