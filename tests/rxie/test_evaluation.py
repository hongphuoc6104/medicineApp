import unittest

from research.rxie.evaluation import (
    parent_accuracy,
    record_exact_match,
    relation_prf,
    strict_entity_prf,
)
from research.rxie.schema import (
    Entity,
    EntityType,
    MedicationRecord,
    ParentAssignment,
    Relation,
    RelationType,
)


class EvaluationTest(unittest.TestCase):
    def test_strict_entity_prf_requires_exact_boundary_and_type(self):
        gold = [Entity("gold", EntityType.DRUG, 0, 11, "Paracetamol")]
        predicted = [Entity("pred", EntityType.DRUG, 0, 10, "Paracetamo")]

        score = strict_entity_prf(gold, predicted)

        self.assertEqual(score.precision, 0.0)
        self.assertEqual(score.recall, 0.0)
        self.assertEqual(score.f1, 0.0)

    def test_relation_prf_uses_parent_attribute_and_relation_type(self):
        gold = [Relation("drug-1", "qty-1", RelationType.HAS_QUANTITY)]
        predicted = [Relation("drug-1", "qty-1", RelationType.HAS_DOSE)]

        self.assertEqual(relation_prf(gold, predicted).f1, 0.0)

    def test_parent_accuracy_scores_explicit_null_assignment(self):
        gold = [ParentAssignment("note-1", None)]
        predicted = [ParentAssignment("note-1", None)]

        self.assertEqual(parent_accuracy(gold, predicted), 1.0)

    def test_record_exact_match_checks_complete_multiset(self):
        gold = [MedicationRecord(drug="Paracetamol", strength="500 mg")]
        predicted = [MedicationRecord(drug="Paracetamol", strength="650 mg")]

        self.assertEqual(record_exact_match(gold, predicted), 0.0)
