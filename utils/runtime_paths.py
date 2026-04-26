import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Writable runtime root.
    - Dev: current working directory
    - PyInstaller: directory of the executable
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def get_bundle_root() -> Path:
    """
    Read-only bundle root.
    - PyInstaller onefile/onedir: sys._MEIPASS
    - Dev: app root
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass).resolve()
    return get_app_root()


def resolve_resource(relative_path: str) -> Path:
    """
    Resolve resource path with fallback order:
    1) writable app root (dev and external deployments)
    2) bundled root (_MEIPASS)
    """
    rel = Path(relative_path)
    app_candidate = get_app_root() / rel
    if app_candidate.exists():
        return app_candidate
    return get_bundle_root() / rel
