# Questock Recorded Demo

## Preconditions

- use the reviewed release candidate
- use `QUESTOCK_SOURCE_MODE=recorded`
- do not configure live provider or LLM credentials
- confirm `GET /health` reports `basis_at=2026-07-26T00:00:00Z`

The UI must display recorded demo data, no live connectivity, and the fixed
basis date. News and research notes are Questock-authored summaries. The
disclosure is verified public listing metadata.

## Start

```powershell
docker compose build --pull --no-cache
docker compose up -d --wait
docker compose ps
```

Open the UI at `http://127.0.0.1:8501`.

## Scenario Script

| Step | Prompt | Expected result |
|---|---|---|
| 1 | `삼성전자 최근 이슈 요약` | `complete`; one recent recorded news Evidence |
| 2 | `삼성전자 리포트 요약` | `complete`; Questock synthetic research note |
| 3 | `삼성전자 최근 공시 핵심` | `partial`; verified receipt metadata plus coverage warning |
| 4 | `PER이 뭐야?` | `complete`; approved glossary Evidence |
| 5 | `삼성전자 최근 이슈 요약` then `그럼 위험 요인은?` in one session | security context preserved; follow-up is `partial` |
| 6 | `SK하이닉스 최근 공시 요약` | `no_evidence`; no Samsung receipt or locator |
| 7 | `삼성전자 지금 매수해야 해?` | `blocked`; no Evidence |

For each response, open **분석 과정 보기** and confirm:

- resolved security and intent
- requested source status
- hard-filter, freshness, and retrieval counts
- final EvidenceDecision
- fixed-template generation when the live LLM is unavailable

Run the API smoke set:

```powershell
uv run --no-sync python scripts/release_smoke.py --api-url http://127.0.0.1:8000/api/chat
```

## Three-Minute Code Flow

1. `app/api/routes_chat.py` validates the public request and retrieves the
   process singleton from `app/runtime.py`.
2. `app/runtime.py` validates the source mode, loads `data/demo` once, injects
   the manifest clock, and shares one session store.
3. `app/services/demo_source_gateway.py` returns only recorded documents
   connected to the resolved security and preserves requested source order.
4. `app/services/chat_service.py` runs planning, normalization, hard filtering,
   freshness, BM25 retrieval, EvidencePolicy, budget, and citation validation.
5. The disabled live LLM produces a project-owned fixed-template fallback
   grounded in selected Evidence.
6. `app/ui/app.py` renders the answer, source provenance, warnings, and the
   approved public process summary.

## Known Limits

- no live news, OpenDART, report provider, or Gemini connectivity
- no claim of actual source coverage
- one verified DART listing item; report-body facts are excluded
- fixed in-memory anonymous sessions; no persistent user data
- no personalized investment advice

## Cleanup

```powershell
docker compose down
```
