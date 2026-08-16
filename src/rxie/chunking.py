"""
Sliding window chunking, token windowing, and long-document reconstruction policy.

Policies:
  1. Token-Level Sliding Window Policy (Model Training / Inference):
     - ``max_input_tokens`` includes model special tokens.
     - Content is windowed before each window receives its own special tokens.
     - Multi-window documents are fully covered; 0 silent truncation.
     - Overlap logits are merged by global token index before BIO decoding.

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
    EntityType,
    GoldEntity,
    GoldEntityV2,
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
    global_token_indices: list[int | None]


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
    """Verify every source gold entity appears in at least one chunk."""
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
    tokenizer: Any,
    max_input_tokens: int = 256,
    content_overlap: int = 64,
    mask_overlap_for_training: bool = False,
    entity_token_ranges: list[tuple[int, int]] | None = None,
) -> list[TokenWindow]:
    """Build independently valid model inputs from content-only tokenization.

    ``max_input_tokens`` is the final model input capacity, including special
    tokens. During training every global content token has exactly one loss
    owner. Tokens belonging to one gold entity are assigned to the same owner
    window so overlap masking cannot split BIO supervision.
    """
    if not (len(input_ids) == len(offsets) == len(labels)):
        raise ValueError("input_ids, offsets, and labels must have equal lengths")

    special_count = int(tokenizer.num_special_tokens_to_add(pair=False))
    content_capacity = max_input_tokens - special_count
    if content_capacity <= 0:
        raise ValueError("max_input_tokens must leave room for content tokens")
    if content_overlap < 0 or content_overlap >= content_capacity:
        raise ValueError("content_overlap must satisfy 0 <= overlap < content capacity")

    total_tokens = len(input_ids)
    step = content_capacity - content_overlap
    starts = [0]
    while starts[-1] + content_capacity < total_tokens:
        starts.append(starts[-1] + step)
    ranges = [(start, min(total_tokens, start + content_capacity)) for start in starts]

    owner_by_token: dict[int, int] = {}
    if mask_overlap_for_training:
        for token_idx in range(total_tokens):
            candidates = [
                (min(token_idx - start, end - 1 - token_idx), -window_idx, window_idx)
                for window_idx, (start, end) in enumerate(ranges)
                if start <= token_idx < end
            ]
            owner_by_token[token_idx] = max(candidates)[2]

        for entity_start, entity_end in entity_token_ranges or []:
            if not (0 <= entity_start < entity_end <= total_tokens):
                raise ValueError(
                    f"Invalid entity token range: {(entity_start, entity_end)}"
                )
            candidates = [
                (min(entity_start - start, end - entity_end), -window_idx, window_idx)
                for window_idx, (start, end) in enumerate(ranges)
                if start <= entity_start and entity_end <= end
            ]
            if not candidates:
                raise ValueError(
                    f"Gold entity range {(entity_start, entity_end)} is not "
                    "enclosed by any content window"
                )
            entity_owner = max(candidates)[2]
            for token_idx in range(entity_start, entity_end):
                owner_by_token[token_idx] = entity_owner

    windows: list[TokenWindow] = []
    for window_idx, (start, end) in enumerate(ranges):
        content_ids = list(input_ids[start:end])
        window_ids = list(tokenizer.build_inputs_with_special_tokens(content_ids))
        if content_ids:
            content_positions = [
                index
                for index in range(len(window_ids) - len(content_ids) + 1)
                if window_ids[index : index + len(content_ids)] == content_ids
            ]
            if len(content_positions) != 1:
                raise ValueError(
                    "Content tokens are not a unique contiguous model-input subsequence"
                )
            content_position = content_positions[0]
        else:
            content_position = 0
        special_mask = [1] * len(window_ids)
        special_mask[content_position : content_position + len(content_ids)] = [
            0
        ] * len(content_ids)
        if len(window_ids) != len(special_mask) or len(window_ids) > max_input_tokens:
            raise ValueError("Tokenizer produced an invalid special-token window")

        local_offsets: list[tuple[int, int]] = []
        local_labels: list[int] = []
        global_indices: list[int | None] = []
        content_pos = 0
        for is_special in special_mask:
            if is_special:
                local_offsets.append((0, 0))
                local_labels.append(-100)
                global_indices.append(None)
                continue

            global_idx = start + content_pos
            local_offsets.append(offsets[global_idx])
            global_indices.append(global_idx)
            if mask_overlap_for_training and owner_by_token[global_idx] != window_idx:
                local_labels.append(-100)
            else:
                local_labels.append(labels[global_idx])
            content_pos += 1

        if content_pos != len(content_ids):
            raise ValueError("Special-token mask did not preserve every content token")

        windows.append(
            TokenWindow(
                window_idx=window_idx,
                total_windows=len(ranges),
                token_start=start,
                token_end=end,
                input_ids=window_ids,
                attention_mask=[1] * len(window_ids),
                labels=local_labels,
                offsets=local_offsets,
                global_token_indices=global_indices,
            )
        )

    return windows


def merge_window_logits(
    windows: list[TokenWindow],
    window_logits: list[list[list[float]]],
) -> tuple[list[list[float]], list[tuple[int, int]]]:
    """Select center-most logits for each global content token."""
    if len(windows) != len(window_logits):
        raise ValueError("windows and window_logits must have equal lengths")
    if windows:
        declared_total = windows[0].total_windows
        if any(window.total_windows != declared_total for window in windows):
            raise ValueError("Windows disagree about total_windows")
        if {window.window_idx for window in windows} != set(range(declared_total)):
            raise ValueError(
                "Global-token logit merge requires every declared window exactly once"
            )

    selected: dict[int, tuple[tuple[int, int], list[float], tuple[int, int]]] = {}
    for window, logits in zip(windows, window_logits, strict=True):
        if len(logits) != len(window.input_ids):
            raise ValueError("Each logit sequence must match its window input length")
        for local_idx, global_idx in enumerate(window.global_token_indices):
            if global_idx is None:
                continue
            score = (
                min(global_idx - window.token_start, window.token_end - 1 - global_idx),
                -window.window_idx,
            )
            current = selected.get(global_idx)
            if current is None or score > current[0]:
                selected[global_idx] = (
                    score,
                    list(logits[local_idx]),
                    window.offsets[local_idx],
                )

    if not selected:
        return [], []
    expected = set(range(max(window.token_end for window in windows)))
    if set(selected) != expected:
        raise ValueError("Global-token logit merge found missing token indices")

    return (
        [selected[idx][1] for idx in range(len(expected))],
        [selected[idx][2] for idx in range(len(expected))],
    )


def decode_windows_to_document(
    source_doc: AnnotationDocumentV2,
    windows: list[TokenWindow],
    window_logits: list[list[list[float]]],
    id_to_label: dict[int, str],
) -> AnnotationDocumentV2:
    """Merge overlap logits globally, then decode one BIO sequence."""
    raw_text = source_doc.raw_text
    extracted_entities: list[GoldEntityV2] = []
    global_logits, offsets = merge_window_logits(windows, window_logits)
    predictions = [max(range(len(row)), key=row.__getitem__) for row in global_logits]

    current_type: EntityType | None = None
    current_start = 0
    current_end = 0

    def flush() -> None:
        nonlocal current_type, current_start, current_end
        if current_type is not None and current_start < current_end:
            extracted_entities.append(
                GoldEntityV2(
                    entity_id=f"e_{len(extracted_entities) + 1}",
                    type=current_type,
                    text=raw_text[current_start:current_end],
                    start=current_start,
                    end=current_end,
                    parent_entity_id=None,
                )
            )
        current_type = None

    for label_id, (token_start, token_end) in zip(predictions, offsets, strict=True):
        tag = id_to_label.get(label_id, "O")
        if tag.startswith("B-"):
            flush()
            current_type = EntityType(tag[2:])
            current_start, current_end = token_start, token_end
        elif tag.startswith("I-") and current_type == EntityType(tag[2:]):
            current_end = token_end
        elif tag.startswith("I-"):
            flush()
            current_type = EntityType(tag[2:])
            current_start, current_end = token_start, token_end
        else:
            flush()
    flush()

    return AnnotationDocumentV2(
        schema_version="rxie.annotation.v2",
        document_id=source_doc.document_id,
        prescription_id=source_doc.prescription_id,
        patient_id=source_doc.patient_id,
        raw_text=raw_text,
        entities=extracted_entities,
        relations=[],
    )
