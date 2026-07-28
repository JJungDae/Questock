from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree

from app.services.m5_d1_inventory import (
    DISCLOSURE_WINDOW_END,
    DISCLOSURE_WINDOW_START,
    M5_D1_INVENTORY_PATH,
    SECURITY_DART_IDENTITIES,
    M5D1InventoryError,
    build_source_inventory_payload,
    normalize_disclosure_inventory,
    normalize_news_inventory,
    validate_corp_code_registry,
    write_source_inventory,
)
from scripts.collect_m5_news_snapshot import (
    NAVER_ENDPOINT,
    collect_m5_news,
)
from scripts.collect_naver_news_snapshot import (
    NaverApiHubNewsTransport,
    NewsCollectionError,
    collect_news_query_pages,
)

DEFAULT_RAW_ROOT = Path("var/service_completion/m5_d1/raw")
MAX_NAVER_REQUESTS = 120
MAX_OPENDART_REQUESTS = 30
OPENDART_CORP_CODE_ENDPOINT = (
    "https://opendart.fss.or.kr/api/corpCode.xml"
)
OPENDART_LIST_ENDPOINT = "https://opendart.fss.or.kr/api/list.json"
OPENDART_QUERY_SPECS = (
    ("A", "A", None),
    ("B", "B", None),
    ("C", "C", None),
    ("E", "E", None),
    ("I", "I", None),
)
_FILTERED_DART_RAW_RE = re.compile(
    r"^KRX-(?P<stock_code>\d{6})-(?:A|B|C|E|I)"
    r"-page-\d+\.json$"
)
NEWS_EXPANSION_QUERIES = {
    "KRX:005930": (
        "삼성전자",
        "삼전",
        "삼성전자 반도체",
        "삼성전자 HBM",
        "삼성전자 파운드리",
        "삼성전자 주가",
    ),
    "KRX:000660": (
        "SK하이닉스",
        "하이닉스",
        "SK하이닉스 HBM",
        "SK하이닉스 반도체",
        "SK하이닉스 실적",
        "SK하이닉스 주가",
    ),
    "KRX:005380": (
        "현대차",
        "현대자동차",
        "현대차 실적",
        "현대차 전기차",
        "현대차 판매",
        "현대차 주가",
    ),
}


class OpenDartInventoryTransport:
    def __init__(self, *, api_key: str) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise M5D1InventoryError("OpenDART credential is unavailable")
        self._api_key = api_key.strip()
        self.request_count = 0

    def corporation_registry(self) -> tuple[dict[str, str], ...]:
        payload = self._request_binary(
            OPENDART_CORP_CODE_ENDPOINT,
            {"crtfc_key": self._api_key},
        )
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                names = archive.namelist()
                if len(names) != 1:
                    raise M5D1InventoryError(
                        "OpenDART corporation registry is invalid"
                    )
                root = ElementTree.fromstring(archive.read(names[0]))
        except (
            OSError,
            ValueError,
            zipfile.BadZipFile,
            ElementTree.ParseError,
        ):
            raise M5D1InventoryError(
                "OpenDART corporation registry is invalid"
            ) from None
        entries = []
        for item in root.findall("list"):
            entries.append(
                {
                    "corp_code": item.findtext("corp_code", ""),
                    "corp_name": item.findtext("corp_name", ""),
                    "stock_code": item.findtext("stock_code", ""),
                    "modify_date": item.findtext("modify_date", ""),
                }
            )
        if not entries:
            raise M5D1InventoryError(
                "OpenDART corporation registry is invalid"
            )
        return tuple(entries)

    def disclosure_pages(
        self,
        *,
        corp_code: str,
        disclosure_type: str,
        disclosure_detail_type: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        pages: list[dict[str, Any]] = []
        page_no = 1
        while True:
            parameters: dict[str, object] = {
                "crtfc_key": self._api_key,
                "corp_code": corp_code,
                "bgn_de": DISCLOSURE_WINDOW_START.strftime("%Y%m%d"),
                "end_de": DISCLOSURE_WINDOW_END.strftime("%Y%m%d"),
                "last_reprt_at": "N",
                "pblntf_ty": disclosure_type,
                "page_no": page_no,
                "page_count": 100,
                "sort": "date",
                "sort_mth": "asc",
            }
            if disclosure_detail_type is not None:
                parameters["pblntf_detail_ty"] = disclosure_detail_type
            payload = self._request_json(
                OPENDART_LIST_ENDPOINT,
                parameters,
            )
            status = payload.get("status")
            if status == "013":
                return tuple(pages)
            if (
                status != "000"
                or not isinstance(payload.get("list"), list)
                or type(payload.get("total_page")) is not int
                or payload["total_page"] < 1
            ):
                raise M5D1InventoryError(
                    "OpenDART disclosure response is invalid"
                )
            pages.append(payload)
            if page_no >= payload["total_page"]:
                return tuple(pages)
            page_no += 1

    def _request_json(
        self,
        endpoint: str,
        parameters: dict[str, object],
    ) -> dict[str, Any]:
        payload = self._request_binary(endpoint, parameters)
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise M5D1InventoryError(
                "OpenDART response is invalid"
            ) from None
        if not isinstance(value, dict):
            raise M5D1InventoryError("OpenDART response is invalid")
        return value

    def _request_binary(
        self,
        endpoint: str,
        parameters: dict[str, object],
    ) -> bytes:
        if self.request_count >= MAX_OPENDART_REQUESTS:
            raise M5D1InventoryError(
                "OpenDART request budget is exhausted"
            )
        query = urllib.parse.urlencode(parameters)
        request = urllib.request.Request(
            f"{endpoint}?{query}",
            headers={"User-Agent": "Questock-M5-D1-Inventory/1.0"},
            method="GET",
        )
        self.request_count += 1
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.read()
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
        ):
            raise M5D1InventoryError(
                "OpenDART request failed"
            ) from None


def collect_source_inventory(
    *,
    naver_transport: NaverApiHubNewsTransport | None,
    opendart_transport: OpenDartInventoryTransport | None,
    raw_root: Path,
    output_path: Path,
    collected_at: datetime,
    reuse_news_raw: bool = False,
    expand_news: bool = False,
    reuse_dart_raw: bool = False,
) -> dict[str, Any]:
    news_raw_dir = raw_root / "news"
    news_expansion_raw_dir = raw_root / "news_expansion"
    dart_raw_dir = raw_root / "dart"
    if reuse_news_raw:
        news_runs = load_news_runs_from_raw(
            news_raw_dir,
            expected_files_per_security=16,
        )
    else:
        if naver_transport is None:
            raise M5D1InventoryError("Naver transport is unavailable")
        news_runs = collect_m5_news(
            transport=naver_transport,
            raw_dir=news_raw_dir,
        )
    if expand_news:
        if naver_transport is None:
            raise M5D1InventoryError("Naver transport is unavailable")
        expansion_runs = collect_news_expansion(
            transport=naver_transport,
            raw_dir=news_expansion_raw_dir,
        )
        news_runs = _merge_news_runs(news_runs, expansion_runs)
    elif news_expansion_raw_dir.exists():
        expansion_runs = load_news_runs_from_raw(
            news_expansion_raw_dir,
            expected_files_per_security=6,
        )
        news_runs = _merge_news_runs(news_runs, expansion_runs)
    naver_calls = sum(run["api_call_count"] for run in news_runs)
    if naver_calls > MAX_NAVER_REQUESTS:
        raise M5D1InventoryError("Naver request budget is exhausted")
    news_items, news_rejections = normalize_news_inventory(
        {
            run["security_id"]: run["items"]
            for run in news_runs
        },
        collected_at=collected_at,
    )

    if reuse_dart_raw:
        corp_registry, raw_disclosures, opendart_calls = (
            load_dart_inventory_from_raw(
                dart_raw_dir,
                prior_inventory_path=output_path,
            )
        )
    else:
        if opendart_transport is None:
            raise M5D1InventoryError("OpenDART transport is unavailable")
        registry_entries = opendart_transport.corporation_registry()
        corp_registry = validate_corp_code_registry(registry_entries)
        raw_disclosures = {
            security_id: [] for security_id in SECURITY_DART_IDENTITIES
        }
        dart_raw_dir.mkdir(parents=True, exist_ok=True)
        for security_id, (_stock_code, corp_code, _name) in (
            SECURITY_DART_IDENTITIES.items()
        ):
            safe_id = security_id.replace(":", "-")
            for query_label, disclosure_type, detail_type in (
                OPENDART_QUERY_SPECS
            ):
                pages = opendart_transport.disclosure_pages(
                    corp_code=corp_code,
                    disclosure_type=disclosure_type,
                    disclosure_detail_type=detail_type,
                )
                for page_index, page in enumerate(pages, start=1):
                    (
                        dart_raw_dir
                        / (
                            f"{safe_id}-{query_label}"
                            f"-page-{page_index}.json"
                        )
                    ).write_text(
                        json.dumps(
                            page,
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    raw_disclosures[security_id].extend(
                        item
                        for item in page["list"]
                        if isinstance(item, dict)
                    )
        opendart_calls = opendart_transport.request_count
    disclosure_items = normalize_disclosure_inventory(raw_disclosures)
    payload = build_source_inventory_payload(
        news_items=news_items,
        disclosure_items=disclosure_items,
        corp_registry=corp_registry,
        news_rejections=news_rejections,
        collected_at=collected_at,
        provider_calls={
            "naver": naver_calls,
            "opendart": opendart_calls,
        },
    )
    write_source_inventory(payload, output_path)
    return payload


def load_news_runs_from_raw(
    raw_dir: Path,
    *,
    expected_files_per_security: int,
) -> tuple[dict[str, Any], ...]:
    grouped: dict[str, list[dict[str, Any]]] = {
        security_id: [] for security_id in SECURITY_DART_IDENTITIES
    }
    call_counts = {
        security_id: 0 for security_id in SECURITY_DART_IDENTITIES
    }
    file_counts = {
        security_id: 0 for security_id in SECURITY_DART_IDENTITIES
    }
    try:
        paths = sorted(raw_dir.glob("*.json"))
    except OSError:
        raise M5D1InventoryError(
            "reused Naver raw inventory is unavailable"
        ) from None
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise M5D1InventoryError(
                "reused Naver raw inventory is invalid"
            ) from None
        if (
            not isinstance(payload, dict)
            or payload.get("security_id") not in grouped
            or not isinstance(payload.get("query"), str)
            or not isinstance(payload.get("pages"), list)
        ):
            raise M5D1InventoryError(
                "reused Naver raw inventory is invalid"
            )
        security_id = payload["security_id"]
        query = payload["query"]
        file_counts[security_id] += 1
        call_counts[security_id] += len(payload["pages"])
        for page_index, page in enumerate(payload["pages"]):
            if not isinstance(page, dict):
                raise M5D1InventoryError(
                    "reused Naver raw inventory is invalid"
                )
            items = page.get("items")
            if not isinstance(items, list):
                raise M5D1InventoryError(
                    "reused Naver raw inventory is invalid"
                )
            grouped[security_id].extend(
                {
                    **item,
                    "_questock_query_provenance": (
                        f"{query}|reused_raw|"
                        f"start={1 + page_index * 100}"
                    ),
                }
                for item in items
                if isinstance(item, dict)
            )
    if (
        not paths
        or any(
            count != expected_files_per_security
            for count in file_counts.values()
        )
    ):
        raise M5D1InventoryError(
            "reused Naver raw inventory coverage is invalid"
        )
    return tuple(
        {
            "security_id": security_id,
            "items": grouped[security_id],
            "api_call_count": call_counts[security_id],
        }
        for security_id in SECURITY_DART_IDENTITIES
    )


def load_dart_inventory_from_raw(
    raw_dir: Path,
    *,
    prior_inventory_path: Path,
) -> tuple[
    dict[str, dict[str, str]],
    dict[str, list[dict[str, Any]]],
    int,
]:
    try:
        prior_payload = json.loads(
            prior_inventory_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise M5D1InventoryError(
            "prior OpenDART inventory is unavailable"
        ) from None
    corp_registry = prior_payload.get("corp_registry")
    provider_calls = prior_payload.get("provider_calls")
    if (
        not isinstance(corp_registry, dict)
        or not isinstance(provider_calls, dict)
        or type(provider_calls.get("opendart")) is not int
        or provider_calls["opendart"] < 1
    ):
        raise M5D1InventoryError(
            "prior OpenDART inventory is invalid"
        )
    _validate_reused_corp_registry(corp_registry)
    raw_disclosures: dict[str, list[dict[str, Any]]] = {
        security_id: [] for security_id in SECURITY_DART_IDENTITIES
    }
    labels_by_security: dict[str, set[str]] = {
        security_id: set() for security_id in SECURITY_DART_IDENTITIES
    }
    stock_to_security = {
        stock_code: security_id
        for security_id, (
            stock_code,
            _corp_code,
            _name,
        ) in SECURITY_DART_IDENTITIES.items()
    }
    try:
        paths = sorted(raw_dir.glob("*.json"))
    except OSError:
        raise M5D1InventoryError(
            "reused OpenDART raw inventory is unavailable"
        ) from None
    for path in paths:
        match = _FILTERED_DART_RAW_RE.fullmatch(path.name)
        if match is None:
            continue
        security_id = stock_to_security.get(match.group("stock_code"))
        if security_id is None:
            raise M5D1InventoryError(
                "reused OpenDART raw inventory is invalid"
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise M5D1InventoryError(
                "reused OpenDART raw inventory is invalid"
            ) from None
        if (
            not isinstance(payload, dict)
            or payload.get("status") != "000"
            or not isinstance(payload.get("list"), list)
        ):
            raise M5D1InventoryError(
                "reused OpenDART raw inventory is invalid"
            )
        labels_by_security[security_id].add(path.name.rsplit("-page-", 1)[0])
        raw_disclosures[security_id].extend(
            item
            for item in payload["list"]
            if isinstance(item, dict)
        )
    if any(len(labels) < 4 for labels in labels_by_security.values()):
        raise M5D1InventoryError(
            "reused OpenDART raw inventory coverage is invalid"
        )
    return (
        {
            security_id: {
                key: str(value)
                for key, value in corp_registry[security_id].items()
            }
            for security_id in SECURITY_DART_IDENTITIES
        },
        raw_disclosures,
        provider_calls["opendart"],
    )


def _validate_reused_corp_registry(
    corp_registry: dict[str, Any],
) -> None:
    if set(corp_registry) != set(SECURITY_DART_IDENTITIES):
        raise M5D1InventoryError(
            "prior OpenDART corporation registry is invalid"
        )
    for security_id, (
        stock_code,
        corp_code,
        expected_name,
    ) in SECURITY_DART_IDENTITIES.items():
        item = corp_registry.get(security_id)
        if (
            not isinstance(item, dict)
            or item.get("stock_code") != stock_code
            or item.get("corp_code") != corp_code
            or expected_name not in str(item.get("corp_name"))
            or item.get("verification_status")
            != "verified_official_api"
        ):
            raise M5D1InventoryError(
                "prior OpenDART corporation registry is invalid"
            )


def collect_news_expansion(
    *,
    transport: NaverApiHubNewsTransport,
    raw_dir: Path,
) -> tuple[dict[str, Any], ...]:
    if raw_dir.exists() and any(raw_dir.glob("*.json")):
        raise M5D1InventoryError(
            "Naver expansion raw inventory already exists"
        )
    raw_dir.mkdir(parents=True, exist_ok=True)
    output: list[dict[str, Any]] = []
    for security_id, queries in NEWS_EXPANSION_QUERIES.items():
        items: list[dict[str, Any]] = []
        call_count = 0
        safe_id = security_id.replace(":", "-")
        for query_index, query in enumerate(queries, start=1):
            pages = collect_news_query_pages(
                query=query,
                sort="date",
                display=100,
                max_calls=3,
                timeout_seconds=15,
                transport=transport,
            )
            call_count += len(pages)
            raw_path = raw_dir / f"{safe_id}-q{query_index}.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "security_id": security_id,
                        "query": query,
                        "pages": pages,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            for page_index, page in enumerate(pages):
                raw_items = page.get("items")
                if not isinstance(raw_items, list):
                    continue
                items.extend(
                    {
                        **item,
                        "_questock_query_provenance": (
                            f"{query}|date|"
                            f"start={1 + page_index * 100}"
                        ),
                    }
                    for item in raw_items
                    if isinstance(item, dict)
                )
        output.append(
            {
                "security_id": security_id,
                "items": items,
                "api_call_count": call_count,
            }
        )
    return tuple(output)


def _merge_news_runs(
    first: tuple[dict[str, Any], ...],
    second: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    first_by_security = {
        run.get("security_id"): run for run in first
    }
    second_by_security = {
        run.get("security_id"): run for run in second
    }
    if (
        set(first_by_security) != set(SECURITY_DART_IDENTITIES)
        or set(second_by_security) != set(SECURITY_DART_IDENTITIES)
    ):
        raise M5D1InventoryError("Naver run coverage is invalid")
    return tuple(
        {
            "security_id": security_id,
            "items": [
                *first_by_security[security_id]["items"],
                *second_by_security[security_id]["items"],
            ],
            "api_call_count": (
                first_by_security[security_id]["api_call_count"]
                + second_by_security[security_id]["api_call_count"]
            ),
        }
        for security_id in SECURITY_DART_IDENTITIES
    )


def _dotenv(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise M5D1InventoryError(
            "credential file is unavailable"
        ) from None
    output: dict[str, str] = {}
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        normalized = value.strip()
        if (
            len(normalized) >= 2
            and normalized[0] == normalized[-1]
            and normalized[0] in {"'", '"'}
        ):
            normalized = normalized[1:-1]
        output[key.strip()] = normalized
    return output


def _credential(
    name: str,
    dotenv: dict[str, str],
) -> str:
    value = os.getenv(name) or dotenv.get(name)
    if not isinstance(value, str) or not value.strip():
        raise M5D1InventoryError("credentials are not configured")
    return value.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect the M5-D1 news and OpenDART source inventory.",
    )
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output", type=Path, default=M5_D1_INVENTORY_PATH)
    parser.add_argument(
        "--reuse-news-raw",
        action="store_true",
        help="Reuse the prior ignored Naver raw collection.",
    )
    parser.add_argument(
        "--expand-news",
        action="store_true",
        help="Add the bounded event-neutral Naver expansion collection.",
    )
    parser.add_argument(
        "--reuse-dart-raw",
        action="store_true",
        help="Reuse the prior ignored filtered OpenDART collection.",
    )
    arguments = parser.parse_args(argv)
    try:
        dotenv = _dotenv(arguments.env_file)
        payload = collect_source_inventory(
            naver_transport=(
                None
                if arguments.reuse_news_raw and not arguments.expand_news
                else NaverApiHubNewsTransport(
                    endpoint=NAVER_ENDPOINT,
                    client_id=_credential("NAVER_CLIENT_ID", dotenv),
                    client_secret=_credential(
                        "NAVER_CLIENT_SECRET",
                        dotenv,
                    ),
                )
            ),
            opendart_transport=OpenDartInventoryTransport(
                api_key=_credential("OPENDART_API_KEY", dotenv),
            )
            if not arguments.reuse_dart_raw
            else None,
            raw_root=arguments.raw_root,
            output_path=arguments.output,
            collected_at=datetime.now(UTC),
            reuse_news_raw=arguments.reuse_news_raw,
            expand_news=arguments.expand_news,
            reuse_dart_raw=arguments.reuse_dart_raw,
        )
    except (
        M5D1InventoryError,
        NewsCollectionError,
        OSError,
    ):
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "m5_d1_inventory_collection_failed",
                },
                separators=(",", ":"),
            )
        )
        return 1
    coverage = payload["coverage"]
    print(
        json.dumps(
            {
                "status": "PASS",
                "provider_calls": payload["provider_calls"],
                "news_counts": {
                    key: value["total"]
                    for key, value in coverage["news"].items()
                },
                "disclosure_counts": {
                    key: value["total"]
                    for key, value in coverage["disclosures"].items()
                },
                "source_sha256": payload["source_sha256"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
