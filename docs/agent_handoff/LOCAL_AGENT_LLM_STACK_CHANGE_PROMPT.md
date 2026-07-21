LiteLLM+Gemini 채택 문서를 적용했습니다.

확인 파일:
- docs/agent_handoff/LLM_STACK_DECISION.md
- docs/agent_handoff/PROJECT_PLAN_FINAL_PASS.md
- docs/agent_handoff/FINANCIAL_CAPABILITY_BASELINE.md
- docs/agent_handoff/RISK_RESPONSE_MATRIX.md
- docs/agent_handoff/AGENT_WORKFLOW.md
- docs/TASK_CARDS/B0-M0-01-03-planning.md

결정:
- `LLMClient → LiteLLM Python SDK → Gemini`
- 기본 모델 `gemini/gemini-2.5-flash` 무료 등급
- 유료 모델 검토는 MVP end-to-end 완성 이후
- credential `GEMINI_API_KEY`
- Proxy·Router·자동 fallback·multi-LLM·Search Grounding·유료 모델 전환은 MVP 완성 전 제외
- M1-01 core model은 변경하지 않음
- 실제 LiteLLM dependency와 adapter 구현은 M3-01에서 별도 승인

이번에는 문서 정합성만 확인하고 다음을 보고하세요.
1. 현재 코드와 새 결정의 충돌 여부
2. M1-02 진행에 영향이 없는지
3. M3-01에서 추가할 파일·dependency·LLMStatus·data gate·live smoke 계획

코드 수정, dependency 설치, live Gemini 호출, billing 연결, commit·push는 별도 승인 전 수행하지 마세요.
