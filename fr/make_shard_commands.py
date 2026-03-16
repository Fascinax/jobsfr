import json
from itertools import groupby

with open('fr/data/occupations.json', encoding='utf-8') as f:
    occs = json.load(f)
with open('fr/data/scores_shards/s1.json', encoding='utf-8') as f:
    done = set(e['slug'] for e in json.load(f))
for i in range(1, 9):
    try:
        with open(f'fr/data/scores_shards/shard_{i}.json', encoding='utf-8') as f:
            done.update(e['slug'] for e in json.load(f))
    except Exception:
        pass
missing = [i for i, occ in enumerate(occs) if occ['slug'] not in done]

# Regroupe les indices manquants en plages contiguës
ranges = []
for k, g in groupby(enumerate(missing), lambda x: x[1] - x[0]):
    group = list(g)
    start = group[0][1]
    end = group[-1][1] + 1
    ranges.append((start, end))

for idx, (start, end) in enumerate(ranges, 1):
    print(f"python fr/score_fr.py --start {start} --end {end} --output fr/data/scores_shards/missing_{idx}.json --delay 0.2")
