import json
import statistics
from collections import Counter

with open("fr/data/scores.json") as f:
    scores = json.load(f)

exposures = [s["exposure"] for s in scores]
dist = Counter(exposures)

print("=" * 60)
print("  ANALYSE DES SCORES D'EXPOSITION A L'IA")
print("  1584 métiers français (France Travail / ROME)")
print("=" * 60)

print("\n--- Distribution des scores ---")
print(f"Total métiers: {len(scores)}")
print()
for k in sorted(dist.keys()):
    bar = "█" * (dist[k] // 4)
    print(f"  Score {k:2d}: {dist[k]:4d} ({dist[k]*100/len(scores):5.1f}%)  {bar}")

avg = sum(exposures) / len(exposures)
med = statistics.median(exposures)
print(f"\n  Moyenne:    {avg:.2f}")
print(f"  Médiane:    {med}")
print(f"  Min: {min(exposures)}, Max: {max(exposures)}")
print(f"  Écart-type: {statistics.stdev(exposures):.2f}")

print("\n--- Regroupement par tranche ---")
low = [s for s in scores if s["exposure"] <= 3]
mid_low = [s for s in scores if 4 <= s["exposure"] <= 5]
mid_high = [s for s in scores if 6 <= s["exposure"] <= 7]
high = [s for s in scores if s["exposure"] >= 8]
print(f"  Faible (1-3):     {len(low):4d} métiers ({len(low)*100/len(scores):5.1f}%)")
print(f"  Moyen-bas (4-5):  {len(mid_low):4d} métiers ({len(mid_low)*100/len(scores):5.1f}%)")
print(f"  Moyen-haut (6-7): {len(mid_high):4d} métiers ({len(mid_high)*100/len(scores):5.1f}%)")
print(f"  Élevé (8-10):     {len(high):4d} métiers ({len(high)*100/len(scores):5.1f}%)")

print("\n--- TOP 25 métiers les PLUS exposés ---")
top = sorted(scores, key=lambda x: -x["exposure"])
for i, s in enumerate(top[:25], 1):
    print(f"  {i:2d}. [{s['exposure']:2d}] {s['title']}")

print("\n--- TOP 25 métiers les MOINS exposés ---")
bot = sorted(scores, key=lambda x: x["exposure"])
for i, s in enumerate(bot[:25], 1):
    print(f"  {i:2d}. [{s['exposure']:2d}] {s['title']}")

# Analyse par domaine ROME (première lettre du code)
rome_domains = {
    "A": "Agriculture / Espaces verts",
    "B": "Arts / Spectacle",
    "C": "Banque / Assurance / Immobilier",
    "D": "Commerce / Vente",
    "E": "Communication / Média / Multimédia",
    "F": "Construction / BTP",
    "G": "Hôtellerie / Restauration / Tourisme / Loisirs",
    "H": "Industrie",
    "I": "Installation / Maintenance",
    "J": "Santé",
    "K": "Services à la personne / collectivité",
    "L": "Spectacle",
    "M": "Support à l'entreprise",
    "N": "Transport / Logistique",
}

print("\n--- Moyenne par domaine ROME ---")
domain_scores = {}
for s in scores:
    letter = s["code_rome"][0]
    domain_scores.setdefault(letter, []).append(s["exposure"])

domain_avgs = []
for letter in sorted(domain_scores.keys()):
    vals = domain_scores[letter]
    avg_d = sum(vals) / len(vals)
    name = rome_domains.get(letter, "Inconnu")
    domain_avgs.append((avg_d, letter, name, len(vals)))

domain_avgs.sort(key=lambda x: -x[0])
for avg_d, letter, name, count in domain_avgs:
    bar = "█" * int(avg_d * 3)
    print(f"  {letter} - {name:<45s} moy={avg_d:.1f}  (n={count:3d})  {bar}")

# Analyse croisée avec offres d'emploi
print("\n--- Croisement scores x offres d'emploi ---")
import csv
occ_data = {}
with open("fr/data/occupations_fr.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        occ_data[row["slug"]] = row

# Score moyen pondéré par nb offres
weighted_sum = 0
weight_total = 0
high_exposure_high_demand = []
low_exposure_high_demand = []
for s in scores:
    slug = s["slug"]
    if slug in occ_data and occ_data[slug]["nb_offres"]:
        nb = int(occ_data[slug]["nb_offres"])
        weighted_sum += s["exposure"] * nb
        weight_total += nb
        if s["exposure"] >= 8 and nb >= 500:
            high_exposure_high_demand.append((s, nb))
        if s["exposure"] <= 3 and nb >= 500:
            low_exposure_high_demand.append((s, nb))

if weight_total:
    print(f"  Score moyen pondéré par offres: {weighted_sum/weight_total:.2f}")

print(f"\n  Métiers TRÈS exposés (>=8) ET très demandés (>=500 offres): {len(high_exposure_high_demand)}")
high_exposure_high_demand.sort(key=lambda x: -x[1])
for s, nb in high_exposure_high_demand[:15]:
    print(f"    [{s['exposure']}] {s['title']} — {nb} offres")

print(f"\n  Métiers PEU exposés (<=3) ET très demandés (>=500 offres): {len(low_exposure_high_demand)}")
low_exposure_high_demand.sort(key=lambda x: -x[1])
for s, nb in low_exposure_high_demand[:15]:
    print(f"    [{s['exposure']}] {s['title']} — {nb} offres")

# BMO croisement
print("\n--- Croisement scores x difficultés de recrutement (BMO) ---")
high_diff_high_expo = []
for s in scores:
    slug = s["slug"]
    if slug in occ_data and occ_data[slug]["taux_difficulte"]:
        td = float(occ_data[slug]["taux_difficulte"])
        pr = int(occ_data[slug]["projets_recrutement"]) if occ_data[slug]["projets_recrutement"] else 0
        if s["exposure"] >= 7 and td >= 60 and pr >= 1000:
            high_diff_high_expo.append((s, td, pr))

high_diff_high_expo.sort(key=lambda x: -x[1])
print(f"  Métiers exposés (>=7) + difficiles à recruter (>=60%) + volume (>=1000 projets): {len(high_diff_high_expo)}")
for s, td, pr in high_diff_high_expo[:15]:
    print(f"    [{s['exposure']}] {s['title']} — difficulté {td}%, {pr} projets")

print("\n" + "=" * 60)
print("  FIN DE L'ANALYSE")
print("=" * 60)
