# LOCAL_AGENT_HANDOFF_README.md

## 설치 위치

이 ZIP은 프로젝트의 `docs/` 디렉터리 안에서 압축 해제한다.

예상 결과:

```text
<project-root>/
└─ docs/
   └─ agent_handoff/
      ├─ LOCAL_AGENT_HANDOFF_README.md
      ├─ LOCAL_AGENT_START_PROMPT.md
      ├─ README_AGENT_RULES.md
      ├─ PROJECT_PLAN_FINAL_PASS.md
      ├─ WORK_LOG_TEMPLATE.md
      ├─ TASK_CARD_TEMPLATE.md
      ├─ HANDOFF_TEMPLATE.md
      ├─ EXTENSION_COMPATIBILITY.md
      ├─ RISK_RESPONSE_MATRIX.md
      ├─ AGENT_WORKFLOW.md
      ├─ FINANCIAL_CAPABILITY_BASELINE.md
      └─ EVALUATION_TAXONOMY_DRAFT.md
```

저장소 루트에 ZIP 자체를 둘 필요는 없다.  
압축 해제 후 ZIP은 저장소 밖에 보관하는 편이 안전하다.

## 사용 방법

1. `docs/agent_handoff/LOCAL_AGENT_START_PROMPT.md` 내용을 로컬 에이전트에 전달한다.
2. 첫 응답에서는 구현이 아니라 저장소 초기 확인과 첫 작업 계획만 받는다.
3. 계획을 검토한 뒤 구현 범위를 승인한다.
4. 구현 결과를 확인한 뒤 commit·push·PR·merge·배포를 각각 필요한 범위만 승인한다.
5. 확인된 Step만 오늘자 작업 로그에 기록한다.

## handoff 파일 보호

이 디렉터리의 파일은 사용자 제공 입력이다.

로컬 에이전트는 사용자 승인 없이 다음을 수행하지 않는다.

- 수정
- 이동
- 삭제
- 덮어쓰기
- commit

초기 `git status`에서 이 파일들이 untracked로 표시되면 기존 사용자 작업과 구분하여 별도로 보고한다.

## 승인 전 변경이 발생한 경우

즉시 작업을 중단한다.

- 발생한 변경 파일과 diff를 사용자에게 보고한다.
- 사용자 승인 없이 reset, checkout, restore, clean, 삭제 또는 덮어쓰기를 수행하지 않는다.
- 원상 복구 방법을 제안한 뒤 사용자의 지시를 기다린다.
