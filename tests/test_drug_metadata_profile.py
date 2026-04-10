from server.services.drug_service import DrugService


def test_merge_vn_entry_builds_basic_metadata_profile():
    service = DrugService()
    profile = service._base_metadata_profile("Hapacol 500")

    service._merge_vn_entry(
        profile,
        {
            "tenThuoc": "Hapacol Extra",
            "soDangKy": "VD-20570-14",
            "baoChe": "Viên nén",
            "dongGoi": "Hộp 10 vỉ x 10 viên",
            "congTySx": "DHG Pharma",
            "nuocSx": "Việt Nam",
            "hoatChat": [
                {"ten": "Paracetamol", "nongDo": "500mg"},
                {"ten": "Caffein", "nongDo": "65mg"},
            ],
        },
    )

    assert profile["displayName"] == "Hapacol Extra"
    assert profile["brandName"] == "Hapacol Extra"
    assert profile["dosageForm"] == "Viên nén"
    assert profile["manufacturer"] == "DHG Pharma"
    assert profile["country"] == "Việt Nam"
    assert profile["registrationNumber"] == "VD-20570-14"
    assert profile["packaging"] == "Hộp 10 vỉ x 10 viên"
    assert profile["activeIngredients"] == [
        {"name": "Paracetamol", "strength": "500mg", "source": "ddi_vn"},
        {"name": "Caffein", "strength": "65mg", "source": "ddi_vn"},
    ]
    assert "ddi_vn" in profile["sources"]


def test_merge_ndc_properties_extracts_visual_characteristics():
    service = DrugService()
    profile = service._base_metadata_profile("Tylenol")

    service._merge_ndc_properties(
        profile,
        {
            "ndc10": "66715-6557-2",
            "splSetIdItem": "88b68447-b016-4d5b-a5e3-c4ebccb14f8c",
            "packagingList": {
                "packaging": ["2 POUCH in 1 CARTON / 2 TABLET in 1 POUCH"],
            },
            "propertyConceptList": {
                "propertyConcept": [
                    {"propName": "COLORTEXT", "propValue": "white"},
                    {"propName": "COLOR", "propValue": "C48325"},
                    {"propName": "IMPRINT_CODE", "propValue": "TYLENOL;1072"},
                    {"propName": "SHAPE", "propValue": "C48345"},
                    {"propName": "SIZE", "propValue": "20 mm"},
                    {"propName": "SCORE", "propValue": "1"},
                ],
            },
        },
    )

    assert profile["identifiers"]["ndc"] == "66715-6557-2"
    assert profile["identifiers"]["setId"] == "88b68447-b016-4d5b-a5e3-c4ebccb14f8c"
    assert profile["visual"]["colors"] == ["white"]
    assert profile["visual"]["colorCodes"] == ["C48325"]
    assert profile["visual"]["imprint"] == ["TYLENOL", "1072"]
    assert profile["visual"]["shapeCode"] == "C48345"
    assert profile["visual"]["sizeMm"] == 20.0
    assert profile["visual"]["score"] == 1
    assert profile["packaging"] == "2 POUCH in 1 CARTON / 2 TABLET in 1 POUCH"
    assert "rxnorm_ndc" in profile["sources"]


def test_merge_dailymed_entry_adds_images_without_duplicates():
    service = DrugService()
    profile = service._base_metadata_profile("Tylenol")

    payload = {
        "setid": "set-123",
        "title": "TYLENOL TABLET",
        "published_date": "Mar 02, 2026",
        "images": [
            {"url": "https://example.com/pill-1.jpg", "name": "pill-1.jpg"},
            {"url": "https://example.com/pill-1.jpg", "name": "pill-1.jpg"},
        ],
    }

    service._merge_dailymed_entry(profile, payload)
    service._merge_dailymed_entry(profile, payload)

    assert profile["identifiers"]["setId"] == "set-123"
    assert profile["images"] == [
        {
            "url": "https://example.com/pill-1.jpg",
            "name": "pill-1.jpg",
            "source": "dailymed",
        }
    ]
    assert "dailymed" in profile["sources"]
    assert any("TYLENOL TABLET" in note for note in profile["notes"])
