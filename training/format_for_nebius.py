"""Convert validated NL→GraphQL pairs to OpenAI chat format JSONL with 80/20
train/val split. Output files are ready to upload to Nebius Studio Data Lab.

Usage:
    python format_for_nebius.py validated_pairs.jsonl
    # produces training/train.jsonl and training/val.jsonl
"""
import json
import random
import sys
from pathlib import Path

SYSTEM = (
    "You translate natural language questions about data assets into DataHub "
    "GraphQL read queries. The target is DataHub Core with Olist datasets "
    "ingested under sqlite platform instances olist_source (clean) and "
    "olist_dirty (planted issues). URN format is "
    "urn:li:dataset:(urn:li:dataPlatform:sqlite,<instance>.main.<table>,PROD). "
    "Return only valid GraphQL, no markdown, no explanation."
)


def to_chat(pair: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": pair["nl"]},
            {"role": "assistant", "content": pair["graphql"]},
        ]
    }


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "validated_pairs.jsonl")
    if not src.exists():
        print(f"❌ {src} not found", file=__import__('sys').stderr)
        sys.exit(1)

    with open(src) as f:
        pairs = [json.loads(line) for line in f if line.strip()]

    random.seed(42)
    random.shuffle(pairs)

    split = int(len(pairs) * 0.8)
    train_pairs = pairs[:split]
    val_pairs = pairs[split:]

    out_dir = src.parent
    train_path = out_dir / "train.jsonl"
    val_path = out_dir / "val.jsonl"

    with open(train_path, "w") as f:
        for p in train_pairs:
            f.write(json.dumps(to_chat(p)) + "\n")
    with open(val_path, "w") as f:
        for p in val_pairs:
            f.write(json.dumps(to_chat(p)) + "\n")

    print(f"train: {len(train_pairs)} pairs → {train_path}")
    print(f"val:   {len(val_pairs)} pairs → {val_path}")
    print()
    print("Next: upload both files to Nebius Studio → Data Lab → Datasets")


if __name__ == "__main__":
    main()
