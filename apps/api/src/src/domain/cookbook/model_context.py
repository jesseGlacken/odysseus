"""
model_context.py

Query and cache model context window sizes from OpenAI-compatible APIs.
Provides token estimation for context usage tracking.

Moved from src/model_context.py to src/domain/cookbook/model_context.py (ODY-19 / P2.2).
The original location keeps a backward-compat shim.
"""

import ipaddress
import logging
import sys
from typing import Dict, List, Optional, Tuple

from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}
_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _in_tailscale_range(host: str) -> bool:
    try:
        return ipaddress.ip_address(host) in _TAILSCALE_CGNAT
    except ValueError:
        return False


def _is_private_ip_literal(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in network for network in _PRIVATE_NETWORKS)


def _normalize_base_for_compare(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    for suffix in ("/chat/completions", "/models", "/completions", "/v1/messages"):
        if url.endswith(suffix):
            url = url[: -len(suffix)].rstrip("/")
    return url


def _configured_endpoint_kind(url: str) -> Optional[str]:
    target = _normalize_base_for_compare(url)
    if not target:
        return None
    if "core.database" not in sys.modules:
        return None
    try:
        from core.database import SessionLocal, ModelEndpoint
        db = SessionLocal()
        try:
            rows = db.query(ModelEndpoint).filter(ModelEndpoint.is_enabled == True).all()
            for ep in rows:
                base = _normalize_base_for_compare(getattr(ep, "base_url", "") or "")
                if not base:
                    continue
                if target != base and not target.startswith(base + "/"):
                    continue
                kind = (getattr(ep, "endpoint_kind", None) or "auto").strip().lower()
                if kind in ("local", "api", "proxy"):
                    return kind
                if getattr(ep, "api_key", None):
                    parsed = urlparse(base)
                    host = (parsed.hostname or "").lower()
                    path = (parsed.path or "").rstrip("/")
                    if parsed.port != 11434 and "ollama" not in host and (path.endswith("/v1") or "/openai" in path):
                        return "proxy"
                return "auto"
        finally:
            db.close()
    except Exception:
        return None


def is_local_endpoint(url: str) -> bool:
    kind = _configured_endpoint_kind(url)
    if kind in ("api", "proxy"):
        return False
    if kind == "local":
        return True
    try:
        host = urlparse(url).hostname or ""
        return host in _LOCAL_HOSTS or _is_private_ip_literal(host) or _in_tailscale_range(host)
    except Exception:
        return False


DEFAULT_CONTEXT = 128000
REQUEST_TIMEOUT = 5

KNOWN_CONTEXT_WINDOWS = {
    'claude-sonnet-4-5': 200000, 'claude-sonnet-4-6': 200000, 'claude-sonnet-4': 200000,
    'claude-opus-4': 200000, 'claude-haiku-4': 200000, 'claude-haiku-3-5': 200000,
    'claude-3-5-sonnet': 200000, 'claude-3-5-haiku': 200000, 'claude-3-opus': 200000,
    'claude-3-sonnet': 200000, 'claude-3-haiku': 200000,
    'gpt-5': 400000, 'gpt-4.1': 1047576, 'gpt-4.1-mini': 1047576, 'gpt-4.1-nano': 1047576,
    'gpt-4o': 128000, 'gpt-4o-mini': 128000, 'gpt-4-turbo': 128000, 'gpt-4': 8192,
    'gpt-3.5-turbo': 16385, 'o1': 200000, 'o1-mini': 128000, 'o1-pro': 200000,
    'o3': 200000, 'o3-mini': 200000, 'o4-mini': 200000,
    'deepseek-chat': 64000, 'deepseek-coder': 64000, 'deepseek-reasoner': 64000,
    'deepseek-r1': 64000, 'deepseek-v3': 64000, 'deepseek-v2': 64000,
    'gemini-2.5-pro': 1048576, 'gemini-2.5-flash': 1048576, 'gemini-2.0-flash': 1048576,
    'gemini-1.5-pro': 1048576, 'gemini-1.5-flash': 1048576,
    'gemma-4': 262144, 'gemma-3': 128000, 'gemma-2': 8192,
    'mistral-large': 128000, 'mistral-medium': 32000, 'mistral-small': 32000,
    'mistral-nemo': 128000, 'mistral-7b': 32000, 'mixtral': 32000,
    'codestral': 32000, 'pixtral': 128000,
    'grok-4': 131072, 'grok-3': 131072, 'grok-2': 131072,
    'llama-4': 1048576, 'llama-3.3': 131072, 'llama-3.2': 131072,
    'llama-3.1': 131072, 'llama-3': 131072,
    'qwen3': 131072, 'qwen2.5': 131072, 'qwen2': 32768, 'qwq': 32768,
    'command-r-plus': 128000, 'command-r': 128000, 'command-a': 256000,
    'sonar-pro': 200000, 'sonar': 128000,
    'minimax': 1000000, 'moonshot': 128000, 'kimi': 128000,
    'phi-4': 16000, 'phi-3': 128000, 'nemotron': 131072,
    'yi-large': 32768, 'yi-1.5': 16384, 'yi-lightning': 16384,
    'hermes': 131072, 'nous-hermes': 131072,
    'mimo-v2.5-pro': 1048576, 'mimo-v2.5': 1048576,
    'dolphin': 32768, 'mythomax': 4096, 'wizard': 32768,
    'openchat': 8192, 'solar': 32768,
}

_context_cache: Dict[Tuple[str, str], Tuple[int, bool]] = {}


def _get_context_length_cached(endpoint_url: str, model: str) -> Tuple[int, bool]:
    configured_kind = _configured_endpoint_kind(endpoint_url)
    is_local = is_local_endpoint(endpoint_url)
    cache_key = (endpoint_url, model)
    if not is_local and cache_key in _context_cache:
        return _context_cache[cache_key]
    ctx, known = _query_context_length(endpoint_url, model)
    if not is_local and (ctx != DEFAULT_CONTEXT or configured_kind in ("api", "proxy")):
        _context_cache[cache_key] = (ctx, known)
    logger.info(f"Context length for {model}: {ctx}")
    return ctx, known


def get_context_length(endpoint_url: str, model: str) -> int:
    return _get_context_length_cached(endpoint_url, model)[0]


def get_context_length_known(endpoint_url: str, model: str) -> Tuple[int, bool]:
    return _get_context_length_cached(endpoint_url, model)


def budget_context_for_model(endpoint_url: str, model: str, *, fallback: int = 0) -> int:
    try:
        ctx, known = get_context_length_known(endpoint_url, model)
        return ctx if known else 0
    except Exception:
        return fallback


def _lookup_known(model: str) -> Optional[int]:
    name = model.lower()
    basename = name.split("/")[-1] if "/" in name else name
    basename = basename.split(":")[0]
    best_key: Optional[str] = None
    best_ctx: Optional[int] = None
    for key, ctx in KNOWN_CONTEXT_WINDOWS.items():
        if key in basename or key in name:
            if best_key is None or len(key) > len(best_key):
                best_key, best_ctx = key, ctx
    return best_ctx


def _model_ctx_from_entry(m: dict) -> Optional[int]:
    if not isinstance(m, dict):
        return None
    for field in ("context_length", "context_window", "max_model_len", "max_context_length", "max_seq_len"):
        val = m.get(field)
        if val and isinstance(val, (int, float)) and val > 0:
            return int(val)
    meta = m.get("meta") or m.get("model_extra") or {}
    if isinstance(meta, dict):
        for field in ("n_ctx", "context_length", "context_window", "max_model_len"):
            val = meta.get(field)
            if val and isinstance(val, (int, float)) and val > 0:
                return int(val)
    return None


_catalog_ctx_cache: Dict[str, Dict[str, int]] = {}


def _proxy_catalog_context(endpoint_url: str, model: str) -> Optional[int]:
    cat = _catalog_ctx_cache.get(endpoint_url)
    if cat is None:
        from src.endpoint_resolver import build_models_url
        try:
            r = httpx.get(build_models_url(endpoint_url), timeout=REQUEST_TIMEOUT)
        except Exception as e:
            logger.debug(f"Failed to fetch proxy catalog for context length: {e}")
            return None
        if not r.is_success:
            return None
        cat = {}
        try:
            for m in (r.json().get("data") or []):
                mid = m.get("id") if isinstance(m, dict) else None
                ctx = _model_ctx_from_entry(m) if mid else None
                if mid and ctx:
                    cat[mid] = ctx
        except Exception as e:
            logger.debug(f"Failed to parse proxy catalog for context length: {e}")
            return None
        _catalog_ctx_cache[endpoint_url] = cat
    if model in cat:
        return cat[model]
    base = model.split("/")[-1]
    for mid, ctx in cat.items():
        if mid.split("/")[-1] == base:
            return ctx
    return None


def _query_context_length(endpoint_url: str, model: str) -> Tuple[int, bool]:
    known = _lookup_known(model)
    api_ctx = None
    configured_kind = _configured_endpoint_kind(endpoint_url)

    if configured_kind in ("api", "proxy"):
        if known:
            logger.info(f"Using known context window for {model}: {known}")
            return known, True
        api_ctx = _proxy_catalog_context(endpoint_url, model)
        if api_ctx:
            logger.info(f"Proxy catalog reports context window for {model}: {api_ctx}")
            return api_ctx, True
        return DEFAULT_CONTEXT, False

    if is_local_endpoint(endpoint_url):
        try:
            base = endpoint_url.split("/v1")[0] if "/v1" in endpoint_url else endpoint_url.rsplit("/", 1)[0]
            r = httpx.get(f"{base}/slots", timeout=REQUEST_TIMEOUT)
            if r.is_success:
                slots = r.json()
                if isinstance(slots, list) and slots:
                    n_ctx = slots[0].get("n_ctx")
                    if n_ctx and isinstance(n_ctx, int) and n_ctx > 0:
                        logger.info(f"llama.cpp /slots reports n_ctx={n_ctx} for {model}")
                        return n_ctx, True
        except Exception:
            pass

    from src.copilot import is_copilot_base
    if is_copilot_base(endpoint_url):
        if known:
            logger.info(f"Using known context window for {model}: {known}")
            return known, True
        return DEFAULT_CONTEXT, False

    from src.endpoint_resolver import build_models_url
    models_url = build_models_url(endpoint_url)
    try:
        r = httpx.get(models_url, timeout=REQUEST_TIMEOUT)
        if r.is_success:
            data = r.json()
            models_list = data.get("data") or []
            for m in models_list:
                mid = m.get("id", "")
                if mid == model or mid.split("/")[-1] == model.split("/")[-1]:
                    api_ctx = _model_ctx_from_entry(m)
                    break
    except Exception as e:
        logger.debug(f"Failed to query context length for {model}: {e}")

    if api_ctx and known:
        _is_local = is_local_endpoint(endpoint_url)
        if _is_local and api_ctx < known:
            logger.info(f"Local endpoint reports {api_ctx} for {model} (known max: {known}) — using API value")
            return api_ctx, True
        result = max(api_ctx, known)
        if api_ctx < known:
            logger.info(f"API reported {api_ctx} for {model}, using known {known} instead")
        return result, True
    if api_ctx:
        return api_ctx, True
    if known:
        logger.info(f"Using known context window for {model}: {known}")
        return known, True
    return DEFAULT_CONTEXT, False


def estimate_tokens(messages: List[Dict]) -> int:
    total = 0
    for msg in messages:
        total += 4
        content = msg.get("content", "")
        if isinstance(content, str):
            total += int(len(content) * 0.3)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    total += int(len(item.get("text", "")) * 0.3)
        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") if isinstance(tc.get("function"), dict) else tc
                name = fn.get("name", "") or ""
                args = fn.get("arguments", "") or ""
                if not isinstance(args, str):
                    args = str(args)
                total += 4
                total += int((len(str(name)) + len(args)) * 0.3)
    return total
