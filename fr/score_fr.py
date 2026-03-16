"""
Score each French occupation's AI exposure using GitHub Copilot SDK.

Reads Markdown descriptions from fr/pages/, sends each to an LLM with a
scoring rubric adapted for French jobs (ROME 4.0), and collects structured
scores. Results are cached incrementally to fr/data/scores.json.

Usage:
    uv run python fr/score_fr.py
    uv run python fr/score_fr.py --model google/gemini-2.0-flash-001
    uv run python fr/score_fr.py --start 0 --end 10
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from openrouter_sdk_client import OpenRouterClient

load_dotenv()

DEFAULT_MODEL = "google/gemini-2.0-flash-001"
DEFAULT_OUTPUT_FILE = "fr/data/scores.json"

SYSTEM_PROMPT = """\
Tu es un analyste expert qui évalue l'exposition des métiers français à \
l'intelligence artificielle. On va te fournir la description détaillée d'un \
métier issu du référentiel ROME 4.0 de France Travail, avec ses compétences, \
savoir-faire et contextes de travail.

Évalue l'**Exposition à l'IA** de ce métier sur une échelle de 0 à 10.

L'Exposition à l'IA mesure : dans quelle mesure l'IA va-t-elle transformer \
ce métier ? Considère à la fois les effets directs (l'IA automatisant des \
tâches actuellement réalisées par des humains) et les effets indirects (l'IA \
rendant chaque travailleur si productif que moins de postes sont nécessaires).

Un signal clé est le caractère fondamentalement numérique du travail. Si le \
métier peut être exercé entièrement depuis un bureau à domicile sur un \
ordinateur — rédaction, programmation, analyse, communication — alors \
l'exposition à l'IA est intrinsèquement élevée (7+), car les capacités de \
l'IA dans les domaines numériques progressent rapidement. Même si l'IA \
actuelle ne peut pas gérer tous les aspects d'un tel métier, la trajectoire \
est raide et le plafond très haut. À l'inverse, les métiers nécessitant une \
présence physique, une habileté manuelle ou une interaction humaine en temps \
réel dans le monde physique ont une barrière naturelle à l'exposition à l'IA.

Utilise ces ancres pour calibrer ton score :

- **0–1 : Exposition minimale.** Le travail est presque entièrement \
physique, manuel, ou nécessite une présence humaine en temps réel dans des \
environnements imprévisibles. L'IA n'a essentiellement aucun impact. \
Exemples : couvreur, paysagiste, plongeur professionnel, maçon.

- **2–3 : Exposition faible.** Travail principalement physique ou \
relationnel. L'IA peut aider pour des tâches périphériques (planification, \
paperasse) mais ne touche pas le cœur du métier. \
Exemples : électricien, plombier, pompier, aide-soignant.

- **4–5 : Exposition modérée.** Mélange de travail physique/relationnel et \
de travail intellectuel. L'IA peut significativement assister les parties \
informationnelles, mais une part substantielle nécessite la présence humaine. \
Exemples : infirmier, policier, vétérinaire, technicien de maintenance.

- **6–7 : Exposition élevée.** Travail principalement intellectuel avec un \
besoin de jugement humain, de relations ou de présence physique. Les outils \
IA sont déjà utiles et les travailleurs les utilisant sont plus productifs. \
Exemples : enseignant, cadre/manager, comptable, journaliste, RH.

- **8–9 : Exposition très élevée.** Le métier s'exerce presque entièrement \
sur ordinateur. Toutes les tâches principales — rédaction, programmation, \
analyse, conception, communication — sont dans des domaines où l'IA progresse \
rapidement. Le métier fait face à une restructuration majeure. \
Exemples : développeur logiciel, graphiste, traducteur, analyste de données, \
juriste d'entreprise, rédacteur web.

- **10 : Exposition maximale.** Traitement routinier d'informations, \
entièrement numérique, sans composante physique. L'IA peut déjà faire la \
plupart du travail aujourd'hui. \
Exemples : opérateur de saisie, télévendeur, assistant administratif de base.

Réponds UNIQUEMENT avec un objet JSON dans ce format exact, sans autre texte :
{
  "exposure": <0-10>,
  "rationale": "<2-3 phrases expliquant les facteurs clés, en français>"
}\
"""


def score_occupation(client, text):
    """Send one occupation to the LLM and parse the structured response."""
    return client.chat_json(system=SYSTEM_PROMPT, user=text)


def load_existing_scores(output_file, force):
    scores = {}
    if os.path.exists(output_file) and not force:
        with open(output_file, encoding="utf-8") as f:
            for entry in json.load(f):
                scores[entry["slug"]] = entry
    return scores


def save_scores(output_file, scores):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(list(scores.values()), f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--force", action="store_true",
                        help="Re-score even if already cached")
    args = parser.parse_args()

    with open("fr/data/occupations.json", encoding="utf-8") as f:
        occupations = json.load(f)

    subset = occupations[args.start:args.end]
    output_file = args.output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    scores = load_existing_scores(output_file, args.force)

    print(f"Scoring {len(subset)} métiers with {args.model}")
    print(f"Already cached: {len(scores)}")

    errors = []
    client = OpenRouterClient(model=args.model)

    for i, occ in enumerate(subset):
        slug = occ["slug"]

        if slug in scores:
            continue

        md_path = f"fr/pages/{slug}.md"
        if not os.path.exists(md_path):
            print(f"  [{i+1}] SKIP {slug} (no markdown)")
            continue

        with open(md_path, encoding="utf-8") as f:
            text = f.read()

        print(f"  [{i+1}/{len(subset)}] {occ['title']}...", end=" ", flush=True)

        try:
            result = score_occupation(client, text)
            scores[slug] = {
                "slug": slug,
                "code_rome": occ["code_rome"],
                "title": occ["title"],
                **result,
            }
            print(f"exposure={result['exposure']}")
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append(slug)

        # Save after each one (incremental checkpoint)
        save_scores(output_file, scores)

        if i < len(subset) - 1:
            time.sleep(args.delay)

    print(f"\nDone. Scored {len(scores)} métiers, {len(errors)} errors.")
    if errors:
        print(f"Errors: {errors}")

    # Summary stats
    vals = [s for s in scores.values() if "exposure" in s]
    if vals:
        avg = sum(s["exposure"] for s in vals) / len(vals)
        by_score = {}
        for s in vals:
            bucket = s["exposure"]
            by_score[bucket] = by_score.get(bucket, 0) + 1
        print(f"\nExposition moyenne sur {len(vals)} métiers: {avg:.1f}")
        print("Distribution:")
        for k in sorted(by_score):
            print(f"  {k}: {'█' * by_score[k]} ({by_score[k]})")


if __name__ == "__main__":
    main()
