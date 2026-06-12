"""Unit-aliasing tests for the nutrition resolver.

The key bug these guard against: USDA portion labels are inconsistent across foods
(salt -> "teaspoon", cinnamon -> "tsp"), so a single user-typed unit must match either
spelling. See app/services/nutrition.py.
"""

from dataclasses import dataclass

from app.services.nutrition import resolve_grams


@dataclass
class FakePortion:
    description: str | None = None
    modifier: str | None = None
    amount: float | None = 1.0
    gram_weight: float | None = None


def test_tsp_matches_teaspoon_labeled_portion():
    # salt-style portion
    portions = [FakePortion(description="teaspoon", amount=1.0, gram_weight=6.0)]
    grams, reason = resolve_grams(2, "tsp", portions)
    assert reason is None
    assert grams == 12.0


def test_teaspoon_matches_tsp_labeled_portion():
    # cinnamon-style portion (reverse of above)
    portions = [FakePortion(description="tsp", amount=1.0, gram_weight=2.6)]
    grams, reason = resolve_grams(1, "teaspoon", portions)
    assert reason is None
    assert grams == 2.6


def test_one_unit_matches_both_spellings_in_same_recipe():
    salt = [FakePortion(description="teaspoon", amount=1.0, gram_weight=6.0)]
    cinnamon = [FakePortion(description="tsp", amount=1.0, gram_weight=2.6)]
    assert resolve_grams(1, "tsp", salt)[1] is None
    assert resolve_grams(1, "tsp", cinnamon)[1] is None


def test_plural_and_abbreviation_equivalence():
    portions = [FakePortion(description="cup", amount=1.0, gram_weight=240.0)]
    assert resolve_grams(1, "cup", portions)[0] == 240.0
    assert resolve_grams(1, "cups", portions)[0] == 240.0
    assert resolve_grams(1, "c", portions)[0] == 240.0


def test_case_sensitive_t_vs_T():
    teaspoon_food = [FakePortion(description="teaspoon", amount=1.0, gram_weight=6.0)]
    tablespoon_food = [FakePortion(description="tablespoon", amount=1.0, gram_weight=18.0)]
    # lowercase t -> teaspoon, uppercase T -> tablespoon
    assert resolve_grams(1, "t", teaspoon_food)[0] == 6.0
    assert resolve_grams(1, "T", tablespoon_food)[0] == 18.0
    # and they must NOT cross-match
    assert resolve_grams(1, "T", teaspoon_food)[1] == "unit_unmatched"
    assert resolve_grams(1, "t", tablespoon_food)[1] == "unit_unmatched"


def test_mass_units_unchanged():
    assert resolve_grams(100, "g", [])[0] == 100.0
    assert resolve_grams(100, "grams", [])[0] == 100.0
    assert resolve_grams(1, "oz", [])[0] == 28.3495


def test_unknown_unit_unmatched():
    portions = [FakePortion(description="cup", amount=1.0, gram_weight=240.0)]
    assert resolve_grams(1, "blorp", portions)[1] == "unit_unmatched"


def test_no_false_positive_substring():
    # "cup" must not match a "cupcake" portion (old substring bug)
    portions = [FakePortion(description="cupcake", amount=1.0, gram_weight=50.0)]
    assert resolve_grams(1, "cup", portions)[1] == "unit_unmatched"


def test_multiword_portion_label_token_match():
    portions = [FakePortion(description="1 large", amount=1.0, gram_weight=50.0)]
    assert resolve_grams(2, "large", portions)[0] == 100.0
