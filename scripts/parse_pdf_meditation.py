#!/usr/bin/env python3
"""
분당우리교회 '한 구절 묵상' 격월 핸드북 PDF에서 지정한 날짜의 공식 묵상
콘텐츠를 오프라인으로(네트워크 접속 없이) 파싱해 JSON으로 출력한다.

fetch_meditation.py(실시간 웹 스크래핑)와 동일한 출력 스키마를 갖도록
만들어서, build_email.py를 그대로 재사용할 수 있다.

사용법:
    python3 parse_pdf_meditation.py <PDF경로> <M/D>   (예: 9/26)
    python3 parse_pdf_meditation.py <PDF경로> <YYYY-MM-DD>

배경:
    매일 woorichurch.org 홈페이지에 접속해서 콘텐츠를 가져오는 방식은
    실행 환경의 네트워크/세션 안정성 문제로 자주 조용히 실패했다.
    이 핸드북 PDF(교회가 격월로 공식 발행)를 저장소에 미리 받아두고
    오프라인으로 파싱하면, 매일 실행 시 woorichurch.org에 전혀
    접속하지 않아도 된다. PDF는 격월(홀수 달 마지막 주)로 갱신되어야
    하며, scripts/pdf/ 아래에 버전을 올려 관리한다.

PDF 레이아웃 (2단):
    왼쪽 컬럼: 날짜/제목/본문(장)/본문개요/한구절 참조/한구절 본문
               (개역개정+새번역)/한 구절 묵상(본문 해설)
    오른쪽 컬럼: 묵상질문(➋로 표시되는 항목만 텍스트 박스로 존재하며,
               ➊은 모든 날짜에 공통인 고정 문구라 하드코딩한다)/기도문
    일요일은 표준 항목 페이지 바로 다음 장에 "가정예배" 별지가 추가로
    붙는데, 이 별지는 passage-only 박스("책이름 N장/편")가 없다는
    특징으로 걸러낸다.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

KST = timezone(timedelta(hours=9))

FIXED_Q1 = "말씀을 통해 하나님이 오늘 나에게 주신 교훈 또는 감동은 무엇인가요?"

PASSAGE_RE = re.compile(r"^[가-힣]+\s*\d+[장편]$")
VERSE_REF_RE = re.compile(r"^[가-힣]+\s*\d+[장편]\s*[\d\-]+절$")
BULLET_RE = re.compile(r"^[➊➋➌➍➎➏➐➑➒➓]")
LABEL_LINE_RE = re.compile(r"^\[[^\]\n]*\]$")
VERSE_NUM_RE = re.compile(r"^\d{1,3}\s")


def dewrap(t: str) -> str:
    """PDF는 좁은 컬럼 폭에 맞춰 줄을 강제로 자르기 때문에(단어 중간에서도
    끊김), 줄바꿈은 의미 있는 줄바꿈이 아니라 인쇄용 개행일 뿐이다. 심지어
    pdfminer가 이 강제 개행 지점을 아예 별도의 텍스트 박스로 쪼개버리는
    경우도 있어서(예: "...미"로 끝나는 박스와 "혹에..."로 시작하는 별도
    박스), 박스 경계도 의미 있는 경계라고 믿을 수 없다. 그래서 이
    함수는 여러 박스를 미리 "\n"으로 합친 문자열을 받아, 줄 끝에 실제로
    남아 있는 공백 문자로 "원래 띄어쓰기가 있었는지"를 판단한다 — 단어
    중간을 자른 경우엔 공백이 없고, 단어/문장 경계에서 자연스럽게 넘어간
    경우엔 공백이 남아 있다. 그 공백을 그대로 둔 채 줄바꿈만 제거해
    이어붙인다(공백을 새로 끼워 넣지 않는다). 다만 "[ 개역개정 ]"처럼
    대괄호 라벨인 줄 앞뒤로는 실제 줄바꿈을 넣어 라벨을 본문과 시각적으로
    분리한다. 또한 "15  여인이..."처럼 절 번호로 시작하는 줄은, 바로 앞
    절이 끝나는 지점에서 공백이 아예 박스 분리(줄바꿈)로 흡수돼 버리는
    경우가 있어(절과 절 사이는 새 박스로 나뉘는 경우가 많다), 앞에 공백이
    없으면 하나 보충해 절 번호가 앞 문장에 그대로 들러붙지 않게 한다."""
    out = []
    for ln in t.split("\n"):
        if LABEL_LINE_RE.match(ln.strip()):
            if out:
                out.append("\n")
            out.append(ln.strip())
            out.append("\n")
        else:
            if out and VERSE_NUM_RE.match(ln) and out[-1] and not out[-1][-1].isspace():
                out.append(" ")
            out.append(ln)
    return "".join(out).strip()


def today_kst() -> str:
    d = datetime.now(KST)
    return f"{d.month}/{d.day}"


def normalize_date_arg(arg: str) -> str:
    """'9/26' 또는 '2026-09-26' 형태를 'M/D' 매칭용 문자열로 변환."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", arg)
    if m:
        return f"{int(m.group(2))}/{int(m.group(3))}"
    return arg


def get_boxes(page) -> list:
    boxes = []
    for el in page:
        if isinstance(el, LTTextContainer):
            # 앞쪽 공백/개행은 전부 지우되, 뒤쪽은 개행만 지우고 공백은
            # 남긴다 — dewrap()이 "박스 끝에 공백이 있었는지"로 그 자리에
            # 원래 띄어쓰기가 있었는지를 판단하는데, 여기서 .strip()으로
            # 지워버리면 그 정보가 사라진다(특히 pdfminer가 한 문단을
            # 단어 중간에서 별도 박스로 쪼개는 경우에 문제가 된다).
            t = el.get_text().lstrip()
            t = t.rstrip("\n")
            if t.strip():
                boxes.append((el.bbox, t))
    # 위에서 아래로(내림차순 y), 같은 줄이면 왼쪽에서 오른쪽으로
    boxes.sort(key=lambda b: (-round(b[0][3] / 5), b[0][0]))
    return boxes


def find_entry_page(pdf_path: str, md: str):
    """md(예: '9/26')로 시작하는 날짜 박스를 가진 페이지들 중,
    passage-only 박스("책 N장/편")가 있는 표준 항목 페이지를 찾는다.

    각 2개월 주기의 첫째 날(예: 9/1)은 동일한 항목이 두 번 나온다: 처음
    것은 "「한 구절 묵상」 이렇게 묵상하세요." 안내문이 세로쓰기로 겹쳐진
    안내용 페이지이고, 바로 뒤에 안내문 없는 "진짜" 표준 항목 페이지가
    또 있다. 안내문 마커가 있는 페이지는 우선순위를 낮춘다."""
    pattern_date = re.compile(r"^" + re.escape(md) + r"\b")
    INTRO_PAGE_MARKER = "이렇게 묵상하세요"
    candidates = []
    for i, page in enumerate(extract_pages(pdf_path)):
        boxes = get_boxes(page)
        has_date = any(pattern_date.match(t) for _, t in boxes)
        if has_date:
            has_passage = any(PASSAGE_RE.match(t) for _, t in boxes)
            is_intro_page = any(INTRO_PAGE_MARKER in t for _, t in boxes)
            candidates.append((i, boxes, has_passage, is_intro_page))
    for i, boxes, has_passage, is_intro_page in candidates:
        if has_passage and not is_intro_page:
            return i, boxes
    for i, boxes, has_passage, is_intro_page in candidates:
        if has_passage:
            return i, boxes
    if candidates:
        return candidates[0][0], candidates[0][1]
    return None, None


def parse_entry(boxes: list) -> dict:
    left = [b for b in boxes if b[0][0] < 350 and b[0][1] > 40]
    right = [b for b in boxes if b[0][0] >= 350 and b[0][1] > 40]

    date_display = ""
    title = ""
    passage = ""
    verse_ref = ""
    overview = ""

    remaining_left = []
    for bbox, t in left:
        if re.match(r"^\d{1,2}/\d{1,2}", t):
            date_display = t.replace("\n", " ").strip()
        elif PASSAGE_RE.match(t.strip()):
            passage = t.strip()
        elif VERSE_REF_RE.match(t.strip()):
            verse_ref = t.strip()
        elif "오늘의 본문" in t or "오늘의 한 구절" in t:
            # 일부 페이지는 이 라벨("오늘의 본문 l", "오늘의 한 구절")이
            # 바로 뒤 값(passage/verse_ref)과 별개 박스로 분리되어 나온다.
            # 값은 위에서 이미 채워졌으므로 라벨 자체는 버린다.
            continue
        else:
            remaining_left.append((bbox, t))

    # title: 날짜 다음, passage 이전 박스 (남은 것 중 가장 위).
    # 각 2개월 주기의 첫째 날(예: 9/1)은 안내문("이렇게 묵상하세요" 등)과
    # 같은 페이지를 공유해서 안내문 박스가 더 위에 있을 수 있으므로 걸러낸다.
    remaining_left.sort(key=lambda b: -b[0][3])
    INTRO_MARKERS = ("이렇게", "➊", "➋", "➌", "➍", "➎", "➏")
    title_idx = None
    for idx, (bbox, t) in enumerate(remaining_left):
        clean = t.replace("\n", " ").strip()
        if any(m in clean for m in INTRO_MARKERS):
            continue
        if len(clean) > 40:
            continue
        title_idx = idx
        break
    if title_idx is not None:
        title = remaining_left[title_idx][1].replace("\n", " ").strip()
        remaining_left = remaining_left[:title_idx] + remaining_left[title_idx + 1:]

    # overview: passage와 verse_ref 사이에 있는, 짧지 않은 문단
    # (남은 박스 중 verse_text/meditation이 아닌 첫 문단으로 처리)
    verse_lines = []
    meditation_lines = []
    used_overview = False
    for bbox, t in remaining_left:
        if not used_overview and not t.startswith("[") and not re.match(r"^\d", t):
            overview = t.replace("\n", " ").strip()
            used_overview = True
        else:
            verse_lines.append((bbox, t))

    # meditation: 가장 아래(y가 가장 작은) 문단으로, '['로 시작하지 않고
    # 길이가 어느 정도 되는 것.
    verse_lines.sort(key=lambda b: b[0][1])  # y0 오름차순 (아래 -> 위)
    meditation_text = ""
    remaining_verse = []
    for bbox, t in verse_lines:
        if not meditation_text and not t.startswith("[") and len(t) > 60:
            meditation_text = dewrap(t)
        else:
            remaining_verse.append((bbox, t))
    remaining_verse.sort(key=lambda b: -b[0][3])  # 다시 위->아래 순서로

    # pdfminer가 컬럼 폭 때문에 강제로 꺾인 줄을 아예 별도 박스로 쪼개버리는
    # 경우가 있어(단어 중간에서도) 박스 경계를 의미 있는 경계로 믿을 수 없다.
    # 그래서 모든 박스를 일단 "\n"으로 합친 뒤, dewrap() 하나로 한 번에
    # 처리한다 — 라벨 줄만 실제 줄바꿈으로 분리되고, 나머지는 원래 있던
    # 공백만 살려 자연스럽게 이어붙는다.
    verse_text = dewrap("\n".join(t for _, t in remaining_verse))

    # 오른쪽 컬럼: 불릿(➊,➋ 등)은 질문, 나머지는 기도.
    # 각 2개월 주기의 첫째 날은 안내 캡션("묵상노트", "심정이 통하는 기도" 등)이
    # 실제 페이지 위에 겹쳐 있어 별도 텍스트 박스로 잡히므로 걸러낸다.
    GUIDE_CAPTIONS = {
        "묵상노트",
        "아래 질문을 활용하여 묵상해 보세요.",
        "심정이 통하는 기도",
        "말씀을 나의 언어로 바꾸어 기도해 보세요.",
        "함께 기도",
    }
    # 불릿 질문이 줄바꿈되면 이어지는 줄(예: "적어보세" 다음 줄 "요.")이
    # 별도 박스로 분리되어 나오는 경우가 있다. 같은 문단 내 줄바꿈의 세로
    # 간격은 매우 좁다(~4.5pt). 반면 문단과 다음 태그(사역 이름 등) 사이
    # 간격은 그보다 뚜렷이 넓고(~11pt+), 같은 줄에 나란히 배치된 서로 다른
    # 안내 캡션은 간격이 음수(y 범위가 겹침)로 나온다. 따라서 0 이상 8
    # 미만의 좁은 양수 간격일 때만 "줄바꿈 이어짐"으로 보고 합친다.
    right_sorted = sorted(right, key=lambda b: -b[0][3])
    merged_right = []
    for bbox, t in right_sorted:
        gap = merged_right[-1][0][1] - bbox[3] if merged_right else None
        if merged_right and not BULLET_RE.match(t) and gap is not None and 0 <= gap < 8:
            prev_bbox, prev_t = merged_right[-1]
            merged_right[-1] = (prev_bbox, prev_t.rstrip() + t.lstrip())
        else:
            merged_right.append((bbox, t))

    bullet_items = {}
    prayer_parts = []
    for bbox, t in merged_right:
        if t.strip() in GUIDE_CAPTIONS:
            continue
        if BULLET_RE.match(t):
            m = re.match(r"^([➊➋➌➍➎➏➐➑➒➓])\s*(.*)$", t, re.DOTALL)
            bullet_items[m.group(1)] = m.group(2).replace("\n", " ").strip()
        else:
            # 박스 내부의 줄바꿈(컬럼 폭 때문에 생긴 것)을 dewrap()으로 풀어준다.
            # 박스와 박스 사이의 구분(기도문 vs 사역 이름 등)은 아래에서
            # "\n\n"으로 유지되므로 여기서는 손대지 않는다.
            dewrapped = dewrap(t)
            # 일부 PDF 판에서는 "함께 기도   유아세례식"처럼 안내 캡션과
            # 사역/행사 이름이 같은 박스 안에 한 줄로 붙어 나온다. 캡션
            # 접두어만 떼어내고 나머지(실제 사역/행사 이름)는 살린다.
            for cap in GUIDE_CAPTIONS:
                if dewrapped.startswith(cap) and dewrapped[len(cap):len(cap) + 1].isspace():
                    dewrapped = dewrapped[len(cap):].strip()
                    break
            if dewrapped:
                prayer_parts.append(dewrapped)

    BULLET_ORDER = "➊➋➌➍➎➏➐➑➒➓"
    questions_list = []
    for idx, ch in enumerate(BULLET_ORDER):
        if ch in bullet_items:
            questions_list.append(f"{idx + 1}. {bullet_items[ch]}")
        elif ch == "➊":
            questions_list.append(f"1. {FIXED_Q1}")
    questions = "\n\n".join(questions_list)
    prayer = "\n\n".join(prayer_parts).strip()

    return {
        "date_display": date_display,
        "title": title,
        "passage": passage,
        "verse_ref": verse_ref,
        "overview": overview,
        "verse_text": verse_text,
        "meditation": meditation_text,
        "questions": questions,
        "prayer": prayer,
    }


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: parse_pdf_meditation.py <pdf_path> [M/D or YYYY-MM-DD]", file=sys.stderr)
        sys.exit(2)
    pdf_path = sys.argv[1]
    date_arg = sys.argv[2] if len(sys.argv) > 2 else today_kst()
    md = normalize_date_arg(date_arg)

    page_idx, boxes = find_entry_page(pdf_path, md)
    if boxes is None:
        print(
            json.dumps(
                {"error": "date_not_found_in_pdf", "date": md, "pdf": pdf_path},
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    data = parse_entry(boxes)
    data["date"] = date_arg
    data["source_url"] = "https://www.woorichurch.org/modu/s_board/list.asp?board_seq=47 (오프라인 PDF 파싱)"

    missing = [k for k in ("title", "passage", "verse_text") if not data.get(k)]
    if missing:
        print(
            json.dumps(
                {
                    "error": "parse_incomplete",
                    "missing_fields": missing,
                    "page_index": page_idx,
                    "data": data,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
