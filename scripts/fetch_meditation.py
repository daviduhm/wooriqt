#!/usr/bin/env python3
"""
분당우리교회 '한 구절 묵상' 페이지에서 지정한 날짜(기본: 오늘, KST)의
공식 묵상 콘텐츠를 가져와 JSON으로 출력한다.

사용법:
    python3 fetch_meditation.py [YYYY-MM-DD]

주의:
    이 환경의 네트워크 정책상 www.woorichurch.org 는 차단되어 있고
    www 없는 woorichurch.org 만 허용되어 있다. 반드시 naked domain을 쓸 것.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
BASE_URL = "https://woorichurch.org/modu/ov/ov_meditation.asp"


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def fetch_html(date_str: str) -> str:
    url = f"{BASE_URL}?lef=3&ov_date={date_str}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    # 페이지는 Content-Type 헤더상 utf-8 이지만 혹시 몰라 fallback 처리
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp949", errors="replace")


def clean_block(text: str) -> str:
    """<br> 계열을 줄바꿈으로, 나머지 태그를 제거하고 엔티티를 unescape."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    # 각 줄 앞뒤 공백 정리, 과도한 빈 줄 정리
    lines = [ln.strip() for ln in text.splitlines()]
    # 연속 빈 줄은 하나로
    cleaned = []
    prev_blank = False
    for ln in lines:
        if ln == "":
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(ln)
            prev_blank = False
    return "\n".join(cleaned).strip()


def extract_section(page: str, label: str) -> str:
    pattern = (
        r'<h4[^>]*class="tit"[^>]*>\s*'
        + re.escape(label)
        + r'\s*</h4>\s*<div[^>]*class="cont"[^>]*>(.*?)</div>'
    )
    m = re.search(pattern, page, re.DOTALL)
    if not m:
        return ""
    return clean_block(m.group(1))


def extract_meta(page: str) -> dict:
    def find(pattern):
        m = re.search(pattern, page, re.DOTALL)
        return clean_block(m.group(1)) if m else ""

    date_disp = find(r'<p class="date">(.*?)</p>')
    title = find(r'<p class="sbj">(.*?)</p>')
    passage = find(r'오늘의 본문\s*:\s*(.*?)</p>')
    verse_ref = find(r'오늘의 한 구절\s*:\s*(.*?)</p>')
    return {
        "date_display": date_disp,
        "title": title,
        "passage": passage,
        "verse_ref": verse_ref,
    }


def parse(page: str, date_str: str) -> dict:
    meta = extract_meta(page)
    data = {
        "date": date_str,
        "date_display": meta["date_display"],
        "title": meta["title"],
        "passage": meta["passage"],
        "verse_ref": meta["verse_ref"],
        "overview": extract_section(page, "본문 개요"),
        "verse_text": extract_section(page, "오늘의 한 구절"),
        "meditation": extract_section(page, "한 구절 묵상"),
        "questions": extract_section(page, "묵상질문"),
        "prayer": extract_section(page, "심정이 통하는 기도"),
        "source_url": f"{BASE_URL}?ov_date={date_str}",
    }
    return data


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else today_kst()
    page = fetch_html(date_str)
    data = parse(page, date_str)

    missing = [k for k in ("title", "passage", "verse_text") if not data.get(k)]
    if missing:
        print(
            json.dumps(
                {"error": "parse_incomplete", "missing_fields": missing, "data": data},
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
