#!/usr/bin/env python3
"""
marketing_ideas_skill - Skill de estrategias de marketing para SaaS.

Skill puramente procedimental que proporciona acceso a una biblioteca
de 139 ideas de marketing probadas, organizadas por categoría, etapa,
presupuesto y timeline.

Esta skill es principalmente instruccional - el agente KAI usa el SKILL.md
para guiar al usuario a través de las ideas de marketing más relevantes
según su contexto, producto, audiencia y recursos disponibles.
"""

from typing import Optional, List, Dict, Any


class MarketingIdeasOrchestrator:
    """
    Orquestador para la skill de marketing-ideas.
    
    Proporciona acceso a las 139 ideas de marketing organizadas por:
    - Categoría (Content & SEO, Paid Ads, Social, etc.)
    - Etapa del producto (Pre-lanzamiento, Early, Growth, Scale)
    - Presupuesto (Free, Low, Medium, High)
    - Timeline (Quick wins, Medium-term, Long-term)
    """
    
    def __init__(self):
        self.name = "marketing_ideas"
        self.description = "Biblioteca de 139 ideas de marketing probadas para SaaS"
        self._categories = self._build_category_index()
    
    def _build_category_index(self) -> Dict[str, List[int]]:
        """Construye índice de categorías con rangos de ideas."""
        return {
            "content_seo": list(range(1, 11)),
            "competitor": list(range(11, 14)),
            "free_tools": list(range(14, 23)),
            "paid_ads": list(range(23, 35)),
            "social_community": list(range(35, 45)),
            "email": list(range(45, 54)),
            "partnerships": list(range(54, 65)),
            "events": list(range(65, 73)),
            "pr_media": list(range(73, 77)),
            "launches": list(range(77, 87)),
            "product_led": list(range(87, 97)),
            "content_formats": list(range(97, 110)),
            "unconventional": list(range(110, 123)),
            "platforms": list(range(123, 131)),
            "international": list(range(131, 133)),
            "developer": list(range(133, 137)),
            "audience_specific": list(range(137, 140)),
        }
    
    def get_categories(self) -> Dict[str, str]:
        """Retorna las categorías disponibles con descripciones."""
        return {
            "content_seo": "Content & SEO (1-10)",
            "competitor": "Competidores & Comparación (11-13)",
            "free_tools": "Herramientas Gratis & Engineering (14-22)",
            "paid_ads": "Publicidad Pagada (23-34)",
            "social_community": "Redes Sociales & Comunidad (35-44)",
            "email": "Email Marketing (45-53)",
            "partnerships": "Partnerships & Programas (54-64)",
            "events": "Eventos & Speaking (65-72)",
            "pr_media": "PR & Medios (73-76)",
            "launches": "Lanzamientos & Promociones (77-86)",
            "product_led": "Crecimiento Product-Led (87-96)",
            "content_formats": "Formatos de Contenido (97-109)",
            "unconventional": "No Convencionales & Creativos (110-122)",
            "platforms": "Plataformas & Marketplaces (123-130)",
            "international": "Internacional & Localización (131-132)",
            "developer": "Desarrolladores & Técnico (133-136)",
            "audience_specific": "Audiencia-Específico (137-139)",
        }
    
    def get_stage_recommendations(self) -> Dict[str, List[str]]:
        """Retorna recomendaciones por etapa del producto."""
        return {
            "pre_launch": [
                "Waitlist referrals (#79)",
                "Early access pricing (#81)",
                "Product Hunt prep (#78)"
            ],
            "early_stage": [
                "Content & SEO (#1-10)",
                "Community building (#35)",
                "Founder-led sales (#47)"
            ],
            "growth": [
                "Paid acquisition (#23-34)",
                "Partnerships (#54-64)",
                "Events (#65-72)"
            ],
            "scale": [
                "Brand campaigns",
                "International expansion (#131-132)",
                "Media acquisitions (#73)"
            ]
        }
    
    def get_budget_recommendations(self) -> Dict[str, List[str]]:
        """Retorna recomendaciones por nivel de presupuesto."""
        return {
            "free": [
                "Content & SEO",
                "Community building",
                "Social media",
                "Comment marketing"
            ],
            "low": [
                "Targeted ads",
                "Sponsorships",
                "Free tools"
            ],
            "medium": [
                "Events",
                "Partnerships",
                "PR"
            ],
            "high": [
                "Acquisitions",
                "Conferences",
                "Brand campaigns"
            ]
    }

# Instancia global para uso del agente
orchestrator = MarketingIdeasOrchestrator()