"""Reranker skip paths must not load CrossEncoder or return empty lists."""

import pytest

from app.core import reranker as reranker_mod
from app.core.reranker import Reranker


@pytest.fixture
def fresh_reranker():
    reranker_mod.Reranker._instance = None
    instance = Reranker()
    yield instance
    reranker_mod.Reranker._instance = None


def _candidates():
    return [
        {"id": "1", "text": "first hybrid hit", "score": 1.0},
        {"id": "2", "text": "second hybrid hit", "score": 0.8},
        {"id": "3", "text": "third hybrid hit", "score": 0.5},
    ]


def test_rerank_skipped_when_enable_rerank_false(monkeypatch, fresh_reranker):
    monkeypatch.setattr(reranker_mod.settings, "enable_rerank", False)
    monkeypatch.setattr(reranker_mod.settings, "top_k_rerank", 2)

    def _boom():
        raise AssertionError("CrossEncoder must not be loaded when rerank is disabled")

    monkeypatch.setattr(fresh_reranker, "_get_model", _boom)
    out = fresh_reranker.rerank("q", _candidates(), top_k=2)
    assert [c["id"] for c in out] == ["1", "2"]
    assert out != []


def test_rerank_skipped_when_top_k_rerank_zero(monkeypatch, fresh_reranker):
    monkeypatch.setattr(reranker_mod.settings, "enable_rerank", True)
    monkeypatch.setattr(reranker_mod.settings, "top_k_rerank", 0)

    def _boom():
        raise AssertionError("CrossEncoder must not be loaded when TOP_K_RERANK=0")

    monkeypatch.setattr(fresh_reranker, "_get_model", _boom)
    candidates = _candidates()
    out = fresh_reranker.rerank("q", candidates, top_k=0)
    assert out == candidates
    assert out != []
