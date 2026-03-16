# Exposition des Métiers Français à l'IA

Adaptation française du projet [karpathy/jobs](https://github.com/karpathy/jobs) qui cartographie l'exposition des métiers américains à l'IA. Cette version utilise les données françaises du **ROME 4.0** (France Travail), le **BMO 2025** en open data et l'**API Offres d'emploi** pour construire un observatoire équivalent pour le marché du travail français.

## Aperçu

- **~1 584 fiches métiers** du ROME 4.0 (vs 342 occupations BLS aux US)
- **Scoring LLM** de l'exposition à l'IA (0-10) adapté au contexte français
- **Données marché** : offres d'emploi, salaires estimés via l'API France Travail, projets de recrutement BMO 2025
- **Visualisation interactive** : treemap similaire à karpathy.ai/jobs

## Différences avec le projet US

| Aspect | US (Karpathy) | France (cette adaptation) |
|--------|--------------|---------------------------|
| Source métiers | BLS Occupational Outlook Handbook | ROME 4.0 (France Travail) |
| Nb de métiers | 342 | ~1 584 |
| Données tâches | O*NET (très détaillé) | Compétences ROME (4 niveaux) |
| Salaires | BLS (précis, médiane) | API Offres (estimé depuis offres) |
| Emploi | BLS (nb emplois 2024) | Nb offres d'emploi (proxy) |
| Perspectives | BLS Outlook 2034 | N/A (BMO partiel) |
| Scoring | GitHub Copilot SDK | Idem |

## Prérequis

### Credentials

1. **France Travail API** : Créer un compte sur [francetravail.io](https://francetravail.io/data/api) et obtenir des identifiants OAuth2. Souscrire à l'API :
   - `Offres d'emploi v2`

2. **GitHub Copilot** : Utiliser un PAT GitHub avec scope Copilot (ou `gh auth login`).

3. Créer un fichier `.env` à la racine :
   ```
   FRANCE_TRAVAIL_CLIENT_ID=votre_client_id
   FRANCE_TRAVAIL_CLIENT_SECRET=votre_client_secret
   GITHUB_PAT=votre_pat_github_avec_scope_copilot
   ```

### Installation

```bash
uv sync
```

## Pipeline

Exécuter les scripts dans l'ordre :

### 1. Récupérer les fiches ROME 4.0

```bash
uv run python fr/fetch_rome.py
```

Télécharge les fiches détaillées ROME 4.0 depuis l'open data France Travail. Résultat : `fr/data/fiches_detail.json`.

### 2. Parser en Markdown

```bash
uv run python fr/parse_rome.py
```

Convertit les fiches JSON en fichiers Markdown lisibles (un par métier dans `fr/pages/`), et génère l'index `fr/data/occupations.json`.

### 3. Récupérer les données BMO

```bash
uv run python fr/fetch_bmo.py
```

Télécharge le BMO 2025 en open data et la table de passage FAP→ROME, puis produit `fr/data/bmo_per_rome.json`.

### 4. Récupérer les données marché

```bash
uv run python fr/fetch_market_data.py
```

Enrichit chaque métier avec le nombre d'offres et les salaires estimés depuis l'API Offres d'emploi, puis fusionne les indicateurs BMO si disponibles. Résultat : `fr/data/market_data.json`.

### 5. Scorer l'exposition à l'IA

```bash
uv run python fr/score_fr.py
```

Envoie chaque fiche Markdown à un LLM (Copilot SDK, `gemini-3-flash-preview` par défaut) avec un prompt calibré pour le contexte français. Résultat : `fr/data/scores.json`.

Options :
```bash
uv run python fr/score_fr.py --start 0 --end 10   # tester sur les 10 premiers
uv run python fr/score_fr.py --model gemini-3-flash-preview
uv run python fr/score_fr.py --force               # re-scorer tout
```

### 6. Générer le CSV consolidé

```bash
uv run python fr/make_csv_fr.py
```

Fusionne toutes les sources en un CSV unifié : `fr/data/occupations_fr.csv`.

### 7. Construire les données du site

```bash
uv run python fr/build_site_data_fr.py
```

Fusionne CSV + scores en un JSON compact pour la visualisation : `fr/site/data.json`.

### 8. Générer le prompt d'analyse

```bash
uv run python fr/make_prompt_fr.py
```

Produit un fichier Markdown consolidé (`fr/data/prompt_fr.md`) contenant toutes les données, conçu pour être copié-collé dans un LLM pour analyse.

### 9. Visualiser

Ouvrir `fr/site/index.html` dans un navigateur (servir via un serveur local pour que `fetch()` fonctionne) :

```bash
cd fr/site && python -m http.server 8000
```

Puis ouvrir http://localhost:8000

## Architecture

```
fr/
├── fetch_rome.py          # 1. Télécharger les fiches ROME 4.0
├── parse_rome.py          # 2. Convertir JSON → Markdown
├── fetch_bmo.py           # 3. BMO 2025 + passage FAP→ROME
├── fetch_market_data.py   # 4. Données marché (offres, salaires, BMO)
├── score_fr.py            # 5. Scoring LLM exposition IA
├── make_csv_fr.py         # 6. CSV consolidé
├── build_site_data_fr.py  # 7. JSON pour le site
├── make_prompt_fr.py      # 8. Prompt d'analyse
├── data/
│   ├── bmo_per_rome.json      # BMO national redistribué par code ROME
│   ├── fiches_detail.json     # Détails complets par métier
│   ├── occupations.json       # Index simplifié
│   ├── market_data.json       # Données marché
│   ├── scores.json            # Scores d'exposition IA
│   ├── occupations_fr.csv     # CSV consolidé
│   └── prompt_fr.md           # Prompt d'analyse
├── pages/                     # Markdown par métier
│   ├── developpeur-informatique.md
│   ├── infirmier-en-soins-generaux.md
│   └── ...
└── site/
    ├── index.html             # Visualisation treemap
    └── data.json              # Données compactes
```

## Limites connues

1. **Pas d'équivalent O*NET** : Le ROME ne décrit pas les tâches aussi finement que O*NET. Le scoring LLM s'appuie sur les descriptions de compétences, pas sur des tâches unitaires.

2. **Salaires estimés** : Les salaires sont extraits des offres d'emploi (quand renseignés), ce qui biaise vers les offres qui mentionnent le salaire. Pour des données plus précises, croiser avec les données INSEE/DADS.

3. **Offres ≠ Emploi** : Le nombre d'offres est un proxy du dynamisme, pas du stock d'emplois. Pour le stock réel, intégrer les données INSEE ou DARES.

4. **BMO partiel** : Le passage FAP→ROME ne couvre pas tous les codes ROME. Une partie du BMO est redistribuée par sous-domaine, ce qui reste utile mais moins précis qu'une correspondance native ROME.

5. **Scoring subjectif** : Comme pour le projet original, le scoring est subjectif et dépend du modèle LLM et du prompt.

## Sources de données complémentaires

Pour enrichir le projet :

- **BMO (Besoins en Main-d'Œuvre)** : Enquête annuelle France Travail sur les besoins de recrutement → tensions par métier
- **Data Emploi** : Indicateurs actualisés trimestriellement (demandeurs, embauches, dynamisme)
- **INSEE DADS/DSN** : Salaires réels par profession (PCS)
- **France Stratégie "Les métiers en 2030"** : Projections démographiques et économiques
- **Tables ROME/FAP/PCS** : Correspondances entre nomenclatures pour croiser les sources

## Crédits

- Inspiré par [Andrej Karpathy](https://karpathy.ai/jobs/) et son analyse du marché US
- Données : [France Travail Open Data](https://francetravail.io/data/api)
- Recherche sur l'exposition IA en France : Antonin Bergeaud et al.
