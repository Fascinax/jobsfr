import json
import os
import time

expected = {
    'missing_1.json': 64,
    'missing_2.json': 108,
    'missing_3.json': 110,
    'missing_4.json': 106,
    'missing_5.json': 108,
    'missing_6.json': 110,
    'missing_7.json': 106,
    'missing_8.json': 108,
}

base = 'fr/data/scores_shards'
start = time.time()
timeout_s = 2400

while True:
    counts = {}
    for name in expected:
        path = os.path.join(base, name)
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    counts[name] = len(json.load(f))
            except Exception:
                counts[name] = -1
        else:
            counts[name] = 0

    line = ' | '.join(f"{k}:{counts[k]}/{expected[k]}" for k in sorted(expected))
    print(line, flush=True)

    if all(counts[k] == expected[k] for k in expected):
        print('DONE')
        raise SystemExit(0)

    if time.time() - start > timeout_s:
        print('TIMEOUT')
        raise SystemExit(1)

    time.sleep(20)
