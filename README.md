# Questock

Questock is an evidence-grounded Korean stock RAG prototype for Samsung
Electronics, SK hynix, and Hyundai Motor. The recorded runtime supports the
release demo and the approved immutable service snapshot. Neither mode calls
live news, OpenDART, research-report, or LLM providers.

## Runtime Flow

```text
FastAPI ChatRequest
-> process-level runtime and SourceGateway
-> QueryPlanner and security resolution
-> Evidence normalization, hard filter, and freshness
-> lexical retrieval and EvidencePolicy
-> context budget and citation validation
-> fixed-template answer fallback
-> public process summary
-> Streamlit UI
```

The main implementation boundaries are:

- `app/runtime.py`: mode selection, fixed demo clock, and singleton service
- `app/services/demo_source_gateway.py`: recorded corpus loader and gateway
- `app/services/service_snapshot.py`: immutable service snapshot validation
- `app/services/service_snapshot_gateway.py`: recorded snapshot gateway
- `app/services/chat_service.py`: orchestration
- `app/ui/app.py`: user-facing answer and process view
- `data/demo/manifest.json`: recorded corpus version and fixed basis timestamp

## Setup

Use the locked environment from the repository root:

```powershell
uv sync --locked --extra dev
```

Real credentials belong only in local environment variables or an untracked
environment file. `.env.example` contains names and empty placeholders only.
Questock does not automatically load `.env` files.

## Local Run

Recorded API:

```powershell
$env:QUESTOCK_SOURCE_MODE = "recorded"
uv run --no-sync uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Approved service snapshot API:

```powershell
$env:QUESTOCK_SOURCE_MODE = "recorded"
$env:QUESTOCK_SNAPSHOT_ID = "svc-20260724-1402"
uv run --no-sync uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Recorded UI in a second terminal:

```powershell
$env:QUESTOCK_API_URL = "http://127.0.0.1:8000/api/chat"
$env:QUESTOCK_UI_TIMEOUT_SECONDS = "21"
uv run --no-sync streamlit run streamlit_app.py
```

Endpoints:

- API health: `http://127.0.0.1:8000/health`
- API chat: `http://127.0.0.1:8000/api/chat`
- UI: `http://127.0.0.1:8501`

Unset or empty `QUESTOCK_SOURCE_MODE` selects `unconfigured`. That mode returns
a truthful provider-unavailable fallback and does not silently switch to live
data.

## Container Run

Compose uses one non-root image for API and UI. The API host port is loopback
only; the UI is exposed on port 8501.

```powershell
docker compose build --pull --no-cache
docker compose up -d --wait
docker compose ps
```

Cleanup is scoped to this project:

```powershell
docker compose down
```

## Configuration

- `QUESTOCK_SOURCE_MODE`: `unconfigured` or `recorded`
- `QUESTOCK_SNAPSHOT_ID`: empty for the release demo or
  `svc-20260724-1402` for the approved service snapshot
- `QUESTOCK_IMAGE_TAG`: immutable release SHA for release builds
- `QUESTOCK_API_URL`: Streamlit chat endpoint
- `QUESTOCK_UI_TIMEOUT_SECONDS`: UI request timeout
- `QUESTOCK_LLM_MODE`: `disabled` or `gemini`
- `QUESTOCK_REQUEST_PROTECTION_ENABLED`: application request limits
- `QUESTOCK_RESPONSE_CACHE_ENABLED`: bounded 90-second response cache

The recorded fixed-generation mode requires no provider or LLM credential.
Gemini mode requires an API credential in the API process only.

The approved live-generation contract is `gemini/gemini-3.5-flash` with
`LLM_THINKING_LEVEL=minimal`, `LLM_MAX_OUTPUT_TOKENS=1024`,
`LLM_TIMEOUT_SECONDS=10`, and retry `0`. The legacy
`LLM_THINKING_BUDGET` setting is rejected. One separately approved sanitized
Gemini smoke passed; FSC-2 implementation remains pending Human Owner review.

## Verification

```powershell
uv run --no-sync ruff check --select E4,E7,E9,F app tests scripts streamlit_app.py
uv run --no-sync pytest tests -q
uv run --no-sync python scripts/m3_gate.py
uv run --no-sync python scripts/secret_scan.py
uv run --no-sync python -m compileall app tests scripts -q
```

The release smoke script targets a running recorded API:

```powershell
uv run --no-sync python scripts/release_smoke.py --api-url http://127.0.0.1:8000/api/chat
```

## Data Boundary

- Service-snapshot news contains only Human Owner-approved, Questock-authored
  short summaries and public reference URLs.
- Service-snapshot research reports contain only verified structured facts and
  Questock-authored short summaries. Source PDFs, excerpts, and raw text are
  excluded, and report Evidence is not eligible for external LLM processing.
- The DART item contains a Human Owner-approved receipt and six verified body
  facts. It preserves each approved value and unit, physical PDF page, DART
  printed page, and fact-specific section locator.
- The DART item is not the full disclosure body and does not establish actual
  disclosure coverage.
- The fixed basis timestamp comes from the manifest, not the system clock.
- The demo corpus is scenario evidence, not proof of actual source coverage.
- Live Gemini and live provider integration remain not activated.

Questock provides evidence-oriented information, not personalized investment
advice, price targets, buy or sell instructions, or guaranteed forecasts.
