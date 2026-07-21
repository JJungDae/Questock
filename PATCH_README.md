# LiteLLM + Gemini 2.5 Flash 무료 등급 문서 패치

프로젝트 루트에서 압축 해제하면 `docs/` 아래 파일이 교체·추가된다.

## 교체

- docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md
- docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md
- docs/agent_handoff/RISK_RESPONSE_MATRIX.md
- docs/agent_handoff/AGENT_WORKFLOW.md
- docs/TASK_CARDS/B0-M0-01-03-planning.md

## 추가

- docs/agent_handoff/LLM_STACK_DECISION.md
- docs/agent_handoff/LOCAL_AGENT_LLM_STACK_CHANGE_PROMPT.md

## 의도적으로 수정하지 않음

- `.gitignore`
- `.env.example`
- M1-01 Task Card
- app·tests·pyproject.toml
- credential 값

M1-01은 LiteLLM 도입과 독립적인 core 계약이므로 재작업하지 않는다.

기본 모델은 `gemini/gemini-2.5-flash` 무료 등급이며, 유료 모델 전환은 MVP 완성 이후 별도 결정한다.


## 검수 후 추가 보완

- 무료 등급의 데이터 이용 조건과 최소 전송 원칙
- 리포트 manifest에 `external_llm_processing_allowed` 1개 필드만 추가
- `usage_basis`는 기존 `usage_note`로 대체
- redaction pipeline은 P0에서 만들지 않음
- LLM 작업 ID를 M3-01로 통일
- LLMStatus·thinking/output/timeout 설정·sanitized live smoke gate
- LiteLLM dependency 승인·제거·lock file 산출물
