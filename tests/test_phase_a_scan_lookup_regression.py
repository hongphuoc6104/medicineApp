import numpy as np

from core.phase_a.s6_drug_search.drug_lookup import DrugLookup
from core.pipeline import MedicinePipeline


def test_drug_lookup_keeps_valid_parenthetical_match_for_losartan():
    lookup = DrugLookup()

    result = lookup.lookup("Losartan ( Cozaar 50 mg ) 50 mg")

    assert result["name"] in {"Cozaar 50mg", "Losartan 50mg", "Cozaar"}
    assert result["score"] >= 0.65


def test_scan_prescription_app_keeps_high_confidence_unmapped_drugname(monkeypatch):
    pipe = MedicinePipeline()

    class _FakeTextBlock:
        def __init__(self, text, bbox):
            self.text = text
            self.bbox = bbox

    class _FakeOcrResult:
        def __init__(self, blocks):
            self.text_blocks = blocks

    class _FakeOcr:
        def extract(self, _img):
            return _FakeOcrResult(
                [
                    _FakeTextBlock(
                        "Losartan ( Cozaar 50 mg ) 50 mg",
                        [[0, 0], [10, 0], [10, 10], [0, 10]],
                    )
                ]
            )

    class _FakeMapper:
        def lookup(self, _text):
            return {"name": None, "score": 0.0}

    monkeypatch.setattr(pipe, "_get_ocr", lambda: _FakeOcr())
    monkeypatch.setattr(pipe, "_classify_blocks", lambda _blocks: [
        {
            "label": "drugname",
            "text": "Losartan ( Cozaar 50 mg ) 50 mg",
            "confidence": 0.9758,
            "bbox": [[0, 0], [10, 0], [10, 10], [0, 10]],
        }
    ])
    monkeypatch.setattr(pipe, "_get_drug_mapper", lambda: _FakeMapper())

    result = pipe.scan_prescription_app(np.zeros((50, 50, 3), dtype=np.uint8), skip_yolo=True)

    assert len(result["medications"]) == 1
    assert result["medications"][0]["drug_name_raw"] == "Losartan ( Cozaar 50 mg ) 50 mg"
    assert result["medications"][0]["mapping_status"] == "unmapped_candidate"
