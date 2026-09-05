# wooriqt

분당우리교회 '한 구절 묵상' 페이지를 매일 스크래핑해서 이메일로 보내주는 자동화.

- 대상 페이지(정식 주소): https://www.woorichurch.org/modu/ov/ov_meditation.asp?lef=3
  - 특정 날짜 콘텐츠는 `?ov_date=YYYY-MM-DD` 쿼리로 조회할 수 있다
    (예: `https://www.woorichurch.org/modu/ov/ov_meditation.asp?ov_date=2026-09-05`).
  - 2026-09-04에는 이 저장소가 실행되는 환경(claude.ai/code 원격 세션)의 네트워크
    정책이 `www.woorichurch.org`를 403으로 차단하고 naked domain(`woorichurch.org`)만
    허용한 적이 있었다. 2026-09-05에 정책이 바뀌어 www도 정상 접속됨을 확인했다.
    `scripts/fetch_meditation.py`는 www로 먼저 시도하고, 혹시 다시 막히면 자동으로
    naked domain으로 폴백한다.
- 수신자: geehoon.uhm@gmail.com
- 실행 방식: Claude Code Remote Routine(트리거)이 매일 새 세션을 만들어 실행.

## 스크립트

- `scripts/fetch_meditation.py [YYYY-MM-DD]`
  지정한 날짜(기본: 오늘, KST)의 공식 묵상 콘텐츠(제목, 본문, 오늘의 한 구절
  [개역개정/새번역], 본문 개요, 한 구절 묵상, 묵상질문, 기도)를 JSON으로 출력한다.
  외부 의존성 없이 표준 라이브러리(urllib, re, html)만 사용한다.

- `scripts/build_email.py <merged.json>`
  `fetch_meditation.py`의 출력 JSON에 AI가 작성한 보충 필드
  (`background`, `deeper_reflection`, `ai_prayer`, `reflection_questions`)를 합쳐
  이메일 제목(`subject`)/HTML 본문(`html`)/텍스트 본문(`text`)을 JSON으로 출력한다.

## 매일 실행 흐름 (Routine 프롬프트가 수행)

1. `TZ=Asia/Seoul date +%Y-%m-%d`로 오늘 날짜(KST) 확인.
2. `python3 scripts/fetch_meditation.py`로 오늘의 공식 묵상 콘텐츠를 가져온다.
3. 가져온 공식 콘텐츠를 바탕으로 AI가 말씀의 배경(🏛️), 더 깊은 묵상(🌿),
   보충 기도(🙏), 추가 적용 질문(💭)을 작성해 JSON에 병합한다.
4. `python3 scripts/build_email.py`로 최종 이메일(subject/html/text)을 만든다.
5. Gmail로 즉시 발송(초안 아님) — `mcp__Gmail__send_message`.
6. PushNotification으로도 전체 내용을 전달.
