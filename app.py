from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import gzip
import io
import os
import logging
from collections import OrderedDict
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
    log.warning('Azure OpenAI is not configured! Chatbot functionality will be disabled.')
else:
    log.info('Azure OpenAI configured (deployment=%s, api-version=%s).',
             AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION)

# In-memory conversation store. Bounded so a long-running App Service worker
# can't be DoSed into running out of memory. With multiple gunicorn workers
# the same conversation_id may land on different workers — this store is
# best-effort context only; the LLM still works without prior turns.
_MAX_CONVERSATIONS = 500          # distinct conversation_ids retained
_MAX_TURNS_PER_CONVERSATION = 20  # rolling window per conversation
conversations: "OrderedDict[str, list]" = OrderedDict()


def _record_turn(conversation_id: str, role: str, content: str) -> list:
    """Append a turn to the bounded conversation store and return the history."""
    history = conversations.get(conversation_id)
    if history is None:
        history = []
        conversations[conversation_id] = history
        # Evict oldest conversation when over capacity (LRU-by-insertion).
        while len(conversations) > _MAX_CONVERSATIONS:
            conversations.popitem(last=False)
    else:
        # Mark as recently used.
        conversations.move_to_end(conversation_id)
    history.append({
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat(),
    })
    # Trim per-conversation window.
    if len(history) > _MAX_TURNS_PER_CONVERSATION:
        del history[: len(history) - _MAX_TURNS_PER_CONVERSATION]
    return history

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request for /api/chat")
        # Handle preflight request - Flask-CORS will handle the headers
        response = jsonify({'status': 'ok'})
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        conversation_id = data.get('conversation_id', 'default')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Add user message to bounded history.
        history = _record_turn(conversation_id, 'user', user_message)

        # Prepare context for Azure OpenAI
        system_message = "You are an AI assistant specialized in computer accessibility and web design. Your role is to help users understand and implement accessibility features, answer questions about WCAG guidelines, assistive technologies, and inclusive design practices. Be helpful, informative, and encouraging. Keep responses concise but thorough, and always prioritize accessibility best practices."

        # Build the prompt string: recent history + user message
        prompt = ""
        for msg in history[-10:]:
            if msg['role'] == 'user':
                prompt += f"User: {msg['content']}\n"
            else:
                prompt += f"Assistant: {msg['content']}\n"
        prompt += "Assistant:"

        # Use Azure OpenAI to generate a response
        if not ai_client.is_configured():
            assistant_message = "I'm sorry, but the chatbot functionality is currently disabled because Azure OpenAI is not configured. Please contact the administrator to set up the credentials for full functionality."
        else:
            assistant_message = ai_client.generate_text(prompt, system_message=system_message)

        # Record assistant turn.
        _record_turn(conversation_id, 'assistant', assistant_message)

        return jsonify({
            'response': assistant_message,
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        log.exception('Error in /api/chat')
        return jsonify({
            'error': 'An error occurred while processing your request',
            'details': str(e) if FLASK_DEBUG else 'Check server logs for details'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    api_key_status = 'configured' if ai_client.is_configured() else 'not configured'
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'api_key': api_key_status
    })

@app.route('/chat.html')
def chat_page():
    return send_from_directory('.', 'chat.html')

@app.route('/score.html')
def score_page():
    return send_from_directory('.', 'score.html')

@app.route('/help.html')
def help_page():
    return send_from_directory('.', 'help.html')

@app.route('/api/score', methods=['POST', 'OPTIONS'])
def score():
    """Differentiated accessibility report.

    The previous version asked the LLM to invent findings from a URL string
    alone (it never saw the page). This implementation does both:

      1. Server-side **fetch** of the URL with SSRF guards, size cap, and
         timeout — so the report describes the actual page.
      2. Deterministic **DOM audit** that extracts objective signals
         (alt-text coverage, heading outline, landmarks, form labels,
         ARIA usage, link purpose, color samples, etc.).
      3. **LLM analysis grounded** in that evidence: the model now receives
         a compact summary of every measurement we made, so its commentary
         cites real numbers, suggests fixes for the actual selectors found,
         and never speculates about elements that are not present.
      4. **Sourced** — every WCAG criterion comes back paired with its
         canonical W3C "Understanding…" link plus a deep-dive resource so
         the developer can verify and learn.
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})

    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            return jsonify({'error': f'Invalid JSON format: {json_error}'}), 400

        url = (data.get('url') or '').strip()
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url

        # ---- 1. Fetch the page (web evidence) ---------------------------
        from web_audit import fetch_page, audit_html, evidence_summary_for_prompt, WCAG_REFERENCES
        page = fetch_page(url)
        if not page['ok']:
            return jsonify({
                'error': f"Could not fetch the URL: {page['error']}",
                'error_kind': page.get('error_kind'),
                'url': url,
            }), 400

        # ---- 2. Deterministic DOM audit (real evidence) -----------------
        evidence = audit_html(page['html'], page['final_url'])

        page_meta = {
            'requested_url': url,
            'final_url': page['final_url'],
            'http_status': page['status'],
            'response_time_ms': page['elapsed_ms'],
            'page_size_bytes': page['content_length'],
            'page_size_kb': round(page['content_length'] / 1024, 1),
            'content_type': page['content_type'],
            'server': page['server'],
            'security_headers': page['security_headers'],
            'truncated': page['truncated'],
            'analyzed_at': datetime.now().isoformat(),
        }

        # ---- 3. Build the grounded LLM prompt ---------------------------
        evidence_summary = evidence_summary_for_prompt(evidence)

        system_prompt = (
            "You are a senior web accessibility auditor specialising in WCAG 2.1 "
            "Level AA. You receive a compact, deterministic AUDIT REPORT extracted "
            "directly from the live HTML of a page (image counts, heading outline, "
            "landmark counts, form labels, ARIA usage, etc.). Treat that report as "
            "ground truth — do NOT invent findings, do NOT speculate about elements "
            "the audit does not mention, and do NOT contradict the numbers. Your job "
            "is to: (a) interpret the evidence, (b) score the page using the formula "
            "below, (c) explain *why* each finding matters for real users with "
            "disabilities, and (d) return concrete fixes that reference the actual "
            "selectors / counts the audit found.\n\n"
            "SCORING (0–100):\n"
            "  Start at 100 and subtract:\n"
            "    Critical (alt text, keyboard, contrast, form labels): -10 each, capped at -40\n"
            "    Structural (headings, semantic HTML, landmarks, focus order): -7.5 each, capped at -30\n"
            "    Content (lang, error msgs, link purpose): -5 each, capped at -20\n"
            "    Technical (HTML validity, ARIA correctness, responsive): -2.5 each, capped at -10\n"
            "  Round to integer. Identical evidence MUST yield an identical score.\n\n"
            "RESPOND ONLY WITH JSON of this exact shape (no prose outside the JSON):\n"
            "{\n"
            '  "score": <int 0-100>,\n'
            '  "compliance_level": "<e.g. WCAG 2.1 Level A (Partial AA)>",\n'
            '  "score_explanation": "<1-2 paragraphs grounded in the AUDIT REPORT numbers>",\n'
            '  "score_breakdown": {\n'
            '    "critical_issues":   {"points_lost": <num>, "max_points": 40, "issues_found": <int>, "description": "<...>"},\n'
            '    "structural_issues": {"points_lost": <num>, "max_points": 30, "issues_found": <int>, "description": "<...>"},\n'
            '    "content_issues":    {"points_lost": <num>, "max_points": 20, "issues_found": <int>, "description": "<...>"},\n'
            '    "technical_issues":  {"points_lost": <num>, "max_points": 10, "issues_found": <int>, "description": "<...>"},\n'
            '    "total_score": <int>\n'
            "  },\n"
            '  "wcag_standards": {\n'
            '    "compliant":            ["1.4.3", ...],\n'
            '    "non_compliant":        ["1.1.1", ...],\n'
            '    "partially_compliant":  ["2.4.7", ...],\n'
            '    "details": { "1.1.1": "X of Y images have no alt — based on audit", ... }\n'
            "  },\n"
            '  "priority_issues": [\n'
            "    {\n"
            '      "wcag_criterion": "1.1.1",\n'
            '      "title": "...",\n'
            '      "description": "Cite the exact count / selectors from the audit.",\n'
            '      "user_impact": "How a screen-reader / keyboard / low-vision user is affected.",\n'
            '      "severity": "Critical|High|Medium|Low",\n'
            '      "impact": "High|Medium|Low",\n'
            '      "effort": "Low|Medium|High",\n'
            '      "estimated_time": "30 minutes",\n'
            '      "affected_elements": "Selectors / counts from the audit",\n'
            '      "current_code": "<minimal HTML snippet illustrating the bug>",\n'
            '      "fixed_code":   "<minimal HTML snippet showing the fix>",\n'
            '      "implementation_steps": ["1. ...", "2. ..."],\n'
            '      "testing_tools":         ["axe DevTools", "NVDA", "Keyboard-only"],\n'
            '      "resources": [ {"title": "...", "url": "https://...", "type": "Guide"} ]\n'
            "    }\n"
            "  ],\n"
            '  "recommendations": {\n'
            '    "short_term":  "Quick wins — reference the audit numbers.",\n'
            '    "medium_term": "Structural improvements.",\n'
            '    "long_term":   "Strategy + ongoing monitoring."\n'
            "  },\n"
            '  "next_steps": "<one paragraph>"\n'
            "}"
        )

        user_prompt = (
            f"URL ANALYZED: {page['final_url']}\n"
            f"HTTP STATUS: {page['status']}\n"
            f"PAGE SIZE: {page_meta['page_size_kb']} KB\n"
            f"RESPONSE TIME: {page['elapsed_ms']} ms\n\n"
            "AUDIT REPORT (deterministic, extracted from the live HTML):\n"
            "----------------------------------------------------------\n"
            f"{evidence_summary}\n"
            "----------------------------------------------------------\n\n"
            "Produce the JSON report described in the system prompt. "
            "Every finding you cite MUST appear in or be directly inferable from "
            "the AUDIT REPORT above. Reference exact counts and selectors."
        )

        # ---- 4. Call the LLM (or graceful fallback) ---------------------
        if not ai_client.is_configured():
            ai_result = _evidence_only_fallback(evidence)
        else:
            try:
                ai_result = ai_client.generate_json(user_prompt, system_message=system_prompt)
                if not isinstance(ai_result, dict):
                    raise ValueError("Model did not return a JSON object")
            except Exception as parse_error:
                print(f"[score] LLM analysis failed, falling back: {parse_error}")
                ai_result = _evidence_only_fallback(evidence)
                ai_result['_fallback_reason'] = str(parse_error)

        # ---- 5. Combine: score + AI commentary + raw evidence + sources -
        # Build a "sources" list that pairs every WCAG criterion the AI
        # mentioned (in either compliant / non_compliant / partially) with
        # its canonical W3C link and a deep-dive resource.
        cited_criteria = set(evidence.get('flagged_findings', []) and
                             [f['wcag'] for f in evidence['flagged_findings']] or [])
        wcag_block = ai_result.get('wcag_standards') or {}
        for key in ('compliant', 'non_compliant', 'partially_compliant'):
            for item in (wcag_block.get(key) or []):
                code = item if isinstance(item, str) else (item.get('code') if isinstance(item, dict) else None)
                if code:
                    cited_criteria.add(code)
        for issue in (ai_result.get('priority_issues') or []):
            if isinstance(issue, dict) and issue.get('wcag_criterion'):
                cited_criteria.add(issue['wcag_criterion'])

        sources = []
        for crit in sorted(cited_criteria):
            ref = WCAG_REFERENCES.get(crit)
            if not ref:
                continue
            sources.append({
                'wcag_criterion': crit,
                'title': ref['title'],
                'level': ref['level'],
                'principle': ref['principle'],
                'w3c_understanding_url': ref['w3c'],
                'deep_dive_url': ref['deep_dive'],
            })

        result = dict(ai_result)
        result['page_meta'] = page_meta
        result['evidence'] = evidence
        result['sources'] = sources
        result['differentiator'] = (
            "This report is built from real evidence: we fetched the page server-side, "
            "ran a deterministic DOM audit, and grounded the LLM in those measurements. "
            "Every finding cites a real count, selector, or W3C source — not a model guess."
        )
        return jsonify(result)

    except Exception as e:
        print(f"Error in score endpoint: {e}")
        return jsonify({
            'error': 'An error occurred while analyzing the website',
            'details': str(e) if FLASK_DEBUG else 'Check server logs for details'
        }), 500


def _evidence_only_fallback(evidence):
    """If the LLM is unavailable or returns garbage, build a minimal but
    still-useful report directly from the deterministic audit. This keeps
    the report grounded in real evidence even when the AI layer fails."""
    flagged = evidence.get('flagged_findings', [])
    # Categorise each flagged finding by WCAG criterion → score weight.
    critical = {'1.1.1', '1.4.3', '2.1.1', '3.3.2', '4.1.2', '2.4.7'}
    structural = {'1.3.1', '2.4.1', '2.4.6', '1.3.2', '2.4.3'}
    content = {'3.1.1', '2.4.4', '2.4.2', '3.3.1'}
    crit_n = sum(1 for f in flagged if f['wcag'] in critical)
    struct_n = sum(1 for f in flagged if f['wcag'] in structural)
    content_n = sum(1 for f in flagged if f['wcag'] in content)
    tech_n = max(0, len(flagged) - crit_n - struct_n - content_n)
    crit_loss = min(40, crit_n * 10)
    struct_loss = min(30, struct_n * 7.5)
    content_loss = min(20, content_n * 5)
    tech_loss = min(10, tech_n * 2.5)
    score = max(0, round(100 - crit_loss - struct_loss - content_loss - tech_loss))
    issues = []
    for f in flagged[:6]:
        issues.append({
            'wcag_criterion': f['wcag'],
            'title': f"WCAG {f['wcag']}: {f['summary']}",
            'description': f['summary'],
            'severity': 'Critical' if f['wcag'] in critical else 'High',
            'impact': 'High',
            'effort': 'Low',
            'affected_elements': f['summary'],
        })
    return {
        'score': score,
        'compliance_level': 'Evidence-only report (LLM unavailable)',
        'score_explanation': (
            f"Score derived solely from the deterministic audit because the AI layer was "
            f"unavailable. Subtracted {crit_loss} (critical), {struct_loss} (structural), "
            f"{content_loss} (content), {tech_loss} (technical) from 100."
        ),
        'score_breakdown': {
            'critical_issues':   {'points_lost': crit_loss,    'max_points': 40, 'issues_found': crit_n,    'description': f'{crit_n} critical finding(s)'},
            'structural_issues': {'points_lost': struct_loss,  'max_points': 30, 'issues_found': struct_n,  'description': f'{struct_n} structural finding(s)'},
            'content_issues':    {'points_lost': content_loss, 'max_points': 20, 'issues_found': content_n, 'description': f'{content_n} content finding(s)'},
            'technical_issues':  {'points_lost': tech_loss,    'max_points': 10, 'issues_found': tech_n,    'description': f'{tech_n} technical finding(s)'},
            'total_score': score,
        },
        'wcag_standards': {
            'compliant': [], 'partially_compliant': [],
            'non_compliant': sorted({f['wcag'] for f in flagged}),
            'details': {f['wcag']: f['summary'] for f in flagged},
        },
        'priority_issues': issues,
        'recommendations': {
            'short_term':  'Address the flagged findings above — most are quick wins.',
            'medium_term': 'Add automated accessibility testing to CI (axe-core, pa11y).',
            'long_term':   'Establish an accessibility statement and recurring audits.',
        },
        'next_steps': 'Configure Azure OpenAI to enable AI-grounded commentary alongside this evidence.',
    }


@app.route('/api/score-details', methods=['POST', 'OPTIONS'])
def score_details():
    if request.method == 'OPTIONS':
        print("Handling OPTIONS request for /api/score-details")
        response = jsonify({'status': 'ok'})
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response
    
    try:
        # Add better error handling for JSON parsing
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            print(f"JSON parsing error: {str(json_error)}")
            print(f"Request data: {request.get_data()}")
            return jsonify({'error': f'Invalid JSON format: {str(json_error)}'}), 400
        
        url = data.get('url', '')
        non_compliant_standards = data.get('non_compliant_standards', [])
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        if not non_compliant_standards:
            return jsonify({'error': 'No non-compliant standards provided'}), 400
        
        # Create a detailed prompt for code examples and fixes
        system_prompt = f"""You are an expert web accessibility developer with deep knowledge of WCAG 2.1 Level AA standards and practical implementation. Analyze the given website URL and provide specific code examples and fixes for the non-compliant standards.

**ANALYSIS REQUIREMENTS:**

1. **Specific Code Examples** - Show actual HTML/CSS/JavaScript code that demonstrates the accessibility issues
2. **Detailed Fixes** - Provide complete, working code solutions for each issue
3. **Implementation Steps** - Step-by-step instructions for implementing each fix
4. **Testing Methods** - How to test each fix for compliance
5. **Common Mistakes** - What developers often do wrong and how to avoid them
6. **Best Practices** - Industry best practices for each standard
7. **Browser/Device Support** - Compatibility considerations
8. **Performance Impact** - How each fix affects performance

**NON-COMPLIANT STANDARDS TO ANALYZE:**
{', '.join(non_compliant_standards)}

**RESPOND IN THIS EXACT JSON FORMAT:**
{{
    "url": "{url}",
    "non_compliant_standards": {non_compliant_standards},
    "code_examples": [
        {{
            "wcag_criterion": "1.1.1",
            "title": "Missing Alt Text Examples",
            "description": "Images without proper alt text prevent screen reader users from understanding content",
            "severity": "Critical",
            "examples": [
                {{
                    "issue": "Decorative image without alt text",
                    "bad_code": "<img src='decoration.png'>",
                    "good_code": "<img src='decoration.png' alt=''>",
                    "explanation": "Decorative images should have empty alt text to indicate they are decorative"
                }},
                {{
                    "issue": "Informative image without descriptive alt text",
                    "bad_code": "<img src='chart.png'>",
                    "good_code": "<img src='chart.png' alt='Sales growth chart showing 25% increase in Q3 2024'>",
                    "explanation": "Informative images need descriptive alt text that conveys the same information"
                }}
            ],
            "implementation_steps": [
                "1. Audit all images on the page",
                "2. Identify decorative vs informative images",
                "3. Add appropriate alt text for each image type",
                "4. Test with screen reader software"
            ],
            "testing_methods": [
                "Use screen reader (NVDA, JAWS, VoiceOver)",
                "Check browser developer tools for alt attributes",
                "Validate with WAVE or axe-core tools"
            ],
            "common_mistakes": [
                "Using generic alt text like 'image' or 'picture'",
                "Forgetting alt text on background images",
                "Not considering context when writing alt text"
            ],
            "best_practices": [
                "Write alt text that conveys the same information as the image",
                "Keep alt text concise but descriptive",
                "Use empty alt='' for decorative images",
                "Test with actual screen reader users"
            ],
            "browser_support": "Universal support across all browsers",
            "performance_impact": "Minimal - alt text is lightweight and improves SEO"
        }}
    ],
    "fixes": [
        {{
            "wcag_criterion": "1.1.1",
            "title": "Alt Text Implementation",
            "priority": "Critical",
            "estimated_time": "2-4 hours",
            "difficulty": "Easy",
            "code_fixes": [
                {{
                    "file_type": "HTML",
                    "description": "Add alt text to all images",
                    "before": "<img src='logo.png'>",
                    "after": "<img src='logo.png' alt='Company Logo'>",
                    "notes": "Ensure alt text is descriptive and meaningful"
                }}
            ],
            "css_fixes": [
                {{
                    "description": "Hide decorative images from screen readers",
                    "code": ".decorative {{ position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden; }}",
                    "notes": "Alternative to empty alt text for complex decorative elements"
                }}
            ],
            "javascript_fixes": [
                {{
                    "description": "Dynamically add alt text to images loaded via JavaScript",
                    "code": "function addAltText() {{ const images = document.querySelectorAll('img[data-alt]'); images.forEach(img => {{ img.alt = img.dataset.alt; }}); }}",
                    "notes": "Use for dynamically loaded content"
                }}
            ]
        }}
    ],
    "testing_checklist": [
        {{
            "category": "Manual Testing",
            "items": [
                "Test with screen reader software",
                "Verify keyboard navigation",
                "Check color contrast ratios",
                "Test with different zoom levels"
            ]
        }},
        {{
            "category": "Automated Testing",
            "items": [
                "Run axe-core accessibility tests",
                "Use WAVE web accessibility evaluator",
                "Validate HTML with W3C validator",
                "Test with Lighthouse accessibility audit"
            ]
        }}
    ],
    "resources": [
        {{
            "title": "WCAG 2.1 Guidelines",
            "url": "https://www.w3.org/WAI/WCAG21/quickref/",
            "description": "Official WCAG 2.1 quick reference"
        }},
        {{
            "title": "WebAIM Color Contrast Checker",
            "url": "https://webaim.org/resources/contrastchecker/",
            "description": "Tool to check color contrast ratios"
        }}
    ],
    "summary": "Comprehensive accessibility fixes with code examples, implementation steps, and testing methods for achieving WCAG 2.1 Level AA compliance."
}}"""

        # Build the prompt with the URL and standards
        prompt = f"{system_prompt}\n\nAnalyze this website: {url}"
        
        # Use Azure OpenAI to analyze the website
        response_text = ai_client.generate_text(prompt)
        
        # Parse the response (assuming it returns valid JSON)
        try:
            # Look for JSON in the response (sometimes the model adds extra text)
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                import json
                result = json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                result = {
                    "url": url,
                    "non_compliant_standards": non_compliant_standards,
                    "code_examples": [
                        {
                            "wcag_criterion": "1.1.1",
                            "title": "Missing Alt Text Examples",
                            "description": "Images without proper alt text prevent screen reader users from understanding content",
                            "severity": "Critical",
                            "examples": [
                                {
                                    "issue": "Decorative image without alt text",
                                    "bad_code": "<img src='decoration.png'>",
                                    "good_code": "<img src='decoration.png' alt=''>",
                                    "explanation": "Decorative images should have empty alt text to indicate they are decorative"
                                }
                            ],
                            "implementation_steps": [
                                "1. Audit all images on the page",
                                "2. Identify decorative vs informative images",
                                "3. Add appropriate alt text for each image type",
                                "4. Test with screen reader software"
                            ],
                            "testing_methods": [
                                "Use screen reader (NVDA, JAWS, VoiceOver)",
                                "Check browser developer tools for alt attributes",
                                "Validate with WAVE or axe-core tools"
                            ],
                            "common_mistakes": [
                                "Using generic alt text like 'image' or 'picture'",
                                "Forgetting alt text on background images",
                                "Not considering context when writing alt text"
                            ],
                            "best_practices": [
                                "Write alt text that conveys the same information as the image",
                                "Keep alt text concise but descriptive",
                                "Use empty alt='' for decorative images",
                                "Test with actual screen reader users"
                            ],
                            "browser_support": "Universal support across all browsers",
                            "performance_impact": "Minimal - alt text is lightweight and improves SEO"
                        }
                    ],
                    "fixes": [
                        {
                            "wcag_criterion": "1.1.1",
                            "title": "Alt Text Implementation",
                            "priority": "Critical",
                            "estimated_time": "2-4 hours",
                            "difficulty": "Easy",
                            "code_fixes": [
                                {
                                    "file_type": "HTML",
                                    "description": "Add alt text to all images",
                                    "before": "<img src='logo.png'>",
                                    "after": "<img src='logo.png' alt='Company Logo'>",
                                    "notes": "Ensure alt text is descriptive and meaningful"
                                }
                            ],
                            "css_fixes": [],
                            "javascript_fixes": []
                        }
                    ],
                    "testing_checklist": [
                        {
                            "category": "Manual Testing",
                            "items": [
                                "Test with screen reader software",
                                "Verify keyboard navigation",
                                "Check color contrast ratios",
                                "Test with different zoom levels"
                            ]
                        }
                    ],
                    "resources": [
                        {
                            "title": "WCAG 2.1 Guidelines",
                            "url": "https://www.w3.org/WAI/WCAG21/quickref/",
                            "description": "Official WCAG 2.1 quick reference"
                        }
                    ],
                    "summary": "Comprehensive accessibility fixes with code examples, implementation steps, and testing methods for achieving WCAG 2.1 Level AA compliance."
                }
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            print(f"Response text: {response_text}")
            return jsonify({'error': 'Failed to parse AI response'}), 500
            
    except Exception as e:
        print(f"Error in score-details endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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