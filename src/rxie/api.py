"""FastAPI application for RxIE entity classification."""

import os
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from .classifier import EntityClassifier, ModelUnavailableError
from .huggingface import HuggingFaceTokenClassifier
from .schemas import EntityResponse, OcrDocument
from .text import build_document_text, validate_entities

ClassifierProvider = Callable[[], EntityClassifier]


class HealthResponse(BaseModel):
    status: str


class ModelInfoResponse(BaseModel):
    configured: bool
    available: bool
    model_version: str | None


class ProductionClassifierProvider:
    """Load a configured local artifact once, on first inference request."""

    def __init__(self) -> None:
        value = os.getenv("RXIE_MODEL_PATH")
        self.path = Path(value).expanduser() if value else None
        self._classifier: EntityClassifier | None = None
        self._error: str | None = None
        self._lock = Lock()

    @property
    def configured(self) -> bool:
        return self.path is not None

    @property
    def available(self) -> bool:
        return self.path is not None and self.path.is_dir() and self._error is None

    @property
    def model_version(self) -> str | None:
        return self._classifier.model_version if self._classifier else None

    def __call__(self) -> EntityClassifier:
        if self.path is None:
            raise ModelUnavailableError("RXIE_MODEL_PATH is not configured")
        if not self.path.is_dir():
            raise ModelUnavailableError("RXIE_MODEL_PATH is not a model directory")
        if self._error:
            raise ModelUnavailableError(self._error)
        with self._lock:
            if self._classifier is None:
                try:
                    self._classifier = HuggingFaceTokenClassifier(self.path)
                except Exception as exc:
                    self._error = f"model artifact could not be loaded: {exc}"
                    raise ModelUnavailableError(self._error) from exc
        return self._classifier


def create_app(classifier_provider: ClassifierProvider | None = None) -> FastAPI:
    app = FastAPI(title="RxIE", version="0.1.0")
    production = ProductionClassifierProvider() if classifier_provider is None else None
    provider = classifier_provider or production
    assert provider is not None

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/model-info", response_model=ModelInfoResponse)
    def model_info() -> ModelInfoResponse:
        if production is None:
            try:
                classifier = provider()
            except ModelUnavailableError:
                return ModelInfoResponse(
                    configured=True, available=False, model_version=None
                )
            return ModelInfoResponse(
                configured=True,
                available=True,
                model_version=classifier.model_version,
            )
        return ModelInfoResponse(
            configured=production.configured,
            available=production.available,
            model_version=production.model_version,
        )

    def get_classifier() -> EntityClassifier:
        try:
            return provider()
        except ModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/entities", response_model=EntityResponse)
    def entities(
        request: OcrDocument,
        classifier: Annotated[EntityClassifier, Depends(get_classifier)],
    ) -> EntityResponse:
        text = build_document_text(request)
        predictions = classifier.classify(text)
        try:
            validate_entities(predictions, text)
        except ValueError as exc:
            raise HTTPException(
                status_code=500, detail=f"invalid model output: {exc}"
            ) from exc
        return EntityResponse(
            document_id=request.document_id,
            model_version=classifier.model_version,
            entities=predictions,
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("rxie.api:app", host="0.0.0.0", port=8000)
