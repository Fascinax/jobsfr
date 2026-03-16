"""Merge shard files + base scores.json into a single scores.json."""
import json
import glob
import os

BASE_FILE = "fr/data/scores.json"
SHARDS_DIR = "fr/data/scores_shards"
OUTPUT_FILE = "fr/data/scores.json"


def load_list_as_dict(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {entry["slug"]: entry for entry in data if "slug" in entry}
    return data


def main():
    merged = load_list_as_dict(BASE_FILE)
    print(f"Base scores.json: {len(merged)} entries")

    shard_files = sorted(glob.glob(f"{SHARDS_DIR}/shard_*.json"))
    for path in shard_files:
        shard = load_list_as_dict(path)
        before = len(merged)
        merged.update(shard)
        print(f"  {os.path.basename(path)}: {len(shard)} entries (+{len(merged) - before} new)")

    result = list(merged.values())
    print(f"\nTotal: {len(result)} entries → {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("Done.")


if __name__ == "__main__":
    main()
