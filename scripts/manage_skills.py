#!/usr/bin/env python3
"""
CLI para gestión de Agent Skills
Uso: python scripts/manage_skills.py [command] [options]

Soporta skills desde:
- Local filesystem: ./path/to/skill
- GitHub: owner/repo o owner/repo/subdir
- skills.sh registry: owner/repo/skill-name
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional
from tabulate import tabulate

# Agregar root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.skill_installer import SkillInstaller, setup_skills_environment
from core.skill_sources import SkillSourceResolver, clear_cache


@click.group()
@click.option('--skills-dir', default='./skills', help='Path to skills directory')
@click.pass_context
def cli(ctx, skills_dir):
    """🧰 Agent Skills Manager - Instala, descubre y gestiona skills"""
    ctx.ensure_object(dict)
    ctx.obj['installer'] = SkillInstaller(skills_dir)


@cli.command()
@click.option('--filter', '-f', help='Filtrar por nombre/descripción')
@click.option('--json', 'output_json', is_flag=True, help='Output JSON')
@click.pass_context
def list(ctx, filter, output_json):
    """📋 Lista todos los skills instalados"""
    installer = ctx.obj['installer']
    
    if filter:
        skills = installer.search_skills(filter)
        if not skills:
            click.echo(f"❌ No skills found matching: {filter}")
            return
    else:
        skills = installer.discover_skills()
    
    if not skills:
        click.echo("No skills installed")
        return
    
    if output_json:
        data = [s.to_dict() for s in skills]
        click.echo(json.dumps(data, indent=2))
    else:
        data = [
            [s.name, s.description[:40] + "..." if len(s.description) > 40 else s.description, 
             s.license or "-", len(s.scripts or [])]
            for s in skills
        ]
        headers = ["Name", "Description", "License", "Scripts"]
        click.echo("\n" + tabulate(data, headers=headers, tablefmt="grid"))
        click.echo(f"\n✅ Total: {len(skills)} skills")


@cli.command()
@click.argument('name')
@click.option('--json', 'output_json', is_flag=True, help='Output JSON')
@click.pass_context
def show(ctx, name, output_json):
    """📖 Muestra detalles de un skill"""
    installer = ctx.obj['installer']
    
    try:
        skill = installer.load_skill(name)
    except ValueError:
        click.echo(f"❌ Skill not found: {name}")
        sys.exit(1)
    
    if output_json:
        click.echo(json.dumps(skill.to_dict(), indent=2))
    else:
        click.echo(f"\n🧰 Skill: {skill.name}")
        click.echo("=" * 80)
        click.echo(f"\nDescription:\n  {skill.description}")
        
        if skill.license:
            click.echo(f"\nLicense: {skill.license}")
        
        if skill.compatibility:
            click.echo(f"\nCompatibility:\n  {skill.compatibility}")
        
        if skill.scripts:
            click.echo(f"\nScripts ({len(skill.scripts)}):")
            for script in skill.scripts:
                click.echo(f"  - {script}")
        
        if skill.installed_at:
            click.echo(f"\nInstalled: {skill.installed_at}")
        
        click.echo("\n" + "=" * 80)


@cli.command()
@click.argument('identifier')
@click.option('--force', '-f', is_flag=True, help='Overwrite if already installed')
@click.pass_context
def install(ctx, identifier, force):
    """📥 Instala un skill desde diferentes fuentes
    
    Ejemplos:
      python manage_skills.py install ./local/path
      python manage_skills.py install owner/repo
      python manage_skills.py install owner/repo/subdir
      python manage_skills.py install owner/repo/skill-name
    """
    installer = ctx.obj['installer']
    
    try:
        click.echo(f"🔍 Resolving: {identifier}...")
        success = installer.install_from_identifier(identifier, force=force)
        
        if success:
            click.echo(f"✅ Skill installed successfully")
        else:
            click.echo(f"❌ Installation failed")
            sys.exit(1)
    
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@click.pass_context
def remove(ctx, name, yes):
    """🗑️  Desinstala un skill"""
    installer = ctx.obj['installer']
    
    success = installer.remove_skill(name, confirm=not yes)
    
    if not success:
        sys.exit(1)


@cli.command()
@click.option('--query', '-q', help='Search query')
@click.option('--source', '-s', type=click.Choice(['local', 'github', 'registry']), 
              help='Search source')
@click.pass_context
def search(ctx, query, source):
    """🔍 Busca skills por nombre o descripción
    
    Ejemplos:
      python manage_skills.py search -q "react"
      python manage_skills.py search -q "database" -s registry
      python manage_skills.py search -q "testing" -s github
    """
    installer = ctx.obj['installer']
    
    if not query:
        click.echo("❌ Please provide a search query: -q 'search term'")
        sys.exit(1)
    
    # Búsqueda local
    if not source or source == 'local':
        results = installer.search_skills(query, limit=20)
        
        if results:
            data = [
                [s.name, s.description[:40] + "..." if len(s.description) > 40 else s.description]
                for s in results
            ]
            headers = ["Name", "Description"]
            click.echo("\n📦 LOCAL SKILLS:")
            click.echo(tabulate(data, headers=headers, tablefmt="grid"))
            click.echo(f"✅ Found {len(results)} local skills\n")
    
    # Búsqueda en registry (skills.sh)
    if not source or source == 'registry':
        try:
            from core.skill_sources import SkillsShRegistry
            registry = SkillsShRegistry()
            
            click.echo("🔍 Searching skills.sh registry...")
            remote_results = registry.search(query, limit=10)
            
            if remote_results:
                data = [
                    [r.get('name', 'N/A'), r.get('description', 'N/A')[:40] + "..."]
                    for r in remote_results[:10]
                ]
                headers = ["Name", "Description"]
                click.echo("\n🌐 REGISTRY (skills.sh):")
                click.echo(tabulate(data, headers=headers, tablefmt="grid"))
                click.echo(f"✅ Found {len(remote_results)} remote skills\n")
        
        except Exception as e:
            click.echo(f"⚠️  Could not search registry: {e}")


@cli.command()
@click.argument('identifier')
@click.pass_context
def info(ctx, identifier):
    """ℹ️  Muestra información sobre un skill remoto
    
    Ejemplos:
      python manage_skills.py info owner/repo
      python manage_skills.py info owner/repo/subdir
      python manage_skills.py info ./local/skill
    """
    resolver = SkillSourceResolver()
    
    try:
        info_data = resolver.get_info(identifier)
        
        click.echo("\n" + "=" * 80)
        click.echo(f"Skill Info: {identifier}")
        click.echo("=" * 80)
        click.echo(json.dumps(info_data, indent=2))
        click.echo("=" * 80)
    
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def cache(ctx):
    """💾 Gestión de cache de skills descargados
    
    Muestra información del cache y opciones de limpieza
    """
    cache_dir = Path("./.skills-cache")
    
    if not cache_dir.exists():
        click.echo("Cache is empty")
        return
    
    # Contar archivos
    files = list(cache_dir.rglob("*"))
    skill_dirs = [d for d in cache_dir.iterdir() if d.is_dir()]
    
    click.echo("\n" + "=" * 80)
    click.echo("SKILLS CACHE")
    click.echo("=" * 80)
    click.echo(f"Location: {cache_dir}")
    click.echo(f"Cached skills: {len(skill_dirs)}")
    click.echo(f"Total files: {len(files)}")
    
    if skill_dirs:
        click.echo("\nCached items:")
        for skill_dir in sorted(skill_dirs):
            size = sum(f.stat().st_size for f in skill_dir.rglob("*") if f.is_file())
            size_mb = size / (1024 * 1024)
            click.echo(f"  - {skill_dir.name} ({size_mb:.2f} MB)")
    
    click.echo("\n" + "=" * 80)


@cli.command()
@click.confirmation_option(prompt='Clear all cached skills?')
@click.pass_context
def cache_clear(ctx):
    """🗑️  Limpia el cache de skills descargados"""
    try:
        clear_cache()
        click.echo("✅ Cache cleared")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx):
    """✅ Valida todos los skills instalados"""
    from scripts.validate_skills import SkillValidator
    
    installer = ctx.obj['installer']
    validator = SkillValidator(str(installer.skills_root))
    
    valid = validator.validate_all()
    
    if valid:
        click.echo("\n✅ All skills are valid!")
        sys.exit(0)
    else:
        click.echo("\n❌ Some skills have errors")
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """🚀 Inicializa el entorno de skills"""
    installer = ctx.obj['installer']
    
    # Crear estructura básica
    skills_root = installer.skills_root
    skills_root.mkdir(parents=True, exist_ok=True)
    
    # Crear directorios
    (skills_root / '_templates').mkdir(exist_ok=True)
    (skills_root / '_examples').mkdir(exist_ok=True)
    
    click.echo(f"✅ Skills environment initialized at: {skills_root}")
    
    # Descubrir skills existentes
    skills = installer.discover_skills()
    if skills:
        click.echo(f"📦 Found {len(skills)} existing skills")


@cli.command()
@click.pass_context
def registry(ctx):
    """📋 Muestra el registry de skills"""
    installer = ctx.obj['installer']
    
    registry_data = installer.get_all_metadata()
    
    if not registry_data:
        click.echo("Registry is empty")
        return
    
    click.echo(json.dumps(registry_data, indent=2))


@cli.command()
@click.argument('output', type=click.Path(), default='skills.json')
@click.pass_context
def export(ctx, output):
    """💾 Exporta metadata de skills a JSON"""
    installer = ctx.obj['installer']
    
    registry_data = installer.get_all_metadata()
    
    output_path = Path(output)
    with open(output_path, 'w') as f:
        json.dump(registry_data, f, indent=2)
    
    click.echo(f"✅ Exported {len(registry_data)} skills to {output_path}")


@cli.command()
@click.option('--all', '-a', is_flag=True, help='Setup para todos los scripts')
@click.pass_context
def setup(ctx, all):
    """⚙️  Configura el entorno para desarrollo"""
    installer = ctx.obj['installer']
    
    click.echo("🔧 Setting up skills environment...")
    
    # Configurar paths
    setup_skills_environment(str(installer.skills_root))
    
    click.echo("✅ Environment ready!")
    click.echo(f"   - Skills root: {installer.skills_root}")
    click.echo(f"   - Registry: {installer.registry_path}")
    
    # Validar
    skills = installer.discover_skills()
    click.echo(f"   - Skills found: {len(skills)}")


def main():
    """Entry point"""
    try:
        cli(obj={})
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
