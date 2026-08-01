# api/analytics.py

"""
API endpoints para registrar y consultar analíticas y métricas de uso del sistema.
Permite realizar un seguimiento del tráfico en la web de presentación y el software.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text, desc, case, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AnalyticsEvent, Account
from core.dependencies import get_db_session
from utils.security import get_current_admin_account, decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Schemas ---

class TrackEventRequest(BaseModel):
    session_id: str = Field(..., description="ID único de la sesión del visitante")
    event_type: str = Field("pageview", description="Tipo de evento (e.g. pageview, click, form_submit)")
    path: str = Field(..., description="Ruta de la página visitada (e.g. /presentacion o /chat)")
    referrer: Optional[str] = Field(None, description="URL de origen referidora")
    event_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales del evento")

class AnalyticsSummaryMetric(BaseModel):
    pageviews: int
    visitors: int
    active_users: Optional[int] = None

class AnalyticsSummaryResponse(BaseModel):
    summary: Dict[str, AnalyticsSummaryMetric]
    charts: Dict[str, Any]

# --- Helper to parse browser from User-Agent ---
def parse_browser_and_os(ua_string: Optional[str]) -> tuple:
    if not ua_string:
        return "Desconocido", "Desconocido"
    
    ua_lower = ua_string.lower()
    
    # Simple browser parsing
    if "edg/" in ua_lower or "edge" in ua_lower:
        browser = "Edge"
    elif "opera" in ua_lower or "opr/" in ua_lower:
        browser = "Opera"
    elif "chrome" in ua_lower or "chromium" in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"
    else:
        browser = "Otro"
        
    # Simple OS parsing
    if "windows" in ua_lower:
        os = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower or "macintel" in ua_lower:
        os = "macOS"
    elif "android" in ua_lower:
        os = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os = "iOS"
    elif "linux" in ua_lower:
        os = "Linux"
    else:
        os = "Otro"
        
    return browser, os

# --- Endpoints ---

@router.post("/analytics/track", status_code=status.HTTP_201_CREATED, summary="Registrar un evento de analíticas")
async def track_event(
    request: Request,
    event_data: TrackEventRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Registra un evento de tráfico o interacción desde el frontend.
    Puede ser anónimo o vinculable a un usuario mediante el token de autenticación (si está presente).
    """
    user_id = None
    
    # Intentar detectar si hay usuario autenticado mediante el header de Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = decode_access_token(token)
            if payload:
                user_id_str = payload.get("sub")
                if user_id_str:
                    user_id = uuid.UUID(user_id_str)
        except Exception as e:
            # Si el token es inválido o expira, no fallamos el trackeo, simplemente lo registramos de forma anónima
            logger.debug(f"Error decodificando token en track_event: {e}")

    if user_id:
        try:
            await db.execute(
                update(Account)
                .where(Account.id == user_id)
                .values(last_active_at=datetime.now(timezone.utc))
            )
        except Exception as e:
            logger.debug(f"Error actualizando last_active_at en track_event: {e}")

    # Obtener IP y User-Agent
    ip_address = request.client.host if request.client else "unknown"
    user_agent_str = request.headers.get("user-agent", "unknown")
    
    # Guardar evento en base de datos
    try:
        new_event = AnalyticsEvent(
            session_id=event_data.session_id,
            account_id=user_id,
            event_type=event_data.event_type,
            path=event_data.path,
            referrer=event_data.referrer,
            user_agent=user_agent_str,
            ip_address=ip_address,
            event_metadata=event_data.event_metadata
        )
        db.add(new_event)
        # Session commit se maneja automáticamente por la dependencia get_db_session en su bloque finally, 
        # pero forzamos flush para verificar integridad si es necesario.
        await db.flush()
        return {"status": "success", "event_id": new_event.id}
    except Exception as e:
        logger.error(f"Error al registrar evento de analíticas: {e}", exc_info=True)
        # No queremos tumbar el frontend por un fallo en analíticas, devolvemos un 200/201 simulado
        return {"status": "ignored", "detail": str(e)}


@router.get("/admin/analytics/summary", response_model=AnalyticsSummaryResponse, summary="Obtener resumen de analíticas (solo admin)")
async def get_analytics_summary(
    period: str = Query("7d", description="Período de tiempo (24h, 7d, 30d, all)"),
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Devuelve métricas resumidas y de series de tiempo de analíticas.
    Segmenta entre la web de presentación (/presentacion) y la aplicación/software central.
    Solo para administradores del sistema.
    """
    # Determinar rango de fecha
    now = datetime.now()
    if period == "24h":
        start_date = now - timedelta(hours=24)
        trunc_unit = "hour"
    elif period == "7d":
        start_date = now - timedelta(days=7)
        trunc_unit = "day"
    elif period == "30d":
        start_date = now - timedelta(days=30)
        trunc_unit = "day"
    else:  # all
        start_date = now - timedelta(days=365 * 10)  # 10 años atrás
        trunc_unit = "day"

    # 1. Obtener métricas generales agregadas (Presentation, App y Total)
    try:
        # Consulta para métricas globales
        # Segmentamos por ruta (/presentacion%)
        metrics_stmt = select(
            case(
                (AnalyticsEvent.path.like("/presentacion%"), "presentation"),
                else_="app"
            ).label("segment"),
            func.count(AnalyticsEvent.id).label("pageviews"),
            func.count(func.distinct(AnalyticsEvent.session_id)).label("visitors"),
            func.count(func.distinct(AnalyticsEvent.account_id)).label("active_users")
        ).where(
            AnalyticsEvent.timestamp >= start_date
        ).group_by(
            text("segment")
        )
        
        metrics_result = await db.execute(metrics_stmt)
        rows = metrics_result.all()
        
        # Inicializar mapeo de respuesta
        summary = {
            "presentation": {"pageviews": 0, "visitors": 0, "active_users": 0},
            "app": {"pageviews": 0, "visitors": 0, "active_users": 0},
            "total": {"pageviews": 0, "visitors": 0, "active_users": 0}
        }
        
        for row in rows:
            seg = row.segment
            summary[seg] = {
                "pageviews": row.pageviews,
                "visitors": row.visitors,
                "active_users": row.active_users
            }
            
        # Calcular total
        summary["total"] = {
            "pageviews": summary["presentation"]["pageviews"] + summary["app"]["pageviews"],
            "visitors": summary["presentation"]["visitors"] + summary["app"]["visitors"], # Esto es una suma simple, para visitors únicos reales se requeriría otra query, pero es una aproximación válida
            "active_users": summary["app"]["active_users"] # Los usuarios identificados están solo en la App
        }

        # 2. Línea de tiempo para Gráficos
        # Consulta de visitas a lo largo del tiempo agrupadas por día/hora y segmento
        time_stmt = select(
            func.date_trunc(trunc_unit, AnalyticsEvent.timestamp).label("time_bucket"),
            case(
                (AnalyticsEvent.path.like("/presentacion%"), "presentation"),
                else_="app"
            ).label("segment"),
            func.count(AnalyticsEvent.id).label("pageviews"),
            func.count(func.distinct(AnalyticsEvent.session_id)).label("visitors")
        ).where(
            AnalyticsEvent.timestamp >= start_date
        ).group_by(
            text("time_bucket"), text("segment")
        ).order_by(
            text("time_bucket")
        )
        
        time_result = await db.execute(time_stmt)
        time_rows = time_result.all()
        
        # Consolidar datos de línea de tiempo
        timeline_dict = {}
        for row in time_rows:
            bucket_str = row.time_bucket.strftime("%Y-%m-%d %H:%M" if period == "24h" else "%Y-%m-%d")
            if bucket_str not in timeline_dict:
                timeline_dict[bucket_str] = {
                    "time": bucket_str,
                    "presentation_pageviews": 0,
                    "presentation_visitors": 0,
                    "app_pageviews": 0,
                    "app_visitors": 0
                }
            
            seg = row.segment
            timeline_dict[bucket_str][f"{seg}_pageviews"] = row.pageviews
            timeline_dict[bucket_str][f"{seg}_visitors"] = row.visitors

        timeline_chart = list(timeline_dict.values())

        # 3. Páginas más visitadas (Top 10)
        pages_stmt = select(
            AnalyticsEvent.path,
            func.count(AnalyticsEvent.id).label("views"),
            func.count(func.distinct(AnalyticsEvent.session_id)).label("unique_visitors")
        ).where(
            AnalyticsEvent.timestamp >= start_date,
            AnalyticsEvent.event_type == "pageview"
        ).group_by(
            AnalyticsEvent.path
        ).order_by(
            desc("views")
        ).limit(10)
        
        pages_result = await db.execute(pages_stmt)
        top_pages = [
            {
                "path": r.path, 
                "views": r.views, 
                "unique_visitors": r.unique_visitors,
                "is_presentation": r.path.startswith("/presentacion")
            }
            for r in pages_result.all()
        ]

        # 4. Distribución de Tipos de Eventos
        events_stmt = select(
            AnalyticsEvent.event_type,
            func.count(AnalyticsEvent.id).label("count")
        ).where(
            AnalyticsEvent.timestamp >= start_date
        ).group_by(
            AnalyticsEvent.event_type
        ).order_by(
            desc("count")
        )
        events_result = await db.execute(events_stmt)
        event_types = [{"event": r.event_type, "count": r.count} for r in events_result.all()]

        # 5. Referidores de Tráfico (Top 10)
        referrer_stmt = select(
            AnalyticsEvent.referrer,
            func.count(AnalyticsEvent.id).label("count")
        ).where(
            AnalyticsEvent.timestamp >= start_date,
            AnalyticsEvent.referrer != None,
            AnalyticsEvent.referrer != ""
        ).group_by(
            AnalyticsEvent.referrer
        ).order_by(
            desc("count")
        ).limit(10)
        
        referrer_result = await db.execute(referrer_stmt)
        top_referrers = []
        for r in referrer_result.all():
            ref = r.referrer
            # Limpiar referrer para mostrar solo dominio si es posible
            if ref.startswith("http"):
                try:
                    from urllib.parse import urlparse
                    ref = urlparse(ref).netloc
                except Exception:
                    pass
            top_referrers.append({"referrer": ref or "Directo / Desconocido", "count": r.count})

        # 6. Distribución de Navegadores (User-Agent parsing)
        ua_stmt = select(
            AnalyticsEvent.user_agent,
            func.count(AnalyticsEvent.id).label("count")
        ).where(
            AnalyticsEvent.timestamp >= start_date
        ).group_by(
            AnalyticsEvent.user_agent
        ).order_by(
            desc("count")
        ).limit(100) # Tomamos los top 100 UAs para agrupar en Python
        
        ua_result = await db.execute(ua_stmt)
        browser_counts = {}
        os_counts = {}
        
        for r in ua_result.all():
            browser, os = parse_browser_and_os(r.user_agent)
            browser_counts[browser] = browser_counts.get(browser, 0) + r.count
            os_counts[os] = os_counts.get(os, 0) + r.count

        top_browsers = [{"name": b, "value": c} for b, c in sorted(browser_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        top_os = [{"name": o, "value": c} for o, c in sorted(os_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

        return {
            "summary": summary,
            "charts": {
                "timeline": timeline_chart,
                "top_pages": top_pages,
                "event_types": event_types,
                "top_referrers": top_referrers,
                "browsers": top_browsers,
                "operating_systems": top_os
            }
        }
    except Exception as e:
        logger.error(f"Error generando resumen de analíticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error obteniendo métricas del sistema: {str(e)}"
        )


def map_path_to_feature(path: str) -> str:
    if not path:
        return "Navegación General"
    path_lower = path.lower()
    if path_lower.startswith("/chat") or path_lower.startswith("/c/"):
        return "Asistente de Chat"
    elif path_lower.startswith("/notes") or path_lower.startswith("/notas"):
        return "Gestor de Notas"
    elif path_lower.startswith("/forms") or path_lower.startswith("/formularios"):
        return "Formularios Dinámicos"
    elif path_lower.startswith("/mindmap"):
        return "Mapas Mentales"
    elif path_lower.startswith("/knowledge-graph") or path_lower.startswith("/grafo"):
        return "Grafo de Conocimiento"
    elif path_lower.startswith("/settings") or path_lower.startswith("/perfil"):
        return "Configuración y Perfil"
    elif path_lower.startswith("/presentacion"):
        return "Web de Presentación"
    return "Navegación General"


@router.get("/admin/analytics/users", summary="Obtener analíticas de uso por usuario (solo admin)")
async def get_admin_user_analytics(
    admin_account: Account = Depends(get_current_admin_account),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(Account))
    accounts = result.scalars().all()
    
    now = datetime.now(timezone.utc)
    user_stats = []
    for acc in accounts:
        events_stmt = select(
            AnalyticsEvent.path,
            func.count(AnalyticsEvent.id).label("count")
        ).where(
            AnalyticsEvent.account_id == acc.id
        ).group_by(
            AnalyticsEvent.path
        ).order_by(
            desc("count")
        )
        
        events_res = await db.execute(events_stmt)
        rows = events_res.all()
        
        total_events = sum(r.count for r in rows)
        feature_counts = {}
        for r in rows:
            feat = map_path_to_feature(r.path)
            feature_counts[feat] = feature_counts.get(feat, 0) + r.count
            
        top_features = [
            {
                "name": feat,
                "count": count,
                "percentage": round((count / total_events) * 100) if total_events > 0 else 0
            }
            for feat, count in sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)[:4]
        ]
        
        status_label = "never"
        if acc.last_active_at:
            last_act = acc.last_active_at if acc.last_active_at.tzinfo else acc.last_active_at.replace(tzinfo=timezone.utc)
            delta = (now - last_act).total_seconds()
            if delta < 900:  # 15 min
                status_label = "online"
            elif delta < 86400:  # 24h
                status_label = "active"
            else:
                status_label = "inactive"
                
        user_stats.append({
            "account_id": str(acc.id),
            "name": acc.name or acc.username or "Usuario",
            "email": acc.email,
            "username": acc.username,
            "is_admin": bool(acc.is_admin),
            "last_login_at": acc.last_login_at.isoformat() if acc.last_login_at else None,
            "last_active_at": acc.last_active_at.isoformat() if acc.last_active_at else None,
            "total_events": total_events,
            "status": status_label,
            "top_features": top_features
        })
        
    return {"users": user_stats}

