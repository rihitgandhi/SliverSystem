"""
image_audit.py
==============

Deterministic image inspection used to ground the alt-text generator.

The Alt Text endpoint takes a base64-encoded image. Before asking the LLM
"please describe this", we extract objective facts about the file so the
generated alt-text can be evaluated against:

  - actual dimensions, aspect ratio, format, color mode, file size
  - whether the file is plausibly **decorative** (extreme aspect ratio,
    very small, single dominant colour, transparent, etc.)
  - dominant colours (top 3) so the LLM doesn't hallucinate the palette
  - EXIF camera/orientation when present (so the description can mention
    "photograph" vs. "illustration" reliably)
  - a coverage check against the WCAG decision tree for non-text content

Returned data is a JSON-serialisable ``evidence`` dict mirroring the shape
used by ``web_audit`` so the frontend can render a Differentiator + Evidence
+ Sources panel identically across all AI tools.
"""

from __future__ import annotations

import base64
import io
from collections import Counter
from typing import Any, Dict, List, Tuple

from PIL import Image, ExifTags, ImageStat


# Canonical references for image-accessibility guidance — every report
# carries these so the user can verify what the LLM said.
ALT_TEXT_REFERENCES: List[Dict[str, str]] = [
    {
        "wcag_criterion": "1.1.1",
        "title": "Non-text Content (Alt text decision tree)",
        "level": "A",
        "principle": "Perceivable",
        "w3c_understanding_url": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
        "deep_dive_url": "https://www.w3.org/WAI/tutorials/images/decision-tree/",
    },
    {
        "wcag_criterion": "1.4.5",
        "title": "Images of Text",
        "level": "AA",
        "principle": "Perceivable",
        "w3c_understanding_url": "https://www.w3.org/WAI/WCAG21/Understanding/images-of-text.html",
        "deep_dive_url": "https://webaim.org/techniques/alttext/#text",
    },
    {
        "wcag_criterion": "Pattern: Decorative",
        "title": "Decorative images (alt=\"\")",
        "level": "—",
        "principle": "Perceivable",
        "w3c_understanding_url": "https://www.w3.org/WAI/tutorials/images/decorative/",
        "deep_dive_url": "https://webaim.org/techniques/alttext/#decorative",
    },
    {
        "wcag_criterion": "Pattern: Functional",
        "title": "Functional images (icons, controls)",
        "level": "—",
        "principle": "Perceivable",
        "w3c_understanding_url": "https://www.w3.org/WAI/tutorials/images/functional/",
        "deep_dive_url": "https://webaim.org/techniques/alttext/#functional",
    },
    {
        "wcag_criterion": "Pattern: Informative",
        "title": "Informative images (writing meaningful alt text)",
        "level": "—",
        "principle": "Perceivable",
        "w3c_understanding_url": "https://www.w3.org/WAI/tutorials/images/informative/",
        "deep_dive_url": "https://webaim.org/techniques/alttext/#informative",
    },
    {
        "wcag_criterion": "Pattern: Complex",
        "title": "Complex images (charts, diagrams) + long description",
        "level": "—",
        "principle": "Perceivable",
        "w3c_understanding_url": "https://www.w3.org/WAI/tutorials/images/complex/",
        "deep_dive_url": "https://webaim.org/techniques/alttext/#complex",
    },
]


def _strip_data_url_prefix(b64: str) -> str:
    """Remove a leading 'data:image/...;base64,' header if present."""
    if "," in b64 and b64.lstrip().startswith("data:"):
        return b64.split(",", 1)[1]
    return b64


def _hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb[:3])


def _classify_aspect(ratio: float) -> str:
    if ratio >= 4.0:
        return "ultra-wide banner"
    if ratio >= 2.0:
        return "wide banner / hero"
    if ratio >= 1.3:
        return "landscape"
    if ratio >= 0.85:
        return "near-square"
    if ratio >= 0.5:
        return "portrait"
    return "tall vertical"


def audit_image(image_b64: str) -> Dict[str, Any]:
    """Inspect a base64 image and return an evidence dict.

    Returns a dict with ``ok`` False on bad input so the caller can show a
    helpful error rather than a stack trace.
    """
    try:
        raw_b64 = _strip_data_url_prefix(image_b64 or "")
        image_bytes = base64.b64decode(raw_b64, validate=True)
    except Exception as exc:
        return {"ok": False, "error": f"Invalid base64 image data: {exc}"}

    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im.load()
            width, height = im.size
            mode = im.mode
            fmt = (im.format or "").upper()
            has_alpha = im.mode in ("LA", "RGBA", "PA") or (
                im.mode == "P" and "transparency" in im.info
            )
            ratio = (width / height) if height else 0.0

            # EXIF (only meaningful for camera images)
            exif: Dict[str, str] = {}
            try:
                raw_exif = im._getexif() if hasattr(im, "_getexif") else None
            except Exception:
                raw_exif = None
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    if name in ("Make", "Model", "DateTimeOriginal",
                                "Orientation", "Software", "ImageDescription",
                                "Artist", "Copyright"):
                        try:
                            exif[name] = str(value).strip("\x00 ").strip()
                        except Exception:
                            pass

            # Brightness via grayscale ImageStat
            try:
                gray = im.convert("L")
                stat = ImageStat.Stat(gray)
                brightness = round(stat.mean[0], 1)
                contrast_stddev = round(stat.stddev[0], 1)
            except Exception:
                brightness = None
                contrast_stddev = None

            # Top dominant colours (down-sample first to keep this cheap)
            dominant: List[Dict[str, Any]] = []
            try:
                sample = im.convert("RGB").resize((64, 64))
                pixels = list(sample.getdata())
                # Bucket by 32-step quantisation so visually similar colours merge
                quant = [(r >> 5 << 5, g >> 5 << 5, b >> 5 << 5) for (r, g, b) in pixels]
                counts = Counter(quant).most_common(3)
                total = sum(c for _, c in counts) or 1
                for color, c in counts:
                    dominant.append({
                        "hex": _hex(color),
                        "rgb": list(color),
                        "percentage": round(100 * c / total, 1),
                    })
            except Exception:
                pass

    except Exception as exc:
        return {"ok": False, "error": f"Could not decode image: {exc}"}

    # Decorative / functional heuristics (informational only — the LLM
    # makes the final call, but we surface the signals that influenced it)
    pixel_count = width * height
    is_tiny = pixel_count < (24 * 24)
    is_extremely_wide = ratio >= 6 or ratio <= (1 / 6)
    near_uniform = (dominant[0]["percentage"] >= 90) if dominant else False
    likely_decorative = bool(is_tiny or near_uniform)
    likely_chart = (ratio >= 0.7 and ratio <= 1.6 and contrast_stddev is not None
                    and contrast_stddev > 70 and (fmt in ("PNG", "GIF", "BMP", "WEBP")))
    likely_photo = bool(exif and (exif.get("Make") or exif.get("Model"))) or (
        fmt in ("JPEG", "JPG") and pixel_count > (300 * 300)
    )
    likely_text_heavy = bool(fmt in ("PNG", "GIF", "WEBP") and contrast_stddev is not None
                             and contrast_stddev > 80 and ratio > 1.4)

    classifications: List[str] = []
    if likely_decorative:
        classifications.append("decorative")
    if likely_chart:
        classifications.append("chart-or-diagram")
    if likely_photo:
        classifications.append("photograph")
    if likely_text_heavy:
        classifications.append("possible-image-of-text (WCAG 1.4.5)")
    if not classifications:
        classifications.append("informative (general)")

    file_size_kb = round(len(image_bytes) / 1024, 1)
    megapixels = round(pixel_count / 1_000_000, 2)

    evidence = {
        "ok": True,
        "format": fmt or "UNKNOWN",
        "mode": mode,
        "width": width,
        "height": height,
        "aspect_ratio": round(ratio, 3),
        "aspect_label": _classify_aspect(ratio),
        "pixel_count": pixel_count,
        "megapixels": megapixels,
        "file_size_bytes": len(image_bytes),
        "file_size_kb": file_size_kb,
        "has_alpha": has_alpha,
        "brightness_mean_0_255": brightness,
        "contrast_stddev": contrast_stddev,
        "dominant_colors": dominant,
        "exif": exif,
        "classifications": classifications,
        "heuristics": {
            "tiny": is_tiny,
            "near_uniform_color": near_uniform,
            "extreme_aspect": is_extremely_wide,
            "likely_decorative": likely_decorative,
            "likely_chart": likely_chart,
            "likely_photograph": likely_photo,
            "likely_image_of_text": likely_text_heavy,
        },
    }
    return evidence


def evidence_summary_for_prompt(evidence: Dict[str, Any]) -> str:
    """Render the image-evidence dict into a compact LLM-friendly summary."""
    e = evidence
    if not e.get("ok"):
        return f"IMAGE ANALYSIS FAILED: {e.get('error', 'unknown error')}"
    lines = []
    lines.append("IMAGE FILE ANALYSIS")
    lines.append(f"  format={e['format']} mode={e['mode']} size={e['width']}x{e['height']}px "
                 f"({e['megapixels']} MP); ratio={e['aspect_ratio']} ({e['aspect_label']}); "
                 f"file={e['file_size_kb']} KB; alpha={e['has_alpha']}")
    if e.get("brightness_mean_0_255") is not None:
        lines.append(f"  brightness={e['brightness_mean_0_255']}/255  contrast_stddev={e['contrast_stddev']}")
    if e.get("dominant_colors"):
        palette = ", ".join(
            f"{c.get('hex', '?')} ({c['percentage']}%)" if 'percentage' in c
            else f"{c.get('hex', '?')}"
            for c in e["dominant_colors"]
        )
        lines.append(f"  dominant_colors: {palette}")
    if e.get("exif"):
        for k, v in e["exif"].items():
            lines.append(f"  exif.{k}={v}")
    h = e.get("heuristics", {})
    on_flags = [k for k, v in h.items() if v]
    if on_flags:
        lines.append(f"  heuristic_flags: {', '.join(on_flags)}")
    lines.append(f"  inferred_classifications: {', '.join(e.get('classifications') or ['general'])}")
    return "\n".join(lines)
