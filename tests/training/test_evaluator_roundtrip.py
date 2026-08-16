"""Unit tests for prediction to structured evaluator roundtrip."""

from rxie.evaluation import evaluate_structured_annotations
from rxie.schemas import AnnotationDocumentV2, EntityRelation, EntityType, GoldEntityV2, RelationType


def test_evaluator_predictions_roundtrip():
    gold_doc = AnnotationDocumentV2(
        schema_version="rxie.annotation.v2",
        document_id="doc_val_01",
        prescription_id="RX_001",
        patient_id="PAT_001",
        raw_text="Amlodipine 5mg ngày uống 1 viên",
        entities=[
            GoldEntityV2(
                entity_id="e1",
                type=EntityType.DRUG,
                text="Amlodipine",
                start=0,
                end=10,
                medication_id="RX_001_M01",
            ),
            GoldEntityV2(
                entity_id="e2",
                type=EntityType.STRENGTH,
                text="5mg",
                start=11,
                end=14,
                medication_id="RX_001_M01",
                parent_entity_id="e1",
            ),
            GoldEntityV2(
                entity_id="e3",
                type=EntityType.DOSAGE,
                text="1 viên",
                start=25,
                end=31,
                medication_id="RX_001_M01",
                parent_entity_id="e1",
            ),
        ],
        relations=[
            EntityRelation(head_entity_id="e1", tail_entity_id="e2", relation_type=RelationType.HAS_STRENGTH),
            EntityRelation(head_entity_id="e1", tail_entity_id="e3", relation_type=RelationType.HAS_DOSAGE),
        ],
    )

    pred_doc = gold_doc.model_copy(deep=True)
    report = evaluate_structured_annotations([gold_doc], [pred_doc])

    assert report.entity_micro.f1 == 1.0
    assert report.entity_macro.f1 == 1.0
    assert report.record_exact_match == 1.0
    assert report.parent_accuracy == 1.0
    assert report.prescription_macro_summary["prescription_macro_entity_f1"] == 1.0
