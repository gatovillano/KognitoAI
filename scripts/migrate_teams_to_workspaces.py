#!/usr/bin/env python3
"""
Script de migración de Equipos a Workspaces

Este script permite migrar datos de equipos existentes a workspaces antes de eliminar
las tablas de equipos. Proporciona opciones para:
1. Verificar equipos con recursos asociados
2. Migrar recursos a workspaces existentes
3. Crear nuevos workspaces para equipos
4. Generar reportes de migración

Uso:
    python scripts/migrate_teams_to_workspaces.py --help
"""

import asyncio
import argparse
import sys
import uuid
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import json

from sqlalchemy import select, func, text, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Importar desde el proyecto
from core.database import (
    SessionLocal, Account, Team, TeamMember, Nota, AgendaEvent, 
    Workspace, WorkspacePermission, LangchainPgEmbedding, UserDocumentTopic
)
from utils.security import generate_api_token


class TeamMigrationManager:
    """Gestiona la migración de equipos a workspaces."""
    
    def __init__(self):
        self.db: Optional[AsyncSession] = None
        self.migration_log = []
        
    async def __aenter__(self):
        """Context manager entry."""
        self.db = SessionLocal()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.db:
            await self.db.close()
    
    def log_action(self, action: str, details: Dict = None):
        """Registra una acción en el log de migración."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "details": details or {}
        }
        self.migration_log.append(log_entry)
        print(f"[{timestamp}] {action}: {details or {}}")
    
    async def get_teams_with_resources(self) -> List[Dict]:
        """Obtiene equipos que tienen recursos asociados."""
        self.log_action("Buscando equipos con recursos")
        
        # Consulta para obtener equipos con sus recursos
        query = text("""
            WITH team_resources AS (
                SELECT 
                    t.id as team_id,
                    t.name as team_name,
                    t.admin_id,
                    COUNT(DISTINCT tm.account_id) as members_count,
                    COUNT(DISTINCT n.id) as notes_count,
                    COUNT(DISTINCT ae.id) as events_count,
                    COUNT(DISTINCT lpe.id) as documents_count,
                    COUNT(DISTINCT udt.id) as topics_count
                FROM teams t
                LEFT JOIN team_members tm ON t.id = tm.team_id
                LEFT JOIN notas n ON t.id = n.team_id
                LEFT JOIN agenda_events ae ON t.id = ae.team_id
                LEFT JOIN langchain_pg_embedding lpe ON t.id = lpe.team_id
                LEFT JOIN user_document_topics udt ON t.id = udt.team_id
                GROUP BY t.id, t.name, t.admin_id
                HAVING COUNT(DISTINCT tm.account_id) > 0 
                   OR COUNT(DISTINCT n.id) > 0
                   OR COUNT(DISTINCT ae.id) > 0
                   OR COUNT(DISTINCT lpe.id) > 0
                   OR COUNT(DISTINCT udt.id) > 0
            )
            SELECT * FROM team_resources ORDER BY team_name;
        """)
        
        result = await self.db.execute(query)
        teams_data = [dict(row) for row in result.mappings()]
        
        self.log_action(f"Encontrados {len(teams_data)} equipos con recursos")
        return teams_data
    
    async def get_user_workspaces(self, account_id: uuid.UUID) -> List[Dict]:
        """Obtiene workspaces existentes de un usuario."""
        query = select(Workspace).where(Workspace.account_id == account_id)
        result = await self.db.execute(query)
        workspaces = result.scalars().all()
        
        return [{
            "id": str(ws.id),
            "name": ws.name,
            "created_at": ws.created_at.isoformat()
        } for ws in workspaces]
    
    async def create_workspace_for_team(self, team: Dict, admin_account_id: uuid.UUID) -> uuid.UUID:
        """Crea un nuevo workspace para un equipo."""
        workspace_name = f"Equipo: {team['team_name']}"
        
        # Verificar si ya existe un workspace con este nombre
        existing_ws = await self.db.scalar(
            select(Workspace).where(
                Workspace.account_id == admin_account_id,
                Workspace.name == workspace_name
            )
        )
        
        if existing_ws:
            self.log_action(f"Workspace existente encontrado para el equipo {team['team_name']}", 
                          {"workspace_id": str(existing_ws.id)})
            return existing_ws.id
        
        # Crear nuevo workspace
        new_workspace = Workspace(
            account_id=admin_account_id,
            name=workspace_name,
            system_prompt=f"Espacio de trabajo migrado desde el equipo '{team['team_name']}'",
            color="#007bff"
        )
        
        self.db.add(new_workspace)
        await self.db.flush()  # Para obtener el ID
        
        # Crear permiso de owner para el administrador
        permission = WorkspacePermission(
            workspace_id=new_workspace.id,
            account_id=admin_account_id,
            role='owner'
        )
        self.db.add(permission)
        
        self.log_action(f"Workspace creado para el equipo {team['team_name']}", 
                      {"workspace_id": str(new_workspace.id)})
        
        return new_workspace.id
    
    async def migrate_team_members(self, team_id: uuid.UUID, workspace_id: uuid.UUID) -> int:
        """Migra miembros del equipo al workspace."""
        # Obtener miembros del equipo
        query = select(TeamMember).where(TeamMember.team_id == team_id)
        result = await self.db.execute(query)
        members = result.scalars().all()
        
        migrated_count = 0
        for member in members:
            # Crear permiso para el miembro en el workspace
            existing_permission = await self.db.scalar(
                select(WorkspacePermission).where(
                    WorkspacePermission.workspace_id == workspace_id,
                    WorkspacePermission.account_id == member.account_id
                )
            )
            
            if not existing_permission:
                permission = WorkspacePermission(
                    workspace_id=workspace_id,
                    account_id=member.account_id,
                    role='editor'  # Por defecto, todos los miembros son editores
                )
                self.db.add(permission)
                migrated_count += 1
        
        self.log_action(f"Miembros del equipo migrados al workspace", 
                      {"team_id": str(team_id), "workspace_id": str(workspace_id), 
                       "migrated_members": migrated_count})
        
        return migrated_count
    
    async def migrate_team_notes(self, team_id: uuid.UUID, workspace_id: uuid.UUID) -> int:
        """Migra notas del equipo al workspace."""
        query = update(Nota).where(
            Nota.team_id == team_id
        ).values(workspace_id=workspace_id, team_id=None)
        
        result = await self.db.execute(query)
        
        self.log_action(f"Notas del equipo migradas al workspace", 
                      {"team_id": str(team_id), "workspace_id": str(workspace_id),
                       "migrated_notes": result.rowcount})
        
        return result.rowcount
    
    async def migrate_team_events(self, team_id: uuid.UUID, workspace_id: uuid.UUID) -> int:
        """Migra eventos del equipo al workspace."""
        query = update(AgendaEvent).where(
            AgendaEvent.team_id == team_id
        ).values(workspace_id=workspace_id, team_id=None)
        
        result = await self.db.execute(query)
        
        self.log_action(f"Eventos del equipo migrados al workspace", 
                      {"team_id": str(team_id), "workspace_id": str(workspace_id),
                       "migrated_events": result.rowcount})
        
        return result.rowcount
    
    async def migrate_team_documents(self, team_id: uuid.UUID, workspace_id: uuid.UUID) -> int:
        """Migra documentos del equipo al workspace."""
        query = update(LangchainPgEmbedding).where(
            LangchainPgEmbedding.team_id == team_id
        ).values(workspace_id=workspace_id, team_id=None)
        
        result = await self.db.execute(query)
        
        self.log_action(f"Documentos del equipo migrados al workspace", 
                      {"team_id": str(team_id), "workspace_id": str(workspace_id),
                       "migrated_documents": result.rowcount})
        
        return result.rowcount
    
    async def migrate_team_topics(self, team_id: uuid.UUID, workspace_id: uuid.UUID) -> int:
        """Migra topics/colecciones del equipo al workspace."""
        query = update(UserDocumentTopic).where(
            UserDocumentTopic.team_id == team_id
        ).values(workspace_id=workspace_id, team_id=None)
        
        result = await self.db.execute(query)
        
        self.log_action(f"Topics del equipo migrados al workspace", 
                      {"team_id": str(team_id), "workspace_id": str(workspace_id),
                       "migrated_topics": result.rowcount})
        
        return result.rowcount
    
    async def migrate_team_to_workspace(self, team: Dict, workspace_id: uuid.UUID) -> Dict:
        """Realiza la migración completa de un equipo a un workspace."""
        team_id = uuid.UUID(team['team_id'])
        
        self.log_action(f"Iniciando migración del equipo {team['team_name']}")
        
        # Migrar diferentes tipos de recursos
        results = {
            "team_id": str(team_id),
            "team_name": team['team_name'],
            "workspace_id": str(workspace_id),
            "migrations": {}
        }
        
        # Migrar miembros
        results["migrations"]["members"] = await self.migrate_team_members(team_id, workspace_id)
        
        # Migrar notas
        results["migrations"]["notes"] = await self.migrate_team_notes(team_id, workspace_id)
        
        # Migrar eventos
        results["migrations"]["events"] = await self.migrate_team_events(team_id, workspace_id)
        
        # Migrar documentos
        results["migrations"]["documents"] = await self.migrate_team_documents(team_id, workspace_id)
        
        # Migrar topics
        results["migrations"]["topics"] = await self.migrate_team_topics(team_id, workspace_id)
        
        # Commit de todos los cambios
        await self.db.commit()
        
        total_resources = sum(results["migrations"].values())
        self.log_action(f"Equipo {team['team_name']} migrado exitosamente", 
                      {"total_resources": total_resources})
        
        return results
    
    async def list_teams_summary(self):
        """Lista un resumen de todos los equipos con recursos."""
        teams = await self.get_teams_with_resources()
        
        if not teams:
            print("No se encontraron equipos con recursos asociados.")
            return
        
        print(f"\n=== RESUMEN DE EQUIPOS CON RECURSOS ===")
        print(f"Total de equipos: {len(teams)}")
        print("-" * 80)
        
        for team in teams:
            print(f"\nEquipo: {team['team_name']} (ID: {team['team_id']})")
            print(f"  Administrador: {team['admin_id']}")
            print(f"  Miembros: {team['members_count']}")
            print(f"  Notas: {team['notes_count']}")
            print(f"  Eventos: {team['events_count']}")
            print(f"  Documentos: {team['documents_count']}")
            print(f"  Topics: {team['topics_count']}")
    
    async def interactive_migration(self):
        """Realiza una migración interactiva de equipos."""
        teams = await self.get_teams_with_resources()
        
        if not teams:
            print("No se encontraron equipos con recursos asociados.")
            return
        
        print(f"\n=== MIGRACIÓN INTERACTIVA DE EQUIPOS ===")
        
        migration_results = []
        
        for team in teams:
            print(f"\nEquipo: {team['team_name']}")
            print(f"Recursos: {team['members_count']} miembros, {team['notes_count']} notas, "
                  f"{team['events_count']} eventos, {team['documents_count']} documentos")
            
            # Preguntar al usuario qué hacer con este equipo
            while True:
                choice = input("\n¿Qué desea hacer con este equipo?\n"
                             "1. Crear nuevo workspace\n"
                             "2. Migrar a workspace existente\n"
                             "3. Saltar este equipo\n"
                             "Seleccione una opción (1-3): ").strip()
                
                if choice == "1":
                    # Crear nuevo workspace
                    workspace_id = await self.create_workspace_for_team(team, uuid.UUID(team['admin_id']))
                    result = await self.migrate_team_to_workspace(team, workspace_id)
                    migration_results.append(result)
                    break
                    
                elif choice == "2":
                    # Mostrar workspaces existentes
                    workspaces = await self.get_user_workspaces(uuid.UUID(team['admin_id']))
                    
                    if not workspaces:
                        print("El administrador no tiene workspaces existentes. Se creará uno nuevo.")
                        workspace_id = await self.create_workspace_for_team(team, uuid.UUID(team['admin_id']))
                        result = await self.migrate_team_to_workspace(team, workspace_id)
                        migration_results.append(result)
                        break
                    
                    print("\nWorkspaces existentes:")
                    for i, ws in enumerate(workspaces, 1):
                        print(f"{i}. {ws['name']} (ID: {ws['id']})")
                    
                    try:
                        ws_choice = int(input("Seleccione el workspace (número): ")) - 1
                        if 0 <= ws_choice < len(workspaces):
                            workspace_id = uuid.UUID(workspaces[ws_choice]['id'])
                            result = await self.migrate_team_to_workspace(team, workspace_id)
                            migration_results.append(result)
                            break
                        else:
                            print("Selección inválida.")
                    except ValueError:
                        print("Por favor ingrese un número válido.")
                        
                elif choice == "3":
                    print(f"Equipo {team['team_name']} omitido.")
                    break
                    
                else:
                    print("Opción inválida. Por favor seleccione 1, 2 o 3.")
        
        # Mostrar resumen de migración
        print(f"\n=== RESUMEN DE MIGRACIÓN ===")
        for result in migration_results:
            print(f"\nEquipo: {result['team_name']}")
            print(f"Workspace: {result['workspace_id']}")
            print(f"  Miembros migrados: {result['migrations']['members']}")
            print(f"  Notas migradas: {result['migrations']['notes']}")
            print(f"  Eventos migrados: {result['migrations']['events']}")
            print(f"  Documentos migrados: {result['migrations']['documents']}")
            print(f"  Topics migrados: {result['migrations']['topics']}")
    
    async def generate_migration_report(self, output_file: str = None):
        """Genera un reporte detallado de la migración."""
        teams = await self.get_teams_with_resources()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_teams_with_resources": len(teams),
                "total_members": sum(team['members_count'] for team in teams),
                "total_notes": sum(team['notes_count'] for team in teams),
                "total_events": sum(team['events_count'] for team in teams),
                "total_documents": sum(team['documents_count'] for team in teams),
                "total_topics": sum(team['topics_count'] for team in teams),
            },
            "teams": teams,
            "migration_log": self.migration_log
        }
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"Reporte de migración guardado en: {output_file}")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        
        return report


async def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Script de migración de Equipos a Workspaces")
    parser.add_argument("--action", choices=["list", "migrate", "report"], 
                       default="list", help="Acción a realizar")
    parser.add_argument("--output", "-o", help="Archivo de salida para el reporte")
    parser.add_argument("--team-id", help="ID específico de equipo para migrar")
    parser.add_argument("--workspace-id", help="ID de workspace para migrar equipo específico")
    
    args = parser.parse_args()
    
    async with TeamMigrationManager() as manager:
        if args.action == "list":
            await manager.list_teams_summary()
            
        elif args.action == "migrate":
            if args.team_id and args.workspace_id:
                # Migrar equipo específico a workspace específico
                teams = await manager.get_teams_with_resources()
                target_team = next((t for t in teams if t['team_id'] == args.team_id), None)
                
                if target_team:
                    result = await manager.migrate_team_to_workspace(
                        target_team, uuid.UUID(args.workspace_id))
                    print(f"Equipo {target_team['team_name']} migrado exitosamente")
                else:
                    print(f"Equipo con ID {args.team_id} no encontrado")
            else:
                # Migración interactiva
                await manager.interactive_migration()
                
        elif args.action == "report":
            await manager.generate_migration_report(args.output)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMigración cancelada por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"Error durante la migración: {e}")
        sys.exit(1)