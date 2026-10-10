import pytest

from helpers import make_core
from kundli.yogas.engine import RuleError, chart_functions, evaluate, evaluate_yogas, load_rules

RAJA_NEG = {"Sun": 11, "Moon": 10, "Mars": 0, "Mercury": 8, "Jupiter": 1, "Venus": 4, "Saturn": 8, "Rahu": 11}

# (yoga id, lagna, positive placement, negative placement) -- every case worked by hand in the comments
CASES = [
    ("ruchaka", 0, {"Mars": 9}, {"Mars": 2}),                    # Mars exalted Capricorn, 10th | Gemini 3rd
    ("bhadra", 5, {"Mercury": 5}, {"Mercury": 8}),               # Mercury own/exalted Virgo, lagna | Sagittarius
    ("hamsa", 0, {"Jupiter": 3}, {"Jupiter": 6}),                # Jupiter exalted Cancer 4th | Libra
    ("malavya", 0, {"Venus": 6}, {"Venus": 11}),                 # Venus own Libra 7th | Pisces is 12th (not kendra)
    ("sasa", 0, {"Saturn": 9}, {"Saturn": 2}),                   # Saturn own Capricorn 10th | Gemini
    ("gajakesari", 0, {"Moon": 0, "Jupiter": 3}, {"Moon": 0, "Jupiter": 1}),
    ("budhaditya", 0, {"Sun": 4, "Mercury": 4}, {"Sun": 4, "Mercury": 5}),
    ("chandra_mangala", 0, {"Moon": 1, "Mars": 1}, {"Moon": 1, "Mars": 2}),
    ("kemadruma", 0, {"Moon": 0, "Mars": 2, "Mercury": 2, "Jupiter": 2, "Venus": 2, "Saturn": 2},
     {"Moon": 0, "Mars": 1, "Mercury": 2, "Jupiter": 2, "Venus": 2, "Saturn": 2}),
    ("sunapha", 0, {"Moon": 0, "Jupiter": 1}, {"Moon": 0, "Jupiter": 5, "Mars": 5, "Mercury": 5, "Venus": 5, "Saturn": 5}),
    ("anapha", 0, {"Moon": 0, "Mars": 11}, {"Moon": 0, "Mars": 5, "Jupiter": 5, "Venus": 5, "Saturn": 5, "Mercury": 5}),
    ("durudhura", 0, {"Moon": 0, "Mars": 11, "Jupiter": 1}, {"Moon": 0, "Mars": 11, "Jupiter": 5, "Venus": 5, "Saturn": 5, "Mercury": 5}),
    ("parivartana", 0, {"Mars": 1, "Venus": 0}, {"Mars": 0, "Venus": 1, "Moon": 3, "Sun": 4, "Mercury": 5, "Jupiter": 8, "Saturn": 9}),
    ("kaal_sarpa", 0, {"Rahu": 0, "Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4, "Jupiter": 5, "Venus": 1, "Saturn": 2},
     {"Rahu": 0, "Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4, "Jupiter": 5, "Venus": 1, "Saturn": 8}),
    ("mangal_lagna", 0, {"Mars": 3}, {"Mars": 2}),                # 4th from lagna | 3rd
    ("guru_chandala", 0, {"Jupiter": 5, "Rahu": 5}, {"Jupiter": 5, "Rahu": 4}),
    ("grahan_surya", 0, {"Sun": 2, "Rahu": 8}, {"Sun": 2, "Rahu": 4}),
    ("grahan_chandra", 0, {"Moon": 2, "Rahu": 8}, {"Moon": 2, "Rahu": 4}),
    ("shakata", 0, {"Jupiter": 0, "Moon": 5}, {"Jupiter": 0, "Moon": 3}),   # Moon 6th from Jupiter | 4th
    ("daridra", 0, {"Saturn": 5}, {"Saturn": 9}),                 # 11th lord Saturn in 6th | in 10th
    ("raja_kendra_trikona", 0, {"Sun": 3, "Moon": 3}, RAJA_NEG),  # Moon (kendra) with Sun (trikona)
    ("yogakaraka", 1, {}, {}),                                    # Taurus lagna: Saturn rules 9th+10th (special-cased below)
    ("dhana_2_11", 0, {"Venus": 1, "Saturn": 1}, {"Venus": 1, "Saturn": 9}),
    ("harsha", 0, {"Mercury": 7}, {"Mercury": 2}),                # 6th lord Mercury in 8th | 3rd
    ("sarala", 0, {"Mars": 5}, {"Mars": 2}),                      # 8th lord Mars in 6th | 3rd
    ("vimala", 0, {"Jupiter": 7}, {"Jupiter": 2}),                # 12th lord Jupiter in 8th | 3rd
    ("amala", 0, {"Jupiter": 9, "Sun": 4, "Mars": 2, "Mercury": 2, "Venus": 2, "Saturn": 2, "Moon": 3},
     {"Jupiter": 9, "Saturn": 9, "Sun": 4, "Mars": 2, "Mercury": 2, "Venus": 2, "Moon": 3}),
    ("adhi", 0, {"Moon": 0, "Mercury": 5, "Venus": 6}, {"Moon": 0, "Jupiter": 7, "Mercury": 2, "Venus": 2}),
    ("neecha_bhanga_saturn", 0, {"Saturn": 0, "Mars": 6, "Sun": 5, "Moon": 1}, {"Saturn": 0, "Mars": 2, "Sun": 5, "Moon": 1}),
    ("pitru_sun_node", 0, {"Sun": 4, "Rahu": 4}, {"Sun": 4, "Rahu": 3}),
    ("pitru_ninth", 0, {"Rahu": 8}, {"Rahu": 3, "Mars": 2, "Jupiter": 11}),
]


def _get(core, yid):
    return {y["id"]: y for y in evaluate_yogas(core)}[yid]


@pytest.mark.parametrize("yid,lagna,pos,neg", CASES, ids=[c[0] for c in CASES])
def test_yoga_positive_and_negative(yid, lagna, pos, neg):
    if yid == "yogakaraka":
        assert _get(make_core(1, {}), yid)["present"] and _get(make_core(1, {}), yid)["planets_involved"] == ["Saturn"]
        assert not _get(make_core(0, {}), yid)["present"]
        return
    assert _get(make_core(lagna, pos), yid)["present"], f"{yid} should be present"
    assert not _get(make_core(lagna, neg), yid)["present"], f"{yid} should be absent"


def test_cancellations():
    # Mars in 4th (Cancer) is debilitated -> not cancelled by itself; mangal present, jupiter conj Mars cancels
    y = _get(make_core(0, {"Mars": 3, "Jupiter": 3}), "mangal_lagna")
    assert y["present"] and "jupiter_conjunct_or_aspects_mars" in y["cancelled_by"] and not y["effective"]
    y = _get(make_core(0, {"Mars": 7}), "mangal_lagna")                         # 8th house, own sign Scorpio
    assert "mars_own_or_exalted" in y["cancelled_by"]
    y = _get(make_core(0, {"Moon": 0, "Jupiter": 3}), "gajakesari")             # Jupiter exalted: no cancellation
    assert y["effective"] and y["cancelled_by"] == []
    y = _get(make_core(0, {"Moon": 0, "Jupiter": 9}), "gajakesari")             # Jupiter debilitated Capricorn
    assert y["present"] and "jupiter_debilitated" in y["cancelled_by"]
    y = _get(make_core(0, {"Jupiter": 0, "Moon": 5}), "shakata")
    assert y["effective"]
    y = _get(make_core(0, {"Jupiter": 0, "Moon": 6}), "shakata")                # Moon 7th from Jupiter -> not shakata
    assert not y["present"]
    y = _get(make_core(0, {"Jupiter": 0, "Moon": 9, "Saturn": 9}), "shakata")   # Moon 10th from Jupiter
    assert not y["present"]
    y = _get(make_core(0, {"Jupiter": 11, "Moon": 5}), "shakata")               # 7th from Jupiter at 11 -> 5 is 7th
    assert not y["present"]
    y = _get(make_core(0, {"Jupiter": 11, "Moon": 4}), "shakata")               # 6th from Jupiter, Moon 5th from lagna
    assert y["present"] and y["effective"]


def test_kemadruma_cancellation():
    base = {"Moon": 0, "Mars": 2, "Mercury": 2, "Jupiter": 2, "Venus": 2, "Saturn": 2}
    y = _get(make_core(0, base), "kemadruma")
    assert y["present"] and "moon_in_kendra" in y["cancelled_by"]        # Moon in lagna (kendra) cancels
    y = _get(make_core(0, {**base, "Moon": 1, "Mars": 3, "Mercury": 3, "Jupiter": 3, "Venus": 3, "Saturn": 3}), "kemadruma")
    assert y["present"]


def test_yoga_rule_files_are_complete_and_sourced():
    rules = load_rules()
    assert len(rules) >= 30
    for r in rules:
        assert {"id", "name", "category", "condition", "source"} <= set(r)
    ids = {y["id"] for y in evaluate_yogas(make_core(0, {}))}
    for need in ("ruchaka", "bhadra", "hamsa", "malavya", "sasa", "gajakesari", "budhaditya", "chandra_mangala", "adhi",
                 "amala", "harsha", "kemadruma", "sunapha", "anapha", "durudhura", "parivartana", "kaal_sarpa",
                 "mangal_lagna", "pitru_sun_node", "guru_chandala", "grahan_surya", "shakata", "daridra",
                 "raja_kendra_trikona", "dhana_2_11", "neecha_bhanga_saturn"):
        assert need in ids


def test_every_yoga_result_has_required_fields():
    for y in evaluate_yogas(make_core(0, {})):
        assert {"present", "strength", "planets_involved", "cancelled_by", "source"} <= set(y)


# ---- safe evaluator ----
@pytest.mark.parametrize("bad", ["__import__('os').system('true')", "(1).__class__", "open('x')",
                                 "[x for x in range(3)]", "lambda: 1", "jupiter.house", "house(mars)[0]",
                                 "unknown_name", "len.__call__([])", "1 if True else 2", "f'{1}'", "{'a': 1}"])
def test_evaluator_rejects_unsafe_syntax(bad):
    fns = chart_functions(make_core(0, {}))
    with pytest.raises((RuleError, SyntaxError)):
        evaluate(bad, fns)


def test_evaluator_basic():
    fns = chart_functions(make_core(0, {"Mars": 9}))
    assert evaluate("house(mars) == 10 and not retro(mars)", fns)
    assert evaluate("house_from(jupiter, moon) in [1, 4, 7, 10] or 1 < 2", fns)
