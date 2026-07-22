from __future__ import annotations

import asyncio
import json
import sys

from app.health import build_error_payload, build_health_payload


def _exit_code(status: object) -> int:
    if status == "ok":
        return 0
    if status == "degraded":
        return 1
    return 2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        payload = build_error_payload({"status": "error"})
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        sys.stdout.write("\n")
        return 2
    try:
        payload = asyncio.run(build_health_payload())
    except Exception:
        payload = build_error_payload({"status": "error"})
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    sys.stdout.write("\n")
    return _exit_code(payload.get("status"))


if __name__ == "__main__":
    raise SystemExit(main())
