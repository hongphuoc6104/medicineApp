import unittest

from research.rxie.schema import (
    Entity,
    EntityType,
    MedicationRecord,
    OcrBlock,
    ParentAssignment,
    PrescriptionDocument,
    Relation,
    RelationType,
)


def _document(parent_id="drug-1", relation_type=RelationType.HAS_STRENGTH):
    raw_text = "Paracetamol 500 mg"
    return PrescriptionDocument(
        document_id="rx-1",
        raw_text=raw_text,
        ocr_engine="fixture",
        ocr_blocks=(
            OcrBlock(
                region_id="region-1",
                text=raw_text,
                confidence=0.9,
                reading_order=0,
                bbox=((0, 0), (100, 0), (100, 20), (0, 20)),
            ),
        ),
        entities=(
            Entity(
                "drug-1",
                EntityType.DRUG,
                0,
                11,
                "Paracetamol",
                source_region_ids=("region-1",),
            ),
            Entity(
                "strength-1",
                EntityType.STRENGTH,
                12,
                18,
                "500 mg",
                source_region_ids=("region-1",),
            ),
        ),
        parent_assignments=(ParentAssignment("strength-1", parent_id),),
        relations=(
            (Relation("drug-1", "strength-1", relation_type),)
            if parent_id is not None
            else ()
        ),
        records=(MedicationRecord(drug="Paracetamol", strength="500 mg"),),
    )


class PrescriptionDocumentTest(unittest.TestCase):
    def test_accepts_valid_structured_annotation(self):
        document = _document()

        self.assertEqual(document.parent_assignments[0].drug_id, "drug-1")
        self.assertEqual(document.records[0].strength, "500 mg")

    def test_supports_explicit_null_parent(self):
        document = _document(parent_id=None)

        self.assertIsNone(document.parent_assignments[0].drug_id)

    def test_rejects_relation_type_that_conflicts_with_attribute(self):
        with self.assertRaisesRegex(ValueError, "conflicts"):
            _document(relation_type=RelationType.HAS_QUANTITY)

    def test_rejects_unknown_source_region(self):
        document = _document()
        invalid_entity = Entity(
            "drug-2",
            EntityType.DRUG,
            0,
            11,
            "Paracetamol",
            source_region_ids=("missing-region",),
        )

        with self.assertRaisesRegex(ValueError, "unknown OCR regions"):
            PrescriptionDocument(
                document_id=document.document_id,
                raw_text=document.raw_text,
                ocr_engine=document.ocr_engine,
                ocr_blocks=document.ocr_blocks,
                entities=(invalid_entity,),
                parent_assignments=(),
                relations=(),
                records=(),
            )
