# Questock 유사 서비스·차별화 후보 검토

> 조사일: `2026-07-28`
> 목적: 평가·LLM 모델 비교보다 먼저 수행할 차별화 기능 선택
> 조사 범위: 로그인 없이 확인 가능한 공식 소개·도움말·앱 설명
> 한계: 실제 유료 기능과 로그인 후 UX를 직접 비교한 결과가 아니며,
> 시장 전체의 유일성을 증명하는 조사가 아니다.

## 1. 공개 기능 비교

| 서비스 | 공개된 핵심 기능 | Questock과 겹치는 부분 | Questock이 따라가기 어려운 부분 |
|---|---|---|---|
| 네이버페이 증권 | 국내외 시세·시장 흐름, 관심종목 가격·공시·리서치 알림, 보유주식 통합, 주문·토론방 | 시세, 뉴스·공시·리서치 접근 | 시장 전체 범위, 계좌·주문·관심종목 생태계 |
| 토스증권 Open API | 실시간 호가·체결·캔들, 종목·시장 정보, 계좌·주문, 외부 AI와 연결한 대화형 포트폴리오 분석 예시 | 자연어 금융 질의와 시세 활용 | 실제 계좌·거래·포트폴리오 연결 |
| Fiscal.ai | 금융·KPI 데이터, AI 리서치, 차트·대시보드, 비교, 관심종목·알림, 실적·공시·IR 자료와 출처 감사 | AI 질의, 재무·공시 근거, 출처 연결, 요약 | 글로벌 범위, 장기 정형 재무 데이터, 모델링·스크리닝 |
| Perplexity Finance | 자연어 심층 조사, 공시·실적발표·실시간 가격·내부자·거시 데이터, 촉매 감시, 원문 링크 | 근거형 질의, 최신 뉴스·가격, 출처 링크 | 대규모 데이터·connector, 자동 심층 조사와 감시 |
| AlphaSense | 대화형 금융 검색, 공시·transcript·리서치·재무 데이터, 인용·원문 excerpt, deep research, workflow·watchlist·alert | 멀티턴 질의, 리서치·공시 검색, 근거 확인 | 프리미엄 데이터 규모, 전문 분석 workflow·자동화 |
| TipRanks | AI 종목 개요, 긍정·부정 요인, 재무·기술·위험 분석, peer 비교, 실적발표·기업 이벤트·sentiment | 종목 요약, 긍정·위험 구조, 가격변동 배경 | 광범위한 지표·peer·기술·sentiment·score |

확인한 공식 자료:

- 네이버페이 앱 증권 기능:
  <https://apps.apple.com/kr/app/id1554807824>
- 토스증권 Open API:
  <https://home.tossinvest.com/ko/open-api>
- Fiscal.ai:
  <https://fiscal.ai/>
- Fiscal.ai source-linked analyst skills:
  <https://docs.fiscal.ai/docs/guides/mcp-skills>
- Perplexity Finance:
  <https://www.perplexity.ai/enterprise/use-cases/finance>
- AlphaSense Generative Search:
  <https://help.alpha-sense.com/hc/en-us/articles/42591266633875-Quick-Start-Guide-to-Generative-Search>
- AlphaSense 2026 workflow·monitoring update:
  <https://help.alpha-sense.com/hc/en-us/articles/52207495181203-AlphaSense-Product-Updates-May-2026>
- TipRanks AI Stock Analysis:
  <https://www.tipranks.com/news/labs/introducing-stock-ai-analysis-smarter-insights-faster-decisions>

## 2. 기존 기능·초기 아이디어 판정

### 단독으로는 차별화하기 어려움

- 근거가 붙은 자연어 종목 질의
- 뉴스·공시·리서치 요약
- 긍정·위험·불확실성 구분
- 재무 추세·차트·KPI
- 종목·peer 비교
- 관심종목·알림·portfolio
- 시장 screening
- 긴 리서치 보고서와 자동 slide
- AI model 선택

위 기능은 현재 서비스 중 하나 이상과 겹친다. 구현 범위와 데이터가 더
작은 Questock이 같은 기능 수로 경쟁하는 방향은 적절하지 않다.

### 차별화 가능성이 남은 현재 조합

Questock의 개별 요소도 완전히 새로운 것은 아니지만, 아래 조합은 이번
공개 자료 조사에서 대표 기능으로 직접 확인하지 못했다.

1. 심사자가 과거 날짜와 장 전·장 중·애프터마켓·장 마감 시점을 선택
2. 선택 시점 이후에 공개된 뉴스·공시·가격을 hard filter로 배제
3. 해당 시점에서 확인 가능했던 가격과 근거만으로 답변
4. 필요한 자료가 부족하면 source별 누락과 보류 상태를 공개
5. 국내 주식 초보자가 일상 표현으로 같은 과정을 질문

이는 단순한 “최신 AI 종목 분석”보다 **당시 알 수 있었던 정보만으로
답변을 재현하고 검증하는 서비스**로 설명할 수 있다.

## 3. 권장 차별화 기능

### 1순위 — As-of Replay / 시점 비교 답변

같은 종목·같은 질문을 두 기준 시점에 실행해 다음만 비교한다.

- 당시 가격과 시장 상태
- 그 시점까지 공개된 근거
- 새로 추가되거나 사라진 핵심 요인
- 답변 상태와 근거 충분성 변화
- 미래 정보 사용 건수 `0`

회사 간 우열 비교, 가격 예측, 매수·매도 추천은 포함하지 않는다.

장점:

- 현재 M5 시점 선택·temporal filter·가격 snapshot을 재사용할 수 있음
- 교수·심사자가 직접 미래 정보 누출 여부를 확인 가능
- “왜 답이 달라졌는가”를 근거 시간순으로 설명 가능
- 일반적인 최신 요약 서비스와 발표상 차이를 한 화면에서 보여주기 쉬움

### 2순위 — 근거 타임라인

선택 시점까지의 가격 snapshot, 뉴스, 공시, 리포트를 공개 시각순으로
보여주고 다음을 구분한다.

- 가격 관측 이전에 존재한 근거
- 가격 관측 이후라 원인 근거로 사용할 수 없는 자료
- 직접 원인 기사
- 당일 호재·악재에 해당하지만 직접 원인으로 단정할 수 없는 자료

### 3순위 — 독립 원출처·상충 관점 표시

재배포 기사를 여러 독립 근거로 세지 않고, 같은 사건에 대한 뉴스·공시·
리포트의 공통 사실과 다른 관점을 묶어 표시한다. 초기 아이디어 `E05`와
기존 `A05-M`을 개선하는 방향이다.

## 4. 다음 작업 순서 제안

```text
M5-01-HR1 배포·사용자 확인
→ 1순위 As-of Replay의 최소 범위와 시연 화면 확정
→ 차별화 기능 구현·시간 누출 테스트
→ golden set과 범용 평가 지표 확립
→ 시간이 남으면 LLM 모델 비교
```

## 5. 결론

- 기존 기능과 초기 아이디어의 **개별 기능 대부분은 유사 서비스와
  겹친다**.
- 따라서 알림·portfolio·screening·기술지표를 하나 더 붙이는 것으로는
  차별화하기 어렵다.
- 그러나 현재 구현된 `기준 시점 선택 + 이후 정보 강제 배제 + 근거 부족
  보류`를 `같은 질문의 시점별 재현·비교`로 강화하는 방향은 차별화
  후보로 남아 있다.
- 이 결론은 공개 자료 기반의 빠른 제품 검토이며 “시장에 동일 기능이
  전혀 없다”는 주장은 아니다.
