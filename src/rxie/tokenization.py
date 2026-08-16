"""
Unified Tokenization and Offset Mapping Module for RxIE.
Single Source of Truth across all Tokenizer Audits, Alignment Verification,
Training Dataset Preparation, Release Gate, and Model Inference.
"""

from __future__ import annotations

import re
from typing import Any


def tokenize_with_offsets(
    tokenizer: Any,
    text: str,
    *,
    add_special_tokens: bool = False,
) -> tuple[list[int], list[tuple[int, int]]]:
    """
    Extract token IDs and character offsets across fast and Python tokenizers.
    Special tokens (BOS, EOS, CLS, SEP) receive offset (0, 0). Training
    window construction uses ``add_special_tokens=False`` and adds a valid
    special-token envelope independently to every content window.
    Every text token receives its exact [start, end) character range in `text`.
    """
    if getattr(tokenizer, "is_fast", False):
        enc = tokenizer(
            text,
            return_offsets_mapping=True,
            add_special_tokens=add_special_tokens,
        )
        return enc["input_ids"], enc["offset_mapping"]

    # Python / Word-level BPE Tokenizer (e.g. vinai/phobert-base-v2)
    input_ids: list[int] = []
    offsets: list[tuple[int, int]] = []

    if add_special_tokens and getattr(tokenizer, "bos_token_id", None) is not None:
        input_ids.append(tokenizer.bos_token_id)
        offsets.append((0, 0))
    elif add_special_tokens and getattr(tokenizer, "cls_token_id", None) is not None:
        input_ids.append(tokenizer.cls_token_id)
        offsets.append((0, 0))

    for m in re.finditer(r"\S+", text):
        w_text = m.group(0)
        w_start, w_end = m.start(), m.end()
        sub_tokens = tokenizer.tokenize(w_text)
        sub_ids = tokenizer.convert_tokens_to_ids(sub_tokens)

        cur = w_start
        for st, sid in zip(sub_tokens, sub_ids, strict=True):
            clean = st.replace("@@", "").replace("_", "")
            idx = text.lower().find(clean.lower(), cur)
            if idx != -1 and idx < w_end:
                offsets.append((idx, idx + len(clean)))
                cur = idx + len(clean)
            else:
                offsets.append((cur, w_end))
                cur = w_end
            input_ids.append(sid)

    if add_special_tokens and getattr(tokenizer, "eos_token_id", None) is not None:
        input_ids.append(tokenizer.eos_token_id)
        offsets.append((0, 0))
    elif add_special_tokens and getattr(tokenizer, "sep_token_id", None) is not None:
        input_ids.append(tokenizer.sep_token_id)
        offsets.append((0, 0))

    return input_ids, offsets


def count_document_tokens(tokenizer: Any, text: str) -> int:
    """Return the total number of tokens (including special tokens) for a given text."""
    input_ids, _ = tokenize_with_offsets(tokenizer, text, add_special_tokens=True)
    return len(input_ids)
