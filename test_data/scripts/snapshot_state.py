# -*- coding: utf-8 -*-
"""Génère ``test_data/.test_state.json`` — empreinte SHA-256 + date de chaque
fichier source au moment de la qualification.

Sert au diagnostic « Phase 0 » du protocole de qualification : à la campagne
suivante, comparer l'état courant à ce fichier permet de savoir quels modules
ont changé et donc quels tests/inputs/références mettre à jour.

Usage :
    python test_data/scripts/snapshot_state.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATE_PATH = ROOT / "test_data" / ".test_state.json"

# Périmètre source suivi (logique métier + UI + build + entrée).
SOURCE_GLOBS = ["src/**/*.py", "main.py", "build.py"]
# On exclut les secrets (gitignored) et les caches.
EXCLUDE_PARTS = {"__pycache__", "_secret.py"}


def _iter_sources():
    for pattern in SOURCE_GLOBS:
        for p in sorted(ROOT.glob(pattern)):
            if any(part in EXCLUDE_PARTS for part in p.parts) or p.name in EXCLUDE_PARTS:
                continue
            yield p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main() -> None:
    files = {}
    for p in _iter_sources():
        rel = p.relative_to(ROOT).as_posix()
        stat = p.stat()
        files[rel] = {
            "sha256": _sha256(p),
            "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "size": stat.st_size,
        }

    state = {
        "qualified_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "source_count": len(files),
        "files": files,
    }
    STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"OK : {STATE_PATH}")
    print(f"  - {len(files)} fichiers source empreintés (commit {state['git_commit']})")


if __name__ == "__main__":
    main()
