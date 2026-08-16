"""Deterministic conversion between OCR regions and model text offsets."""

from dataclasses import dataclass

from .schemas import Entity, OcrDocument


@dataclass(frozen=True)
class RegionSpan:
    region_id: str
    start: int
    end: int


@dataclass(frozen=True)
class DocumentText:
    raw_text: str
    regions: tuple[RegionSpan, ...]

    def source_regions(self, start: int, end: int) -> list[str]:
        return [
            region.region_id
            for region in self.regions
            if region.start < end and start < region.end
        ]


def build_document_text(document: OcrDocument) -> DocumentText:
    """Join regions with newlines after sorting by page and reading order."""
    ordered = [
        region
        for page in sorted(document.pages, key=lambda item: item.page_index)
        for region in sorted(
            page.regions, key=lambda item: (item.reading_order, item.region_id)
        )
    ]
    parts: list[str] = []
    spans: list[RegionSpan] = []
    cursor = 0
    for index, region in enumerate(ordered):
        if index:
            parts.append("\n")
            cursor += 1
        start = cursor
        parts.append(region.text)
        cursor += len(region.text)
        spans.append(RegionSpan(region.region_id, start, cursor))
    return DocumentText("".join(parts), tuple(spans))


def validate_entities(entities: list[Entity], text: DocumentText) -> None:
    """Validate model spans, exact text, ordering, and OCR provenance."""
    previous = (-1, -1)
    known_regions = {region.region_id for region in text.regions}
    for entity in entities:
        if entity.end > len(text.raw_text):
            raise ValueError("entity span exceeds raw_text")
        if text.raw_text[entity.start : entity.end] != entity.text:
            raise ValueError("entity text does not match raw_text span")
        position = (entity.start, entity.end)
        if position < previous:
            raise ValueError("entities must be ordered by start and end offset")
        previous = position
        expected = text.source_regions(entity.start, entity.end)
        if not expected:
            raise ValueError("entity span must overlap an OCR region")
        if set(entity.source_region_ids) - known_regions:
            raise ValueError("entity references an unknown OCR region")
        if entity.source_region_ids != expected:
            raise ValueError("source_region_ids do not match the entity span")
