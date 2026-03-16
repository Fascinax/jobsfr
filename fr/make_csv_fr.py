"""
Build a CSV summary of all French occupations from ROME and market data.

Merges occupations.json, fiches_detail.json, and market_data.json into a
unified CSV similar to the US occupations.csv.

Usage:
    uv run python fr/make_csv_fr.py
"""

import csv
import json
import os


OUTPUT_CSV = "fr/data/occupations_fr.csv"


def count_base_competences(fiche):
    competences = fiche.get("competences", {})
    savoir_faire = competences.get("savoir_faire", {}).get("enjeux", [])
    return sum(len(enjeu.get("items", [])) for enjeu in savoir_faire)


def count_specific_competences(fiche):
    competences = fiche.get("competences", {})
    savoirs = competences.get("savoirs", {}).get("categories", [])
    return sum(len(categorie.get("items", [])) for categorie in savoirs)


def main():
    with open("fr/data/occupations.json", encoding="utf-8") as f:
        occupations = json.load(f)

    # Load market data if available
    market = {}
    market_path = "fr/data/market_data.json"
    if os.path.exists(market_path):
        with open(market_path, encoding="utf-8") as f:
            for entry in json.load(f):
                market[entry["code_rome"]] = entry

    # Load fiches for additional metadata
    fiches = {}
    fiches_path = "fr/data/fiches_detail.json"
    if os.path.exists(fiches_path):
        with open(fiches_path, encoding="utf-8") as f:
            for fiche in json.load(f):
                rome = fiche.get("rome", {})
                code = rome.get("code_rome", fiche.get("code", fiche.get("codeRome", "")))
                if code:
                    fiches[code] = fiche

    fieldnames = [
        "title",
        "code_rome",
        "slug",
        "nb_offres",
        "projets_recrutement",
        "projets_difficiles",
        "projets_saisonniers",
        "taux_difficulte",
        "taux_saisonnier",
        "salary_min",
        "salary_median",
        "salary_max",
        "nb_competences_base",
        "nb_competences_specifiques",
        "nb_appellations",
    ]

    rows = []
    for occ in occupations:
        code = occ["code_rome"]
        mkt = market.get(code, {})
        fiche = fiches.get(code, {})

        appellations = fiche.get("appellations", [])

        rows.append({
            "title": occ["title"],
            "code_rome": code,
            "slug": occ["slug"],
            "nb_offres": mkt.get("nb_offres", ""),
            "projets_recrutement": mkt.get("projets_recrutement", ""),
            "projets_difficiles": mkt.get("projets_difficiles", ""),
            "projets_saisonniers": mkt.get("projets_saisonniers", ""),
            "taux_difficulte": mkt.get("taux_difficulte", ""),
            "taux_saisonnier": mkt.get("taux_saisonnier", ""),
            "salary_min": mkt.get("salary_min", ""),
            "salary_median": mkt.get("salary_median", ""),
            "salary_max": mkt.get("salary_max", ""),
            "nb_competences_base": count_base_competences(fiche),
            "nb_competences_specifiques": count_specific_competences(fiche),
            "nb_appellations": len(appellations),
        })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")

    # Quick stats
    with_offres = sum(1 for r in rows if r["nb_offres"])
    with_bmo = sum(1 for r in rows if r["projets_recrutement"])
    with_salary = sum(1 for r in rows if r["salary_median"])
    print(f"  With job offers data: {with_offres}/{len(rows)}")
    print(f"  With BMO data: {with_bmo}/{len(rows)}")
    print(f"  With salary data: {with_salary}/{len(rows)}")

    if rows[:3]:
        print("\nSample rows:")
        for r in rows[:3]:
            salary = f"€{r['salary_median']}" if r["salary_median"] else "N/A"
            print(f"  {r['title']} ({r['code_rome']}): {salary}, {r['nb_offres'] or 0} offres")


if __name__ == "__main__":
    main()
