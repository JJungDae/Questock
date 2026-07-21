# STOCK_SCOPE_CHANGE_NOTICE.md

## 결정

M0 지원 종목을 다음 3개 보통주로 확정한다.

- 삼성전자 — `KRX:005930`
- SK하이닉스 — `KRX:000660`
- 현대자동차 — `KRX:005380`

기존 NAVER 종목 후보는 P0 지원 범위에서 제외한다.  
뉴스 provider 후보로서의 NAVER Search API는 종목 NAVER와 별개이므로 그대로 유지한다.

## 선정 이유

- 삼성전자와 SK하이닉스가 함께 등장하는 기사에서 회사별 사실·수치 귀속을 검증한다.
- 현대자동차로 산업 다양성을 유지한다.
- P0에서는 단일 종목 질문만 지원한다.
- 삼성전자와 SK하이닉스의 직접 비교·우열 판단은 P0·P1과 현재 M5 기본 큐에서 제외한다. 별도 데이터 계약·평가 fixture·Human Owner 승인이 있을 때만 새 계획으로 추가한다.

## 설계 변경

전체 RAG 흐름은 유지한다.

변경되는 최소 계약:

```text
FinancialDocument
- primary_security_ids
- mentioned_security_ids

Evidence
- subject_security_ids
- mentioned_security_ids
- scope: company_specific | industry_common | multi_company
```

필터와 validator는 다음을 보장해야 한다.

- 삼성전자 질문에 SK하이닉스 전용 사실·수치가 들어가지 않음
- SK하이닉스 질문에 삼성전자 전용 사실·수치가 들어가지 않음
- 산업 공통 Evidence를 회사 고유 실적으로 표현하지 않음
- 주체가 불명확한 수치를 사용하지 않음

## 현재 승인 상태

- 종목 3개 구성: 승인됨
- M1-01 구현: 아직 별도 승인 필요
- intent 전체 범위·리포트 원문·credential 방식: 기존 미확인 상태 유지
- commit·push·PR·merge·배포: 승인되지 않음

## 정합성 보완

- 리포트 schema도 복수 종목 필드로 통일
- scope별 validation 불변조건 추가
- 세 종목 각각 뉴스·공시·리포트 golden coverage 확보
- R30 중복·표 구조 오류와 A23 범위 충돌 수정
