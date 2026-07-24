# src/domain/chat/chat_processor.py
"""Chat processor: context preface builder, RAG/memory retrieval, web search.

Moved from src/chat_processor.py to src/domain/chat/chat_processor.py (ODY-19 / P2.2).
The original location keeps a backward-compat shim.

Import change: `from src.chat_helpers import extract_urls` → relative import.
"""
import logging
import math
import re
import time
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple
from .chat_helpers import extract_urls
from src.youtube_handler import is_youtube_url
from src.search import comprehensive_web_search, fetch_webpage_content
from src.prompt_security import UNTRUSTED_CONTEXT_POLICY, untrusted_context_message

logger = logging.getLogger(__name__)


def _clean_search_query(query: str, max_len: int = 200) -> str:
    import markdown as _md
    from bs4 import BeautifulSoup as _BS
    html = _md.markdown(query, extensions=["fenced_code"])
    soup = _BS(html, "html.parser")
    for pre in soup.find_all("pre"):
        pre.decompose()
    for code in soup.find_all("code"):
        code.replace_with(code.get_text())
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


_STOPWORDS = frozenset(
    "a an the is am are was were be been being have has had do does did "
    "will would shall should can could may might must need ought dare "
    "i me my mine we us our ours you your yours he him his she her hers "
    "it its they them their theirs this that these those "
    "and but or nor not no so if then else than too also very "
    "in on at to for of by with from up out about into over after "
    "what when where which who whom how why all each every some any "
    "just very really actually like well also still already even "
    "oh ok okay yes yeah hey hi hello thanks thank please sorry "
    "much more most own other another such only same here there "
    "because while during before until since through between both "
    "few many several some none nothing something anything everything "
    "get got make made go going went been come came take took "
    "know think want let say tell give see look find way thing "
    "don doesn didn won wouldn couldn shouldn wasn weren isn aren haven hasn "
    "don't doesn't didn't won't wouldn't couldn't shouldn't "
    "it's i'm i've i'll i'd you're you've you'll he's she's we're we've they're they've "
    "that's there's here's what's who's how's let's can't".split()
)


def _content_tokens(text: str) -> list:
    words = re.findall(r'[a-z0-9]+(?:[-_][a-z0-9]+)*', text.lower())
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


class ChatProcessor:
    def __init__(self, memory_manager, personal_docs_manager, memory_vector=None, skills_manager=None):
        self.memory_manager = memory_manager
        self.personal_docs_manager = personal_docs_manager
        self.memory_vector = memory_vector
        self.skills_manager = skills_manager

    RAG_SIMILARITY_THRESHOLD = 0.35

    def _hybrid_retrieve(self, message: str, mem_entries: list, k: int = 5) -> list:
        if not mem_entries or not message.strip():
            return []
        now = time.time()
        query_tokens = _content_tokens(message)
        if not query_tokens:
            if not (self.memory_vector and self.memory_vector.healthy):
                return []
        N = len(mem_entries)
        doc_freq: Counter = Counter()
        mem_token_cache: dict = {}
        for mem in mem_entries:
            toks = set(_content_tokens(mem["text"]))
            mem_token_cache[mem["id"]] = toks
            for t in toks:
                doc_freq[t] += 1

        def _bm25_score(query_toks, mem_id):
            mem_toks = mem_token_cache.get(mem_id, set())
            if not mem_toks or not query_toks:
                return 0.0
            score = 0.0
            mem_len = len(mem_toks)
            avg_len = max(sum(len(v) for v in mem_token_cache.values()) / N, 1)
            k1, b = 1.5, 0.75
            for qt in query_toks:
                if qt not in mem_toks:
                    continue
                df = doc_freq.get(qt, 0)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
                tf = 1
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * mem_len / avg_len))
                score += idf * tf_norm
            return score

        has_vector = self.memory_vector and self.memory_vector.healthy
        vector_scores: dict = {}
        if has_vector:
            results = self.memory_vector.search(message, k=min(k * 3, 20))
            mem_by_id = {m["id"]: m for m in mem_entries}
            for r in results:
                if r["memory_id"] in mem_by_id:
                    vector_scores[r["memory_id"]] = max(r["score"], 0.0)

        scored = []
        for mem in mem_entries:
            mid = mem["id"]
            vs = vector_scores.get(mid, 0.0)
            kw = _bm25_score(query_tokens, mid)
            kw_norm = min(kw / 6.0, 1.0) if kw > 0 else 0.0
            category = mem.get("category", "fact")
            msg_lower = message.lower()
            mem_lower = mem["text"].lower()
            cat_boost = 1.0
            if any(w in msg_lower for w in ["name", "who am i", "my name"]):
                if category == "identity" or any(w in mem_lower for w in ["name is", "i am", "called"]):
                    cat_boost = 1.4
            elif any(w in msg_lower for w in ["phone", "email", "address", "contact"]):
                if category == "contact" or "@" in mem_lower:
                    cat_boost = 1.3
            elif any(w in msg_lower for w in ["like", "prefer", "favorite"]):
                if category == "preference":
                    cat_boost = 1.2
            kw_norm = min(kw_norm * cat_boost, 1.0)
            ts = mem.get("timestamp", 0)
            days_old = max((now - ts) / 86400, 0)
            recency = 1.0 / (1.0 + days_old * 0.05)
            if has_vector:
                if vs < 0.20 and kw_norm < 0.08:
                    continue
                final = (0.55 * vs) + (0.40 * kw_norm) + (0.05 * recency)
            else:
                if kw_norm < 0.08:
                    continue
                final = (0.95 * kw_norm) + (0.05 * recency)
            if final > 0.12:
                scored.append((final, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:k]]

    def build_context_preface(
        self,
        message: str,
        session: Any,
        use_web: bool = False,
        use_rag: bool = True,
        use_memory: bool = True,
        time_filter: Optional[str] = None,
        preset_system_prompt: Optional[str] = None,
        owner: Optional[str] = None,
        character_name: Optional[str] = None,
        agent_mode: bool = False,
        incognito: bool = False,
        use_skills: bool = True,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]], List[Dict[str, str]]]:
        preface = []
        rag_sources = []

        if preset_system_prompt:
            preface.append({"role": "system", "content": preset_system_prompt})
        preface.append({"role": "system", "content": UNTRUSTED_CONTEXT_POLICY})

        self._last_used_memories = []
        if use_memory:
            mem_entries = self.memory_manager.load(owner=owner)
            pinned = [m for m in mem_entries if m.get("pinned")]
            extended = [m for m in mem_entries if not m.get("pinned")]
            _used_ids: list = []
            if pinned:
                pinned_text = "\n- ".join([m["text"] for m in pinned])
                preface.append(untrusted_context_message(
                    "saved memory: pinned user facts", f"Core facts about the user:\n- {pinned_text}",
                ))
                for m in pinned:
                    self._last_used_memories.append({"text": m["text"], "category": m.get("category", "fact"), "type": "pinned"})
                    if m.get("id"):
                        _used_ids.append(m["id"])
            if extended:
                relevant = self._hybrid_retrieve(message, extended, k=3)
                if relevant:
                    ext_text = "\n".join([f"- {m['text']}" for m in relevant])
                    preface.append(untrusted_context_message(
                        "saved memory: retrieved context",
                        f"Memory context. Do not reference unless the user asks about these topics.\n{ext_text}",
                    ))
                    for m in relevant:
                        self._last_used_memories.append({"text": m["text"], "category": m.get("category", "fact"), "type": "recalled"})
                        if m.get("id"):
                            _used_ids.append(m["id"])
            if _used_ids and hasattr(self.memory_manager, "increment_uses"):
                try:
                    self.memory_manager.increment_uses(_used_ids)
                except Exception as _e:
                    logger.warning("Failed to increment memory uses: %s", _e)

        if use_rag:
            try:
                rag_manager = getattr(self.personal_docs_manager, 'rag_manager', None)
                if rag_manager:
                    results = rag_manager.search(message, k=5, owner=owner)
                    relevant = [r for r in results if r.get("similarity", 0) >= self.RAG_SIMILARITY_THRESHOLD]
                    if relevant:
                        logger.info(f"RAG: {len(relevant)}/{len(results)} results above threshold {self.RAG_SIMILARITY_THRESHOLD}")
                        rag_sources = [
                            {
                                "filename": r["metadata"].get("filename", r["metadata"].get("source", "unknown")),
                                "snippet": r["document"][:200],
                                "similarity": round(r.get("similarity", 0), 3)
                            }
                            for r in relevant
                        ]
                        rag_content = "Relevant documents:\n\n" + "\n\n---\n\n".join(
                            f"[{s['filename']}]\n{r['document']}" for s, r in zip(rag_sources, relevant)
                        )
                        if len(rag_content) > 10000:
                            rag_content = rag_content[:10000] + "\n[Truncated]"
                        preface.append(untrusted_context_message("retrieved documents", rag_content))
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")

        web_sources = []
        if use_web:
            try:
                from src.llm_core import llm_call
                t_url, t_model, t_headers = session.endpoint_url, session.model, session.headers
                fallback_query = next((line.strip() for line in message.split("\n") if line.strip()), "")
                search_query = fallback_query
                try:
                    generated_query = llm_call(
                        t_url, t_model,
                        [{"role": "system", "content": "Extract a concise search query from the user's message. Reply ONLY with the query."}, {"role": "user", "content": message}],
                        headers=t_headers, temperature=0.1, max_tokens=50, timeout=15,
                    ).strip()
                    if generated_query:
                        search_query = generated_query
                    else:
                        logger.warning("LLM generated an empty search query, using fallback.")
                except Exception as e:
                    logger.warning(f"Failed to generate search query via LLM, using fallback: {e}")
                search_query = " ".join(search_query.split())
                if len(search_query) > 150:
                    search_query = search_query[:150].strip()
                search_query = _clean_search_query(search_query, max_len=150)
                if search_query:
                    web_context, web_sources = comprehensive_web_search(search_query, time_filter=time_filter, return_sources=True)
                    preface.append(untrusted_context_message("web search results", web_context))
            except Exception as e:
                logger.error(f"Web search failed: {e}")
                preface.append({"role": "system", "content": "Web search encountered an error and could not retrieve results."})

        urls = extract_urls(message)
        non_yt_urls = [u for u in urls if not is_youtube_url(u)]
        skip_url_fetch = len(message) > 2000 or len(non_yt_urls) > 3
        if not skip_url_fetch:
            for url in non_yt_urls:
                result = fetch_webpage_content(url)
                if result.get('success'):
                    content = result.get('content', '')[:10000]
                    preface.append(untrusted_context_message(f"web page: {url}", f"Content from {url}:\n\n{content}"))

        if agent_mode and not incognito and use_skills and self.skills_manager:
            try:
                idx = self.skills_manager.index_for(owner=owner)
            except Exception as e:
                logger.debug(f"Skills index unavailable: {e}")
                idx = []
            if idx:
                by_cat: Dict[str, list] = {}
                for s in idx:
                    by_cat.setdefault(s.get("category") or "general", []).append(s)
                lines = ["[Available skills — call manage_skills(action='view', name='...') to load one when relevant]"]
                for cat in sorted(by_cat):
                    lines.append(f"  {cat}:")
                    for s in sorted(by_cat[cat], key=lambda x: x["name"]):
                        desc = s.get("description") or ""
                        lines.append(f"    - {s['name']}: {desc}" if desc else f"    - {s['name']}")
                preface.append(untrusted_context_message("available skills index", "\n".join(lines)))

        return preface, rag_sources, web_sources
