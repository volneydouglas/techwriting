from techlint import Config, lint_text
from techlint.finding import Severity


def find(text, rule, **kw):
    findings, _sup, _rep = lint_text(text, config=Config(**kw))
    return [f for f in findings if f.rule == rule]


class TestSentenceLength:
    LONG = ("The maintenance technician located at the central facility must "
            "carefully examine each and every one of the connecting elements "
            "that attach the auxiliary pump assembly to the primary mounting "
            "bracket structure on the lower panel of the main unit before the "
            "next scheduled inspection window closes for the quarter.")

    def test_well_over_budget_is_minor(self):
        hits = find(self.LONG, "CLARITY-LENGTH")
        assert hits and hits[0].severity == Severity.MINOR

    def test_slightly_over_budget_is_info_only(self):
        text = " ".join(["word"] * 33) + "."
        hits = find(text, "CLARITY-LENGTH")
        assert hits and hits[0].severity == Severity.INFO

    def test_procedure_mode_is_stricter(self):
        text = ("Remove the six bolts and then remove the panel and put it on "
                "the flat workbench beside the large toolbox now please.")
        assert find(text, "CLARITY-LENGTH", mode="procedure")
        assert not find(text, "CLARITY-LENGTH", mode="narrative")

    def test_short_sentence_ok(self):
        assert not find("Remove the panel.", "CLARITY-LENGTH")


class TestPassiveVoice:
    def test_named_agent_flagged_in_any_mode(self):
        hits = find("The config is read by the daemon at startup.", "CLARITY-PASSIVE")
        assert hits and hits[0].severity == Severity.MINOR

    def test_agentless_obligation_flagged_in_procedures(self):
        text = "The temperature must be adjusted before the run."
        assert find(text, "CLARITY-PASSIVE", mode="procedure")

    def test_spec_passive_not_flagged_in_reference_mode(self):
        # Calibration: RFC 793 is legitimately full of these.
        text = "The URG flag is set when urgent data is sent."
        assert not find(text, "CLARITY-PASSIVE", mode="reference")

    def test_state_adjectives_not_passive(self):
        assert not find("The field is required.", "CLARITY-PASSIVE", mode="procedure")
        assert not find("The method is deprecated.", "CLARITY-PASSIVE", mode="procedure")

    def test_imperative_suggestion_uses_real_base_form(self):
        hits = find("The value must be ensured.", "CLARITY-PASSIVE", mode="procedure")
        assert hits and "Ensure" in hits[0].suggestion

    def test_configured_base_form(self):
        hits = find("The proxy must be configured first.", "CLARITY-PASSIVE",
                    mode="procedure")
        assert hits and "Configure" in hits[0].suggestion

    def test_active_is_clean(self):
        assert not find("The daemon reads the config at startup.", "CLARITY-PASSIVE")


class TestPlainLanguage:
    def test_nominalization(self):
        hits = find("Perform a calculation of the checksum.", "CLARITY-NOMINAL")
        assert hits and "calculate" in hits[0].suggestion

    def test_wordiness(self):
        hits = find("In order to proceed, restart the service.", "CLARITY-WORDY")
        assert hits and hits[0].suggestion == '"to"'

    def test_utilize(self):
        assert find("Utilize the cache for repeat queries.", "CLARITY-WORDY")

    def test_plain_verb_not_flagged(self):
        assert not find("Calculate the checksum.", "CLARITY-NOMINAL")


class TestGopenSwan:
    def test_subject_verb_distance(self):
        text = ("The configuration file, which the installer writes during the "
                "first run and which several later steps depend on, is stored "
                "in the data directory.")
        assert find(text, "CLARITY-SVDIST")

    def test_adjacent_subject_verb_ok(self):
        assert not find("The configuration file is stored in the data directory.",
                        "CLARITY-SVDIST")

    def test_weak_stress_position(self):
        text = ("The service retries the request three times before it gives up "
                "and reports the failure, in most cases.")
        assert find(text, "CLARITY-STRESS")


class TestConventions:
    def test_latin_abbreviation(self):
        assert find("Discard temporary files (e.g., logs).", "CLARITY-LATIN")

    def test_latin_can_be_allowed(self):
        assert not find("Discard temporary files (e.g., logs).", "CLARITY-LATIN",
                        style={"latin_abbreviations": "allow"})

    def test_gendered_pronoun(self):
        assert find("The user must enter his password.", "CLARITY-INCLUSIVE")

    def test_neutral_is_clean(self):
        assert not find("The user must enter their password.", "CLARITY-INCLUSIVE")

    def test_non_inclusive_compound(self):
        hits = find("Add the address to the whitelist.", "CLARITY-INCLUSIVE")
        assert hits and "allowlist" in hits[0].suggestion

    def test_normative_keywords_in_procedures(self):
        assert find("The client should retry the request.", "CLARITY-NORMATIVE",
                    mode="procedure")
        assert not find("The client should retry the request.", "CLARITY-NORMATIVE",
                        mode="reference")

    def test_locale_us(self):
        hits = find("Check the colour of the badge.", "CLARITY-LOCALE")
        assert hits and hits[0].suggestion == "color"

    def test_locale_gb(self):
        hits = find("Check the color of the badge.", "CLARITY-LOCALE", locale="gb")
        assert hits and hits[0].suggestion == "colour"

    def test_contractions_allowed_by_default(self):
        assert not find("Don't remove the cover.", "CLARITY-CONTRACTION")

    def test_contractions_can_be_flagged(self):
        assert find("Don't remove the cover.", "CLARITY-CONTRACTION",
                    style={"contractions": "flag"})

    def test_dropped_that(self):
        hits = find("Make sure the valve is open.", "CLARITY-THAT")
        assert hits and "that" in hits[0].suggestion
        assert not find("Make sure that the valve is open.", "CLARITY-THAT")

    def test_imperative_with_plain_object_is_clean(self):
        # Found by dogfooding: "check the log" takes an object, not a clause,
        # so it needs no "that".
        assert not find("Check the agent log at /var/log/app.log.", "CLARITY-THAT")
        assert not find("Verify the checksum before you install.", "CLARITY-THAT")

    def test_clause_after_other_verbs_still_flagged(self):
        assert find("Confirm all the replicas have synced.", "CLARITY-THAT")
        assert find("Verify the service is running.", "CLARITY-THAT")


class TestRemovedAviationRules:
    """Rules that only made sense inside the ASD-STE100 controlled vocabulary."""

    def test_semicolons_allowed(self):
        findings, _s, _r = lint_text("Remove the cover; install the seal.",
                                     config=Config())
        assert not any("semicolon" in f.message.lower() for f in findings)

    def test_perfect_tense_allowed(self):
        findings, _s, _r = lint_text("The operator has adjusted the linkage.",
                                     config=Config())
        assert not any(f.rule.startswith("STE") for f in findings)

    def test_progressive_tense_allowed(self):
        findings, _s, _r = lint_text("The pressure is increasing quickly.",
                                     config=Config())
        assert not any("progressive" in f.message.lower() for f in findings)

    def test_no_approved_word_dictionary(self):
        # "chip -> PARTICLE" and friends are gone.
        findings, _s, _r = lint_text("Examine the chip and the panel.",
                                     config=Config())
        assert not any(f.rule == "STE-DICT" for f in findings)
