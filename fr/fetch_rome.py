"""
Fetch all ROME 4.0 fiches métiers from France Travail open data.

Downloads the complete ROME dataset (ZIP containing JSON files) from:
  https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html

No API key or OAuth required — this is open data under licence ouverte.

Usage:
    python fr/fetch_rome.py
    python fr/fetch_rome.py --force
"""

import argparse
import io
import json
import os
import zipfile

import httpx

OPEN_DATA_URL = "https://api.francetravail.fr/api-nomenclatureemploi/v1/open-data/json"

RAW_DIR = "fr/data/rome_raw"
OUTPUT_FICHES = "fr/data/fiches_detail.json"


def download_and_extract(force=False):
    if os.path.isdir(RAW_DIR) and os.listdir(RAW_DIR) and not force:
        print(f"Raw data already cached in {RAW_DIR}/ (use --force to re-download)")
        return

    print(f"Downloading ROME open data from {OPEN_DATA_URL} ...")
    response = httpx.get(OPEN_DATA_URL, follow_redirects=True, timeout=120)
    response.raise_for_status()
    print(f"  Downloaded {len(response.content):,} bytes")

    os.makedirs(RAW_DIR, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(RAW_DIR)
        print(f"  Extracted {len(zf.namelist())} files to {RAW_DIR}/")


def find_fiches_file():
    for name in os.listdir(RAW_DIR):
        if "fiche_emploi_metier" in name and name.endswith(".json"):
            return os.path.join(RAW_DIR, name)
    raise FileNotFoundError("No fiche_emploi_metier JSON found in extracted data")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    os.makedirs("fr/data", exist_ok=True)

    if os.path.exists(OUTPUT_FICHES) and not args.force:
        with open(OUTPUT_FICHES, encoding="utf-8") as f:
            fiches = json.load(f)
        print(f"Already have {len(fiches)} fiches in {OUTPUT_FICHES} (use --force)")
        return

    download_and_extract(args.force)

    raw_path = find_fiches_file()
    print(f"Reading {raw_path} ...")
    with open(raw_path, encoding="latin-1") as f:
        fiches = json.load(f)
    print(f"  Loaded {len(fiches)} fiches métier")

    with open(OUTPUT_FICHES, "w", encoding="utf-8") as f:
        json.dump(fiches, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {OUTPUT_FICHES} ({len(fiches)} fiches)")


if __name__ == "__main__":
    main()
