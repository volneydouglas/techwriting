"""Documentation-convention rules drawn from the major style guides."""

from techlint import Config, lint_file, lint_text


def find(text, rule, **kw):
    findings, _sup, _rep = lint_text(text, config=Config(**kw))
    return [f for f in findings if f.rule == rule]


class TestLinkText:
    def test_click_here_flagged(self):
        hits = find("For setup, [click here](setup.md).", "DOC-LINKTEXT")
        assert hits and "click here" in hits[0].extract.lower()

    def test_bare_here_flagged(self):
        assert find("See [here](setup.md) for details.", "DOC-LINKTEXT")

    def test_learn_more_flagged(self):
        assert find("[Learn more](x.md) about caching.", "DOC-LINKTEXT")

    def test_descriptive_text_ok(self):
        assert not find("Read the [cache configuration guide](x.md).", "DOC-LINKTEXT")

    def test_links_in_code_ignored(self):
        assert not find("```\n[click here](x.md)\n```\n", "DOC-LINKTEXT")


class TestCondescension:
    def test_adverbs_always_flagged(self):
        assert find("Simply run the installer.", "DOC-CONDESCEND")
        assert find("Obviously you need Python.", "DOC-CONDESCEND")
        assert find("Clearly this is the wrong port.", "DOC-CONDESCEND")

    def test_reader_directed_adjective_flagged(self):
        assert find("It is easy to configure the proxy.", "DOC-CONDESCEND")
        assert find("Setup is straightforward.", "DOC-CONDESCEND")

    def test_adjective_describing_a_thing_is_clean(self):
        # Calibration: RFCs use these constantly and correctly.
        assert not find("The algorithm uses a simple hash table.",
                        "DOC-CONDESCEND")
        assert not find("This is the Simple Mail Transfer Protocol section.",
                        "DOC-CONDESCEND")

    def test_temporal_just_is_clean(self):
        assert not find("The lock is released just before the retry.",
                        "DOC-CONDESCEND")
        assert not find("Run this just in time for the cutover.", "DOC-CONDESCEND")

    def test_filler_just_flagged(self):
        assert find("Just restart the service.", "DOC-CONDESCEND")


class TestPolitenessAndPhrasing:
    def test_please_note(self):
        assert find("Please note that the cache is disabled.", "DOC-PLEASE")

    def test_please_run(self):
        assert find("Please run the migration first.", "DOC-PLEASE")

    def test_allows_you_to(self):
        hits = find("The API allows you to filter results.", "DOC-ALLOWS")
        assert hits and "lets you" in hits[0].suggestion

    def test_enables_you_to(self):
        assert find("This enables you to batch requests.", "DOC-ALLOWS")


class TestAddressingTheReader:
    def test_third_person_flagged(self):
        assert find("The user must supply a token.", "DOC-PERSON")
        assert find("The developer should check the logs.", "DOC-PERSON")

    def test_second_person_clean(self):
        assert not find("You must supply a token.", "DOC-PERSON")

    def test_plain_noun_clean(self):
        assert not find("The scheduler must supply a token.", "DOC-PERSON")


class TestTense:
    def test_future_tense_flagged(self):
        hits = find("The endpoint will return a 404.", "DOC-TENSE")
        assert hits and "returns" in hits[0].suggestion

    def test_present_tense_clean(self):
        assert not find("The endpoint returns a 404.", "DOC-TENSE")

    def test_narrative_mode_exempt(self):
        assert not find("The endpoint will return a 404.", "DOC-TENSE",
                        mode="narrative")


class TestAcronyms:
    TEXT = ("The FQDN is resolved first. Every FQDN must be absolute. "
            "A second FQDN check runs later.")

    def test_off_by_default(self):
        # Calibration: too noisy to enable without a dictionary.
        assert not find(self.TEXT, "DOC-ACRONYM")

    def test_flagged_when_enabled(self):
        assert find(self.TEXT, "DOC-ACRONYM", budgets={"check_acronyms": True})

    def test_expanded_acronym_ok(self):
        text = ("The fully qualified domain name (FQDN) is resolved first. "
                "Every FQDN must be absolute. A third FQDN appears here.")
        assert not find(text, "DOC-ACRONYM", budgets={"check_acronyms": True})

    def test_well_known_exempt(self):
        text = "The API returns JSON over HTTPS. The API is versioned. API v2 exists."
        assert not find(text, "DOC-ACRONYM", budgets={"check_acronyms": True})

    def test_single_use_not_flagged(self):
        text = "The XYZ header is optional. Everything else is required here."
        assert not find(text, "DOC-ACRONYM", budgets={"check_acronyms": True})

    def test_vowel_heavy_caps_word_not_flagged(self):
        # "FILES", "TOTAL", "AREA" are emphasized words, not acronyms.
        text = "See FILES below. The FILES section lists them. FILES is long."
        assert not find(text, "DOC-ACRONYM", budgets={"check_acronyms": True})

    def test_known_acronyms_config(self):
        assert not find(self.TEXT, "DOC-ACRONYM",
                        budgets={"check_acronyms": True, "known_acronyms": ["FQDN"]})


class TestHeadingsAndImages:
    def test_skipped_heading_level(self):
        assert find("# Title\n\n### Deep\n\nBody text here.\n", "DOC-HEADING")

    def test_sequential_headings_ok(self):
        assert not find("# Title\n\n## Section\n\n### Sub\n\nBody.\n", "DOC-HEADING")

    def test_multiple_h1(self):
        assert find("# One\n\nBody.\n\n# Two\n\nMore body.\n", "DOC-HEADING")

    def test_missing_alt_text(self):
        hits = find("![](diagram.png)\n", "DOC-ALT")
        assert hits and "diagram.png" in hits[0].message

    def test_alt_text_present_ok(self):
        assert not find("![Request flow diagram](diagram.png)\n", "DOC-ALT")


class TestMinimalism:
    def test_late_first_instruction_in_procedure(self):
        preamble = ("This section describes the background of the deployment "
                    "system and its history in the organization. " * 12)
        text = preamble + "\n\nRun the installer."
        assert find(text, "DOC-ACTION", mode="procedure")

    def test_prompt_instruction_ok(self):
        assert not find("Run the installer. Then restart the service.",
                        "DOC-ACTION", mode="procedure")

    def test_reference_mode_exempt(self):
        preamble = ("This section describes the background of the deployment "
                    "system and its history in the organization. " * 12)
        assert not find(preamble, "DOC-ACTION", mode="reference")


class TestReadability:
    def test_dense_prose_flagged(self):
        text = " ".join(
            ["The instantiation of the aforementioned configuration "
             "abstraction necessitates comprehensive initialization "
             "procedures throughout the distributed infrastructure "
             "environment."] * 20)
        assert find(text, "DOC-READABILITY")

    def test_plain_prose_clean(self):
        text = " ".join(["The cache holds the last 100 results. "
                         "When it is full, the oldest one goes."] * 20)
        assert not find(text, "DOC-READABILITY")

    def test_short_document_skipped(self):
        assert not find("Short and dense instantiation abstraction.",
                        "DOC-READABILITY")

    def test_target_is_configurable(self):
        text = " ".join(["The cache holds the last 100 results. "
                         "When it is full, the oldest one goes."] * 20)
        assert find(text, "DOC-READABILITY", budgets={"grade_level": 0})


class TestBattery:
    def test_docs_battery_can_be_disabled(self):
        findings, _s, _r = lint_text(
            "Simply click [here](x.md).",
            config=Config(enable_docs=False, enable_ai=False,
                          enable_stats=False, enable_clarity=False))
        assert not [f for f in findings if f.rule.startswith("DOC-")]

    def test_convention_axis(self):
        _f, _s, rep = lint_text("Simply run it. The user must click [here](x.md).",
                                config=Config())
        assert rep["axes"]["convention"] > 0
