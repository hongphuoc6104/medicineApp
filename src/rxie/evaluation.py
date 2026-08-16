"""Strict entity-level, relation, record, and dual-level structured evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

from .alignment import DEFAULT_ACTIVE_ENTITY_TYPES
from .schemas import (
    AnnotationDocumentV2,
    Entity,
    EntityType,
    GoldEntityV2,
    RelationType,
)


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
    macro: PrfScore
    per_class: dict[EntityType, PrfScore]


@dataclass(frozen=True)
class RelationEvaluation:
    parent_accuracy: float
    relation_micro: PrfScore
    relation_macro: PrfScore
    per_type: dict[RelationType, PrfScore]


@dataclass(frozen=True)
class RecordEvaluation:
    record_exact_match: float
    record_tuple_prf: PrfScore
    document_exact_match: float
    total_gold_records: int
    total_predicted_records: int
    exact_matched_records: int


@dataclass(frozen=True)
class StructuredEvaluationReport:
    schema_version: str
    task_type: str
    active_entity_types: tuple[EntityType, ...]
    entity_micro: PrfScore
    entity_macro: PrfScore
    entity_per_class: dict[EntityType, PrfScore]
    parent_accuracy: float | None
    relation_micro: PrfScore | None
    relation_macro: PrfScore | None
    relation_per_type: dict[RelationType, PrfScore] | None
    record_exact_match: float | None
    record_tuple_prf: PrfScore | None
    document_exact_match: float | None
    prescription_macro_summary: dict[str, Any]
    prescription_breakdown: dict[str, dict[str, Any]]
    empty_gold_document_false_positive: dict[str, Any]
    empty_gold_prescription_false_positive: dict[str, Any]

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_type": self.task_type,
            "active_entity_types": [
                entity_type.value for entity_type in self.active_entity_types
            ],
            "entity_micro": self.entity_micro.__dict__,
            "entity_macro": self.entity_macro.__dict__,
            "entity_per_class": {
                k.value: v.__dict__ for k, v in self.entity_per_class.items()
            },
            "parent_accuracy": self.parent_accuracy,
            "relation_micro": self.relation_micro.__dict__
            if self.relation_micro
            else None,
            "relation_macro": self.relation_macro.__dict__
            if self.relation_macro
            else None,
            "relation_per_type": (
                {k.value: v.__dict__ for k, v in self.relation_per_type.items()}
                if self.relation_per_type is not None
                else None
            ),
            "record_exact_match": self.record_exact_match,
            "record_tuple_prf": self.record_tuple_prf.__dict__
            if self.record_tuple_prf
            else None,
            "document_exact_match": self.document_exact_match,
            "prescription_macro_summary": self.prescription_macro_summary,
            "prescription_breakdown": self.prescription_breakdown,
            "empty_gold_document_false_positive": (
                self.empty_gold_document_false_positive
            ),
            "empty_gold_prescription_false_positive": (
                self.empty_gold_prescription_false_positive
            ),
        }


def _calc_prf(tp: int, pred: int, gold: int) -> PrfScore:
    precision = tp / pred if pred else 0.0
    recall = tp / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PrfScore(precision, recall, f1, tp, pred, gold)


def _normalize_active_types(
    active_entity_types: Iterable[EntityType | str],
) -> tuple[EntityType, ...]:
    normalized = tuple(
        EntityType(entity_type) if isinstance(entity_type, str) else entity_type
        for entity_type in active_entity_types
    )
    if normalized != tuple(DEFAULT_ACTIVE_ENTITY_TYPES):
        expected = [entity_type.value for entity_type in DEFAULT_ACTIVE_ENTITY_TYPES]
        raise ValueError(f"Token NER active entity types must be exactly {expected}")
    return normalized


def evaluate_strict_entities(
    gold_entities: list[GoldEntityV2] | list[Entity] | Iterable[Any],
    pred_entities: list[GoldEntityV2] | list[Entity] | Iterable[Any],
    active_entity_types: Iterable[EntityType | str] | None = None,
) -> EntityEvaluation:
    gold_keys = {(e.type, e.start, e.end) for e in gold_entities}
    pred_keys = {(e.type, e.start, e.end) for e in pred_entities}

    if active_entity_types is not None:
        target_types = {
            EntityType(t) if isinstance(t, str) else t for t in active_entity_types
        }
        eval_gold_keys = {k for k in gold_keys if k[0] in target_types}
        eval_pred_keys = {k for k in pred_keys if k[0] in target_types}
    else:
        target_types = set(EntityType)
        eval_gold_keys = gold_keys
        eval_pred_keys = pred_keys

    overall_tp = len(eval_gold_keys & eval_pred_keys)
    overall_prf = _calc_prf(overall_tp, len(eval_pred_keys), len(eval_gold_keys))

    per_class: dict[EntityType, PrfScore] = {}
    f1_list: list[float] = []
    p_list: list[float] = []
    r_list: list[float] = []

    for ent_type in EntityType:
        g_c = {k for k in gold_keys if k[0] == ent_type}
        p_c = {k for k in pred_keys if k[0] == ent_type}
        score = _calc_prf(len(g_c & p_c), len(p_c), len(g_c))
        if ent_type in target_types:
            per_class[ent_type] = score
            f1_list.append(score.f1)
            p_list.append(score.precision)
            r_list.append(score.recall)

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0
    macro_p = sum(p_list) / len(p_list) if p_list else 0.0
    macro_r = sum(r_list) / len(r_list) if r_list else 0.0
    macro_prf = PrfScore(
        macro_p, macro_r, macro_f1, overall_tp, len(eval_pred_keys), len(eval_gold_keys)
    )

    return EntityEvaluation(overall=overall_prf, macro=macro_prf, per_class=per_class)


# Backwards-compatible aliases
strict_entity_evaluation = evaluate_strict_entities


def strict_entity_prf(gold: Iterable[Entity], predicted: Iterable[Entity]) -> PrfScore:
    return evaluate_strict_entities(list(gold), list(predicted)).overall


def evaluate_relations(
    gold_doc: AnnotationDocumentV2,
    pred_doc: AnnotationDocumentV2,
) -> RelationEvaluation:
    gold_map = {e.entity_id: e for e in gold_doc.entities}
    pred_map = {e.entity_id: e for e in pred_doc.entities}

    gold_attrs = [e for e in gold_doc.entities if e.type != EntityType.DRUG]
    correct_parent_count = 0

    for ga in gold_attrs:
        matching_pred = next(
            (
                pe
                for pe in pred_doc.entities
                if pe.type == ga.type and pe.start == ga.start and pe.end == ga.end
            ),
            None,
        )
        if matching_pred is not None:
            gold_parent_span = None
            if ga.parent_entity_id and ga.parent_entity_id in gold_map:
                gp = gold_map[ga.parent_entity_id]
                gold_parent_span = (gp.type, gp.start, gp.end)

            pred_parent_span = None
            if (
                matching_pred.parent_entity_id
                and matching_pred.parent_entity_id in pred_map
            ):
                pp = pred_map[matching_pred.parent_entity_id]
                pred_parent_span = (pp.type, pp.start, pp.end)

            if gold_parent_span == pred_parent_span:
                correct_parent_count += 1

    parent_accuracy = correct_parent_count / len(gold_attrs) if gold_attrs else 1.0

    def extract_triples(doc: AnnotationDocumentV2) -> set[tuple]:
        emap = {e.entity_id: e for e in doc.entities}
        triples = set()
        for r in doc.relations:
            if r.head_entity_id in emap and r.tail_entity_id in emap:
                h = emap[r.head_entity_id]
                t = emap[r.tail_entity_id]
                triples.add(
                    (
                        (h.type, h.start, h.end),
                        (t.type, t.start, t.end),
                        r.relation_type,
                    )
                )
        return triples

    gold_triples = extract_triples(gold_doc)
    pred_triples = extract_triples(pred_doc)

    tp = len(gold_triples & pred_triples)
    micro_prf = _calc_prf(tp, len(pred_triples), len(gold_triples))

    per_type: dict[RelationType, PrfScore] = {}
    f1_list: list[float] = []

    for r_type in RelationType:
        gt_c = {t for t in gold_triples if t[2] == r_type}
        pt_c = {t for t in pred_triples if t[2] == r_type}
        score = _calc_prf(len(gt_c & pt_c), len(pt_c), len(gt_c))
        per_type[r_type] = score
        f1_list.append(score.f1)

    macro_prf = PrfScore(
        precision=sum(s.precision for s in per_type.values()) / len(per_type),
        recall=sum(s.recall for s in per_type.values()) / len(per_type),
        f1=sum(f1_list) / len(f1_list),
        true_positive=tp,
        predicted=len(pred_triples),
        gold=len(gold_triples),
    )

    return RelationEvaluation(
        parent_accuracy=parent_accuracy,
        relation_micro=micro_prf,
        relation_macro=macro_prf,
        per_type=per_type,
    )


def evaluate_records(
    gold_docs: list[AnnotationDocumentV2],
    pred_docs: list[AnnotationDocumentV2],
) -> RecordEvaluation:
    total_gold_records = 0
    total_pred_records = 0
    exact_matched_records = 0
    doc_em_count = 0

    gold_tuples_all: set[tuple] = set()
    pred_tuples_all: set[tuple] = set()

    for g_doc, p_doc in zip(gold_docs, pred_docs, strict=False):
        g_drugs = [e for e in g_doc.entities if e.type == EntityType.DRUG]
        p_drugs = [e for e in p_doc.entities if e.type == EntityType.DRUG]

        total_gold_records += len(g_drugs)
        total_pred_records += len(p_drugs)

        g_records: list[tuple[tuple, frozenset[tuple]]] = []
        for gd in g_drugs:
            attrs = frozenset(
                (e.type, e.start, e.end)
                for e in g_doc.entities
                if e.parent_entity_id == gd.entity_id
            )
            g_records.append(((gd.type, gd.start, gd.end), attrs))
            for a in attrs:
                gold_tuples_all.add(
                    ((g_doc.document_id, (gd.type, gd.start, gd.end)), a)
                )

        p_records: list[tuple[tuple, frozenset[tuple]]] = []
        for pd in p_drugs:
            attrs = frozenset(
                (e.type, e.start, e.end)
                for e in p_doc.entities
                if e.parent_entity_id == pd.entity_id
            )
            p_records.append(((pd.type, pd.start, pd.end), attrs))
            for a in attrs:
                pred_tuples_all.add(
                    ((p_doc.document_id, (pd.type, pd.start, pd.end)), a)
                )

        matched_in_doc = 0
        for gr in g_records:
            if gr in p_records:
                exact_matched_records += 1
                matched_in_doc += 1

        if (
            len(g_records) > 0
            and matched_in_doc == len(g_records)
            and len(p_records) == len(g_records)
        ):
            doc_em_count += 1
        elif len(g_records) == 0 and len(p_records) == 0:
            doc_em_count += 1

    record_em = (
        exact_matched_records / total_gold_records if total_gold_records else 1.0
    )
    doc_em = doc_em_count / len(gold_docs) if gold_docs else 1.0

    tuple_tp = len(gold_tuples_all & pred_tuples_all)
    tuple_prf = _calc_prf(tuple_tp, len(pred_tuples_all), len(gold_tuples_all))

    return RecordEvaluation(
        record_exact_match=record_em,
        record_tuple_prf=tuple_prf,
        document_exact_match=doc_em,
        total_gold_records=total_gold_records,
        total_predicted_records=total_pred_records,
        exact_matched_records=exact_matched_records,
    )


def evaluate_dual_level(
    gold_docs: list[AnnotationDocumentV2],
    pred_docs: list[AnnotationDocumentV2],
    active_entity_types: Iterable[EntityType | str] = DEFAULT_ACTIVE_ENTITY_TYPES,
    *,
    task_type: Literal["token_ner", "structured_extraction"] = "structured_extraction",
) -> StructuredEvaluationReport:
    active_types = _normalize_active_types(active_entity_types)
    gold_by_id = {doc.document_id: doc for doc in gold_docs}
    pred_by_id = {doc.document_id: doc for doc in pred_docs}
    if len(gold_by_id) != len(gold_docs) or len(pred_by_id) != len(pred_docs):
        raise ValueError("Duplicate document_id in evaluation input")
    if set(gold_by_id) != set(pred_by_id):
        raise ValueError("Gold and prediction document_id sets must match exactly")

    paired_docs = []
    for document_id in sorted(gold_by_id):
        gold_doc = gold_by_id[document_id]
        pred_doc = pred_by_id[document_id]
        if gold_doc.prescription_id != pred_doc.prescription_id:
            raise ValueError(f"Prescription mismatch for document {document_id}")
        if not gold_doc.prescription_id:
            raise ValueError(f"Missing prescription_id for document {document_id}")
        paired_docs.append((gold_doc, pred_doc))

    def entity_keys(
        docs: Iterable[AnnotationDocumentV2],
        entity_type: EntityType | None = None,
    ) -> set[tuple[str, EntityType, int, int]]:
        return {
            (doc.document_id, entity.type, entity.start, entity.end)
            for doc in docs
            for entity in doc.entities
            if entity.type in active_types
            and (entity_type is None or entity.type == entity_type)
        }

    def evaluate_docs(
        scoped_gold: list[AnnotationDocumentV2],
        scoped_pred: list[AnnotationDocumentV2],
    ) -> EntityEvaluation:
        gold_keys = entity_keys(scoped_gold)
        pred_keys = entity_keys(scoped_pred)
        overall = _calc_prf(len(gold_keys & pred_keys), len(pred_keys), len(gold_keys))
        per_class = {}
        for entity_type in active_types:
            gold_class = entity_keys(scoped_gold, entity_type)
            pred_class = entity_keys(scoped_pred, entity_type)
            per_class[entity_type] = _calc_prf(
                len(gold_class & pred_class),
                len(pred_class),
                len(gold_class),
            )
        macro = PrfScore(
            precision=sum(score.precision for score in per_class.values())
            / len(active_types),
            recall=sum(score.recall for score in per_class.values())
            / len(active_types),
            f1=sum(score.f1 for score in per_class.values()) / len(active_types),
            true_positive=overall.true_positive,
            predicted=overall.predicted,
            gold=overall.gold,
        )
        return EntityEvaluation(overall=overall, macro=macro, per_class=per_class)

    ordered_gold = [pair[0] for pair in paired_docs]
    ordered_pred = [pair[1] for pair in paired_docs]
    entity_eval = evaluate_docs(ordered_gold, ordered_pred)

    by_rx_gold: dict[str, list[AnnotationDocumentV2]] = defaultdict(list)
    by_rx_pred: dict[str, list[AnnotationDocumentV2]] = defaultdict(list)

    for g, p in paired_docs:
        rx_id = str(g.prescription_id)
        by_rx_gold[rx_id].append(g)
        by_rx_pred[rx_id].append(p)

    rx_breakdown: dict[str, dict[str, Any]] = {}
    rx_f1s: list[float] = []
    empty_rx_count = 0
    empty_rx_fp_count = 0

    for rx_id, g_sub in by_rx_gold.items():
        p_sub = by_rx_pred[rx_id]
        sub_ent_eval = evaluate_docs(g_sub, p_sub)
        has_active_gold = sub_ent_eval.overall.gold > 0
        empty_false_positive = (
            not has_active_gold and sub_ent_eval.overall.predicted > 0
        )
        if has_active_gold:
            rx_f1s.append(sub_ent_eval.overall.f1)
        else:
            empty_rx_count += 1
            empty_rx_fp_count += int(empty_false_positive)

        rx_breakdown[rx_id] = {
            "active_entity_micro_f1": sub_ent_eval.overall.f1
            if has_active_gold
            else None,
            "entity_macro_f1": sub_ent_eval.macro.f1,
            "active_true_positive": sub_ent_eval.overall.true_positive,
            "active_predicted": sub_ent_eval.overall.predicted,
            "active_gold": sub_ent_eval.overall.gold,
            "included_in_primary_metric": has_active_gold,
            "empty_gold_false_positive": empty_false_positive,
            "record_exact_match": None,
            "document_exact_match": None,
        }

    macro_summary = {
        "prescription_macro_entity_f1": sum(rx_f1s) / len(rx_f1s) if rx_f1s else None,
        "total_prescription_count": len(by_rx_gold),
        "active_gold_prescription_count": len(rx_f1s),
        "excluded_empty_gold_prescription_count": empty_rx_count,
        "prescription_macro_record_em": None,
    }

    empty_doc_count = 0
    empty_doc_fp_count = 0
    for gold_doc, pred_doc in paired_docs:
        gold_count = len(entity_keys([gold_doc]))
        if gold_count == 0:
            empty_doc_count += 1
            empty_doc_fp_count += int(len(entity_keys([pred_doc])) > 0)

    def fp_rate(eligible: int, false_positive: int) -> dict[str, Any]:
        return {
            "eligible_unit_count": eligible,
            "false_positive_unit_count": false_positive,
            "rate": false_positive / eligible if eligible else None,
        }

    if task_type == "structured_extraction":
        record_eval = evaluate_records(ordered_gold, ordered_pred)
        relation_eval = (
            evaluate_relations(ordered_gold[0], ordered_pred[0])
            if ordered_gold
            else None
        )
        parent_accuracy = relation_eval.parent_accuracy if relation_eval else 0.0
        relation_micro = (
            relation_eval.relation_micro if relation_eval else _calc_prf(0, 0, 0)
        )
        relation_macro = (
            relation_eval.relation_macro if relation_eval else _calc_prf(0, 0, 0)
        )
        relation_per_type = relation_eval.per_type if relation_eval else {}
        record_exact_match = record_eval.record_exact_match
        record_tuple_prf = record_eval.record_tuple_prf
        document_exact_match = record_eval.document_exact_match
    else:
        parent_accuracy = None
        relation_micro = None
        relation_macro = None
        relation_per_type = None
        record_exact_match = None
        record_tuple_prf = None
        document_exact_match = None

    return StructuredEvaluationReport(
        schema_version="rxie.evaluation.v2",
        task_type=task_type,
        active_entity_types=active_types,
        entity_micro=entity_eval.overall,
        entity_macro=entity_eval.macro,
        entity_per_class=entity_eval.per_class,
        parent_accuracy=parent_accuracy,
        relation_micro=relation_micro,
        relation_macro=relation_macro,
        relation_per_type=relation_per_type,
        record_exact_match=record_exact_match,
        record_tuple_prf=record_tuple_prf,
        document_exact_match=document_exact_match,
        prescription_macro_summary=macro_summary,
        prescription_breakdown=rx_breakdown,
        empty_gold_document_false_positive=fp_rate(empty_doc_count, empty_doc_fp_count),
        empty_gold_prescription_false_positive=fp_rate(
            empty_rx_count, empty_rx_fp_count
        ),
    )


# Standard export alias
evaluate_structured_annotations = evaluate_dual_level
