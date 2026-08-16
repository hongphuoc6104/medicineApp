"""Benchmark-contract tests for token windows, loss ownership, and logit merge."""

from rxie.chunking import (
    create_token_sliding_windows,
    decode_windows_to_document,
    merge_window_logits,
)
from rxie.schemas import AnnotationDocumentV2


class FakeTokenizer:
    bos_token_id = 101
    eos_token_id = 102

    def num_special_tokens_to_add(self, pair: bool = False) -> int:
        assert pair is False
        return 2

    def build_inputs_with_special_tokens(self, token_ids: list[int]) -> list[int]:
        return [self.bos_token_id, *token_ids, self.eos_token_id]

    def get_special_tokens_mask(
        self,
        token_ids: list[int],
        already_has_special_tokens: bool = False,
    ) -> list[int]:
        assert already_has_special_tokens is False
        return [1, *([0] * len(token_ids)), 1]


def _windows(*, training: bool):
    tokenizer = FakeTokenizer()
    token_count = 20
    labels = [0] * token_count
    labels[6] = 1
    labels[7:10] = [2, 2, 2]
    return create_token_sliding_windows(
        input_ids=list(range(1000, 1000 + token_count)),
        offsets=[(i, i + 1) for i in range(token_count)],
        labels=labels,
        tokenizer=tokenizer,
        max_input_tokens=10,
        content_overlap=4,
        mask_overlap_for_training=training,
        entity_token_ranges=[(6, 10)],
    )


def test_each_window_has_special_tokens_and_respects_total_capacity():
    windows = _windows(training=False)
    assert len(windows) > 2
    for window in windows:
        assert window.input_ids[0] == FakeTokenizer.bos_token_id
        assert window.input_ids[-1] == FakeTokenizer.eos_token_id
        assert window.labels[0] == window.labels[-1] == -100
        assert window.offsets[0] == window.offsets[-1] == (0, 0)
        assert window.global_token_indices[0] is None
        assert window.global_token_indices[-1] is None
        assert len(window.input_ids) <= 10


def test_every_global_token_contributes_loss_once():
    windows = _windows(training=True)
    supervised_count = {idx: 0 for idx in range(20)}
    for window in windows:
        for global_idx, label in zip(
            window.global_token_indices, window.labels, strict=True
        ):
            if global_idx is not None and label != -100:
                supervised_count[global_idx] += 1
    assert set(supervised_count.values()) == {1}


def test_entity_boundary_survives_overlap_masking():
    windows = _windows(training=True)
    owners = []
    owned_labels = []
    for window in windows:
        entity_labels = []
        for global_idx, label in zip(
            window.global_token_indices, window.labels, strict=True
        ):
            if global_idx is not None and 6 <= global_idx < 10 and label != -100:
                entity_labels.append(label)
        if entity_labels:
            owners.append(window.window_idx)
            owned_labels = entity_labels
    assert owners == [1]
    assert owned_labels == [1, 2, 2, 2]


def test_global_logit_merge_is_center_based_and_window_order_independent():
    windows = _windows(training=False)
    logits = []
    for window in windows:
        rows = []
        for global_idx in window.global_token_indices:
            rows.append([5.0, 0.0, 0.0] if global_idx is not None else [5.0, 0.0, 0.0])
        logits.append(rows)

    # Token 6 occurs in two windows. Window 1 is more central and must win.
    for window, rows in zip(windows, logits, strict=True):
        for local_idx, global_idx in enumerate(window.global_token_indices):
            if global_idx == 6:
                rows[local_idx] = (
                    [0.0, 9.0, 0.0] if window.window_idx == 1 else [9.0, 0.0, 0.0]
                )
            elif global_idx in {7, 8, 9}:
                rows[local_idx] = [0.0, 0.0, 9.0]

    merged, _ = merge_window_logits(windows, logits)
    reversed_merged, _ = merge_window_logits(
        list(reversed(windows)), list(reversed(logits))
    )
    assert merged == reversed_merged
    assert max(range(3), key=merged[6].__getitem__) == 1

    doc = AnnotationDocumentV2(
        schema_version="rxie.annotation.v2",
        document_id="doc-1",
        prescription_id="rx-1",
        raw_text="abcdefghijklmnopqrst",
        entities=[],
        relations=[],
    )
    decoded = decode_windows_to_document(
        doc,
        windows,
        logits,
        {0: "O", 1: "B-DRUG", 2: "I-DRUG"},
    )
    assert [(e.type.value, e.start, e.end, e.text) for e in decoded.entities] == [
        ("DRUG", 6, 10, "ghij")
    ]
    assert decoded.relations == []
    assert decoded.entities[0].parent_entity_id is None


def test_invalid_overlap_is_rejected():
    tokenizer = FakeTokenizer()
    try:
        create_token_sliding_windows(
            [1],
            [(0, 1)],
            [0],
            tokenizer,
            max_input_tokens=10,
            content_overlap=8,
        )
    except ValueError as exc:
        assert "content_overlap" in str(exc)
    else:
        raise AssertionError("Invalid overlap must be rejected")


def test_merge_rejects_missing_declared_window():
    windows = _windows(training=False)
    logits = [[[1.0, 0.0, 0.0] for _ in window.input_ids] for window in windows[:-1]]
    try:
        merge_window_logits(windows[:-1], logits)
    except ValueError as exc:
        assert "every declared window" in str(exc)
    else:
        raise AssertionError("A truncated window cohort must not decode")


def test_empty_content_builds_a_special_token_only_window():
    windows = create_token_sliding_windows(
        [],
        [],
        [],
        FakeTokenizer(),
        max_input_tokens=10,
        content_overlap=4,
    )
    assert windows[0].input_ids == [101, 102]
    assert windows[0].labels == [-100, -100]
    assert windows[0].global_token_indices == [None, None]
