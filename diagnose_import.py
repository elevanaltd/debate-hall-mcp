import importlib.util
import os
import sys
import sysconfig


def print_python_path():
    print("Python Path:")
    for path in sys.path:
        print(f"  - {path}")

def print_module_search_locations(module_name):
    print(f"\nSearching for module: {module_name}")
    spec = importlib.util.find_spec(module_name)
    if spec:
        print("Module found:")
        print(f"  - Location: {spec.origin}")
        print(f"  - Submodule search locations: {spec.submodule_search_locations}")
    else:
        print("  Module not found")

def print_site_packages_info():
    site_packages_path = sysconfig.get_paths()['purelib']
    print(f"\nSite-packages path: {site_packages_path}")
    print("Installed packages:")
    try:
        import pkg_resources
        for package in sorted(pkg_resources.working_set, key=lambda x: x.project_name):
            print(f"  - {package.project_name} {package.version}")
    except ImportError:
        print("  Unable to list packages (pkg_resources not available)")

def print_project_structure(directory):
    print(f"\nProject Structure at {directory}:")
    for root, _dirs, files in os.walk(directory):
        level = root.replace(directory, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")

def main():
    print("Python Import Diagnostic Tool\n")

    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Print general diagnostic information
    print_python_path()
    print_module_search_locations("debate_hall_mcp")
    print_site_packages_info()
    print_project_structure(current_dir)

    # Attempt to import the module
    try:
        import debate_hall_mcp
        print("\n✓ Module import successful")
        print(f"Module version: {debate_hall_mcp.__version__}")
    except ImportError as e:
        print(f"\n❌ Module import failed: {e}")
        print("\nPossible reasons:")
        print("1. PYTHONPATH not set correctly")
        print("2. Package not installed in editable mode")
        print("3. Project structure misconfiguration")

if __name__ == "__main__":
    main()
