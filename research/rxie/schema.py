"""Versioned data contract for RxIE datasets and model outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

RXIE_SCHEMA_VERSION = "rxie.v0.1"


class EntityType(str, Enum):
    DRUG = "DRUG"
    STRENGTH = "STRENGTH"
    DOSAGE = "DOSAGE"
    FREQUENCY = "FREQUENCY"
    QUANTITY = "QUANTITY"
    DURATION = "DURATION"
    ROUTE = "ROUTE"
    INSTRUCTION = "INSTRUCTION"
    FORM = "FORM"
    NOTE = "NOTE"


class RelationType(str, Enum):
    HAS_STRENGTH = "HAS_STRENGTH"
    HAS_DOSE = "HAS_DOSE"
    HAS_FREQUENCY = "HAS_FREQUENCY"
    HAS_QUANTITY = "HAS_QUANTITY"
    HAS_DURATION = "HAS_DURATION"
    HAS_ROUTE = "HAS_ROUTE"
    HAS_INSTRUCTION = "HAS_INSTRUCTION"
    HAS_FORM = "HAS_FORM"


ENTITY_TO_RELATION = {
    EntityType.STRENGTH: RelationType.HAS_STRENGTH,
    EntityType.DOSAGE: RelationType.HAS_DOSE,
    EntityType.FREQUENCY: RelationType.HAS_FREQUENCY,
    EntityType.QUANTITY: RelationType.HAS_QUANTITY,
    EntityType.DURATION: RelationType.HAS_DURATION,
    EntityType.ROUTE: RelationType.HAS_ROUTE,
    EntityType.INSTRUCTION: RelationType.HAS_INSTRUCTION,
    EntityType.FORM: RelationType.HAS_FORM,
}


@dataclass(frozen=True)
class OcrBlock:
    region_id: str
    text: str
    confidence: Optional[float]
    reading_order: int
    bbox: Optional[tuple[tuple[float, float], ...]] = None

    def __post_init__(self) -> None:
        if not self.region_id:
            raise ValueError("OCR region_id must not be empty")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("OCR confidence must be between 0 and 1")
        if self.reading_order < 0:
            raise ValueError("OCR reading_order must be non-negative")
        if self.bbox is not None and len(self.bbox) != 4:
            raise ValueError("OCR bbox must contain exactly four points")


@dataclass(frozen=True)
class Entity:
    entity_id: str
    entity_type: EntityType
    start: int
    end: int
    text: str
    normalized: Optional[str] = None
    source_region_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("Entity ID must not be empty")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("Entity span must satisfy 0 <= start < end")


@dataclass(frozen=True)
class ParentAssignment:
    attribute_id: str
    drug_id: Optional[str]


@dataclass(frozen=True)
class Relation:
    drug_id: str
    attribute_id: str
    relation_type: RelationType


@dataclass(frozen=True)
class MedicationRecord:
    drug: str
    strength: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    quantity: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None
    instruction: Optional[str] = None
    form: Optional[str] = None


@dataclass(frozen=True)
class PrescriptionDocument:
    document_id: str
    raw_text: str
    ocr_engine: str
    ocr_blocks: tuple[OcrBlock, ...]
    entities: tuple[Entity, ...]
    parent_assignments: tuple[ParentAssignment, ...]
    relations: tuple[Relation, ...]
    records: tuple[MedicationRecord, ...]
    source_domain: Optional[str] = None
    template_family: Optional[str] = None
    schema_version: str = field(default=RXIE_SCHEMA_VERSION)

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ValueError("Document ID must not be empty")
        if self.schema_version != RXIE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported RxIE schema: {self.schema_version}")

        entities_by_id = {entity.entity_id: entity for entity in self.entities}
        if len(entities_by_id) != len(self.entities):
            raise ValueError("Entity IDs must be unique within a document")

        region_ids = {block.region_id for block in self.ocr_blocks}
        if len(region_ids) != len(self.ocr_blocks):
            raise ValueError("OCR region IDs must be unique within a document")

        for entity in self.entities:
            if entity.end > len(self.raw_text):
                raise ValueError(f"Entity {entity.entity_id} exceeds raw text")
            unknown_regions = set(entity.source_region_ids) - region_ids
            if unknown_regions:
                raise ValueError(
                    f"Entity {entity.entity_id} references unknown OCR regions"
                )

        seen_attributes = set()
        parent_by_attribute = {}
        for assignment in self.parent_assignments:
            attribute = entities_by_id.get(assignment.attribute_id)
            if attribute is None or attribute.entity_type == EntityType.DRUG:
                raise ValueError("Parent assignment must reference an attribute")
            if assignment.attribute_id in seen_attributes:
                raise ValueError("Each attribute must have one parent assignment")
            seen_attributes.add(assignment.attribute_id)
            parent_by_attribute[assignment.attribute_id] = assignment.drug_id
            if assignment.drug_id is not None:
                drug = entities_by_id.get(assignment.drug_id)
                if drug is None or drug.entity_type != EntityType.DRUG:
                    raise ValueError("Parent drug must reference a DRUG entity")

        attribute_ids = {
            entity.entity_id
            for entity in self.entities
            if entity.entity_type != EntityType.DRUG
        }
        if seen_attributes != attribute_ids:
            raise ValueError("Every attribute must have one parent assignment")

        for relation in self.relations:
            drug = entities_by_id.get(relation.drug_id)
            attribute = entities_by_id.get(relation.attribute_id)
            if drug is None or drug.entity_type != EntityType.DRUG:
                raise ValueError("Relation head must reference a DRUG entity")
            if attribute is None or attribute.entity_type == EntityType.DRUG:
                raise ValueError("Relation tail must reference an attribute")
            if parent_by_attribute.get(relation.attribute_id) != relation.drug_id:
                raise ValueError("Relation must agree with the parent assignment")
            expected = ENTITY_TO_RELATION.get(attribute.entity_type)
            if expected is not None and relation.relation_type != expected:
                raise ValueError("Relation type conflicts with attribute type")
