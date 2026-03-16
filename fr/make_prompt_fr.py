"""
Generate prompt_fr.md — a single file containing all French project data,
designed to be copy-pasted into an LLM for analysis.

Equivalent of make_prompt.py for the French adaptation.

Usage:
    uv run python fr/make_prompt_fr.py
"""

import csv
import json
import os


def fmt_salary(salary):
    if salary is None:
        return "?"
    return f"{salary:,} €".replace(",", " ")


def fmt_offres(n):
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 1_000:
        return f"{n / 1e3:.0f}K"
    return str(n)


def main():
    with open("fr/data/occupations.json", encoding="utf-8") as f:
        occupations = json.load(f)

    # Load CSV if available
    csv_rows = {}
    csv_path = "fr/data/occupations_fr.csv"
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as f:
            csv_rows = {row["slug"]: row for row in csv.DictReader(f)}

    # Load scores
    scores = {}
    scores_path = "fr/data/scores.json"
    if os.path.exists(scores_path):
        with open(scores_path, encoding="utf-8") as f:
            scores = {s["slug"]: s for s in json.load(f)}

    # Merge
    records = []
    for occ in occupations:
        slug = occ["slug"]
        row = csv_rows.get(slug, {})
        score = scores.get(slug, {})
        salary = int(row["salary_median"]) if row.get("salary_median") else None
        nb_offres = int(row["nb_offres"]) if row.get("nb_offres") else None
        projets_recrutement = int(row["projets_recrutement"]) if row.get("projets_recrutement") else None
        taux_difficulte = float(row["taux_difficulte"]) if row.get("taux_difficulte") else None
        records.append({
            "title": occ["title"],
            "slug": slug,
            "code_rome": occ.get("code_rome", row.get("code_rome", "")),
            "salary": salary,
            "nb_offres": nb_offres,
            "projets_recrutement": projets_recrutement,
            "taux_difficulte": taux_difficulte,
            "exposure": score.get("exposure"),
            "rationale": score.get("rationale", ""),
        })

    records.sort(key=lambda r: (-(r["exposure"] or 0), -(r["nb_offres"] or 0)))

    lines = []

    lines.append("# Exposition des Métiers Français à l'IA")
    lines.append("")
    lines.append("Ce document contient les données structurées sur les métiers français issus du référentiel ROME 4.0 de France Travail, chacun évalué pour son exposition à l'IA sur une échelle de 0 à 10 par un LLM.")
    lines.append("")
    lines.append("Inspiré par : https://karpathy.ai/jobs/")
    lines.append("Source des données : ROME 4.0 open data + API Offres d'emploi + BMO 2025")
    lines.append("")

    # Methodology
    lines.append("## Méthodologie de scoring")
    lines.append("")
    lines.append("Chaque métier est évalué sur un axe unique d'Exposition à l'IA de 0 à 10, mesurant dans quelle mesure l'IA va transformer ce métier. Le score prend en compte l'automatisation directe et les effets indirects sur la productivité.")
    lines.append("")
    lines.append("Heuristique clé : si le métier peut s'exercer entièrement depuis un bureau à domicile sur un ordinateur, l'exposition est intrinsèquement élevée (7+).")
    lines.append("")
    lines.append("Ancres de calibration :")
    lines.append("- 0-1 Minimal : couvreurs, maçons, paysagistes")
    lines.append("- 2-3 Faible : électriciens, plombiers, pompiers, aides-soignants")
    lines.append("- 4-5 Modéré : infirmiers, policiers, vétérinaires, techniciens")
    lines.append("- 6-7 Élevé : enseignants, cadres, comptables, journalistes")
    lines.append("- 8-9 Très élevé : développeurs, graphistes, traducteurs, analystes")
    lines.append("- 10 Maximum : opérateurs de saisie, télévendeurs")
    lines.append("")

    # Aggregate stats
    scored_records = [r for r in records if r["exposure"] is not None]
    lines.append("## Statistiques agrégées")
    lines.append("")
    lines.append(f"- Total métiers : {len(records)}")
    lines.append(f"- Métiers scorés : {len(scored_records)}")

    total_offres = sum(r["nb_offres"] or 0 for r in records)
    total_bmo = sum(r["projets_recrutement"] or 0 for r in records)
    lines.append(f"- Total offres référencées : {total_offres:,}")
    lines.append(f"- Total projets de recrutement BMO : {total_bmo:,}")

    if scored_records:
        avg = sum(r["exposure"] for r in scored_records) / len(scored_records)
        lines.append(f"- Exposition moyenne à l'IA : {avg:.1f}/10")
    lines.append("")

    # Tier breakdown
    tiers = [
        ("Minimal (0-1)", 0, 1),
        ("Faible (2-3)", 2, 3),
        ("Modéré (4-5)", 4, 5),
        ("Élevé (6-7)", 6, 7),
        ("Très élevé (8-10)", 8, 10),
    ]
    lines.append("### Répartition par niveau d'exposition")
    lines.append("")
    lines.append("| Niveau | Métiers | Offres | % offres |")
    lines.append("|--------|---------|--------|----------|")
    for name, lo, hi in tiers:
        group = [r for r in records if r["exposure"] is not None and lo <= r["exposure"] <= hi]
        offres = sum(r["nb_offres"] or 0 for r in group)
        pct = offres / total_offres * 100 if total_offres else 0
        lines.append(f"| {name} | {len(group)} | {fmt_offres(offres)} | {pct:.1f}% |")
    lines.append("")

    # Full table by exposure
    lines.append(f"## Tous les métiers ({len(records)})")
    lines.append("")
    lines.append("Triés par exposition à l'IA (décroissant), puis par nombre d'offres.")
    lines.append("")

    for exp in range(10, -1, -1):
        group = [r for r in records if r["exposure"] == exp]
        if not group:
            continue
        group_offres = sum(r["nb_offres"] or 0 for r in group)
        lines.append(f"### Exposition {exp}/10 ({len(group)} métiers, {fmt_offres(group_offres)} offres)")
        lines.append("")
        lines.append("| # | Métier | Code ROME | Salaire médian | Offres | BMO | Tension BMO | Justification |")
        lines.append("|---|--------|-----------|---------------|--------|-----|-------------|---------------|")
        for i, r in enumerate(group, 1):
            rationale = r["rationale"].replace("|", "/").replace("\n", " ") if r["rationale"] else ""
            bmo = fmt_offres(r["projets_recrutement"]) if r["projets_recrutement"] is not None else "?"
            tension = f"{r['taux_difficulte']:.1f}%" if r["taux_difficulte"] is not None else "?"
            lines.append(f"| {i} | {r['title']} | {r['code_rome']} | {fmt_salary(r['salary'])} | {fmt_offres(r['nb_offres'])} | {bmo} | {tension} | {rationale} |")
        lines.append("")

    text = "\n".join(lines)
    with open("fr/data/prompt_fr.md", "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Wrote prompt_fr.md ({len(text):,} chars, {len(lines):,} lines)")


if __name__ == "__main__":
    main()
