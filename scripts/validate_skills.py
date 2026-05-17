#!/usr/bin/env python3
"""
Validador de Skills según especificación agentskills.io
Verifica que cada skill tenga SKILL.md con frontmatter válido
"""

import os
import yaml
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Especificación de campos SKILL.md
REQUIRED_FIELDS = {"name", "description"}
OPTIONAL_FIELDS = {"license", "compatibility", "metadata", "allowed-tools"}
ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

# Reglas de validación
CONSTRAINTS = {
    "name": {
        "max_length": 64,
        "pattern": r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",  # lowercase-with-hyphens
        "rules": "lowercase letters, numbers, hyphens only"
    },
    "description": {
        "max_length": 1024,
        "min_length": 10,
        "rules": "clear description of what and when to use"
    },
    "license": {
        "examples": ["MIT", "Apache-2.0", "Proprietary"]
    },
    "compatibility": {
        "max_length": 500
    }
}


class SkillValidator:
    def __init__(self, skills_root: str = "./skills"):
        self.skills_root = Path(skills_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.successes: List[str] = []
        self.results: Dict[str, Dict] = {}

    def validate_all(self) -> bool:
        """Validate all skills in the directory"""
        if not self.skills_root.exists():
            print(f"❌ Skills directory not found: {self.skills_root}")
            return False

        skill_dirs = [d for d in self.skills_root.iterdir() if d.is_dir() and not d.name.startswith("_")]
        
        if not skill_dirs:
            print(f"⚠️  No skills found in {self.skills_root}")
            return False

        print(f"🔍 Validating {len(skill_dirs)} skills...\n")

        for skill_dir in sorted(skill_dirs):
            self.validate_skill(skill_dir)

        self._print_summary()
        return len(self.errors) == 0

    def validate_skill(self, skill_dir: Path) -> bool:
        """Validate a single skill"""
        skill_name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"

        self.results[skill_name] = {
            "errors": [],
            "warnings": [],
            "valid": False
        }

        # Check if SKILL.md exists
        if not skill_md.exists():
            msg = f"❌ {skill_name}: SKILL.md not found"
            print(msg)
            self.errors.append(msg)
            self.results[skill_name]["errors"].append("SKILL.md not found")
            return False

        # Read and parse SKILL.md
        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract frontmatter
            if not content.startswith("---"):
                msg = f"❌ {skill_name}: SKILL.md must start with '---'"
                print(msg)
                self.errors.append(msg)
                self.results[skill_name]["errors"].append("Missing YAML frontmatter")
                return False

            parts = content.split("---", 2)
            if len(parts) < 3:
                msg = f"❌ {skill_name}: Invalid YAML frontmatter format"
                print(msg)
                self.errors.append(msg)
                self.results[skill_name]["errors"].append("Invalid frontmatter")
                return False

            try:
                frontmatter = yaml.safe_load(parts[1])
            except yaml.YAMLError as e:
                msg = f"❌ {skill_name}: Invalid YAML: {e}"
                print(msg)
                self.errors.append(msg)
                self.results[skill_name]["errors"].append(f"YAML parse error: {e}")
                return False

            # Validate frontmatter
            valid = self._validate_frontmatter(skill_name, frontmatter)
            
            # Validate directory structure
            self._validate_structure(skill_name, skill_dir)

            if valid:
                msg = f"✅ {skill_name}"
                print(msg)
                self.successes.append(msg)
                self.results[skill_name]["valid"] = True

            return valid

        except Exception as e:
            msg = f"❌ {skill_name}: Error reading SKILL.md: {e}"
            print(msg)
            self.errors.append(msg)
            self.results[skill_name]["errors"].append(str(e))
            return False

    def _validate_frontmatter(self, skill_name: str, frontmatter: dict) -> bool:
        """Validate YAML frontmatter"""
        valid = True

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in frontmatter:
                msg = f"  ⚠️  Missing required field: {field}"
                print(msg)
                self.warnings.append(f"{skill_name}: {msg}")
                self.results[skill_name]["errors"].append(f"Missing field: {field}")
                valid = False
            elif frontmatter[field] is None or frontmatter[field] == "":
                msg = f"  ⚠️  Field '{field}' is empty"
                print(msg)
                self.warnings.append(f"{skill_name}: {msg}")
                self.results[skill_name]["errors"].append(f"Empty field: {field}")
                valid = False

        # Validate 'name' field
        if "name" in frontmatter:
            name_valid = self._validate_field_name(frontmatter["name"])
            if not name_valid:
                msg = f"  ❌ Invalid 'name': {frontmatter['name']}"
                print(msg)
                self.errors.append(f"{skill_name}: {msg}")
                self.results[skill_name]["errors"].append("Invalid name format")
                valid = False
            
            # Name should match directory name
            if frontmatter["name"] != skill_name:
                msg = f"  ⚠️  'name' field doesn't match directory name: {frontmatter['name']} != {skill_name}"
                print(msg)
                self.warnings.append(f"{skill_name}: {msg}")
                self.results[skill_name]["warnings"].append("Name mismatch with directory")

        # Validate 'description' field
        if "description" in frontmatter:
            desc = frontmatter["description"]
            if len(desc) < CONSTRAINTS["description"]["min_length"]:
                msg = f"  ⚠️  Description too short (min {CONSTRAINTS['description']['min_length']} chars)"
                print(msg)
                self.warnings.append(f"{skill_name}: {msg}")
                self.results[skill_name]["warnings"].append("Description too short")
            
            if len(desc) > CONSTRAINTS["description"]["max_length"]:
                msg = f"  ❌ Description too long (max {CONSTRAINTS['description']['max_length']} chars)"
                print(msg)
                self.errors.append(f"{skill_name}: {msg}")
                self.results[skill_name]["errors"].append("Description too long")
                valid = False

        # Check unknown fields
        unknown = set(frontmatter.keys()) - ALL_FIELDS
        if unknown:
            msg = f"  ⚠️  Unknown fields in frontmatter: {', '.join(unknown)}"
            print(msg)
            self.warnings.append(f"{skill_name}: {msg}")

        return valid

    def _validate_field_name(self, name: str) -> bool:
        """Validate 'name' field according to spec"""
        import re
        
        if not isinstance(name, str):
            return False
        
        if len(name) > CONSTRAINTS["name"]["max_length"]:
            return False
        
        pattern = CONSTRAINTS["name"]["pattern"]
        if not re.match(pattern, name):
            return False
        
        return True

    def _validate_structure(self, skill_name: str, skill_dir: Path):
        """Validate directory structure"""
        # Check for scripts directory
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            scripts = list(scripts_dir.glob("*.py"))
            if scripts:
                msg = f"  📁 Found {len(scripts)} Python scripts"
                # print(msg)
                self.results[skill_name]["info"] = msg
        else:
            msg = f"  ⚠️  No scripts/ directory found"
            # print(msg)
            self.results[skill_name]["warnings"].append("No scripts directory")

        # Check for references directory
        refs_dir = skill_dir / "references"
        if refs_dir.exists():
            refs = list(refs_dir.glob("*.md"))
            if refs:
                msg = f"  📁 Found {len(refs)} reference files"
                # print(msg)

    def _print_summary(self):
        """Print validation summary"""
        total = len(self.results)
        valid = sum(1 for r in self.results.values() if r["valid"])
        
        print("\n" + "=" * 60)
        print(f"VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total skills: {total}")
        print(f"Valid: {valid} ✅")
        print(f"Issues: {total - valid} ⚠️")
        
        if self.errors:
            print(f"\n🔴 Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n🟡 Warnings ({len(self.warnings)}):")
            for warning in self.warnings[:5]:  # Show first 5
                print(f"  - {warning}")
            if len(self.warnings) > 5:
                print(f"  ... and {len(self.warnings) - 5} more")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Agent Skills")
    parser.add_argument("--skills-dir", default="./skills", help="Path to skills directory")
    parser.add_argument("--skill", help="Validate single skill (e.g., 'search-and-research')")
    
    args = parser.parse_args()
    
    validator = SkillValidator(args.skills_dir)
    
    if args.skill:
        skill_dir = Path(args.skills_dir) / args.skill
        if skill_dir.exists():
            valid = validator.validate_skill(skill_dir)
            sys.exit(0 if valid else 1)
        else:
            print(f"❌ Skill not found: {skill_dir}")
            sys.exit(1)
    else:
        valid = validator.validate_all()
        sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
