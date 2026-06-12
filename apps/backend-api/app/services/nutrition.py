"""Compute per-serving nutrition for a recipe from its linked USDA foods.

USDA macros are stored per 100 g, so each recipe line must be converted to grams
before scaling. Mass units convert directly; volume/count units ("cup", "1 large")
need the food's USDA household-measure portions. Anything that can't be resolved is
reported in `Macros.unresolved` rather than silently dropped, so the displayed
totals stay trustworthy.
"""

import re
from dataclasses import dataclass, field

# Macro columns on the Food model that we sum (all expressed per 100 g).
NUTRIENT_FIELDS = (
    "energy_kcal",
    "protein_g",
    "fat_g",
    "sat_fat_g",
    "carbs_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
)

# Direct mass -> grams. Volume/count units are intentionally absent: their gram
# weight is food-specific and comes from food_portions instead.
MASS_TO_GRAMS = {
    "mg": 0.001,
    "g": 1.0, "gram": 1.0, "grams": 1.0, "gm": 1.0, "gms": 1.0,
    "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
    "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
    "lb": 453.592, "lbs": 453.592, "pound": 453.592, "pounds": 453.592,
}

# Volume/count units have no fixed gram weight (it's food-specific, from food_portions),
# but their *spelling* is wildly inconsistent — both in user input ("tsp" vs "teaspoon")
# and in the USDA portion labels themselves (salt uses "teaspoon", cinnamon uses "tsp").
# Group every spelling under one canonical unit so a single user-typed unit can match a
# portion regardless of which spelling either side happens to use.
UNIT_SYNONYMS = {
    "teaspoon":    {"teaspoon", "teaspoons", "tsp", "tsp.", "ts"},
    "tablespoon":  {"tablespoon", "tablespoons", "tbsp", "tbsp.", "tbs", "tbl"},
    "cup":         {"cup", "cups", "c"},
    # NOTE: bare "t"/"T" are NOT listed here — they are case-sensitive (see _CASE_SENSITIVE)
    # because lowercasing would collapse teaspoon and tablespoon together.
    "pint":        {"pint", "pints", "pt"},
    "quart":       {"quart", "quarts", "qt"},
    "gallon":      {"gallon", "gallons", "gal"},
    "fluid ounce": {"fluid ounce", "fluid ounces", "fl oz", "floz", "fl. oz."},
    "milliliter":  {"milliliter", "milliliters", "millilitre", "millilitres", "ml"},
    "liter":       {"liter", "liters", "litre", "litres", "l"},
    "stick":       {"stick", "sticks"},
    "clove":       {"clove", "cloves"},
    "slice":       {"slice", "slices"},
}
_ALIAS_TO_CANON = {alias: canon for canon, aliases in UNIT_SYNONYMS.items() for alias in aliases}

# Single-letter units whose meaning depends on case (cooking convention):
# lowercase "t" = teaspoon, uppercase "T" = tablespoon.
_CASE_SENSITIVE = {"t": "teaspoon", "T": "tablespoon"}


@dataclass
class Macros:
    energy_kcal: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    sat_fat_g: float = 0.0
    carbs_g: float = 0.0
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    servings: float = 1.0
    # Ingredient names that have no food link or no resolvable unit.
    unresolved: list[str] = field(default_factory=list)


def _singular(unit: str) -> str:
    return unit[:-1] if unit.endswith("s") and len(unit) > 1 else unit


def _unit_aliases(unit_raw: str) -> set[str]:
    """All known spellings of a user-entered unit, for matching against portion labels.

    Takes the *raw* (un-lowercased) unit so the case-sensitive "t"/"T" pair can be told
    apart before everything else is folded to lowercase. Unknown units fall back to their
    own singular/plural forms, preserving the original behavior.
    """
    stripped = unit_raw.strip()
    canon = _CASE_SENSITIVE.get(stripped)  # exact bare "t"/"T" only
    if not canon:
        u = stripped.lower()
        canon = _ALIAS_TO_CANON.get(u) or _ALIAS_TO_CANON.get(_singular(u))
        if not canon:
            return {u, _singular(u)}
    return set(UNIT_SYNONYMS[canon])


def _portion_grams_per_unit(unit_raw: str, portions) -> float | None:
    """Grams for one of `unit_raw` using the food's USDA portions, or None."""
    aliases = _unit_aliases(unit_raw)
    for p in portions:
        if p.gram_weight is None:
            continue
        haystack = " ".join(filter(None, [p.modifier, p.description])).lower().strip()
        if not haystack:
            continue
        tokens = set(re.findall(r"[a-z]+", haystack))
        if aliases & tokens or haystack in aliases:
            amount = float(p.amount) if p.amount else 1.0
            if amount == 0:
                continue
            return float(p.gram_weight) / amount
    return None


def resolve_grams(quantity, unit, portions) -> tuple[float | None, str | None]:
    """Convert a recipe-line quantity+unit to grams.

    Returns (grams, None) on success, or (None, reason) where reason is one of
    'no_quantity', 'no_unit', 'unit_unmatched' — so callers can explain the failure.
    """
    if quantity is None:
        return None, "no_quantity"
    unit_raw = (unit or "").strip()
    if not unit_raw:
        return None, "no_unit"
    qty = float(quantity)
    if unit_raw.lower() in MASS_TO_GRAMS:
        return qty * MASS_TO_GRAMS[unit_raw.lower()], None
    per_unit = _portion_grams_per_unit(unit_raw, portions)
    if per_unit is not None:
        return qty * per_unit, None
    return None, "unit_unmatched"


def to_grams(quantity, unit, portions) -> float | None:
    """Convert a recipe-line quantity+unit to grams, or None if unresolvable."""
    return resolve_grams(quantity, unit, portions)[0]


def supported_units(portions) -> list[str]:
    """Distinct human-friendly measure labels for a food, drawn from its USDA portions.

    These are the volume/count units (e.g. "cup", "tablespoon") that can be converted
    for this specific food; mass units (g, oz, lb, kg) always work regardless.
    """
    out: list[str] = []
    seen: set[str] = set()
    for p in portions:
        if p.gram_weight is None:
            continue
        label = (p.description or p.modifier or "").strip()
        if label and label.lower() not in seen:
            seen.add(label.lower())
            out.append(label)
    return out


def _servings(metadata) -> float:
    if isinstance(metadata, dict):
        raw = metadata.get("servings")
        try:
            val = float(raw)
            if val > 0:
                return val
        except (TypeError, ValueError):
            pass
    return 1.0


@dataclass
class MacroLine:
    """One recipe line for macro computation: its linked food (or None), amount and name."""

    food: object | None
    quantity: float | None
    unit: str | None
    name: str


def compute_macros(lines, servings: float) -> Macros:
    """Sum per-serving macros across recipe lines.

    Each line carries its linked `food` (with `.portions` loaded and the per-100 g
    NUTRIENT_FIELDS) plus `quantity`/`unit`/`name`. Lines with no food link or no
    resolvable unit are listed in `unresolved` and contribute nothing.
    """
    totals = {f: 0.0 for f in NUTRIENT_FIELDS}
    unresolved: list[str] = []

    for line in lines:
        food = line.food
        if food is None:
            unresolved.append(line.name)
            continue
        grams = to_grams(line.quantity, line.unit, food.portions)
        if grams is None:
            unresolved.append(line.name)
            continue
        scale = grams / 100.0
        for f in NUTRIENT_FIELDS:
            value = getattr(food, f)
            if value is not None:
                totals[f] += float(value) * scale

    servings = servings if servings and servings > 0 else 1.0
    per_serving = {f: round(totals[f] / servings, 2) for f in NUTRIENT_FIELDS}
    return Macros(servings=servings, unresolved=unresolved, **per_serving)


def recipe_macros(recipe) -> Macros:
    """Sum per-serving macros across a recipe's ingredients.

    Requires recipe_ingredients -> ingredient -> food (+ food.portions) to be
    loaded. Ingredients with no food link or no resolvable unit are listed in
    `unresolved` and contribute nothing.
    """
    lines = [
        MacroLine(
            food=ri.ingredient.food if ri.ingredient else None,
            quantity=ri.quantity,
            unit=ri.unit,
            name=ri.ingredient.name if ri.ingredient else "unknown",
        )
        for ri in recipe.recipe_ingredients
    ]
    return compute_macros(lines, _servings(recipe.recipie_metadata))
