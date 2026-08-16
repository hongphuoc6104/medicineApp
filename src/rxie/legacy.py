"""Convert the tracked DRUG-only JSON dataset to RxIE annotation JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .annotations import convert_legacy_bio, dump_jsonl


def convert_file(source: Path, destination: Path) -> int:
    payload: Any = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("legacy dataset must be a JSON list")

    documents = []
    seen_ids: set[str] = set()
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"legacy row {index} must be an object")
        document_id = row.get("id")
        tokens = row.get("tokens")
        tags = row.get("ner_tags")
        if not isinstance(document_id, str) or not document_id:
            raise ValueError(f"legacy row {index} has no valid id")
        if document_id in seen_ids:
            raise ValueError(f"duplicate legacy document id: {document_id}")
        if not isinstance(tokens, list) or not all(
            isinstance(token, str) for token in tokens
        ):
            raise ValueError(f"legacy row {index} has invalid tokens")
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"legacy row {index} has invalid ner_tags")
        seen_ids.add(document_id)
        documents.append(convert_legacy_bio(document_id, tokens, tags))

    destination.parent.mkdir(parents=True, exist_ok=True)
    dump_jsonl(documents, destination)
    return len(documents)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    count = convert_file(args.source, args.destination)
    print(f"converted {count} legacy documents to {args.destination}")


if __name__ == "__main__":
    main()
