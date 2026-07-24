# src/domain/llm/endpoint_resolver.py
"""Unified endpoint resolution for all backend services.

Moved from src/endpoint_resolver.py to src/domain/llm/endpoint_resolver.py (ODY-19 / P2.2).
The original location keeps a backward-compat shim.

Import change: `from src.llm_core import ...` → relative import (same domain).
"""

import json
import logging
import socket
import subprocess
from typing import Optional, Tuple, Dict
from urllib.parse import urlparse, urlunparse

from core.database import SessionLocal, ModelEndpoint
# llm_core.py is large and deferred to ODY-70; import via the legacy flat path.
# When llm_core.py moves to domain/llm/, change this to a relative import.
from src.llm_core import _detect_provider, _host_match, _is_kimi_code_url, KIMI_CODE_USER_AGENT, _ollama_api_root

logger = logging.getLogger(__name__)

_NON_CHAT_MODEL = (
    "text-embedding", "embedding", "tts-", "whisper", "dall-e",
    "moderation", "rerank", "reranker", "clip", "stable-diffusion",
)


def _first_chat_model(models) -> Optional[str]:
    for m in (models or []):
        if not any(p in str(m).lower() for p in _NON_CHAT_MODEL):
            return m
    return (models[0] if models else None)


def _endpoint_cached_models(ep) -> list:
    raw = getattr(ep, "cached_models", None) or getattr(ep, "models", None)
    if not raw:
        return []
    try:
        models = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []
    return models if isinstance(models, list) else []


def _endpoint_pinned_models(ep) -> list:
    raw = getattr(ep, "pinned_models", None)
    if not raw:
        return []
    try:
        models = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []
    return models if isinstance(models, list) else []


def _is_mlx_deepseek_v4_repo_id(model_id: str) -> bool:
    return "mlx-community/deepseek-v4" in str(model_id or "").lower()


def _is_mlx_deepseek_v4_shim_id(model_id: str) -> bool:
    return "/.cache/odysseus/mlx-shims/deepseek-v4" in str(model_id or "").lower()


def _filter_mlx_deepseek_v4_repo_when_shimmed(model_ids) -> list:
    ids = list(model_ids or [])
    has_shim = any(_is_mlx_deepseek_v4_shim_id(m) for m in ids)
    if not has_shim:
        return ids
    return [m for m in ids if not _is_mlx_deepseek_v4_repo_id(m)]


def _endpoint_hidden_models(ep) -> set:
    raw = getattr(ep, "hidden_models", None)
    if not raw:
        return set()
    try:
        hidden = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return set()
    return set(hidden) if isinstance(hidden, list) else set()


def _endpoint_enabled_models(ep) -> list:
    hidden = _endpoint_hidden_models(ep)
    merged = []
    seen = set()
    for m in [*_endpoint_cached_models(ep), *_endpoint_pinned_models(ep)]:
        if not isinstance(m, str) or not m or m in seen:
            continue
        seen.add(m)
        merged.append(m)
    merged = _filter_mlx_deepseek_v4_repo_when_shimmed(merged)
    return [m for m in merged if m not in hidden]


def resolve_endpoint_runtime(ep, owner: Optional[str] = None) -> Tuple[str, Optional[str]]:
    base = normalize_base(getattr(ep, "base_url", "") or "")
    api_key = getattr(ep, "api_key", None)
    auth_id = getattr(ep, "provider_auth_id", None)
    if auth_id:
        from src.chatgpt_subscription import resolve_runtime_credentials
        creds = resolve_runtime_credentials(auth_id, owner=owner)
        base = normalize_base(creds.get("base_url") or base)
        api_key = creds.get("api_key")
    return base, api_key


_tailscale_cache: Dict[str, Optional[str]] = {}


def _resolve_tailscale_host(hostname: str) -> Optional[str]:
    if hostname in _tailscale_cache:
        return _tailscale_cache[hostname]
    try:
        socket.getaddrinfo(hostname, None, socket.AF_INET)
        _tailscale_cache[hostname] = None
        return None
    except socket.gaierror:
        pass
    try:
        result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            import json as _json
            data = _json.loads(result.stdout)
            peers = data.get("Peer", {})
            for _id, peer in peers.items():
                peer_name = (peer.get("HostName") or "").lower()
                dns_name = (peer.get("DNSName") or "").split(".")[0].lower()
                if peer_name == hostname.lower() or dns_name == hostname.lower():
                    addrs = peer.get("TailscaleIPs", [])
                    if addrs:
                        ip = addrs[0]
                        logger.info(f"Resolved '{hostname}' via Tailscale → {ip}")
                        _tailscale_cache[hostname] = ip
                        return ip
    except Exception as e:
        logger.debug(f"Tailscale resolution failed for '{hostname}': {e}")
    _tailscale_cache[hostname] = None
    return None


def resolve_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return url
    ip = _resolve_tailscale_host(hostname)
    if ip:
        netloc = ip
        if parsed.port:
            netloc = f"{ip}:{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))
    return url


def normalize_base(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    for suffix in ["/models", "/chat/completions", "/completions", "/v1/messages", "/responses"]:
        if url.endswith(suffix):
            url = url[: -len(suffix)].rstrip("/")
    for suffix in ["/chat", "/tags", "/generate"]:
        if url.endswith("/api" + suffix):
            url = url[: -len(suffix)].rstrip("/")
    return url


def _validated_endpoint_base(url: str) -> str:
    base = (url or "").strip().rstrip("/")
    if "?" in base or "#" in base:
        raise ValueError("Endpoint base URL must not include query or fragment")
    return urlunparse(urlparse(base)._replace(query="", fragment="")).rstrip("/")


def _prepare_endpoint_base(base: str) -> str:
    base = _validated_endpoint_base(normalize_base(base))
    return _validated_endpoint_base(normalize_base(resolve_url(base)))


def _append_endpoint_path(base: str, suffix: str) -> str:
    parsed = urlparse(base)
    current = (parsed.path or "").rstrip("/")
    extra = "/" + suffix.lstrip("/")
    path = f"{current}{extra}" if current else extra
    return urlunparse(parsed._replace(path=path, query="", fragment=""))


def _pathless_host(base: str, host: str) -> bool:
    parsed = urlparse(base)
    return (parsed.hostname or "").lower() == host and not (parsed.path or "").strip("/")


def _anthropic_api_root(base: str) -> str:
    base = (base or "").strip().rstrip("/")
    if _host_match(base, "anthropic.com") and base.endswith("/v1"):
        return base[:-3].rstrip("/")
    return base


def build_chat_url(base: str) -> str:
    base = _prepare_endpoint_base(base)
    provider = _detect_provider(base)
    if provider == "anthropic":
        return _append_endpoint_path(_anthropic_api_root(base), "/v1/messages")
    if provider == "ollama":
        return _append_endpoint_path(_ollama_api_root(base), "/chat")
    if provider == "chatgpt-subscription":
        return _append_endpoint_path(base, "/responses")
    if _pathless_host(base, "api.openai.com"):
        base = _append_endpoint_path(base, "/v1")
    return _append_endpoint_path(base, "/chat/completions")


def build_models_url(base: str) -> Optional[str]:
    base = _prepare_endpoint_base(base)
    provider = _detect_provider(base)
    if provider == "anthropic":
        return _append_endpoint_path(_anthropic_api_root(base), "/v1/models")
    if provider == "ollama":
        return _append_endpoint_path(_ollama_api_root(base), "/tags")
    if provider == "chatgpt-subscription":
        return None
    parsed = urlparse(base)
    host = (parsed.hostname or "").lower()
    is_local = host in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
    uses_v1_models_by_default = is_local or host in {"api.deepseek.com", "api.openai.com"}
    if not parsed.path and uses_v1_models_by_default:
        base = _append_endpoint_path(base, "/v1")
    return _append_endpoint_path(base, "/models")


def build_headers(api_key: Optional[str], base: str) -> Dict[str, str]:
    provider = _detect_provider(base)
    headers: Dict[str, str] = {}
    if provider == "anthropic":
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        return headers
    if provider == "copilot":
        from src.copilot import copilot_headers
        return copilot_headers(api_key)
    if provider == "chatgpt-subscription":
        from src.chatgpt_subscription import chatgpt_headers
        return chatgpt_headers(api_key)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if provider == "openrouter":
        headers.setdefault("HTTP-Referer", "https://github.com/odysseus-dev/odysseus")
        headers.setdefault("X-OpenRouter-Title", "Odysseus")
    if _is_kimi_code_url(base):
        headers.setdefault("User-Agent", KIMI_CODE_USER_AGENT)
    return headers


def resolve_endpoint(
    setting_prefix: str,
    fallback_url: Optional[str] = None,
    fallback_model: Optional[str] = None,
    fallback_headers: Optional[Dict] = None,
    owner: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
    try:
        from src.settings import get_user_setting, load_settings
        settings = load_settings()
    except Exception:
        return fallback_url, fallback_model, fallback_headers

    owner_str = owner or ""
    def _stg(key: str) -> str:
        return (get_user_setting(key, owner_str, settings.get(key, "")) or "").strip()

    ep_id = _stg(f"{setting_prefix}_endpoint_id")
    model = _stg(f"{setting_prefix}_model")

    if not ep_id and setting_prefix not in ("utility", "default"):
        ep_id = _stg("utility_endpoint_id")
        model = _stg("utility_model")

    if not ep_id and fallback_url and fallback_model:
        return fallback_url, fallback_model, fallback_headers

    if not ep_id:
        ep_id = _stg("default_endpoint_id")
        model = _stg("default_model")

    if not ep_id:
        return fallback_url, fallback_model, fallback_headers

    db = SessionLocal()
    try:
        ep = db.query(ModelEndpoint).filter(ModelEndpoint.id == ep_id, ModelEndpoint.is_enabled == True)
        if owner:
            from src.auth_helpers import owner_filter
            ep = owner_filter(ep, ModelEndpoint, owner).first()
        else:
            ep = ep.first()
        if not ep:
            return fallback_url, fallback_model, fallback_headers
        try:
            base, api_key = resolve_endpoint_runtime(ep, owner=owner)
        except Exception as e:
            logger.warning("Could not resolve endpoint runtime credentials: %s", e)
            return fallback_url, fallback_model, fallback_headers
        chat_url = build_chat_url(base)
        headers = build_headers(api_key, base)
        if model and model in _endpoint_hidden_models(ep):
            model = ""
        if not model:
            model = _first_chat_model(_endpoint_enabled_models(ep)) or ""
        if not model and not fallback_model:
            logger.warning('[resolve_endpoint] no usable model (all models hidden or list empty)')
        return chat_url, model or fallback_model, headers
    except Exception as e:
        logger.debug(f"Could not resolve {setting_prefix} endpoint: {e}")
        return fallback_url, fallback_model, fallback_headers
    finally:
        db.close()


def resolve_endpoint_by_id(ep_id: str, model: Optional[str] = None, owner: Optional[str] = None) -> Optional[Tuple[str, str, Dict]]:
    if not ep_id:
        return None
    db = SessionLocal()
    try:
        q = db.query(ModelEndpoint).filter(ModelEndpoint.id == ep_id, ModelEndpoint.is_enabled == True)
        if owner:
            from src.auth_helpers import owner_filter
            q = owner_filter(q, ModelEndpoint, owner)
        ep = q.first()
        if not ep:
            return None
        try:
            base, api_key = resolve_endpoint_runtime(ep, owner=owner)
        except Exception as e:
            logger.warning("Could not resolve endpoint runtime credentials: %s", e)
            return None
        chat_url = build_chat_url(base)
        headers = build_headers(api_key, base)
        m = (model or "").strip()
        if m and m in _endpoint_hidden_models(ep):
            m = ""
        if not m:
            m = _first_chat_model(_endpoint_enabled_models(ep)) or ""
        if not m:
            return None
        return chat_url, m, headers
    except Exception as e:
        logger.debug(f"Could not resolve endpoint {ep_id}: {e}")
        return None
    finally:
        db.close()


def resolve_chat_fallback_candidates(owner: Optional[str] = None) -> list:
    return _resolve_fallback_candidates("default_model_fallbacks", owner=owner)


def resolve_utility_fallback_candidates(owner: Optional[str] = None) -> list:
    try:
        from src.settings import get_user_setting, load_settings
        settings = load_settings()
        utility_ep = (get_user_setting("utility_endpoint_id", owner or "", settings.get("utility_endpoint_id", "")) or "").strip()
        if not utility_ep:
            utility_chain = get_user_setting("utility_model_fallbacks", owner or "", settings.get("utility_model_fallbacks") or []) or []
            if utility_chain:
                return _resolve_fallback_candidates("utility_model_fallbacks", owner=owner)
            return _resolve_fallback_candidates("default_model_fallbacks", owner=owner)
    except Exception:
        pass
    return _resolve_fallback_candidates("utility_model_fallbacks", owner=owner)


def resolve_vision_fallback_candidates(owner: Optional[str] = None) -> list:
    return _resolve_fallback_candidates("vision_model_fallbacks", owner=owner)


def _resolve_fallback_candidates(setting_key: str, owner: Optional[str] = None) -> list:
    out = []
    try:
        from src.settings import get_user_setting, load_settings
        settings = load_settings()
        chain = get_user_setting(setting_key, owner or "", settings.get(setting_key) or []) or []
    except Exception:
        return out
    for entry in chain:
        if not isinstance(entry, dict):
            continue
        resolved = resolve_endpoint_by_id(entry.get("endpoint_id", ""), entry.get("model", ""), owner=owner)
        if resolved:
            out.append(resolved)
    return out
