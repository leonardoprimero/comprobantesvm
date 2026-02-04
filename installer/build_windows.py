"""
Script de build para Windows.
Genera Launcher.exe y Api.exe, copia bot, node, chromium y poppler.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def run(cmd, cwd=ROOT):
    print("Running:", " ".join(map(str, cmd)))
    subprocess.check_call(cmd, cwd=cwd)


def clean_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def find_chromium_exe() -> Optional[Path]:
    """Busca el ejecutable de Chromium en cache de Puppeteer o local."""
    # 1. Buscar en cache global (Puppeteer nuevo)
    home = Path.home()
    
    # Rutas posibles de cache
    cache_roots = [
        home / ".cache" / "puppeteer",
        home / ".config" / "puppeteer",  # A veces aquí
    ]
    
    # Soporte para XDG_CACHE_HOME
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        cache_roots.insert(0, Path(xdg_cache) / "puppeteer")

    # 2. Buscar en node_modules local (legacy)
    cache_roots.append(ROOT / "bot" / "node_modules" / "puppeteer" / ".local-chromium")

    print(f"Buscando Chromium en: {[str(p) for p in cache_roots]}")

    for root in cache_roots:
        if root.exists():
            # Buscar recursivamente
            matches = list(root.rglob("chrome.exe" if sys.platform == "win32" else "chrome"))
            if not matches and sys.platform == "darwin":
                 matches = list(root.rglob("Chromium"))
                 
            if matches:
                print(f"Chromium encontrado en: {matches[0]}")
                return matches[0]

    return None


def copy_bot(dest: Path):
    def _ignore(path, names):
        ignore = set()
        if ".local-chromium" in names:
            ignore.add(".local-chromium")
        if ".cache" in names:
            ignore.add(".cache")
        return ignore

    bot_src = ROOT / "bot"
    bot_dest = dest / "bot"
    shutil.copytree(bot_src, bot_dest, dirs_exist_ok=True, ignore=_ignore)


def main():
    clean_dir(DIST)
    (BUILD / "pyinstaller").mkdir(parents=True, exist_ok=True)

    # Build Launcher (GUI)
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--workpath", str(BUILD / "pyinstaller"),
        "--distpath", str(DIST),
        "--name", "Launcher",
        "--paths", ".",  # Include project root for local modules
        "--collect-all", "customtkinter",
        "--hidden-import", "app",
        "--hidden-import", "app.paths",
        "--hidden-import", "app.license",
        "--hidden-import", "storage",
        "--hidden-import", "storage.sheets_storage",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "qrcode",
        "launcher.py"
    ])

    # Build API (onefile)
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--workpath", str(BUILD / "pyinstaller"),
        "--distpath", str(DIST),
        "--name", "Api",
        "--paths", ".",  # Include project root for local modules
        # Hidden imports for all project modules
        "--hidden-import", "app",
        "--hidden-import", "app.main",
        "--hidden-import", "app.extractor",
        "--hidden-import", "app.paths",
        "--hidden-import", "app.license",
        "--hidden-import", "app.config",
        "--hidden-import", "app.validator",
        "--hidden-import", "app.sheets",
        "--hidden-import", "storage",
        "--hidden-import", "storage.storage_manager",
        "--hidden-import", "storage.excel_storage",
        "--hidden-import", "storage.sheets_storage",
        "--hidden-import", "billing",
        "--hidden-import", "billing.cost_tracker",
        "--hidden-import", "watcher",
        "--hidden-import", "watcher.folder_watcher",
        # External dependencies
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "fastapi",
        "--hidden-import", "starlette",
        "--hidden-import", "pydantic",
        "--hidden-import", "openai",
        "--hidden-import", "httpx",
        "--hidden-import", "pdf2image",
        "--hidden-import", "openpyxl",
        "--hidden-import", "gspread",
        "--hidden-import", "PIL",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        # Force collect all local project modules
        "--collect-submodules", "app",
        "--collect-submodules", "storage",
        "--collect-submodules", "billing",
        "--collect-submodules", "watcher",
        "run.py"
    ])

    launcher_dir = DIST / "Launcher"
    api_exe = DIST / "Api.exe"
    if api_exe.exists():
        shutil.copy2(api_exe, launcher_dir / "Api.exe")
    else:
        raise FileNotFoundError(f"Api.exe NO fue generado en: {api_exe}")

    # Config example
    config_example = ROOT / "config.example.json"
    if config_example.exists():
        shutil.copy2(config_example, launcher_dir / "config.example.json")

    # Copy bot + node_modules
    copy_bot(launcher_dir)

    # Copy node portable
    node_src = BUILD / "node"
    if node_src.exists():
        shutil.copytree(node_src, launcher_dir / "node", dirs_exist_ok=True)

    # Copy Chromium (from puppeteer)
    chrome_exe = find_chromium_exe()
    if chrome_exe:
        chrome_dir = chrome_exe.parent
        chromium_dest = launcher_dir / "chromium"
        if chromium_dest.exists():
            shutil.rmtree(chromium_dest)
        shutil.copytree(chrome_dir, chromium_dest)

    # Copy Poppler
    poppler_src = BUILD / "poppler"
    if poppler_src.exists():
        shutil.copytree(poppler_src, launcher_dir / "poppler", dirs_exist_ok=True)

    # Extra docs
    readme = ROOT / "README_CLIENTE.md"
    if readme.exists():
        shutil.copy2(readme, launcher_dir / "README_CLIENTE.md")


if __name__ == "__main__":
    main()
