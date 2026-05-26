# -*- coding: utf-8 -*-
"""Exécute les scénarios d'organisation sur les inputs et dépose les sorties
dans ``test_data/outputs_reels/``.

Chaque scénario correspond à un (ou plusieurs) tests de la matrice et utilise
l'API Python directement (pas l'EXE) pour rapidité et reproductibilité.

Usage :
    python test_data/scripts/run_tests.py              # tous les scénarios
    python test_data/scripts/run_tests.py --only T-051 # un test précis
    python test_data/scripts/run_tests.py --list       # liste sans exécution
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

# Force UTF-8 stdout (Git Bash sous Windows = cp1252 par défaut)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

# Path setup
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

INPUTS_DIR  = ROOT / "test_data" / "inputs"
OUTPUTS_DIR = ROOT / "test_data" / "outputs_reels"


# -----------------------------------------------------------------------------
# Définition des scénarios
# -----------------------------------------------------------------------------
SCENARIOS = [
    # ID test         input                              options
    ("T-051", "input_nominal",            dict(organize_by_date=True, date_format="year/month/day")),
    ("T-052", "input_vide",               dict(organize_by_date=True)),
    ("T-053", "input_volumineux",         dict(organize_by_date=True, date_format="year")),
    ("T-055", "input_caracteres_speciaux",dict(organize_by_date=True)),
    ("T-056", "input_corrompu",           dict(organize_by_date=True)),
    ("T-057", "input_gps_piexif",         dict(organize_by_date=False, organize_by_location=True, use_geocoding=False, validate_disk_space=False)),
    ("T-058", "input_pairs",              dict(organize_by_date=True, date_format="year", keep_raw_jpeg_pairs=True)),
    ("T-059", "input_bursts",             dict(organize_by_date=True, date_format="year", detect_bursts=True, burst_threshold_seconds=3, burst_min_count=3)),
    ("T-060", "input_pas_exif",           dict(organize_by_date=True)),
    ("T-066", "input_nominal",            dict(organize_by_date=True, date_format="year/month/day")),
    ("T-068", "input_nominal",            dict(organize_by_date=True, organize_by_camera=True, multilayer=True, criteria_order=["date","camera","location"])),
    ("T-069", "input_nominal",            dict(organize_by_date=True, date_format="year", export_index_csv=True)),
    ("T-070", "input_nominal",            dict(organize_by_date=True, date_format="year", export_index_json=True)),
    ("T-074", "input_nominal",            dict(organize_by_date=True, date_format="year", rename_template="{date:%Y%m%d}_{counter:04d}")),
    ("T-076", "input_bursts",             dict(organize_by_date=True, date_format="year", detect_bursts=True)),
    ("T-079", "input_pas_exif",           dict(organize_by_date=True)),
]


def run_one(test_id: str, input_name: str, options_dict: dict, verbose: bool = True) -> dict:
    """Exécute un scénario et retourne un dict résumé."""
    from core.operations import FileManager, OrganizationOptions, SmartOrganizer

    input_dir  = INPUTS_DIR / input_name
    output_dir = OUTPUTS_DIR / test_id

    # Reset output dir
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # List files
    fm = FileManager()
    files = fm.list_files(
        str(input_dir),
        recursive=True,
        include_images=True,
        include_raw=True,
        include_videos=False,
    )

    # Build options
    full_options = dict(
        organize_by_date=False,
        organize_by_camera=False,
        organize_by_location=False,
        copy_not_move=True,           # toujours COPY en tests pour préserver inputs
        validate_disk_space=False,    # désactivé en tests (cache pleins fréquents)
    )
    full_options.update(options_dict)
    options = OrganizationOptions(**full_options)

    organizer = SmartOrganizer()
    t0 = time.time()
    result = organizer.organize(files, str(output_dir), options)
    elapsed = time.time() - t0

    summary = {
        "test_id":   test_id,
        "input":     input_name,
        "files_in":  len(files),
        "processed": result.processed,
        "skipped":   result.skipped,
        "errors":    result.errors,
        "elapsed_s": round(elapsed, 2),
        "output":    str(output_dir),
    }
    if verbose:
        print(f"  {test_id:8s} {input_name:32s} → {result.processed}/{len(files)} ok, "
              f"{result.skipped} skip, {result.errors} err, {elapsed:.2f}s")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Filtrer sur un ID test (ex. T-051)")
    parser.add_argument("--list", action="store_true", help="Liste les scénarios sans exécution")
    args = parser.parse_args()

    if args.list:
        print(f"{len(SCENARIOS)} scénarios définis :")
        for tid, inp, _ in SCENARIOS:
            print(f"  {tid:8s} → {inp}")
        return

    selected = [(tid, inp, opt) for tid, inp, opt in SCENARIOS
                if not args.only or tid == args.only]
    if not selected:
        print(f"Aucun scénario ne matche '{args.only}'")
        return

    print(f"=== Exécution de {len(selected)} scénarios ===")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    summaries = []
    for tid, inp, opts in selected:
        try:
            s = run_one(tid, inp, opts)
            summaries.append(s)
        except Exception as exc:
            print(f"  {tid} : ERREUR {exc}")
            summaries.append({"test_id": tid, "input": inp, "error": str(exc)})

    # Écrire le récap JSON
    report_path = OUTPUTS_DIR / "_run_summary.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)
    print(f"\n=== Résumé écrit dans {report_path} ===")


if __name__ == "__main__":
    main()
