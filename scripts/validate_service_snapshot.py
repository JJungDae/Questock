from __future__ import annotations

import json
import sys

from app.services.service_snapshot import (
    SERVICE_SNAPSHOT_ID,
    ServiceSnapshotValidationError,
    load_service_snapshot,
)


def main() -> int:
    try:
        snapshot = load_service_snapshot(SERVICE_SNAPSHOT_ID)
    except ServiceSnapshotValidationError:
        print(
            json.dumps(
                {"status": "FAIL", "reason": "snapshot_validation_failed"}
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "snapshot_id": snapshot.snapshot_id,
                "document_count": len(snapshot.documents),
                "coverage": snapshot.coverage,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
