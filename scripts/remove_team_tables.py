#!/usr/bin/env python3
"""
Script para eliminar tablas de equipos después de la migración

Este script permite eliminar de forma segura las tablas de equipos después de
verificar que la migración se ha realizado correctamente.

ADVERTENCIA: Esta operación es irreversible. Asegúrese de tener respaldos
y de que la migración se haya completado exitosamente.

Uso:
    python scripts/remove_team_tables.py --help
"""

import asyncio
import argparse
import sys
from typing import List
from datetime import datetime
import logging

from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal, Team, TeamMember


class TeamTableRemover:
    """Gestiona la eliminación segura de tablas de equipos."""
    
    def __init__(self):
        self.db: AsyncSession = None
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Configura el logger para el script."""
        logger = logging.getLogger("TeamTableRemover")
        logger.setLevel(logging.INFO)
        
        # Crear handler para consola
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        # Formato del log
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger
    
    async def __aenter__(self):
        """Context manager entry."""
        self.db = SessionLocal()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.db:
            await self.db.close()
    
    async def verify_migration_complete(self) -> bool:
        """Verifica que no hay equipos con recursos asociados."""
        self.logger.info("Verificando estado de migración...")
        
        # Verificar si hay equipos sin migrar
        query = text("""
            WITH team_resources AS (
                SELECT 
                    t.id as team_id,
                    t.name as team_name,
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
                GROUP BY t.id, t.name
                HAVING COUNT(DISTINCT tm.account_id) > 0 
                   OR COUNT(DISTINCT n.id) > 0
                   OR COUNT(DISTINCT ae.id) > 0
                   OR COUNT(DISTINCT lpe.id) > 0
                   OR COUNT(DISTINCT udt.id) > 0
            )
            SELECT COUNT(*) as teams_with_resources FROM team_resources;
        """)
        
        result = await self.db.execute(query)
        teams_with_resources = result.scalar_one()
        
        if teams_with_resources > 0:
            self.logger.error(f"❌ Hay {teams_with_resources} equipos con recursos no migrados")
            return False
        
        # Verificar si hay equipos sin miembros (pueden eliminarse)
        teams_query = select(Team)
        teams_result = await self.db.execute(teams_query)
        teams = teams_result.scalars().all()
        
        teams_without_members = 0
        for team in teams:
            members_query = select(TeamMember).where(TeamMember.team_id == team.id)
            members_result = await self.db.execute(members_query)
            members_count = len(members_result.scalars().all())
            
            if members_count == 0:
                teams_without_members += 1
        
        self.logger.info(f"✅ Verificación completada: {len(teams)} equipos totales, "
                        f"{teams_without_members} sin miembros, 0 con recursos")
        
        return True
    
    async def get_teams_summary(self) -> dict:
        """Obtiene un resumen de los equipos existentes."""
        teams_query = select(Team)
        teams_result = await self.db.execute(teams_query)
        teams = teams_result.scalars().all()
        
        summary = {
            "total_teams": len(teams),
            "teams_info": []
        }
        
        for team in teams:
            # Contar miembros
            members_query = select(TeamMember).where(TeamMember.team_id == team.id)
            members_result = await self.db.execute(members_query)
            members_count = len(members_result.scalars().all())
            
            team_info = {
                "id": str(team.id),
                "name": team.name,
                "admin_id": str(team.admin_id),
                "members_count": members_count,
                "created_at": team.created_at.isoformat()
            }
            summary["teams_info"].append(team_info)
        
        return summary
    
    async def backup_teams_data(self, backup_file: str = None) -> str:
        """Crea un respaldo de los datos de equipos."""
        if not backup_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"team_backup_{timestamp}.sql"
        
        self.logger.info(f"Creando respaldo de equipos en: {backup_file}")
        
        # Obtener datos de equipos y miembros
        teams_summary = await self.get_teams_summary()
        
        backup_content = f"""-- Respaldo de datos de equipos
-- Generado el: {datetime.now().isoformat()}
-- Total de equipos: {teams_summary['total_teams']}

"""
        
        # Agregar datos de equipos
        backup_content += "-- Datos de equipos\n"
        for team_info in teams_summary["teams_info"]:
            backup_content += f"INSERT INTO teams_backup VALUES " \
                           f"('{team_info['id']}', '{team_info['name']}', " \
                           f"'{team_info['admin_id']}', '{team_info['created_at']}');\n"
        
        # Guardar respaldo
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(backup_content)
        
        self.logger.info(f"Respaldo creado exitosamente: {backup_file}")
        return backup_file
    
    async def remove_team_tables(self, confirm_deletion: bool = False):
        """Elimina las tablas de equipos."""
        if not confirm_deletion:
            raise ValueError("Para eliminar las tablas, debe confirmar la operación")
        
        self.logger.warning("INICIANDO ELIMINACIÓN DE TABLAS DE EQUIPOS")
        self.logger.warning("Esta operación es IRREVERSIBLE")
        
        try:
            # Desactivar temporalmente las restricciones de clave foránea
            await self.db.execute(text("SET session_replication_role = 'replica';"))
            
            # Eliminar datos de TeamMember primero (por las FK)
            team_members_query = delete(TeamMember)
            team_members_result = await self.db.execute(team_members_query)
            
            self.logger.info(f"Eliminados {team_members_result.rowcount} registros de team_members")
            
            # Eliminar datos de Team
            teams_query = delete(Team)
            teams_result = await self.db.execute(teams_query)
            
            self.logger.info(f"Eliminados {teams_result.rowcount} registros de teams")
            
            # Confirmar los cambios
            await self.db.commit()
            
            # Reactivar las restricciones de clave foránea
            await self.db.execute(text("SET session_replication_role = 'origin';"))
            
            self.logger.info("✅ Tablas de equipos eliminadas exitosamente")
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"❌ Error al eliminar tablas de equipos: {e}")
            raise
    
    async def list_teams(self):
        """Lista todos los equipos existentes."""
        summary = await self.get_teams_summary()
        
        print(f"\n=== RESUMEN DE EQUIPOS EXISTENTES ===")
        print(f"Total de equipos: {summary['total_teams']}")
        print("-" * 80)
        
        for team in summary["teams_info"]:
            print(f"\nEquipo: {team['name']} (ID: {team['id']})")
            print(f"  Administrador: {team['admin_id']}")
            print(f"  Miembros: {team['members_count']}")
            print(f"  Creado: {team['created_at']}")
    
    async def interactive_removal(self):
        """Realiza la eliminación de tablas de forma interactiva."""
        # Verificar migración
        migration_complete = await self.verify_migration_complete()
        
        if not migration_complete:
            print("\n❌ ADVERTENCIA: La migración no está completa.")
            print("No se pueden eliminar las tablas de equipos.")
            print("Por favor, complete la migración primero.")
            return
        
        # Mostrar resumen
        await self.list_teams()
        
        # Confirmación del usuario
        print(f"\n⚠️  ADVERTENCIA: Esta operación eliminará permanentemente")
        print(f"   todas las tablas relacionadas con equipos.")
        print(f"   Esta acción es IRREVERSIBLE.")
        
        confirmation = input("\n¿Está seguro de que desea continuar? (escriba 'confirmar'): ").strip()
        
        if confirmation.lower() != 'confirmar':
            print("Operación cancelada.")
            return
        
        # Crear respaldo
        backup_file = await self.backup_teams_data()
        print(f"Respaldo creado: {backup_file}")
        
        # Confirmar eliminación
        final_confirmation = input("¿Desea proceder con la eliminación? (s/n): ").strip().lower()
        
        if final_confirmation == 's':
            await self.remove_team_tables(confirm_deletion=True)
            print("✅ Eliminación completada exitosamente")
        else:
            print("Operación cancelada.")


async def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Script para eliminar tablas de equipos después de la migración")
    parser.add_argument("--action", choices=["verify", "list", "remove", "backup"], 
                       default="verify", help="Acción a realizar")
    parser.add_argument("--confirm", action="store_true", 
                       help="Confirmar eliminación (requerido para --action remove)")
    
    args = parser.parse_args()
    
    async with TeamTableRemover() as remover:
        if args.action == "verify":
            migration_complete = await remover.verify_migration_complete()
            if migration_complete:
                print("✅ Migración verificada: No hay equipos con recursos pendientes")
            else:
                print("❌ Migración incompleta: Hay equipos con recursos no migrados")
                sys.exit(1)
                
        elif args.action == "list":
            await remover.list_teams()
            
        elif args.action == "remove":
            if not args.confirm:
                print("Para eliminar las tablas, use la opción --confirm")
                sys.exit(1)
            await remover.interactive_removal()
            
        elif args.action == "backup":
            backup_file = await remover.backup_teams_data()
            print(f"Respaldo guardado en: {backup_file}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)