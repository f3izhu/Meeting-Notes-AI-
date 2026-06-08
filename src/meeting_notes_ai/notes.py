from __future__ import annotations

import re
from collections import Counter
from typing import Any


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "if",
    "in",
    "into",
    "is",
    "it",
    "no",
    "not",
    "of",
    "on",
    "or",
    "such",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "will",
    "with",
    "we",
    "you",
    "i",
}


def split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in raw if s and len(s.strip()) > 10]


def top_keywords(text: str, k: int = 12) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]+", text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(k)]


def extract_key_points(text: str, max_points: int = 6) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []

    keywords = set(top_keywords(text, k=20))
    scored: list[tuple[float, str]] = []
    for sentence in sentences:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]+", sentence.lower())
        unique_words = set(words)
        keyword_hits = len(unique_words.intersection(keywords))
        length_score = min(len(sentence) / 200.0, 1.0)
        score = keyword_hits + length_score
        scored.append((score, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = []
    seen = set()
    for _, sentence in scored:
        normalized = sentence.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append(sentence)
        if len(selected) >= max_points:
            break
    return selected


def extract_action_items(text: str, max_items: int = 8) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []

    patterns = [
        r"\baction item\b",
        r"\btodo\b",
        r"\bfollow up\b",
        r"\bnext step\b",
        r"\bneed to\b",
        r"\bshould\b",
        r"\bwill\b",
        r"\bby (monday|tuesday|wednesday|thursday|friday|next week|tomorrow)\b",
    ]
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

    out = []
    for sentence in sentences:
        if any(p.search(sentence) for p in compiled):
            out.append(sentence)
        if len(out) >= max_items:
            break
    return out


def extract_decisions(text: str, max_items: int = 8) -> list[str]:
    sentences = split_sentences(text)
    if not sentences:
        return []

    decision_patterns = [
        r"\bwe decided\b",
        r"\bdecision\b",
        r"\bagreed\b",
        r"\bapproved\b",
        r"\bresolved\b",
        r"\bwill proceed\b",
        r"\bwe chose\b",
    ]
    compiled = [re.compile(p, re.IGNORECASE) for p in decision_patterns]

    out = []
    for sentence in sentences:
        if any(p.search(sentence) for p in compiled):
            out.append(sentence)
        if len(out) >= max_items:
            break
    return out


def _extract_owner(sentence: str) -> str | None:
    patterns = [
        r"^(?P<owner>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|should|must|needs to|can)\b",
        r"\b(?i:owner)\s*[:\-]\s*(?P<owner>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        r"\b(?i:assignee)\s*[:\-]\s*(?P<owner>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    ]
    # 1. Try matching the original sentence first (e.g. "Owner: Daniel")
    for pattern in patterns:
        match = re.search(pattern, sentence)
        if match:
            owner = match.groupdict().get("owner")
            if owner:
                owner_clean = owner.strip()
                if owner_clean.lower() not in {"we", "they", "he", "she", "you", "i", "it", "this", "there", "everyone", "someone"}:
                    return owner_clean

    # 2. Clean common introductory prefixes and try matching again
    cleaned = sentence.strip()
    cleaned = re.sub(r"^(?i:action item|todo|follow up|next step|assignee|owner)\s*[:\-]?\s*", "", cleaned)
    cleaned = re.sub(r"^(?i:please|we need to)\s+", "", cleaned)

    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            owner = match.groupdict().get("owner")
            if owner:
                owner_clean = owner.strip()
                if owner_clean.lower() not in {"we", "they", "he", "she", "you", "i", "it", "this", "there", "everyone", "someone"}:
                    return owner_clean
    return None


def _extract_due(sentence: str) -> str | None:
    patterns = [
        r"\bby\s+([A-Za-z0-9,\-/ ]{2,30})",
        r"\bbefore\s+([A-Za-z0-9,\-/ ]{2,30})",
        r"\b(on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
        r"\b(tomorrow|next week|next month|today)\b",
        r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, sentence, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_task(sentence: str) -> str:
    text = sentence.strip()
    # Clean common introductory prefixes
    text = re.sub(r"^(?i:action item|todo|follow up|next step|assignee|owner)\s*[:\-]?\s*", "", text)
    text = re.sub(r"^(?i:please|we need to)\s+", "", text)

    text = re.sub(r"^(?P<owner>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|should|must|needs to|can)\s+", "", text)
    text = re.sub(r"\b(?i:owner|assignee)\s*[:\-]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", "", text)
    return text.strip(" .")


def extract_structured_action_items(text: str, max_items: int = 8) -> list[dict[str, Any]]:
    sentences = extract_action_items(text, max_items=max_items * 2)
    if not sentences:
        return []

    out: list[dict[str, Any]] = []
    seen = set()
    for sentence in sentences:
        normalized = sentence.lower().strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        owner = _extract_owner(sentence)
        due = _extract_due(sentence)
        task = _extract_task(sentence)
        out.append(
            {
                "task": task,
                "owner": owner,
                "due": due,
                "source_text": sentence.strip(),
            }
        )
        if len(out) >= max_items:
            break
    return out


def fallback_summary(text: str) -> dict[str, Any]:
    key_points = extract_key_points(text)
    action_items = extract_action_items(text)
    decisions = extract_decisions(text)
    structured_items = extract_structured_action_items(text)
    summary_line = " ".join(key_points[:2]).strip()
    if not summary_line:
        summary_line = "Auto-generated local summary from the transcript."

    return {
        "meeting_summary": summary_line,
        "key_points": key_points,
        "action_items": action_items,
        "structured_action_items": structured_items,
        "decisions": decisions,
    }


def export_html(
    meeting_title: str,
    meeting_date: str,
    duration: str,
    segments_captured: int,
    avg_latency: float,
    summary: dict[str, Any],
    transcript_lines: list[str],
) -> str:
    """Generate a self-contained styled HTML document for meeting notes."""
    import html as html_mod

    title_esc = html_mod.escape(meeting_title or "Untitled Meeting")
    date_esc = html_mod.escape(meeting_date)
    summary_text = html_mod.escape(str(summary.get("meeting_summary", "")))

    def _list_html(items: list, css_class: str = "") -> str:
        if not items:
            return '<p class="muted">None recorded.</p>'
        parts = []
        for item in items:
            if isinstance(item, dict):
                task = html_mod.escape(str(item.get("task", "")))
                owner = html_mod.escape(str(item.get("owner") or "Unassigned"))
                due = html_mod.escape(str(item.get("due") or "No due date"))
                parts.append(
                    f'<li class="{css_class}">'
                    f'<span class="task">{task}</span>'
                    f'<span class="meta">Owner: {owner} &middot; Due: {due}</span>'
                    f'</li>'
                )
            else:
                parts.append(f'<li class="{css_class}">{html_mod.escape(str(item))}</li>')
        return "<ul>" + "\n".join(parts) + "</ul>"

    key_points_html = _list_html(summary.get("key_points", []))
    decisions_html = _list_html(summary.get("decisions", []))
    action_items_html = _list_html(summary.get("action_items", []))
    structured_html = _list_html(summary.get("structured_action_items", []), "structured")

    transcript_html = "\n".join(
        f"<div class='seg'>{html_mod.escape(line)}</div>" for line in transcript_lines
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_esc} - Meeting Notes</title>
<style>
  :root {{
    --bg: #1e1e2e; --surface: #252538; --text: #cdd6f4;
    --muted: #7f849c; --accent: #89b4fa; --green: #a6e3a1;
    --yellow: #f9e2af; --pink: #f5c2e7; --red: #f38ba8;
    --border: #313244;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text);
    line-height: 1.6; padding: 2rem;
    max-width: 900px; margin: 0 auto;
  }}
  h1 {{
    color: var(--accent); font-size: 1.8rem;
    border-bottom: 2px solid var(--border); padding-bottom: 0.6rem;
    margin-bottom: 0.3rem;
  }}
  .meta-bar {{
    color: var(--muted); font-size: 0.85rem; margin-bottom: 1.6rem;
  }}
  .meta-bar span {{ margin-right: 1.5rem; }}
  h2 {{
    color: var(--accent); font-size: 1.15rem; margin-top: 1.6rem;
    margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;
  }}
  .summary-box {{
    background: var(--surface); padding: 1rem 1.2rem;
    border-left: 3px solid var(--accent); border-radius: 6px;
    margin-bottom: 0.5rem;
  }}
  ul {{ list-style: none; padding: 0; }}
  li {{
    background: var(--surface); padding: 0.6rem 1rem;
    border-radius: 6px; margin-bottom: 0.35rem;
    border-left: 3px solid var(--green);
  }}
  li.structured {{
    border-left-color: var(--yellow);
    display: flex; flex-direction: column; gap: 0.15rem;
  }}
  li.structured .task {{ font-weight: 600; }}
  li.structured .meta {{ color: var(--muted); font-size: 0.85rem; }}
  .muted {{ color: var(--muted); font-style: italic; }}
  .transcript {{
    background: #11111b; padding: 1rem; border-radius: 6px;
    max-height: 400px; overflow-y: auto; font-family: 'Consolas', monospace;
    font-size: 0.85rem; line-height: 1.5;
  }}
  .transcript .seg {{
    padding: 0.15rem 0;
    border-bottom: 1px solid var(--border);
  }}
  .footer {{
    margin-top: 2rem; padding-top: 1rem;
    border-top: 1px solid var(--border);
    color: var(--muted); font-size: 0.75rem; text-align: center;
  }}
  @media print {{
    body {{ background: #fff; color: #222; padding: 1rem; }}
    h1, h2 {{ color: #1a1a2e; }}
    li, .summary-box, .transcript {{ background: #f5f5f5; border-color: #ccc; }}
    .transcript {{ max-height: none; }}
  }}
</style>
</head>
<body>
<h1>{title_esc}</h1>
<div class="meta-bar">
  <span>📅 {date_esc}</span>
  <span>⏱ {html_mod.escape(duration)}</span>
  <span>📊 {segments_captured} segments</span>
  <span>⚡ {avg_latency:.2f}s avg latency</span>
</div>

<h2>📝 Summary</h2>
<div class="summary-box">{summary_text}</div>

<h2>💡 Key Points</h2>
{key_points_html}

<h2>🤝 Decisions</h2>
{decisions_html}

<h2>✅ Action Items</h2>
{action_items_html}

<h2>📋 Structured Action Items</h2>
{structured_html}

<h2>🎙 Full Transcript</h2>
<div class="transcript">{transcript_html}</div>

<div class="footer">Generated by Meeting Notes AI</div>
</body>
</html>"""

