"""Dependency-injectable classifier boundary."""

from typing import Protocol

from .schemas import Entity
from .text import DocumentText


class EntityClassifier(Protocol):
    @property
    def model_version(self) -> str: ...

    def classify(self, document: DocumentText) -> list[Entity]: ...


class ModelUnavailableError(RuntimeError):
    """Raised when a production model cannot be provided."""
