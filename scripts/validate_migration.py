#!/usr/bin/env python3
"""
Script de validación de migración de equipos a workspaces

Este script permite validar que la migración de equipos a workspaces se haya
realizado correctamente, verificando la integridad de los datos y la consistencia
de las relaciones.

Uso:
    python scripts/validate_migration.py --help
"""

import asyncio
import argparse
import sys
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import (
    SessionLocal, Account, Team, TeamMember, Nota, AgendaEvent,
    Workspace, WorkspacePermission, LangchainPgEmbedding, UserDocumentTopic
)


class MigrationValidator:
    """Valida la integridad de la migración de equipos a workspaces."""
    
    def __init__(self):
        self.db: Optional[AsyncSession] = None
        self.validation_results = []
        
    async def __aenter__(self):
        """Context manager entry."""
        self.db = SessionLocal()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.db:
            await self.db.close()
    
    def log_validation(self, category: str, status: str, message: str, details: Dict = None):
        """Registra un resultado de validación."""
        result = {
            "category": category,
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.validation_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
        print(f"{status_icon} [{category}] {message}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    async def validate_teams_without_resources(self):
        """Valida que no haya equipos con recursos asociados."""
        self.log_validation("TEAMS", "INFO", "Verificando equipos sin recursos...")
        
        # Contar equipos totales
        teams_query = select(func.count()).select_from(Team)
        teams_result = await self.db.execute(teams_query)
        total_teams = teams_result.scalar_one()
        
        # Contar equipos con recursos
        teams_with_resources_query = text("""
            SELECT COUNT(*) as teams_with_resources
            FROM teams t
            WHERE EXISTS (SELECT 1 FROM team_members tm WHERE tm.team_id = t.id)
               OR EXISTS (SELECT 1 FROM notas n WHERE n.team_id = t.id)
               OR EXISTS (SELECT 1 FROM agenda_events ae WHERE ae.team_id = t.id)
               OR EXISTS (SELECT 1 FROM langchain_pg_embedding lpe WHERE lpe.team_id = t.id)
               OR EXISTS (SELECT 1 FROM user_document_topics udt WHERE udt.team_id = t.id)
        """)
        
        teams_with_resources_result = await self.db.execute(teams_with_resources_query)
        teams_with_resources = teams_with_resources_result.scalar_one()
        
        teams_without_resources = total_teams - teams_with_resources
        
        if teams_with_resources == 0:
            self.log_validation("TEAMS", "PASS", 
                              f"No hay equipos con recursos asociados ({total_teams} equipos totales)",
                              {"total_teams": total_teams, "teams_without_resources": teams_without_resources})
        else:
            self.log_validation("TEAMS", "FAIL", 
                              f"Hay {teams_with_resources} equipos con recursos no migrados",
                              {"total_teams": total_teams, "teams_with_resources": teams_with_resources})
    
    async def validate_workspace_integrity(self):
        """Valida la integridad de los workspaces creados."""
        self.log_validation("WORKSPACES", "INFO", "Validando integridad de workspaces...")
        
        # Contar workspaces
        workspaces_query = select(func.count()).select_from(Workspace)
        workspaces_result = await self.db.execute(workspaces_query)
        total_workspaces = workspaces_result.scalar_one()
        
        # Contar permisos de workspaces
        permissions_query = select(func.count()).select_from(WorkspacePermission)
        permissions_result = await self.db.execute(permissions_query)
        total_permissions = permissions_result.scalar_one()
        
        # Verificar workspaces sin permisos
        workspaces_without_perms_query = text("""
            SELECT COUNT(*) 
            FROM workspaces w 
            WHERE NOT EXISTS (
                SELECT 1 FROM workspace_permissions wp 
                WHERE wp.workspace_id = w.id
            )
        """)
        
        workspaces_without_perms_result = await self.db.execute(workspaces_without_perms_query)
        workspaces_without_perms = workspaces_without_perms_result.scalar_one()
        
        if workspaces_without_perms > 0:
            self.log_validation("WORKSPACES", "WARN", 
                              f"Hay {workspaces_without_perms} workspaces sin permisos asignados",
                              {"total_workspaces": total_workspaces, "workspaces_without_perms": workspaces_without_perms})
        else:
            self.log_validation("WORKSPACES", "PASS", 
                              f"Todos los workspaces tienen permisos asignados",
                              {"total_workspaces": total_workspaces, "total_permissions": total_permissions})
    
    async def validate_resource_migration(self):
        """Valida que los recursos se hayan migrado correctamente."""
        self.log_validation("RESOURCES", "INFO", "Validando migración de recursos...")
        
        # Validar notas
        notes_query = text("""
            SELECT 
                COUNT(*) as total_notes,
                COUNT(*) FILTER (WHERE team_id IS NOT NULL) as notes_with_team_id,
                COUNT(*) FILTER (WHERE workspace_id IS NOT NULL) as notes_with_workspace_id
            FROM notas
        """)
        
        notes_result = await self.db.execute(notes_query)
        notes_data = notes_result.mappings().first()
        
        # Validar eventos
        events_query = text("""
            SELECT 
                COUNT(*) as total_events,
                COUNT(*) FILTER (WHERE team_id IS NOT NULL) as events_with_team_id,
                COUNT(*) FILTER (WHERE workspace_id IS NOT NULL) as events_with_workspace_id
            FROM agenda_events
        """)
        
        events_result = await self.db.execute(events_query)
        events_data = events_result.mappings().first()
        
        # Validar documentos
        docs_query = text("""
            SELECT 
                COUNT(*) as total_docs,
                COUNT(*) FILTER (WHERE team_id IS NOT NULL) as docs_with_team_id,
                COUNT(*) FILTER (WHERE workspace_id IS NOT NULL) as docs_with_workspace_id
            FROM langchain_pg_embedding
        """)
        
        docs_result = await self.db.execute(docs_query)
        docs_data = docs_result.mappings().first()
        
        # Validar topics
        topics_query = text("""
            SELECT 
                COUNT(*) as total_topics,
                COUNT(*) FILTER (WHERE team_id IS NOT NULL) as topics_with_team_id,
                COUNT(*) FILTER (WHERE workspace_id IS NOT NULL) as topics_with_workspace_id
            FROM user_document_topics
        """)
        
        topics_result = await self.db.execute(topics_query)
        topics_data = topics_result.mappings().first()
        
        # Reportar resultados
        if notes_data['notes_with_team_id'] > 0:
            self.log_validation("RESOURCES", "FAIL", 
                              f"Hay {notes_data['notes_with_team_id']} notas aún asociadas a equipos",
                              {"total_notes": notes_data['total_notes']})
        else:
            self.log_validation("RESOURCES", "PASS", "Todas las notas están migradas a workspaces")
        
        if events_data['events_with_team_id'] > 0:
            self.log_validation("RESOURCES", "FAIL", 
                              f"Hay {events_data['events_with_team_id']} eventos aún asociados a equipos",
                              {"total_events": events_data['total_events']})
        else:
            self.log_validation("RESOURCES", "PASS", "Todos los eventos están migrados a workspaces")
        
        if docs_data['docs_with_team_id'] > 0:
            self.log_validation("RESOURCES", "FAIL", 
                              f"Hay {docs_data['docs_with_team_id']} documentos aún asociados a equipos",
                              {"total_docs": docs_data['total_docs']})
        else:
            self.log_validation("RESOURCES", "PASS", "Todos los documentos están migrados a workspaces")
        
        if topics_data['topics_with_team_id'] > 0:
            self.log_validation("RESOURCES", "FAIL", 
                              f"Hay {topics_data['topics_with_team_id']} topics aún asociados a equipos",
                              {"total_topics": topics_data['total_topics']})
        else:
            self.log_validation("RESOURCES", "PASS", "Todos los topics están migrados a workspaces")
    
    async def validate_member_permissions(self):
        """Valida que los miembros de equipos tengan permisos en workspaces."""
        self.log_validation("PERMISSIONS", "INFO", "Validando permisos de miembros...")
        
        # Contar miembros de equipos
        members_query = select(func.count()).select_from(TeamMember)
        members_result = await self.db.execute(members_query)
        total_team_members = members_result.scalar_one()
        
        # Contar permisos en workspaces
        workspace_perms_query = select(func.count()).select_from(WorkspacePermission)
        workspace_perms_result = await self.db.execute(workspace_perms_query)
        total_workspace_permissions = workspace_perms_result.scalar_one()
        
        if total_team_members > 0:
            self.log_validation("PERMISSIONS", "WARN", 
                              f"Aún hay {total_team_members} miembros de equipos sin migrar",
                              {"total_team_members": total_team_members, 
                               "total_workspace_permissions": total_workspace_permissions})
        else:
            self.log_validation("PERMISSIONS", "PASS", 
                              "No hay miembros de equipos, todos deberían estar en workspaces",
                              {"total_workspace_permissions": total_workspace_permissions})
    
    async def validate_team_consistency(self):
        """Valida la consistencia de datos de equipos."""
        self.log_validation("CONSISTENCY", "INFO", "Validando consistencia de datos...")
        
        # Verificar equipos huérfanos (sin administrador válido)
        orphaned_teams_query = text("""
            SELECT COUNT(*) 
            FROM teams t 
            WHERE NOT EXISTS (
                SELECT 1 FROM accounts a WHERE a.id = t.admin_id
            )
        """)
        
        orphaned_teams_result = await self.db.execute(orphaned_teams_query)
        orphaned_teams = orphaned_teams_result.scalar_one()
        
        # Verificar miembros huérfanos (sin cuenta válida)
        orphaned_members_query = text("""
            SELECT COUNT(*) 
            FROM team_members tm 
            WHERE NOT EXISTS (
                SELECT 1 FROM accounts a WHERE a.id = tm.account_id
            )
        """)
        
        orphaned_members_result = await self.db.execute(orphaned_members_query)
        orphaned_members = orphaned_members_result.scalar_one()
        
        if orphaned_teams > 0:
            self.log_validation("CONSISTENCY", "WARN", 
                              f"Hay {orphaned_teams} equipos con administradores huérfanos")
        else:
            self.log_validation("CONSISTENCY", "PASS", "No hay equipos huérfanos")
        
        if orphaned_members > 0:
            self.log_validation("CONSISTENCY", "WARN", 
                              f"Hay {orphaned_members} miembros de equipos huérfanos")
        else:
            self.log_validation("CONSISTENCY", "PASS", "No hay miembros de equipos huérfanos")
    
    async def generate_validation_report(self, output_file: str = None) -> Dict:
        """Genera un reporte completo de validación."""
        self.log_validation("VALIDATION", "INFO", "Iniciando validación completa...")
        
        # Ejecutar todas las validaciones
        await self.validate_teams_without_resources()
        await self.validate_workspace_integrity()
        await self.validate_resource_migration()
        await self.validate_member_permissions()
        await self.validate_team_consistency()
        
        # Calcular resumen
        total_checks = len(self.validation_results)
        passed_checks = len([r for r in self.validation_results if r['status'] == 'PASS'])
        warning_checks = len([r for r in self.validation_results if r['status'] == 'WARN'])
        failed_checks = len([r for r in self.validation_results if r['status'] == 'FAIL'])
        
        # Determinar estado general
        if failed_checks > 0:
            overall_status = "CRITICAL"
        elif warning_checks > 0:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"
        
        validation_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "warnings": warning_checks,
                "failed": failed_checks
            },
            "results": self.validation_results
        }
        
        # Mostrar resumen
        print(f"\n" + "=" * 60)
        print("RESUMEN DE VALIDACIÓN")
        print("=" * 60)
        
        status_icon = "✅" if overall_status == "PASS" else "⚠️" if overall_status == "WARNING" else "❌"
        print(f"{status_icon} Estado general: {overall_status}")
        print(f"   Total de verificaciones: {total_checks}")
        print(f"   Exitosas: {passed_checks}")
        print(f"   Advertencias: {warning_checks}")
        print(f"   Fallidas: {failed_checks}")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(validation_report, f, indent=2, ensure_ascii=False)
            print(f"\nReporte guardado en: {output_file}")
        
        return validation_report
    
    async def show_detailed_results(self):
        """Muestra resultados detallados de la validación."""
        print(f"\n" + "=" * 60)
        print("RESULTADOS DETALLADOS")
        print("=" * 60)
        
        for result in self.validation_results:
            status_icon = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
            print(f"\n{status_icon} {result['category']}: {result['message']}")
            if result['details']:
                for key, value in result['details'].items():
                    print(f"    • {key}: {value}")


async def main():
    """Función principal del validador."""
    parser = argparse.ArgumentParser(description="Script de validación de migración de equipos a workspaces")
    parser.add_argument("--output", "-o", help="Archivo de salida para el reporte")
    parser.add_argument("--detailed", action="store_true", help="Mostrar resultados detallados")
    
    args = parser.parse_args()
    
    async with MigrationValidator() as validator:
        report = await validator.generate_validation_report(args.output)
        
        if args.detailed:
            await validator.show_detailed_results()
        
        # Recomendaciones basadas en el resultado
        print(f"\n" + "=" * 60)
        print("RECOMENDACIONES")
        print("=" * 60)
        
        if report['overall_status'] == "CRITICAL":
            print("❌ La migración tiene problemas críticos que deben resolverse.")
            print("   No se recomienda eliminar las tablas de equipos.")
            print("   Revise los errores y complete la migración pendiente.")
        elif report['overall_status'] == "WARNING":
            print("⚠️  La migración tiene algunas advertencias pero es mayormente exitosa.")
            print("   Puede proceder con precaución, pero considere resolver las advertencias.")
        else:
            print("✅ La migración se completó exitosamente.")
            print("   El sistema está listo para la eliminación de tablas de equipos.")
        
        return report['overall_status']


if __name__ == "__main__":
    try:
        status = asyncio.run(main())
        sys.exit(0 if status in ["PASS", "WARNING"] else 1)
    except Exception as e:
        print(f"Error durante la validación: {e}")
        sys.exit(1)