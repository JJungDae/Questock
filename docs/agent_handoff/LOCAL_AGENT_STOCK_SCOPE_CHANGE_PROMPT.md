# LOCAL_AGENT_STOCK_SCOPE_CHANGE_PROMPT.md

`docs/agent_handoff/STOCK_SCOPE_CHANGE_NOTICE.md`와 교체된 기준 문서, 다음 Task Card를 확인하세요.

- `docs/TASK_CARDS/B0-M0-01-03-planning.md`
- `docs/TASK_CARDS/M1-01-core-models.md`

변경 결정:

- P0 종목은 삼성전자·SK하이닉스·현대자동차로 확정
- NAVER 종목은 P0에서 제외
- NAVER Search API는 뉴스 provider 후보로 유지
- 공동 기사 처리를 위해 FinancialDocument와 Evidence에 회사 귀속 field를 추가
- P0는 단일 종목 질문만 지원하며 직접 종목 비교는 P0·P1·현재 M5 기본 큐에서 제외

이번 응답에서는 구현하지 마세요.

다음만 보고하세요.

1. 변경 문서 확인 결과
2. 기존 B0 기록과 변경 결정의 차이
3. M1-01에 추가된 schema·validation invariant·fixture 영향
4. 현재 남은 M0 미확인 항목
5. 수정된 M1-01 작업 전 계획과 승인 요청

M1-01 구현, dependency 설치, commit, push는 별도 승인 전까지 수행하지 마세요.
