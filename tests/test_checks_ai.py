from techlint import Config, lint_text
from techlint.finding import Severity


def find(text, rule, **kw):
    findings, _sup, _rep = lint_text(text, config=Config(**kw))
    return [f for f in findings if f.rule == rule]


def rules(text, **kw):
    findings, _sup, _rep = lint_text(text, config=Config(**kw))
    return {f.rule for f in findings}


class TestArtifacts:
    def test_chat_frame_is_blocker(self):
        hits = find("As an AI language model, I cannot verify this.", "AI-ARTIFACT")
        assert hits and hits[0].severity == Severity.BLOCKER

    def test_pleasantry(self):
        assert find("I hope this helps! Let me know if you'd like more.", "AI-ARTIFACT")

    def test_unfilled_placeholder(self):
        assert find("Contact [Your Company Name] for support.", "AI-ARTIFACT")

    def test_unnamed_study(self):
        assert find("Studies show that caching improves latency.", "AI-ARTIFACT")

    def test_cited_claim_is_not_flagged(self):
        assert not find(
            "Studies show a 40% gain (Kobak et al. 2025).", "AI-ARTIFACT")


class TestVocabulary:
    def test_strong_tier_is_major(self):
        hits = find("This guide delves into the API.", "AI-VOCAB")
        assert hits and hits[0].severity == Severity.MAJOR
        assert hits[0].meta["tier"] == "strong"

    def test_ratio_is_reported(self):
        hits = find("The results underscore the value of caching.", "AI-VOCAB")
        assert hits and hits[0].meta["ratio"] > 5

    def test_mild_tier_not_reported_individually(self):
        # Calibration: mild-tier words appear in a 1981 RFC.
        assert not find("The client acknowledges the packet.", "AI-VOCAB")

    def test_domain_vocabulary_exempt(self):
        text = "This guide delves into the API."
        assert find(text, "AI-VOCAB")
        assert not find(text, "AI-VOCAB", domain_vocabulary={"delves"})

    def test_homograph_noun_use_exempt(self):
        # PEP 8 means the `_` character, not "emphasizes".
        assert not find("Names may use leading underscores.", "AI-VOCAB")
        assert not find("A double underscore triggers mangling.", "AI-VOCAB")
        # "the realm" is the Kerberos noun; the idiom "in the realm of" is
        # caught by the empty-transition phrase rule instead.
        assert not find("Set the realm before you authenticate.", "AI-VOCAB")

    def test_homograph_verb_use_flagged(self):
        assert find("This underscores the need for retries.", "AI-VOCAB")

    def test_plain_technical_prose_is_clean(self):
        text = ("The cache stores the last 100 results. When it is full, the "
                "oldest entry is removed first.")
        assert not [r for r in rules(text) if r.startswith("AI-")]


class TestPatterns:
    def test_throat_clearing(self):
        assert find("It is important to note that the cache is disabled.", "AI-PHRASE")

    def test_scene_setting(self):
        assert find("In today's fast-paced digital landscape, teams ship code.",
                    "AI-PHRASE")

    def test_antithesis_variants(self):
        # The general forms the first version of this tool missed.
        assert find("It's not just about speed, it's about reliability.", "AI-PHRASE")
        assert find("This isn't merely a cache. It is a coordination layer.",
                    "AI-PHRASE")
        assert find("It is more than just a linter.", "AI-PHRASE")

    def test_x_not_y_figure(self):
        assert find("This is a map, not a verdict.", "AI-PHRASE")

    def test_self_posed_qa(self):
        assert find("The result? Latency dropped by half.", "AI-PHRASE")

    def test_participial_editorial(self):
        assert find("Latency dropped, underscoring the value of caching.", "AI-PHRASE")

    def test_working_participle_not_flagged(self):
        # "allowing" does real work; calibration found it in pre-LLM prose.
        assert not find("The lock is released, allowing the client to retry.",
                        "AI-PHRASE")

    def test_importance_claim(self):
        assert find("Logging plays a crucial role in debugging.", "AI-PHRASE")

    def test_essay_closer(self):
        assert find("In conclusion, the system works well.", "AI-PHRASE")

    def test_copula_chain_is_blocker(self):
        hits = find("The problem was the latency, and the latency was the problem.",
                    "AI-COPULA")
        assert hits and hits[0].severity == Severity.BLOCKER


class TestStructural:
    def test_em_dash_budget(self):
        chunk = ("The system is fast — very fast — and reliable — always. " * 5
                 + "It also scales well with heavy traffic and many users. " * 12)
        assert find(chunk, "AI-DASH")

    def test_few_em_dashes_ok(self):
        text = "The system is fast — and reliable. " + "It works well every day. " * 20
        assert not find(text, "AI-DASH")

    def test_transition_openers(self):
        text = ("Moreover, the system is fast. Furthermore, it is reliable. "
                "Additionally, it is secure. It has good documentation too.")
        assert find(text, "AI-OPENER")

    def test_hedge_stack(self):
        assert find("This may possibly be somewhat faster in some cases.", "AI-HEDGE")

    def test_bold_term_list(self):
        text = "\n".join([
            "- **Speed:** Fast.", "- **Security:** Strong.",
            "- **Scale:** Big.", "- **Support:** Always.",
        ])
        assert find(text, "AI-BOLDLIST")

    def test_emoji(self):
        assert find("Deploy the service 🚀 to production.", "AI-EMOJI")

    def test_vocab_density(self):
        smelly = ("The comprehensive framework showcases notable advancements "
                  "and offers a robust approach that emphasizes seamless "
                  "integration while highlighting the pivotal capabilities. ") * 20
        assert find(smelly, "AI-VOCAB-DENSITY")


class TestScoring:
    def test_slop_scores_far_above_canon(self):
        slop = ("In today's fast-paced world, our robust platform delves into "
                "cutting-edge technology to seamlessly deliver comprehensive, "
                "transformative solutions. It's important to note that this "
                "journey unlocks unprecedented synergy. ") * 3
        _f, _s, rep = lint_text(slop, config=Config())
        assert rep["wscore"] > 25
        assert rep["verdict"] == "heavy"

    def test_ai_battery_can_be_disabled(self):
        findings, _s, _r = lint_text(
            "Let us delve into this.",
            config=Config(enable_ai=False, enable_stats=False))
        assert not [f for f in findings if f.rule.startswith("AI-")]
