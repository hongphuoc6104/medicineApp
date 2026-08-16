from fastapi.testclient import TestClient

from rxie.api import create_app
from rxie.schemas import Entity, EntityType
from tests.rxie.test_schema import payload


class DeterministicClassifier:
    model_version = "test-v1"

    def classify(self, document):
        return [
            Entity(
                type=EntityType.DRUG,
                text=document.raw_text[0:11],
                normalized="paracetamol",
                start=0,
                end=11,
                confidence=0.99,
                source_region_ids=document.source_regions(0, 11),
            )
        ]


def test_health_and_model_info():
    client = TestClient(create_app(lambda: DeterministicClassifier()))

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/model-info").json() == {
        "configured": True,
        "available": True,
        "model_version": "test-v1",
    }


def test_entities_uses_injected_classifier():
    response = TestClient(create_app(lambda: DeterministicClassifier())).post(
        "/entities", json=payload()
    )

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "rxie.entities.v1",
        "document_id": "rx-1",
        "model_version": "test-v1",
        "entities": [
            {
                "type": "DRUG",
                "text": "Paracetamol",
                "normalized": "paracetamol",
                "start": 0,
                "end": 11,
                "confidence": 0.99,
                "source_region_ids": ["r1"],
            }
        ],
    }


def test_entities_returns_503_without_production_model(monkeypatch):
    monkeypatch.delenv("RXIE_MODEL_PATH", raising=False)
    client = TestClient(create_app())

    assert client.post("/entities", json=payload()).status_code == 503
