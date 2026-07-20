import numpy as np

from core.drug_search.drug_lookup import DrugLookup
from core.pipeline import MedicinePipeline


def test_drug_lookup_keeps_valid_parenthetical_match_for_losartan():
    lookup = DrugLookup()

    result = lookup.lookup("Losartan ( Cozaar 50 mg ) 50 mg")

    assert result["name"] in {"Cozaar 50mg", "Losartan 50mg", "Cozaar"}
    assert result["score"] >= 0.65


def test_scan_prescription_app_keeps_high_confidence_unmapped_drugname(monkeypatch):
    pipe = MedicinePipeline()

    class _FakeMapper:
        def lookup(self, _text):
            return {"name": None, "score": 0.0}

    monkeypatch.setattr(pipe, "_classify_blocks", lambda _blocks: [
        {
            "label": "drugname",
            "text": "Losartan ( Cozaar 50 mg ) 50 mg",
            "confidence": 0.9758,
            "bbox": [[0, 0], [10, 0], [10, 10], [0, 10]],
        }
    ])
    monkeypatch.setattr(pipe, "_get_drug_mapper", lambda: _FakeMapper())

    result = pipe.scan_prescription_app(ocr_text="Losartan ( Cozaar 50 mg ) 50 mg")

    assert len(result["medications"]) == 1
    assert len(result["medication_candidates"]) == 1
    assert result["medications"][0]["ocr_text"] == "Losartan ( Cozaar 50 mg ) 50 mg"
    assert result["medications"][0]["drug_name_raw"] == "Losartan ( Cozaar 50 mg ) 50 mg"
    assert result["medications"][0]["mapping_status"] == "unmapped_candidate"
