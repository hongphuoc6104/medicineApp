"""
Sliding window chunking and long-document handling policy.

Two Distinct Policies:
  1. Token-Level Policy (Training/Benchmark):
     - Window Size: 512 tokens
     - Stride: 64 tokens
     (Enforced during tokenization and model inference via configs/benchmark_v1.yaml)

  2. Character-Level Fallback Policy (Generic Text Partitioning):
     - max_chars: 1500 characters
     - overlap_chars: 400 characters (step = max_chars - overlap_chars = 1100 chars)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schemas import AnnotationDocument, GoldEntity


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    total_chunks: int
    char_start: int
    char_end: int
    raw_text: str
    entities: list[GoldEntity]


def chunk_document_by_characters(
    document: AnnotationDocument,
    max_chars: int = 1500,
    overlap_chars: int = 400,
) -> list[DocumentChunk]:
    """
    Partition long document into overlapping character chunks.
    Ensures that any entity whose boundary crosses a chunk split is preserved
    in the chunk where it is completely enclosed.
    """
    raw = document.raw_text
    total_len = len(raw)

    if total_len <= max_chars:
        return [
            DocumentChunk(
                chunk_index=0,
                total_chunks=1,
                char_start=0,
                char_end=total_len,
                raw_text=raw,
                entities=list(document.entities),
            )
        ]

    chunks = []
    start = 0
    chunk_idx = 0

    while start < total_len:
        end = min(total_len, start + max_chars)

        # Collect all entities completely enclosed in [start, end]
        chunk_entities = []
        for ent in document.entities:
            if ent.start >= start and ent.end <= end:
                # Adjust relative offsets for chunk
                rel_ent = GoldEntity(
                    type=ent.type,
                    text=ent.text,
                    start=ent.start - start,
                    end=ent.end - start,
                )
                chunk_entities.append(rel_ent)

        chunks.append(
            DocumentChunk(
                chunk_index=chunk_idx,
                total_chunks=0,  # updated below
                char_start=start,
                char_end=end,
                raw_text=raw[start:end],
                entities=chunk_entities,
            )
        )
        chunk_idx += 1
        if end >= total_len:
            break
        start += max_chars - overlap_chars

    # Update total_chunks count
    num_chunks = len(chunks)
    final_chunks = [
        DocumentChunk(
            chunk_index=c.chunk_index,
            total_chunks=num_chunks,
            char_start=c.char_start,
            char_end=c.char_end,
            raw_text=c.raw_text,
            entities=c.entities,
        )
        for c in chunks
    ]
    return final_chunks


def verify_gold_entities_recoverable(
    document: AnnotationDocument, chunks: list[DocumentChunk]
) -> bool:
    """Verify that 100% of gold entities in the source document appear in at least one chunk."""
    if not document.entities:
        return True

    recovered_entities = set()
    for chunk in chunks:
        for ent in chunk.entities:
            abs_start = chunk.char_start + ent.start
            abs_end = chunk.char_start + ent.end
            recovered_entities.add((ent.type, ent.text, abs_start, abs_end))

    for gold in document.entities:
        key = (gold.type, gold.text, gold.start, gold.end)
        if key not in recovered_entities:
            return False
    return True
