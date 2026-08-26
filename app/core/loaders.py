"""
Document loaders.

Each loader takes a file path and returns plain text. The `load_documents`
function walks a directory tree, dispatches by extension, and returns a list
of dicts ready for chunking.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from tqdm import tqdm


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Individual loaders
# ----------------------------------------------------------------------
def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            parts.append(f"\n[Page {i + 1}]\n{text}")
    return "\n".join(parts)


def _load_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _load_html(path: Path) -> str:
    from bs4 import BeautifulSoup

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


LOADERS: dict[str, Callable[[Path], str]] = {
    ".pdf": _load_pdf,
    ".md": _load_markdown,
    ".markdown": _load_markdown,
    ".html": _load_html,
    ".htm": _load_html,
    ".txt": _load_text,
}

SUPPORTED_EXTENSIONS = tuple(LOADERS.keys())


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def load_documents(source_dir: str) -> list[dict]:
    """Load all supported documents from a directory tree.

    Returns a list of dicts with keys: ``content``, ``source``, ``section``,
    ``metadata``. The metadata dict contains: ``filename``, ``extension``,
    ``size_bytes``, ``modified``.
    """
    source = Path(source_dir)
    if not source.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    documents: list[dict] = []
    files = [p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in LOADERS]

    for file_path in tqdm(files, desc="Loading documents"):
        loader = LOADERS[file_path.suffix.lower()]
        try:
            content = loader(file_path)
        except Exception as e:
            logger.warning("Failed to load %s: %s", file_path, e)
            continue
        if not content or not content.strip():
            logger.warning("Empty content in %s, skipping", file_path)
            continue
        documents.append(
            {
                "content": content,
                "source": str(file_path.resolve()),
                "section": None,
                "metadata": {
                    "filename": file_path.name,
                    "extension": file_path.suffix.lower(),
                    "size_bytes": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime,
                },
            }
        )
    return documents
