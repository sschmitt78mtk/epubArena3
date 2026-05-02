"""
Unit tests for the Chunker.chunkit() method in collect.py.
No real epub files are used - Chunk objects are constructed directly with HTML content.
Run with:  python -m pytest tests/test_chunkit.py -v
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work from the tests/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from store import Chunk
from collect import Chunker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(html: str, chapter_name: str = "ch1", chapter_id: int = 1) -> Chunk:
    """Convenience factory for a raw input Chunk."""
    return Chunk(chapter_name, 0, "raw", html, chapter_id)


# ===========================================================================
# 1. Empty input
# ===========================================================================

class TestChunkitEmptyInput:
    def test_empty_list_returns_empty(self):
        chunker = Chunker(maxps=20, maxwords=350)
        assert chunker.chunkit([]) == []


# ===========================================================================
# 2. Single paragraph
# ===========================================================================

class TestChunkitSingleParagraph:
    def test_single_paragraph_produces_one_text_chunk(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<p>Hello world</p>")])
        assert len(result) == 1
        assert result[0].chunktype == "text"
        assert result[0].content == "\nHello world"
        assert result[0].source_chaptername == "ch1"
        assert result[0].chapter_id == 1
        assert result[0].chunk_id == 0


# ===========================================================================
# 3. Headings
# ===========================================================================

class TestChunkitHeading:
    def test_h1_heading(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<h1>Title</h1>")])
        assert len(result) == 1
        assert result[0].chunktype == "heading"
        assert result[0].content == "Title"
        assert result[0].headinglevel == "h1"

    def test_h3_heading(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<h3>Section</h3>")])
        assert len(result) == 1
        assert result[0].chunktype == "heading"
        assert result[0].content == "Section"
        assert result[0].headinglevel == "h3"


# ===========================================================================
# 4. Table
# ===========================================================================

class TestChunkitTable:
    def test_table_produces_table_chunk(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = '<table><tr><td>Cell</td></tr></table>'
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 1
        assert result[0].chunktype == "table"
        assert result[0].content == html

    def test_pre_produces_table_chunk(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = "<pre>some code here</pre>"
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 1
        assert result[0].chunktype == "table"
        assert result[0].content == html


# ===========================================================================
# 5. Image
# ===========================================================================

class TestChunkitImage:
    def test_image_with_path(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk('<img src="../Images/photo.png" />')])
        assert len(result) == 1
        assert result[0].chunktype == "image"
        assert result[0].content == "images/photo.png"

    def test_image_simple_src(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk('<img src="cover.jpeg">')])
        assert len(result) == 1
        assert result[0].chunktype == "image"
        assert result[0].content == "images/cover.jpeg"


# ===========================================================================
# 6. Source-code paragraph
# ===========================================================================

class TestChunkitSourceCode:
    def test_single_source_code_paragraph(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = '<p class="source-code">def hello():\n    print("hi")</p>'
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 1
        assert result[0].chunktype == "table"
        # Raw HTML of the source-code paragraph is preserved
        assert "source-code" in result[0].content

    def test_consecutive_source_code_paragraphs_merged(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = '<p class="source-code">line1</p><p class="source-code">line2</p>'
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 1
        assert result[0].chunktype == "table"
        assert "\n" in result[0].content  # two paragraphs joined by newline


# ===========================================================================
# 7. List item
# ===========================================================================

class TestChunkitListItem:
    def test_list_item_added_with_bullet(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<li>Item one</li>")])
        assert len(result) == 1
        assert result[0].chunktype == "text"
        assert "* Item one" in result[0].content


# ===========================================================================
# 8. Quote element
# ===========================================================================

class TestChunkitQuote:
    def test_quote_added_to_text(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<q>To be or not to be</q>")])
        assert len(result) == 1
        assert result[0].chunktype == "text"
        assert "To be or not to be" in result[0].content


# ===========================================================================
# 9. dd / dl / dt elements
# ===========================================================================

class TestChunkitDefinitionElements:
    def test_dd_added_to_text(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<dd>A definition</dd>")])
        assert len(result) == 1
        assert result[0].chunktype == "text"
        assert "A definition" in result[0].content

    def test_dt_added_to_text(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<dt>A term</dt>")])
        assert len(result) == 1
        assert result[0].chunktype == "text"
        assert "A term" in result[0].content

    def test_dl_added_to_text(self):
        chunker = Chunker(maxps=20, maxwords=350)
        result = chunker.chunkit([_make_chunk("<dl>A list</dl>")])
        assert len(result) == 1
        assert result[0].chunktype == "text"
        assert "A list" in result[0].content


# ===========================================================================
# 10. maxps split
# ===========================================================================

class TestChunkitMaxps:
    def test_split_at_maxps(self):
        """
        When paracount reaches maxps, accumulated text is output as a chunk.
        Note: the paragraph that triggers the split is not carried over
        (this is the current behaviour of chunkit).
        """
        chunker = Chunker(maxps=2, maxwords=350)
        html = "<p>Line one</p><p>Line two</p><p>Line three</p>"
        result = chunker.chunkit([_make_chunk(html)])
        text_chunks = [c for c in result if c.chunktype == "text"]
        # Paragraph 1 accumulated; paragraph 2 triggers the split (paracount=2)
        # and is lost; paragraph 3 starts a new chunk.
        assert len(text_chunks) == 2
        assert "Line one" in text_chunks[0].content
        assert "Line three" in text_chunks[1].content


# ===========================================================================
# 11. maxwords split
# ===========================================================================

class TestChunkitMaxwords:
    def test_split_at_maxwords(self):
        """
        When word count exceeds maxwords, accumulated text is output.
        Note: the paragraph that triggers the split is not carried over
        (this is the current behaviour of chunkit).
        """
        chunker = Chunker(maxps=20, maxwords=3)
        html = "<p>short</p><p>this is a longer paragraph that exceeds the word limit</p>"
        result = chunker.chunkit([_make_chunk(html)])
        text_chunks = [c for c in result if c.chunktype == "text"]
        # 'short' (0 spaces) is accumulated; the second paragraph triggers
        # maxwords (>3 spaces) and is lost.
        assert len(text_chunks) == 1
        assert "short" in text_chunks[0].content


# ===========================================================================
# 12. Consecutive same-level headings merged
# ===========================================================================

class TestChunkitConsecutiveHeadings:
    def test_same_level_headings_merged(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = "<h2>Part 1</h2><h2>Part 2</h2>"
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 1
        assert result[0].chunktype == "heading"
        assert result[0].content == "Part 1\nPart 2"
        assert result[0].headinglevel == "h2"


# ===========================================================================
# 13. Different-level headings split
# ===========================================================================

class TestChunkitDifferentLevelHeadings:
    def test_different_level_headings_produce_separate_chunks(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 2
        assert result[0].chunktype == "heading"
        assert result[0].content == "Title"
        assert result[0].headinglevel == "h1"
        assert result[1].chunktype == "heading"
        assert result[1].content == "Subtitle"
        assert result[1].headinglevel == "h2"


# ===========================================================================
# 14. Mixed content
# ===========================================================================

class TestChunkitMixedContent:
    def test_heading_then_paragraph(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = "<h1>Chapter Title</h1><p>Some body text here.</p>"
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 2
        assert result[0].chunktype == "heading"
        assert result[0].content == "Chapter Title"
        assert result[0].headinglevel == "h1"
        assert result[1].chunktype == "text"
        assert "Some body text here." in result[1].content

    def test_text_then_table_then_text(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = '<p>Intro text</p><table><tr><td>Data</td></tr></table><p>Outro text</p>'
        result = chunker.chunkit([_make_chunk(html)])
        assert len(result) == 3
        assert result[0].chunktype == "text"
        assert result[1].chunktype == "table"
        assert result[2].chunktype == "text"
        assert "Intro text" in result[0].content
        assert "Outro text" in result[2].content

    def test_chunk_ids_are_sequential(self):
        chunker = Chunker(maxps=20, maxwords=350)
        html = '<h1>Title</h1><p>Text</p><img src="pic.png">'
        result = chunker.chunkit([_make_chunk(html)])
        for i, chunk in enumerate(result):
            assert chunk.chunk_id == i

    def test_full_chapter_variety(self):
        """Exercise many element types in one input chunk."""
        chunker = Chunker(maxps=20, maxwords=350)
        html = (
            "<h1>My Chapter</h1>"
            "<p>Opening paragraph.</p>"
            '<img src="images/fig1.png">'
            "<p>Another paragraph.</p>"
            "<table><tr><td>Cell</td></tr></table>"
            "<li>List item</li>"
            "<p>Final paragraph.</p>"
        )
        result = chunker.chunkit([_make_chunk(html)])
        types = [c.chunktype for c in result]
        assert "heading" in types
        assert "text" in types
        assert "image" in types
        assert "table" in types
        # Verify chunk IDs are sequential
        for i, chunk in enumerate(result):
            assert chunk.chunk_id == i

    def test_heading_flushes_accumulated_text(self):
        """A heading in the middle should flush the text collected so far."""
        chunker = Chunker(maxps=20, maxwords=350)
        html = "<p>Before heading</p><h2>Mid Heading</h2><p>After heading</p>"
        result = chunker.chunkit([_make_chunk(html)])
        types = [c.chunktype for c in result]
        # Expected order: text, heading, text
        assert types == ["text", "heading", "text"]
        assert "Before heading" in result[0].content
        assert result[1].content == "Mid Heading"
        assert "After heading" in result[2].content

    def test_table_flushes_accumulated_text(self):
        """A table should flush the text collected so far."""
        chunker = Chunker(maxps=20, maxwords=350)
        html = "<p>Before table</p><table><tr><td>X</td></tr></table>"
        result = chunker.chunkit([_make_chunk(html)])
        types = [c.chunktype for c in result]
        assert types == ["text", "table"]
        assert "Before table" in result[0].content

    def test_image_flushes_accumulated_text(self):
        """An image should flush the text collected so far."""
        chunker = Chunker(maxps=20, maxwords=350)
        html = '<p>Before image</p><img src="photo.jpg">'
        result = chunker.chunkit([_make_chunk(html)])
        types = [c.chunktype for c in result]
        assert types == ["text", "image"]
        assert "Before image" in result[0].content


# ===========================================================================
# Edge cases
# ===========================================================================

class TestChunkitEdgeCases:
    def test_chunker_state_reset_on_new_instance(self):
        """Each Chunker instance should start with currentChunkID=0."""
        c1 = Chunker(maxps=20, maxwords=350)
        c1.chunkit([_make_chunk("<p>First run</p>")])
        c2 = Chunker(maxps=20, maxwords=350)
        result = c2.chunkit([_make_chunk("<p>Second run</p>")])
        assert result[0].chunk_id == 0

    def test_multiple_input_chunks_sequential_ids(self):
        """Chunk IDs continue incrementing across multiple input Chunk objects."""
        chunker = Chunker(maxps=20, maxwords=350)
        inputs = [
            _make_chunk("<p>Paragraph A</p>", chapter_name="ch1", chapter_id=1),
            _make_chunk("<p>Paragraph B</p>", chapter_name="ch2", chapter_id=2),
        ]
        result = chunker.chunkit(inputs)
        ids = [c.chunk_id for c in result]
        assert ids == list(range(len(result)))