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
        The paragraph that triggers the split is carried over to the next chunk.
        """
        chunker = Chunker(maxps=2, maxwords=350)
        html = "<p>Line one</p><p>Line two</p><p>Line three</p>"
        result = chunker.chunkit([_make_chunk(html)])
        text_chunks = [c for c in result if c.chunktype == "text"]
        # Paragraph 1 accumulated; paragraph 2 triggers the split (paracount=2)
        # and is carried over to the next chunk; paragraph 3 also triggers.
        assert len(text_chunks) == 3
        assert "Line one" in text_chunks[0].content
        assert "Line two" in text_chunks[1].content
        assert "Line three" in text_chunks[2].content


# ===========================================================================
# 11. maxwords split
# ===========================================================================

class TestChunkitMaxwords:
    def test_split_at_maxwords(self):
        """
        When word count exceeds maxwords, accumulated text is output.
        The paragraph that triggers the split is carried over to the next chunk.
        """
        chunker = Chunker(maxps=20, maxwords=3)
        html = "<p>short</p><p>this is a longer paragraph that exceeds the word limit</p>"
        result = chunker.chunkit([_make_chunk(html)])
        text_chunks = [c for c in result if c.chunktype == "text"]
        # 'short' (0 spaces) is accumulated; the second paragraph triggers
        # maxwords (>3 spaces) and is carried over to chunk 1.
        assert len(text_chunks) == 2
        assert "short" in text_chunks[0].content
        assert "longer paragraph" in text_chunks[1].content


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


# ===========================================================================
# 15. Long text processing with maxps and maxwords parameters
# ===========================================================================

class TestChunkitLongTextParameters:
    """Tests that verify chunkit correctly processes long texts depending on
    maxps (maximum paragraphs per chunk) and maxwords (maximum spaces/words
    per chunk).

    When a paragraph triggers a split (by reaching maxps or exceeding
    maxwords), the accumulated text is output as a chunk and the triggering
    paragraph is carried over to the next chunk — no text is lost.
    """

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _paras_to_html(paragraphs: list[str]) -> str:
        """Wrap each plain-text paragraph in <p> tags and concatenate."""
        return "".join(f"<p>{t}</p>" for t in paragraphs)

    @staticmethod
    def _text_chunks(result: list[Chunk]) -> list[Chunk]:
        return [c for c in result if c.chunktype == "text"]

    # -- tests ---------------------------------------------------------------

    def test_many_short_paragraphs_split_by_maxps(self):
        """10 short paragraphs with maxps=3: every 3rd paragraph triggers a
        split and is carried over. Expected: 5 text chunks, all paragraphs
        present."""
        paras = [f"Para {i}" for i in range(10)]  # each has 1 space
        html = self._paras_to_html(paras)
        chunker = Chunker(maxps=3, maxwords=350)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        assert len(tc) == 5
        # Chunk 0: Para 0, Para 1  (Para 2 triggers, carried to chunk 1)
        assert "Para 0" in tc[0].content
        assert "Para 1" in tc[0].content
        assert "Para 2" not in tc[0].content
        # Chunk 1: Para 2, Para 3  (Para 4 triggers, carried to chunk 2)
        assert "Para 2" in tc[1].content
        assert "Para 3" in tc[1].content
        assert "Para 4" not in tc[1].content
        # Chunk 2: Para 4, Para 5  (Para 6 triggers, carried to chunk 3)
        assert "Para 4" in tc[2].content
        assert "Para 5" in tc[2].content
        assert "Para 6" not in tc[2].content
        # Chunk 3: Para 6, Para 7  (Para 8 triggers, carried to chunk 4)
        assert "Para 6" in tc[3].content
        assert "Para 7" in tc[3].content
        assert "Para 8" not in tc[3].content
        # Chunk 4: Para 8, Para 9 (end of input)
        assert "Para 8" in tc[4].content
        assert "Para 9" in tc[4].content

        # All paragraphs must appear in output
        all_content = "".join(c.content for c in tc)
        for i in range(10):
            assert f"Para {i}" in all_content, f"Para {i} missing from output"

    def test_wordy_paragraphs_split_by_maxwords(self):
        """10 paragraphs each with 3 spaces (4 words), maxwords=10.
        After 3 accumulated paragraphs (9 spaces), the 4th would exceed
        maxwords and triggers the split; the 4th is carried over.
        Expected: 4 chunks, all paragraphs present."""
        paras = ["word word word word"] * 10  # 3 spaces each
        html = self._paras_to_html(paras)
        chunker = Chunker(maxps=20, maxwords=10)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        assert len(tc) == 4
        # First three chunks each accumulated 3 paragraphs (9 spaces)
        assert tc[0].content.count(" ") == 9
        assert tc[1].content.count(" ") == 9
        assert tc[2].content.count(" ") == 9
        # Last chunk has the carried-over paragraph (3 spaces)
        assert tc[3].content.count(" ") == 3

    def test_no_split_with_generous_limits(self):
        """Same long text with very large maxps and maxwords stays as one chunk."""
        paras = [f"Para {i}" for i in range(10)]
        html = self._paras_to_html(paras)
        chunker = Chunker(maxps=100, maxwords=10000)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        assert len(tc) == 1
        for i in range(10):
            assert f"Para {i}" in tc[0].content

    def test_maxps_and_maxwords_interact(self):
        """Mixed paragraph lengths where some splits are triggered by maxps
        and others by maxwords. Triggering paragraphs are carried over."""
        # maxps=4, maxwords=8
        # p0-p2: short (1 space each) → accumulate 3 spaces
        # p3: short → paracount=4 triggers maxps split (p3 carried to chunk 1)
        # p4: x y (1 space) → accumulate with carried p3
        # p5: long (9 spaces) → 2+9=11 > 8 triggers maxwords (p5 carried to chunk 2)
        # p6: a b c (2 spaces) → 9+2=11 > 8 triggers again (p6 carried to chunk 3)
        # p7: very long (11 spaces) → 2+11=13 > 8 triggers (p7 carried to chunk 4)
        # p8: final (0 spaces) → 11+0=11 > 8 triggers (p8 carried to chunk 5)
        # End: output final
        paragraphs = [
            "a b",                                                  # 1 space
            "c d",                                                  # 1 space
            "e f",                                                  # 1 space
            "g h",                                                  # 1 space  → maxps trigger
            "x y",                                                  # 1 space
            "one two three four five six seven eight nine ten",     # 9 spaces → maxwords trigger
            "a b c",                                                # 2 spaces
            "d e f g h i j k l m n o",                             # 11 spaces → maxwords trigger
            "final",                                                # 0 spaces
        ]
        html = self._paras_to_html(paragraphs)
        chunker = Chunker(maxps=4, maxwords=8)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        assert len(tc) == 6
        # Chunk 0: maxps trigger — a b, c d, e f accumulated
        assert "a b" in tc[0].content
        assert "c d" in tc[0].content
        assert "e f" in tc[0].content
        assert "g h" not in tc[0].content

        # Chunk 1: maxwords trigger — g h (carried) + x y accumulated
        assert "g h" in tc[1].content
        assert "x y" in tc[1].content
        assert "one two" not in tc[1].content

        # Chunk 2: maxwords trigger — long p5 (carried)
        assert "one two three four five six seven eight nine ten" in tc[2].content
        assert "a b c" not in tc[2].content

        # Chunk 3: maxwords trigger — a b c (carried)
        assert "a b c" in tc[3].content
        assert "d e f g" not in tc[3].content

        # Chunk 4: maxwords trigger — long p7 (carried)
        assert "d e f g h i j k l m n o" in tc[4].content
        assert "final" not in tc[4].content

        # Chunk 5: end of input — final (carried)
        assert "final" in tc[5].content

        # All paragraphs must appear in output
        all_content = "".join(c.content for c in tc)
        for p in paragraphs:
            assert p in all_content, f"Paragraph '{p}' missing from output"

    def test_output_chunk_space_counts_within_maxwords(self):
        """With restrictive maxwords, no output text chunk should exceed
        maxwords spaces in the accumulated portion before the trigger."""
        paras = ["word word word"] * 12  # 2 spaces each
        html = self._paras_to_html(paras)
        chunker = Chunker(maxps=20, maxwords=6)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        for chunk in tc:
            assert chunk.content.count(" ") <= 6, (
                f"Chunk has {chunk.content.count(' ')} spaces, "
                f"exceeding maxwords=6"
            )

    def test_small_maxps_produces_many_chunks(self):
        """With maxps=2, every other paragraph triggers a split and is
        carried over. 7 paragraphs → 7 chunks (each containing 1 paragraph)."""
        paras = [f"Para {i}" for i in range(7)]
        html = self._paras_to_html(paras)
        chunker = Chunker(maxps=2, maxwords=350)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        assert len(tc) == 7
        # Each chunk contains exactly one paragraph (carried over from trigger)
        for i in range(7):
            assert f"Para {i}" in tc[i].content
        # All paragraphs present
        all_content = "".join(c.content for c in tc)
        for i in range(7):
            assert f"Para {i}" in all_content, f"Para {i} missing from output"

    def test_varying_paragraph_lengths_with_maxwords(self):
        """Mix of short and long paragraphs with maxwords=15.
        Long paragraphs trigger the split and are carried over."""
        paragraphs = [
            "short text",                                           # 1 space
            "another short one",                                    # 2 spaces
            "this is a really long paragraph with many many words exceeding the maximum word count",  # 14 spaces → trigger
            "brief",                                                # 0 spaces
            "medium length paragraph here",                         # 3 spaces
            "more text to add here now",                            # 5 spaces
            "and even more text continues here today",              # 6 spaces
            "one more paragraph",                                   # 2 spaces → trigger (14+2>15)
            "final words",                                          # 1 space
        ]
        html = self._paras_to_html(paragraphs)
        chunker = Chunker(maxps=20, maxwords=15)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        assert len(tc) == 4
        # Chunk 0: short text + another short one (3 spaces total; p2 triggers)
        assert "short text" in tc[0].content
        assert "another short one" in tc[0].content
        assert tc[0].content.count(" ") == 3

        # Chunk 1: long p2 (carried) + brief (14 spaces; p4 triggers)
        assert "this is a really long paragraph" in tc[1].content
        assert "brief" in tc[1].content
        assert tc[1].content.count(" ") == 14

        # Chunk 2: medium + more + and even (14 spaces; p7 triggers)
        assert "medium length paragraph here" in tc[2].content
        assert "more text to add here now" in tc[2].content
        assert "and even more text continues here today" in tc[2].content
        assert tc[2].content.count(" ") == 14

        # Chunk 3: one more paragraph (carried) + final words
        assert "one more paragraph" in tc[3].content
        assert "final words" in tc[3].content

        # All paragraphs must appear in output
        all_content = "".join(c.content for c in tc)
        for p in paragraphs:
            assert p in all_content, f"Paragraph '{p}' missing from output"

    def test_no_paragraph_lost_on_split(self):
        """Reproduces the reported bug: a middle paragraph that triggers a
        maxwords split must be carried over, not discarded.

        Three paragraphs where the second is long enough to exceed maxwords
        when combined with the first. All three must appear in the output.
        """
        p1 = "Boss, other people might have appended, almost automatically, but never her."
        p2 = "He straightened up, sighing, and joined her standing pretty much exactly where he thought she would have ended up, right next to the well, though keeping a careful distance between herself and its creepy coated sides."
        p3 = "Why? Oh, right no, no point that is why I volunteered, so those dumbasses would not try."
        html = f"<p>{p1}</p><p>{p2}</p><p>{p3}</p>"
        chunker = Chunker(maxps=20, maxwords=20)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        # The critical assertion: no paragraph is lost
        all_content = "".join(c.content for c in tc)
        assert p1 in all_content, "First paragraph missing from output"
        assert p2 in all_content, "Second paragraph (triggering paragraph) missing from output"
        assert p3 in all_content, "Third paragraph missing from output"

        # Verify split actually happened (p2 should trigger maxwords)
        assert len(tc) >= 2, "Expected at least 2 chunks due to maxwords split"

    def test_very_long_text_exact_content_verification(self):
        """50 paragraphs with maxps=8, maxwords=200. Verifies the exact
        content string of every output chunk — not just containment but
        character-for-character equality — including newlines and spacing.

        With maxps=8 every 8th paragraph triggers a split and is carried
        over to the next chunk. No paragraphs are lost.
        Expected: 7 text chunks (6 from maxps triggers + 1 final).
        """
        num_paras = 50
        maxps = 8
        maxwords = 200
        paras = [f"Para {i}" for i in range(num_paras)]
        html = self._paras_to_html(paras)
        chunker = Chunker(maxps=maxps, maxwords=maxwords)
        result = chunker.chunkit([_make_chunk(html)])
        tc = self._text_chunks(result)

        # ---- Build expected content strings independently ----
        # This mirrors the FIXED paragraph-accumulation logic of chunkit
        # where triggering paragraphs are carried over to the next chunk.
        expected_contents: list[str] = []
        chunktext = ""
        paracount = 0
        for text in paras:
            if chunktext != "":
                chunktext += "\n"           # line A in chunkit
            paracount += 1
            if (chunktext.count(" ") + text.count(" ")) > maxwords or paracount >= maxps:
                expected_contents.append(chunktext)   # trigger → output
                chunktext = "\n" + text               # carry over triggering paragraph
                paracount = 1
            else:
                chunktext += "\n" + text              # accumulate
        if chunktext != "":
            expected_contents.append(chunktext)       # final remainder

        # ---- Number of chunks ----
        assert len(tc) == len(expected_contents), (
            f"Expected {len(expected_contents)} chunks, got {len(tc)}"
        )

        # ---- Exact content for every chunk ----
        for i, (chunk, expected) in enumerate(zip(tc, expected_contents)):
            assert chunk.content == expected, (
                f"Chunk {i} content mismatch:\n"
                f"  expected: {expected!r}\n"
                f"  actual:   {chunk.content!r}"
            )

        # ---- Spot-check a few specific content values ----
        # With maxps=8 and carry-over, each chunk has 7 paragraphs:
        # carried (paracount=1) + 6 accumulated (paracount 2-7), then the
        # 7th new paragraph triggers the next split.
        # Chunk 0: Paras 0-6 accumulated; Para 7 triggers split (carried to chunk 1)
        assert tc[0].content == "\n" + "\n\n".join(f"Para {i}" for i in range(7)) + "\n"
        # Chunk 1: Para 7 (carried) + Paras 8-13; Para 14 triggers (carried to chunk 2)
        assert tc[1].content == "\n" + "\n\n".join(f"Para {i}" for i in range(7, 14)) + "\n"
        # Last chunk: Para 49 (carried, end of input, no trailing \n)
        assert tc[-1].content == "\nPara 49"

        # ---- All paragraphs must appear in output ----
        all_content = "".join(c.content for c in tc)
        for i in range(num_paras):
            assert f"Para {i}" in all_content, f"Para {i} missing from output"

        # ---- Structural checks on every chunk ----
        for i, chunk in enumerate(tc):
            assert chunk.chunktype == "text"
            assert chunk.chunk_id == i
            assert chunk.source_chaptername == "ch1"
            assert chunk.chapter_id == 1
