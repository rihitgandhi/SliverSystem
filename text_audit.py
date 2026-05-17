"""
text_audit.py
=============

Deterministic readability analysis for the Content Simplifier.

Computes objective text statistics (sentence/word counts, syllable estimates,
Flesch Reading Ease, Flesch-Kincaid Grade Level, Automated Readability Index,
sentence-length distribution, jargon hits, passive-voice count, average word
length) so the LLM is grounded in real numbers when it claims "I lowered
this from grade 12 to grade 6". The frontend then shows a before/after
diff of the same metrics.

References (cited in the report):

  - Flesch Reading Ease — https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests
  - Plain-language style — https://www.plainlanguage.gov/guidelines/
  - WCAG 3.1.5 Reading Level — https://www.w3.org/WAI/WCAG21/Understanding/reading-level.html
  - WCAG 3.1.3 Unusual Words — https://www.w3.org/WAI/WCAG21/Understanding/unusual-words.html
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List


READABILITY_REFERENCES: List[Dict[str, str]] = [
    {
        "wcag_criterion": "3.1.5",
        "title": "Reading Level (lower secondary)",
        "level": "AAA",
        "principle": "Understandable",
        "w3c_understanding_url": "https://www.w3.org/WAI/WCAG21/Understanding/reading-level.html",
        "deep_dive_url": "https://www.plainlanguage.gov/guidelines/",
    },
    {
        "wcag_criterion": "3.1.3",
        "title": "Unusual Words / Jargon",
        "level": "AAA",
        "principle": "Understandable",
        "w3c_understanding_url": "https://www.w3.org/WAI/WCAG21/Understanding/unusual-words.html",
        "deep_dive_url": "https://www.nngroup.com/articles/plain-language-experts/",
    },
    {
        "wcag_criterion": "3.1.4",
        "title": "Abbreviations (expand on first use)",
        "level": "AAA",
        "principle": "Understandable",
        "w3c_understanding_url": "https://www.w3.org/WAI/WCAG21/Understanding/abbreviations.html",
        "deep_dive_url": "https://www.w3.org/WAI/perspective-videos/notifications/",
    },
    {
        "wcag_criterion": "Plain-language",
        "title": "U.S. Federal Plain Language Guidelines",
        "level": "—",
        "principle": "Understandable",
        "w3c_understanding_url": "https://www.plainlanguage.gov/guidelines/",
        "deep_dive_url": "https://readabilityformulas.com/the-flesch-reading-ease-readability-formula/",
    },
]

# Common jargon / "fifty-cent" words that the simplifier should flag.
JARGON_WORDS = {
    "utilize", "utilization", "leverage", "facilitate", "endeavor",
    "ascertain", "commence", "commencement", "demonstrate", "endeavour",
    "implementation", "subsequent", "subsequently", "prior to", "in order to",
    "due to the fact that", "at this point in time", "in the event that",
    "notwithstanding", "heretofore", "henceforth", "aforementioned",
    "operational", "stakeholders", "synergize", "synergy", "paradigm",
    "robust", "scalable", "actionable", "deliverable", "deliverables",
    "incentivize", "operationalize", "monetize", "ideate", "drilldown",
    "optimization", "instantiate", "instantiation", "deprecation",
    "asynchronous", "preliminary", "ramifications", "consequently",
    "moreover", "furthermore", "nevertheless", "irregardless",
}
PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|being|am)\s+(?:[a-z]+ly\s+)?(?:[a-z]+ed|made|done|given|"
    r"taken|sent|known|seen|written|paid|put|set|cut|met|kept|held|brought|told|left)\b",
    re.I,
)
ABBREV_RE = re.compile(r"\b([A-Z]{2,})\b")  # ALLCAPS sequences (potential acronyms)
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?")


# ---------------------------------------------------------------------------
def _count_syllables(word: str) -> int:
    """Cheap syllable estimator (good enough for FK grade)."""
    word = word.lower()
    if not word:
        return 0
    # Remove non-letters
    word = re.sub(r"[^a-z]", "", word)
    if len(word) <= 3:
        return 1
    # Drop trailing silent 'e'
    if word.endswith("e"):
        word = word[:-1]
    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel
    return max(1, count)


def _grade_label(grade: float) -> str:
    if grade < 4:
        return "Early elementary (grade 1–3)"
    if grade < 7:
        return "Late elementary (grade 4–6)"
    if grade < 10:
        return "Middle school (grade 7–9)"
    if grade < 13:
        return "High school (grade 10–12)"
    if grade < 16:
        return "College (grade 13–15)"
    return "Graduate-level (grade 16+)"


def _flesch_band(score: float) -> str:
    if score >= 90:
        return "Very easy — 5th grader"
    if score >= 80:
        return "Easy — 6th grader"
    if score >= 70:
        return "Fairly easy — 7th grader"
    if score >= 60:
        return "Standard — 8th–9th grader"
    if score >= 50:
        return "Fairly difficult — 10th–12th grader"
    if score >= 30:
        return "Difficult — College student"
    return "Very difficult — College graduate"


def audit_text(text: str) -> Dict[str, Any]:
    """Compute readability metrics for ``text``."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "Empty text"}

    sentences = [s.strip() for s in SENTENCE_RE.findall(text) if s.strip() and re.search(r"[A-Za-z]", s)]
    sentence_count = max(1, len(sentences))
    words = WORD_RE.findall(text)
    word_count = len(words)
    if word_count == 0:
        return {"ok": False, "error": "No words detected"}

    syllable_total = sum(_count_syllables(w) for w in words)
    chars_alpha = sum(len(w) for w in words)
    avg_word_len = chars_alpha / word_count

    # Flesch Reading Ease
    flesch = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_total / word_count)
    flesch = round(flesch, 1)

    # Flesch-Kincaid Grade Level
    fk_grade = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_total / word_count) - 15.59
    fk_grade = round(fk_grade, 1)

    # Automated Readability Index (uses chars instead of syllables — handy
    # second opinion that doesn't depend on our syllable heuristic)
    ari = 4.71 * (chars_alpha / word_count) + 0.5 * (word_count / sentence_count) - 21.43
    ari = round(ari, 1)

    # Sentence-length distribution
    sent_lengths = [len(WORD_RE.findall(s)) for s in sentences]
    longest_sentence_words = max(sent_lengths) if sent_lengths else 0
    long_sentences = sum(1 for n in sent_lengths if n > 25)
    short_sentences = sum(1 for n in sent_lengths if n <= 12)

    # Polysyllabic words (3+ syllables)
    polysyllabic = sum(1 for w in words if _count_syllables(w) >= 3)
    polysyllabic_ratio = round(polysyllabic / word_count, 3)

    # Jargon hits
    jargon_hits: List[str] = []
    text_lower = text.lower()
    for j in JARGON_WORDS:
        if re.search(rf"\b{re.escape(j)}\b", text_lower):
            jargon_hits.append(j)

    # Passive voice
    passive_count = len(PASSIVE_RE.findall(text))

    # Acronyms / abbreviations
    abbrevs = sorted(set(ABBREV_RE.findall(text)))[:10]

    # Most-frequent non-trivial words
    stopwords = {
        "the", "and", "a", "to", "of", "in", "is", "it", "that", "for",
        "on", "with", "as", "are", "was", "were", "be", "by", "an", "or",
        "this", "from", "you", "we", "i", "they", "he", "she", "but",
        "not", "have", "has", "had", "if", "their", "our", "your", "its",
        "at", "so", "do", "does", "did", "will", "would", "can", "could",
    }
    freq = Counter(w.lower() for w in words if w.lower() not in stopwords and len(w) > 3).most_common(8)

    return {
        "ok": True,
        "stats": {
            "char_count": len(text),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_words_per_sentence": round(word_count / sentence_count, 1),
            "avg_word_length_chars": round(avg_word_len, 2),
            "syllable_total": syllable_total,
            "polysyllabic_words": polysyllabic,
            "polysyllabic_ratio": polysyllabic_ratio,
            "longest_sentence_words": longest_sentence_words,
            "long_sentences_over_25": long_sentences,
            "short_sentences_under_12": short_sentences,
        },
        "readability": {
            "flesch_reading_ease": flesch,
            "flesch_band": _flesch_band(flesch),
            "fk_grade_level": fk_grade,
            "fk_grade_label": _grade_label(fk_grade),
            "automated_readability_index": ari,
            "ari_grade_label": _grade_label(ari),
        },
        "issues": {
            "passive_voice_count": passive_count,
            "jargon_hits": jargon_hits,
            "abbreviations_found": abbrevs,
        },
        "frequent_words": [{"word": w, "count": c} for w, c in freq],
    }


def evidence_summary_for_prompt(evidence: Dict[str, Any]) -> str:
    if not evidence.get("ok"):
        return f"TEXT ANALYSIS FAILED: {evidence.get('error', 'unknown')}"
    s = evidence["stats"]
    r = evidence["readability"]
    i = evidence["issues"]
    lines = ["READABILITY ANALYSIS (deterministic, before LLM rewrite)"]
    lines.append(
        f"  words={s['word_count']} sentences={s['sentence_count']} "
        f"avg_words_per_sentence={s['avg_words_per_sentence']} "
        f"avg_word_len={s['avg_word_length_chars']} chars"
    )
    lines.append(
        f"  longest_sentence={s['longest_sentence_words']} words; "
        f"long_sentences(>25w)={s['long_sentences_over_25']}; "
        f"short_sentences(<=12w)={s['short_sentences_under_12']}"
    )
    lines.append(
        f"  polysyllabic_words={s['polysyllabic_words']} ({s['polysyllabic_ratio']*100:.0f}% of total)"
    )
    lines.append(
        f"  Flesch Reading Ease={r['flesch_reading_ease']} ({r['flesch_band']})"
    )
    lines.append(
        f"  Flesch-Kincaid grade={r['fk_grade_level']} ({r['fk_grade_label']})"
    )
    lines.append(
        f"  Automated Readability Index={r['automated_readability_index']} "
        f"({r['ari_grade_label']})"
    )
    lines.append(f"  passive_voice_clauses_detected={i['passive_voice_count']}")
    if i["jargon_hits"]:
        lines.append(f"  jargon_to_replace: {', '.join(i['jargon_hits'][:12])}")
    if i["abbreviations_found"]:
        lines.append(f"  acronyms_found: {', '.join(i['abbreviations_found'])}")
    return "\n".join(lines)
