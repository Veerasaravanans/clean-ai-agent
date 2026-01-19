#!/usr/bin/env python3
"""
setup_directories.py - Create all project directories
"""

from pathlib import Path

# All directories to create
DIRECTORIES = [
    "backend/routes",
    "backend/services",
    "backend/tools",
    "backend/langgraph",
    "backend/models",
    "frontend",
    "data/test_cases",
    "data/prompts",
    "data/vector_db",
    "data/results",
    "data/screenshots",
    "tests/unit",
    "tests/integration",
    "tests/e2e",
    "scripts",
    "logs"
]

# __init__.py files to create
INIT_FILES = [
    "backend/__init__.py",
    "backend/routes/__init__.py",
    "backend/services/__init__.py",
    "backend/tools/__init__.py",
    "backend/langgraph/__init__.py",
    "backend/models/__init__.py",
    "tests/__init__.py",
    "tests/unit/__init__.py",
    "tests/integration/__init__.py",
    "tests/e2e/__init__.py"
]

def main():
    """Create all directories and __init__.py files."""
    print("Creating project structure...\n")
    
    # Create directories
    for directory in DIRECTORIES:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ {directory}/")
    
    print()
    
    # Create __init__.py files
    for init_file in INIT_FILES:
        path = Path(init_file)
        if not path.exists():
            path.write_text('"""Package initialization."""\n')
        print(f"✅ {init_file}")
    
    # Create .gitkeep files for empty data directories
    gitkeep_dirs = [
        "data/screenshots",
        "data/results",
        "data/vector_db"
    ]
    
    print()
    for directory in gitkeep_dirs:
        gitkeep = Path(directory) / ".gitkeep"
        gitkeep.touch(exist_ok=True)
        print(f"✅ {gitkeep}")
    
    print("\n✅ All directories created successfully!")

if __name__ == "__main__":
    main()