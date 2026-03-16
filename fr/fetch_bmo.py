"""
Download and process BMO (Besoins en Main-d'Oeuvre) open data.

Produces per-ROME recruitment projections by:
1. Downloading BMO 2025 Excel from France Travail open data
2. Downloading FAP→ROME correspondence CSV from France-Travail/mobiville
3. Aggregating BMO nationally and distributing to ROME codes

Output: fr/data/bmo_per_rome.json

Usage:
    python fr/fetch_bmo.py
    python fr/fetch_bmo.py --force
"""

import argparse
import json
import math
import os
import re

import httpx
import openpyxl

BMO_EXCEL_URL = "https://www.francetravail.org/files/live/sites/peorg/files/documents/Statistiques-et-analyses/Open-data/BMO/Base_open_data_BMO_2025.xlsx"
FAP_ROME_CSV_URL = "https://raw.githubusercontent.com/France-Travail/mobiville/master/api/src/assets/datas/table-correspondance-pcs-rome.csv"

BMO_EXCEL_PATH = "fr/data/bmo/BMO_2025.xlsx"
FAP_ROME_CSV_PATH = "fr/data/bmo/table-correspondance-pcs-rome.csv"
OUTPUT_PATH = "fr/data/bmo_per_rome.json"


def download_if_missing(url, path, force=False):
    if os.path.exists(path) and not force:
        print(f"  {path} already exists, skipping download")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = httpx.get(url, follow_redirects=True, timeout=60)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    print(f"  Downloaded {path} ({len(r.content):,} bytes)")


def parse_fap_rome_csv(path):
    """Parse FAP→PCS→ROME correspondence CSV into {fap_code: set(rome_codes)}."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().strip().split("\n")

    fap_to_rome = {}
    current_fap = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith('"') or line.startswith(" "):
            continue
        parts = line.split(";")
        if len(parts) < 3:
            continue

        fap = parts[0].strip()
        rome = parts[2].strip() if len(parts) > 2 else ""

        if fap and re.match(r"^[A-Z]\d[A-Z]\d\d$", fap):
            current_fap = fap
            if current_fap not in fap_to_rome:
                fap_to_rome[current_fap] = set()
            if rome and re.match(r"^[A-Z]\d{4}$", rome):
                fap_to_rome[current_fap].add(rome)
        elif current_fap and rome and re.match(r"^[A-Z]\d{4}$", rome):
            fap_to_rome[current_fap].add(rome)

    return fap_to_rome


def aggregate_bmo_nationally(path):
    """Read BMO Excel, aggregate met/xmet/smet nationally per BMO code."""
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["BMO_2025_open_data"]
    bmo = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        code_fap = row[1]
        nom = row[2]
        met_s, xmet_s, smet_s = row[11], row[12], row[13]
        if code_fap not in bmo:
            bmo[code_fap] = {"nom": nom, "met": 0, "xmet": 0, "smet": 0}
        for key, val in [("met", met_s), ("xmet", xmet_s), ("smet", smet_s)]:
            if val and val != "*":
                try:
                    bmo[code_fap][key] += int(val)
                except (ValueError, TypeError):
                    pass
    wb.close()
    return bmo


def build_bmo_to_rome(fap_to_rome, bmo_codes):
    """Map BMO codes to ROME codes using FAP correspondence.

    Returns: {bmo_code: set(rome_codes)}, list of unmatched codes
    """
    sous_domaine_to_rome = {}
    for fap, romes in fap_to_rome.items():
        sd = fap[:2]
        if sd not in sous_domaine_to_rome:
            sous_domaine_to_rome[sd] = set()
        sous_domaine_to_rome[sd].update(romes)

    bmo_to_rome = {}
    unmatched = []

    for bmo in bmo_codes:
        matched = set()
        fap_z = bmo.replace("X", "Z")
        if fap_z in fap_to_rome:
            matched = set(fap_to_rome[fap_z])
        else:
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                candidate = bmo[0:2] + letter + bmo[3:]
                if candidate in fap_to_rome:
                    matched.update(fap_to_rome[candidate])
            if not matched:
                sd = bmo[:2]
                if sd in sous_domaine_to_rome:
                    matched = set(sous_domaine_to_rome[sd])

        if matched:
            bmo_to_rome[bmo] = matched
        else:
            unmatched.append(bmo)

    return bmo_to_rome, unmatched


def distribute_bmo_to_rome(bmo_national, bmo_to_rome):
    """Distribute BMO values across ROME codes proportionally.

    Each BMO family's values are divided equally among its mapped ROME codes.
    When a ROME code appears in multiple BMO families, contributions are summed.
    """
    rome_bmo = {}

    for bmo_code, data in bmo_national.items():
        if bmo_code not in bmo_to_rome:
            continue
        rome_codes = bmo_to_rome[bmo_code]
        n = len(rome_codes)
        if n == 0:
            continue

        share_met = data["met"] / n
        share_xmet = data["xmet"] / n
        share_smet = data["smet"] / n

        for rome in rome_codes:
            if rome not in rome_bmo:
                rome_bmo[rome] = {
                    "projets_recrutement": 0.0,
                    "projets_difficiles": 0.0,
                    "projets_saisonniers": 0.0,
                    "source_bmo_codes": [],
                }
            rome_bmo[rome]["projets_recrutement"] += share_met
            rome_bmo[rome]["projets_difficiles"] += share_xmet
            rome_bmo[rome]["projets_saisonniers"] += share_smet
            rome_bmo[rome]["source_bmo_codes"].append(bmo_code)

    for rome, data in rome_bmo.items():
        data["projets_recrutement"] = round(data["projets_recrutement"])
        data["projets_difficiles"] = round(data["projets_difficiles"])
        data["projets_saisonniers"] = round(data["projets_saisonniers"])
        met = data["projets_recrutement"]
        data["taux_difficulte"] = (
            round(data["projets_difficiles"] / met * 100, 1) if met > 0 else 0
        )
        data["taux_saisonnier"] = (
            round(data["projets_saisonniers"] / met * 100, 1) if met > 0 else 0
        )

    return rome_bmo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if os.path.exists(OUTPUT_PATH) and not args.force:
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        print(f"BMO data already exists: {len(data)} ROME codes. Use --force to refresh.")
        return

    print("Step 1: Download source files")
    download_if_missing(BMO_EXCEL_URL, BMO_EXCEL_PATH, args.force)
    download_if_missing(FAP_ROME_CSV_URL, FAP_ROME_CSV_PATH, args.force)

    print("Step 2: Parse FAP→ROME correspondence")
    fap_to_rome = parse_fap_rome_csv(FAP_ROME_CSV_PATH)
    print(f"  {len(fap_to_rome)} FAP detailed codes -> {sum(len(v) for v in fap_to_rome.values())} ROME mappings")

    print("Step 3: Aggregate BMO nationally")
    bmo_national = aggregate_bmo_nationally(BMO_EXCEL_PATH)
    print(f"  {len(bmo_national)} BMO codes, {sum(b['met'] for b in bmo_national.values()):,} total recruitment projects")

    print("Step 4: Map BMO codes to ROME")
    bmo_to_rome, unmatched = build_bmo_to_rome(fap_to_rome, set(bmo_national.keys()))
    print(f"  Matched: {len(bmo_to_rome)}/{len(bmo_national)}, unmatched: {len(unmatched)}")

    print("Step 5: Distribute BMO to ROME codes")
    rome_bmo = distribute_bmo_to_rome(bmo_national, bmo_to_rome)
    print(f"  {len(rome_bmo)} ROME codes with BMO data")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rome_bmo, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")

    top = sorted(rome_bmo.items(), key=lambda x: -x[1]["projets_recrutement"])[:10]
    print("\nTop 10 ROME codes by recruitment projects:")
    for rome, data in top:
        print(f"  {rome}: {data['projets_recrutement']:,} projets ({data['taux_difficulte']}% difficiles)")


if __name__ == "__main__":
    main()
