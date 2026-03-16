"""
Build a compact JSON for the French website by merging CSV stats with AI exposure scores.

Reads occupations_fr.csv (for stats) and scores.json (for AI exposure).
Writes fr/site/data.json.

Usage:
    uv run python fr/build_site_data_fr.py
"""

import csv
import json
import os


def main():
    # Load AI exposure scores
    scores_path = "fr/data/scores.json"
    if os.path.exists(scores_path):
        with open(scores_path, encoding="utf-8") as f:
            scores = {s["slug"]: s for s in json.load(f)}
    else:
        scores = {}
        print("Warning: scores.json not found, site data will have no exposure scores")

    # Load CSV stats
    csv_path = "fr/data/occupations_fr.csv"
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        # Fall back to occupations.json
        with open("fr/data/occupations.json", encoding="utf-8") as f:
            occupations = json.load(f)
        rows = [{"slug": o["slug"], "title": o["title"], "code_rome": o["code_rome"]} for o in occupations]

    # Merge
    data = []
    for row in rows:
        slug = row["slug"]
        score = scores.get(slug, {})

        salary = None
        if row.get("salary_median"):
            try:
                val = int(row["salary_median"])
                if 10000 <= val <= 300000:
                    salary = val
            except (ValueError, TypeError):
                pass

        nb_offres = None
        if row.get("nb_offres"):
            try:
                nb_offres = int(row["nb_offres"])
            except (ValueError, TypeError):
                pass

        projets_recrutement = None
        if row.get("projets_recrutement"):
            try:
                projets_recrutement = int(row["projets_recrutement"])
            except (ValueError, TypeError):
                pass

        taux_difficulte = None
        if row.get("taux_difficulte"):
            try:
                taux_difficulte = float(row["taux_difficulte"])
            except (ValueError, TypeError):
                pass

        salary_min = None
        if row.get("salary_min"):
            try:
                val = int(row["salary_min"])
                if 10000 <= val <= 300000:
                    salary_min = val
            except (ValueError, TypeError):
                pass

        salary_max = None
        if row.get("salary_max"):
            try:
                val = int(row["salary_max"])
                if 10000 <= val <= 300000:
                    salary_max = val
            except (ValueError, TypeError):
                pass

        taux_saisonnier = None
        if row.get("taux_saisonnier"):
            try:
                taux_saisonnier = float(row["taux_saisonnier"])
            except (ValueError, TypeError):
                pass

        projets_difficiles = None
        if row.get("projets_difficiles"):
            try:
                projets_difficiles = int(row["projets_difficiles"])
            except (ValueError, TypeError):
                pass

        nb_competences_base = None
        if row.get("nb_competences_base"):
            try:
                nb_competences_base = int(row["nb_competences_base"])
            except (ValueError, TypeError):
                pass

        nb_competences_specifiques = None
        if row.get("nb_competences_specifiques"):
            try:
                nb_competences_specifiques = int(row["nb_competences_specifiques"])
            except (ValueError, TypeError):
                pass

        nb_appellations = None
        if row.get("nb_appellations"):
            try:
                nb_appellations = int(row["nb_appellations"])
            except (ValueError, TypeError):
                pass

        data.append({
            "title": row["title"],
            "slug": slug,
            "code_rome": row.get("code_rome", ""),
            "salary_min": salary_min,
            "salary": salary,
            "salary_max": salary_max,
            "nb_offres": nb_offres,
            "projets_recrutement": projets_recrutement,
            "projets_difficiles": projets_difficiles,
            "taux_difficulte": taux_difficulte,
            "taux_saisonnier": taux_saisonnier,
            "nb_competences_base": nb_competences_base,
            "nb_competences_specifiques": nb_competences_specifiques,
            "nb_appellations": nb_appellations,
            "exposure": score.get("exposure"),
            "exposure_rationale": score.get("rationale"),
        })

    os.makedirs("fr/site", exist_ok=True)
    with open("fr/site/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Wrote {len(data)} métiers to fr/site/data.json")
    total_offres = sum(d["nb_offres"] or 0 for d in data)
    total_bmo = sum(d["projets_recrutement"] or 0 for d in data)
    scored = sum(1 for d in data if d["exposure"] is not None)
    print(f"Total offres: {total_offres:,}")
    print(f"Total projets BMO: {total_bmo:,}")
    print(f"Scored: {scored}/{len(data)}")


if __name__ == "__main__":
    main()
