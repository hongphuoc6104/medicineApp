import re


class NerPostFilter:
    """Heuristic post-filter to remove obvious non-drug OCR blocks."""

    DOSAGE_RE = re.compile(
        r"(uống|ngày\s+\d|lần\s*,|sau\s*ăn|trước\s*ăn|"
        r"sáng\s+uống|trưa\s+uống|tối\s+uống|"
        r"mỗi\s+lần|hòa\s+tan|nhỏ\s+mắt)",
        re.IGNORECASE,
    )
    PURE_NUM_RE = re.compile(r"^[\d\s.,]+$")
    UNIT_ONLY_RE = re.compile(
        r"^(viên\s+sủi|viên|ống|lọ|tab|gói)(\s+[\d\s]*)?$",
        re.IGNORECASE,
    )
    DOSAGE_ONLY_RE = re.compile(
        r"^[\d\s.,]*(mg|ml|mcg|g|iu)\b",
        re.IGNORECASE,
    )
    HEADER_RE = re.compile(
        r"(đơn\s+thuốc|bhyt|bệnh\s+viện|phòng\s+khám|"
        r"họ\s+tên|giới\s+tính|địa\s+chỉ|chẩn\s+đoán|"
        r"thuốc\s+điều\s+trị|mã\s+số|số\s+phiếu|"
        r"bộ\s+y\s+tế|sở\s+y\s+tế|xem\s+tiếp)",
        re.IGNORECASE,
    )

    @staticmethod
    def is_likely_drug(text: str) -> bool:
        txt = (text or "").strip()
        if len(txt) < 4:
            return False

        if txt.casefold() in {"viên sủi", "vien sui"}:
            return False

        if (
            NerPostFilter.DOSAGE_RE.search(txt)
            or NerPostFilter.PURE_NUM_RE.match(txt)
            or NerPostFilter.UNIT_ONLY_RE.match(txt)
            or NerPostFilter.DOSAGE_ONLY_RE.match(txt)
            or NerPostFilter.HEADER_RE.search(txt)
        ):
            return False

        return True
