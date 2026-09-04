#!/usr/bin/env python3
"""
fetch_meditation.py 가 만든 공식 묵상 JSON에, AI가 작성한 보충 묵상 필드를
합쳐 이메일 제목/HTML 본문/텍스트 본문을 만든다.

사용법:
    python3 build_email.py <merged.json> [output_prefix]

merged.json 은 fetch_meditation.py 출력 필드에 더해 다음을 포함해야 한다:
    background            : str  (🏛️ 말씀의 배경, 문단은 빈 줄로 구분)
    deeper_reflection      : str  (🌿 더 깊은 묵상, 문단은 빈 줄로 구분)
    ai_prayer              : str  (🙏 오늘의 기도, AI가 작성)
    reflection_questions   : str  (💭 적용 질문, AI가 작성, 줄바꿈으로 구분해도 됨)

출력:
    - stdout: {"subject": ..., "html": ..., "text": ...} JSON (참고용).
    - output_prefix가 주어지면 다음 파일도 함께 쓴다(Gmail 전송 시 Read 도구로
      그대로 읽어 옮겨쓰기 위함 — stdout JSON을 손으로 파싱/재이스케이프하다가
      내용이 깨지는 것을 방지):
        <prefix>.subject.txt
        <prefix>.html
        <prefix>.text.txt
"""
import html
import json
import sys

# 이메일 전체에서 공통으로 쓰는 스타일을 <style> 블록으로 묶어 인라인 style
# 중복을 줄인다. (반복되는 inline style은 이메일 HTML 용량을 키워서, 이후
# 이 내용을 통째로 옮겨 적어야 하는 도구 호출에서 잘리거나 깨질 위험을 높인다.)
STYLE_BLOCK = """<style>
  .qt-wrap{max-width:640px;margin:0 auto;padding:24px;font-family:'Apple SD Gothic Neo',-apple-system,BlinkMacSystemFont,'Malgun Gothic',sans-serif;}
  .qt-h1{font-size:20px;color:#1a1a1a;margin:0 0 4px;}
  .qt-sub{font-size:16px;color:#4a6fa5;font-weight:600;margin:0 0 20px;}
  .qt-h2{font-size:17px;color:#1a1a1a;margin:28px 0 10px;border-left:4px solid #4a6fa5;padding-left:10px;}
  .qt-p{margin:0 0 14px;line-height:1.8;color:#333;}
  .qt-label{margin:0 0 4px;color:#555;}
  .qt-box{background:#f4f6fb;border-left:4px solid #4a6fa5;padding:14px 16px;border-radius:4px;margin:0 0 14px;}
  .qt-box-prayer{background:#fff8ec;border-left:4px solid #c9974c;padding:14px 16px;border-radius:4px;margin:0 0 14px;}
  .qt-footer{margin:28px 0 4px;color:#333;}
  .qt-source{margin:16px 0 0;font-size:12px;color:#999;}
  .qt-source a{color:#999;}
</style>"""


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def paragraphs_html(text: str) -> str:
    if not text:
        return ""
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    out = []
    for p in parts:
        p_html = esc(p).replace("\n", "<br>")
        out.append(f'<p class="qt-p">{p_html}</p>')
    return "\n".join(out)


def section_html(icon_title: str, body_html: str) -> str:
    return f'\n<h2 class="qt-h2">{esc(icon_title)}</h2>\n{body_html}\n'


def box_html(body_html: str, cls="qt-box") -> str:
    return f'<div class="{cls}">{body_html}</div>'


def build(data: dict) -> dict:
    date_display = data.get("date_display", data.get("date", ""))
    title = data.get("title", "")
    passage = data.get("passage", "")
    verse_ref = data.get("verse_ref", "")
    overview = data.get("overview", "")
    verse_text = data.get("verse_text", "")
    official_meditation = data.get("meditation", "")
    official_questions = data.get("questions", "")
    official_prayer = data.get("prayer", "")
    background = data.get("background", "")
    deeper_reflection = data.get("deeper_reflection", "")
    ai_prayer = data.get("ai_prayer", "")
    reflection_questions = data.get("reflection_questions", "")
    source_url = data.get("source_url", "")

    subject = f"📖 한 구절 묵상 · {date_display} — {title}"

    body_sections = []

    body_sections.append(
        section_html(
            f"📌 오늘의 본문: {passage}",
            f'<p class="qt-label">✍️ 오늘의 한 구절: {esc(verse_ref)}</p>'
            + box_html(paragraphs_html(verse_text)),
        )
    )

    if overview:
        body_sections.append(section_html("📖 본문 개요", paragraphs_html(overview)))

    if background:
        body_sections.append(section_html("🏛️ 말씀의 배경", paragraphs_html(background)))

    if official_meditation:
        body_sections.append(
            section_html("🌿 한 구절 묵상 (공식)", paragraphs_html(official_meditation))
        )

    if deeper_reflection:
        body_sections.append(
            section_html("🌿 더 깊은 묵상", paragraphs_html(deeper_reflection))
        )

    prayer_combined_html = ""
    if official_prayer:
        prayer_combined_html += box_html(paragraphs_html(official_prayer), cls="qt-box-prayer")
    if ai_prayer:
        prayer_combined_html += box_html(paragraphs_html(ai_prayer), cls="qt-box-prayer")
    if prayer_combined_html:
        body_sections.append(section_html("🙏 오늘의 기도", prayer_combined_html))

    q_combined = "\n\n".join([q for q in [official_questions, reflection_questions] if q])
    if q_combined:
        body_sections.append(section_html("💭 적용 질문", paragraphs_html(q_combined)))

    html_body = f"""{STYLE_BLOCK}
<div class="qt-wrap">
  <h1 class="qt-h1">📖 한 구절 묵상 · {esc(date_display)}</h1>
  <p class="qt-sub">{esc(title)}</p>
  {"".join(body_sections)}
  <p class="qt-footer">— 오늘도 말씀 안에서 평안한 하루 되세요.</p>
  <p class="qt-source">출처: <a href="{esc(source_url)}">{esc(source_url)}</a></p>
</div>""".strip()

    text_lines = [
        f"📖 한 구절 묵상 · {date_display}",
        title,
        "",
        f"📌 오늘의 본문: {passage}",
        f"✍️ 오늘의 한 구절: {verse_ref}",
        verse_text,
        "",
    ]
    if overview:
        text_lines += ["📖 본문 개요", overview, ""]
    if background:
        text_lines += ["🏛️ 말씀의 배경", background, ""]
    if official_meditation:
        text_lines += ["🌿 한 구절 묵상 (공식)", official_meditation, ""]
    if deeper_reflection:
        text_lines += ["🌿 더 깊은 묵상", deeper_reflection, ""]
    if official_prayer or ai_prayer:
        text_lines += ["🙏 오늘의 기도"]
        if official_prayer:
            text_lines += [official_prayer, ""]
        if ai_prayer:
            text_lines += [ai_prayer, ""]
    if q_combined:
        text_lines += ["💭 적용 질문", q_combined, ""]
    text_lines += ["— 오늘도 말씀 안에서 평안한 하루 되세요.", "", f"출처: {source_url}"]
    text_body = "\n".join(text_lines)

    return {"subject": subject, "html": html_body, "text": text_body}


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: build_email.py <merged.json> [output_prefix]", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    result = build(data)

    if len(sys.argv) == 3:
        prefix = sys.argv[2]
        with open(f"{prefix}.subject.txt", "w", encoding="utf-8") as f:
            f.write(result["subject"])
        with open(f"{prefix}.html", "w", encoding="utf-8") as f:
            f.write(result["html"])
        with open(f"{prefix}.text.txt", "w", encoding="utf-8") as f:
            f.write(result["text"])
        print(f"wrote {prefix}.subject.txt ({len(result['subject'])} chars)", file=sys.stderr)
        print(f"wrote {prefix}.html ({len(result['html'])} chars)", file=sys.stderr)
        print(f"wrote {prefix}.text.txt ({len(result['text'])} chars)", file=sys.stderr)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
