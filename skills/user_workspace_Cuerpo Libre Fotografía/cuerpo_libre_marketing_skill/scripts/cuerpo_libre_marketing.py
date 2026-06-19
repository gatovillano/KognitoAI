from langchain_core.tools import BaseTool
from typing import Optional, Dict, List
import json

class CuerpoLibreMarketingTool(BaseTool):
    name: str = "cuerpo_libre_marketing"
    description: str = "Herramienta de marketing especializada para el proyecto 'Cuerpo Libre' de fotografía artística de desnudo. Genera planes de marketing, estrategias de contenido, análisis de audiencia y recomendaciones éticas adaptadas al nicho de diversidad corporal y desnudo artístico."

    def _run(self, accion: str = "plan_completo", canal: Optional[str] = None) -> str:
        """
        Genera contenido de marketing para Cuerpo Libre.
        
        Args:
            accion: Tipo de contenido a generar. Opciones:
                - "plan_completo": Plan de marketing completo
                - "contenido_redes": Estrategia de contenido para redes sociales
                - "seo": Estrategia de SEO y blog
                - "email": Flujos de email marketing
                - "lanzamiento": Plan de lanzamiento
                - "etico": Consideraciones éticas y legales
            canal: Canal específico si es necesario (instagram, tiktok, blog, etc.)
        """
        
        proyecto = {
            "nombre": "Cuerpo Libre",
            "tipo": "Fotografía artística de desnudo",
            "ubicacion": "Chile",
            "precio": "$47.000",
            "incluye": ["300+ fotos", "2 horas de sesión", "30+ fotos editadas", "locación flexible"],
            "filsofia": ["diversidad corporal", "redefinición del deseo", "mirada no objetificada", "lo erótico como acto liberador"]
        }
        
        acciones = {
            "plan_completo": self._generar_plan_completo(proyecto),
            "contenido_redes": self._generar_contenido_redes(proyecto, canal),
            "seo": self._generar_estrategia_seo(proyecto),
            "email": self._generar_email_marketing(proyecto),
            "lanzamiento": self._generar_plan_lanzamiento(proyecto),
            "etico": self._generar_consideraciones_eticas(proyecto)
        }
        
        return acciones.get(accion, acciones["plan_completo"])
    
    def _generar_plan_completo(self, proyecto: Dict) -> str:
        return f"""
# 📸 PLAN DE MARKETING — {proyecto['nombre'].upper()}

## 1 🎯 Posicionamiento Estratégico

### Declaración de Posicionamiento
> **Para** personas que buscan reconectar con su cuerpo a través del arte y la vulnerabilidad, **que** desean ser vistas más allá de los cánones de belleza hegemónicos, **nuestro** proyecto de fotografía artística de desnudos **es un** espacio de creación colaborativa **que** celebra la diversidad corporal y redefine lo erótico como acto liberador. **A diferencia de** la fotografía comercial o pornográfica que cosifica, **nosotros** co-creamos la obra contigo, centrándonos en tu mirada, tu deseo y tu historia, **porque** cada cuerpo merece ser protagonista de su propia narrativa visual.

### Propuesta de Valor Única
> **"{proyecto['nombre']} es el espacio donde tu cuerpo deja de ser objeto para convertirse en obra de arte. A través de una sesión fotográfica colaborativa, no solo obtendrás un portafolio de imágenes poderosas, sino que reconectarás con tu sensualidad, tu vulnerabilidad y tu belleza única —sin juicios, sin cánones, sin límites."**

### Identidad de Marca
| Campo | Definición |
|-------|------------|
| **Voz** | Cálida, empática, respetuosa, artística, sin tabúes |
| **Tono** | Cercano pero formal, íntimo pero profesional, liberador |
| **Evitar** | Lenguaje vulgar, cosificador, comparaciones con cuerpos "ideales" |
| **Preferido** | "cuerpo", "desnudo artístico", "creación conjunta", "sesión", "participante" |

## 2 👥 Audiencia Objetivo (ICP)

### ICP Primario
| Atributo | Descripción |
|----------|-------------|
| **Quién** | Mujeres y personas de géneros diversos, 18–45 años |
| **Ubicación** | Chile, hablantes de español |
| **Perfil** | Interesadas en autoconocimiento, body positivity, arte feminista, desconstrucción de cánones |
| **Dónde están** | Instagram, TikTok, Pinterest, comunidades de body positivity, círculos de arte alternativo |
| **Pain points** | No se sienten cómodas en su cuerpo; quieren un recuerdo que las represente de verdad; buscan experiencia transformadora, no solo fotos |
| **Triggers** | Cumpleaños/hitos personales, procesos de aceptación corporal, recomendación de amigas |

### ICP Secundario
- Parejas que quieren sesión de desnudo artístico conjunto
- Personas mayores de 45 años en procesos de reivindicación corporal
- Comunidades trans y no-binarias en búsqueda de representación visual

## 3 📊 Estrategia de Contenido por Canal

### 🎵 TikTok / Reels (Canal principal)
**Frecuencia**: 6 posts/semana
**Distribución**:
- 40% Educativo/Empoderador: "3 mitos sobre el desnudo artístico"
- 30% Detrás de cámaras: Proceso de edición, locación, música
- 20% Testimonios: Participantes contando su experiencia (con consentimiento)
- 10% Tu historia: Por qué haces esto, tu recorrido

**Hook recomendados**:
- "Lo que nunca te dijeron sobre el desnudo artístico..."
- "Después de 14 años fotografiando, aprendí esto sobre los cuerpos..."
- "Tu cuerpo no necesita ser perfecto para ser arte"

### 📷 Instagram (Autoridad)
- Estética: Tonos cálidos, naturales, poco retoque
- Carruseles: Frases empoderadoras + fragmentos de fotos
- Stories: Encuestas, Q&As, testimonios

### 📝 Blog / SEO (Atracción orgánica)
**Keywords objetivo**:
- Primarias: "desnudo artístico Chile", "fotografía de desnudo artístico Santiago"
- Long-tail: "qué esperar de una sesión de desnudo artístico", "cómo prepararse"

**Artículos pilares**:
1. "Desnudo artístico vs pornografía: diferencias y por qué importan"
2. "Qué esperar de tu primera sesión de desnudo artístico (paso a paso)"
3. "Cómo el desnudo artístico puede ayudarte a sanar tu relación con tu cuerpo"

## 4 🤝 Comunidad y Alianzas

| Tipo | Acción |
|------|--------|
| **Psicólogos/terapeutas** | Alianza para recomendar Cuerpo Libre como herramienta terapéutica |
| **Espacios de yoga/meditación** | Cross-promotion en comunidades afines |
| **Creadoras body positive** | Colaboraciones de contenido |
| **Programa de referidos** | "Trae una amiga: 20% descuento mutuo" |

## 5 📧 Email Marketing

### Flujo automático
| Día | Contenido |
|-----|-----------|
| Día 0 | Bienvenida + "Qué esperar de Cuerpo Libre" |
| Día 2 | Testimonio en video de participante |
| Día 4 | Detrás de cámaras / proceso creativo |
| Día 7 | CTA para agendar consulta gratuita |

### Lead magnets
- Guía: "5 pasos para reconectar con tu cuerpo antes de una sesión"
- Checklist: "¿Estás lista para tu primera sesión de desnudo artístico?"
- Acceso a galería privada de portafolio (solo por email)

## 6 📈 Métricas a Medir

| Métrica | Objetivo (mes 1) |
|---------|------------------|
| Seguidores Instagram | +200 |
| Seguidores TikTok | +500 |
| Visitas blog | 100/mes |
| Consultas recibidas | 5–10 |
| Sesiones cerradas | 2–3 |
| Tasa conversión consulta→venta | 30%

## 7 ⚠️ Consideraciones Éticas (CRÍTICAS)
- **Consentimiento escrito** para toda publicación de imágenes
- **Anonimato** opcional (seudónimos, sin rostro)
- **Verificación de edad** (documento de identidad)
- **Propiedad de imágenes**: Contrato claro sobre derechos de uso
- **Contenido sensible**: Advertencias cuando corresponda

## 8 🚀 Ideas de Alto Impacto
1. **Mini-documental**: Serie de 3–4 capítulos sobre participantes
2. **Evento presencial**: Muestra de fotos + conversatorio sobre cuerpo y deseo
3. **Podcast**: Entrevistas a participantes sobre su experiencia (sin fotos si no quieren)
4. **Precio accesible**: "El arte no es solo para elites"
"""
    
    def _generar_contenido_redes(self, proyecto: Dict, canal: Optional[str]) -> str:
        if canal == "instagram":
            return """
# 📷 CONTENIDO PARA INSTAGRAM

## Estrategia de Feed (9 posts iniciales)

### Post 1: Presentación
**Imagen**: Fragmento de tu mejor foto artística
**Texto**: "Después de 14 años fotografiando historias, empecé a fotografizar verdades. Cada cuerpo tiene una narrativa que merece ser contada. Bienvenidos a Cuerpo Libre. #DesnudoArte #BodyPositivityChile"

### Post 2: Filosofía
**Imagen**: Carrusel con 3 fotos mostrando diversidad corporal
**Texto**: "No hacemos desnudos. Hacemos declaraciones. Cada sesión es una conversación entre tú y tu cuerpo, mediada por mi lente y tu historia. ↓"

### Post 3: Proceso
**Imagen**: Detrás de cámaras (tu mano ajustando la cámara, locación)
**Texto**: "Lo que no ven: 2 horas de charla antes de la primera foto. Necesito conocer tu historia para poder capturarla."

### Post 4: Testimonio corto
**Imagen**: Fragmento de foto (sin rostro si es necesario)
**Texto**: "María, 34 años, nunca se había atrevido a hacer una sesión así. Me dijo: 'Nunca me vi tan hermosa'. Tu cuerpo también tiene esa belleza esperando."

### Post 5: Educación
**Imagen**: Infografía simple
**Texto**: "Desnudo artístico ≠ pornografía. Las diferencias: 1) Consentimiento constante, 2) Mirada no objetificadora, 3) Tu historia al centro, 4) Sin explotación."

### Post 6: Oferta
**Imagen**: Collage de 4 fotos variadas
**Texto**: "Sesiones de desnudo artístico en Santiago. $47.000 incluye 300+ fotos, edición profesional y 2 horas de creación conjunta. Link en bio para consulta gratuita."

### Post 7: Diversidad
**Imagen**: Serie de 3 cuerpos diferentes (distintas edades, tallas, tonos de piel)
**Texto**: "No hay cuerpos 'perfectos'. Hay cuerpos con historia. Y todos son dignos de ser arte."

### Post 8: Detrás de cámaras
**Imagen**: Música/playlist que usas en sesiones, o tus equipos
**Texto**: "La playlist es sagrada. Cada canción está elegida para que te sientas cómoda, poderosa, tú."

### Post 9: Llamado a la acción
**Imagen**: Tu foto, sonriendo, en tu espacio de trabajo
**Texto**: "Si llevas tiempo queriendo hacer esto pero no te atreves...Escríbeme. La primera consulta es gratuita. No te arrepentirás."

## Estrategia de Stories
- Encuestas: "¿Te atreverías a hacer una sesión de desnudo artístico?"
- Q&As: Pregúntame lo que quieras sobre el proceso
- Testimonios: Videos cortos de participantes
- Detrás de cámaras: Momentos reales de las sesiones
"""
        elif canal == "tiktok":
            return """
# 🎵 CONTENIDO PARA TIKTOK / REELS

## Guión 1: Presentación (15 segundos)
**Hook (0-3s)**: "Después de 14 años de fotografía periodística, empecé a fotografiar algo más importante: verdades."
**Cuerpo (3-10s)**: "En Cuerpo Libre no hacemos desnudos. Hacemos declaraciones. Cada cuerpo tiene una historia que merece ser contada."
**CTA (10-15s)**: "Si quieres vivir esta experiencia, link en bio."

## Guión 2: Mito vs Realidad (20 segundos)
**Hook**: "3 mitos sobre el desnudo artístico que debes dejar de creer"
**Mito 1**: "Que es solo para cuerpos perfectos" → Realidad: "Es para cuerpos con historia"
**Mito 2**: "Que es explotador" → Realidad: "Es colaborativo, tú tienes el control total"
**Mito 3**: "Que es pornografía" → Realidad: "La diferencia es el respeto, la mirada, la narrativa"
**CTA**: "¿Qué otro mito has escuchado? Comenta"

## Guión 3: Detrás de cámaras (15 segundos)
**Hook**: "Esto es lo que pasa antes de la primera foto"
**Cuerpo**: "Charlamos 2 horas. Conozco tu historia, tus miedos, tus deseos. Solo entonces empiezo a disparar."
**CTA**: "¿Te gustaría vivir esta experiencia?"

## Guión 4: Testimonio (30 segundos)
**Hook**: "Lo que dijo María después de su sesión"
**Cuerpo**: [Video testimonial de participante]
"Nunca me vi tan hermosa. No es que las fotos me hayan cambiado el cuerpo, es que me ayudaron a ver lo que siempre estuvo ahí."
**CTA**: "¿Te atreves? Link en bio"

## Guión 5: Educación (60 segundos)
**Hook**: "La diferencia entre desnudo artístico y pornografía"
**Cuerpo**: No es la desnudez. Es la intención. En el arte, el cuerpo es el sujeto, no el objeto. Es tu historia, no mi deseo. Es colaboración, no consumo.
**CTA**: "Guarda este video para aclararle a tus amigas"
"""
        return "Canal no reconocido. Usa 'instagram' o 'tiktok'."
    
    def _generar_estrategia_seo(self, proyecto: Dict) -> str:
        return f"""
# 📝 ESTRATEGIA SEO PARA {proyecto['nombre'].upper()}

## Keywords Objetivo

### Primarias (alta intención, baja competencia)
- "desnudo artístico Chile" (volumen: 50–100/mes)
- "fotografía de desnudo artístico Santiago" (volumen: 20–50/mes)
- "fotógrafo de desnudo artístico Chile" (volumen: 30–60/mes)

### Secundarias (intención media)
- "sesión de fotos desnudo artístico"
- "body positivity Chile"
- "aceptación corporal fotografía"
- "desnudo artístico femenino Chile"

### Long-tail (conversión alta)
- "qué esperar de una sesión de desnudo artístico"
- "cómo prepararse para una sesión de fotos desnudo"
- "desnudo artístico para principiantes Chile"
- "fotógrafo de desnudo respetuoso Santiago"

## Estructura de URLs Sugerida
- `/` - Home
- `/sesiones` - Página de servicios
- `/portafolio` - Galería de trabajos
- `/proceso` - Qué esperar paso a paso
- `/blog` - Artículos
- `/contacto` - Formulario de consulta

## Artículos Pilares (Prioridad Alta)

1. **"Desnudo artístico vs pornografía: diferencias y por qué importan"**
   - Palabra clave principal: "desnudo artístico vs pornografía"
   - Palabras secundarias: "desnudo artístico Chile", "fotografía de desnudo"
   - Estructura: Comparación clara, posición ética, FAQ

2. **"Qué esperar de tu primera sesión de desnudo artístico (paso a paso)"**
   - Palabra clave principal: "qué esperar de una sesión de desnudo artístico"
   - Palabras secundarias: "primera sesión de desnudo", "cómo prepararse"
   - Estructura: Antes/durante/después, checklist, FAQ

3. **"Cómo el desnudo artístico puede ayudarte a sanar tu relación con tu cuerpo"**
   - Palabra clave principal: "aceptación corporal fotografía"
   - Palabras secundarias: "body positivity Chile", "desnudo artístico terapéutico"
   - Estructura: Testimonios, beneficios psicológicos, casos

4. **"Guía definitiva de body positivity en Chile"**
   - Palabra clave principal: "body positivity Chile"
   - Palabras secundarias: "aceptación corporal Chile", "desnudo artístico body positive"
   - Estructura: Historia, recursos, comunidades, cómo participar

## SEO Técnico
- Título principal: "Cuerpo Libre — Fotografía Artística de Desnudo | Santiago, Chile"
- Meta descripción: "Sesiones de desnudo artístico íntimo y colaborativo en Santiago. Reconecta con tu cuerpo a través de la fotografía. +300 fotos por sesión. $47.000"
- Schema markup: ProfessionalService o PhotographyBusiness
- Velocidad de carga: Optimizar imágenes (WebP, lazy loading)
- Mobile-first: Diseño responsivo obligatorio
"""
    
    def _generar_email_marketing(self, proyecto: Dict) -> str:
        return f"""
# 📧 EMAIL MARKETING — {proyecto['nombre'].upper()}

## Flujo Automático para Nuevos Contactos

### Email 1: Bienvenida (Inmediato)
**Asunto**: Bienvenida a Cuerpo Libre — Tu cuerpo merece ser arte

**Hola [Nombre],**

Gracias por interesarte en Cuerpo Libre. Entiendo que dar el paso de una sesión de desnudo artístico puede generar nervios, dudas o incluso miedo. Estoy aquí para acompañarte en cada paso.

**Qué puedes esperar:**
- ✅ 2 horas de creación conjunta, a tu ritmo
- ✅ 300+ fotografías para que elijas
- ✅ 30+ fotos editadas profesionalmente
- ✅ Tu historia al centro, no mi lente
- ✅ Total respeto, sin juicios, sin límites

**Próximos pasos:**
1. Agenda una consulta gratuita de 15 minutos (link)
2. Conversamos sobre tus expectativas, miedos y deseos
3. Diseñamos la sesión que tú necesitas

**Si tienes preguntas, responde este email.**

Con respeto y arte,
Gato
Fotógrafo — Cuerpo Libre

---

### Email 2: Social Proof (Día 2)
**Asunto**: Lo que dijo una participante después de su sesión

**Hola [Nombre],**

Te escribo para compartirte algo que me movió la semana pasada.

María, 34 años, nunca se había atrevido a hacer una sesión de desnudo. Me dijo al final:

"Nunca me vi tan hermosa. No es que las fotos me hayan cambiado el cuerpo, es que me ayudaron a ver lo que siempre estuvo ahí."

Eso es lo que quiero que vivas tú también.

**Tu cuerpo no necesita ser perfecto para ser arte.**

Si quieres conversar sobre cómo sería tu sesión, aquí tienes el link para la consulta gratuita.

Hasta pronto,
Gato

---

### Email 3: Proceso (Día 4)
**Asunto**: Así es una sesión de Cuerpo Libre (por dentro)

**Hola [Nombre],**

Te gustaría ver qué pasa realmente en una sesión?

No es solo disparar fotos. Es:
1. **Charlamos 2 horas primero**: Necesito conocer tu historia, tus miedos, qué significa tu cuerpo para ti
2. **Tú tienes el control total**: Tú decides qué mostrar, cómo, cuándo. Yo solo soy el medium
3. **Música y ambiente**: Creamos un espacio donde te sientas cómoda, poderosa, tú
4. **Las fotos son tuyas**: Tú eliges cuáles se publican, cuáles no. Siempre.

**Este soy yo detrás de la cámara:** [link a reel/detrás de cámaras]

Si quieres vivir esta experiencia, aquí tienes el link para la consulta.

Hasta pronto,
Gato

---

### Email 4: Conversión (Día 7)
**Asunto**: ¿Lista para tu primera sesión? 💫

**Hola [Nombre],**

Te he escrito durante la semana para que conozcas más sobre Cuerpo Libre. Ahora quiero preguntarte:

¿Estás lista para dar el paso?

**Lo que incluye tu sesión:**
- 📸 300+ fotografías para que elijas
- ⏰ 2 horas de creación conjunta
- 🎨 30+ fotos editadas profesionalmente
- 🏠 Locación flexible (tu casa o la mía)
- 💰 Todo por $47.000

**Primeros 3 interesados este mes:** 20% descuento ($37.600)

**Agenda tu consulta gratuita aquí:** [link]

No te arrepentirás.

Con respeto,
Gato

---

## Lead Magnets para Capturar Emails

1. **"Guía: 5 pasos para reconectar con tu cuerpo antes de una sesión"**
2. **"Checklist: ¿Estás lista para tu primera sesión de desnudo artístico?"**
3. **Acceso a galería privada de portafolio** (solo por email)
"""
    
    def _generar_plan_lanzamiento(self, proyecto: Dict) -> str:
        return f"""
# 🚀 PLAN DE LANZAMIENTO — {proyecto['nombre'].upper()}

## Semana 1: Fundación
- [ ] Optimizar cuentas de Instagram y TikTok
- [ ] Publicar primeros 9 posts del feed
- [ ] Grabar 3 reels: presentación, detrás de cámaras, testimonio piloto
- [ ] Escribir 1 artículo del blog
- [ ] Crear formulario de consulta gratuita
- [ ] Configurar email automático de bienvenida

## Semana 2: Lanzamiento Suave
- [ ] Publicar 1 reel por día (educativo/empoderador)
- [ ] Contactar 10 psicólogos/terapeutas para alianza
- [ ] Contactar 5 espacios de yoga/meditación locales
- [ ] Publicar primer testimonio en video
- [ ] Invitar a red personal a compartir contenido

## Semana 3: Amplificación
- [ ] Lanzar programa de referidos (20% descuento mutuo)
- [ ] Grabar 2 reels más de sesión real
- [ ] Publicar 2 artículos más del blog
- [ ] Hacer colaboración con cuenta de body positivity
- [ ] Activar captura de emails con lead magnet

## Semana 4: Optimización
- [ ] Analizar métricas y doblar apuesta en formato ganador
- [ ] Escribir artículo "Qué esperar de tu primera sesión"
- [ ] Configurar seguimiento de consultas (hoja de cálculo o CRM)
- [ ] Definir métricas mensuales

## Métricas Objetivo (Mes 1)
- Seguidores Instagram: +200
- Seguidores TikTok: +500
- Visitas blog: 100/mes
- Consultas: 5–10
- Sesiones cerradas: 2–3
- Tasa conversión: 30%
"""
    
    def _generar_consideraciones_eticas(self, proyecto: Dict) -> str:
        return f"""
# ⚠️ CONSIDERACIONES ÉTICAS Y LEGALES — {proyecto['nombre'].upper()}

## Aspectos Críticos

| Aspecto | Acción Requerida |
|---------|------------------|
| **Consentimiento** | Autorización escrita expresa para publicar cualquier imagen |
| **Anonimato** | Permitir seudónimos o sin rostro bajo solicitud |
| **Verificación de edad** | Documento de identidad en primera sesión (mayoría de edad) |
| **Propiedad de imágenes** | Contrato claro: quién es dueña, cómo se pueden usar |
| **Privacidad de datos** | No compartir información de participantes con terceros |
| **Contenido sensible** | Marcar cuentas y contenido con advertencias cuando corresponda |

## Contrato Recomendado (Puntos Clave)

1. **Propiedad**: La participante es dueña de sus imágenes
2. **Uso**: Solo se publica con autorización escrita expresa
3. **Retiro**: Puede solicitar retiro de imágenes en cualquier momento
4. **Anonimato**: Derecho a usar seudónimo o no mostrar rostro
5. **Edad**: Declaración de mayoría de edad
6. **Pago**: Política de cancelación y reembolso

## Líneas Éticas No Negociables
- Nunca comparar cuerpos entre participantes
- Nunca usar lenguaje cosificador o vulgar
- Nunca presionar para mostrar más de lo cómodo
- Nunca publicar sin consentimiento explícito
- Nunca compartir datos de participantes
"""
