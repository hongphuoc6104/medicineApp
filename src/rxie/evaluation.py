"""Strict entity-level evaluation for the ten supported classes."""

from collections.abc import Iterable
from dataclasses import dataclass

from .schemas import Entity, EntityType


@dataclass(frozen=True)
class PrfScore:
    precision: float
    recall: float
    f1: float
    true_positive: int
    predicted: int
    gold: int


@dataclass(frozen=True)
class EntityEvaluation:
    overall: PrfScore
    per_class: dict[EntityType, PrfScore]


def _score(gold: set[tuple], predicted: set[tuple]) -> PrfScore:
    true_positive = len(gold & predicted)
    precision = true_positive / len(predicted) if predicted else float(not gold)
    recall = true_positive / len(gold) if gold else float(not predicted)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PrfScore(precision, recall, f1, true_positive, len(predicted), len(gold))


def strict_entity_evaluation(
    gold: Iterable[Entity], predicted: Iterable[Entity]
) -> EntityEvaluation:
    """Micro and per-class exact type/start/end scores."""
    gold_keys = {(item.type, item.start, item.end) for item in gold}
    predicted_keys = {(item.type, item.start, item.end) for item in predicted}
    per_class = {
        entity_type: _score(
            {key for key in gold_keys if key[0] == entity_type},
            {key for key in predicted_keys if key[0] == entity_type},
        )
        for entity_type in EntityType
    }
    return EntityEvaluation(_score(gold_keys, predicted_keys), per_class)


def strict_entity_prf(gold: Iterable[Entity], predicted: Iterable[Entity]) -> PrfScore:
    return strict_entity_evaluation(gold, predicted).overall
