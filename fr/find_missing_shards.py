import glob
import json

with open('fr/data/occupations.json', encoding='utf-8') as f:
    occs = json.load(f)

shard_files = sorted(glob.glob('fr/data/scores_shards/*.json'))
done = set()
for path in shard_files:
    try:
        with open(path, encoding='utf-8') as f:
            done.update(e['slug'] for e in json.load(f))
    except Exception:
        pass

missing = [i for i, occ in enumerate(occs) if occ['slug'] not in done]
print('Shard files used:', len(shard_files))
print('Missing indices:', missing)
print('Total missing:', len(missing))
if missing:
    print('First missing:', missing[0], occs[missing[0]]['slug'])
    print('Last missing:', missing[-1], occs[missing[-1]]['slug'])
