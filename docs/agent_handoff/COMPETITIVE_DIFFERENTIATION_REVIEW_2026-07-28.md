# Questock 유사 서비스·차별화 후보 재검토

> 최초 조사일: `2026-07-28`
> 재검토일: `2026-07-28`
> 상태: `REVIEWED / HUMAN OWNER DECISION REQUIRED`
> 목적: 평가·LLM 모델 비교보다 먼저 수행할 차별화 기능 선택
> 조사 범위: 로그인 없이 확인 가능한 공식 소개·도움말·개발 문서
> 한계: 실제 유료 기능과 로그인 후 UX를 직접 비교한 결과가 아니며,
> 시장 전체의 유일성을 증명하는 조사가 아니다.

## 0. 재검토로 변경된 결론

최초 검토에서 1순위로 제시했던 `As-of Replay / 시점 비교 답변`은
Human Owner 피드백에 따라 차별화 후보에서 제외한다. 현재의 시점 선택은
실시간 서비스를 구현하지 못한 데모 제약이며, 향후 실시간 서비스에서는
없어질 수 있기 때문이다.

또한 이번 재검토에서 다음 기능도 이미 다른 서비스의 공개 기능으로
확인했다.

- 같은 사건의 여러 기사를 한 묶음으로 보여주기:
  Ground News, Google News
- 여러 보도사의 관점과 고유 기사 수가 충분한지 구분하기:
  Ground News
- 조사 과정·인라인 인용·원문 이동:
  AlphaSense, Perplexity Finance, Fiscal.ai
- 긍정·부정 요인, 위험, 기업 이벤트 요약:
  TipRanks

따라서 `기사 묶기`, `출처 링크`, `호재·악재 요약`, `공시 연결` 중
하나만 구현해서는 차별화라고 주장할 수 없다.

## 1. 공식 공개 기능 재확인

| 서비스 | 공식 페이지에서 확인한 기능 | Questock 단독 기능으로 주장할 수 없는 부분 |
|---|---|---|
| Perplexity Finance | 뉴스·데이터 피드의 촉매 추적, 공시·실적발표·리서치 종합, 답변에서 원 공시·transcript·데이터로 직접 연결 | 촉매 추적, 멀티소스 종합, 원문 연결 |
| AlphaSense | 질의를 조사 계획으로 분해, 공시·transcript·리서치 등 대규모 자료 검색, 요약별 인라인 인용과 원문 해당 구절 확인, primary/secondary 문서 구분 | 조사 과정, 자료 유형 구분, 인라인 검증 |
| TipRanks | 긍정·부정 요인, 재무·기술·위험, 실적발표, 기업 이벤트와 sentiment, 검증 데이터·다층 사실 검증·출처 표시 | 호재·악재·위험·이벤트 요약, 출처 표시 |
| Fiscal.ai | 모든 숫자를 제출 문서의 정확한 페이지와 연결, 최근 뉴스·bull/bear 논점·변화 모니터링, 감사 가능한 데이터 흐름 | 공시 기반 수치 검증, 최근 뉴스와 상반 관점 |
| Ground News | 서로 다른 보도사의 동일 사건 기사를 한 story로 병합, 여러 보도사의 headline·framing 비교, 충분한 고유 기사가 있을 때만 비교 요약 제공 | 사건 클러스터, 다수 보도사 관점 비교, 고유 기사 충분성 판단 |
| Google News | 같은 story의 추가 출처·지역 보도·관점·시간 흐름을 Full Coverage로 제공 | 동일 사건의 다중 출처·타임라인 |

확인한 공식 자료:

- Perplexity Finance:
  <https://www.perplexity.ai/enterprise/use-cases/finance>
- AlphaSense Generative Search:
  <https://help.alpha-sense.com/hc/en-us/articles/41666587181203-Interacting-with-Generative-Search>
- AlphaSense primary/secondary documents:
  <https://help.alpha-sense.com/hc/en-us/articles/41711142211603-Searching-Primary-Secondary-Documents-Mentions>
- TipRanks AI Stock Analysis:
  <https://www.tipranks.com/news/labs/introducing-stock-ai-analysis-smarter-insights-faster-decisions>
- TipRanks AI Equity Research:
  <https://www.tipranks.com/news/labs/tipranks-ai-equity-research-offers-next-generation-stock-analysis>
- Fiscal.ai source-linked skills:
  <https://docs.fiscal.ai/docs/guides/mcp-skills>
- Ground News 소개:
  <https://ground.news/about>
- Ground News 동일 기사 비교:
  <https://help.ground.news/en/articles/485057>
- Ground News 고유 기사 충분성:
  <https://help.ground.news/en/articles/3189505>
- Google Full Coverage:
  <https://support.google.com/websearch/answer/11127743?hl=en>

## 2. 공개 자료로 확인되지 않은 조합

이번 공식 공개 자료에서는 아래 전체 흐름을 금융 초보자용 답변의 한
기능으로 제공한다고 명시한 대표 서비스를 확인하지 못했다.

1. 국내 종목 뉴스를 사건 단위로 묶는다.
2. 재배포·동일 원출처 가능성을 별도로 표시하여 보도사 개수를 곧바로
   독립 근거 개수로 세지 않는다.
3. 같은 사건에서 여러 기사에 공통으로 확인된 사실과 서로 다른 해석을
   구분한다.
4. DART 공시는 가격변동의 직접 원인으로 자동 단정하지 않고
   `공식 확인`, `배경 근거`, `상충`, `연결 없음`으로 역할을 구분한다.
5. 확인되지 않은 내용과 현재 자료로 알 수 없는 내용을 초보자에게
   명시한다.
6. 위 결과를 자료 목록이 아니라 자연스러운 근거 기반 답변으로 제공한다.

이 조합은 Questock의 **차별화 목표 후보**로는 타당하다. 다만 이는
공식 공개 페이지에서 동일한 전체 조합을 확인하지 못했다는 뜻일 뿐이다.
로그인 후 기능, 유료 기능, 비공개 기업용 기능까지 포함해 시장에 전혀
없다는 증거는 아니다. 따라서 발표와 문서에서는 다음 표현을 사용한다.

허용:

> Questock은 동일 사건을 반복 보도 건수로 과장하지 않고, 뉴스 사이의
> 공통 사실·다른 해석과 DART 공식 근거의 역할, 아직 확인되지 않은
> 부분을 초보자에게 함께 설명하는 것을 차별화 목표로 한다.

금지:

- 업계 최초
- 국내 유일
- 다른 서비스에는 없는 기능
- 독립 근거 개수를 완전히 판별한다
- 공시가 뉴스의 인과관계를 증명한다

## 3. 차별화 경계

### 차별화의 중심

`근거 대조형 답변 / Evidence Cross-check`

- 사건 중심 뉴스 묶음
- 보수적인 원출처·재배포 관계 표시
- 공통 사실과 다른 해석 분리
- DART 공식 자료의 역할 구분
- 미확인·자료 부족 공개
- 초보자 친화적인 자연어 답변

### 차별화가 아닌 품질 계약

- 선택 시점 이후 자료를 사용하지 않는 temporal cutoff
- 인용 링크
- 근거 기반 답변
- 보안·개인정보·투자조언 제한

위 항목은 반드시 유지하지만 차별화 기능으로 홍보하지 않는다. 특히
현재의 시점 선택 UI는 데모와 정확성 검증을 위한 임시 제약으로 취급한다.

### 이번 단계에서 제외

- 리서치 리포트 추가 수집·가공·대조
- 실시간 뉴스·가격 서비스로 전환
- 보도사 신뢰도나 정치적 성향 평가
- 회사 간 투자 매력도 순위
- 매수·매도·보유 추천과 주가 예측

리서치 리포트 원문은 Human Owner가 작업 에이전트의 전처리를 허용했지만,
수집·가공 시간이 필요하므로 후속 단계로 둔다. 1단계는 뉴스와 DART
공시만으로 차별화 흐름을 검증한다.

## 4. 판정

- `기사 클러스터링` 자체: `NOT DIFFERENTIATED`
- `출처 링크·인용` 자체: `NOT DIFFERENTIATED`
- `긍정·부정·위험 요약` 자체: `NOT DIFFERENTIATED`
- `공시 연결` 자체: `NOT DIFFERENTIATED`
- 위 요소를 결합한 `근거 대조형 답변`:
  `PLAUSIBLE DIFFERENTIATION TARGET / NOT MARKET-EXCLUSIVITY PROOF`

구현 전 기준은
`docs/TASK_CARDS/M5-D1-evidence-crosscheck.md`로 분리한다. 구현 후에는
작은 수작업 정답셋으로 사건 묶음, 원출처 관계 주장, 공시 역할, 인용
지지 여부를 검증해야 차별화 기능이 실제로 성립했다고 말할 수 있다.
