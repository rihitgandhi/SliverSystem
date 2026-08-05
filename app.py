from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import gzip
import io
import os
import logging
from datetime import datetime
import json
from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
    FLASK_SECRET_KEY,
    FLASK_DEBUG,
    HOST,
    PORT,
)
import ai_client

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = FLASK_SECRET_KEY

# ---------------------------------------------------------------------------
# Logging — send to stdout so Azure App Service log stream picks it up.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if FLASK_DEBUG else logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
log = app.logger

# ---------------------------------------------------------------------------
# Optional Azure Application Insights instrumentation.
# Activated automatically when APPLICATIONINSIGHTS_CONNECTION_STRING is set
# (the Bicep template injects this). The dependency is optional — if it isn't
# installed we just log and continue, so local development still works.
# ---------------------------------------------------------------------------
if os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING'):
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor  # type: ignore
        configure_azure_monitor(logger_name=__name__)
        log.info('Application Insights configured.')
    except Exception as exc:  # pragma: no cover — telemetry is best-effort
        log.warning('Application Insights not configured: %s', exc)

# ---------------------------------------------------------------------------
# CORS — same-origin requests don't trigger CORS, so this list only matters
# when the frontend is hosted on a different origin (e.g. GitHub Pages).
# Origins can be overridden via the ALLOWED_ORIGINS env var (comma-separated).
# When deployed on App Service we auto-add https://<WEBSITE_HOSTNAME>.
# ---------------------------------------------------------------------------
_default_origins = [
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'https://rihitgandhi.github.io',
]
_extra = os.getenv('ALLOWED_ORIGINS', '').strip()
allowed_origins = list(_default_origins)
if _extra:
    allowed_origins.extend([o.strip() for o in _extra.split(',') if o.strip()])
_app_service_host = os.getenv('WEBSITE_HOSTNAME', '').strip()
if _app_service_host:
    allowed_origins.append(f'https://{_app_service_host}')

CORS(app,
     resources={r"/api/*": {"origins": allowed_origins}},
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
     supports_credentials=False)


# Lightweight request logging — only in debug mode.
@app.before_request
def log_request_info():
    if FLASK_DEBUG:
        log.debug('Request: %s %s', request.method, request.path)


# Performance: gzip-compress JSON / HTML / CSS / JS responses, and add
# Cache-Control headers for static assets so the browser can re-use them
# across page loads.
_COMPRESSIBLE_TYPES = (
    'text/html', 'text/css', 'application/javascript',
    'application/json', 'image/svg+xml', 'text/plain'
)
_STATIC_PREFIXES = ('/css/', '/scripts/', '/styles/', '/images/')


@app.after_request
def _post_process(response):
    # Cache static assets aggressively (1 day) and HTML for a short window
    path = request.path or ''
    if path.startswith(_STATIC_PREFIXES):
        response.headers.setdefault('Cache-Control', 'public, max-age=86400')
    elif path.endswith('.html') or path == '/':
        response.headers.setdefault('Cache-Control', 'public, max-age=300')

    # Skip compression for already-compressed bodies, ranged responses,
    # or unsupported content types.
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding.lower():
        return response
    if response.status_code < 200 or response.status_code >= 300:
        return response
    if 'Content-Encoding' in response.headers:
        return response

    content_type = (response.headers.get('Content-Type') or '').split(';', 1)[0].strip().lower()
    if not any(content_type.startswith(t) for t in _COMPRESSIBLE_TYPES):
        return response

    # Materialise the body. Static files use direct_passthrough by default —
    # turning it off forces Flask to read the file into memory so we can gzip it.
    if response.direct_passthrough:
        response.direct_passthrough = False

    raw = response.get_data()
    if len(raw) < 1024:  # not worth compressing tiny bodies
        return response

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=6) as gz:
        gz.write(raw)
    response.set_data(buffer.getvalue())
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = str(len(response.get_data()))
    response.headers.add('Vary', 'Accept-Encoding')
    return response

# Configure Azure OpenAI
if not ai_client.is_configured():
    log.warning('Azure OpenAI is not configured! AI-powered features will be disabled.')
else:
    log.info('Azure OpenAI configured (deployment=%s, api-version=%s).',
             AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    api_key_status = 'configured' if ai_client.is_configured() else 'not configured'
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'api_key': api_key_status
    })

@app.route('/help.html')
def help_page():
    return send_from_directory('.', 'help.html')

@app.route('/memory-layer.html')
def memory_layer_page():
    return send_from_directory('.', 'memory-layer.html')

@app.route('/voice-navigation.html')
def voice_navigation_page():
    return send_from_directory('.', 'voice-navigation.html')

@app.route('/api/cors-test', methods=['GET', 'OPTIONS'])
def cors_test():
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request for /api/cors-test")
        response = jsonify({'status': 'ok'})
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    print("Handling GET request for /api/cors-test")
    response = jsonify({
        'message': 'CORS test successful',
        'origin': request.headers.get('Origin', 'No Origin'),
        'timestamp': datetime.now().isoformat()
    })
    print(f"GET response headers: {dict(response.headers)}")
    return response

@app.route('/api/alt-text', methods=['POST', 'OPTIONS'])
def generate_alt_text():
    """Generate AI-powered alt text — grounded in deterministic image evidence.

    Differentiated workflow (mirrors /api/score):
      1. Decode the uploaded image and run a **deterministic file audit**
         (dimensions, format, dominant colours, EXIF, decorative heuristics).
      2. Pass that evidence to the vision LLM as ground truth so the
         generated alt-text never contradicts the actual image properties
         and the model can pick an appropriate WCAG pattern (decorative,
         informative, functional, complex).
      3. Return alt-text + evidence + W3C sources so the user can verify
         every claim and understand WHY a given pattern was chosen.
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})

    try:
        data = request.json or {}
        image_data = data.get('image', '')
        detail_level = data.get('detail_level', 'standard')
        context = data.get('context', '')
        tone = data.get('tone', 'neutral')

        if not image_data:
            return jsonify({'error': 'No image provided'}), 400

        from image_audit import audit_image, evidence_summary_for_prompt, ALT_TEXT_REFERENCES

        # ---- 1. Inspect the file (real evidence) -----------------------
        evidence = audit_image(image_data)
        if not evidence.get('ok'):
            return jsonify({'error': evidence.get('error', 'Could not decode image')}), 400

        # Strip data-URL prefix for the vision call
        if ',' in image_data and image_data.lstrip().startswith('data:'):
            image_b64 = image_data.split(',', 1)[1]
        else:
            image_b64 = image_data

        detail_instructions = {
            'concise':  '8-15 words, single phrase, only the essential meaning',
            'standard': '20-40 words, balanced detail, one focused sentence',
            'detailed': '40-80 words, comprehensive description for complex/informative images',
        }

        # ---- 2. Ground the LLM in the file analysis --------------------
        evidence_summary = evidence_summary_for_prompt(evidence)

        system_prompt = (
            "You are a senior accessibility specialist generating alt-text. You "
            "receive both the image AND a deterministic FILE ANALYSIS REPORT "
            "(dimensions, format, dominant palette, EXIF, decorative/photo/chart "
            "heuristics). Use that report as ground truth — never claim a colour "
            "or aspect that contradicts it.\n\n"
            "Follow the W3C ALT-TEXT DECISION TREE:\n"
            "  • If the file analysis says the image is decorative or near-uniform, "
            "    return alt='' and explain why.\n"
            "  • If it's a photograph (EXIF Make/Model present, or large JPEG), "
            "    describe people, action, setting, and any text visible.\n"
            "  • If it's a chart/diagram, summarise the takeaway and recommend a long "
            "    description (aria-describedby).\n"
            "  • If it's possibly an image of text (WCAG 1.4.5), warn that real text "
            "    would be more accessible.\n\n"
            "Rules: never start with 'image of' or 'picture of'. No filler. Match the "
            "requested length and tone. If the image is ambiguous, say so — do not "
            "invent details.\n\n"
            "RESPOND ONLY WITH JSON of this exact shape (use these EXACT key names — "
            "no synonyms, no extra wrapper object, no prose outside JSON):\n"
            "{\n"
            '  "main_alt_text": "<primary recommendation. EMPTY STRING if decorative.>",\n'
            '  "alternatives": ["<v1>", "<v2>", "<v3>"],\n'
            '  "wcag_pattern": "decorative | informative | functional | complex | image_of_text",\n'
            '  "pattern_rationale": "1-2 sentences citing specific evidence from the FILE ANALYSIS",\n'
            '  "long_description_recommended": true | false,\n'
            '  "long_description_draft": "<empty string if not recommended; otherwise a 2-4 sentence draft>",\n'
            '  "warnings": ["<e.g. \'Possible image of text — prefer real HTML text\'>"],\n'
            '  "html_snippet_suggestion": "<ready-to-paste <img …> tag>"\n'
            "}"
        )

        user_prompt = (
            f"DETAIL LEVEL: {detail_instructions.get(detail_level, detail_instructions['standard'])}\n"
            f"CONTEXT GIVEN BY USER: {context or '(none)'}\n"
            f"TONE REQUESTED: {tone}\n\n"
            "FILE ANALYSIS REPORT (deterministic, computed locally):\n"
            "----------------------------------------------------------\n"
            f"{evidence_summary}\n"
            "----------------------------------------------------------\n\n"
            "Now look at the attached image and produce the JSON described above. "
            "Cite at least one concrete detail from the FILE ANALYSIS REPORT in "
            "pattern_rationale."
        )

        # ---- 3. Call the LLM (or fall back gracefully) -----------------
        if not ai_client.is_configured():
            ai_result = {
                "main_alt_text": "(AI vision service is not configured)",
                "alternatives": [],
                "wcag_pattern": "informative",
                "pattern_rationale": "Heuristic only: the file analysis suggests this is "
                                     + ", ".join(evidence.get("classifications", ["informative"])) + ".",
                "long_description_recommended": "chart-or-diagram" in evidence.get("classifications", []),
                "long_description_draft": "",
                "warnings": ["Configure Azure OpenAI to enable AI-grounded alt-text generation."],
                "html_snippet_suggestion": '<img src="…" alt="">',
                "_fallback_reason": "ai_not_configured",
            }
        else:
            try:
                ai_result = ai_client.generate_json_with_image(
                    user_prompt, image_b64=image_b64, mime_type='image/jpeg',
                )
                if not isinstance(ai_result, dict):
                    raise ValueError("Vision model did not return a JSON object")
            except Exception as parse_error:
                print(f"[alt-text] LLM call failed, evidence-only fallback: {parse_error}")
                klass = evidence.get("classifications", ["informative"])[0]
                ai_result = {
                    "main_alt_text": "",
                    "alternatives": [],
                    "wcag_pattern": ("decorative" if "decorative" in klass else
                                     "complex" if "chart" in klass else
                                     "image_of_text" if "image-of-text" in klass else
                                     "informative"),
                    "pattern_rationale": f"Evidence-only fallback: file analysis classifies this as {klass}.",
                    "long_description_recommended": "chart" in klass,
                    "long_description_draft": "",
                    "warnings": [f"AI fallback: {parse_error}"],
                    "html_snippet_suggestion": '<img src="…" alt="">',
                }

        # ---- 4. Combine + attach sources -------------------------------
        result = dict(ai_result) if isinstance(ai_result, dict) else {"main_alt_text": str(ai_result)}

        # Normalise common aliases the model sometimes returns
        if not result.get("main_alt_text"):
            for alias in ("essential_meaning", "alt_text", "alt", "description",
                          "primary_alt", "recommended_alt"):
                if result.get(alias):
                    result["main_alt_text"] = result[alias]
                    break
        # If the model picked the decorative pattern but left alt empty, that's
        # the correct choice — surface it explicitly to the user.
        if (result.get("wcag_pattern") == "decorative" or
            (evidence.get("heuristics", {}).get("likely_decorative") and not result.get("main_alt_text"))):
            if not result.get("main_alt_text"):
                result["main_alt_text"] = '""  (decorative — leave alt empty)'
            if not result.get("wcag_pattern"):
                result["wcag_pattern"] = "decorative"
        # Make sure key fields exist so the UI doesn't show null/undefined
        result.setdefault("alternatives", [])
        result.setdefault("warnings", [])
        result.setdefault("long_description_recommended", False)
        result.setdefault("long_description_draft", "")
        if not result.get("html_snippet_suggestion"):
            alt_for_html = "" if result.get("wcag_pattern") == "decorative" else (result.get("main_alt_text") or "")
            # strip the parenthetical hint we may have added
            if alt_for_html.startswith('""'):
                alt_for_html = ""
            result["html_snippet_suggestion"] = '<img src="…" alt="' + alt_for_html.replace('"', '&quot;') + '">'

        result["evidence"] = evidence
        result["sources"] = ALT_TEXT_REFERENCES
        result["differentiator"] = (
            "This isn't a one-shot vision call. We first inspected the file "
            "(dimensions, palette, EXIF, decorative heuristics) and grounded the "
            "AI in that analysis — so the alt-text matches the actual image and "
            "the chosen WCAG pattern is justified, not guessed."
        )
        return jsonify(result)

    except ValueError as ve:
        print(f"Alt-text JSON parse error: {ve}")
        return jsonify({'error': 'AI returned an unexpected response. Please try again.'}), 502
    except Exception as e:
        print(f"Error generating alt text: {str(e)}")
        return jsonify({'error': str(e) if FLASK_DEBUG else 'Failed to generate alt text. Please try again.'}), 500

@app.route('/api/review-code', methods=['POST', 'OPTIONS'])
def review_code():
    """Differentiated, evidence-grounded code review.

    Workflow:
      1. Run a deterministic accessibility lint over the submitted code:
         every finding has a real line number, severity, and WCAG citation.
      2. Compute a baseline score from the lint and pre-flag the issues.
      3. Pass the lint findings + the original code to the LLM as ground
         truth. The model must reference real line numbers and may add
         issues the lint missed (e.g. semantic / contextual problems) but
         cannot contradict what was statically detected.
      4. Return the merged report + sources for every triggered rule.
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})

    try:
        data = request.json or {}
        code = data.get('code', '')
        code_type = data.get('code_type', 'html')
        if not code.strip():
            return jsonify({'error': 'No code provided'}), 400

        from code_audit import audit_code, evidence_summary_for_prompt

        # ---- 1. Deterministic lint (real evidence) ---------------------
        evidence = audit_code(code, hint_lang=code_type)
        evidence_summary = evidence_summary_for_prompt(evidence)

        system_prompt = (
            "You are a senior web accessibility code reviewer. You receive both "
            "the source code AND a deterministic STATIC LINT REPORT (line numbers, "
            "severities, WCAG criteria) extracted by an automated tool. Treat the "
            "lint report as ground truth — every finding it lists IS in the code. "
            "Your job is to:\n"
            "  • interpret each lint finding for real users with disabilities,\n"
            "  • identify ADDITIONAL semantic / contextual issues the static lint "
            "    cannot catch (ARIA misuse, role mismatches, focus-trap risk, etc.),\n"
            "  • produce concrete fix snippets,\n"
            "  • aggregate everything into a single ranked issue list and a score.\n\n"
            "Severity scale: critical | high | moderate | low. Use the same WCAG "
            "criterion the lint cited for issues it already raised; assign one of "
            "your own for new issues.\n\n"
            "RESPOND ONLY WITH JSON:\n"
            "{\n"
            '  "score": <int 0-100>,\n'
            '  "score_explanation": "<one paragraph grounded in the lint counts>",\n'
            '  "summary_counts": {"critical": <n>, "high": <n>, "moderate": <n>, "low": <n>},\n'
            '  "issues": [\n'
            '    { "title": "...", "severity": "...", "wcag_criterion": "...",\n'
            '      "line": <int|null>, "description": "...",\n'
            '      "user_impact": "How a screen-reader / keyboard / low-vision user is affected.",\n'
            '      "code_snippet": "<minimal current snippet>",\n'
            '      "fix":          "<minimal corrected snippet>",\n'
            '      "fix_steps":   ["1. ...", "2. ..."],\n'
            '      "rule_id":     "<lint rule_id if from the static report>"\n'
            "    }\n"
            "  ],\n"
            '  "recommendations": ["<broad guidance grounded in the lint stats>"],\n'
            '  "next_steps": "<one paragraph>"\n'
            "}"
        )

        user_prompt = (
            f"LANGUAGE (auto-detected): {evidence['language']}\n"
            f"DETERMINISTIC SCORE: {evidence['deterministic_score']} / 100\n\n"
            "STATIC LINT REPORT:\n"
            "----------------------------------------------------------\n"
            f"{evidence_summary}\n"
            "----------------------------------------------------------\n\n"
            "ORIGINAL CODE (cite line numbers):\n"
            "----------------------------------------------------------\n"
            f"{code[:8000]}\n"
            "----------------------------------------------------------\n\n"
            "Produce the JSON described in the system prompt. Every issue you list "
            "MUST cite a line number that exists in the code. Use the rule_id from "
            "the lint report for findings it already raised."
        )

        # ---- 2. LLM call (or evidence-only fallback) -------------------
        if not ai_client.is_configured():
            ai_result = _code_evidence_only_fallback(evidence)
        else:
            try:
                ai_result = ai_client.generate_json(user_prompt, system_message=system_prompt)
                if not isinstance(ai_result, dict):
                    raise ValueError("Model did not return a JSON object")
            except Exception as parse_error:
                print(f"[review-code] LLM analysis failed, falling back: {parse_error}")
                ai_result = _code_evidence_only_fallback(evidence)
                ai_result['_fallback_reason'] = str(parse_error)

        # ---- 3. Merge + sources ---------------------------------------
        result = dict(ai_result)
        result['evidence'] = evidence
        result['sources'] = evidence['sources']
        result['differentiator'] = (
            "We ran a deterministic accessibility lint against your code first — "
            f"detecting {sum(evidence['severity_counts'].values())} issue(s) at exact "
            "line numbers — then grounded the AI in those findings. The AI adds "
            "semantic context and fixes, but every cited line is real."
        )
        return jsonify(result)

    except ValueError as ve:
        print(f"Review-code JSON parse error: {ve}")
        return jsonify({'error': 'AI returned an unexpected response. Please try again.'}), 502
    except Exception as e:
        print(f"Error reviewing code: {str(e)}")
        return jsonify({'error': str(e) if FLASK_DEBUG else 'Failed to review code. Please try again.'}), 500


def _code_evidence_only_fallback(evidence):
    """Build a usable review purely from the deterministic lint."""
    issues = []
    for f in evidence.get('findings', []):
        ref = None
        from code_audit import CODE_RULE_REFERENCES
        ref = CODE_RULE_REFERENCES.get(f['rule_id']) or {}
        issues.append({
            'title': ref.get('title', f['rule_id']),
            'severity': f['severity'].capitalize(),
            'wcag_criterion': f['wcag_criterion'],
            'line': f['line'],
            'description': f['message'],
            'user_impact': '—',
            'code_snippet': f['snippet'],
            'fix': '',
            'fix_steps': [],
            'rule_id': f['rule_id'],
        })
    sc = evidence['severity_counts']
    return {
        'score': evidence['deterministic_score'],
        'score_explanation': (
            f"Score based on the deterministic lint alone (AI commentary unavailable). "
            f"Found {sc['critical']} critical, {sc['high']} high, {sc['moderate']} moderate, "
            f"{sc['low']} low-severity issue(s)."
        ),
        'summary_counts': sc,
        'issues': issues,
        'recommendations': [
            'Address critical issues first — they block entire user groups.',
            'Adopt an automated accessibility lint (axe-core, eslint-plugin-jsx-a11y) in CI.',
        ],
        'next_steps': 'Configure Azure OpenAI to enable AI-grounded code review on top of this lint.',
    }

@app.route('/api/simplify-content', methods=['POST', 'OPTIONS'])
def simplify_content():
    """Differentiated content simplifier with measured before/after readability.

    Workflow:
      1. Compute objective readability metrics for the ORIGINAL text
         (Flesch, FK Grade, ARI, jargon, passive voice, etc.).
      2. Pass those numbers + the user's target grade to the LLM as the
         success criteria — model must beat them.
      3. Re-measure the LLM's output. If it didn't improve grade or word
         count, surface that honestly in the response.
      4. Return original/simplified text + before+after evidence + deltas
         + W3C / plain-language sources.
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})

    try:
        data = request.json or {}
        content = (data.get('content') or '').strip()
        reading_level = data.get('reading_level', 'middle')
        simplification_level = data.get('simplification_level', 'moderate')
        content_type = data.get('content_type', 'general')

        if not content:
            return jsonify({'error': 'No content provided'}), 400

        from text_audit import audit_text, evidence_summary_for_prompt, READABILITY_REFERENCES

        target_grades = {
            'elementary': '3rd grade (FK ~3.0)',
            'middle':     '6th grade (FK ~6.0)',
            'high':       '9th grade (FK ~9.0)',
            'college':    '12th grade (FK ~12.0)',
        }
        target_grade_text = target_grades.get(reading_level, target_grades['middle'])

        # ---- 1. Measure the original (real evidence) -------------------
        before_evidence = audit_text(content)
        if not before_evidence.get('ok'):
            return jsonify({'error': before_evidence.get('error', 'Could not analyse text')}), 400

        before_summary = evidence_summary_for_prompt(before_evidence)

        system_prompt = (
            "You are a plain-language editor and accessibility specialist. You "
            "receive both the ORIGINAL text AND a deterministic READABILITY "
            "REPORT (Flesch, FK grade, sentence stats, jargon list, passive count). "
            "Your job is to rewrite the text so the *measured* FK grade drops to "
            "the target band. Keep meaning intact.\n\n"
            "Plain-language rules:\n"
            "  • Sentences ≤ 20 words. Break up the long ones flagged in the report.\n"
            "  • Replace every jargon word the report listed with a common synonym.\n"
            "  • Convert passive voice to active where natural.\n"
            "  • Expand acronyms on first use.\n"
            "  • Keep paragraphs short (≤ 4 sentences).\n"
            "  • Preserve every fact / number from the original.\n\n"
            "RESPOND ONLY WITH JSON:\n"
            "{\n"
            '  "simplified_content": "<rewritten plain-language text>",\n'
            '  "improvements": ["<each improvement should reference a specific metric from the report>"],\n'
            '  "jargon_replacements": [{"from": "...", "to": "..."}],\n'
            '  "preserved_facts": ["<key facts kept intact>"],\n'
            '  "remaining_concerns": ["<anything still hard to simplify and why>"]\n'
            "}"
        )

        user_prompt = (
            f"TARGET READING LEVEL: {target_grade_text}\n"
            f"SIMPLIFICATION INTENSITY: {simplification_level}\n"
            f"CONTENT TYPE: {content_type}\n\n"
            "READABILITY REPORT FOR ORIGINAL TEXT (must improve every metric):\n"
            "----------------------------------------------------------\n"
            f"{before_summary}\n"
            "----------------------------------------------------------\n\n"
            "ORIGINAL TEXT:\n"
            "----------------------------------------------------------\n"
            f"{content[:6000]}\n"
            "----------------------------------------------------------\n\n"
            "Rewrite the text and return the JSON described in the system prompt. "
            "Each improvement must cite a number from the report (e.g. \"FK grade 14.2 → ~6\")."
        )

        # ---- 2. LLM call (or fallback) ---------------------------------
        if not ai_client.is_configured():
            ai_result = {
                "simplified_content": content,
                "improvements": ["AI service is not configured — original text returned unchanged."],
                "jargon_replacements": [],
                "preserved_facts": [],
                "remaining_concerns": ["Configure Azure OpenAI credentials to enable rewriting."],
                "_fallback_reason": "ai_not_configured",
            }
        else:
            try:
                ai_result = ai_client.generate_json(user_prompt, system_message=system_prompt)
                if not isinstance(ai_result, dict) or not ai_result.get('simplified_content'):
                    raise ValueError("Model did not return a usable JSON object")
            except Exception as parse_error:
                print(f"[simplify] LLM call failed, returning original: {parse_error}")
                ai_result = {
                    "simplified_content": content,
                    "improvements": [f"AI fallback: {parse_error}"],
                    "jargon_replacements": [],
                    "preserved_facts": [],
                    "remaining_concerns": ["AI service did not return a valid response."],
                }

        # ---- 3. Measure the AI output ---------------------------------
        simplified = ai_result.get('simplified_content') or content
        after_evidence = audit_text(simplified)

        # ---- 4. Compute deltas ----------------------------------------
        deltas: dict = {}
        if after_evidence.get('ok'):
            b, a = before_evidence['readability'], after_evidence['readability']
            bs, asd = before_evidence['stats'], after_evidence['stats']
            deltas = {
                'fk_grade_change': round(a['fk_grade_level'] - b['fk_grade_level'], 1),
                'flesch_change':   round(a['flesch_reading_ease'] - b['flesch_reading_ease'], 1),
                'word_count_change':     asd['word_count'] - bs['word_count'],
                'sentence_count_change': asd['sentence_count'] - bs['sentence_count'],
                'avg_sentence_length_change': round(
                    asd['avg_words_per_sentence'] - bs['avg_words_per_sentence'], 1
                ),
                'passive_voice_change':
                    after_evidence['issues']['passive_voice_count']
                    - before_evidence['issues']['passive_voice_count'],
                'jargon_remaining': len(after_evidence['issues']['jargon_hits']),
                'jargon_removed': max(
                    0,
                    len(before_evidence['issues']['jargon_hits'])
                    - len(after_evidence['issues']['jargon_hits']),
                ),
            }

        # ---- 5. Build response (back-compat keys retained) ------------
        result = {
            'original_content': content,
            'simplified_content': simplified,
            'original_grade_level':
                f"Grade {before_evidence['readability']['fk_grade_level']} "
                f"({before_evidence['readability']['fk_grade_label']})",
            'simplified_grade_level':
                (f"Grade {after_evidence['readability']['fk_grade_level']} "
                 f"({after_evidence['readability']['fk_grade_label']})")
                if after_evidence.get('ok') else 'n/a',
            'original_word_count': before_evidence['stats']['word_count'],
            'simplified_word_count':
                after_evidence['stats']['word_count'] if after_evidence.get('ok') else 0,
            'improvements': ai_result.get('improvements', []),
            'jargon_replacements': ai_result.get('jargon_replacements', []),
            'preserved_facts': ai_result.get('preserved_facts', []),
            'remaining_concerns': ai_result.get('remaining_concerns', []),
            'before_evidence': before_evidence,
            'after_evidence': after_evidence,
            'deltas': deltas,
            'sources': READABILITY_REFERENCES,
            'differentiator': (
                "We measure your text BEFORE and AFTER the AI rewrite using the "
                "same Flesch / Flesch-Kincaid / ARI formulas used by editors and "
                "researchers — so every claim of 'easier to read' is backed by a "
                "real number, not a vibe."
            ),
        }
        if '_fallback_reason' in ai_result:
            result['_fallback_reason'] = ai_result['_fallback_reason']
        return jsonify(result)

    except ValueError as ve:
        print(f"Simplify-content JSON parse error: {ve}")
        return jsonify({'error': 'AI returned an unexpected response. Please try again.'}), 502
    except Exception as e:
        print(f"Error simplifying content: {str(e)}")
        return jsonify({'error': str(e) if FLASK_DEBUG else 'Failed to simplify content. Please try again.'}), 500

if __name__ == '__main__':
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Azure OpenAI Status: {'Configured' if ai_client.is_configured() else 'NOT CONFIGURED'}")
    if not ai_client.is_configured():
        print("WARNING: Please update .env with your Azure OpenAI credentials (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT)")
    app.run(debug=FLASK_DEBUG, host=HOST, port=PORT) 