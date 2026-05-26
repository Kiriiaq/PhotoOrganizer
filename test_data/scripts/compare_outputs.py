# -*- coding: utf-8 -*-
"""Compare ``test_data/outputs_reels/`` à ``test_data/outputs_reference/``.

Produit un rapport de diff lisible : pour chaque test scénario, vérifie :
  - Structure des dossiers (présence/absence)
  - Liste des fichiers feuilles
  - Cohérence (hash partiel pour fichiers binaires, ligne-à-ligne pour CSV/JSON)

Le rapport sort en stdout + dans ``test_data/outputs_reels/_diff_report.md``.

Usage :
    python test_data/scripts/compare_outputs.py
    python test_data/scripts/compare_outputs.py --only T-051
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Force UTF-8 stdout (Git Bash sous Windows = cp1252 par défaut)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REF_DIR = ROOT / "test_data" / "outputs_reference"
REAL_DIR = ROOT / "test_data" / "outputs_reels"


def list_tree(root: Path) -> dict:
    """Renvoie {relative_path: file_size} pour tout sous-arbre de ``root``."""
    if not root.exists():
        return {}
    result = {}
    for path in root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            # Ignore le fichier index csv/json horodaté (timestamp variable)
            if "_photoorganizer_index_" in rel:
                continue
            result[rel] = path.stat().st_size
    return result


def quick_hash(path: Path, n_bytes: int = 64 * 1024) -> str:
    """Hash partiel head+tail (rapide, suffisant pour comparer 2 copies)."""
    h = hashlib.blake2b(digest_size=16)
    size = path.stat().st_size
    with open(path, "rb") as f:
        h.update(f.read(n_bytes))
        if size > n_bytes * 2:
            f.seek(-n_bytes, os.SEEK_END)
            h.update(f.read(n_bytes))
    h.update(str(size).encode())
    return h.hexdigest()


def compare_one(test_id: str) -> dict:
    ref  = REF_DIR / test_id
    real = REAL_DIR / test_id

    if not ref.exists():
        return {"test_id": test_id, "status": "NO_REF",
                "note": "Aucune référence définie pour ce test."}
    if not real.exists():
        return {"test_id": test_id, "status": "NO_REAL",
                "note": "Pas de sortie réelle (run_tests.py pas exécuté ?)"}

    ref_tree  = list_tree(ref)
    real_tree = list_tree(real)
    missing = sorted(set(ref_tree) - set(real_tree))
    extra   = sorted(set(real_tree) - set(ref_tree))
    common  = sorted(set(ref_tree) & set(real_tree))

    # Comparer les fichiers communs
    diffs = []
    for rel in common:
        ref_path = ref / rel
        real_path = real / rel
        if ref_path.suffix.lower() in (".csv", ".json", ".txt", ".md"):
            # Diff textuel léger : nb lignes
            try:
                ref_lines = ref_path.read_text(encoding="utf-8").splitlines()
                real_lines = real_path.read_text(encoding="utf-8").splitlines()
                if ref_lines != real_lines:
                    diffs.append(f"{rel} : contenu texte différent (ref {len(ref_lines)}l, réel {len(real_lines)}l)")
            except Exception as exc:
                diffs.append(f"{rel} : lecture impossible ({exc})")
        else:
            # Binaire : hash partiel
            try:
                if quick_hash(ref_path) != quick_hash(real_path):
                    diffs.append(f"{rel} : hash partiel différent (ref {ref_tree[rel]} B, réel {real_tree[rel]} B)")
            except Exception as exc:
                diffs.append(f"{rel} : hash impossible ({exc})")

    status = "OK" if not missing and not extra and not diffs else "DIFF"
    return {
        "test_id": test_id,
        "status":  status,
        "missing": missing,
        "extra":   extra,
        "diffs":   diffs,
        "ref_count":  len(ref_tree),
        "real_count": len(real_tree),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Filtrer sur un ID test")
    args = parser.parse_args()

    # Liste des tests = sous-dossiers de outputs_reference/
    test_ids = sorted([p.name for p in REF_DIR.iterdir() if p.is_dir()] if REF_DIR.exists() else [])
    if args.only:
        test_ids = [t for t in test_ids if t == args.only]

    if not test_ids:
        print(f"Aucune référence dans {REF_DIR}. Voir le README pour générer.")
        return

    print(f"=== Comparaison de {len(test_ids)} test(s) ===\n")
    results = []
    for tid in test_ids:
        r = compare_one(tid)
        results.append(r)
        status_icon = {"OK": "✅", "DIFF": "❌", "NO_REF": "⚠️", "NO_REAL": "⚠️"}.get(r["status"], "?")
        print(f"  {status_icon}  {tid}  {r['status']}")
        if r.get("missing"):
            print(f"      Manquants : {', '.join(r['missing'][:3])}{'…' if len(r['missing']) > 3 else ''}")
        if r.get("extra"):
            print(f"      En trop   : {', '.join(r['extra'][:3])}{'…' if len(r['extra']) > 3 else ''}")
        if r.get("diffs"):
            for d in r["diffs"][:3]:
                print(f"      Diff      : {d}")

    # Écriture du rapport Markdown
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REAL_DIR / "_diff_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Diff réel vs référence\n\n")
        f.write(f"Tests comparés : {len(results)}\n\n")
        f.write("| ID | Statut | Manquants | En trop | Diffs |\n|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| {r['test_id']} | {r['status']} | "
                    f"{len(r.get('missing', []))} | {len(r.get('extra', []))} | "
                    f"{len(r.get('diffs', []))} |\n")
        f.write("\n## Détails par test\n\n")
        for r in results:
            f.write(f"### {r['test_id']} — {r['status']}\n\n")
            if r.get("missing"):
                f.write(f"**Manquants** ({len(r['missing'])}) :\n")
                for m in r["missing"]:
                    f.write(f"- {m}\n")
            if r.get("extra"):
                f.write(f"\n**En trop** ({len(r['extra'])}) :\n")
                for e in r["extra"]:
                    f.write(f"- {e}\n")
            if r.get("diffs"):
                f.write(f"\n**Différences** ({len(r['diffs'])}) :\n")
                for d in r["diffs"]:
                    f.write(f"- {d}\n")
            f.write("\n")

    print(f"\n=== Rapport écrit dans {report_path} ===")
    ok = sum(1 for r in results if r["status"] == "OK")
    diff = sum(1 for r in results if r["status"] == "DIFF")
    print(f"OK : {ok} / DIFF : {diff} / Autre : {len(results) - ok - diff}")


if __name__ == "__main__":
    main()
