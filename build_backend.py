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
    f'--add-data=static{os.pathsep}static',
    f'--add-data=src{os.pathsep}src',
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
