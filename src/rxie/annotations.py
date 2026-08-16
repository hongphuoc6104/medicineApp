"""JSONL annotation I/O and DRUG-only legacy BIO conversion."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from pydantic import ValidationError

from .schemas import (
    AnnotationDocument,
    AnnotationProvenance,
    EntityType,
    GoldEntity,
)

LEGACY_PROVENANCE_WARNING = (
    "Converted from legacy token/BIO data; labels are DRUG-only and are not "
    "ten-class ground truth."
)
LEGACY_TAGS = frozenset({"O", "B-DRUG", "I-DRUG"})


def load_jsonl(path: str | Path) -> list[AnnotationDocument]:
    """Load and validate versioned annotation records from a UTF-8 JSONL file."""
    source = Path(path)
    documents: list[AnnotationDocument] = []
    document_ids: set[str] = set()
    with source.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                document = AnnotationDocument.model_validate_json(line)
            except (ValidationError, ValueError) as exc:
                location = f"{source}:{line_number}"
                raise ValueError(f"invalid annotation at {location}: {exc}") from exc
            if document.document_id in document_ids:
                raise ValueError(
                    f"duplicate document_id at {source}:{line_number}: "
                    f"{document.document_id}"
                )
            document_ids.add(document.document_id)
            documents.append(document)
    return documents


def legacy_bio_to_char_spans(
    tokens: Sequence[str], tags: Sequence[str]
) -> tuple[str, list[GoldEntity]]:
    """Reconstruct space-joined legacy text and convert DRUG BIO tags to spans."""
    if len(tokens) != len(tags):
        raise ValueError("legacy tokens and BIO tags must have the same length")
    unsupported = sorted(set(tags) - LEGACY_TAGS)
    if unsupported:
        raise ValueError(f"unsupported legacy BIO tags: {unsupported}")
    if any(not token for token in tokens):
        raise ValueError("legacy tokens must not be empty")

    raw_text = " ".join(tokens)
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for token in tokens:
        offsets.append((cursor, cursor + len(token)))
        cursor += len(token) + 1

    entities: list[GoldEntity] = []
    entity_start: int | None = None
    entity_end: int | None = None
    for tag, (start, end) in zip(tags, offsets, strict=True):
        if tag == "I-DRUG" and entity_start is None:
            raise ValueError("I-DRUG must follow B-DRUG or I-DRUG")
        if tag != "I-DRUG" and entity_start is not None:
            entities.append(
                GoldEntity(
                    type=EntityType.DRUG,
                    text=raw_text[entity_start:entity_end],
                    start=entity_start,
                    end=entity_end,
                )
            )
            entity_start = None
        if tag == "B-DRUG":
            entity_start, entity_end = start, end
        elif tag == "I-DRUG":
            entity_end = end

    if entity_start is not None:
        entities.append(
            GoldEntity(
                type=EntityType.DRUG,
                text=raw_text[entity_start:entity_end],
                start=entity_start,
                end=entity_end,
            )
        )
    return raw_text, entities


def convert_legacy_bio(
    document_id: str, tokens: Sequence[str], tags: Sequence[str]
) -> AnnotationDocument:
    """Create an annotation record that retains its DRUG-only legacy provenance."""
    raw_text, entities = legacy_bio_to_char_spans(tokens, tags)
    return AnnotationDocument(
        document_id=document_id,
        raw_text=raw_text,
        entities=entities,
        provenance=AnnotationProvenance(
            source="legacy_drug_only", warnings=[LEGACY_PROVENANCE_WARNING]
        ),
    )


def dump_jsonl(documents: Iterable[AnnotationDocument], path: str | Path) -> None:
    """Write annotation records as deterministic UTF-8 JSONL."""
    with Path(path).open("w", encoding="utf-8") as handle:
        for document in documents:
            payload = json.dumps(
                document.model_dump(mode="json"), ensure_ascii=False
            )
            handle.write(payload)
            handle.write("\n")
