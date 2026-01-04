import os
import sys


def print_import_details():
    print("Python Path:")
    for path in sys.path:
        print(f"  - {path}")

    print("\nCurrent Working Directory:")
    print(f"  {os.getcwd()}")

    print("\nEnvironment Variables:")
    print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")

    print("\nTrying to import debate_hall_mcp:")
    try:
        import debate_hall_mcp
        print("  ✓ Import successful")
        print(f"  Location: {debate_hall_mcp.__file__}")
        print(f"  Version: {debate_hall_mcp.__version__}")
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")

    print("\nChecking sys.path for potential matches:")
    for path in sys.path:
        potential_module = os.path.join(path, 'debate_hall_mcp')
        if os.path.exists(potential_module):
            print(f"  Potential match: {potential_module}")

    print("\nTrying to add project source to path:")
    project_src = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
    sys.path.insert(0, project_src)
    print(f"  Added {project_src} to sys.path")

    print("\nRetrying import after path modification:")
    try:
        import debate_hall_mcp
        print("  ✓ Import successful after path modification")
        print(f"  Location: {debate_hall_mcp.__file__}")
        print(f"  Version: {debate_hall_mcp.__version__}")
    except ImportError as e:
        print(f"  ❌ Import still failed: {e}")

if __name__ == "__main__":
    print_import_details()
