import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from apps.logistics.services.normalization import to_integer
from apps.logistics.services.validation import validate_route_record
from apps.logistics.services.workbook import (
    build_payload_groups,
    extract_reference_data,
    frame_records,
    read_workbook,
)


def main() -> None:
    dataset_path = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR / "data" / "dataset.xlsx"
    frames = read_workbook(dataset_path.read_bytes())
    offices, priorities, points = extract_reference_data(frames)
    payload_groups = build_payload_groups(frames["route_payload"])
    geographic_points = {point["id"]: point for point in points}
    seen_source_ids: set[int] = set()
    seen_business_keys: set[tuple] = set()
    valid = 0
    rejected = 0
    codes: Counter[str] = Counter()

    for row in frame_records(frames["routes"]):
        route_id = to_integer(row.get("idRoute"))
        payloads = payload_groups.get(route_id, []) if route_id is not None else []
        result = validate_route_record(
            row,
            payloads[0] if payloads else None,
            office_ids={office["id"] for office in offices},
            priority_ids={priority["id"] for priority in priorities},
            geographic_points=geographic_points,
            seen_source_ids=seen_source_ids,
            seen_business_keys=seen_business_keys,
            duplicate_payload=len(payloads) > 1,
        )
        if result.is_valid:
            valid += 1
        else:
            rejected += 1
            codes.update(issue.code for issue in result.issues)

    print(
        json.dumps(
            {
                "dataset": str(dataset_path),
                "total_rows": valid + rejected,
                "valid_rows": valid,
                "rejected_rows": rejected,
                "issue_counts": dict(codes.most_common()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

