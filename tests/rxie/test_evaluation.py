from rxie.evaluation import strict_entity_evaluation
from rxie.schemas import Entity, EntityType


def entity(entity_type, start, end, text="x"):
    return Entity(
        type=entity_type,
        text=text,
        start=start,
        end=end,
        confidence=1,
        source_region_ids=["r1"],
    )


def test_strict_scores_require_exact_type_and_boundaries():
    gold = [entity(EntityType.DRUG, 0, 11, "Paracetamol")]
    predicted = [entity(EntityType.DRUG, 0, 10, "Paracetamo")]

    result = strict_entity_evaluation(gold, predicted)

    assert result.overall.f1 == 0
    assert result.per_class[EntityType.DRUG].predicted == 1
    assert result.per_class[EntityType.STRENGTH].f1 == 1


def test_reports_micro_and_per_class_scores():
    drug = entity(EntityType.DRUG, 0, 11, "Paracetamol")
    strength = entity(EntityType.STRENGTH, 12, 18, "500 mg")

    result = strict_entity_evaluation([drug, strength], [drug])

    assert result.overall.precision == 1
    assert result.overall.recall == 0.5
    assert result.overall.f1 == 2 / 3
    assert result.per_class[EntityType.DRUG].f1 == 1
    assert result.per_class[EntityType.STRENGTH].f1 == 0
