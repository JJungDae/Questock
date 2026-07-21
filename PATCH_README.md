# PATCH_README.md

## 적용 방법

이 ZIP을 프로젝트 루트에서 압축 해제하면 다음 파일이 교체·추가된다.

```text
docs/agent_handoff/
docs/TASK_CARDS/
```

기존 파일을 덮어쓰기 전에 Git diff 또는 별도 백업으로 현재 내용을 확인한다.

## 교체 파일

- PROJECT_PLAN_FINAL_PASS.md
- FINANCIAL_CAPABILITY_BASELINE.md
- RISK_RESPONSE_MATRIX.md
- EXTENSION_COMPATIBILITY.md
- EVALUATION_TAXONOMY_DRAFT.md
- AGENT_WORKFLOW.md
- B0-M0-01-03-planning.md
- M1-01-core-models.md

## 추가 파일

- STOCK_SCOPE_CHANGE_NOTICE.md
- LOCAL_AGENT_STOCK_SCOPE_CHANGE_PROMPT.md

README_AGENT_RULES.md와 승인·Git 안전 절차는 변경하지 않는다.


## 이번 최종 정합성 수정

- RISK_RESPONSE_MATRIX의 R30 요약 행과 상세 행 구조 복구
- 리포트 schema의 단일 security_id 제거
- FinancialDocument·Evidence scope별 validation 불변조건 추가
- 세 종목 각각 뉴스·공시·리포트 golden coverage 충족
- 공식 P0 범위를 세 종목으로 통일
- B0 승인 상태와 미확인 목록 충돌 제거
- A23-M/A23-H 범위 정합성 수정
- 직접 종목 비교를 현재 기본 큐에서 제외
