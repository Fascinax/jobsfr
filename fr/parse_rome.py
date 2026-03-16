"""
Parse ROME 4.0 fiches métiers into clean Markdown descriptions.

Converts the JSON fiche data into readable Markdown files, one per métier,
suitable for LLM scoring. Similar to parse_detail.py + process.py combined.

Usage:
    uv run python fr/parse_rome.py
    uv run python fr/parse_rome.py --force
"""

import argparse
import json
import os
import re


def slugify(text):
    """Convert a French title to a URL-safe slug."""
    text = text.lower()
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ù": "u", "û": "u", "ü": "u",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ç": "c",
        "œ": "oe", "æ": "ae",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def format_fiche_markdown(fiche):
    """Convert a ROME open data fiche JSON into Markdown text."""
    lines = []

    rome = fiche.get("rome", {})
    title = rome.get("intitule", "")
    code = rome.get("code_rome", "")

    lines.append(f"# {title}")
    lines.append(f"**Code ROME:** {code}")
    lines.append("")

    definition = fiche.get("definition", "")
    if definition:
        lines.append("## Définition")
        lines.append(definition)
        lines.append("")

    acces = fiche.get("acces_metier", "")
    if acces:
        lines.append("## Accès au métier")
        lines.append(acces)
        lines.append("")

    competences = fiche.get("competences", {})

    # Savoir-faire
    sf_enjeux = competences.get("savoir_faire", {}).get("enjeux", [])
    if sf_enjeux:
        lines.append("## Savoir-faire")
        for enjeu in sf_enjeux:
            cat = enjeu.get("libelle", "")
            if cat:
                lines.append(f"### {cat}")
            for item in enjeu.get("items", []):
                label = item.get("libelle", "")
                coeur = item.get("coeur_metier")
                suffix = f" *({coeur})*" if coeur else ""
                lines.append(f"- {label}{suffix}")
        lines.append("")

    # Savoir-être
    se_enjeux = competences.get("savoir_etre_professionnel", {}).get("enjeux", [])
    if se_enjeux:
        lines.append("## Savoir-être professionnels")
        for enjeu in se_enjeux:
            for item in enjeu.get("items", []):
                lines.append(f"- {item.get('libelle', '')}")
        lines.append("")

    # Savoirs
    savoirs_cats = competences.get("savoirs", {}).get("categories", [])
    if savoirs_cats:
        lines.append("## Savoirs")
        for cat in savoirs_cats:
            cat_label = cat.get("libelle", "")
            if cat_label:
                lines.append(f"### {cat_label}")
            for item in cat.get("items", []):
                label = item.get("libelle", "")
                coeur = item.get("coeur_metier")
                suffix = f" *({coeur})*" if coeur else ""
                lines.append(f"- {label}{suffix}")
        lines.append("")

    # Contextes de travail
    contextes = fiche.get("contextes_travail", [])
    if contextes:
        lines.append("## Contextes de travail")
        for ctx in contextes:
            cat = ctx.get("libelle", "")
            if cat:
                lines.append(f"### {cat}")
            for item in ctx.get("items", []):
                lines.append(f"- {item.get('libelle', '')}")
        lines.append("")

    # Secteurs d'activité
    secteurs = fiche.get("secteurs_activite", [])
    if secteurs:
        lines.append("## Secteurs d'activité")
        for s in secteurs:
            principal = " *(principal)*" if s.get("principal") else ""
            lines.append(f"- {s.get('libelle', '')}{principal}")
        lines.append("")

    # Appellations
    appellations = fiche.get("appellations", [])
    if appellations:
        lines.append("## Appellations métier")
        for app in appellations[:30]:
            lines.append(f"- {app.get('libelle', '')}")
        if len(appellations) > 30:
            lines.append(f"- ... et {len(appellations) - 30} autres appellations")
        lines.append("")

    # Mobilités
    mobilites = fiche.get("mobilites", [])
    if mobilites:
        lines.append("## Mobilités professionnelles")
        for m in mobilites:
            lines.append(f"- {m.get('rome_cible', '')}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fiches_path = "fr/data/fiches_detail.json"
    if not os.path.exists(fiches_path):
        print(f"Error: {fiches_path} not found. Run fetch_rome.py first.")
        return

    with open(fiches_path, encoding="utf-8") as f:
        fiches = json.load(f)

    os.makedirs("fr/pages", exist_ok=True)

    # Also build the occupations index (equivalent to occupations.json)
    occupations = []

    written = 0
    skipped = 0

    for fiche in fiches:
        rome = fiche.get("rome", {})
        code = rome.get("code_rome", "")
        title = rome.get("intitule", "")
        if not code or not title:
            continue

        slug = slugify(title)

        # Build occupation entry
        occupations.append({
            "title": title,
            "code_rome": code,
            "slug": slug,
        })

        md_path = f"fr/pages/{slug}.md"
        if os.path.exists(md_path) and not args.force:
            skipped += 1
            continue

        md = format_fiche_markdown(fiche)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        written += 1

    # Write occupations index
    with open("fr/data/occupations.json", "w", encoding="utf-8") as f:
        json.dump(occupations, f, ensure_ascii=False, indent=2)

    print(f"Parsed {len(fiches)} fiches → {written} written, {skipped} skipped")
    print(f"Wrote occupations index: fr/data/occupations.json ({len(occupations)} métiers)")


if __name__ == "__main__":
    main()
