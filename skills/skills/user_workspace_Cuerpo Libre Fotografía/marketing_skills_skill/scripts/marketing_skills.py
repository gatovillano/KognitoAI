"""
Marketing Skills Suite - Plan de Marketing Generator
Genera planes de marketing completos y accionables para proyectos creativos.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ProjectType(Enum):
    FOTOGRAFIA = "fotografía"
    ARTE = "arte"
    SERVICIOS = "servicios"
    PRODUCTO = "producto"
    DIGITAL = "contenido digital"

class Stage(Enum):
    LANZAMIENTO = "lanzamiento"
    CRECIMIENTO = "crecimiento"
    ESCALA = "escala"
    MADUREZ = "madurez"

@dataclass
class TargetAudience:
    genero: str
    edad: str
    ubicacion: str
    intereses: List[str]
    pain_points: List[str]

@dataclass
class MarketingPlan:
    posicionamiento: Dict[str, str]
    audiencia: TargetAudience
    embudo: Dict[str, List[str]]
    canales: Dict[str, Dict]
    calendario_30dias: Dict[str, List[str]]
    metricas: Dict[str, Dict]
    consideraciones_eticas: List[str]

class MarketingPlanGenerator:
    """Generador de planes de marketing completos para proyectos creativos."""

    def __init__(self):
        self.skills_catalog = self._load_skills_catalog()

    def _load_skills_catalog(self) -> Dict:
        """Carga el catálogo completo de 160+ skills de marketing."""
        return {
            "seo": {
                "keyword-research": "Investigación de palabras clave",
                "content-strategy": "Estrategia de contenido SEO",
                "technical-seo": "SEO técnico (Core Web Vitals, mobile-friendly)",
                "on-page-seo": "Optimización on-page (títulos, meta, schema)",
                "local-seo": "SEO local",
                "entity-seo": "SEO de entidades"
            },
            "contenido": {
                "copywriting": "Escritura persuasiva (PAS, AIDA, BAB)",
                "article-content": "Artículos largos",
                "video-marketing": "Guiones para video y reels",
                "visual-content": "Planificación visual",
                "newsletter": "Email marketing"
            },
            "canales": {
                "email-marketing": "Marketing por correo",
                "influencer-marketing": "Marketing de influencers",
                "referral-program": "Programas de referidos",
                "community-forum": "Comunidades"
            },
            "estrategias": {
                "branding": "Estrategia de marca",
                "content-marketing": "Marketing de contenidos",
                "growth-funnel": "Embudo de crecimiento",
                "conversion-optimization": "Optimización de conversiones",
                "product-launch": "Lanzamiento de productos"
            }
        }

    def generate(
        self,
        project_type: str,
        target_audience: Dict,
        budget: str = "bajo",
        stage: str = "lanzamiento",
        contexto_especifico: Optional[str] = None
    ) -> MarketingPlan:
        """
        Genera un plan de marketing completo.

        Args:
            project_type: Tipo de proyecto (fotografía, arte, servicios, etc.)
            target_audience: Diccionario con datos de la audiencia objetivo
            budget: Presupuesto (bajo, medio, alto)
            stage: Etapa del proyecto (lanzamiento, crecimiento, escala, madurez)
            contexto_especifico: Contexto adicional del proyecto

        Returns:
            MarketingPlan: Plan completo estructurado
        """
        # 1. Generar posicionamiento
        posicionamiento = self._generar_posicionamiento(project_type, target_audience)

        # 2. Definir audiencia
        audiencia = TargetAudience(
            genero=target_audience.get("genero", "mujeres y géneros diversos"),
            edad=target_audience.get("edad", "18-45"),
            ubicacion=target_audience.get("ubicacion", "Chile"),
            intereses=target_audience.get("intereses", ["body positivity", "arte", "fotografía"]),
            pain_points=target_audience.get("pain_points", [
                "No se sienten cómodas en su cuerpo",
                "Quieren un recuerdo que las represente de verdad",
                "Buscan una experiencia transformadora"
            ])
        )

        # 3. Diseñar embudo
        embudo = self._diseñar_embudo(project_type, budget)

        # 4. Seleccionar canales
        canales = self._seleccionar_canales(audiencia, budget, stage)

        # 5. Crear calendario de 30 días
        calendario = self._crear_calendario_30dias(stage)

        # 6. Definir métricas
        metricas = self._definir_metricas(canales)

        # 7. Consideraciones éticas
        etica = self._generar_consideraciones_eticas(project_type)

        return MarketingPlan(
            posicionamiento=posicionamiento,
            audiencia=audiencia,
            embudo=embudo,
            canales=canales,
            calendario_30dias=calendario,
            metricas=metricas,
            consideraciones_eticas=etica
        )

    def _generar_posicionamiento(self, project_type: str, audience: Dict) -> Dict[str, str]:
        """Genera declaración de posicionamiento usando fórmula de Geoffrey Moore."""
        return {
            "formula_moore": f"Para {audience.get('genero', 'personas')} "
                           f"que {audience.get('pain_points', ['buscan reconectar con su cuerpo'])[0]}, "
                           f"nuestro {project_type} es un espacio de creación colaborativa "
                           f"que celebra la diversidad corporal y redefine lo erótico como acto liberador.",
            "propuesta_valor": "No hacemos desnudos, hacemos declaraciones. "
                             "Tu cuerpo no necesita ser perfecto para ser arte.",
            "voz": "Cálida, empática, respetuosa, artística, sin tabúes",
            "tono": "Cercano pero formal, íntimo pero profesional, liberador"
        }

    def _diseñar_embudo(self, project_type: str, budget: str) -> Dict[str, List[str]]:
        """Diseña embudo de conversación y ventas."""
        return {
            "conciencia": [
                "Contenido en redes (reels, carruseles)",
                "SEO para consultas sobre body positivity",
                "Contenido colaborativo con creadores afines"
            ],
            "interes": [
                "Blog posts sobre proceso de sesión",
                "Contenido educativo en redes",
                "Guías descargables"
            ],
            "consideracion": [
                "Testimonios en video",
                "Portfolio curado",
                "Consulta gratuita personalizada"
            ],
            "conversion": [
                "Propuesta personalizada",
                "Contrato claro con consentimiento",
                "Pago seguro"
            ],
            "fidelizacion": [
                "Comunidad privada de participantes",
                "Descuentos para sesiones futuras",
                "Programa de referidos"
            ]
        }

    def _seleccionar_canales(self, audience: TargetAudience, budget: str, stage: str) -> Dict:
        """Selecciona canales según audiencia y presupuesto."""
        canales_base = {
            "principales": {
                "instagram": {
                    "objetivo": "Autoridad y portafolio",
                    "frecuencia": "3-5 posts/semana + stories diarias",
                    "contenido": ["Portfolio", "Testimonios", "Detrás de cámaras", "Educativo"]
                },
                "tiktok": {
                    "objetivo": "Adquisición y viralidad",
                    "frecuencia": "1-2 reels/día",
                    "contenido": ["Testimonios", "Educativo", "Proceso", "Estético"]
                }
            },
            "secundarios": {
                "email": {
                    "objetivo": "Nutrición y conversión",
                    "frecuencia": "1-2 emails/semana",
                    "contenido": ["Bienvenida", "Testimonios", "Proceso", "Ofertas"]
                },
                "blog": {
                    "objetivo": "SEO y autoridad a largo plazo",
                    "frecuencia": "1 artículo/2 semanas",
                    "contenido": ["Guías", "Educativo", "SEO local"]
                }
            }
        }

        if budget in ["medio", "alto"]:
            canales_base["pagados"] = {
                "meta-ads": {
                    "objetivo": "Alcance y conversión",
                    "presupuesto_sugerido": "$50-200/semana"
                },
                "google-ads": {
                    "objetivo": "Captura de demanda",
                    "presupuesto_sugerido": "$30-100/semana"
                }
            }

        return canales_base

    def _crear_calendario_30dias(self, stage: str) -> Dict[str, List[str]]:
        """Crea plan de lanzamiento de 30 días."""
        return {
            "semana_1_fundacion": [
                "Optimizar perfiles de redes (bio, highlights, enlaces)",
                "Publicar primeros 9 posts del feed",
                "Grabar 3 reels iniciales (presentación, proceso, testimonio piloto)",
                "Escribir primer artículo del blog",
                "Crear formulario de consulta gratuita",
                "Configurar email de bienvenida automático"
            ],
            "semana_2_lanzamiento_suave": [
                "Publicar 1 reel/día (educativo/empoderador)",
                "Contactar 5 psicólogos/terapeutas para alianza",
                "Contactar 5 espacios de yoga/meditación locales",
                "Publicar primer testimonio en video",
                "Invitar a amigos/colegas a compartir contenido"
            ],
            "semana_3_amplificacion": [
                "Lanzar programa de referidos",
                "Grabar 2 reels más (detrás de cámaras real)",
                "Publicar 2 artículos más del blog",
                "Hacer colaboración con cuenta de body positivity",
                "Crear guía descargable y capturar emails"
            ],
            "semana_4_optimizacion": [
                "Analizar qué contenido tuvo más engagement",
                "Doblar apuesta en formato ganador",
                "Escribir artículo principal: 'Qué esperar de tu primera sesión'",
                "Configurar seguimiento de consultas",
                "Definir métricas mensuales"
            ]
        }

    def _definir_metricas(self, canales: Dict) -> Dict:
        """Define KPIs por canal."""
        return {
            "redes_sociales": {
                "instagram": {"objetivo_mes1": "+200 seguidores", "engagement_rate": ">3%"},
                "tiktok": {"objetivo_mes1": "+500 seguidores", "tasa_completacion": ">25%"}
            },
            "conversion": {
                "consultas": {"objetivo_mes1": "5-10"},
                "sesiones_cerradas": {"objetivo_mes1": "2-3"},
                "tasa_conversion": {"objetivo": "30% consulta→venta"}
            },
            "web": {
                "visitas_blog": {"objetivo_mes1": "100/mes"},
                "tiempo_promedio": {"objetivo": ">2 minutos"},
                "tasa_rebote": {"objetivo": "<60%"}
            }
        }

    def _generar_consideraciones_eticas(self, project_type: str) -> List[str]:
        """Genera consideraciones éticas específicas para proyectos sensibles."""
        consideraciones_base = [
            "Consentimiento escrito para toda publicación de imágenes",
            "Verificación de mayoría de edad de todas las participantes",
            "Permitir anonimato o uso de seudónimos",
            "No compartir datos de participantes con terceros",
            "Clarificar propiedad de imágenes en contrato"
        ]

        if "desnudo" in project_type.lower() or "erótico" in project_type.lower():
            consideraciones_base.extend([
                "Marcar contenido sensible con advertencias",
                "Respetar límites de cada participante en todo momento",
                "Nunca usar lenguaje cosificador en marketing",
                "Evitar comparaciones con cuerpos 'ideales'"
            ])

        return consideraciones_base

    def generar_contenido_redes(self, plataforma: str, tipo: str, contexto: str) -> Dict:
        """
        Genera contenido específico para redes sociales.

        Args:
            plataforma: 'instagram', 'tiktok', 'twitter', 'linkedin'
            tipo: 'post', 'reel', 'story', 'carousel'
            contexto: Contexto del proyecto y mensaje a transmitir

        Returns:
            Dict con estructura del contenido, copy y hashtags
        """
        templates = {
            "instagram_post": {
                "estructura": "Imagen + copy largo + hashtags",
                "copy_max_length": 2200,
                "hashtags_sugeridos": 15
            },
            "tiktok_reel": {
                "estructura": "Hook visual (0-3s) + cuerpo (3-25s) + CTA (25-30s)",
                "duracion_optima": "15-30 segundos",
                "hook_estrategias": ["Pregunta controversial", "Afirmación fuerte", "Mito a derribar"]
            },
            "twitter_post": {
                "estructura": "Hook + cuerpo + CTA",
                "longitud_optima": "100-250 caracteres",
                "formato": "Thread para contenido largo"
            }
        }

        return {
            "plantilla": templates.get(f"{plataforma}_{tipo}", templates["instagram_post"]),
            "contexto": contexto,
            "sugerencias": [
                "Usar pregunta en el hook para generar engagement",
                "Incluir CTA claro al final",
                "Adaptar tono a la plataforma"
            ]
        }