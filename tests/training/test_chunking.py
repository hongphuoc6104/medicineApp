"""Unit tests for document chunking and gold entity recoverability."""

import json
from pathlib import Path

from rxie.chunking import chunk_document_by_characters, verify_gold_entities_recoverable
from rxie.schemas import AnnotationDocument, EntityType, GoldEntity


def test_chunking_short_document():
    doc = AnnotationDocument(
        schema_version="rxie.annotation.v1",
        document_id="doc_short",
        raw_text="Amlodipine 5mg ngày uống 1 viên",
        entities=[
            GoldEntity(type=EntityType.DRUG, text="Amlodipine", start=0, end=10),
            GoldEntity(type=EntityType.STRENGTH, text="5mg", start=11, end=14),
            GoldEntity(type=EntityType.ROUTE, text="uống", start=20, end=24),
            GoldEntity(type=EntityType.DOSAGE, text="1 viên", start=25, end=31),
        ],
    )
    chunks = chunk_document_by_characters(doc, max_chars=1000, stride_chars=200)
    assert len(chunks) == 1
    assert chunks[0].char_start == 0
    assert chunks[0].char_end == len(doc.raw_text)
    assert verify_gold_entities_recoverable(doc, chunks)


def test_chunking_long_document_recoverability():
    raw_text = (
        "Khoa Khám Bệnh - Bệnh Viện Đa Khoa Trung Ương Cần Thơ\n"
        "Đơn thuốc điều trị ngoại trú\n"
        "1. Amlodipine 5mg - Ngày uống 1 viên buổi sáng sau ăn\n"
        + ("Boilerplate padding text line for testing length requirements. " * 30)
        + "\n2. Metformin 750mg - Ngày uống 2 viên sau ăn tối\n"
        + ("More padding boilerplate text to simulate long document. " * 30)
        + "\n3. Rosuvastatin 10mg - Ngày uống 1 viên buổi tối trước ngủ\n"
    )

    doc = AnnotationDocument(
        schema_version="rxie.annotation.v1",
        document_id="doc_long",
        raw_text=raw_text,
        entities=[
            GoldEntity(type=EntityType.DRUG, text="Amlodipine", start=raw_text.find("Amlodipine"), end=raw_text.find("Amlodipine") + 10),
            GoldEntity(type=EntityType.STRENGTH, text="5mg", start=raw_text.find("5mg"), end=raw_text.find("5mg") + 3),
            GoldEntity(type=EntityType.DRUG, text="Metformin", start=raw_text.find("Metformin"), end=raw_text.find("Metformin") + 9),
            GoldEntity(type=EntityType.STRENGTH, text="750mg", start=raw_text.find("750mg"), end=raw_text.find("750mg") + 5),
            GoldEntity(type=EntityType.DRUG, text="Rosuvastatin", start=raw_text.find("Rosuvastatin"), end=raw_text.find("Rosuvastatin") + 12),
            GoldEntity(type=EntityType.STRENGTH, text="10mg", start=raw_text.find("10mg"), end=raw_text.find("10mg") + 4),
        ],
    )

    # Chunk with small window size to force multiple splits
    chunks = chunk_document_by_characters(doc, max_chars=800, stride_chars=300)
    assert len(chunks) >= 3
    assert verify_gold_entities_recoverable(doc, chunks), "Every gold entity must be recoverable across chunks"
