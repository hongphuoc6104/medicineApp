"""Numerical and aggregation contracts for benchmark Token NER metrics."""

import pytest

from rxie.alignment import DEFAULT_ACTIVE_ENTITY_TYPES
from rxie.evaluation import evaluate_structured_annotations
from rxie.schemas import AnnotationDocumentV2, EntityType, GoldEntityV2


def _entity(
    entity_id: str, entity_type: EntityType, start: int, end: int
) -> GoldEntityV2:
    return GoldEntityV2(
        entity_id=entity_id,
        type=entity_type,
        text="x" * (end - start),
        start=start,
        end=end,
    )


def _doc(document_id: str, prescription_id: str, entities: list[GoldEntityV2]):
    return AnnotationDocumentV2(
        schema_version="rxie.annotation.v2",
        document_id=document_id,
        prescription_id=prescription_id,
        raw_text="x" * 120,
        entities=entities,
        relations=[],
    )


def _evaluate(gold, predicted):
    return evaluate_structured_annotations(
        gold,
        predicted,
        active_entity_types=DEFAULT_ACTIVE_ENTITY_TYPES,
        task_type="token_ner",
    )


def test_active_macro_is_exact_mean_of_six_classes_and_ignores_inactive():
    types = list(DEFAULT_ACTIVE_ENTITY_TYPES)
    gold_entities = [
        _entity(f"g{i}", entity_type, i * 10, i * 10 + 2)
        for i, entity_type in enumerate(types)
    ]
    predicted = [
        _entity("p0", types[0], 0, 2),
        _entity("p1", types[1], 10, 12),
        _entity("p3", types[3], 31, 33),
        _entity("p4", types[4], 40, 42),
        _entity("p4-extra", types[4], 42, 44),
        _entity("p5", types[5], 50, 52),
        _entity("inactive", EntityType.FORM, 90, 91),
    ]
    report = _evaluate(
        [_doc("d1", "rx1", gold_entities)],
        [_doc("d1", "rx1", predicted)],
    )

    assert report.entity_macro.f1 == pytest.approx(11 / 18)
    assert set(report.entity_per_class) == set(DEFAULT_ACTIVE_ENTITY_TYPES)
    assert EntityType.FORM not in report.entity_per_class


def test_document_identity_prevents_equal_offsets_from_collapsing():
    gold = [
        _doc("d1", "rx1", [_entity("g1", EntityType.DRUG, 0, 2)]),
        _doc("d2", "rx1", [_entity("g2", EntityType.DRUG, 0, 2)]),
    ]
    predicted = [
        _doc("d2", "rx1", []),
        _doc("d1", "rx1", [_entity("p1", EntityType.DRUG, 0, 2)]),
    ]
    report = _evaluate(gold, predicted)
    assert report.entity_micro.true_positive == 1
    assert report.entity_micro.gold == 2
    assert report.entity_micro.predicted == 1


def test_empty_gold_prescription_is_excluded_and_reported_separately():
    gold = [
        _doc("positive", "rx-positive", [_entity("g1", EntityType.DRUG, 0, 2)]),
        _doc("empty", "rx-empty", []),
    ]
    predicted = [
        _doc("positive", "rx-positive", [_entity("p1", EntityType.DRUG, 0, 2)]),
        _doc("empty", "rx-empty", [_entity("fp", EntityType.DRUG, 5, 7)]),
    ]
    report = _evaluate(gold, predicted)

    assert report.prescription_macro_summary["prescription_macro_entity_f1"] == 1.0
    assert report.prescription_macro_summary["active_gold_prescription_count"] == 1
    assert (
        report.prescription_macro_summary["excluded_empty_gold_prescription_count"] == 1
    )
    assert report.empty_gold_prescription_false_positive == {
        "eligible_unit_count": 1,
        "false_positive_unit_count": 1,
        "rate": 1.0,
    }
    assert report.empty_gold_document_false_positive["rate"] == 1.0
    assert report.parent_accuracy is None
    assert report.relation_micro is None
    assert report.record_exact_match is None


def test_mismatched_document_sets_are_rejected():
    with pytest.raises(ValueError, match="document_id sets"):
        _evaluate([_doc("gold", "rx", [])], [_doc("pred", "rx", [])])
