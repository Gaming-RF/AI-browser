import PyInstaller.__main__
import os
import shutil

# Ensure we're in the right directory
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

# PyInstaller arguments
args = [
    'server.py',
    '--name=backend',
    '--onefile',
    '--clean',
    '--noconsole',
    '--add-data=static;static',
    '--add-data=src;src',
    '--hidden-import=uvicorn',
    '--hidden-import=fastapi',
    '--hidden-import=pydantic',
    '--hidden-import=playwright',
    '--hidden-import=httpx',
    '--hidden-import=src.core',
    '--hidden-import=src.memory.manager',
    '--hidden-import=src.agents.factory',
]

print("Starting PyInstaller build...")
PyInstaller.__main__.run(args)
print("Build complete. Executable is in the dist/ folder.")
