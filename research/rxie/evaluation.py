"""Deterministic RxIE metrics used by all model ablations."""

from collections import Counter
from dataclasses import astuple, dataclass
from typing import Iterable

from .schema import Entity, MedicationRecord, ParentAssignment, Relation


@dataclass(frozen=True)
class PrfScore:
    precision: float
    recall: float
    f1: float
    true_positive: int
    predicted: int
    gold: int


def _prf(gold: set[tuple], predicted: set[tuple]) -> PrfScore:
    true_positive = len(gold & predicted)
    precision = true_positive / len(predicted) if predicted else float(not gold)
    recall = true_positive / len(gold) if gold else float(not predicted)
    denominator = precision + recall
    f1 = 2 * precision * recall / denominator if denominator else 0.0
    return PrfScore(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positive=true_positive,
        predicted=len(predicted),
        gold=len(gold),
    )


def strict_entity_prf(
    gold: Iterable[Entity], predicted: Iterable[Entity]
) -> PrfScore:
    """Match entities only when both span boundary and type are exact."""
    gold_keys = {(item.entity_type, item.start, item.end) for item in gold}
    predicted_keys = {
        (item.entity_type, item.start, item.end) for item in predicted
    }
    return _prf(gold_keys, predicted_keys)


def relation_prf(
    gold: Iterable[Relation], predicted: Iterable[Relation]
) -> PrfScore:
    gold_keys = {
        (item.drug_id, item.attribute_id, item.relation_type) for item in gold
    }
    predicted_keys = {
        (item.drug_id, item.attribute_id, item.relation_type)
        for item in predicted
    }
    return _prf(gold_keys, predicted_keys)


def parent_accuracy(
    gold: Iterable[ParentAssignment], predicted: Iterable[ParentAssignment]
) -> float:
    """Measure parent choice over gold attributes, including explicit NULL."""
    gold_map = {item.attribute_id: item.drug_id for item in gold}
    predicted_map = {item.attribute_id: item.drug_id for item in predicted}
    if not gold_map:
        return float(not predicted_map)
    correct = sum(
        predicted_map.get(attribute_id) == drug_id
        for attribute_id, drug_id in gold_map.items()
    )
    return correct / len(gold_map)


def record_exact_match(
    gold: Iterable[MedicationRecord], predicted: Iterable[MedicationRecord]
) -> float:
    """Return one only when the complete medication-record multiset matches."""
    gold_records = Counter(astuple(record) for record in gold)
    predicted_records = Counter(astuple(record) for record in predicted)
    return float(gold_records == predicted_records)
