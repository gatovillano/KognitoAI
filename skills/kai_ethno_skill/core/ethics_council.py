"""
Ethics Council - Consejo de Ética
Sistema de veto ético para el pipeline de investigación
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EthicsVerdict(Enum):
    """Veredictos del consejo de ética"""
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    VETO = "veto"


class EthicsConcern:
    """Preocupación ética identificada"""

    def __init__(
        self,
        category: str,
        severity: str,
        description: str,
        recommendation: str,
        auto_resolvable: bool = False,
    ):
        self.category = category
        self.severity = severity  # low, medium, high, critical
        self.description = description
        self.recommendation = recommendation
        self.auto_resolvable = auto_resolvable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
            "auto_resolvable": self.auto_resolvable,
        }


class EthicsCouncil:
    """
    Consejo de ética que revisa las operaciones del pipeline.
    Puede emitir vetos que bloquean completamente el flujo.
    """

    # Patrones de PII sensibles
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
        "dni": r"\b[0-9]{8}[A-Za-z]\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "ip": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    }

    # Categorías de preocupación ética
    CONCERN_CATEGORIES = [
        "pii_exposure",
        "bias_in_sources",
        "lack_of_consent",
        "harmful_content",
        "misrepresentation",
        "plagiarism_risk",
        "data_fabrication",
        "undisclosed_conflict",
    ]

    def __init__(self, strict_mode: bool = False):
        """
        Inicializa el consejo de ética.

        Args:
            strict_mode: Si True, aplica revisión más estricta
        """
        self.strict_mode = strict_mode
        self.review_history: List[Dict[str, Any]] = []
        self.veto_count = 0

    async def review(
        self, data: Dict[str, Any], context: str, metadata: Optional[Dict[str, Any]] = None
    ) -> EthicsVerdict:
        """
        Revisa datos en un contexto específico.

        Args:
            data: Datos a revisar
            context: Contexto de la revisión (bibliographic, ethnographic, etc.)
            metadata: Metadatos adicionales

        Returns:
            EthicsVerdict con la decisión
        """
        logger.info(f"Ethics Council revisando contexto: {context}")

        concerns = []
        data_str = str(data)

        # Revisión 1: Detección de PII
        pii_concerns = self._check_pii(data_str, context)
        concerns.extend(pii_concerns)

        # Revisión 2: Sesgos en fuentes
        if context in ["bibliographic", "synthesis"]:
            bias_concerns = self._check_source_bias(data)
            concerns.extend(bias_concerns)

        # Revisión 3: Contenido potencialmente dañino
        harm_concerns = self._check_harmful_content(data_str)
        concerns.extend(harm_concerns)

        # Revisión 4: Integridad académica
        integrity_concerns = self._check_academic_integrity(data)
        concerns.extend(integrity_concerns)

        # Determinar veredicto
        verdict = self._determine_verdict(concerns)

        # Registrar revisión
        review_record = {
            "timestamp": self._get_timestamp(),
            "context": context,
            "verdict": verdict.value,
            "concerns": [c.to_dict() for c in concerns],
            "strict_mode": self.strict_mode,
        }
        self.review_history.append(review_record)

        if verdict == EthicsVerdict.VETO:
            self.veto_count += 1
            logger.warning(f"VETO emitido en contexto: {context}")
            for concern in concerns:
                if concern.severity in ["high", "critical"]:
                    logger.warning(f"  - {concern.category}: {concern.description}")
        elif verdict == EthicsVerdict.NEEDS_REVIEW:
            logger.info(f"Revisión necesaria en contexto: {context}")
        else:
            logger.info(f"Aprobado en contexto: {context}")

        return verdict

    def _check_pii(self, text: str, context: str) -> List[EthicsConcern]:
        """Detecta PII en el texto"""
        concerns = []

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                severity = "high" if pii_type in ["dni", "ssn", "credit_card"] else "medium"
                concerns.append(
                    EthicsConcern(
                        category="pii_exposure",
                        severity=severity,
                        description=f"Detectados {len(matches)} posibles {pii_type} en {context}",
                        recommendation=f"Anonimizar {pii_type} antes de continuar",
                        auto_resolvable=True,
                    )
                )

        return concerns

    def _check_source_bias(self, data: Dict[str, Any]) -> List[EthicsConcern]:
        """Detecta posibles sesgos en las fuentes"""
        concerns = []

        if isinstance(data, dict) and "sources" in data:
            sources = data["sources"]
            if not isinstance(sources, list):
                return concerns

            # Verificar diversidad de bases de datos
            databases = set()
            for source in sources:
                if isinstance(source, dict):
                    db = source.get("database", "unknown")
                    databases.add(db)

            if len(databases) < 2 and len(sources) > 10:
                concerns.append(
                    EthicsConcern(
                        category="bias_in_sources",
                        severity="medium",
                        description=f"Fuentes concentradas en {len(databases)} base(s) de datos",
                        recommendation="Ampliar búsqueda a múltiples bases de datos",
                        auto_resolvable=False,
                    )
                )

            # Verificar concentración por año
            years = []
            for source in sources:
                if isinstance(source, dict) and "year" in source:
                    try:
                        years.append(int(source["year"]))
                    except (ValueError, TypeError):
                        pass

            if years:
                year_range = max(years) - min(years)
                if year_range < 2 and len(sources) > 20:
                    concerns.append(
                        EthicsConcern(
                            category="bias_in_sources",
                            severity="low",
                            description="Alta concentración temporal de fuentes",
                            recommendation="Incluir fuentes de diferentes períodos",
                            auto_resolvable=False,
                        )
                    )

        return concerns

    def _check_harmful_content(self, text: str) -> List[EthicsConcern]:
        """Detecta contenido potencialmente dañino"""
        concerns = []

        # Palabras clave de contenido sensible (lista simplificada)
        harmful_keywords = [
            "violencia",
            "abuso",
            "maltrato",
            "discriminación",
            "racismo",
            "sexismo",
            "homofobia",
            "suicidio",
            "autolesión",
        ]

        text_lower = text.lower()
        for keyword in harmful_keywords:
            if keyword in text_lower:
                concerns.append(
                    EthicsConcern(
                        category="harmful_content",
                        severity="medium",
                        description=f"Contenido potencialmente sensible detectado: '{keyword}'",
                        recommendation="Revisar contexto y considerar advertencias de contenido",
                        auto_resolvable=False,
                    )
                )
                break  # Solo reportar una vez

        return concerns

    def _check_academic_integrity(self, data: Dict[str, Any]) -> List[EthicsConcern]:
        """Verifica integridad académica"""
        concerns = []

        if isinstance(data, dict):
            # Verificar si hay fuentes sin DOI ni URL
            if "sources" in data and isinstance(data["sources"], list):
                no_identifier = sum(
                    1
                    for s in data["sources"]
                    if isinstance(s, dict)
                    and not s.get("doi")
                    and not s.get("url")
                    and not s.get("isbn")
                )

                if no_identifier > len(data["sources"]) * 0.3:
                    concerns.append(
                        EthicsConcern(
                            category="plagiarism_risk",
                            severity="low",
                            description=f"{no_identifier} fuentes sin identificadores persistentes",
                            recommendation="Verificar accesibilidad y procedencia de fuentes",
                            auto_resolvable=False,
                        )
                    )

        return concerns

    def _determine_verdict(self, concerns: List[EthicsConcern]) -> EthicsVerdict:
        """Determina el veredicto basado en las preocupaciones"""
        if not concerns:
            return EthicsVerdict.APPROVED

        # Contar por severidad
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for concern in concerns:
            severity_counts[concern.severity] = severity_counts.get(concern.severity, 0) + 1

        # Veto por severidad critical o múltiples high
        if severity_counts["critical"] > 0:
            return EthicsVerdict.VETO

        if severity_counts["high"] >= 2:
            return EthicsVerdict.VETO

        if severity_counts["high"] >= 1:
            return EthicsVerdict.NEEDS_REVIEW

        # En modo estricto, más sensible
        if self.strict_mode:
            if severity_counts["medium"] >= 3:
                return EthicsVerdict.NEEDS_REVIEW

        return EthicsVerdict.APPROVED

    def _get_timestamp(self) -> str:
        """Genera timestamp ISO"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_review_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene historial de revisiones"""
        return self.review_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del consejo"""
        total = len(self.review_history)
        if total == 0:
            return {"total_reviews": 0}

        verdicts = {"approved": 0, "needs_review": 0, "veto": 0}
        for record in self.review_history:
            v = record.get("verdict", "approved")
            verdicts[v] = verdicts.get(v, 0) + 1

        return {
            "total_reviews": total,
            "vetoes": self.veto_count,
            "verdicts": verdicts,
            "approval_rate": verdicts["approved"] / total if total > 0 else 0,
        }
