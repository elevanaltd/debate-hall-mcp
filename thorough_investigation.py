#!/usr/bin/env python3
"""Thorough investigation of module loading issues."""

import importlib.metadata
import importlib.util
import json
import os
import site
import subprocess
import sys
from pathlib import Path


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_python_info():
    """Check Python interpreter information."""
    print_section("Python Interpreter Information")
    print(f"Executable: {sys.executable}")
    print(f"Version: {sys.version}")
    print(f"Prefix: {sys.prefix}")
    print(f"Base Prefix: {sys.base_prefix}")
    print(f"Virtual Environment: {hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)}")

def check_sys_path():
    """Check Python sys.path."""
    print_section("Python sys.path")
    for i, path in enumerate(sys.path):
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"{i:2}. [{exists}] {path}")

def check_site_packages():
    """Check site-packages directories."""
    print_section("Site Packages Directories")
    for path in site.getsitepackages():
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"[{exists}] {path}")

    print("\nUser site packages:")
    user_site = site.getusersitepackages()
    exists = "✓" if os.path.exists(user_site) else "✗"
    print(f"[{exists}] {user_site}")

def check_installed_packages():
    """Check installed packages related to debate-hall-mcp."""
    print_section("Installed Packages")

    # Check pip list
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"],
                              capture_output=True, text=True, check=True)
        packages = json.loads(result.stdout)

        print("Relevant packages:")
        for pkg in packages:
            if any(name in pkg['name'].lower() for name in ['debate', 'mcp', 'octave']):
                print(f"  - {pkg['name']} {pkg['version']}")
    except Exception as e:
        print(f"Error checking pip list: {e}")

    # Check package metadata
    print("\nPackage metadata:")
    try:
        metadata = importlib.metadata.metadata('debate-hall-mcp')
        print(f"  Name: {metadata['Name']}")
        print(f"  Version: {metadata['Version']}")
        print(f"  Summary: {metadata.get('Summary', 'N/A')}")
    except Exception as e:
        print(f"  Error getting metadata: {e}")

def check_project_structure():
    """Check project directory structure."""
    print_section("Project Structure")

    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")

    # Check key directories
    dirs_to_check = [
        'src',
        'src/debate_hall_mcp',
        '.venv',
        '.venv/lib',
        'tests'
    ]

    for dir_path in dirs_to_check:
        full_path = project_root / dir_path
        exists = "✓" if full_path.exists() else "✗"
        is_dir = "DIR" if full_path.is_dir() else "FILE" if full_path.exists() else "N/A"
        print(f"[{exists}] {dir_path:30} ({is_dir})")

    # Check for __init__.py files
    print("\n__init__.py files:")
    src_path = project_root / 'src'
    if src_path.exists():
        for init_file in src_path.rglob('__init__.py'):
            rel_path = init_file.relative_to(project_root)
            size = init_file.stat().st_size
            print(f"  {rel_path} ({size} bytes)")

def check_pth_files():
    """Check for .pth files that might affect imports."""
    print_section("PTH Files")

    for path in sys.path:
        if os.path.exists(path):
            pth_files = list(Path(path).glob('*.pth'))
            if pth_files:
                print(f"\nIn {path}:")
                for pth_file in pth_files:
                    print(f"  {pth_file.name}:")
                    try:
                        content = pth_file.read_text()
                        for line in content.splitlines():
                            if line and not line.startswith('#'):
                                print(f"    -> {line}")
                    except Exception as e:
                        print(f"    Error reading: {e}")

def check_venv_activation():
    """Check virtual environment activation state."""
    print_section("Virtual Environment Status")

    # Check VIRTUAL_ENV
    venv_path = os.environ.get('VIRTUAL_ENV')
    print(f"VIRTUAL_ENV: {venv_path or 'Not set'}")

    # Check if we're in a venv
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"In virtual environment: {in_venv}")

    # Check venv Python vs system Python
    if sys.executable.startswith('/Volumes/HestAI-Projects'):
        print("Using project venv Python: ✓")
    else:
        print("Using system Python: ✗")

def test_imports():
    """Test different import methods."""
    print_section("Import Tests")

    # Test 1: Direct import
    print("\n1. Direct import:")
    try:
        import debate_hall_mcp
        print(f"   ✓ Success: {debate_hall_mcp.__file__}")
        print(f"   Version: {debate_hall_mcp.__version__}")
    except ImportError as e:
        print(f"   ✗ Failed: {e}")

    # Test 2: Add src to path
    print("\n2. With src in path:")
    project_root = Path(__file__).parent
    src_path = str(project_root / 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        print(f"   Added {src_path} to sys.path")

    try:
        # Remove from cache if previously failed
        if 'debate_hall_mcp' in sys.modules:
            del sys.modules['debate_hall_mcp']
        import debate_hall_mcp
        print(f"   ✓ Success: {debate_hall_mcp.__file__}")
        print(f"   Version: {debate_hall_mcp.__version__}")
    except ImportError as e:
        print(f"   ✗ Failed: {e}")

    # Test 3: Check importlib
    print("\n3. Using importlib.util:")
    spec = importlib.util.find_spec('debate_hall_mcp')
    if spec:
        print(f"   ✓ Module found at: {spec.origin}")
        print(f"   Submodule locations: {spec.submodule_search_locations}")
    else:
        print("   ✗ Module not found")

def check_pyproject_toml():
    """Check pyproject.toml configuration."""
    print_section("pyproject.toml Configuration")

    project_root = Path(__file__).parent
    pyproject_path = project_root / 'pyproject.toml'

    if pyproject_path.exists():
        print("pyproject.toml exists: ✓")

        try:
            import tomllib
            with open(pyproject_path, 'rb') as f:
                config = tomllib.load(f)

            print("\nProject metadata:")
            project = config.get('project', {})
            print(f"  Name: {project.get('name', 'N/A')}")
            print(f"  Version: {project.get('version', 'N/A')}")

            print("\nBuild system:")
            build = config.get('build-system', {})
            print(f"  Backend: {build.get('build-backend', 'N/A')}")
            print(f"  Requires: {build.get('requires', [])}")

            print("\nHatch configuration:")
            hatch = config.get('tool', {}).get('hatch', {})
            if hatch:
                targets = hatch.get('build', {}).get('targets', {})
                wheel = targets.get('wheel', {})
                print(f"  Wheel packages: {wheel.get('packages', 'N/A')}")
        except Exception as e:
            print(f"Error parsing pyproject.toml: {e}")
    else:
        print("pyproject.toml exists: ✗")

def check_editable_install():
    """Check if package is installed in editable mode."""
    print_section("Editable Installation Check")

    # Method 1: Check for .pth file
    for path in sys.path:
        if '.venv' in path and 'site-packages' in path:
            pth_file = Path(path) / '_debate_hall_mcp.pth'
            if pth_file.exists():
                print(f"Editable install .pth file found: {pth_file}")
                print(f"  Content: {pth_file.read_text().strip()}")
                return

    # Method 2: Check pip show
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "show", "-f", "debate-hall-mcp"],
                              capture_output=True, text=True, check=True)
        if 'Editable project location' in result.stdout:
            print("Package is installed in editable mode: ✓")
            for line in result.stdout.splitlines():
                if 'Editable' in line or 'Location' in line:
                    print(f"  {line}")
        else:
            print("Package is NOT installed in editable mode: ✗")
            print("  This is likely the issue!")
    except Exception as e:
        print(f"Error checking pip show: {e}")

def main():
    """Run all checks."""
    print("="*60)
    print("  MODULE LOADING INVESTIGATION REPORT")
    print("="*60)

    check_python_info()
    check_venv_activation()
    check_sys_path()
    check_site_packages()
    check_project_structure()
    check_pyproject_toml()
    check_installed_packages()
    check_pth_files()
    check_editable_install()
    test_imports()

    print_section("Summary")
    print("""
Diagnosis complete. Look for:
1. ✗ marks indicating missing/failed items
2. Whether the package is installed in editable mode
3. Whether virtual environment is properly activated
4. Whether src directory needs to be in PYTHONPATH
    """)

if __name__ == "__main__":
    main()
