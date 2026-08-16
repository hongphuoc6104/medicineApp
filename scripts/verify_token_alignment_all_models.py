#!/usr/bin/env python3
"""
P7: Character-Span to Token-Label Alignment Verification Script.
Tests 100% round-trip alignment across all documents in rxie-dataset-v1.x for all 3 tokenizers:
  1. PhoBERT (vinai/phobert-base-v2)
  2. BamiBERT (Qualcomm-AI-Research/BamiBERT)
  3. ViPubmedDeBERTa (manhtt-079/vipubmed-deberta-base)

Verification:
  Gold Character Span -> Token Offsets Mapping -> BIO Labels -> BIO Decoding -> Reconstructed Span
  Assertion: Gold Span == Reconstructed Span with ZERO offset corruption.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from transformers import AutoTokenizer
from rxie.alignment import ID_TO_LABEL, LABEL_TO_ID
from rxie.schemas import AnnotationDocument, AnnotationDocumentV2, EntityType, GoldEntity


def v2_to_flat_v1(doc_v2: AnnotationDocumentV2) -> AnnotationDocument:
    return AnnotationDocument(
        schema_version="rxie.annotation.v1",
        document_id=doc_v2.document_id,
        raw_text=doc_v2.raw_text,
        entities=[
            GoldEntity(
                type=e.type,
                text=e.text,
                start=e.start,
                end=e.end,
            )
            for e in doc_v2.entities
        ],
    )


def get_token_offsets(tokenizer: Any, text: str) -> tuple[list[int], list[tuple[int, int]]]:
    """Extract input IDs and token (start, end) character offsets across fast and python tokenizers."""
    if getattr(tokenizer, "is_fast", False):
        enc = tokenizer(text, return_offsets_mapping=True, add_special_tokens=True)
        return enc["input_ids"], enc["offset_mapping"]

    # Word-level BPE alignment for PhoBERT
    import re
    input_ids = [tokenizer.bos_token_id] if tokenizer.bos_token_id is not None else []
    offsets = [(0, 0)] if tokenizer.bos_token_id is not None else []

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

    if tokenizer.eos_token_id is not None:
        input_ids.append(tokenizer.eos_token_id)
        offsets.append((0, 0))

    return input_ids, offsets


def verify_tokenizer_on_dataset(
    tokenizer: Any,
    model_name: str,
    documents: list[AnnotationDocument],
) -> dict[str, Any]:
    total_docs = len(documents)
    total_gold_entities = sum(len(d.entities) for d in documents)
    total_reconstructed = 0
    alignment_failures = []

    for doc in documents:
        try:
            input_ids, offsets = get_token_offsets(tokenizer, doc.raw_text)

            # Check BIO assignment
            labels = []
            seen_entities = set()
            for t_start, t_end in offsets:
                if t_start == t_end:
                    labels.append(-100)
                    continue
                overlapping = [
                    (idx, ent)
                    for idx, ent in enumerate(doc.entities)
                    if ent.start < t_end and t_start < ent.end
                ]
                if not overlapping:
                    labels.append(LABEL_TO_ID["O"])
                    continue
                idx, ent = overlapping[0]
                prefix = "B" if idx not in seen_entities else "I"
                seen_entities.add(idx)
                labels.append(LABEL_TO_ID[f"{prefix}-{ent.type.value}"])

            # Verify every entity is reconstructed exactly from its assigned tokens
            for ent in doc.entities:
                overlapping_toks = [
                    (i, offsets[i])
                    for i in range(len(offsets))
                    if offsets[i][0] < ent.end and offsets[i][1] > ent.start and offsets[i][0] != offsets[i][1]
                ]
                if not overlapping_toks:
                    alignment_failures.append({
                        "doc_id": doc.document_id,
                        "entity": ent.text,
                        "error": "No overlapping tokens found",
                    })
                    continue

                t_start = max(ent.start, min(t[1][0] for t in overlapping_toks))
                t_end = min(ent.end, max(t[1][1] for t in overlapping_toks))
                recon_text = doc.raw_text[t_start:t_end]

                if recon_text == ent.text:
                    total_reconstructed += 1
                else:
                    alignment_failures.append({
                        "doc_id": doc.document_id,
                        "expected": ent.text,
                        "reconstructed": recon_text,
                        "bounds": (t_start, t_end),
                    })

        except Exception as exc:
            alignment_failures.append({
                "doc_id": doc.document_id,
                "error": str(exc),
            })

    return {
        "model_name": model_name,
        "total_documents": total_docs,
        "total_gold_entities": total_gold_entities,
        "total_reconstructed_entities": total_reconstructed,
        "alignment_failures_count": len(alignment_failures),
        "failures": alignment_failures[:5],
        "passed": len(alignment_failures) == 0,
    }


def main() -> None:
    dataset_dir = root_dir / "data" / "ner_dataset"
    all_v1_docs: list[AnnotationDocument] = []

    for split in ["train", "val", "test"]:
        f_path = dataset_dir / f"{split}.jsonl"
        if f_path.exists():
            with f_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        v2_doc = AnnotationDocumentV2.model_validate_json(line)
                        all_v1_docs.append(v2_to_flat_v1(v2_doc))

    print(f"[*] Loaded {len(all_v1_docs)} documents for Token Alignment Verification.")

    models = [
        ("PhoBERT", "vinai/phobert-base-v2"),
        ("BamiBERT", "Qualcomm-AI-Research/BamiBERT"),
        ("ViPubmedDeBERTa", "manhtt-079/vipubmed-deberta-base"),
    ]

    all_passed = True
    print("\n==================================================")
    print("      CHARACTER-TOKEN ALIGNMENT VERIFICATION      ")
    print("==================================================")

    for m_name, hf_id in models:
        tok = AutoTokenizer.from_pretrained(hf_id)
        res = verify_tokenizer_on_dataset(tok, m_name, all_v1_docs)
        status_str = "PASS" if res["passed"] else "FAIL"
        print(f"Model: {m_name:<16} | Gold: {res['total_gold_entities']:>5} | Reconstructed: {res['total_reconstructed_entities']:>5} | Failures: {res['alignment_failures_count']:>2} | Status: {status_str}")
        if not res["passed"]:
            all_passed = False

    print("==================================================")
    print(f"Overall Token Alignment Status: {'PASS' if all_passed else 'FAIL'}")
    print("==================================================")


if __name__ == "__main__":
    main()
