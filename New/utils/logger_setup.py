"""
Session logging: last_session.log (overwrite) + rotated session_1..session_5.
Logger namespace: SIGNUM_SENTINEL.<MODULE>
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from utils.runtime_paths import get_app_root


def init_session_logging(root: Optional[Path] = None) -> Path:
    """
    Call once at application start before other modules log.
    Returns path to logs directory.
    """
    app = Path(root).resolve() if root else get_app_root()
    log_dir = app / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    last = log_dir / "last_session.log"
    if last.exists():
        _rotate_sessions(log_dir)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for h in list(root_logger.handlers):
        if getattr(h, "_signum_session", False):
            root_logger.removeHandler(h)

    fh = logging.FileHandler(last, mode="w", encoding="utf-8")
    fh.setFormatter(fmt)
    fh._signum_session = True  # type: ignore[attr-defined]
    root_logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch._signum_session = True  # type: ignore[attr-defined]
    root_logger.addHandler(ch)

    logging.getLogger("SIGNUM_SENTINEL").info("Session logging initialized -> %s", last)
    return log_dir


def _rotate_sessions(log_dir: Path) -> None:
    """Drop session_5; shift 4->5 ... 1->2; last_session -> session_1."""
    s5 = log_dir / "session_5.log"
    if s5.exists():
        s5.unlink()
    for i in range(5, 2, -1):
        a = log_dir / f"session_{i - 1}.log"
        b = log_dir / f"session_{i}.log"
        if b.exists():
            b.unlink()
        if a.exists():
            shutil.move(str(a), str(b))
    s1 = log_dir / "session_1.log"
    s2 = log_dir / "session_2.log"
    if s2.exists():
        s2.unlink()
    if s1.exists():
        shutil.move(str(s1), str(s2))
    last = log_dir / "last_session.log"
    if last.exists():
        shutil.move(str(last), str(s1))
