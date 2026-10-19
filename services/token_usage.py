"""Token budget helpers: clamp output tokens and normalise usage numbers.

Each report must stay under 100,000 tokens in total (prompt + output).
"""
import os

TOKEN_LIMIT = 100_000
DEFAULT_MAX_OUTPUT = 16_000
MIN_OUTPUT = 1_000


def estimate_tokens(text):
    """Rough, conservative token estimate (about 3 characters per token)."""
    return len(text or "") // 3 + 1


def max_output_tokens(prompt_text):
    """AI_MAX_OUTPUT_TOKENS (default 16000), clamped so prompt + output < 100k."""
    try:
        wanted = int(os.environ.get("AI_MAX_OUTPUT_TOKENS") or DEFAULT_MAX_OUTPUT)
    except ValueError:
        wanted = DEFAULT_MAX_OUTPUT
    room = TOKEN_LIMIT - estimate_tokens(prompt_text) - 500  # safety margin
    return max(MIN_OUTPUT, min(wanted, room))


def _int(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 0 <= n <= 10_000_000 else None


def normalise_usage(raw):
    """Return {prompt_tokens, output_tokens, total_tokens, limit} or None."""
    if not isinstance(raw, dict):
        return None
    prompt = _int(raw.get("prompt_tokens"))
    output = _int(raw.get("output_tokens"))
    total = _int(raw.get("total_tokens"))
    if total is None and prompt is not None and output is not None:
        total = prompt + output
    if total is None:
        return None
    return {"prompt_tokens": prompt, "output_tokens": output, "total_tokens": total, "limit": TOKEN_LIMIT}


def from_gemini(response):
    """Read Gemini usage_metadata safely (fields may be missing)."""
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return None
    prompt = getattr(meta, "prompt_token_count", None)
    out = (getattr(meta, "candidates_token_count", None) or 0) + (getattr(meta, "thoughts_token_count", None) or 0)
    return normalise_usage({
        "prompt_tokens": prompt,
        "output_tokens": out or None,
        "total_tokens": getattr(meta, "total_token_count", None),
    })
