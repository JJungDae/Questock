# Questock

Questock is an evidence-grounded Korean stock RAG prototype. The current local slice verifies deterministic fixture readiness for one reference security and does not check live provider connectivity.

## Requirements

- Python 3.11 or newer
- Run commands from the repository root

Install the approved local dependencies:

```powershell
python -m pip install --target .deps "pydantic>=2.7,<3" "fastapi>=0.115,<1" "uvicorn>=0.30,<1" "pytest>=8,<9" "httpx>=0.27,<1"
```

Empty environment placeholders are documented in `.env.example`. Keep real values only in a local `.env` file and do not commit or print them.

## Fixture Readiness

M1-08 checks a fixed Samsung Electronics fixture slice using recorded news, recorded disclosure, synthetic manual research-report sections, and the approved local glossary corpus. `live_connectivity_checked` is always `false`; recorded fixtures do not prove NAVER, OpenDART, report-source, or LLM availability.

Run the fixed CLI:

```powershell
$env:PYTHONPATH = ".deps;."; python scripts/m1_phase_slice.py
```

CLI exit codes:

- `0`: ok
- `1`: degraded
- `2`: error

## Health API

Run the local API:

```powershell
$env:PYTHONPATH = ".deps;."; python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Example request:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

`GET /health` reports fixture readiness only. It does not perform live API or LLM calls.

## Secret Scan

Run:

```powershell
python scripts/secret_scan.py
```

Secret scan exit codes:

- `0`: no findings
- `1`: one or more potential findings
- `2`: scanner failure

## Tests

Targeted M1-08 tests:

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q
```

M1-01 through M1-08 regression:

```powershell
$env:PYTHONPATH = ".deps;."; python -m pytest tests/unit/test_core_models.py tests/unit/test_status_contracts.py tests/unit/test_security_resolver.py tests/unit/test_provider_base.py tests/unit/test_config.py tests/unit/test_news_provider.py tests/unit/test_disclosure_provider.py tests/unit/test_report_ingest.py tests/unit/test_glossary_ingest.py tests/unit/test_health_phase_slice.py tests/unit/test_secret_scan.py tests/unit/test_api_health.py -q
```
