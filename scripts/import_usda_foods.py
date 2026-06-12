"""Download and import USDA FoodData Central SR Legacy + Foundation Foods.

Usage (from repo root):
    cd apps/backend-api && uv run python ../../scripts/import_usda_foods.py

Reads DATABASE_URL from the environment, falling back to the local dev default.
Re-running is safe: uses INSERT ... ON CONFLICT DO UPDATE (upsert by fdc_id).
"""

import asyncio
import io
import json
import os
import zipfile

import asyncpg
import requests

DATASETS = [
    (
        "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_json_2018-04.zip",
        "SRLegacyFoods",
    ),
    (
        "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2026-04-30.zip",
        "FoundationFoods",
    ),
]

# FDC nutrient IDs -> column name. Sugar has two candidates; both are tried.
NUTRIENT_MAP = {
    1008: "energy_kcal",
    1003: "protein_g",
    1004: "fat_g",
    1258: "sat_fat_g",
    1005: "carbs_g",
    1079: "fiber_g",
    2000: "sugar_g",
    1063: "sugar_g",  # SR Legacy uses 1063 for total sugars
    1093: "sodium_mg",
}

UPSERT_SQL = """
INSERT INTO foods (fdc_id, name, category, energy_kcal, protein_g, fat_g,
                   sat_fat_g, carbs_g, fiber_g, sugar_g, sodium_mg)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
ON CONFLICT (fdc_id) DO UPDATE SET
    name        = EXCLUDED.name,
    category    = EXCLUDED.category,
    energy_kcal = EXCLUDED.energy_kcal,
    protein_g   = EXCLUDED.protein_g,
    fat_g       = EXCLUDED.fat_g,
    sat_fat_g   = EXCLUDED.sat_fat_g,
    carbs_g     = EXCLUDED.carbs_g,
    fiber_g     = EXCLUDED.fiber_g,
    sugar_g     = EXCLUDED.sugar_g,
    sodium_mg   = EXCLUDED.sodium_mg
"""

PORTION_INSERT_SQL = """
INSERT INTO food_portions (fdc_id, description, modifier, amount, gram_weight)
VALUES ($1, $2, $3, $4, $5)
"""


def download_zip(url: str) -> bytes:
    print(f"  Downloading {url.split('/')[-1]} ...", flush=True)
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    buf = io.BytesIO()
    total = 0
    for chunk in resp.iter_content(chunk_size=1 << 20):
        buf.write(chunk)
        total += len(chunk)
        print(f"\r  {total // (1 << 20)} MB", end="", flush=True)
    print()
    return buf.getvalue()


def parse_foods(data: bytes, top_key: str) -> tuple[list[tuple], list[tuple]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        json_name = next(n for n in zf.namelist() if n.endswith(".json"))
        print(f"  Parsing {json_name} ...", flush=True)
        payload = json.loads(zf.read(json_name))

    rows = []
    portion_rows = []
    for food in payload[top_key]:
        if food is None:
            continue
        nutrients: dict[int, float] = {}
        for fn in food.get("foodNutrients", []):
            n = fn.get("nutrient", {})
            nid = n.get("id")
            amt = fn.get("amount")
            if nid in NUTRIENT_MAP and amt is not None:
                col = NUTRIENT_MAP[nid]
                # Don't overwrite a value already set by a higher-priority ID
                # (2000 is preferred over 1063 for sugar_g; 2000 appears first
                #  in Foundation but 1063 appears in SR Legacy with no 2000)
                if col not in {NUTRIENT_MAP[k] for k, v in nutrients.items()}:
                    nutrients[nid] = amt

        cat = food.get("foodCategory")
        category = cat.get("description") if isinstance(cat, dict) else cat

        def get(nid: int) -> float | None:
            return nutrients.get(nid)

        # Sugar: prefer 2000, fall back to 1063
        sugar = get(2000) if get(2000) is not None else get(1063)

        fdc_id = food["fdcId"]
        rows.append((
            fdc_id,
            food["description"],
            category,
            get(1008),  # energy_kcal
            get(1003),  # protein_g
            get(1004),  # fat_g
            get(1258),  # sat_fat_g
            get(1005),  # carbs_g
            get(1079),  # fiber_g
            sugar,
            get(1093),  # sodium_mg
        ))

        # Household measures (cups, tbsp, "1 large", ...) -> gram weight. These
        # are what make volume/count units convertible to grams downstream.
        for portion in food.get("foodPortions", []):
            gram_weight = portion.get("gramWeight")
            if gram_weight is None:
                continue
            measure = portion.get("measureUnit") or {}
            measure_name = measure.get("name")
            # Skip the USDA "undetermined" placeholder unit.
            if measure_name == "undetermined":
                measure_name = None
            description = portion.get("portionDescription") or measure_name
            portion_rows.append((
                fdc_id,
                description,
                portion.get("modifier"),
                portion.get("amount"),
                gram_weight,
            ))
    return rows, portion_rows


def chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def main() -> None:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://recipie:recipie@localhost:5432/recipie",
    ).replace("postgresql+asyncpg://", "postgresql://")

    all_rows: list[tuple] = []
    all_portions: list[tuple] = []
    for url, top_key in DATASETS:
        data = download_zip(url)
        rows, portions = parse_foods(data, top_key)
        print(f"  Parsed {len(rows)} foods, {len(portions)} portions from {top_key}")
        all_rows.extend(rows)
        all_portions.extend(portions)

    print(f"\nConnecting to database ...")
    conn = await asyncpg.connect(dsn)
    try:
        total = 0
        for batch in chunks(all_rows, 500):
            await conn.executemany(UPSERT_SQL, batch)
            total += len(batch)
            print(f"\r  {total}/{len(all_rows)} foods", end="", flush=True)
        print(f"\nUpserted {total} foods.")

        # Reload portions for every food we just imported: delete-then-insert keeps
        # the import idempotent without needing a unique key on the portion rows.
        fdc_ids = list({r[0] for r in all_rows})
        await conn.execute("DELETE FROM food_portions WHERE fdc_id = ANY($1)", fdc_ids)
        total = 0
        for batch in chunks(all_portions, 500):
            await conn.executemany(PORTION_INSERT_SQL, batch)
            total += len(batch)
            print(f"\r  {total}/{len(all_portions)} portions", end="", flush=True)
        print(f"\nDone. Inserted {total} food portions.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
