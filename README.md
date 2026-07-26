# Questock

Questock is an evidence-grounded Korean stock RAG prototype for Samsung
Electronics, SK hynix, and Hyundai Motor. The release runtime is a deterministic
recorded demo: it does not call live news, OpenDART, research-report, or LLM
providers.

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
- `QUESTOCK_IMAGE_TAG`: immutable release SHA for release builds
- `QUESTOCK_API_URL`: Streamlit chat endpoint
- `QUESTOCK_UI_TIMEOUT_SECONDS`: UI request timeout
- provider and LLM variable names remain documented for deferred work only

The recorded release requires no provider or LLM credential.

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

- News and research-note text is a short Questock-authored synthetic summary
  with a public reference URL.
- The DART item contains human-approved receipt and listing metadata only.
- The fixed basis timestamp comes from the manifest, not the system clock.
- The demo corpus is scenario evidence, not proof of actual source coverage.
- Live Gemini and live provider integration remain not activated.

Questock provides evidence-oriented information, not personalized investment
advice, price targets, buy or sell instructions, or guaranteed forecasts.
