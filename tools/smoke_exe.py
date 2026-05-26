"""Smoke test the freshly built PhotoOrganizer EXEs.

Lance chaque EXE depuis un tempdir hermétique (no VIRTUAL_ENV, no
PYTHONPATH), attend hold_seconds, puis force-kill via `taskkill /F /T`
pour ne pas laisser de fenêtre orpheline.

Status :
  * ALIVE      : l'EXE est toujours vivant à la fin du hold → OK
  * CRASHED rc : il est mort avant la fin du hold → check log tail
  * MISSING    : le fichier n'existe pas

Usage : ``python tools/smoke_exe.py``
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _kill_tree(pid: int) -> None:
    """Force-kill *pid* and every descendant. Windows-only."""
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _smoke(label: str, exe: Path, hold_seconds: float = 6.0) -> dict:
    if not exe.exists():
        return {"label": label, "status": "MISSING", "startup_s": 0.0, "size_mb": 0.0, "tail": ""}

    size_mb = exe.stat().st_size / (1024 * 1024)
    with tempfile.TemporaryDirectory(prefix=f"po_smoke_{label}_") as tmp:
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)
        env.pop("PYTHONPATH", None)
        log_path = Path(tmp) / "smoke.log"
        t0 = time.time()
        with log_path.open("wb") as logf:
            proc = subprocess.Popen(
                [str(exe)],
                cwd=tmp,
                stdout=logf,
                stderr=subprocess.STDOUT,
                env=env,
            )
        deadline = t0 + hold_seconds
        crashed_early = False
        while time.time() < deadline:
            if proc.poll() is not None:
                crashed_early = True
                break
            time.sleep(0.25)
        startup = time.time() - t0

        if crashed_early:
            status = f"CRASHED rc={proc.returncode}"
        else:
            _kill_tree(proc.pid)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            status = "ALIVE"

        try:
            tail = log_path.read_text("utf-8", errors="replace").splitlines()[-12:]
        except Exception:
            tail = []
    return {
        "label": label,
        "status": status,
        "startup_s": startup,
        "size_mb": size_mb,
        "tail": "\n".join(tail),
    }


def _read_version() -> str:
    """Lit ``__version__`` depuis ``src/__init__.py`` (source de vérité unique)."""
    import re

    init_path = Path(__file__).resolve().parent.parent / "src" / "__init__.py"
    try:
        text = init_path.read_text(encoding="utf-8")
    except OSError:
        return "0.0.0-unknown"
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else "0.0.0-unknown"


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    version = _read_version()
    cases = [
        ("release", repo / "dist" / f"PhotoOrganizer-{version}.exe"),
        ("debug", repo / "dist" / f"PhotoOrganizer-{version}-debug.exe"),
        ("light", repo / "dist" / f"PhotoOrganizer-{version}-light.exe"),
    ]
    any_failed = False
    found_any = False
    for label, exe in cases:
        if not exe.exists():
            # On ne traite que les variantes effectivement buildées.
            continue
        found_any = True
        r = _smoke(label, exe)
        ok = r["status"] == "ALIVE"
        any_failed = any_failed or not ok
        print(f"=== {label.upper()} ===")
        print(f"  exe       : {exe.name}")
        print(f"  size      : {r['size_mb']:.1f} MB")
        print(f"  status    : {r['status']}")
        print(f"  hold_time : {r['startup_s']:.2f} s")
        if r["tail"]:
            print("  log tail  :")
            for line in r["tail"].splitlines()[-6:]:
                # Le log peut contenir des chars non-cp1252 (chemins Unicode).
                # On force un encodage tolérant avant l'affichage console.
                safe = line.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
                safe = safe.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                    sys.stdout.encoding or "utf-8", errors="replace"
                )
                print(f"    {safe}")
        print()
    if not found_any:
        print(f"Aucun binaire trouvé pour version {version}. Lance d'abord `python build.py`.")
        return 2
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
