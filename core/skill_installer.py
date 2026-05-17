"""
Skills Installation and Management System

Proporciona instalación, descubrimiento y gestión de skills
siguiendo el estándar agentskills.io.
"""

import os
import sys
import yaml
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import importlib.util

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Metadata de un skill según agentskills.io spec"""
    name: str
    description: str
    path: Path
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    allowed_tools: Optional[str] = None
    scripts: List[str] = None
    installed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['path'] = str(d['path'])
        d['scripts'] = d.get('scripts', [])
        return d


class SkillInstaller:
    """Instala y gestiona skills"""
    
    def __init__(self, skills_root: str = "./skills", registry_path: str = "./.skills-registry.json"):
        self.skills_root = Path(skills_root)
        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()
        
        # Crear directorio si no existe
        self.skills_root.mkdir(parents=True, exist_ok=True)
    
    def install_local_skill(self, skill_path: str, force: bool = False) -> bool:
        """
        Instala un skill local.
        
        Args:
            skill_path: Ruta al skill a instalar (puede ser relativa o absoluta)
            force: Si True, sobrescribe skill existente
        
        Returns:
            True si la instalación fue exitosa
        """
        skill_path = Path(skill_path).resolve()
        
        if not skill_path.exists():
            print(f"❌ Error: Skill path not found: {skill_path}")
            return False
        
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            print(f"❌ Error: SKILL.md not found in {skill_path}")
            return False
        
        # Parsear metadata
        try:
            metadata = self._parse_skill_md(skill_md)
        except Exception as e:
            print(f"❌ Error parsing SKILL.md: {e}")
            return False
        
        # Validar
        if not self._validate_metadata(metadata):
            return False
        
        # Destino
        dest_path = self.skills_root / metadata.name
        
        # Verificar si ya existe
        if dest_path.exists() and not force:
            print(f"⚠️  Skill already installed: {metadata.name}")
            print(f"   Use --force to overwrite")
            return False
        
        # Copiar archivos
        try:
            if dest_path.exists():
                shutil.rmtree(dest_path)
            
            shutil.copytree(skill_path, dest_path)
            print(f"✅ Installed: {metadata.name}")
            
            # Registrar en registry
            metadata.installed_at = datetime.now().isoformat()
            self.registry[metadata.name] = metadata
            self._save_registry()
            
            return True
        
        except Exception as e:
            print(f"❌ Error installing skill: {e}")
            if dest_path.exists():
                shutil.rmtree(dest_path)
            return False

    def install_from_identifier(self, identifier: str, force: bool = False) -> bool:
        """
        Instala un skill desde un identificador local, GitHub o skills.sh.

        Args:
            identifier: Ruta local, URL o identificador remoto.
            force: Si True, sobrescribe skill existente.

        Returns:
            True si la instalación fue exitosa.
        """
        try:
            from core.skill_sources import SkillSourceResolver

            resolver = SkillSourceResolver()
            info = resolver.get_info(identifier)
            resolved_path = resolver.resolve(identifier)

            source_type = info.get("type", "unknown")
            normalized = info.get("normalized", identifier)

            print(f"🔎 Source detected: {source_type}")
            if normalized != identifier:
                print(f"   Normalized to: {normalized}")

            return self.install_local_skill(str(resolved_path), force=force)

        except Exception as e:
            print(f"❌ Error resolving skill identifier '{identifier}': {e}")
            return False
    
    def discover_skills(self) -> List[SkillMetadata]:
        """Descubre todos los skills instalados"""
        skills = []
        
        if not self.skills_root.exists():
            return skills
        
        for skill_dir in sorted(self.skills_root.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith('_'):
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    metadata = self._parse_skill_md(skill_md, skill_dir)
                    metadata.installed_at = self._get_install_time(skill_dir)
                    skills.append(metadata)
                except Exception as e:
                    logger.warning(f"Error parsing {skill_dir}: {e}")
        
        return skills
    
    def search_skills(self, query: str, limit: int = 10) -> List[SkillMetadata]:
        """Busca skills por descripción/tags/nombre"""
        import re
        
        all_skills = self.discover_skills()
        pattern = re.compile(query, re.IGNORECASE)
        
        results = []
        for skill in all_skills:
            if (pattern.search(skill.name) or 
                pattern.search(skill.description)):
                results.append(skill)
        
        return results[:limit]
    
    def load_skill(self, name: str) -> SkillMetadata:
        """Carga un skill específico por nombre"""
        skill_dir = self.skills_root / name
        skill_md = skill_dir / "SKILL.md"
        
        if not skill_md.exists():
            raise ValueError(f"Skill not found: {name}")
        
        return self._parse_skill_md(skill_md, skill_dir)
    
    def remove_skill(self, name: str, confirm: bool = True) -> bool:
        """Desinstala un skill"""
        skill_dir = self.skills_root / name
        
        if not skill_dir.exists():
            print(f"❌ Skill not found: {name}")
            return False
        
        if confirm:
            response = input(f"Remove skill '{name}'? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled")
                return False
        
        try:
            shutil.rmtree(skill_dir)
            if name in self.registry:
                del self.registry[name]
                self._save_registry()
            print(f"✅ Removed: {name}")
            return True
        except Exception as e:
            print(f"❌ Error removing skill: {e}")
            return False
    
    def list_skills(self) -> None:
        """Lista todos los skills instalados"""
        skills = self.discover_skills()
        
        if not skills:
            print("No skills installed")
            return
        
        print("\n" + "=" * 80)
        print(f"{'Skill Name':<30} {'Description':<45} {'License':<10}")
        print("=" * 80)
        
        for skill in skills:
            desc = skill.description[:40] + "..." if len(skill.description) > 40 else skill.description
            license_name = skill.license or "-"
            print(f"{skill.name:<30} {desc:<45} {license_name:<10}")
        
        print("=" * 80)
        print(f"Total: {len(skills)} skills")
    
    def show_skill(self, name: str) -> None:
        """Muestra detalles de un skill"""
        try:
            skill = self.load_skill(name)
        except ValueError:
            print(f"❌ Skill not found: {name}")
            return
        
        print("\n" + "=" * 80)
        print(f"Skill: {skill.name}")
        print("=" * 80)
        print(f"Description:\n  {skill.description}\n")
        
        if skill.license:
            print(f"License: {skill.license}")
        
        if skill.compatibility:
            print(f"Compatibility:\n  {skill.compatibility}\n")
        
        if skill.scripts:
            print(f"Scripts: {', '.join(skill.scripts)}")
        
        if skill.installed_at:
            print(f"Installed: {skill.installed_at}")
        
        print("=" * 80)
    
    def get_all_metadata(self) -> Dict[str, dict]:
        """Retorna todos los skills como dict (para serialización)"""
        skills = self.discover_skills()
        return {s.name: s.to_dict() for s in skills}
    
    # Private methods
    
    def _parse_skill_md(self, skill_md: Path, skill_dir: Optional[Path] = None) -> SkillMetadata:
        """Parsea SKILL.md y extrae metadata"""
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraer frontmatter
        if not content.startswith("---"):
            raise ValueError("SKILL.md must start with YAML frontmatter")
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid SKILL.md format")
        
        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        if not frontmatter:
            raise ValueError("Empty YAML frontmatter")
        
        # Extraer scripts
        scripts = []
        if skill_dir:
            scripts_dir = skill_dir / "scripts"
            if scripts_dir.exists():
                scripts = [p.name for p in scripts_dir.glob("*.py")]
        
        return SkillMetadata(
            name=frontmatter.get('name'),
            description=frontmatter.get('description'),
            path=skill_dir or skill_md.parent,
            license=frontmatter.get('license'),
            compatibility=frontmatter.get('compatibility'),
            metadata=frontmatter.get('metadata'),
            allowed_tools=frontmatter.get('allowed-tools'),
            scripts=scripts
        )
    
    def _validate_metadata(self, metadata: SkillMetadata) -> bool:
        """Valida metadata del skill"""
        if not metadata.name:
            print("❌ Error: Missing 'name' field")
            return False
        
        if not metadata.description:
            print("❌ Error: Missing 'description' field")
            return False
        
        # Validar nombre (lowercase-with-hyphens)
        import re
        if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', metadata.name):
            print(f"❌ Error: Invalid name format: {metadata.name}")
            print("   Name must be lowercase letters, numbers, and hyphens only")
            return False
        
        return True
    
    def _load_registry(self) -> dict:
        """Carga registry de skills instalados"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading registry: {e}")
        return {}
    
    def _save_registry(self) -> None:
        """Guarda registry"""
        try:
            data = {}
            for name, skill in self.registry.items():
                if isinstance(skill, SkillMetadata):
                    data[name] = skill.to_dict()
                else:
                    data[name] = skill
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def _get_install_time(self, skill_dir: Path) -> Optional[str]:
        """Obtiene timestamp de instalación"""
        try:
            stat = skill_dir.stat()
            return datetime.fromtimestamp(stat.st_mtime).isoformat()
        except:
            return None


def setup_skills_environment(skills_root: str = "./skills") -> SkillInstaller:
    """
    Configura el entorno de skills.
    Útil para ejecutar en sandbox o entorno inicializado.
    """
    installer = SkillInstaller(skills_root)
    
    # Agregar skills_root a sys.path para imports
    skills_path = Path(skills_root).resolve()
    if str(skills_path) not in sys.path:
        sys.path.insert(0, str(skills_path))
    
    return installer
