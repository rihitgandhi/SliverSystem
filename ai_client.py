"""
Azure OpenAI client wrapper.

Centralizes all calls to Azure OpenAI so the rest of the application
does not need to know about the underlying SDK. Mirrors the small
subset of behaviour the codebase previously relied on from
``google.generativeai`` (text generation and image-aware generation).
"""

import os
import re
import json
import base64
from typing import Any, Optional

from openai import AzureOpenAI


# ---------------------------------------------------------------------------
# Configuration (read from environment / .env)
# ---------------------------------------------------------------------------
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', '').strip()
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '').strip()
AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', '').strip()
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview').strip()


def is_configured() -> bool:
    """Return True when the credentials needed to call Azure OpenAI exist."""
    return bool(AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT)


# Lazily-created singleton client -------------------------------------------------
_client: Optional[AzureOpenAI] = None


def get_client() -> AzureOpenAI:
    """Return a cached AzureOpenAI client.

    Raises a RuntimeError when the required configuration is missing so the
    caller can decide how to surface the problem (callers in ``app.py``
    typically check :func:`is_configured` first and fall back to a static
    response when it returns ``False``).
    """
    global _client
    if not is_configured():
        raise RuntimeError(
            "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT, "
            "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT."
        )
    if _client is None:
        _client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
    return _client


def generate_text(prompt: str, system_message: Optional[str] = None) -> str:
    """Generate a chat completion for a single prompt and return the text."""
    client = get_client()
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def generate_json(prompt: str, system_message: Optional[str] = None) -> Any:
    """Generate a chat completion that must return JSON, parse and return it.

    Tries Azure OpenAI's ``response_format={"type": "json_object"}`` first
    so the model is forced to return parseable JSON. Falls back to extracting
    the largest JSON-looking block from the text if the model doesn't support
    the parameter. Always returns a Python object (dict/list); raises
    ``ValueError`` only if no JSON can be recovered at all.
    """
    client = get_client()
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    text = ""
    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
    except Exception:
        # Older deployments may not support response_format; retry without it.
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
        )
        text = response.choices[0].message.content or ""

    return _coerce_json(text)


def _coerce_json(text: str) -> Any:
    """Best-effort: turn a model response string into a Python object."""
    if text is None:
        raise ValueError("Empty model response")
    cleaned = text.strip()

    # Strip ```json ... ``` fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # 1) Try the cleaned text directly
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2) Try the largest {...} block
    obj_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except Exception:
            pass

    # 3) Try the largest [...] block
    arr_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except Exception:
            pass

    raise ValueError(f"Model response is not valid JSON: {cleaned[:200]}...")


def generate_with_image(prompt: str, image_b64: str, mime_type: str = "image/jpeg") -> str:
    """Generate a chat completion that includes a base64-encoded image."""
    client = get_client()

    # Validate the base64 payload up-front so callers get a clean error if the
    # client supplied something that cannot be decoded.
    try:
        base64.b64decode(image_b64, validate=True)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid base64 image data: {exc}") from exc

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content or ""


def generate_json_with_image(
    prompt: str,
    image_b64: str,
    mime_type: str = "image/jpeg",
) -> Any:
    """JSON-returning variant of :func:`generate_with_image`."""
    client = get_client()

    try:
        base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image data: {exc}") from exc

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_b64}"
                    },
                },
            ],
        }
    ]

    text = ""
    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
    except Exception:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
        )
        text = response.choices[0].message.content or ""

    return _coerce_json(text)
