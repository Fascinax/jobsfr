"""
Fetch labor market data from France Travail APIs and open data sources.

Enriches occupation data with:
- BMO (Besoins en Main-d'Œuvre) recruitment data
- Salary estimates from France Travail / INSEE
- Tension indicators (supply/demand)
- Number of job seekers and offers per ROME code

Requires France Travail API credentials in .env.

Usage:
    uv run python fr/fetch_market_data.py
    uv run python fr/fetch_market_data.py --force
"""

import argparse
import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
OFFRES_API = "https://api.francetravail.io/partenaire/offresdemploi/v2"
BMO_PER_ROME = "fr/data/bmo_per_rome.json"
TOKEN_TIMEOUT_SECONDS = 60
TOKEN_RETRY_ATTEMPTS = 3

OUTPUT_MARKET = "fr/data/market_data.json"


def get_access_token(client, scope="api_offresdemploiv2 o2dsoffre"):
    """Get OAuth2 access token from France Travail API."""
    client_id = os.environ["FRANCE_TRAVAIL_CLIENT_ID"]
    client_secret = os.environ["FRANCE_TRAVAIL_CLIENT_SECRET"]

    for attempt in range(1, TOKEN_RETRY_ATTEMPTS + 1):
        try:
            response = client.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                },
                timeout=TOKEN_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["access_token"]
        except httpx.TimeoutException:
            if attempt == TOKEN_RETRY_ATTEMPTS:
                raise
            print(f"Token request timed out (attempt {attempt}/{TOKEN_RETRY_ATTEMPTS}), retrying...")
            time.sleep(attempt)


def fetch_offres_stats(client, token, code_rome):
    """Fetch job offer statistics for a ROME code."""
    response = client.get(
        f"{OFFRES_API}/offres/search",
        params={
            "codeROME": code_rome,
            "range": "0-0",  # We only need the Content-Range header for count
        },
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    if response.status_code == 206 or response.status_code == 200:
        content_range = response.headers.get("Content-Range", "")
        # Format: "offres 0-0/1234"
        if "/" in content_range:
            total = content_range.split("/")[-1]
            try:
                return int(total)
            except ValueError:
                pass
    return 0


def _parse_salary_annual(libelle):
    """
    Parse salary from France Travail libelle and return annual amounts.
    Formats: "Mensuel de 1895.0 Euros à 1900.0 Euros sur 12.0 mois"
             "Annuel de 26000.0 Euros à 26400.0 Euros sur 12.0 mois"
             "Horaire de 13.0 Euros à 14.0 Euros sur 12.0 mois"
    """
    import re
    if not libelle:
        return []

    amounts = [float(x) for x in re.findall(r"(\d+\.?\d*)\s*Euros", libelle)]
    if not amounts:
        return []

    low = libelle.lower()
    if low.startswith("annuel"):
        return [int(a) for a in amounts]
    if low.startswith("mensuel"):
        return [int(a * 12) for a in amounts]
    if low.startswith("horaire"):
        return [int(a * 1820) for a in amounts]  # 35h * 52 weeks
    return []


def fetch_salary_data(client, token, code_rome):
    """
    Get salary range from job offers for this ROME code.
    Samples up to 50 offers to compute min/median/max annual salary.
    """
    response = client.get(
        f"{OFFRES_API}/offres/search",
        params={
            "codeROME": code_rome,
            "range": "0-49",
        },
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )

    salaries = []
    if response.status_code in (200, 206):
        data = response.json()
        results = data if isinstance(data, list) else data.get("resultats", [])
        for offre in results:
            salaire = offre.get("salaire", {})
            libelle = salaire.get("libelle", "")
            parsed = _parse_salary_annual(libelle)
            if not parsed:
                complement = salaire.get("complement1", "")
                parsed = _parse_salary_annual(complement)
            salaries.extend(parsed)

    if salaries:
        salaries = [s for s in salaries if 10000 <= s <= 300000]
    if salaries:
        salaries.sort()
        mid = len(salaries) // 2
        return {
            "salary_min": salaries[0],
            "salary_median": salaries[mid],
            "salary_max": salaries[-1],
            "salary_sample_size": len(salaries),
        }
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    occupations_path = "fr/data/occupations.json"
    if not os.path.exists(occupations_path):
        print(f"Error: {occupations_path} not found. Run parse_rome.py first.")
        return

    with open(occupations_path, encoding="utf-8") as f:
        occupations = json.load(f)

    # Load existing market data
    market = {}
    if os.path.exists(OUTPUT_MARKET) and not args.force:
        with open(OUTPUT_MARKET, encoding="utf-8") as f:
            for entry in json.load(f):
                market[entry["code_rome"]] = entry
        print(f"Loaded {len(market)} entries from cache")

    client = httpx.Client()
    token = get_access_token(client)
    print('Got access token')

    subset = occupations[args.start:args.end]
    print(f"Fetching market data for {len(subset)} métiers")

    errors = []
    for i, occ in enumerate(subset):
        code = occ["code_rome"]

        if code in market and not args.force:
            continue

        print(f"  [{i+1}/{len(subset)}] {code} - {occ['title']}...", end=" ", flush=True)

        try:
            nb_offres = fetch_offres_stats(client, token, code)
            salary = fetch_salary_data(client, token, code)

            market[code] = {
                "code_rome": code,
                "title": occ["title"],
                "slug": occ["slug"],
                "nb_offres": nb_offres,
                **salary,
            }
            print(f"OK ({nb_offres} offres)")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("Token expired, refreshing...")
                token = get_access_token(client)
                try:
                    nb_offres = fetch_offres_stats(client, token, code)
                    salary = fetch_salary_data(client, token, code)
                    market[code] = {
                        "code_rome": code,
                        "title": occ["title"],
                        "slug": occ["slug"],
                        "nb_offres": nb_offres,
                        **salary,
                    }
                    print(f"OK (retry, {nb_offres} offres)")
                except Exception as e2:
                    print(f"ERROR: {e2}")
                    errors.append(code)
            else:
                print(f"ERROR: {e}")
                errors.append(code)
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append(code)

        # Incremental save
        with open(OUTPUT_MARKET, "w", encoding="utf-8") as f:
            json.dump(list(market.values()), f, ensure_ascii=False, indent=2)

        if i < len(subset) - 1:
            time.sleep(args.delay)

    client.close()

    # Merge BMO data if available
    if os.path.exists(BMO_PER_ROME):
        with open(BMO_PER_ROME, encoding="utf-8") as f:
            bmo_data = json.load(f)
        bmo_merged = 0
        for code, entry in market.items():
            if code in bmo_data:
                bmo = bmo_data[code]
                entry["projets_recrutement"] = bmo["projets_recrutement"]
                entry["projets_difficiles"] = bmo["projets_difficiles"]
                entry["projets_saisonniers"] = bmo["projets_saisonniers"]
                entry["taux_difficulte"] = bmo["taux_difficulte"]
                entry["taux_saisonnier"] = bmo["taux_saisonnier"]
                bmo_merged += 1
        print(f"BMO data merged for {bmo_merged}/{len(market)} codes")
    else:
        print(f"No BMO data found at {BMO_PER_ROME}. Run fetch_bmo.py first.")

    # Final save
    with open(OUTPUT_MARKET, "w", encoding="utf-8") as f:
        json.dump(list(market.values()), f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(market)} entries, {len(errors)} errors.")

    # Quick stats
    total_offres = sum(m.get("nb_offres", 0) for m in market.values())
    with_salary = sum(1 for m in market.values() if m.get("salary_median"))
    print(f"Total offres across all codes: {total_offres:,}")
    print(f"Métiers with salary data: {with_salary}/{len(market)}")


if __name__ == "__main__":
    main()
