"""
FastAPI server for MedicineApp.

Endpoints:
    GET  /api/health              → Server status
    GET  /api/drug-info/{name}    → Drug information lookup
    GET  /api/drug-metadata/{name} → Drug metadata enrichment
    POST /api/scan-prescription   → Scan prescription image
    POST /api/scan-pills          → Verify pills against prescription
    POST /api/dose-verification   → Verify pills for one occurrence

Run:
    uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
# PaddlePaddle 3.3.0 fixes — MUST be set before any paddle import
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault(
    "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True"
)

import asyncio
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DRUG_DB_PATH = ROOT / "server" / "data" / "drug_db.json"

# Global state
_drug_service = None
_pipeline = None

# VĐ7: Semaphore giới hạn GPU concurrent (RTX 3050 4GB)
# Chỉ cho phép 1 scan chạy đồng thời để tránh OOM
scan_semaphore = asyncio.Semaphore(1)


def _parse_json_list(raw_value: str, field_name: str):
    """Parse JSON list field from multipart form input."""
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid JSON for {field_name}") from exc

    if not isinstance(parsed, list):
        raise HTTPException(400, f"{field_name} must be a JSON array")
    return parsed


async def _enrich_expected_medications(expected_items):
    """Attach structured metadata to expected meds for Phase B scoring."""
    if not expected_items:
        return []

    svc = _get_drug_service()

    async def enrich_item(item):
        item_copy = dict(item)
        drug_name = str(item_copy.get("drugName") or item_copy.get("name") or "").strip()
        if not drug_name:
            return item_copy

        try:
            metadata = await svc.enrich_metadata(drug_name)
        except Exception as exc:
            logger.warning("Drug metadata enrichment failed for %s: %s", drug_name, exc)
            metadata = {}
        item_copy["metadata"] = metadata
        return item_copy

    return await asyncio.gather(*(enrich_item(item) for item in expected_items))


def _get_drug_service():
    global _drug_service
    if _drug_service is None:
        from server.services.drug_service import DrugService
        _drug_service = DrugService()
    return _drug_service


def _get_pipeline():
    """Lazy load the AI pipeline (heavy models)."""
    global _pipeline
    if _pipeline is None:
        try:
            from core.pipeline import MedicinePipeline
            _pipeline = MedicinePipeline()
            logger.info("AI pipeline loaded")
        except Exception as e:
            logger.warning(
                f"AI pipeline not available: {e}"
            )
    return _pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    # VĐ7: Pre-load services + warm-up AI pipeline
    _get_drug_service()

    pipeline = _get_pipeline()
    if pipeline:
        try:
            import numpy as np
            dummy = np.zeros(
                (100, 100, 3), dtype=np.uint8
            )
            pipeline.scan_prescription_app(
                dummy, skip_yolo=True
            )
            logger.info(
                "✅ Pipeline warmed up successfully"
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Warm-up failed: {e} — "
                f"pipeline will lazy-load on first request"
            )

    logger.info("MedicineApp server started")
    yield
    logger.info("MedicineApp server stopped")


app = FastAPI(
    title="MedicineApp API",
    description=(
        "AI-powered prescription scanning "
        "& pill verification"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────

@app.get("/api/health")
async def health():
    svc = _get_drug_service()
    pipeline = _get_pipeline()
    return {
        "status": "ok",
        "drug_db": svc.count(),
        "ai_ready": pipeline is not None,
    }


# ── Drug Info ─────────────────────────────────────────

@app.get("/api/drug-info/{name}")
async def drug_info(name: str, online: bool = False):
    """
    Look up drug information by name.

    Args:
        name: Drug name (e.g. Paracetamol-500mg)
        online: If True, also query RxNorm + DailyMed APIs
    """
    svc = _get_drug_service()

    if online:
        result = await svc.lookup_online(name)
        if result:
            return result
    else:
        result = svc.lookup(name)
        if result:
            return result

    raise HTTPException(404, f"Drug not found: {name}")


@app.get("/api/drug-metadata/{name}")
async def drug_metadata(name: str):
    """Enrich a drug name with structured metadata for Phase B."""
    svc = _get_drug_service()
    return await svc.enrich_metadata(name)


@app.get("/api/drugs")
async def list_drugs(q: str = "", limit: int = 20):
    """List or search local drug DB."""
    svc = _get_drug_service()

    if not q:
        return {
            "drugs": list(svc.get_all().keys()),
            "count": svc.count(),
        }

    matches = svc.search(q, limit=limit)
    return {
        "results": matches,
        "count": len(matches),
        "query": q,
    }


@app.get("/api/drugs/search-online")
async def search_drugs_online(q: str, limit: int = 5):
    """
    Search drugs online using OpenFDA API.

    Returns brand name, generic name, dosage form,
    active ingredients, and pharmacological class.
    Free API, no key required.
    """
    if not q or len(q) < 2:
        raise HTTPException(
            400, "Query too short (min 2 chars)")

    svc = _get_drug_service()
    results = await svc.search_online(q, limit=limit)

    if not results:
        local = svc.search(q, limit=limit)
        if local:
            return {
                "results": local,
                "count": len(local),
                "query": q,
                "source": "local",
            }
        raise HTTPException(
            404, f"No drugs found for: {q}")

    return {
        "results": results,
        "count": len(results),
        "query": q,
        "source": "openfda",
    }


# ── Vietnamese Drug APIs (ddi.lab.io.vn) ──────────────

@app.get("/api/drugs/search-vn")
async def search_vn_drugs(q: str, limit: int = 10):
    """
    Search Vietnamese drugs from ddi.lab.io.vn.

    Returns drug name, active ingredients, dosage form,
    packaging, manufacturer — all in Vietnamese.
    Free API, no key required.
    """
    if not q or len(q) < 2:
        raise HTTPException(
            400, "Query too short (min 2 chars)")

    svc = _get_drug_service()
    results = await svc.search_vn(q, limit=limit)

    if not results:
        raise HTTPException(
            404, f"No VN drugs found for: {q}")

    return {
        "results": results,
        "count": len(results),
        "query": q,
        "source": "ddi.lab.io.vn",
    }


@app.get("/api/drugs/suggest-vn")
async def suggest_vn_drugs(q: str):
    """
    Vietnamese drug name autocomplete.

    Returns list of matching drug names.
    """
    if not q or len(q) < 2:
        raise HTTPException(
            400, "Query too short (min 2 chars)")

    svc = _get_drug_service()
    suggestions = await svc.suggest_vn(q)
    return {"suggestions": suggestions, "query": q}


@app.get("/api/drugs/interactions")
async def drug_interactions(ingredient: str):
    """
    Get drug-drug interactions for an active ingredient.

    Data from Vietnamese drug interaction database.
    Returns interactions grouped by severity.
    """
    if not ingredient or len(ingredient) < 2:
        raise HTTPException(
            400, "Ingredient name too short")

    svc = _get_drug_service()
    result = await svc.interactions(ingredient)

    if not result:
        raise HTTPException(
            404,
            f"No interactions found for: {ingredient}")

    return result


# ── Scan Prescription ─────────────────────────────────

@app.post("/api/scan-prescription")
async def scan_prescription(file: UploadFile = File(...)):
    """
    Scan prescription image → extract drug list.

    Upload a photo of a prescription and get back
    a list of detected medications.
    """
    import cv2
    import numpy as np

    # Read uploaded image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(400, "Invalid image file")

    pipeline = _get_pipeline()
    if pipeline is None:
        # Mock response when AI models aren't loaded
        return {
            "medications": [
                {
                    "drug_name": "Mock-Paracetamol-500mg",
                    "ocr_text": "Paracetamol 500mg",
                    "confidence": 0.95,
                    "match_score": 0.9,
                }
            ],
            "mock": True,
            "message": (
                "AI models not loaded. "
                "Download checkpoint to models/weights/"
            ),
        }

    # VĐ7: Semaphore — chỉ 1 scan đồng thời trên GPU
    async with scan_semaphore:
        result = pipeline.scan_prescription_app(img)
    return result


# ── Scan Pills ────────────────────────────────────────

@app.post("/api/scan-pills")
async def scan_pills(
    file: UploadFile = File(...),
    prescription_json: str = "",
):
    """
    Verify pills match the prescription.

    Upload a photo of pills + the prescription data (from scan)
    to verify which pills are correct.
    """
    import cv2
    import numpy as np

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(400, "Invalid image file")

    # Parse prescription data
    pres_blocks = []
    if prescription_json:
        pres_blocks = json.loads(prescription_json)

    pipeline = _get_pipeline()
    if pipeline is None:
        return {
            "matches": [],
            "detections": [],
            "mock": True,
            "message": "AI models not loaded.",
        }

    result = pipeline.verify_pills(img, pres_blocks)
    return result


@app.post("/api/dose-verification")
async def dose_verification(
    file: UploadFile = File(...),
    occurrence_id: str = "",
    scheduled_time: str = "",
    expected_medications: str = "[]",
    reference_profiles: str = "[]",
):
    """
    Verify pills for a single dose occurrence (dose-centric Phase B).

    Upload one group pill image and provide expected medications for
    the current occurrence along with optional user reference profiles.
    """
    import cv2
    import numpy as np

    if not occurrence_id:
        raise HTTPException(400, "occurrence_id is required")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(400, "Invalid image file")

    expected = _parse_json_list(expected_medications, "expected_medications")
    expected = await _enrich_expected_medications(expected)
    references = _parse_json_list(reference_profiles, "reference_profiles")

    pipeline = _get_pipeline()
    if pipeline is None:
        return {
            "mode": "dose_verification",
            "occurrenceId": occurrence_id,
            "scheduledTime": scheduled_time,
            "detections": [],
            "summary": {
                "totalDetections": 0,
                "assigned": 0,
                "uncertain": 0,
                "unknown": 0,
                "extra": 0,
                "missingExpected": len(expected),
                "perMedication": [],
            },
            "referenceCoverage": {
                "totalExpected": len(expected),
                "withReference": 0,
                "withoutReference": len(expected),
                "missingPlanIds": [
                    str(item.get("planId", "")) for item in expected
                ],
                "missingDrugNames": [
                    str(item.get("drugName", "")) for item in expected
                ],
            },
            "expectedMedications": expected,
            "missingReferences": [
                str(item.get("drugName", "")) for item in expected
            ],
            "mock": True,
            "message": "AI models not loaded.",
        }

    async with scan_semaphore:
        result = pipeline.verify_pills(
            img,
            occurrence_id=occurrence_id,
            scheduled_time=scheduled_time,
            expected_medications=expected,
            reference_profiles=references,
        )
    return result
