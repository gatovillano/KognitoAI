#!/usr/bin/env python3
"""
Asistente de Migración de Equipos a Workspaces

Script interactivo que guía al usuario a través del proceso completo de migración
de equipos a workspaces, desde la verificación inicial hasta la eliminación final
de las tablas de equipos.

Uso:
    python scripts/team_migration_helper.py
"""

import asyncio
import sys
from typing import Dict, List
from datetime import datetime

from migrate_teams_to_workspaces import TeamMigrationManager
from remove_team_tables import TeamTableRemover


class TeamMigrationHelper:
    """Asistente interactivo para la migración de equipos."""
    
    def __init__(self):
        self.migration_manager = TeamMigrationManager()
        self.removal_manager = TeamTableRemover()
    
    async def show_welcome(self):
        """Muestra el mensaje de bienvenida y explicación."""
        print("=" * 80)
        print("           ASISTENTE DE MIGRACIÓN DE EQUIPOS A WORKSPACES")
        print("=" * 80)
        print()
        print("Este asistente le guiará a través del proceso de migración de")
        print("equipos existentes a workspaces, preparando el sistema para la")
        print("eliminación de las tablas de equipos.")
        print()
        print("El proceso consta de 3 fases:")
        print("1. Verificación: Analizar equipos existentes y sus recursos")
        print("2. Migración: Transferir recursos de equipos a workspaces")
        print("3. Limpieza: Eliminar tablas de equipos (opcional)")
        print()
        print("ADVERTENCIA: La fase de limpieza es irreversible.")
        print("Asegúrese de tener respaldos completos antes de proceder.")
        print()
    
    async def phase_1_verification(self):
        """Fase 1: Verificación de equipos existentes."""
        print("\n" + "=" * 60)
        print("FASE 1: VERIFICACIÓN DE EQUIPOS EXISTENTES")
        print("=" * 60)
        
        async with TeamMigrationManager() as manager:
            await manager.list_teams_summary()
        
        print("\n¿Desea proceder con la migración de estos equipos?")
        response = input("(s/n): ").strip().lower()
        return response == 's'
    
    async def phase_2_migration(self):
        """Fase 2: Migración de equipos a workspaces."""
        print("\n" + "=" * 60)
        print("FASE 2: MIGRACIÓN DE EQUIPOS A WORKSPACES")
        print("=" * 60)
        
        async with TeamMigrationManager() as manager:
            print("\nOpciones de migración:")
            print("1. Migración interactiva (recomendado para primeras migraciones)")
            print("2. Migrar equipo específico a workspace existente")
            print("3. Crear workspace para cada equipo automáticamente")
            
            choice = input("\nSeleccione una opción (1-3): ").strip()
            
            if choice == "1":
                await manager.interactive_migration()
            elif choice == "2":
                await self.migrate_specific_team(manager)
            elif choice == "3":
                await self.auto_create_workspaces(manager)
            else:
                print("Opción inválida. Volviendo al menú principal.")
                return False
        
        return True
    
    async def migrate_specific_team(self, manager: TeamMigrationManager):
        """Migra un equipo específico a un workspace existente."""
        print("\n--- Migración de equipo específico ---")
        
        # Listar equipos
        teams = await manager.get_teams_with_resources()
        if not teams:
            print("No hay equipos con recursos para migrar.")
            return
        
        print("\nEquipos disponibles:")
        for i, team in enumerate(teams, 1):
            print(f"{i}. {team['team_name']} ({team['members_count']} miembros)")
        
        try:
            team_choice = int(input("Seleccione el equipo (número): ")) - 1
            if 0 <= team_choice < len(teams):
                selected_team = teams[team_choice]
                
                # Obtener workspaces del administrador
                admin_id = selected_team['admin_id']
                workspaces = await manager.get_user_workspaces(admin_id)
                
                if not workspaces:
                    print("El administrador no tiene workspaces. Se creará uno nuevo.")
                    workspace_id = await manager.create_workspace_for_team(selected_team, admin_id)
                else:
                    print("\nWorkspaces existentes del administrador:")
                    for i, ws in enumerate(workspaces, 1):
                        print(f"{i}. {ws['name']}")
                    
                    ws_choice = int(input("Seleccione el workspace (número): ")) - 1
                    if 0 <= ws_choice < len(workspaces):
                        workspace_id = workspaces[ws_choice]['id']
                    else:
                        print("Selección inválida.")
                        return
                
                # Realizar migración
                result = await manager.migrate_team_to_workspace(selected_team, workspace_id)
                print(f"Equipo {selected_team['team_name']} migrado exitosamente")
            else:
                print("Selección inválida.")
        except ValueError:
            print("Por favor ingrese un número válido.")
    
    async def auto_create_workspaces(self, manager: TeamMigrationManager):
        """Crea un workspace para cada equipo automáticamente."""
        print("\n--- Creación automática de workspaces ---")
        
        teams = await manager.get_teams_with_resources()
        if not teams:
            print("No hay equipos con recursos para migrar.")
            return
        
        print(f"Se crearán workspaces para {len(teams)} equipos.")
        
        confirm = input("¿Desea proceder? (s/n): ").strip().lower()
        if confirm != 's':
            print("Operación cancelada.")
            return
        
        migration_results = []
        for team in teams:
            print(f"\nProcesando equipo: {team['team_name']}")
            
            # Crear workspace
            workspace_id = await manager.create_workspace_for_team(team, team['admin_id'])
            
            # Migrar recursos
            result = await manager.migrate_team_to_workspace(team, workspace_id)
            migration_results.append(result)
        
        # Mostrar resumen
        print(f"\n=== RESUMEN DE MIGRACIÓN AUTOMÁTICA ===")
        for result in migration_results:
            print(f"Equipo: {result['team_name']} -> Workspace: {result['workspace_id']}")
    
    async def phase_3_cleanup(self):
        """Fase 3: Eliminación de tablas de equipos."""
        print("\n" + "=" * 60)
        print("FASE 3: ELIMINACIÓN DE TABLAS DE EQUIPOS")
        print("=" * 60)
        
        print("ADVERTENCIA: Esta fase es IRREVERSIBLE.")
        print("Solo proceda si está completamente seguro de que la migración")
        print("se completó exitosamente y tiene respaldos de sus datos.")
        print()
        
        # Verificar migración
        async with TeamTableRemover() as remover:
            migration_complete = await remover.verify_migration_complete()
            
            if not migration_complete:
                print("❌ La verificación indica que hay equipos con recursos no migrados.")
                print("No se pueden eliminar las tablas en este momento.")
                return False
            
            # Mostrar resumen
            await remover.list_teams()
            
            # Confirmación
            print("\n¿Desea proceder con la eliminación de las tablas de equipos?")
            confirm = input("(escriba 'eliminar'): ").strip()
            
            if confirm == 'eliminar':
                await remover.interactive_removal()
                return True
            else:
                print("Operación cancelada.")
                return False
    
    async def generate_final_report(self):
        """Genera un reporte final de la migración."""
        print("\n" + "=" * 60)
        print("GENERANDO REPORTE FINAL")
        print("=" * 60)
        
        # Generar reporte de migración
        async with TeamMigrationManager() as manager:
            report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report = await manager.generate_migration_report(report_file)
            
        print(f"\nReporte de migración guardado en: {report_file}")
        
        # Resumen rápido
        summary = report.get('summary', {})
        print(f"\nResumen de migración:")
        print(f"- Equipos procesados: {summary.get('total_teams_with_resources', 0)}")
        print(f"- Miembros migrados: {summary.get('total_members', 0)}")
        print(f"- Notas migradas: {summary.get('total_notes', 0)}")
        print(f"- Eventos migrados: {summary.get('total_events', 0)}")
        print(f"- Documentos migrados: {summary.get('total_documents', 0)}")
        print(f"- Topics migrados: {summary.get('total_topics', 0)}")
    
    async def show_final_summary(self, phases_completed: List[str]):
        """Muestra un resumen final de las fases completadas."""
        print("\n" + "=" * 80)
        print("RESUMEN FINAL DE LA MIGRACIÓN")
        print("=" * 80)
        
        print("Fases completadas:")
        for i, phase in enumerate(phases_completed, 1):
            print(f"{i}. ✅ {phase}")
        
        print(f"\nTotal de fases completadas: {len(phases_completed)}")
        
        if "Eliminación de tablas" in phases_completed:
            print("\n🎉 MIGRACIÓN COMPLETA")
            print("Las tablas de equipos han sido eliminadas exitosamente.")
            print("El sistema ahora utiliza exclusivamente workspaces.")
        else:
            print("\n⚠️  MIGRACIÓN PARCIAL")
            print("Las tablas de equipos aún existen en la base de datos.")
            print("Puede ejecutar la fase de eliminación en otro momento.")


async def main():
    """Función principal del asistente."""
    helper = TeamMigrationHelper()
    
    await helper.show_welcome()
    
    phases_completed = []
    
    try:
        # Fase 1: Verificación
        if await helper.phase_1_verification():
            phases_completed.append("Verificación de equipos")
            
            # Fase 2: Migración
            if await helper.phase_2_migration():
                phases_completed.append("Migración de equipos a workspaces")
                
                # Generar reporte intermedio
                await helper.generate_final_report()
                
                # Preguntar si desea proceder con la eliminación
                proceed_to_cleanup = input("\n¿Desea proceder con la eliminación de las tablas de equipos? (s/n): ").strip().lower()
                
                if proceed_to_cleanup == 's':
                    # Fase 3: Eliminación
                    if await helper.phase_3_cleanup():
                        phases_completed.append("Eliminación de tablas")
        
        # Mostrar resumen final
        await helper.show_final_summary(phases_completed)
        
    except KeyboardInterrupt:
        print("\n\nMigración cancelada por el usuario.")
        if phases_completed:
            print("Fases completadas hasta el momento:")
            for phase in phases_completed:
                print(f"- {phase}")
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())