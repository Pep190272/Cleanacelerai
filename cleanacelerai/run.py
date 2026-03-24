"""Standalone run script for Cleanacelerai PRO.

Usage:
    python -m cleanacelerai.run
    # or from the project root:
    pyinstaller cleanacelerai.spec
"""
from cleanacelerai.src.main import main

if __name__ == "__main__":
    main()
