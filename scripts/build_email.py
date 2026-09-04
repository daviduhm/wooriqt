#!/usr/bin/env python3
"""
fetch_meditation.py 가 만든 공식 묵상 JSON에, AI가 작성한 보충 묵상 필드를
합쳐 이메일 제목/HTML 본문/텍스트 본문을 만든다.

사용법:
    python3 build_email.py <merged.json>

merged.json 은 fetch_meditation.py 출력 필드에 더해 다음을 포함해야 한다:
    background          : str  (🏛️ 말씀의 배경, 문단은 빈 줄로 구분)
    deeper_reflection    : str  (🌿 더 깊은 묵상, 문단은 빈 줄로 구분)
    ai_prayer            : str  (🙏 오늘의 기도, AI가 작성)
    reflection_questions : str  (💭 적용 질문, AI가 작성, 줄바꿈으로 구분해도 됨)

출력: {"subject": ..., "html": ..., "text": ...} 를 stdout에 JSON으로 출력.
"""
import html
import json
import sys


def esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def paragraphs_html(text: str) -> str:
    if not text:
        return ""
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    out = []
    for p in parts:
        p_html = esc(p).replace("\n", "<br>")
        out.append(f'<p style="margin:0 0 14px;line-height:1.8;color:#333;">{p_html}</p>')
    return "\n".join(out)


def paragraphs_text(text: str) -> str:
    return (text or "").strip()


def section_html(icon_title: str, body_html: str) -> str:
    return f"""
    <h2 style="font-size:17px;color:#1a1a1a;margin:28px 0 10px;border-left:4px solid #4a6fa5;padding-left:10px;">{esc(icon_title)}</h2>
    {body_html}
    """


def box_html(body_html: str, bg="#f4f6fb", border="#4a6fa5") -> str:
    return (
        f'<div style="background:{bg};border-left:4px solid {border};'
        f'padding:14px 16px;border-radius:4px;margin:0 0 14px;">{body_html}</div>'
    )


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
            f'<p style="margin:0 0 4px;color:#555;">✍️ 오늘의 한 구절: {esc(verse_ref)}</p>'
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
        prayer_combined_html += box_html(paragraphs_html(official_prayer), bg="#fff8ec", border="#c9974c")
    if ai_prayer:
        prayer_combined_html += box_html(paragraphs_html(ai_prayer), bg="#fff8ec", border="#c9974c")
    if prayer_combined_html:
        body_sections.append(section_html("🙏 오늘의 기도", prayer_combined_html))

    q_combined = "\n\n".join([q for q in [official_questions, reflection_questions] if q])
    if q_combined:
        body_sections.append(section_html("💭 적용 질문", paragraphs_html(q_combined)))

    html_body = f"""
<div style="max-width:640px;margin:0 auto;padding:24px;font-family:'Apple SD Gothic Neo',-apple-system,BlinkMacSystemFont,'Malgun Gothic',sans-serif;">
  <h1 style="font-size:20px;color:#1a1a1a;margin:0 0 4px;">📖 한 구절 묵상 · {esc(date_display)}</h1>
  <p style="font-size:16px;color:#4a6fa5;font-weight:600;margin:0 0 20px;">{esc(title)}</p>
  {"".join(body_sections)}
  <p style="margin:28px 0 4px;color:#333;">— 오늘도 말씀 안에서 평안한 하루 되세요.</p>
  <p style="margin:16px 0 0;font-size:12px;color:#999;">출처: <a href="{esc(source_url)}" style="color:#999;">{esc(source_url)}</a></p>
</div>
""".strip()

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
    if len(sys.argv) != 2:
        print("usage: build_email.py <merged.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    result = build(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
