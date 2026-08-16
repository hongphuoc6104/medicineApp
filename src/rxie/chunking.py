"""
Sliding window chunking, token windowing, and long-document reconstruction policy.

Policies:
  1. Token-Level Sliding Window Policy (Model Training / Inference):
     - Window Size: 256 for PhoBERT, 512 for BamiBERT / ViPubmedDeBERTa
     - Stride (Overlap): 64 tokens (step = max_length - stride = 192 or 448 tokens)
     - Multi-window documents are fully covered; 0 silent truncation.
     - Predictions across windows are merged back to document character coordinates with span deduplication.

  2. Character-Level Fallback Policy (Generic Text Partitioning):
     - max_chars: 1500 characters
     - overlap_chars: 400 characters (step = 1100 chars)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schemas import (
    AnnotationDocument,
    AnnotationDocumentV2,
    EntityRelation,
    EntityType,
    GoldEntity,
    GoldEntityV2,
    RelationType,
)


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    total_chunks: int
    char_start: int
    char_end: int
    raw_text: str
    entities: list[GoldEntity]


@dataclass(frozen=True)
class TokenWindow:
    window_idx: int
    total_windows: int
    token_start: int
    token_end: int
    input_ids: list[int]
    attention_mask: list[int]
    labels: list[int]
    offsets: list[tuple[int, int]]


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

        chunk_entities = []
        for ent in document.entities:
            if ent.start >= start and ent.end <= end:
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
                total_chunks=0,
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

    num_chunks = len(chunks)
    return [
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


def create_token_sliding_windows(
    input_ids: list[int],
    offsets: list[tuple[int, int]],
    labels: list[int],
    max_length: int = 256,
    stride: int = 64,
) -> list[TokenWindow]:
    """
    Split a sequence of token IDs, offsets, and labels into sliding windows of max_length with stride overlap.
    """
    total_tokens = len(input_ids)
    if total_tokens <= max_length:
        return [
            TokenWindow(
                window_idx=0,
                total_windows=1,
                token_start=0,
                token_end=total_tokens,
                input_ids=list(input_ids),
                attention_mask=[1] * total_tokens,
                labels=list(labels),
                offsets=list(offsets),
            )
        ]

    step = max_length - stride
    windows: list[TokenWindow] = []
    start = 0
    w_idx = 0

    while start < total_tokens:
        end = min(total_tokens, start + max_length)
        w_input_ids = input_ids[start:end]
        w_offsets = offsets[start:end]
        w_labels = labels[start:end]
        w_att_mask = [1] * len(w_input_ids)

        windows.append(
            TokenWindow(
                window_idx=w_idx,
                total_windows=0,  # updated below
                token_start=start,
                token_end=end,
                input_ids=w_input_ids,
                attention_mask=w_att_mask,
                labels=w_labels,
                offsets=w_offsets,
            )
        )
        w_idx += 1
        if end >= total_tokens:
            break
        start += step

    num_windows = len(windows)
    return [
        TokenWindow(
            window_idx=w.window_idx,
            total_windows=num_windows,
            token_start=w.token_start,
            token_end=w.token_end,
            input_ids=w.input_ids,
            attention_mask=w.attention_mask,
            labels=w.labels,
            offsets=w.offsets,
        )
        for w in windows
    ]


def decode_windows_to_document(
    source_doc: AnnotationDocumentV2,
    windows: list[TokenWindow],
    window_preds: list[list[int]],
    id_to_label: dict[int, str],
) -> AnnotationDocumentV2:
    """
    Decode token predictions across multiple sliding windows of a document,
    merge them into character spans, deduplicate overlapping predictions,
    and build structured relations.
    """
    raw_text = source_doc.raw_text
    extracted_entities: list[GoldEntityV2] = []

    # Map candidate spans: (type, start, end, text) -> list of (distance_from_window_edge, window_idx)
    candidate_spans: dict[tuple[EntityType, int, int, str], float] = {}

    for win, preds in zip(windows, window_preds, strict=True):
        offsets = win.offsets
        win_len = len(offsets)
        current_entity_type: str | None = None
        current_start: int = 0
        current_end: int = 0
        current_tok_start_idx: int = 0

        for idx, (t_start, t_end) in enumerate(offsets):
            if idx >= len(preds):
                break
            label_id = preds[idx]
            if label_id == -100:
                continue
            tag = id_to_label.get(label_id, "O")

            if tag.startswith("B-"):
                if current_entity_type is not None and current_start < current_end:
                    span_text = raw_text[current_start:current_end]
                    # Score confidence: spans closer to center of window have higher score
                    edge_dist = min(current_tok_start_idx, win_len - idx)
                    key = (EntityType(current_entity_type), current_start, current_end, span_text)
                    candidate_spans[key] = max(candidate_spans.get(key, -1.0), float(edge_dist))
                current_entity_type = tag[2:]
                current_start = t_start
                current_end = t_end
                current_tok_start_idx = idx
            elif tag.startswith("I-"):
                ent_type = tag[2:]
                if current_entity_type == ent_type:
                    current_end = t_end
                else:
                    if current_entity_type is not None and current_start < current_end:
                        span_text = raw_text[current_start:current_end]
                        edge_dist = min(current_tok_start_idx, win_len - idx)
                        key = (EntityType(current_entity_type), current_start, current_end, span_text)
                        candidate_spans[key] = max(candidate_spans.get(key, -1.0), float(edge_dist))
                    current_entity_type = ent_type
                    current_start = t_start
                    current_end = t_end
                    current_tok_start_idx = idx
            else:  # "O"
                if current_entity_type is not None and current_start < current_end:
                    span_text = raw_text[current_start:current_end]
                    edge_dist = min(current_tok_start_idx, win_len - idx)
                    key = (EntityType(current_entity_type), current_start, current_end, span_text)
                    candidate_spans[key] = max(candidate_spans.get(key, -1.0), float(edge_dist))
                    current_entity_type = None

        if current_entity_type is not None and current_start < current_end:
            span_text = raw_text[current_start:current_end]
            edge_dist = min(current_tok_start_idx, win_len - 1)
            key = (EntityType(current_entity_type), current_start, current_end, span_text)
            candidate_spans[key] = max(candidate_spans.get(key, -1.0), float(edge_dist))

    # Sort spans by character start offset and deduplicate overlapping spans
    sorted_candidates = sorted(candidate_spans.keys(), key=lambda c: (c[1], -(c[2] - c[1])))
    final_spans: list[tuple[EntityType, int, int, str]] = []
    for cand in sorted_candidates:
        c_type, c_start, c_end, c_text = cand
        # Check overlap with already accepted spans
        has_overlap = False
        for acc_type, acc_start, acc_end, acc_text in final_spans:
            if max(c_start, acc_start) < min(c_end, acc_end):
                has_overlap = True
                break
        if not has_overlap:
            final_spans.append(cand)

    final_spans.sort(key=lambda s: (s[1], s[2]))

    ent_counter = 1
    for s_type, s_start, s_end, s_text in final_spans:
        extracted_entities.append(GoldEntityV2(
            entity_id=f"e_{ent_counter}",
            type=s_type,
            text=s_text,
            start=s_start,
            end=s_end,
        ))
        ent_counter += 1

    # Link non-DRUG entities to the nearest preceding DRUG entity
    drug_entities = [e for e in extracted_entities if e.type == EntityType.DRUG]
    relations: list[EntityRelation] = []

    for e in extracted_entities:
        if e.type != EntityType.DRUG:
            preceding_drugs = [d for d in drug_entities if d.end <= e.start]
            if preceding_drugs:
                parent_drug = preceding_drugs[-1]
                e.parent_entity_id = parent_drug.entity_id
                rel_type = {
                    EntityType.STRENGTH: RelationType.HAS_STRENGTH,
                    EntityType.DOSAGE: RelationType.HAS_DOSAGE,
                    EntityType.FREQUENCY: RelationType.HAS_FREQUENCY,
                    EntityType.ROUTE: RelationType.HAS_ROUTE,
                    EntityType.INSTRUCTION: RelationType.HAS_INSTRUCTION,
                }.get(e.type, RelationType.HAS_INSTRUCTION)
                relations.append(EntityRelation(
                    head_entity_id=parent_drug.entity_id,
                    tail_entity_id=e.entity_id,
                    relation_type=rel_type,
                ))

    return AnnotationDocumentV2(
        schema_version="rxie.annotation.v2",
        document_id=source_doc.document_id,
        prescription_id=source_doc.prescription_id,
        patient_id=source_doc.patient_id,
        raw_text=raw_text,
        entities=extracted_entities,
        relations=relations,
    )
