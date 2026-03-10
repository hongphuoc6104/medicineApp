"""
Tests cho Giai đoạn 2: Thu thập Dữ liệu Thuốc VN.

Xác thực:
- File drug_db_vn_full.json tồn tại và đúng format
- Không có duplicate
- Mỗi record có đủ 3 fields bắt buộc: tenThuoc, soDangKy, hoatChat
- Schema hợp lệ
"""
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
DRUG_DB = ROOT / "data" / "drug_db_vn_full.json"


@pytest.fixture(scope="module")
def drug_data():
    """Load drug database."""
    assert DRUG_DB.exists(), f"File not found: {DRUG_DB}"
    with open(DRUG_DB, encoding="utf-8") as f:
        return json.load(f)


class TestDrugDatabase:
    """Test drug database integrity."""

    def test_file_exists(self):
        assert DRUG_DB.exists()

    def test_total_drugs_count(self, drug_data):
        """Should have ≥ 9000 drugs."""
        assert drug_data["totalDrugs"] >= 9000
        assert len(drug_data["drugs"]) >= 9000

    def test_no_duplicate_records(self, drug_data):
        """All soDangKy should be unique."""
        ids = [
            d["soDangKy"]
            for d in drug_data["drugs"]
            if d.get("soDangKy")
        ]
        assert len(ids) == len(set(ids)), (
            f"Duplicates found: {len(ids) - len(set(ids))}"
        )

    def test_required_fields(self, drug_data):
        """Every drug must have tenThuoc, soDangKy, hoatChat."""
        for i, drug in enumerate(drug_data["drugs"]):
            assert drug.get("tenThuoc"), (
                f"Drug #{i} missing tenThuoc"
            )
            assert drug.get("soDangKy"), (
                f"Drug #{i} missing soDangKy"
            )
            assert isinstance(
                drug.get("hoatChat"), list
            ), f"Drug #{i} hoatChat not a list"

    def test_data_schema_valid(self, drug_data):
        """Sample drugs should have correct field types."""
        for drug in drug_data["drugs"][:10]:
            assert isinstance(drug["tenThuoc"], str)
            assert isinstance(drug["soDangKy"], str)
            assert isinstance(drug["hoatChat"], list)
            if drug["hoatChat"]:
                hc = drug["hoatChat"][0]
                assert "tenHoatChat" in hc

    def test_hoat_chat_completeness(self, drug_data):
        """At least 95% drugs should have active ingredients."""
        with_hc = sum(
            1 for d in drug_data["drugs"]
            if d.get("hoatChat") and len(d["hoatChat"]) > 0
        )
        pct = with_hc / len(drug_data["drugs"]) * 100
        assert pct >= 95, f"Only {pct:.1f}% have hoatChat"

    def test_metadata_fields(self, drug_data):
        """Should have crawledAt and source."""
        assert "crawledAt" in drug_data
        assert drug_data["source"] == "ddi.lab.io.vn"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
