# src/domain/documents/personal_docs.py
"""Personal document indexing, retrieval, and directory management.

Moved from src/personal_docs.py to src/domain/documents/personal_docs.py (ODY-19 / P2.2).
The original location keeps a backward-compat shim.

Import note: `from src.markitdown_runtime import MARKITDOWN_EXTS` is unchanged (not moved).
"""
import os
import re
import json
import logging
from typing import List, Dict, Set, Any, Tuple
from dataclasses import dataclass

from src.markitdown_runtime import MARKITDOWN_EXTS

logger = logging.getLogger(__name__)


def extract_pdf_text(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = "".join((page.extract_text() or "") for page in reader.pages)
        return text
    except ImportError:
        logger.warning("pypdf not installed, cannot extract PDF text")
        return ""
    except Exception as e:
        logger.error(f"Failed to extract PDF text from {file_path}: {e}")
        return ""


def extract_office_text(file_path: str) -> str:
    from src.markitdown_runtime import convert_to_markdown
    return convert_to_markdown(file_path) or ""


@dataclass
class PersonalDocsConfig:
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    DEFAULT_EXTENSIONS: Tuple[str, ...] = (".txt", ".md", ".json", ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".epub")
    DEFAULT_K: int = 5
    STOP_WORDS: Set[str] = None

    def __post_init__(self):
        if self.STOP_WORDS is None:
            self.STOP_WORDS = set("""
            the a an is are was were be been being to of in for on at by with from
            and or if then else when while as it this that those these i you he she
            we they my your our their me him her us them
            """.split())


config = PersonalDocsConfig()


def read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def split_chunks(text: str, size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP) -> List[str]:
    if not isinstance(text, str):
        return []
    text = text.strip()
    if not text:
        return []
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + size, n)
        chunks.append(text[i:j])
        if j >= n:
            break
        i = j - overlap if j - overlap > i else j
    return chunks


def tokenize(s: str) -> Set[str]:
    text = s if isinstance(s, str) else ""
    tokens = re.findall(r"[A-Za-z0-9_\-]+", text.lower())
    return set(t for t in tokens if t not in config.STOP_WORDS and len(t) > 1)


def load_personal_index(personal_dir: str, extensions: Tuple[str, ...] = config.DEFAULT_EXTENSIONS) -> List[Dict[str, Any]]:
    files = []
    for root, _, names in os.walk(personal_dir):
        for name in sorted(names):
            p = os.path.join(root, name)
            if not os.path.isfile(p):
                continue
            if not any(name.lower().endswith(ext) for ext in extensions):
                continue
            size = os.path.getsize(p)
            ext = os.path.splitext(name)[1].lower()
            if ext == ".pdf":
                text = extract_pdf_text(p)
            elif ext in MARKITDOWN_EXTS:
                text = extract_office_text(p)
            else:
                text = read_text_file(p)
            chunks = split_chunks(text)
            display = os.path.relpath(p, personal_dir)
            files.append({"name": display, "path": p, "size": size, "chunks": chunks})
    return files


def retrieve_personal_keyword(personal_index: List[Dict], query: str, k: int = 5) -> List[str]:
    q = tokenize(query)
    if not q:
        return []
    scored = []
    for f in personal_index:
        if not isinstance(f, dict):
            continue
        for idx, ch in enumerate(f.get("chunks") or []):
            score = len(q & tokenize(ch))
            if score > 0:
                scored.append((score, f.get("name", ""), idx, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f"[{fname} :: chunk {idx+1}]\n{ch}" for _, fname, idx, ch in scored[:k]]


def retrieve_personal(personal_index: List[Dict], query: str, k: int = 5, rag_manager=None) -> List[str]:
    if not query:
        return []
    if rag_manager:
        try:
            vector_results = rag_manager.search(query, k)
            if vector_results:
                out = []
                for result in vector_results:
                    source = result["metadata"].get("source", "")
                    filename = os.path.basename(source)
                    out.append(f"[{filename} :: vector search]\n{result['document']}")
                return out
        except Exception as e:
            logger.warning(f"Vector search failed, falling back to keyword search: {e}")
    return retrieve_personal_keyword(personal_index, query, k)


def _string_list(values) -> list[str]:
    return [value for value in values or [] if isinstance(value, str)]


class PersonalDocsManager:
    def __init__(self, personal_dir: str, rag_manager=None):
        self.personal_dir = personal_dir
        self.rag_manager = rag_manager
        self.index = []
        self.indexed_directories = []
        self.excluded_files: Set[str] = set()
        self.directories_file = os.path.join(personal_dir, "indexed_directories.json")
        self._excluded_file = os.path.join(personal_dir, "excluded_files.json")
        self.load_directories()
        self._load_excluded()
        self.refresh_index()

    def load_directories(self):
        try:
            if os.path.exists(self.directories_file):
                with open(self.directories_file, 'r', encoding="utf-8") as f:
                    directories = json.load(f)
                if not isinstance(directories, list):
                    raise ValueError("indexed directories must be a list")
                self.indexed_directories = _string_list(directories)
            else:
                self.indexed_directories = []
        except Exception as e:
            logger.error(f"Error loading directories: {e}")
            self.indexed_directories = []

    def save_directories(self):
        try:
            with open(self.directories_file, 'w', encoding="utf-8") as f:
                json.dump(_string_list(self.indexed_directories), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving directories: {e}")

    def _load_excluded(self):
        try:
            if os.path.exists(self._excluded_file):
                with open(self._excluded_file, 'r', encoding="utf-8") as f:
                    excluded = json.load(f)
                if not isinstance(excluded, list):
                    raise ValueError("excluded files must be a list")
                self.excluded_files = set(_string_list(excluded))
            else:
                self.excluded_files = set()
        except Exception as e:
            logger.error(f"Error loading excluded files: {e}")
            self.excluded_files = set()

    def _save_excluded(self):
        try:
            with open(self._excluded_file, 'w', encoding="utf-8") as f:
                json.dump(_string_list(self.excluded_files), f)
        except Exception as e:
            logger.error(f"Error saving excluded files: {e}")

    def exclude_file(self, filepath: str):
        self.excluded_files.add(os.path.abspath(filepath))
        self._save_excluded()
        self.index = [f for f in self.index if os.path.abspath(f.get("path", "")) != os.path.abspath(filepath)]

    def add_directory(self, directory: str, *, index: bool = True, owner: str = None):
        directory = os.path.abspath(directory)
        self.excluded_files = {
            p for p in self.excluded_files
            if not (p == directory or p.startswith(directory + os.sep))
        }
        self._save_excluded()
        if directory not in self.indexed_directories:
            self.indexed_directories.append(directory)
            self.save_directories()
            if index and self.rag_manager:
                try:
                    result = self.rag_manager.index_personal_documents(directory, owner=owner)
                    logger.info(f"Indexed {result.get('indexed_count', 0)} chunks from {directory}")
                except Exception as e:
                    logger.error(f"Failed to index directory {directory}: {e}")
            self.refresh_index()

    def remove_directory(self, directory: str):
        directory = os.path.abspath(directory)
        if directory in self.indexed_directories:
            self.indexed_directories.remove(directory)
            self.save_directories()
            self.refresh_index()
            if self.rag_manager:
                try:
                    self.rag_manager.remove_directory(directory)
                except Exception as e:
                    logger.error(f"Failed to remove directory from RAG index: {e}")

    def rename_directory(self, old_directory: str, new_directory: str, *, path_map: Dict[str, str] = None):
        old_directory = os.path.abspath(old_directory)
        new_directory = os.path.abspath(new_directory)
        path_map = {os.path.abspath(k): os.path.abspath(v) for k, v in (path_map or {}).items()}

        def rewrite(path: str) -> str:
            abs_path = os.path.abspath(path)
            mapped = path_map.get(abs_path)
            if mapped:
                return mapped
            if abs_path == old_directory:
                return new_directory
            if abs_path.startswith(old_directory + os.sep):
                return new_directory + abs_path[len(old_directory):]
            return abs_path

        changed_dirs = False
        rewritten_dirs = []
        for directory in self.indexed_directories:
            rewritten = rewrite(directory)
            changed_dirs = changed_dirs or rewritten != os.path.abspath(directory)
            if rewritten not in rewritten_dirs:
                rewritten_dirs.append(rewritten)
        if changed_dirs:
            self.indexed_directories = rewritten_dirs
            self.save_directories()

        changed_excluded = False
        rewritten_excluded = set()
        for path in self.excluded_files:
            rewritten = rewrite(path)
            changed_excluded = changed_excluded or rewritten != os.path.abspath(path)
            rewritten_excluded.add(rewritten)
        if changed_excluded:
            self.excluded_files = rewritten_excluded
            self._save_excluded()

        if changed_dirs or changed_excluded:
            self.refresh_index()

    def get_indexed_directories(self):
        return self.indexed_directories.copy()

    def refresh_index(self):
        self.index = []
        base_files = load_personal_index(self.personal_dir)
        for f in base_files:
            if os.path.abspath(f.get("path", "")) in self.excluded_files:
                continue
            f['source_dir'] = self.personal_dir
            self.index.append(f)
        for directory in self.indexed_directories:
            if not os.path.exists(directory) or not os.path.isdir(directory):
                continue
            dir_files = load_personal_index(directory)
            for f in dir_files:
                if os.path.abspath(f.get("path", "")) in self.excluded_files:
                    continue
                f['source_dir'] = directory
                f['name'] = f"{os.path.basename(directory)}/{f['name']}"
                self.index.append(f)

    def retrieve(self, query: str, k: int = 5) -> List[str]:
        return retrieve_personal(self.index, query, k, self.rag_manager)

    def get_file_list(self) -> List[Dict[str, Any]]:
        return [{"name": f["name"], "size": f["size"]} for f in self.index]

    def get_stats(self) -> Dict[str, Any]:
        total_docs = len(self.index)
        total_chunks = sum(len(doc.get('chunks', [])) for doc in self.index)
        total_size = sum(doc.get('size', 0) for doc in self.index)
        extensions: Dict[str, int] = {}
        for doc in self.index:
            ext = os.path.splitext(doc['path'])[1]
            extensions[ext] = extensions.get(ext, 0) + 1
        return {
            'total_documents': total_docs,
            'total_chunks': total_chunks,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_types': extensions,
            'directories_count': len(self.indexed_directories) + 1,
            'base_directory': self.personal_dir,
            'additional_directories': self.indexed_directories,
        }

    def index_all_directories(self):
        if not self.rag_manager:
            logger.warning("No RAG manager available for indexing")
            return
        success_count = 0
        failure_count = 0
        try:
            result = self.rag_manager.index_personal_documents(self.personal_dir)
            if result.get('success'):
                success_count += 1
        except Exception as e:
            failure_count += 1
            logger.error(f"Failed to index base directory {self.personal_dir}: {e}")
        for directory in self.indexed_directories:
            if not os.path.exists(directory):
                failure_count += 1
                continue
            try:
                result = self.rag_manager.index_personal_documents(directory)
                if result.get('success'):
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                logger.error(f"Failed to index directory {directory}: {e}")
        return {"success": success_count, "failed": failure_count}
