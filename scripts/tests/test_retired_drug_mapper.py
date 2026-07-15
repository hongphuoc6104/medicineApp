import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAPPER = ROOT / "core/phase_a/s6_drug_search/drug_mapper.py"
ACTIVE_PYTHON_ROOTS = (ROOT / "core", ROOT / "server")


def test_legacy_drug_mapper_is_absent_and_unreferenced():
    assert not LEGACY_MAPPER.exists()

    active_files = [
        path
        for source_root in ACTIVE_PYTHON_ROOTS
        for path in source_root.rglob("*.py")
    ]
    active_files.extend(path for path in (ROOT / "scripts").glob("*.py"))

    reference_pattern = re.compile(
        r"(?:s6_drug_search(?:\.|\s+import\s+)drug_mapper|"
        r"(?:from|import)\s+[^\n]*drug_mapper|DrugMapper\s*\()"
    )
    references = [
        path.relative_to(ROOT).as_posix()
        for path in active_files
        if reference_pattern.search(path.read_text(encoding="utf-8"))
    ]

    assert references == []
