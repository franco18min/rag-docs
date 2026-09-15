"""Generator context markers and parse_citations mapping (no Gemini)."""

import logging

from app.core.generator import Generator, parse_citations


def _chunks():
    return [
        {
            "text": "Spark is a unified analytics engine.",
            "metadata": {"source": "spark.md", "section": "Intro"},
            "score": 0.9,
        },
        {
            "text": "Delta Lake adds ACID.",
            "metadata": {"source": "delta.md"},
            "score": 0.7,
        },
    ]


def test_format_context_includes_numbered_markers():
    ctx = Generator._format_context(_chunks())
    assert "[#1]" in ctx
    assert "[#2]" in ctx
    assert "spark.md" in ctx
    assert "delta.md" in ctx


def test_parse_citations_maps_markers_in_order():
    answer = "Spark [#1] works with Delta [#2] and Spark again [#1]."
    cites = parse_citations(answer, _chunks())
    assert [c["citation_number"] for c in cites] == [1, 2]
    assert cites[0]["source"] == "spark.md"
    assert cites[1]["source"] == "delta.md"


def test_parse_citations_fallback_warns_without_markers(caplog):
    with caplog.at_level(logging.WARNING):
        cites = parse_citations("No markers here", _chunks())
    assert [c["citation_number"] for c in cites] == [1, 2]
    assert any("No parseable" in rec.message for rec in caplog.records)
