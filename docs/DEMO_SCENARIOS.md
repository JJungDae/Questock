# Questock 기록형 데모

## 사전 조건

- 검수된 release candidate를 사용합니다.
- `QUESTOCK_SOURCE_MODE=recorded`를 사용합니다.
- live provider 또는 LLM credential을 설정하지 않습니다.
- `GET /health` 응답의 `basis_at`이
  `2026-07-26T00:00:00Z`인지 확인합니다.

UI에는 기록형 데모 데이터, 실시간 연결이 없다는 사실, 고정 기준일이
표시되어야 합니다. 뉴스와 리서치 노트는 Questock이 작성한 요약입니다.
공시는 승인된 접수번호 1건과 검증된 본문 fact 6건을 포함하지만, 전체 공시
coverage를 의미하지 않습니다.

## 실행

```powershell
docker compose build --pull --no-cache
docker compose up -d --wait
docker compose ps
```

`http://127.0.0.1:8501`에서 UI를 엽니다.

## 시나리오

| 단계 | 질문 | 예상 결과 |
|---|---|---|
| 1 | `삼성전자 최근 이슈 요약` | `complete`; 최근 기록형 뉴스 Evidence 1건 |
| 2 | `삼성전자 리포트 요약` | `complete`; Questock synthetic research note |
| 3 | `삼성전자 최근 공시 핵심` | `partial`; 검증된 본문 fact와 `insufficient_disclosure_coverage` |
| 4 | `PER이 뭐야?` | `complete`; 승인된 glossary Evidence |
| 5 | 한 세션에서 `삼성전자 최근 이슈 요약` 후 `그럼 위험 요인은?` | 종목 문맥 유지; 후속 답변은 `partial` |
| 6 | `SK하이닉스 최근 공시 요약` | `no_evidence`; 삼성전자 접수번호나 locator를 사용하지 않음 |
| 7 | `삼성전자 지금 매수해야 해?` | `blocked`; Evidence 없음 |

기록형 공시 Evidence는 다음 승인된 locator를 그대로 보존해야 합니다.

| Fact | 값 | 단위 | 실제 PDF 페이지 | DART 인쇄 페이지 | Section label |
|---|---:|---|---:|---:|---|
| 연결 매출 | `133,873,444` | `백만원` | `53` | `50` | `연결 매출` |
| 연결 영업이익 | `57,232,797` | `백만원` | `53` | `50` | `연결 영업이익` |
| DS 부문 매출 | `817,156` | `억원` | `52` | `49` | `DS 부문 매출` |
| DS 부문 영업이익 | `536,633` | `억원` | `52` | `49` | `DS 부문 영업이익` |
| 시설투자 합계 | `112,332` | `억원` | `16` | `13` | `시설투자 합계` |
| HBM4 관련 사실 | `1c D램·4나노 베이스 다이 적용 HBM4 양산 출하` | `null` | `31` | `28` | `HBM4 관련 사실` |

HBM4 항목은 텍스트 fact이므로 숫자 단위가 없습니다. 각 fact의 section
label은 traceability locator이며, 전체 공시 section 계층을 저장했다는 의미가
아닙니다.

각 답변에서 **분석 과정 보기**를 열고 다음을 확인합니다.

- 확정된 종목과 intent
- 요청 source의 상태
- hard filter, freshness, retrieval 건수
- 최종 EvidenceDecision
- live LLM을 사용할 수 없을 때의 fixed-template 생성

API smoke 세트를 실행합니다.

```powershell
uv run --no-sync python scripts/release_smoke.py --api-url http://127.0.0.1:8000/api/chat
```

## 미설정 실패 경로 데모

이 데모는 기록형 정상 시나리오와 분리해 실행합니다. 먼저 기록형 API와 UI를
종료한 뒤 두 surface를 `QUESTOCK_SOURCE_MODE=unconfigured`로 실행합니다.
UI에서 `삼성전자 최근 이슈 요약`을 질문하고 같은 요청의 API 응답도
확인합니다.

API 터미널:

```powershell
$env:QUESTOCK_SOURCE_MODE = "unconfigured"
uv run --no-sync uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

UI 터미널:

```powershell
$env:QUESTOCK_API_URL = "http://127.0.0.1:8000/api/chat"
uv run --no-sync streamlit run streamlit_app.py
```

다음을 확인합니다.

- 최종 판정은 정상적인 자료 없음이 아니라 `provider_failed`
- 요청 provider 상태는 `no_data`가 아니라 `provider_unavailable`
- `data_mode=unconfigured`
- `live_connectivity_checked=false`
- 답변은 프로젝트 소유의 sanitized fixed fallback 사용
- API 응답과 UI에 raw exception, credential, 로컬 경로, prompt 또는 source
  payload가 노출되지 않음

이 검사는 명시적인 runtime mode 검사입니다. 기록형 시나리오와 결합하거나
숨겨진 query 또는 fake query switch로 실행해서는 안 됩니다.

## 3분 코드 흐름

1. `app/api/routes_chat.py`가 public request를 검증하고 `app/runtime.py`의
   process singleton을 가져옵니다.
2. `app/runtime.py`가 source mode를 검증하고 `data/demo`를 한 번 로드한
   뒤 manifest clock을 주입하고 하나의 session store를 공유합니다.
3. `app/services/demo_source_gateway.py`가 확정된 종목과 연결된 기록형
   document만 반환하며 요청된 source 순서를 보존합니다.
4. `app/services/chat_service.py`가 planning, normalization, hard filter,
   freshness, BM25 retrieval, EvidencePolicy, budget, citation validation을
   실행합니다.
5. 비활성화된 live LLM 대신 선택된 Evidence에 근거한 프로젝트 소유
   fixed-template fallback을 생성합니다.
6. `app/ui/app.py`가 답변, source provenance, warning, 승인된 public process
   summary를 표시합니다.

## 알려진 제한

- live 뉴스, OpenDART, 리포트 provider 또는 Gemini 연결 없음
- 실제 source coverage를 확보했다는 주장 없음
- 검증된 DART 공시 1건과 본문 fact 6건만 포함하며, 실제 공시 coverage와
  전체 공시 본문은 제외
- 고정된 in-memory 익명 session만 사용하며 사용자 데이터는 영구 저장하지
  않음
- 개인화된 투자 조언을 제공하지 않음

## 종료

```powershell
docker compose down
```
