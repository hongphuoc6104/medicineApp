"""Strict entity-level, relation, record, and dual-level structured evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

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
    entity_micro: PrfScore
    entity_macro: PrfScore
    entity_per_class: dict[EntityType, PrfScore]
    parent_accuracy: float
    relation_micro: PrfScore
    relation_macro: PrfScore
    relation_per_type: dict[RelationType, PrfScore]
    record_exact_match: float
    record_tuple_prf: PrfScore
    document_exact_match: float
    prescription_macro_summary: dict[str, float]
    prescription_breakdown: dict[str, dict[str, float]]

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "entity_micro": self.entity_micro.__dict__,
            "entity_macro": self.entity_macro.__dict__,
            "entity_per_class": {k.value: v.__dict__ for k, v in self.entity_per_class.items()},
            "parent_accuracy": self.parent_accuracy,
            "relation_micro": self.relation_micro.__dict__,
            "relation_macro": self.relation_macro.__dict__,
            "relation_per_type": {k.value: v.__dict__ for k, v in self.relation_per_type.items()},
            "record_exact_match": self.record_exact_match,
            "record_tuple_prf": self.record_tuple_prf.__dict__,
            "document_exact_match": self.document_exact_match,
            "prescription_macro_summary": self.prescription_macro_summary,
            "prescription_breakdown": self.prescription_breakdown,
        }


def _calc_prf(tp: int, pred: int, gold: int) -> PrfScore:
    precision = tp / pred if pred else (1.0 if not gold else 0.0)
    recall = tp / gold if gold else (1.0 if not pred else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PrfScore(precision, recall, f1, tp, pred, gold)


from .alignment import DEFAULT_ACTIVE_ENTITY_TYPES


def evaluate_strict_entities(
    gold_entities: list[GoldEntityV2] | list[Entity] | Iterable[Any],
    pred_entities: list[GoldEntityV2] | list[Entity] | Iterable[Any],
    active_entity_types: Iterable[EntityType | str] | None = None,
) -> EntityEvaluation:
    gold_keys = {(e.type, e.start, e.end) for e in gold_entities}
    pred_keys = {(e.type, e.start, e.end) for e in pred_entities}

    if active_entity_types is not None:
        target_types = {EntityType(t) if isinstance(t, str) else t for t in active_entity_types}
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
        per_class[ent_type] = score
        if ent_type in target_types:
            f1_list.append(score.f1)
            p_list.append(score.precision)
            r_list.append(score.recall)

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0
    macro_p = sum(p_list) / len(p_list) if p_list else 0.0
    macro_r = sum(r_list) / len(r_list) if r_list else 0.0
    macro_prf = PrfScore(macro_p, macro_r, macro_f1, overall_tp, len(eval_pred_keys), len(eval_gold_keys))

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
            (pe for pe in pred_doc.entities if pe.type == ga.type and pe.start == ga.start and pe.end == ga.end),
            None,
        )
        if matching_pred is not None:
            gold_parent_span = None
            if ga.parent_entity_id and ga.parent_entity_id in gold_map:
                gp = gold_map[ga.parent_entity_id]
                gold_parent_span = (gp.type, gp.start, gp.end)

            pred_parent_span = None
            if matching_pred.parent_entity_id and matching_pred.parent_entity_id in pred_map:
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
                triples.add(((h.type, h.start, h.end), (t.type, t.start, t.end), r.relation_type))
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
                (e.type, e.start, e.end) for e in g_doc.entities if e.parent_entity_id == gd.entity_id
            )
            g_records.append(((gd.type, gd.start, gd.end), attrs))
            for a in attrs:
                gold_tuples_all.add(((g_doc.document_id, (gd.type, gd.start, gd.end)), a))

        p_records: list[tuple[tuple, frozenset[tuple]]] = []
        for pd in p_drugs:
            attrs = frozenset(
                (e.type, e.start, e.end) for e in p_doc.entities if e.parent_entity_id == pd.entity_id
            )
            p_records.append(((pd.type, pd.start, pd.end), attrs))
            for a in attrs:
                pred_tuples_all.add(((p_doc.document_id, (pd.type, pd.start, pd.end)), a))

        matched_in_doc = 0
        for gr in g_records:
            if gr in p_records:
                exact_matched_records += 1
                matched_in_doc += 1

        if len(g_records) > 0 and matched_in_doc == len(g_records) and len(p_records) == len(g_records):
            doc_em_count += 1
        elif len(g_records) == 0 and len(p_records) == 0:
            doc_em_count += 1

    record_em = exact_matched_records / total_gold_records if total_gold_records else 1.0
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
    active_entity_types: Iterable[EntityType | str] | None = None,
) -> StructuredEvaluationReport:
    all_gold_ents = [e for d in gold_docs for e in d.entities]
    all_pred_ents = [e for d in pred_docs for e in d.entities]
    entity_eval = evaluate_strict_entities(all_gold_ents, all_pred_ents, active_entity_types=active_entity_types)

    record_eval = evaluate_records(gold_docs, pred_docs)

    all_parent_accs = []
    for g, p in zip(gold_docs, pred_docs, strict=False):
        r_eval = evaluate_relations(g, p)
        all_parent_accs.append(r_eval.parent_accuracy)

    mean_parent_acc = sum(all_parent_accs) / len(all_parent_accs) if all_parent_accs else 1.0

    by_rx_gold: dict[str, list[AnnotationDocumentV2]] = defaultdict(list)
    by_rx_pred: dict[str, list[AnnotationDocumentV2]] = defaultdict(list)

    for g, p in zip(gold_docs, pred_docs, strict=False):
        rx_id = g.prescription_id or "RX_UNKNOWN"
        by_rx_gold[rx_id].append(g)
        by_rx_pred[rx_id].append(p)

    rx_breakdown: dict[str, dict[str, float]] = {}
    rx_f1s = []
    rx_ems = []

    for rx_id, g_sub in by_rx_gold.items():
        p_sub = by_rx_pred[rx_id]
        g_sub_ents = [e for d in g_sub for e in d.entities]
        p_sub_ents = [e for d in p_sub for e in d.entities]
        sub_ent_eval = evaluate_strict_entities(g_sub_ents, p_sub_ents, active_entity_types=active_entity_types)
        sub_rec_eval = evaluate_records(g_sub, p_sub)

        rx_breakdown[rx_id] = {
            "entity_micro_f1": sub_ent_eval.overall.f1,
            "entity_macro_f1": sub_ent_eval.macro.f1,
            "record_exact_match": sub_rec_eval.record_exact_match,
            "document_exact_match": sub_rec_eval.document_exact_match,
        }
        rx_f1s.append(sub_ent_eval.overall.f1)
        rx_ems.append(sub_rec_eval.record_exact_match)

    macro_summary = {
        "prescription_macro_entity_f1": sum(rx_f1s) / len(rx_f1s) if rx_f1s else 0.0,
        "prescription_macro_record_em": sum(rx_ems) / len(rx_ems) if rx_ems else 0.0,
    }

    relation_eval = evaluate_relations(gold_docs[0], pred_docs[0]) if gold_docs and pred_docs else None
    rel_micro = relation_eval.relation_micro if relation_eval else _calc_prf(0, 0, 0)
    rel_macro = relation_eval.relation_macro if relation_eval else _calc_prf(0, 0, 0)
    rel_per_type = relation_eval.per_type if relation_eval else {r: _calc_prf(0, 0, 0) for r in RelationType}

    return StructuredEvaluationReport(
        entity_micro=entity_eval.overall,
        entity_macro=entity_eval.macro,
        entity_per_class=entity_eval.per_class,
        parent_accuracy=mean_parent_acc,
        relation_micro=rel_micro,
        relation_macro=rel_macro,
        relation_per_type=rel_per_type,
        record_exact_match=record_eval.record_exact_match,
        record_tuple_prf=record_eval.record_tuple_prf,
        document_exact_match=record_eval.document_exact_match,
        prescription_macro_summary=macro_summary,
        prescription_breakdown=rx_breakdown,
    )


# Standard export alias
evaluate_structured_annotations = evaluate_dual_level
