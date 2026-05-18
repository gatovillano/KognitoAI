---
name: cuerpo_libre_marketing
description: |
  Suite de marketing especializada para el proyecto 'Cuerpo Libre' de fotografía artística de desnudo.
  Genera planes de marketing completos, estrategias de contenido por canal, SEO, email marketing,
  planes de lanzamiento y consideraciones éticas adaptadas al nicho de diversidad corporal.
  
  Incluye: posicionamiento estratégico, definición de ICP, embudo de conversión,
  contenido para redes sociales (Instagram, TikTok), estrategia SEO, email marketing,
  plan de lanzamiento 30 días, métricas y consideraciones éticas críticas.
---

## Cuándo usar
- Cuando necesites generar un plan de marketing completo para Cuerpo Libre
- Cuando requieras contenido específico para redes sociales
- Cuando necesites estrategia de SEO o email marketing
- Cuando quieras generar un plan de lanzamiento
- Cuando necesites revisar consideraciones éticas y legales

## Acciones disponibles
- `plan_completo`: Plan de marketing completo (todas las secciones)
- `contenido_redes`: Contenido específico para Instagram o TikTok
- `seo`: Estrategia de SEO y artículos para blog
- `email`: Flujos de email marketing y lead magnets
- `lanzamiento`: Plan de lanzamiento 30 días
- `etico`: Consideraciones éticas y legales

## Ejemplo de uso
```python
tool = CuerpoLibreMarketingTool()
plan = tool._run(accion="plan_completo")
contenido_instagram = tool._run(accion="contenido_redes", canal="instagram")
```