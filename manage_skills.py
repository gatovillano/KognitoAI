#!/usr/bin/env python3
"""
Wrapper script to run skills management CLI from root directory.

This allows: python3 manage_skills.py list
Instead of:  python3 scripts/manage_skills.py list

Or with the correct venv:
venv_host/bin/python manage_skills.py list
"""

import sys
import os

# Add scripts directory to path
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
sys.path.insert(0, scripts_dir)

try:
    # Import and run the actual CLI
    from manage_skills import cli
    if __name__ == '__main__':
        cli()
except ImportError as e:
    print(f"❌ Error: {e}")
    print()
    print("Make sure to use the venv_host Python interpreter:")
    print("  venv_host/bin/python manage_skills.py [command]")
    print()
    print("Or activate the environment first:")
    print("  source venv_host/bin/activate.fish")
    print("  python manage_skills.py [command]")
    sys.exit(1)
