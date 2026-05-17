"""
code_audit.py
=============

Deterministic accessibility lint for the ``/api/review-code`` endpoint.

The endpoint sends user-submitted source code (HTML, JSX, Vue, plain CSS, …)
into an LLM. To stop the model from inventing findings we first run this
static lint to extract objective evidence: rule_id, line number, severity,
WCAG criterion, message, and the offending snippet. The LLM then receives
that report as ground truth and only adds semantic / contextual analysis on
top.

Public API
----------
* ``audit_code(code, hint_lang='auto')`` → ``evidence`` dict
* ``evidence_summary_for_prompt(evidence)`` → plain-text summary for the LLM
* ``CODE_RULE_REFERENCES`` → mapping rule_id → {title, wcag_criterion, …}

Severity scale: ``critical | high | moderate | low``.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Rule reference table — every rule_id maps to a human title, WCAG criterion,
# and canonical W3C / WebAIM source so the final report is sourced.
# ---------------------------------------------------------------------------
CODE_RULE_REFERENCES: Dict[str, Dict[str, str]] = {
    "img-missing-alt": {
        "title": "Image element is missing the alt attribute",
        "wcag_criterion": "1.1.1",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
        "deep_dive": "https://webaim.org/techniques/alttext/",
    },
    "img-redundant-alt": {
        "title": "Alt text uses redundant phrases like 'image of' or 'photo of'",
        "wcag_criterion": "1.1.1",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
        "deep_dive": "https://webaim.org/techniques/alttext/#context",
    },
    "input-missing-label": {
        "title": "Form input has no associated <label> or aria-label",
        "wcag_criterion": "3.3.2",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/labels-or-instructions.html",
        "deep_dive": "https://www.w3.org/WAI/tutorials/forms/labels/",
    },
    "button-empty-name": {
        "title": "Button has no accessible name (no text, aria-label, or title)",
        "wcag_criterion": "4.1.2",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/name-role-value.html",
        "deep_dive": "https://www.w3.org/WAI/ARIA/apg/patterns/button/",
    },
    "link-empty-name": {
        "title": "Link has no accessible name",
        "wcag_criterion": "2.4.4",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context.html",
        "deep_dive": "https://www.w3.org/WAI/tips/writing/#make-link-text-meaningful",
    },
    "link-generic-text": {
        "title": "Link text is generic ('click here', 'read more', etc.)",
        "wcag_criterion": "2.4.4",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context.html",
        "deep_dive": "https://www.nngroup.com/articles/writing-links/",
    },
    "missing-lang": {
        "title": "<html> element is missing the lang attribute",
        "wcag_criterion": "3.1.1",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/language-of-page.html",
        "deep_dive": "https://www.w3.org/International/questions/qa-html-language-declarations",
    },
    "missing-title": {
        "title": "Document is missing a <title> element",
        "wcag_criterion": "2.4.2",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/page-titled.html",
        "deep_dive": "https://webaim.org/techniques/screenreader/#title",
    },
    "missing-viewport": {
        "title": "Missing responsive viewport meta tag",
        "wcag_criterion": "1.4.10",
        "level": "AA",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/reflow.html",
        "deep_dive": "https://developer.mozilla.org/docs/Web/HTML/Viewport_meta_tag",
    },
    "viewport-blocks-zoom": {
        "title": "Viewport meta tag disables user zoom (user-scalable=no / maximum-scale=1)",
        "wcag_criterion": "1.4.4",
        "level": "AA",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/resize-text.html",
        "deep_dive": "https://adrianroselli.com/2015/10/dont-disable-zoom.html",
    },
    "heading-skipped-level": {
        "title": "Heading level is skipped (e.g. h1 → h3)",
        "wcag_criterion": "1.3.1",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
        "deep_dive": "https://www.w3.org/WAI/tutorials/page-structure/headings/",
    },
    "no-h1": {
        "title": "Document defines no <h1>",
        "wcag_criterion": "1.3.1",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
        "deep_dive": "https://www.w3.org/WAI/tutorials/page-structure/headings/",
    },
    "positive-tabindex": {
        "title": "Positive tabindex disrupts natural focus order",
        "wcag_criterion": "2.4.3",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/focus-order.html",
        "deep_dive": "https://www.scottohara.me/blog/2019/05/25/tabindex.html",
    },
    "click-on-non-interactive": {
        "title": "onClick handler on a non-interactive element (div/span) without role/tabindex",
        "wcag_criterion": "2.1.1",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/keyboard.html",
        "deep_dive": "https://www.w3.org/WAI/ARIA/apg/patterns/button/",
    },
    "outline-none": {
        "title": "CSS removes focus outline without providing a visible alternative",
        "wcag_criterion": "2.4.7",
        "level": "AA",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/focus-visible.html",
        "deep_dive": "https://www.sarasoueidan.com/blog/focus-indicators/",
    },
    "aria-hidden-on-focusable": {
        "title": "aria-hidden=\"true\" applied to a focusable element",
        "wcag_criterion": "4.1.2",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/name-role-value.html",
        "deep_dive": "https://www.tpgi.com/short-note-on-aria-hidden-focusable-elements/",
    },
    "duplicate-id": {
        "title": "Duplicate id attribute (breaks label/aria associations)",
        "wcag_criterion": "4.1.1",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/parsing.html",
        "deep_dive": "https://dequeuniversity.com/rules/axe/4.7/duplicate-id",
    },
    "color-contrast-suspect": {
        "title": "Suspected low color-contrast pairing in CSS",
        "wcag_criterion": "1.4.3",
        "level": "AA",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html",
        "deep_dive": "https://webaim.org/articles/contrast/",
    },
    "iframe-missing-title": {
        "title": "<iframe> is missing a title attribute",
        "wcag_criterion": "4.1.2",
        "level": "A",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/name-role-value.html",
        "deep_dive": "https://dequeuniversity.com/rules/axe/4.7/frame-title",
    },
}


# Severity assigned per rule_id.
_SEVERITY: Dict[str, str] = {
    "img-missing-alt": "critical",
    "input-missing-label": "critical",
    "button-empty-name": "critical",
    "link-empty-name": "critical",
    "click-on-non-interactive": "critical",
    "missing-lang": "high",
    "missing-title": "high",
    "viewport-blocks-zoom": "high",
    "aria-hidden-on-focusable": "high",
    "duplicate-id": "high",
    "iframe-missing-title": "high",
    "no-h1": "moderate",
    "heading-skipped-level": "moderate",
    "positive-tabindex": "moderate",
    "outline-none": "moderate",
    "img-redundant-alt": "low",
    "link-generic-text": "low",
    "missing-viewport": "moderate",
    "color-contrast-suspect": "low",
}

# Per-occurrence point deductions — same scale as the score endpoint.
_POINTS = {"critical": 10, "high": 7, "moderate": 4, "low": 2}
_GENERIC_LINK_TEXTS = {
    "click here", "here", "read more", "more", "learn more",
    "this", "this link", "link", "details", "info", "more info",
    "continue", "go",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def audit_code(code: str, hint_lang: str = "auto") -> Dict:
    """Run the deterministic lint and return an evidence dict."""
    if not code:
        return _empty_result(hint_lang)

    language = _detect_language(code, hint_lang)
    lines = code.splitlines()
    findings: List[Dict] = []

    if language in {"html", "jsx", "vue", "auto"}:
        findings.extend(_lint_markup(code, lines))
    if language in {"css", "html", "jsx", "vue", "auto"}:
        findings.extend(_lint_css(code, lines))

    # Deduplicate identical (rule_id, line) pairs.
    seen = set()
    unique: List[Dict] = []
    for f in findings:
        key = (f["rule_id"], f["line"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    findings = sorted(unique, key=lambda f: (f["line"] or 0, f["rule_id"]))

    severity_counts = Counter({"critical": 0, "high": 0, "moderate": 0, "low": 0})
    for f in findings:
        severity_counts[f["severity"]] += 1

    score = 100
    for sev, n in severity_counts.items():
        score -= _POINTS[sev] * n
    score = max(0, min(100, score))

    sources = []
    seen_rules = set()
    for f in findings:
        if f["rule_id"] in seen_rules:
            continue
        seen_rules.add(f["rule_id"])
        ref = CODE_RULE_REFERENCES.get(f["rule_id"], {})
        if ref:
            sources.append({
                "rule_id": f["rule_id"],
                "wcag_criterion": ref.get("wcag_criterion"),
                "title": ref.get("title"),
                "w3c": ref.get("w3c"),
                "deep_dive": ref.get("deep_dive"),
            })

    return {
        "language": language,
        "line_count": len(lines),
        "char_count": len(code),
        "deterministic_score": score,
        "severity_counts": dict(severity_counts),
        "findings": findings,
        "sources": sources,
    }


def evidence_summary_for_prompt(evidence: Dict) -> str:
    """Compact text representation of the lint, fed to the LLM as ground truth."""
    sc = evidence["severity_counts"]
    lines = [
        f"Language: {evidence['language']}",
        f"Lines of code: {evidence['line_count']}",
        f"Deterministic score: {evidence['deterministic_score']}/100",
        f"Severity counts: critical={sc['critical']} high={sc['high']} "
        f"moderate={sc['moderate']} low={sc['low']}",
        "",
        "Findings (rule_id @ line — severity — message):",
    ]
    if not evidence["findings"]:
        lines.append("  (no static issues detected)")
    else:
        for f in evidence["findings"][:60]:  # cap to keep prompt small
            lines.append(
                f"  {f['rule_id']} @ L{f['line']} — {f['severity']} — "
                f"WCAG {f['wcag_criterion']} — {f['message']}"
            )
        if len(evidence["findings"]) > 60:
            lines.append(f"  ... and {len(evidence['findings']) - 60} more.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _empty_result(language: str) -> Dict:
    return {
        "language": language,
        "line_count": 0,
        "char_count": 0,
        "deterministic_score": 100,
        "severity_counts": {"critical": 0, "high": 0, "moderate": 0, "low": 0},
        "findings": [],
        "sources": [],
    }


def _detect_language(code: str, hint: str) -> str:
    h = (hint or "").lower().strip()
    if h in {"html", "jsx", "tsx", "vue", "css", "scss"}:
        return "jsx" if h == "tsx" else h
    sample = code[:2000].lower()
    if "<template" in sample or 'v-for' in sample or 'v-bind' in sample:
        return "vue"
    if re.search(r'classname=|=\{|/>\s*$', code[:4000]):
        return "jsx"
    if "<html" in sample or "<!doctype" in sample or re.search(r'<\w+[^>]*>', sample):
        return "html"
    if re.search(r'\{[^{}]*:[^{}]*;[^{}]*\}', code):
        return "css"
    return "html"


def _line_of(code: str, pos: int) -> int:
    return code.count("\n", 0, pos) + 1


def _snippet_of(lines: List[str], line_no: int) -> str:
    if not lines or line_no < 1 or line_no > len(lines):
        return ""
    return lines[line_no - 1].strip()[:200]


def _make_finding(rule_id: str, line: int, message: str, snippet: str) -> Dict:
    return {
        "rule_id": rule_id,
        "severity": _SEVERITY.get(rule_id, "moderate"),
        "wcag_criterion": CODE_RULE_REFERENCES.get(rule_id, {}).get("wcag_criterion", ""),
        "line": line,
        "message": message,
        "snippet": snippet,
    }


# ---------------------------------------------------------------------------
# Markup (HTML / JSX / Vue) lint
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r'<\s*(?P<tag>[A-Za-z][A-Za-z0-9]*)\b(?P<attrs>[^>]*?)/?\s*>', re.IGNORECASE)
_ATTR_RE = re.compile(r'''(?P<name>[\w:-]+)\s*=\s*(?P<q>["'])(?P<val>.*?)(?P=q)''', re.DOTALL)
_BARE_ATTR_RE = re.compile(r'(?<![\w:-])(?P<name>[\w:-]+)(?=\s|/?>|$)')


def _parse_attrs(attr_blob: str) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    for m in _ATTR_RE.finditer(attr_blob):
        attrs[m.group("name").lower()] = m.group("val")
    # Also catch boolean attributes (no value).
    cleaned = _ATTR_RE.sub("", attr_blob)
    for m in _BARE_ATTR_RE.finditer(cleaned):
        name = m.group("name").lower()
        if name and name not in attrs and "=" not in name:
            attrs.setdefault(name, "")
    return attrs


def _has_accessible_name(attrs: Dict[str, str], inner_text: str = "") -> bool:
    if (inner_text or "").strip():
        return True
    for k in ("aria-label", "aria-labelledby", "title", "alt"):
        if attrs.get(k, "").strip():
            return True
    return False


def _inner_text_after(code: str, end_pos: int, tag: str) -> str:
    """Best-effort extraction of inner text up to closing </tag>."""
    closer = re.compile(r'<\s*/\s*' + re.escape(tag) + r'\s*>', re.IGNORECASE)
    m = closer.search(code, end_pos)
    if not m:
        return ""
    inner = code[end_pos:m.start()]
    # Strip nested tags + JSX expressions.
    inner = re.sub(r'<[^>]+>', ' ', inner)
    inner = re.sub(r'\{[^{}]*\}', ' ', inner)
    return inner.strip()


def _lint_markup(code: str, lines: List[str]) -> List[Dict]:
    findings: List[Dict] = []
    has_html_tag = False
    has_lang = False
    has_title = False
    has_viewport = False
    has_h1 = False
    last_heading_level: Optional[int] = None
    ids_seen: Counter = Counter()
    id_first_line: Dict[str, int] = {}

    for m in _TAG_RE.finditer(code):
        tag = m.group("tag").lower()
        attrs = _parse_attrs(m.group("attrs") or "")
        line = _line_of(code, m.start())
        snip = _snippet_of(lines, line)

        # Track ids for duplicate detection.
        elem_id = attrs.get("id", "").strip()
        if elem_id:
            ids_seen[elem_id] += 1
            id_first_line.setdefault(elem_id, line)

        # aria-hidden on inherently focusable elements.
        if attrs.get("aria-hidden", "").lower() == "true" and tag in {
            "a", "button", "input", "select", "textarea", "iframe",
        }:
            findings.append(_make_finding(
                "aria-hidden-on-focusable", line,
                f"<{tag}> has aria-hidden=\"true\" but is focusable.", snip,
            ))

        # Positive tabindex.
        if "tabindex" in attrs:
            try:
                if int(attrs["tabindex"]) > 0:
                    findings.append(_make_finding(
                        "positive-tabindex", line,
                        f"tabindex={attrs['tabindex']} forces a non-natural focus order.",
                        snip,
                    ))
            except ValueError:
                pass

        if tag == "html":
            has_html_tag = True
            if attrs.get("lang", "").strip():
                has_lang = True
            else:
                findings.append(_make_finding(
                    "missing-lang", line,
                    "<html> element has no lang attribute.", snip,
                ))

        elif tag == "title":
            has_title = True

        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "viewport":
                has_viewport = True
                content = attrs.get("content", "").lower()
                if "user-scalable=no" in content or re.search(r'maximum-scale\s*=\s*1(?!\.)', content):
                    findings.append(_make_finding(
                        "viewport-blocks-zoom", line,
                        "Viewport meta blocks user zoom.", snip,
                    ))

        elif tag == "img":
            # JSX/Vue dynamic alt: alt={...} or :alt="..." should not flag.
            attr_blob = m.group("attrs") or ""
            has_dynamic_alt = bool(
                re.search(r'\balt\s*=\s*\{', attr_blob) or
                re.search(r'\b:alt\s*=', attr_blob) or
                re.search(r'\bv-bind:alt\s*=', attr_blob)
            )
            if "alt" not in attrs and not has_dynamic_alt:
                # Decorative role exception.
                if attrs.get("role", "").lower() != "presentation" and \
                   attrs.get("aria-hidden", "").lower() != "true":
                    findings.append(_make_finding(
                        "img-missing-alt", line,
                        "<img> is missing an alt attribute.", snip,
                    ))
            elif "alt" in attrs:
                alt_val = attrs["alt"].strip().lower()
                if re.match(r'^(image|photo|picture|graphic|icon)\s+of\b', alt_val):
                    findings.append(_make_finding(
                        "img-redundant-alt", line,
                        f"alt=\"{attrs['alt']}\" starts with a redundant phrase.",
                        snip,
                    ))

        elif tag == "input":
            input_type = attrs.get("type", "text").lower()
            if input_type in {"hidden", "submit", "button", "reset", "image"}:
                pass  # no label needed
            else:
                has_label_attr = bool(
                    attrs.get("aria-label", "").strip() or
                    attrs.get("aria-labelledby", "").strip() or
                    attrs.get("title", "").strip()
                )
                # Look for an associated <label for="id">.
                input_id = attrs.get("id", "").strip()
                has_for_label = False
                if input_id:
                    has_for_label = bool(re.search(
                        r'<\s*label\b[^>]*\bfor\s*=\s*["\']' + re.escape(input_id) + r'["\']',
                        code, re.IGNORECASE,
                    ))
                if not (has_label_attr or has_for_label):
                    findings.append(_make_finding(
                        "input-missing-label", line,
                        f"<input type=\"{input_type}\"> has no associated <label> or aria-label.",
                        snip,
                    ))

        elif tag == "button":
            inner = _inner_text_after(code, m.end(), "button")
            if not _has_accessible_name(attrs, inner):
                findings.append(_make_finding(
                    "button-empty-name", line,
                    "<button> has no accessible name.", snip,
                ))

        elif tag == "a":
            inner = _inner_text_after(code, m.end(), "a")
            if not _has_accessible_name(attrs, inner):
                findings.append(_make_finding(
                    "link-empty-name", line,
                    "<a> has no accessible name.", snip,
                ))
            else:
                text_for_check = (inner or attrs.get("aria-label", "") or attrs.get("title", "")).strip().lower()
                # Strip surrounding punctuation.
                text_for_check = re.sub(r'[^\w\s]', '', text_for_check).strip()
                if text_for_check in _GENERIC_LINK_TEXTS:
                    findings.append(_make_finding(
                        "link-generic-text", line,
                        f"Link text \"{text_for_check}\" is too generic.", snip,
                    ))

        elif tag == "iframe":
            if not (attrs.get("title", "").strip() or attrs.get("aria-label", "").strip()):
                findings.append(_make_finding(
                    "iframe-missing-title", line,
                    "<iframe> is missing a title attribute.", snip,
                ))

        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            if level == 1:
                has_h1 = True
            if last_heading_level is not None and level > last_heading_level + 1:
                findings.append(_make_finding(
                    "heading-skipped-level", line,
                    f"Heading jumps from h{last_heading_level} to h{level}.",
                    snip,
                ))
            last_heading_level = level

        elif tag in {"div", "span"}:
            attr_blob = m.group("attrs") or ""
            if re.search(r'\bonclick\s*=', attr_blob, re.IGNORECASE):
                # Acceptable when role and tabindex make it focusable.
                role = attrs.get("role", "").lower()
                if role not in {"button", "link", "menuitem", "tab", "switch", "checkbox"} \
                   or "tabindex" not in attrs:
                    findings.append(_make_finding(
                        "click-on-non-interactive", line,
                        f"<{tag}> has an onClick handler but is not a true interactive element.",
                        snip,
                    ))

    # ---- Document-level checks (only when this looks like a full HTML doc).
    looks_like_doc = has_html_tag or "<!doctype" in code.lower() or "<head" in code.lower()
    if looks_like_doc:
        if not has_lang and not has_html_tag:
            findings.append(_make_finding(
                "missing-lang", 1,
                "Document does not declare a lang attribute on <html>.",
                _snippet_of(lines, 1),
            ))
        if not has_title:
            findings.append(_make_finding(
                "missing-title", 1,
                "Document is missing a <title> element.",
                _snippet_of(lines, 1),
            ))
        if not has_viewport:
            findings.append(_make_finding(
                "missing-viewport", 1,
                "Document is missing a responsive viewport meta tag.",
                _snippet_of(lines, 1),
            ))
        if not has_h1:
            findings.append(_make_finding(
                "no-h1", 1,
                "Document defines no <h1> heading.",
                _snippet_of(lines, 1),
            ))

    for elem_id, count in ids_seen.items():
        if count > 1:
            line = id_first_line.get(elem_id, 1)
            findings.append(_make_finding(
                "duplicate-id", line,
                f"Duplicate id=\"{elem_id}\" appears {count} times.",
                _snippet_of(lines, line),
            ))

    return findings


# ---------------------------------------------------------------------------
# CSS lint (focus + suspicious contrast pairings)
# ---------------------------------------------------------------------------
_OUTLINE_NONE_RE = re.compile(
    r'(?P<sel>[^{}]+)\{[^{}]*outline\s*:\s*(?:none|0(?:px)?)\s*[;}]',
    re.IGNORECASE,
)


def _lint_css(code: str, lines: List[str]) -> List[Dict]:
    findings: List[Dict] = []

    for m in _OUTLINE_NONE_RE.finditer(code):
        block = m.group(0).lower()
        # If the same rule sets a visible alternative, skip.
        if re.search(r'(box-shadow|outline-offset|border|background)\s*:', block):
            continue
        # If the selector targets :focus/:focus-visible specifically, that's worse.
        sel = m.group("sel").lower()
        if ":focus" in sel or sel.strip() in {"*", "a", "button", "input", "textarea", "select"}:
            line = _line_of(code, m.start())
            findings.append(_make_finding(
                "outline-none", line,
                "Removes focus outline without providing a visible alternative.",
                _snippet_of(lines, line),
            ))

    # Heuristic low-contrast: same color for color and background.
    rule_blocks = re.finditer(r'\{(?P<body>[^{}]+)\}', code)
    for rb in rule_blocks:
        body = rb.group("body")
        color = re.search(r'(?<!-)color\s*:\s*([^;]+);', body, re.IGNORECASE)
        bg = re.search(r'background(?:-color)?\s*:\s*([^;]+);', body, re.IGNORECASE)
        if color and bg:
            c = color.group(1).strip().lower()
            b = bg.group(1).strip().lower()
            if c and c == b:
                line = _line_of(code, rb.start())
                findings.append(_make_finding(
                    "color-contrast-suspect", line,
                    f"color and background-color set to the same value ({c}).",
                    _snippet_of(lines, line),
                ))

    return findings
