from techlint.textmodel import parse


class TestParse:
    def test_sentences_split(self):
        doc = parse("The pump is on. The valve is open.")
        assert len(doc.sentences) == 2
        assert doc.sentences[1].text == "The valve is open."

    def test_no_split_on_decimal_or_abbrev(self):
        doc = parse("Set the timeout to 4.5 seconds. Refer to Fig. 3 for details.")
        assert len(doc.sentences) == 2

    def test_headings_excluded_from_prose(self):
        doc = parse("# A heading long enough to trip a sentence budget check\n\nBody text.")
        assert "heading" in [s.kind for s in doc.sentences]
        assert len(doc.prose_sentences()) == 1

    def test_code_blocks_skipped(self):
        doc = parse("Before.\n\n```\nnot prose; delve into this\n```\n\nAfter.")
        assert all("delve" not in s.text for s in doc.sentences)

    def test_inline_code_is_opaque(self):
        doc = parse("Run `foo --delve; bar` to start.")
        assert "delve" not in doc.sentences[0].text

    def test_tables_skipped(self):
        doc = parse("Text.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        assert len(doc.prose_sentences()) == 1

    def test_positions_track_source_lines(self):
        doc = parse("First line.\n\n\nParagraph on line four.")
        assert doc.sentences[0].line == 1
        assert doc.sentences[1].line == 4

    def test_pos_at_maps_offsets(self):
        doc = parse("alpha beta gamma.")
        s = doc.sentences[0]
        assert s.pos_at(0) == (1, 1)
        assert s.pos_at(6) == (1, 7)

    def test_bullets_are_separate_sentences(self):
        doc = parse("- first item\n- second item\n- third item")
        assert len(doc.sentences) == 3
        assert all(s.kind == "bullet" for s in doc.sentences)

    def test_paragraph_grouping(self):
        doc = parse("One. Two. Three.\n\nFour. Five.")
        prose = [p for p in doc.paragraphs if p.kind == "prose"]
        assert [len(p.sentences) for p in prose] == [3, 2]

    def test_word_count_excludes_headings(self):
        doc = parse("# Heading here\n\nOne two three four.")
        assert doc.word_count() == 4
