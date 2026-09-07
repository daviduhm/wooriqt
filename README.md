# wooriqt

분당우리교회 '한 구절 묵상' 페이지를 매일 스크래핑해서 이메일로 보내주는 자동화.

이 저장소는 **public**이다. 코드에 API 키·비밀번호 같은 민감정보는 없으며(직접
검색해 확인했고, git 히스토리도 한 번 전부 재작성해 개인정보를 지웠다), 매일
실행되는 Routine이 GitHub 인증/커넥터 없이 `raw.githubusercontent.com`으로
스크립트를 바로 받아 쓸 수 있도록 하기 위해 의도적으로 public으로 전환했다.

- 대상 페이지(정식 주소): https://www.woorichurch.org/modu/ov/ov_meditation.asp?lef=3
  - 특정 날짜 콘텐츠는 `?ov_date=YYYY-MM-DD` 쿼리로 조회할 수 있다
    (예: `https://www.woorichurch.org/modu/ov/ov_meditation.asp?ov_date=2026-09-05`).
  - 2026-09-04에는 이 저장소가 실행되는 환경(claude.ai/code 원격 세션)의 네트워크
    정책이 `www.woorichurch.org`를 403으로 차단하고 naked domain(`woorichurch.org`)만
    허용한 적이 있었다. 2026-09-05에 정책이 바뀌어 www도 정상 접속됨을 확인했다.
    `scripts/fetch_meditation.py`는 www로 먼저 시도하고, 혹시 다시 막히면 자동으로
    naked domain으로 폴백한다.
- 수신자: 저장소 소유자의 개인 이메일 (Routine 설정에 저장되어 있으며, 이 저장소에는 노출하지 않음)
- 실행 방식: Claude Code Remote Routine(트리거)이 매일 새 세션을 만들어 실행.
  이 세션은 daviduhm/wooriqt 저장소에 대한 GitHub 접근 권한(커넥터/git clone)이
  없을 수 있으므로, 저장소를 클론하지 않고 `raw.githubusercontent.com`에서
  스크립트 2개를 인증 없이 직접 받아 실행한다(아래 "매일 실행 흐름" 참고).

## 스크립트

- `scripts/fetch_meditation.py [YYYY-MM-DD]`
  지정한 날짜(기본: 오늘, KST)의 공식 묵상 콘텐츠(제목, 본문, 오늘의 한 구절
  [개역개정/새번역], 본문 개요, 한 구절 묵상, 묵상질문, 기도)를 JSON으로 출력한다.
  외부 의존성 없이 표준 라이브러리(urllib, re, html)만 사용한다.

- `scripts/build_email.py <merged.json> [output_prefix]`
  `fetch_meditation.py`의 출력 JSON에 AI가 작성한 보충 필드
  (`background`, `deeper_reflection`, `ai_prayer`, `reflection_questions`)를 합쳐
  이메일 제목(`subject`)/HTML 본문(`html`)/텍스트 본문(`text`)을 만든다.
  `output_prefix`를 주면 stdout JSON뿐 아니라 `<prefix>.subject.txt`,
  `<prefix>.html`, `<prefix>.text.txt` 파일로도 저장한다 — Gmail 발송 시 이
  파일들을 Read 도구로 그대로 읽어 옮기면, JSON을 손으로 파싱하다 이스케이프가
  꼬여 내용이 깨지는 사고를 줄일 수 있다.

## 매일 실행 흐름 (Routine 프롬프트가 수행)

0. `curl`로 `https://raw.githubusercontent.com/daviduhm/wooriqt/claude/bundang-woori-meditation-automation-obizjz/scripts/{fetch_meditation.py,build_email.py}` 를
   받아 `/tmp`에 저장한다(인증 불필요, git clone/add_repo 불필요).
1. `TZ=Asia/Seoul date +%Y-%m-%d`로 오늘 날짜(KST) 확인.
2. `python3 fetch_meditation.py`로 오늘의 공식 묵상 콘텐츠를 가져온다.
3. 가져온 공식 콘텐츠를 바탕으로 AI가 말씀의 배경(🏛️), 더 깊은 묵상(🌿),
   보충 기도(🙏), 추가 적용 질문(💭)을 작성해 JSON에 병합한다.
4. `python3 build_email.py ... <prefix>`로 최종 이메일(subject/html/text) 파일을 만든다.
5. Gmail로 즉시 발송(초안 아님) — `mcp__Gmail__send_message`. 발송 후
   `mcp__Gmail__get_message`로 내용이 잘리거나 이중 이스케이프되지 않았는지 검증한다.
6. PushNotification으로도 전체 내용을 전달(5)가 실패해도 사용자에게 내용이 가는 안전망).

## 변경 이력 메모 (문제 해결 과정)

- 처음에는 매일 새 세션이 이 저장소를 `git clone`(또는 `add_repo`)해서 스크립트를
  받는 방식이었는데, Routine이 발화하는 세션에는 GitHub 커넥터/저장소 접근 권한이
  없을 수 있어 실패하는 경우가 있었다.
- 저장소를 private로 유지하면서 전용 persistent 세션에 Routine을 고정 바인딩하는
  방법도 시도했으나, 설정이 복잡하고 세션이 매일 대화를 누적하며 플랫폼 기본
  알림 채널을 못 쓰게 되는 단점이 있어 채택하지 않았다.
- 최종적으로 저장소를 public으로 전환하고(민감정보 없음을 확인 후, git 히스토리도
  재작성해 개인정보 제거) `raw.githubusercontent.com`에서 인증 없이 스크립트를
  받는 방식으로 정착했다. 프롬프트가 짧고, 스크립트를 고치면 다음 날 자동 반영되며,
  GitHub 접근 권한 문제에서 완전히 자유롭다.
