#!/usr/bin/env python3
"""Canonical scan-contract fields for manual or automated audits."""

FIELDS = [
    "qualityState",
    "rejectReason",
    "guidance",
    "drugs",
    "mergedDrugs",
    "mappingStatus",
    "converged",
    "occurrenceId",
]


def main() -> None:
    print("medicineApp scan contract fields")
    for field in FIELDS:
        print(f"- {field}")


if __name__ == "__main__":
    main()
