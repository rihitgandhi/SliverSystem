"""
web_audit.py
============

Server-side helpers that give the accessibility-score endpoint *real evidence*
to ground the LLM with — instead of asking the model to invent findings about
a URL it cannot see.

Two responsibilities:

1. ``fetch_page(url)`` — SSRF-safe HTTP fetch with a hard timeout, response-
   size cap, and private-network blocking. Returns a metadata dict containing
   the final URL, status code, response time, byte size, server header, and
   the decoded HTML body (truncated for safety).

2. ``audit_html(html, base_url)`` — a deterministic DOM walk over the fetched
   markup that extracts objective accessibility signals (image alt-text
   coverage, heading hierarchy, landmarks, form labels, ARIA usage, link
   purpose, language declaration, etc.). The returned ``evidence`` dict is
   what we feed into the LLM prompt so its commentary cites real numbers and
   real selectors rather than hallucinated ones.

This module deliberately uses only ``requests`` + ``BeautifulSoup`` so it can
run inside the existing Flask backend with no new system dependencies.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup, Comment

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
FETCH_TIMEOUT_SECONDS = 12
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB cap on downloaded HTML
USER_AGENT = (
    "AccessAI-Auditor/1.0 (+https://github.com/rihitgandhi/AccessAI) "
    "Mozilla/5.0 (compatible; accessibility crawler)"
)
GENERIC_LINK_TEXTS = {
    "click here", "here", "read more", "more", "learn more",
    "this", "this link", "link", "details", "info", "more info",
    "continue", "go", "see more",
}

# WAI / W3C reference table — each WCAG 2.1 success criterion mapped to its
# canonical Understanding / How-to-Meet URL plus a curated "deep-dive" link.
# This is what makes the report "sourced" rather than invented.
WCAG_REFERENCES: Dict[str, Dict[str, str]] = {
    "1.1.1": {
        "title": "Non-text Content (Alt text)",
        "level": "A",
        "principle": "Perceivable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
        "deep_dive": "https://webaim.org/techniques/alttext/",
    },
    "1.3.1": {
        "title": "Info and Relationships",
        "level": "A",
        "principle": "Perceivable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships.html",
        "deep_dive": "https://www.w3.org/WAI/tutorials/page-structure/",
    },
    "1.3.2": {
        "title": "Meaningful Sequence",
        "level": "A",
        "principle": "Perceivable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/meaningful-sequence.html",
        "deep_dive": "https://www.w3.org/WAI/tutorials/page-structure/content/",
    },
    "1.4.3": {
        "title": "Contrast (Minimum) — 4.5:1",
        "level": "AA",
        "principle": "Perceivable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html",
        "deep_dive": "https://webaim.org/articles/contrast/",
    },
    "1.4.4": {
        "title": "Resize Text (200%)",
        "level": "AA",
        "principle": "Perceivable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/resize-text.html",
        "deep_dive": "https://www.tpgi.com/text-resizing-and-content-reflow/",
    },
    "1.4.10": {
        "title": "Reflow (responsive viewport)",
        "level": "AA",
        "principle": "Perceivable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/reflow.html",
        "deep_dive": "https://www.w3.org/WAI/perspective-videos/zoom/",
    },
    "2.1.1": {
        "title": "Keyboard",
        "level": "A",
        "principle": "Operable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/keyboard.html",
        "deep_dive": "https://webaim.org/techniques/keyboard/",
    },
    "2.4.1": {
        "title": "Bypass Blocks (Skip link / landmarks)",
        "level": "A",
        "principle": "Operable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/bypass-blocks.html",
        "deep_dive": "https://webaim.org/techniques/skipnav/",
    },
    "2.4.2": {
        "title": "Page Titled",
        "level": "A",
        "principle": "Operable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/page-titled.html",
        "deep_dive": "https://www.w3.org/WAI/tips/writing/#provide-informative-unique-page-titles",
    },
    "2.4.4": {
        "title": "Link Purpose (In Context)",
        "level": "A",
        "principle": "Operable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/link-purpose-in-context.html",
        "deep_dive": "https://webaim.org/techniques/hypertext/link_text",
    },
    "2.4.6": {
        "title": "Headings and Labels",
        "level": "AA",
        "principle": "Operable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/headings-and-labels.html",
        "deep_dive": "https://www.w3.org/WAI/tutorials/page-structure/headings/",
    },
    "2.4.7": {
        "title": "Focus Visible",
        "level": "AA",
        "principle": "Operable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/focus-visible.html",
        "deep_dive": "https://www.sarasoueidan.com/blog/focus-indicators/",
    },
    "3.1.1": {
        "title": "Language of Page (lang attribute)",
        "level": "A",
        "principle": "Understandable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/language-of-page.html",
        "deep_dive": "https://www.w3.org/International/questions/qa-html-language-declarations",
    },
    "3.3.2": {
        "title": "Labels or Instructions (Form labels)",
        "level": "A",
        "principle": "Understandable",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/labels-or-instructions.html",
        "deep_dive": "https://webaim.org/techniques/forms/controls",
    },
    "4.1.2": {
        "title": "Name, Role, Value (ARIA, controls)",
        "level": "A",
        "principle": "Robust",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/name-role-value.html",
        "deep_dive": "https://www.w3.org/WAI/ARIA/apg/practices/",
    },
    "4.1.3": {
        "title": "Status Messages",
        "level": "AA",
        "principle": "Robust",
        "w3c": "https://www.w3.org/WAI/WCAG21/Understanding/status-messages.html",
        "deep_dive": "https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/alert_role",
    },
}


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------
def _is_private_host(host: str) -> bool:
    """Return True if host resolves to a private/loopback/link-local IP.

    Used to refuse SSRF-style URLs (10.x, 192.168.x, 127.x, ::1, etc.)
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return True  # fail-closed: if we cannot resolve, refuse
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def fetch_page(url: str) -> Dict[str, Any]:
    """Fetch ``url`` safely and return a metadata dict.

    Returned dict always contains ``ok`` and ``url``. On success it also
    contains ``html`` plus ``status``, ``final_url``, ``elapsed_ms``,
    ``content_type``, ``content_length``, ``server``, ``security_headers``.
    On failure it contains ``error`` and ``error_kind``.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"ok": False, "url": url, "error_kind": "scheme",
                "error": "URL must start with http:// or https://"}
    if not parsed.hostname:
        return {"ok": False, "url": url, "error_kind": "host",
                "error": "URL is missing a hostname"}
    if _is_private_host(parsed.hostname):
        return {"ok": False, "url": url, "error_kind": "private_host",
                "error": f"Refusing to fetch a private/loopback host ({parsed.hostname})"}

    started = time.monotonic()
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=FETCH_TIMEOUT_SECONDS,
            allow_redirects=True,
            stream=True,
        )
    except requests.exceptions.SSLError as exc:
        return {"ok": False, "url": url, "error_kind": "ssl",
                "error": f"TLS error: {exc}"}
    except requests.exceptions.Timeout:
        return {"ok": False, "url": url, "error_kind": "timeout",
                "error": f"Timed out after {FETCH_TIMEOUT_SECONDS}s"}
    except requests.exceptions.ConnectionError as exc:
        return {"ok": False, "url": url, "error_kind": "connection",
                "error": f"Connection failed: {exc}"}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "url": url, "error_kind": "request",
                "error": f"Request failed: {exc}"}

    # Stream-read with size cap
    chunks: List[bytes] = []
    total = 0
    try:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                break
            chunks.append(chunk)
    finally:
        resp.close()
    body_bytes = b"".join(chunks)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    # Decode body using the declared charset, falling back to utf-8 with replace.
    encoding = resp.encoding or "utf-8"
    try:
        html = body_bytes.decode(encoding, errors="replace")
    except (LookupError, TypeError):
        html = body_bytes.decode("utf-8", errors="replace")

    security_headers = {
        h: resp.headers.get(h) for h in (
            "Content-Security-Policy", "Strict-Transport-Security",
            "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy",
            "Permissions-Policy",
        )
        if resp.headers.get(h)
    }

    return {
        "ok": True,
        "url": url,
        "final_url": resp.url,
        "status": resp.status_code,
        "elapsed_ms": elapsed_ms,
        "content_type": resp.headers.get("Content-Type", ""),
        "content_length": total,
        "server": resp.headers.get("Server", ""),
        "security_headers": security_headers,
        "html": html,
        "truncated": total >= MAX_RESPONSE_BYTES,
    }


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def _selector_for(tag) -> str:
    """Build a short, human-readable CSS-ish selector for a BeautifulSoup tag."""
    parts = [tag.name]
    if tag.get("id"):
        parts.append(f"#{tag.get('id')}")
    elif tag.get("class"):
        parts.append("." + ".".join(tag.get("class")[:2]))
    return "".join(parts)


def _short(text: str, n: int = 80) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text if len(text) <= n else text[: n - 1] + "…"


def audit_html(html: str, base_url: str) -> Dict[str, Any]:
    """Walk the fetched HTML and return an objective evidence dict.

    The returned shape is intentionally JSON-serialisable and stable so the
    frontend can render it directly and the LLM can cite specific numbers.
    """
    soup = BeautifulSoup(html or "", "html.parser")

    # Strip script/style/comments so text-content checks aren't polluted
    for s in soup(["script", "style", "noscript"]):
        s.extract()
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()

    html_tag = soup.find("html")
    head = soup.find("head")
    body = soup.find("body") or soup

    # ---- Meta -----------------------------------------------------------
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    lang = html_tag.get("lang", "").strip() if html_tag else ""
    viewport_meta = ""
    if head:
        vp = head.find("meta", attrs={"name": "viewport"})
        if vp:
            viewport_meta = vp.get("content", "")
    charset = ""
    if head:
        meta_charset = head.find("meta", attrs={"charset": True})
        if meta_charset:
            charset = meta_charset.get("charset", "")
        else:
            ct = head.find("meta", attrs={"http-equiv": re.compile("content-type", re.I)})
            if ct and ct.get("content"):
                m = re.search(r"charset=([\w-]+)", ct["content"], re.I)
                if m:
                    charset = m.group(1)

    # ---- Images ---------------------------------------------------------
    images = body.find_all("img")
    imgs_total = len(images)
    imgs_missing_alt: List[Dict[str, str]] = []
    imgs_empty_alt = 0  # decorative — alt="" present, this is OK
    imgs_redundant_alt = 0  # alt that just says "image of …" / filename
    alt_samples: List[str] = []
    for img in images:
        alt = img.get("alt")
        src = img.get("src", "") or img.get("data-src", "")
        if alt is None:
            imgs_missing_alt.append({
                "selector": _selector_for(img),
                "src": _short(src, 100),
            })
        elif alt.strip() == "":
            imgs_empty_alt += 1
        else:
            alt_low = alt.lower().strip()
            if (alt_low.startswith(("image of", "picture of", "photo of", "graphic of"))
                    or alt_low.endswith((".jpg", ".png", ".jpeg", ".gif", ".webp", ".svg"))):
                imgs_redundant_alt += 1
            if len(alt_samples) < 5:
                alt_samples.append(_short(alt, 60))

    # ---- Headings -------------------------------------------------------
    headings: List[Tuple[int, str]] = []
    for h in body.find_all(re.compile(r"^h[1-6]$")):
        level = int(h.name[1])
        headings.append((level, _short(h.get_text(" ", strip=True), 80)))
    h1_count = sum(1 for lvl, _ in headings if lvl == 1)
    skipped_levels: List[str] = []
    if headings:
        prev = 0
        for lvl, text in headings:
            if prev and lvl > prev + 1:
                skipped_levels.append(f"jumped from h{prev} → h{lvl} at \"{text}\"")
            prev = lvl

    # ---- Landmarks ------------------------------------------------------
    landmarks = {
        "main": len(body.find_all("main")),
        "nav": len(body.find_all("nav")),
        "header": len(body.find_all("header")),
        "footer": len(body.find_all("footer")),
        "aside": len(body.find_all("aside")),
        "section": len(body.find_all("section")),
        "article": len(body.find_all("article")),
        "role_main": len(body.find_all(attrs={"role": "main"})),
        "role_navigation": len(body.find_all(attrs={"role": "navigation"})),
        "role_contentinfo": len(body.find_all(attrs={"role": "contentinfo"})),
    }
    # Skip link — first anchor whose href starts with '#' (excluding '#')
    skip_link_present = False
    for a in body.find_all("a", href=True):
        if a["href"].startswith("#") and a["href"] != "#":
            text = a.get_text(" ", strip=True).lower()
            if "skip" in text and ("content" in text or "main" in text or "navigation" in text):
                skip_link_present = True
                break

    # ---- Links ----------------------------------------------------------
    anchors = body.find_all("a")
    links_total = len(anchors)
    links_no_text = 0
    links_generic_text: List[str] = []
    links_target_blank_no_rel = 0
    for a in anchors:
        text = a.get_text(" ", strip=True)
        aria_label = (a.get("aria-label") or "").strip()
        title_attr = (a.get("title") or "").strip()
        effective = text or aria_label or title_attr
        if not effective and not a.find("img", alt=True):
            links_no_text += 1
        elif text and text.lower().strip(".:! ") in GENERIC_LINK_TEXTS:
            if len(links_generic_text) < 5:
                links_generic_text.append(_short(text, 30))
        if a.get("target") == "_blank":
            rel = (a.get("rel") or [])
            if isinstance(rel, list):
                rel_str = " ".join(rel).lower()
            else:
                rel_str = str(rel).lower()
            if "noopener" not in rel_str:
                links_target_blank_no_rel += 1

    # ---- Buttons --------------------------------------------------------
    buttons = body.find_all("button")
    buttons_no_accessible_name = 0
    for b in buttons:
        if (b.get_text(" ", strip=True) or b.get("aria-label") or b.get("title")):
            continue
        if b.find("img", alt=True) or b.find(attrs={"aria-label": True}):
            continue
        buttons_no_accessible_name += 1

    # ---- Forms ----------------------------------------------------------
    forms = body.find_all("form")
    inputs = body.find_all(["input", "textarea", "select"])
    inputs_total = 0
    inputs_unlabeled: List[Dict[str, str]] = []
    label_for_ids = {lbl.get("for") for lbl in body.find_all("label") if lbl.get("for")}
    for el in inputs:
        if el.name == "input" and el.get("type", "text").lower() in ("hidden", "submit", "button", "reset", "image"):
            continue
        inputs_total += 1
        el_id = el.get("id")
        has_label = bool(el_id and el_id in label_for_ids)
        wrapped_in_label = bool(el.find_parent("label"))
        has_aria_label = bool(el.get("aria-label") or el.get("aria-labelledby"))
        has_title = bool(el.get("title"))
        if not (has_label or wrapped_in_label or has_aria_label or has_title):
            inputs_unlabeled.append({
                "selector": _selector_for(el),
                "type": el.get("type", el.name),
                "placeholder": _short(el.get("placeholder", ""), 40),
            })

    # ---- ARIA / interactive -------------------------------------------
    aria_attr_count = 0
    for tag in body.find_all(True):
        for attr in tag.attrs:
            if attr.startswith("aria-") or attr == "role":
                aria_attr_count += 1
    inline_onclick_non_interactive = 0
    for tag in body.find_all(attrs={"onclick": True}):
        if tag.name not in ("button", "a", "input"):
            inline_onclick_non_interactive += 1

    # ---- Tables ---------------------------------------------------------
    tables = body.find_all("table")
    tables_no_th = sum(1 for t in tables if not t.find("th"))
    tables_no_caption = sum(1 for t in tables if not t.find("caption"))

    # ---- iframes --------------------------------------------------------
    iframes = body.find_all("iframe")
    iframes_no_title = sum(1 for f in iframes if not (f.get("title") or "").strip())

    # ---- Inline style colours (best-effort sample) ----------------------
    style_color_pairs: List[Dict[str, str]] = []
    for tag in body.find_all(style=True)[:100]:
        style = tag.get("style", "")
        fg = re.search(r"(?<!background-)color\s*:\s*([^;]+)", style, re.I)
        bg = re.search(r"background(?:-color)?\s*:\s*([^;]+)", style, re.I)
        if fg and bg:
            style_color_pairs.append({
                "selector": _selector_for(tag),
                "color": fg.group(1).strip(),
                "background": bg.group(1).strip(),
                "sample_text": _short(tag.get_text(" ", strip=True), 40),
            })
        if len(style_color_pairs) >= 5:
            break

    # ---- Build evidence ------------------------------------------------
    evidence = {
        "page": {
            "title": title,
            "title_length": len(title),
            "lang": lang,
            "viewport": viewport_meta,
            "charset": charset,
            "doctype_present": str(soup).lstrip()[:9].lower().startswith("<!doctype"),
        },
        "images": {
            "total": imgs_total,
            "missing_alt": len(imgs_missing_alt),
            "missing_alt_samples": imgs_missing_alt[:5],
            "decorative_alt_empty": imgs_empty_alt,
            "redundant_alt": imgs_redundant_alt,
            "alt_samples": alt_samples,
            "coverage_percent": (
                round(100 * (imgs_total - len(imgs_missing_alt)) / imgs_total, 1)
                if imgs_total else 100.0
            ),
        },
        "headings": {
            "total": len(headings),
            "h1_count": h1_count,
            "outline": [{"level": lvl, "text": txt} for lvl, txt in headings[:15]],
            "skipped_levels": skipped_levels,
        },
        "landmarks": landmarks,
        "skip_link_present": skip_link_present,
        "links": {
            "total": links_total,
            "no_text": links_no_text,
            "generic_text_samples": links_generic_text,
            "target_blank_missing_noopener": links_target_blank_no_rel,
        },
        "buttons": {
            "total": len(buttons),
            "no_accessible_name": buttons_no_accessible_name,
        },
        "forms": {
            "form_count": len(forms),
            "inputs_total": inputs_total,
            "inputs_unlabeled": len(inputs_unlabeled),
            "inputs_unlabeled_samples": inputs_unlabeled[:5],
        },
        "aria": {
            "attribute_count": aria_attr_count,
            "inline_onclick_on_non_interactive": inline_onclick_non_interactive,
        },
        "tables": {
            "total": len(tables),
            "missing_th": tables_no_th,
            "missing_caption": tables_no_caption,
        },
        "iframes": {
            "total": len(iframes),
            "missing_title": iframes_no_title,
        },
        "color_samples_inline": style_color_pairs,
    }

    # Lightweight pre-flagging — these are the criteria the LLM should at
    # minimum address (since we have hard evidence one way or the other).
    flagged: List[Dict[str, Any]] = []
    if imgs_total and len(imgs_missing_alt) > 0:
        flagged.append({
            "wcag": "1.1.1",
            "summary": f"{len(imgs_missing_alt)} of {imgs_total} images have no alt attribute",
        })
    if not lang:
        flagged.append({"wcag": "3.1.1", "summary": "<html> is missing a lang attribute"})
    if not title:
        flagged.append({"wcag": "2.4.2", "summary": "<title> is empty or missing"})
    if not viewport_meta:
        flagged.append({"wcag": "1.4.10", "summary": "No <meta name='viewport'> declared"})
    if h1_count == 0 and len(headings) > 0:
        flagged.append({"wcag": "2.4.6", "summary": "No <h1> heading on the page"})
    if h1_count > 1:
        flagged.append({"wcag": "1.3.1", "summary": f"Multiple <h1> elements found ({h1_count})"})
    if skipped_levels:
        flagged.append({"wcag": "1.3.1", "summary": f"Heading hierarchy skips levels: {skipped_levels[0]}"})
    if landmarks["main"] == 0 and landmarks["role_main"] == 0:
        flagged.append({"wcag": "1.3.1", "summary": "No <main> landmark"})
    if not skip_link_present and (landmarks["nav"] > 0 or landmarks["role_navigation"] > 0):
        flagged.append({"wcag": "2.4.1", "summary": "Navigation present but no skip-to-content link"})
    if links_no_text > 0:
        flagged.append({"wcag": "2.4.4", "summary": f"{links_no_text} link(s) with no accessible name"})
    if links_generic_text:
        flagged.append({
            "wcag": "2.4.4",
            "summary": f"Generic link text found: {', '.join(links_generic_text)}",
        })
    if buttons_no_accessible_name > 0:
        flagged.append({
            "wcag": "4.1.2",
            "summary": f"{buttons_no_accessible_name} button(s) without accessible name",
        })
    if len(inputs_unlabeled) > 0:
        flagged.append({
            "wcag": "3.3.2",
            "summary": f"{len(inputs_unlabeled)} form input(s) with no associated label",
        })
    if iframes_no_title > 0:
        flagged.append({
            "wcag": "4.1.2",
            "summary": f"{iframes_no_title} iframe(s) without a title attribute",
        })
    if inline_onclick_non_interactive > 0:
        flagged.append({
            "wcag": "2.1.1",
            "summary": f"{inline_onclick_non_interactive} non-interactive element(s) with inline onclick — likely keyboard-inaccessible",
        })

    # Attach canonical sources for every flagged criterion.
    referenced_criteria = sorted({f["wcag"] for f in flagged})
    sources: List[Dict[str, str]] = []
    for crit in referenced_criteria:
        ref = WCAG_REFERENCES.get(crit)
        if not ref:
            continue
        sources.append({
            "wcag_criterion": crit,
            "title": ref["title"],
            "level": ref["level"],
            "principle": ref["principle"],
            "w3c_understanding_url": ref["w3c"],
            "deep_dive_url": ref["deep_dive"],
        })

    evidence["flagged_findings"] = flagged
    evidence["sources"] = sources
    return evidence


def evidence_summary_for_prompt(evidence: Dict[str, Any]) -> str:
    """Render a compact human-readable summary of the evidence dict so the
    LLM can ingest it cheaply and ground every claim in real numbers.
    """
    e = evidence
    lines: List[str] = []
    lines.append("PAGE METADATA")
    lines.append(
        f"  title='{e['page']['title']}' (len={e['page']['title_length']}); "
        f"lang='{e['page']['lang']}'; viewport='{e['page']['viewport']}'; "
        f"charset='{e['page']['charset']}'; doctype={e['page']['doctype_present']}"
    )
    lines.append("IMAGES")
    img = e["images"]
    lines.append(
        f"  total={img['total']}; missing_alt={img['missing_alt']}; "
        f"decorative_empty_alt={img['decorative_alt_empty']}; "
        f"redundant_alt={img['redundant_alt']}; coverage={img['coverage_percent']}%"
    )
    if img["missing_alt_samples"]:
        for s in img["missing_alt_samples"]:
            lines.append(f"    NO-ALT: {s['selector']}  src={s['src']}")
    lines.append("HEADINGS")
    h = e["headings"]
    lines.append(f"  total={h['total']}; h1_count={h['h1_count']}; skipped_levels={h['skipped_levels'] or 'none'}")
    if h["outline"]:
        outline_str = " > ".join(f"h{o['level']}:{o['text'][:24]}" for o in h["outline"][:6])
        lines.append(f"  outline: {outline_str}")
    lines.append("LANDMARKS")
    l = e["landmarks"]
    lines.append(
        f"  main={l['main']} nav={l['nav']} header={l['header']} footer={l['footer']} "
        f"aside={l['aside']} role_main={l['role_main']}"
    )
    lines.append(f"  skip_link_present={e['skip_link_present']}")
    lines.append("LINKS")
    lk = e["links"]
    lines.append(
        f"  total={lk['total']}; no_text={lk['no_text']}; "
        f"generic_text={lk['generic_text_samples'] or 'none'}; "
        f"target_blank_missing_noopener={lk['target_blank_missing_noopener']}"
    )
    lines.append("BUTTONS")
    lines.append(f"  total={e['buttons']['total']}; no_accessible_name={e['buttons']['no_accessible_name']}")
    lines.append("FORMS")
    f = e["forms"]
    lines.append(
        f"  form_count={f['form_count']}; inputs_total={f['inputs_total']}; "
        f"inputs_unlabeled={f['inputs_unlabeled']}"
    )
    if f["inputs_unlabeled_samples"]:
        for s in f["inputs_unlabeled_samples"]:
            lines.append(
                f"    UNLABELED: {s['selector']} type={s['type']} placeholder='{s['placeholder']}'"
            )
    lines.append("ARIA")
    lines.append(
        f"  aria_attribute_count={e['aria']['attribute_count']}; "
        f"inline_onclick_non_interactive={e['aria']['inline_onclick_on_non_interactive']}"
    )
    lines.append("TABLES")
    t = e["tables"]
    lines.append(f"  total={t['total']}; missing_th={t['missing_th']}; missing_caption={t['missing_caption']}")
    lines.append("IFRAMES")
    fr = e["iframes"]
    lines.append(f"  total={fr['total']}; missing_title={fr['missing_title']}")
    if e.get("color_samples_inline"):
        lines.append("INLINE COLOR PAIRS (sampled)")
        for s in e["color_samples_inline"]:
            lines.append(
                f"  {s['selector']}: color={s['color']} on background={s['background']}  text='{s['sample_text']}'"
            )
    if e.get("flagged_findings"):
        lines.append("PRE-FLAGGED FINDINGS (from deterministic audit)")
        for f in e["flagged_findings"]:
            lines.append(f"  WCAG {f['wcag']}: {f['summary']}")
    return "\n".join(lines)
