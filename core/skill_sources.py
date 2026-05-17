"""
Integraciones de skills desde diferentes fuentes:
- Local filesystem
- GitHub (owner/repo)
- skills.sh registry
"""

import os
import re
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse
import logging

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


class SkillSource:
    """Base class para fuentes de skills"""
    
    def resolve(self, identifier: str) -> Path:
        """Resuelve un identificador a una ruta local"""
        raise NotImplementedError
    
    def get_info(self, identifier: str) -> Dict:
        """Obtiene información sobre un skill"""
        raise NotImplementedError


class LocalSkillSource(SkillSource):
    """Skills desde filesystem local"""
    
    def resolve(self, identifier: str) -> Path:
        """Resuelve ruta local"""
        path = Path(identifier).resolve()
        
        if not path.exists():
            raise ValueError(f"Path not found: {identifier}")
        
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {identifier}")
        
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            raise ValueError(f"SKILL.md not found in {identifier}")
        
        return path
    
    def get_info(self, identifier: str) -> Dict:
        path = self.resolve(identifier)
        return {"type": "local", "path": str(path)}


class GitHubSkillSource(SkillSource):
    """Skills desde GitHub (owner/repo)"""
    
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    GITHUB_ARCHIVE_URL = "https://github.com/{owner}/{repo}/archive/{branch}.zip"
    
    def __init__(self, cache_dir: str = "./.skills-cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def resolve(self, identifier: str) -> Path:
        """
        Resuelve owner/repo o owner/repo/subdir
        Descarga desde GitHub y retorna ruta local
        """
        parts = identifier.split("/")
        
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub identifier: {identifier}")
        
        owner = parts[0]
        repo = parts[1]
        subdir = "/".join(parts[2:]) if len(parts) > 2 else "skills"
        
        # Verificar skill en GitHub
        self._verify_skill_exists(owner, repo, subdir)
        
        # Descargar o usar cache
        local_path = self._get_or_download(owner, repo, subdir)
        
        return local_path
    
    def get_info(self, identifier: str) -> Dict:
        """Obtiene información del skill en GitHub"""
        parts = identifier.split("/")
        owner = parts[0]
        repo = parts[1]
        subdir = "/".join(parts[2:]) if len(parts) > 2 else "skills"
        
        return {
            "type": "github",
            "owner": owner,
            "repo": repo,
            "subdir": subdir,
            "url": f"https://github.com/{owner}/{repo}",
            "raw_url": self.GITHUB_RAW_URL.format(owner=owner, repo=repo, branch="main")
        }
    
    def _verify_skill_exists(self, owner: str, repo: str, subdir: str = "skills"):
        """Verifica que SKILL.md existe en GitHub"""
        if not HAS_REQUESTS:
            logger.warning("requests not installed, skipping GitHub verification")
            return
        
        # Probar con main branch primero, luego master
        for branch in ["main", "master"]:
            url = f"{self.GITHUB_RAW_URL.format(owner=owner, repo=repo, branch=branch)}/{subdir}/SKILL.md"
            
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    return
            except:
                pass
        
        raise ValueError(f"SKILL.md not found in {owner}/{repo}/{subdir}")
    
    def _get_or_download(self, owner: str, repo: str, subdir: str = "skills") -> Path:
        """Descarga skill desde GitHub o usa cache"""
        cache_key = f"{owner}-{repo}-{subdir.replace('/', '-')}"
        cache_path = self.cache_dir / cache_key
        
        # Usar cache si existe
        if cache_path.exists():
            logger.info(f"Using cached skill: {cache_key}")
            return cache_path
        
        if not HAS_REQUESTS:
            raise RuntimeError("requests library required for GitHub downloads")
        
        logger.info(f"Downloading {owner}/{repo}:{subdir}...")
        
        # Descargar archive
        for branch in ["main", "master"]:
            archive_url = self.GITHUB_ARCHIVE_URL.format(owner=owner, repo=repo, branch=branch)
            
            try:
                response = requests.get(archive_url, timeout=30, stream=True)
                if response.status_code == 200:
                    return self._extract_skill(response, owner, repo, branch, subdir, cache_path)
            except Exception as e:
                logger.debug(f"Failed to download from {branch}: {e}")
        
        raise RuntimeError(f"Could not download {owner}/{repo} from GitHub")
    
    def _extract_skill(self, response, owner: str, repo: str, branch: str, 
                       subdir: str, cache_path: Path) -> Path:
        """Extrae el skill del archive ZIP"""
        import zipfile
        
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
        
        try:
            with zipfile.ZipFile(tmp_path) as zf:
                # Estructura esperada: {repo}-{branch}/{subdir}/*
                repo_dir = f"{repo}-{branch}"
                skill_path_in_zip = f"{repo_dir}/{subdir}"
                
                # Crear cache
                cache_path.mkdir(parents=True, exist_ok=True)
                
                # Extraer archivos del skill
                for file_info in zf.filelist:
                    if file_info.filename.startswith(skill_path_in_zip + "/"):
                        # Sacar la ruta relativa al skill
                        rel_path = file_info.filename[len(skill_path_in_zip)+1:]
                        
                        if rel_path:  # Skip el directorio mismo
                            target = cache_path / rel_path
                            target.parent.mkdir(parents=True, exist_ok=True)
                            
                            with zf.open(file_info) as src:
                                with open(target, 'wb') as dst:
                                    dst.write(src.read())
            
            logger.info(f"Extracted to: {cache_path}")
            return cache_path
        
        finally:
            tmp_path.unlink()


class SkillsShRegistry(SkillSource):
    """Skills desde registry skills.sh"""
    
    REGISTRY_URL = "https://www.skills.sh"
    API_URL = "https://api.skills.sh"
    
    def __init__(self):
        if not HAS_REQUESTS:
            raise RuntimeError("requests library required for skills.sh")
    
    def resolve(self, identifier: str) -> Path:
        """Resuelve desde skills.sh y delega a GitHub"""
        # skills.sh skills son en realidad GitHub repos
        # owner/repo/skill-name → owner/repo
        parts = identifier.split("/")
        
        if len(parts) == 2:
            owner, repo = parts
            # Buscar en skills.sh
            return GitHubSkillSource().resolve(f"{owner}/{repo}")
        elif len(parts) == 3:
            owner, repo, skill_name = parts
            # Buscar el skill específico
            return self._resolve_specific_skill(owner, repo, skill_name)
        
        raise ValueError(f"Invalid skills.sh identifier: {identifier}")
    
    def get_info(self, identifier: str) -> Dict:
        """Obtiene información desde skills.sh"""
        try:
            url = f"{self.API_URL}/skills/{identifier}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return {"type": "skills-registry", "identifier": identifier}
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Busca skills en skills.sh"""
        try:
            url = f"{self.API_URL}/search"
            params = {"q": query, "limit": limit}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json().get("results", [])
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        return []
    
    def _resolve_specific_skill(self, owner: str, repo: str, skill_name: str) -> Path:
        """Resuelve un skill específico"""
        # Buscar el skill en la carpeta de skills del repo
        github = GitHubSkillSource()
        
        # Probar directorios comunes
        for subdir in [f"skills/{skill_name}", f"agent-skills/{skill_name}", skill_name]:
            try:
                return github.resolve(f"{owner}/{repo}/{subdir}")
            except:
                pass
        
        raise ValueError(f"Skill not found: {owner}/{repo}/{skill_name}")


class SkillSourceResolver:
    """Resuelve fuentes automáticamente"""
    
    def __init__(self, cache_dir: str = "./.skills-cache"):
        self.local = LocalSkillSource()
        self.github = GitHubSkillSource(cache_dir)
        self.registry = SkillsShRegistry() if HAS_REQUESTS else None

    def normalize_identifier(self, identifier: str) -> str:
        """Normaliza URLs y rutas a un identificador canónico."""
        identifier = identifier.strip()

        if not identifier:
            return identifier

        if identifier.startswith(("http://", "https://")):
            parsed = urlparse(identifier)
            host = parsed.netloc.lower()
            parts = [part for part in parsed.path.split("/") if part]

            if "github.com" in host and len(parts) >= 2:
                owner, repo = parts[0], parts[1]

                if len(parts) >= 4 and parts[2] in {"tree", "blob", "raw"}:
                    remainder = parts[4:]
                    if remainder and remainder[-1].lower().endswith(".md"):
                        remainder = remainder[:-1]
                    if remainder:
                        return f"{owner}/{repo}/{'/'.join(remainder)}"
                    return f"{owner}/{repo}"

                if len(parts) > 2:
                    remainder = parts[2:]
                    if remainder and remainder[-1].lower().endswith(".md"):
                        remainder = remainder[:-1]
                    if remainder:
                        return f"{owner}/{repo}/{'/'.join(remainder)}"

                return f"{owner}/{repo}"

            if "skills.sh" in host and len(parts) >= 3:
                return "/".join(parts[-3:])

        return identifier
    
    def resolve(self, identifier: str) -> Path:
        """Resuelve un identificador a una ruta local"""
        identifier = self.normalize_identifier(identifier)
        
        # 1. Probar local (ruta con / o ./)
        if "/" in identifier or "\\" in identifier:
            if Path(identifier).exists():
                try:
                    return self.local.resolve(identifier)
                except:
                    pass  # No es local, intentar como remote
        
        # 2. Probar como GitHub (owner/repo o owner/repo/path)
        if re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_-]+)?$', identifier):
            try:
                return self.github.resolve(identifier)
            except Exception as e:
                logger.debug(f"Not a valid GitHub path: {e}")
        
        # 3. Probar como skills.sh
        if self.registry and len(identifier.split("/")) >= 2:
            try:
                return self.registry.resolve(identifier)
            except:
                pass
        
        # No se pudo resolver
        raise ValueError(
            f"Could not resolve skill identifier: {identifier}\n"
            f"Supported formats:\n"
            f"  - Local: ./path/to/skill or /absolute/path\n"
            f"  - GitHub: owner/repo or owner/repo/subdir\n"
            f"  - skills.sh: owner/repo or owner/repo/skill-name"
        )
    
    def get_info(self, identifier: str) -> Dict:
        """Obtiene información sobre la fuente"""
        normalized = self.normalize_identifier(identifier)
        
        # Detectar tipo
        if Path(normalized).exists() or ("/" in normalized and normalized.startswith((".","/"))):
            info = self.local.get_info(normalized)
            info["normalized"] = normalized
            return info
        
        if re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+', normalized):
            info = self.github.get_info(normalized)
            info["normalized"] = normalized
            return info
        
        if self.registry:
            info = self.registry.get_info(normalized)
            info["normalized"] = normalized
            return info
        
        return {"type": "unknown", "normalized": normalized}


def clear_cache(cache_dir: str = "./.skills-cache"):
    """Limpia cache de skills descargados"""
    cache_path = Path(cache_dir)
    if cache_path.exists():
        shutil.rmtree(cache_path)
        logger.info(f"Cache cleared: {cache_dir}")
