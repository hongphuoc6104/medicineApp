"""Versioned OCR input and entity output contracts."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OCR_SCHEMA_VERSION = "rxie.ocr.v1"
ENTITIES_SCHEMA_VERSION = "rxie.entities.v1"
ANNOTATION_SCHEMA_VERSION = "rxie.annotation.v1"

Coordinate = Annotated[float, Field(ge=0)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Point = tuple[Coordinate, Coordinate]


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


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OcrEngine(ContractModel):
    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]


class BoundingBox(ContractModel):
    points: tuple[Point, Point, Point, Point]


class OcrRegion(ContractModel):
    region_id: Annotated[str, Field(min_length=1)]
    text: str
    confidence: Confidence | None
    reading_order: Annotated[int, Field(ge=0)]
    bbox: BoundingBox


class OcrPage(ContractModel):
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    page_index: Annotated[int, Field(ge=0)]
    regions: list[OcrRegion]

    @model_validator(mode="after")
    def validate_regions(self) -> OcrPage:
        orders = [region.reading_order for region in self.regions]
        if len(orders) != len(set(orders)):
            raise ValueError("reading_order must be unique within a page")
        for region in self.regions:
            outside_page = any(
                x > self.width or y > self.height
                for x, y in region.bbox.points
            )
            if outside_page:
                raise ValueError("region bbox must be within page dimensions")
        return self


class OcrDocument(ContractModel):
    schema_version: Literal["rxie.ocr.v1"] = OCR_SCHEMA_VERSION
    document_id: Annotated[str, Field(min_length=1)]
    ocr_engine: OcrEngine
    pages: Annotated[list[OcrPage], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_document_ids(self) -> OcrDocument:
        page_indexes = [page.page_index for page in self.pages]
        if len(page_indexes) != len(set(page_indexes)):
            raise ValueError("page_index must be unique within a document")
        region_ids = [r.region_id for page in self.pages for r in page.regions]
        if len(region_ids) != len(set(region_ids)):
            raise ValueError("region_id must be unique within a document")
        return self


class Entity(ContractModel):
    type: EntityType
    text: Annotated[str, Field(min_length=1)]
    normalized: str | None = None
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]
    confidence: Confidence
    source_region_ids: Annotated[list[str], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_span(self) -> Entity:
        if self.end <= self.start:
            raise ValueError("entity span must satisfy start < end")
        if len(self.source_region_ids) != len(set(self.source_region_ids)):
            raise ValueError("source_region_ids must not contain duplicates")
        return self


class EntityResponse(ContractModel):
    schema_version: Literal["rxie.entities.v1"] = ENTITIES_SCHEMA_VERSION
    document_id: Annotated[str, Field(min_length=1)]
    model_version: Annotated[str, Field(min_length=1)]
    entities: list[Entity]


class GoldEntity(ContractModel):
    type: EntityType
    text: Annotated[str, Field(min_length=1)]
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def validate_span(self) -> GoldEntity:
        if self.end <= self.start:
            raise ValueError("gold entity span must satisfy start < end")
        return self


class AnnotationProvenance(ContractModel):
    source: Literal["native", "legacy_drug_only"] = "native"
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_legacy_warning(self) -> AnnotationProvenance:
        if self.source == "legacy_drug_only" and not self.warnings:
            raise ValueError("legacy annotations must include a provenance warning")
        return self


class AnnotationDocument(ContractModel):
    """One versioned JSONL record containing exact character-span labels."""

    schema_version: Literal["rxie.annotation.v1"] = ANNOTATION_SCHEMA_VERSION
    document_id: Annotated[str, Field(min_length=1)]
    raw_text: str
    entities: list[GoldEntity]
    provenance: AnnotationProvenance = Field(default_factory=AnnotationProvenance)

    @model_validator(mode="after")
    def validate_entities(self) -> AnnotationDocument:
        ordered = sorted(self.entities, key=lambda entity: (entity.start, entity.end))
        previous_end = 0
        for entity in ordered:
            if entity.end > len(self.raw_text):
                raise ValueError("gold entity span exceeds raw_text")
            if self.raw_text[entity.start : entity.end] != entity.text:
                raise ValueError("gold entity text does not match raw_text span")
            if entity.start < previous_end:
                raise ValueError("gold entity spans must not overlap")
            previous_end = entity.end
        return self


ANNOTATION_V2_SCHEMA_VERSION = "rxie.annotation.v2"


class RelationType(str, Enum):
    HAS_STRENGTH = "HAS_STRENGTH"
    HAS_DOSAGE = "HAS_DOSAGE"
    HAS_FREQUENCY = "HAS_FREQUENCY"
    HAS_QUANTITY = "HAS_QUANTITY"
    HAS_DURATION = "HAS_DURATION"
    HAS_ROUTE = "HAS_ROUTE"
    HAS_INSTRUCTION = "HAS_INSTRUCTION"
    HAS_FORM = "HAS_FORM"


ENTITY_TO_RELATION_MAP: dict[EntityType, RelationType] = {
    EntityType.STRENGTH: RelationType.HAS_STRENGTH,
    EntityType.DOSAGE: RelationType.HAS_DOSAGE,
    EntityType.FREQUENCY: RelationType.HAS_FREQUENCY,
    EntityType.QUANTITY: RelationType.HAS_QUANTITY,
    EntityType.DURATION: RelationType.HAS_DURATION,
    EntityType.ROUTE: RelationType.HAS_ROUTE,
    EntityType.INSTRUCTION: RelationType.HAS_INSTRUCTION,
    EntityType.FORM: RelationType.HAS_FORM,
}


class GoldEntityV2(ContractModel):
    entity_id: Annotated[str, Field(min_length=1)]
    type: EntityType
    text: Annotated[str, Field(min_length=1)]
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]
    medication_id: Annotated[str, Field(min_length=1)] | None = None
    parent_entity_id: Annotated[str, Field(min_length=1)] | None = None
    source_region_ids: list[str] = Field(default_factory=list)
    normalized: str | None = None

    @model_validator(mode="after")
    def validate_span(self) -> GoldEntityV2:
        if self.end <= self.start:
            raise ValueError("gold entity span must satisfy start < end")
        if self.type == EntityType.DRUG and self.parent_entity_id is not None:
            raise ValueError("DRUG entity must have parent_entity_id == None")
        return self


class EntityRelation(ContractModel):
    head_entity_id: Annotated[str, Field(min_length=1)]
    tail_entity_id: Annotated[str, Field(min_length=1)]
    relation_type: RelationType


class AnnotationDocumentV2(ContractModel):
    """Versioned relational JSONL record containing entities, parent pointers, and relations."""

    schema_version: Literal["rxie.annotation.v2"] = ANNOTATION_V2_SCHEMA_VERSION
    document_id: Annotated[str, Field(min_length=1)]
    prescription_id: Annotated[str, Field(min_length=1)] | None = None
    patient_id: str | None = None
    image_id: str | None = None
    raw_text: str
    entities: list[GoldEntityV2]
    relations: list[EntityRelation] = Field(default_factory=list)
    provenance: AnnotationProvenance = Field(default_factory=AnnotationProvenance)

    @model_validator(mode="after")
    def validate_document(self) -> AnnotationDocumentV2:
        entity_ids = [e.entity_id for e in self.entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("entity_id must be unique within document")

        entity_map = {e.entity_id: e for e in self.entities}

        ordered = sorted(self.entities, key=lambda e: (e.start, e.end))
        prev_end = 0
        for e in ordered:
            if e.end > len(self.raw_text):
                raise ValueError(f"entity span ({e.start}, {e.end}) exceeds raw_text length")
            if self.raw_text[e.start : e.end] != e.text:
                raise ValueError(f"entity text '{e.text}' does not match raw_text")
            if e.start < prev_end:
                raise ValueError(f"gold entity spans must not overlap: {e.text}")
            prev_end = e.end

            if e.parent_entity_id is not None:
                if e.parent_entity_id not in entity_map:
                    raise ValueError(f"parent_entity_id '{e.parent_entity_id}' not found in document")
                parent_entity = entity_map[e.parent_entity_id]
                if parent_entity.type != EntityType.DRUG:
                    raise ValueError(f"parent '{e.parent_entity_id}' must be of type DRUG, got {parent_entity.type}")

        for rel in self.relations:
            if rel.head_entity_id not in entity_map:
                raise ValueError(f"relation head '{rel.head_entity_id}' not found")
            if rel.tail_entity_id not in entity_map:
                raise ValueError(f"relation tail '{rel.tail_entity_id}' not found")
            head = entity_map[rel.head_entity_id]
            tail = entity_map[rel.tail_entity_id]
            if head.type != EntityType.DRUG:
                raise ValueError(f"relation head must be DRUG, got {head.type}")
            expected_rel = ENTITY_TO_RELATION_MAP.get(tail.type)
            if expected_rel and rel.relation_type != expected_rel:
                raise ValueError(
                    f"relation {rel.relation_type} does not match tail entity type {expected_rel}"
                )

        return self
