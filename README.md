# wooriqt

분당우리교회 '한 구절 묵상' 콘텐츠를 매일 이메일로 보내주는 자동화.

이 저장소는 **public**이다. 코드에 API 키·비밀번호 같은 민감정보는 없으며(직접
검색해 확인했고, git 히스토리도 한 번 전부 재작성해 개인정보를 지웠다), 매일
실행되는 Routine이 GitHub 인증/커넥터 없이 `raw.githubusercontent.com`으로
스크립트를 바로 받아 쓸 수 있도록 하기 위해 의도적으로 public으로 전환했다.

- 콘텐츠 출처: 교회가 격월로 발행하는 「한 구절 묵상」 핸드북 PDF
  (https://www.woorichurch.org/modu/s_board/list.asp?board_seq=47 에 게시).
  이 PDF를 저장소에 미리 받아두고(`scripts/pdf/`), **매일 실행 시에는
  woorichurch.org에 전혀 접속하지 않고** 오프라인으로 파싱한다. 이전에는
  매일 홈페이지에 실시간 접속해 스크래핑하는 방식(`scripts/fetch_meditation.py`,
  현재는 사용 안 함/보관용)이었는데, 실행 환경의 네트워크/세션 안정성 문제로
  발송이 조용히(에러 없이) 실패하는 일이 잦아 이 방식으로 전환했다(아래
  "변경 이력 메모" 참고).
- 수신자: 저장소 소유자의 개인 이메일 (Routine 설정에 저장되어 있으며, 이 저장소에는 노출하지 않음)
- 실행 방식: Claude Code Remote Routine(트리거)이 매일 새 세션을 만들어 실행.
  이 세션은 daviduhm/wooriqt 저장소에 대한 GitHub 접근 권한(커넥터/git clone)이
  없을 수 있으므로, 저장소를 클론하지 않고 `raw.githubusercontent.com`에서
  스크립트와 PDF를 인증 없이 직접 받아 실행한다(아래 "매일 실행 흐름" 참고).

## 스크립트

- `scripts/parse_pdf_meditation.py <pdf_path> [M/D 또는 YYYY-MM-DD]`
  저장소에 받아둔 핸드북 PDF에서 지정한 날짜(기본: 오늘, KST)의 공식 묵상
  콘텐츠(제목, 본문, 오늘의 한 구절[개역개정/새번역], 본문 개요, 한 구절 묵상,
  묵상질문, 기도)를 네트워크 접속 없이 파싱해 JSON으로 출력한다. PDF의 2단
  레이아웃을 `pdfminer.six`의 위치 기반(bbox) 파싱으로 읽는다. 자세한 레이아웃
  설명과 예외 케이스(일요일 가정예배 별지, 2개월 주기 첫날의 안내문 겹침 등)는
  스크립트 상단 docstring 참고.

- `scripts/fetch_meditation.py [YYYY-MM-DD]` (보관용, 더 이상 매일 실행에 쓰지 않음)
  과거에 홈페이지를 실시간 스크래핑하던 스크립트. `parse_pdf_meditation.py`와
  동일한 출력 스키마를 가지므로, PDF 파싱이 실패하는 비상시 수동 대체 수단으로
  남겨둔다.

- `scripts/build_email.py <merged.json> [output_prefix]`
  공식 묵상 JSON(위 두 스크립트 중 무엇이 만들었든 동일 스키마)에 AI가 작성한
  보충 필드(`background`, `deeper_reflection`, `ai_prayer`, `reflection_questions`)를
  합쳐 이메일 제목(`subject`)/HTML 본문(`html`)/텍스트 본문(`text`)을 만든다.
  `output_prefix`를 주면 stdout JSON뿐 아니라 `<prefix>.subject.txt`,
  `<prefix>.html`, `<prefix>.text.txt` 파일로도 저장한다 — Gmail 발송 시 이
  파일들을 Read 도구로 그대로 읽어 옮기면, JSON을 손으로 파싱하다 이스케이프가
  꼬여 내용이 깨지는 사고를 줄일 수 있다.

## 매일 실행 흐름 (Routine 프롬프트가 수행)

0. `curl`로 `https://raw.githubusercontent.com/daviduhm/wooriqt/claude/bundang-woori-meditation-automation-obizjz/`
   아래의 `scripts/parse_pdf_meditation.py`, `scripts/build_email.py`,
   `scripts/pdf/<현재 주기 PDF>`를 받아 `/tmp`에 저장한다(인증 불필요,
   git clone/add_repo/woorichurch.org 접속 전혀 불필요).
1. `TZ=Asia/Seoul date +%Y-%m-%d`로 오늘 날짜(KST) 확인.
2. `python3 parse_pdf_meditation.py <pdf> <오늘 날짜>`로 오늘의 공식 묵상
   콘텐츠를 PDF에서 오프라인으로 파싱한다.
3. 가져온 공식 콘텐츠를 바탕으로 AI가 말씀의 배경(🏛️), 더 깊은 묵상(🌿),
   보충 기도(🙏), 추가 적용 질문(💭)을 작성해 JSON에 병합한다.
4. `python3 build_email.py ... <prefix>`로 최종 이메일(subject/html/text) 파일을 만든다.
5. Gmail로 즉시 발송(초안 아님) — `mcp__Gmail__send_message`. 발송 후
   `mcp__Gmail__get_message`로 내용이 잘리거나 이중 이스케이프되지 않았는지 검증한다.
6. PushNotification으로도 전체 내용을 전달(5가 실패해도 사용자에게 내용이 가는 안전망).

## PDF 갱신 (격월, 수동)

- `scripts/pdf/` 아래 PDF는 홀수 달 말(9월/11월/1월 ... 말)에 교회가 다음
  2개월치를 새로 발행하면 수동으로 교체해야 한다. 대상 게시판:
  https://www.woorichurch.org/modu/s_board/list.asp?board_seq=47
- 다운로드 시 직접 다운로드 URL을 바로 요청하면 작은 JS 리다이렉트 스텁만
  내려오므로, 먼저 게시글 `read.asp` 페이지를 같은 쿠키로 방문한 뒤 그
  URL을 `Referer`로 넘겨 `download.asp`를 요청해야 실제 PDF를 받을 수 있다.
- 새 PDF를 받으면 `scripts/parse_pdf_meditation.py`로 그 2개월 범위의 날짜
  몇 개(평일/주일/월경계 포함)를 테스트해 정상 파싱되는지 확인한 뒤 커밋하고,
  Routine 프롬프트가 참조하는 파일명(현재 `scripts/pdf/meditation_2026_09-10.pdf`)도
  함께 갱신한다.

## 변경 이력 메모 (문제 해결 과정)

- 처음에는 매일 새 세션이 이 저장소를 `git clone`(또는 `add_repo`)해서 스크립트를
  받는 방식이었는데, Routine이 발화하는 세션에는 GitHub 커넥터/저장소 접근 권한이
  없을 수 있어 실패하는 경우가 있었다.
- 저장소를 private로 유지하면서 전용 persistent 세션에 Routine을 고정 바인딩하는
  방법도 시도했으나, 설정이 복잡하고 세션이 매일 대화를 누적하며 플랫폼 기본
  알림 채널을 못 쓰게 되는 단점이 있어 채택하지 않았다.
- 저장소를 public으로 전환하고(민감정보 없음을 확인 후, git 히스토리도
  재작성해 개인정보 제거) `raw.githubusercontent.com`에서 인증 없이 스크립트를
  받아 매일 홈페이지(`www.woorichurch.org`)를 실시간 스크래핑하는 방식으로
  한동안 운영했다.
- 이후 발송이 에러 메시지 하나 없이 조용히 실패하는 일이 반복됐다(2주 중
  9일 무발송). 여러 차례 진단한 결과 원인은 Routine이 발화하는 실행 환경
  자체의 세션 조기 종료(플랫폼 레벨 문제)로 좁혀졌고, 프롬프트를 아무리
  방어적으로 고쳐도 재현을 막을 수 없었다. woorichurch.org 접속이 실패
  지점 중 하나로 의심되어, 매일 실행에서 이 접속 자체를 완전히 제거하는
  쪽으로 방향을 바꿨다: 격월 핸드북 PDF를 저장소에 미리 받아두고, 매일은
  네트워크 접속 없이 그 PDF만 오프라인으로 파싱한다.
