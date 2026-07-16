import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server import main


def assert_retired_route_does_not_load_pipeline(path):
    with patch.object(
        main,
        "_get_pipeline",
        side_effect=AssertionError("retired route attempted to initialize AI pipeline"),
    ) as get_pipeline:
        response = TestClient(main.app).post(path)

    assert response.status_code == 404
    get_pipeline.assert_not_called()


def test_scan_pills_route_is_retired_without_loading_pipeline():
    assert_retired_route_does_not_load_pipeline("/api/scan-pills")


def test_dose_verification_route_is_retired_without_loading_pipeline():
    assert_retired_route_does_not_load_pipeline("/api/dose-verification")
