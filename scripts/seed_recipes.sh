#!/usr/bin/env bash
# Smoke-test seed: creates tags then uploads 12 sample recipes to the API.
# Requires the dev auth endpoint (ENVIRONMENT=local).
# Usage: BASE_URL=http://localhost:8000 SEED_EMAIL=you@example.com ./scripts/seed_recipes.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SEED_EMAIL="${SEED_EMAIL:-seed@example.com}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: apt install jq / brew install jq" >&2
  exit 1
fi

# ─── Authenticate (dev-only endpoint) ─────────────────────────────────────
echo "Authenticating as $SEED_EMAIL..."
TOKEN=$(curl -sf -X POST "$BASE_URL/api/v1/auth/dev" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$SEED_EMAIL\", \"display_name\": \"Seed Script\"}" \
  | jq -r '.access_token')

# ─── Helpers ───────────────────────────────────────────────────────────────
create_tag() {
  curl -sf -X POST "$BASE_URL/api/v1/tags/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"name\": \"$1\"}" | jq -r '.id'
}

post_recipe() {
  local name="$1" body="$2" image="${3:-}"
  echo "Creating: $name"
  local id
  id=$(curl -sf -X POST "$BASE_URL/api/v1/recipes/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$body" | jq -r '.id')
  echo "  -> $id"
  if [[ -n "$image" && -f "$SCRIPT_DIR/images/$image" ]]; then
    curl -sf -X POST "$BASE_URL/api/v1/recipes/$id/image" \
      -H "Authorization: Bearer $TOKEN" \
      -F "file=@$SCRIPT_DIR/images/$image" > /dev/null
    echo "  image: $image"
  fi
}

# ─── Tags ──────────────────────────────────────────────────────────────────
echo "Creating tags..."
QUICK=$(create_tag "quick")                 && echo "  quick          -> $QUICK"
SEAFOOD=$(create_tag "seafood")             && echo "  seafood        -> $SEAFOOD"
CHICKEN=$(create_tag "chicken")             && echo "  chicken        -> $CHICKEN"
BEEF=$(create_tag "beef")                   && echo "  beef           -> $BEEF"
VEGETARIAN=$(create_tag "vegetarian")       && echo "  vegetarian     -> $VEGETARIAN"
PASTA=$(create_tag "pasta")                 && echo "  pasta          -> $PASTA"
ASIAN=$(create_tag "Asian")                 && echo "  Asian          -> $ASIAN"
BREAKFAST=$(create_tag "breakfast")         && echo "  breakfast      -> $BREAKFAST"
MEDITERRANEAN=$(create_tag "Mediterranean") && echo "  Mediterranean  -> $MEDITERRANEAN"
MEXICAN=$(create_tag "Mexican")             && echo "  Mexican        -> $MEXICAN"
SOUP=$(create_tag "soup")                   && echo "  soup           -> $SOUP"

# ─── Recipes ───────────────────────────────────────────────────────────────
echo ""
echo "Creating recipes..."

# 1. Classic Garlic Butter Shrimp — quick, seafood
post_recipe "Classic Garlic Butter Shrimp" "$(cat <<EOF
{
  "title": "Classic Garlic Butter Shrimp",
  "description": "Plump shrimp seared in a rich, savory garlic butter sauce with a splash of lemon. Perfect over pasta or with crusty bread.",
  "instructions": "Melt butter with olive oil in a skillet over medium-high heat. Add minced garlic and cook for 1 minute until fragrant. Add shrimp, seasoned with salt and pepper, and cook for 2-3 minutes per side until pink. Stir in fresh lemon juice and chopped parsley just before serving.",
  "image_key": "picture-of-garlic-shrimp.png",
  "recipie_metadata": {"prep_time": 5, "cook_time": 6, "servings": 2, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "shrimp", "quantity": 1.0, "unit": "lb", "note": "large, peeled and deveined", "sort_order": 0},
    {"ingredient_name": "unsalted butter", "quantity": 4.0, "unit": "tbsp", "sort_order": 1},
    {"ingredient_name": "olive oil", "quantity": 1.0, "unit": "tbsp", "sort_order": 2},
    {"ingredient_name": "garlic", "quantity": 4.0, "unit": "cloves", "note": "minced", "sort_order": 3},
    {"ingredient_name": "lemon juice", "quantity": 1.0, "unit": "tbsp", "note": "fresh", "sort_order": 4},
    {"ingredient_name": "parsley", "quantity": 2.0, "unit": "tbsp", "note": "fresh, chopped", "sort_order": 5},
    {"ingredient_name": "salt and black pepper", "note": "to taste", "sort_order": 6}
  ],
  "tag_ids": ["$QUICK", "$SEAFOOD"]
}
EOF
)" "picture-of-garlic-shrimp.jpg"

# 2. 5-Minute Pesto Tortellini — quick, pasta, vegetarian
post_recipe "5-Minute Pesto Tortellini" "$(cat <<EOF
{
  "title": "5-Minute Pesto Tortellini",
  "description": "A comforting, ultra-fast pasta dish utilizing refrigerated tortellini and vibrant basil pesto.",
  "instructions": "Boil the refrigerated tortellini according to package instructions (usually 3 minutes). Drain, reserving 2 tablespoons of pasta water. Return tortellini to the pot, stir in the basil pesto and reserved water, then gently fold in the halved cherry tomatoes. Top with parmesan.",
  "image_key": "picture-of-pesto-tortellini.png",
  "recipie_metadata": {"prep_time": 2, "cook_time": 3, "servings": 3, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "cheese tortellini", "quantity": 9.0, "unit": "oz", "note": "refrigerated", "sort_order": 0},
    {"ingredient_name": "basil pesto", "quantity": 0.5, "unit": "cup", "note": "prepared", "sort_order": 1},
    {"ingredient_name": "cherry tomatoes", "quantity": 0.5, "unit": "cup", "note": "halved", "sort_order": 2},
    {"ingredient_name": "parmesan cheese", "quantity": 2.0, "unit": "tbsp", "note": "grated", "sort_order": 3}
  ],
  "tag_ids": ["$QUICK", "$PASTA", "$VEGETARIAN"]
}
EOF
)" "picture-of-pesto-tortellini.jpg"

# 3. Spicy Peanut Noodles — quick, pasta, Asian
post_recipe "Spicy Peanut Noodles" "$(cat <<EOF
{
  "title": "Spicy Peanut Noodles",
  "description": "Savory, nutty, and slightly spicy noodles that can be enjoyed hot or cold.",
  "instructions": "Cook ramen noodles according to package instructions (discard flavor packet) and drain. In a bowl, whisk together peanut butter, soy sauce, honey, sriracha, garlic, and warm water until smooth. Toss noodles in the sauce and garnish with green onions and crushed peanuts.",
  "image_key": "picture-of-peanut-noodles.png",
  "recipie_metadata": {"prep_time": 5, "cook_time": 3, "servings": 1, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "ramen noodles", "quantity": 1.0, "unit": "pack", "note": "instant, discard flavor packet", "sort_order": 0},
    {"ingredient_name": "peanut butter", "quantity": 2.0, "unit": "tbsp", "note": "creamy", "sort_order": 1},
    {"ingredient_name": "soy sauce", "quantity": 1.0, "unit": "tbsp", "sort_order": 2},
    {"ingredient_name": "honey", "quantity": 1.0, "unit": "tbsp", "sort_order": 3},
    {"ingredient_name": "sriracha", "quantity": 1.0, "unit": "tsp", "sort_order": 4},
    {"ingredient_name": "garlic", "quantity": 1.0, "unit": "clove", "note": "minced", "sort_order": 5},
    {"ingredient_name": "water", "quantity": 2.0, "unit": "tbsp", "note": "warm", "sort_order": 6},
    {"ingredient_name": "peanuts", "quantity": 1.0, "unit": "tbsp", "note": "chopped", "sort_order": 7},
    {"ingredient_name": "green onion", "quantity": 1.0, "note": "sliced", "sort_order": 8}
  ],
  "tag_ids": ["$QUICK", "$PASTA", "$ASIAN"]
}
EOF
)" "picture-of-peanut-noodles.jpg"

# 4. Crispy Black Bean Quesadillas — quick, vegetarian, Mexican
post_recipe "Crispy Black Bean Quesadillas" "$(cat <<EOF
{
  "title": "Crispy Black Bean Quesadillas",
  "description": "A cheesy, protein-packed quesadilla that makes for a perfect quick lunch or late-night snack.",
  "instructions": "Mix black beans, corn, taco seasoning, and half the cheese in a bowl. Place a tortilla in a hot skillet, sprinkle with cheese, add the bean mixture, top with more cheese, and fold over. Cook for 2-3 minutes per side until the tortilla is golden-brown and the cheese is melted.",
  "image_key": "picture-of-quesadilla.png",
  "recipie_metadata": {"prep_time": 5, "cook_time": 6, "servings": 2, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "flour tortillas", "quantity": 4.0, "sort_order": 0},
    {"ingredient_name": "black beans", "quantity": 1.0, "unit": "can", "note": "15 oz, drained and rinsed", "sort_order": 1},
    {"ingredient_name": "corn", "quantity": 0.5, "unit": "cup", "note": "canned, drained", "sort_order": 2},
    {"ingredient_name": "Mexican blend cheese", "quantity": 1.0, "unit": "cup", "note": "shredded", "sort_order": 3},
    {"ingredient_name": "taco seasoning", "quantity": 1.0, "unit": "tsp", "sort_order": 4}
  ],
  "tag_ids": ["$QUICK", "$VEGETARIAN", "$MEXICAN"]
}
EOF
)" "picture-of-quesadilla.jpg"

# 5. Quick Beef Rice Bowls — quick, beef, Asian
post_recipe "Quick Beef Rice Bowls" "$(cat <<EOF
{
  "title": "Quick Beef Rice Bowls",
  "description": "A Japanese-inspired sweet and savory ground beef bowl served over steaming rice.",
  "instructions": "Brown the ground beef in a skillet over medium-high heat with minced ginger. Drain excess fat. Pour in soy sauce, brown sugar, and sesame oil. Simmer for 3 minutes until the sauce reduces slightly. Serve over microwave-heated jasmine rice and garnish with green onions.",
  "image_key": "picture-of-beef-bowl.png",
  "recipie_metadata": {"prep_time": 5, "cook_time": 7, "servings": 2, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "ground beef", "quantity": 0.5, "unit": "lb", "note": "lean", "sort_order": 0},
    {"ingredient_name": "jasmine rice", "quantity": 2.0, "unit": "cups", "note": "cooked", "sort_order": 1},
    {"ingredient_name": "soy sauce", "quantity": 3.0, "unit": "tbsp", "sort_order": 2},
    {"ingredient_name": "brown sugar", "quantity": 1.0, "unit": "tbsp", "sort_order": 3},
    {"ingredient_name": "sesame oil", "quantity": 1.0, "unit": "tsp", "sort_order": 4},
    {"ingredient_name": "ginger", "quantity": 1.0, "unit": "tsp", "note": "fresh, minced", "sort_order": 5},
    {"ingredient_name": "green onions", "quantity": 2.0, "note": "sliced", "sort_order": 6}
  ],
  "tag_ids": ["$QUICK", "$BEEF", "$ASIAN"]
}
EOF
)" "picture-of-beef-bowl.jpg"

# 6. Ultimate Caprese Avocado Toast — quick, vegetarian, breakfast, Mediterranean
post_recipe "Ultimate Caprese Avocado Toast" "$(cat <<EOF
{
  "title": "Ultimate Caprese Avocado Toast",
  "description": "An upgraded avocado toast featuring fresh mozzarella, juicy tomatoes, and a rich balsamic glaze drizzle.",
  "instructions": "Toast the sourdough bread slices. In a small bowl, mash the avocado with lemon juice, salt, and pepper; spread evenly across the toast. Layer alternating slices of fresh mozzarella and cherry tomatoes on top. Garnish with fresh basil leaves and drizzle with balsamic glaze.",
  "image_key": "picture-of-avocado-toast.png",
  "recipie_metadata": {"prep_time": 10, "cook_time": 0, "servings": 2, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "sourdough bread", "quantity": 2.0, "unit": "slices", "sort_order": 0},
    {"ingredient_name": "avocado", "quantity": 1.0, "note": "ripe", "sort_order": 1},
    {"ingredient_name": "cherry tomatoes", "quantity": 0.5, "unit": "cup", "note": "sliced", "sort_order": 2},
    {"ingredient_name": "fresh mozzarella", "quantity": 4.0, "unit": "oz", "note": "sliced or torn", "sort_order": 3},
    {"ingredient_name": "lemon juice", "quantity": 1.0, "unit": "tsp", "sort_order": 4},
    {"ingredient_name": "basil", "note": "fresh leaves", "sort_order": 5},
    {"ingredient_name": "balsamic glaze", "quantity": 1.0, "unit": "tbsp", "sort_order": 6},
    {"ingredient_name": "salt and pepper", "sort_order": 7}
  ],
  "tag_ids": ["$QUICK", "$VEGETARIAN", "$BREAKFAST", "$MEDITERRANEAN"]
}
EOF
)" "picture-of-avocado-toast.jpg"

# 7. Honey Garlic Glazed Salmon — quick, seafood
post_recipe "Honey Garlic Glazed Salmon" "$(cat <<EOF
{
  "title": "Honey Garlic Glazed Salmon",
  "description": "Perfectly seared salmon fillets coated in a sticky, sweet, and savory glaze that tastes gourmet but takes minutes.",
  "instructions": "Season salmon fillets with salt, pepper, and paprika. Sear in a hot skillet with olive oil for 4 minutes skin-side down, then flip. Add butter, garlic, honey, soy sauce, and lemon juice to the pan. Spoon the bubbling sauce over the salmon for another 3 minutes until cooked through.",
  "image_key": "picture-of-glazed-salmon.png",
  "recipie_metadata": {"prep_time": 5, "cook_time": 7, "servings": 2, "difficulty": "medium"},
  "recipe_ingredients": [
    {"ingredient_name": "salmon", "quantity": 2.0, "note": "fillets", "sort_order": 0},
    {"ingredient_name": "olive oil", "quantity": 1.0, "unit": "tbsp", "sort_order": 1},
    {"ingredient_name": "butter", "quantity": 2.0, "unit": "tbsp", "sort_order": 2},
    {"ingredient_name": "garlic", "quantity": 3.0, "unit": "cloves", "note": "minced", "sort_order": 3},
    {"ingredient_name": "honey", "quantity": 3.0, "unit": "tbsp", "sort_order": 4},
    {"ingredient_name": "soy sauce", "quantity": 1.0, "unit": "tbsp", "sort_order": 5},
    {"ingredient_name": "lemon juice", "quantity": 1.0, "unit": "tbsp", "note": "fresh", "sort_order": 6},
    {"ingredient_name": "paprika", "quantity": 0.5, "unit": "tsp", "sort_order": 7}
  ],
  "tag_ids": ["$QUICK", "$SEAFOOD"]
}
EOF
)" "picture-of-glazed-salmon.jpg"

# 8. Loaded Egg Scramble Sandwich — quick, breakfast
post_recipe "Loaded Egg Scramble Sandwich" "$(cat <<EOF
{
  "title": "Loaded Egg Scramble Sandwich",
  "description": "A fluffy, buttery, cheesy egg sandwich elevated with spinach and a quick spicy mayo.",
  "instructions": "Whisk eggs with milk, salt, and pepper. Melt butter in a skillet, add spinach until wilted, then pour in eggs. Scramble gently until just set, then fold in cheddar cheese. Mix mayo and sriracha, spread onto toasted brioche buns, and pile high with the scrambled eggs.",
  "image_key": "picture-of-egg-sandwich.png",
  "recipie_metadata": {"prep_time": 4, "cook_time": 4, "servings": 1, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "eggs", "quantity": 2.0, "note": "large", "sort_order": 0},
    {"ingredient_name": "milk", "quantity": 1.0, "unit": "tbsp", "sort_order": 1},
    {"ingredient_name": "spinach", "quantity": 0.5, "unit": "cup", "note": "fresh", "sort_order": 2},
    {"ingredient_name": "cheddar cheese", "quantity": 0.25, "unit": "cup", "note": "shredded", "sort_order": 3},
    {"ingredient_name": "butter", "quantity": 1.0, "unit": "tbsp", "sort_order": 4},
    {"ingredient_name": "brioche bun", "quantity": 1.0, "note": "toasted", "sort_order": 5},
    {"ingredient_name": "mayonnaise", "quantity": 1.0, "unit": "tbsp", "sort_order": 6},
    {"ingredient_name": "sriracha", "quantity": 1.0, "unit": "tsp", "sort_order": 7}
  ],
  "tag_ids": ["$QUICK", "$BREAKFAST"]
}
EOF
)" "picture-of-egg-sandwich.jpg"

# 9. Sheet Pan Greek Chicken Souvlaki — quick, chicken, Mediterranean
post_recipe "Sheet Pan Greek Chicken Souvlaki" "$(cat <<EOF
{
  "title": "Sheet Pan Greek Chicken Souvlaki",
  "description": "A quick-roasting Greek chicken dinner packed with Mediterranean flavors and zero cleanup fuss.",
  "instructions": "Preheat oven to 425F (220C). Toss cubed chicken, bell pepper, and red onion with olive oil, lemon juice, dried oregano, garlic powder, salt, and pepper on a baking sheet. Roast for 12-15 minutes until chicken is cooked through. Top with crumbled feta cheese before serving.",
  "image_key": "picture-of-greek-chicken.png",
  "recipie_metadata": {"prep_time": 10, "cook_time": 15, "servings": 4, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "chicken breasts", "quantity": 1.5, "unit": "lbs", "note": "cubed", "sort_order": 0},
    {"ingredient_name": "bell pepper", "quantity": 1.0, "note": "large, chopped", "sort_order": 1},
    {"ingredient_name": "red onion", "quantity": 1.0, "note": "chopped", "sort_order": 2},
    {"ingredient_name": "olive oil", "quantity": 3.0, "unit": "tbsp", "sort_order": 3},
    {"ingredient_name": "lemon juice", "quantity": 2.0, "unit": "tbsp", "sort_order": 4},
    {"ingredient_name": "oregano", "quantity": 1.5, "unit": "tsp", "note": "dried", "sort_order": 5},
    {"ingredient_name": "garlic powder", "quantity": 1.0, "unit": "tsp", "sort_order": 6},
    {"ingredient_name": "feta cheese", "quantity": 0.5, "unit": "cup", "note": "crumbled", "sort_order": 7}
  ],
  "tag_ids": ["$QUICK", "$CHICKEN", "$MEDITERRANEAN"]
}
EOF
)" "picture-of-greek-chicken.jpg"

# 10. Creamy Tuscan White Bean Skillet — quick, vegetarian
post_recipe "Creamy Tuscan White Bean Skillet" "$(cat <<EOF
{
  "title": "Creamy Tuscan White Bean Skillet",
  "description": "A rich, velvety, plant-based skillet dish utilizing canned white beans, sun-dried tomatoes, and heavy cream.",
  "instructions": "Heat olive oil from the sun-dried tomato jar in a skillet. Saute garlic and sun-dried tomatoes for 2 minutes. Stir in vegetable broth and heavy cream; bring to a simmer. Add the drained cannellini beans and spinach. Simmer for 5 minutes until spinach wilts and the sauce thickens.",
  "image_key": "picture-of-bean-skillet.png",
  "recipie_metadata": {"prep_time": 5, "cook_time": 7, "servings": 2, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "cannellini beans", "quantity": 1.0, "unit": "can", "note": "15 oz, drained and rinsed", "sort_order": 0},
    {"ingredient_name": "sun-dried tomatoes", "quantity": 0.25, "unit": "cup", "note": "in oil, chopped", "sort_order": 1},
    {"ingredient_name": "garlic", "quantity": 3.0, "unit": "cloves", "note": "minced", "sort_order": 2},
    {"ingredient_name": "vegetable broth", "quantity": 0.25, "unit": "cup", "sort_order": 3},
    {"ingredient_name": "heavy cream", "quantity": 0.5, "unit": "cup", "sort_order": 4},
    {"ingredient_name": "baby spinach", "quantity": 2.0, "unit": "cups", "note": "fresh", "sort_order": 5},
    {"ingredient_name": "salt and pepper", "note": "to taste", "sort_order": 6}
  ],
  "tag_ids": ["$QUICK", "$VEGETARIAN"]
}
EOF
)" "picture-of-bean-skillet.jpg"

# 11. 10-Minute Thai Red Curry Soup — quick, chicken, Asian, soup
post_recipe "10-Minute Thai Red Curry Soup" "$(cat <<EOF
{
  "title": "10-Minute Thai Red Curry Soup",
  "description": "An incredibly fast, deeply aromatic Thai soup made effortless with store-bought curry paste and coconut milk.",
  "instructions": "Heat oil in a pot over medium heat. Fry the red curry paste for 1 minute until fragrant. Pour in coconut milk and chicken broth, bringing it to a simmer. Add the shredded chicken and sliced mushrooms; cook for 4 minutes. Stir in fish sauce and lime juice right before serving.",
  "image_key": "picture-of-curry-soup.png",
  "recipie_metadata": {"prep_time": 4, "cook_time": 6, "servings": 3, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "red curry paste", "quantity": 2.0, "unit": "tbsp", "note": "Thai", "sort_order": 0},
    {"ingredient_name": "coconut milk", "quantity": 1.0, "unit": "can", "note": "14 oz, light", "sort_order": 1},
    {"ingredient_name": "chicken broth", "quantity": 2.0, "unit": "cups", "sort_order": 2},
    {"ingredient_name": "rotisserie chicken", "quantity": 1.5, "unit": "cups", "note": "shredded", "sort_order": 3},
    {"ingredient_name": "button mushrooms", "quantity": 0.5, "unit": "cup", "note": "sliced", "sort_order": 4},
    {"ingredient_name": "fish sauce", "quantity": 1.0, "unit": "tbsp", "sort_order": 5},
    {"ingredient_name": "lime juice", "quantity": 1.0, "unit": "tbsp", "note": "fresh", "sort_order": 6},
    {"ingredient_name": "vegetable oil", "quantity": 1.0, "unit": "tbsp", "sort_order": 7}
  ],
  "tag_ids": ["$QUICK", "$CHICKEN", "$ASIAN", "$SOUP"]
}
EOF
)" "picture-of-curry-soup.jpg"

# 12. Chappy's Quick BBQ Chicken Flatbread — quick, chicken, Mexican
post_recipe "Chappy's Quick BBQ Chicken Flatbread" "$(cat <<EOF
{
  "title": "Chappy's Quick BBQ Chicken Flatbread",
  "description": "An individual personal pizza alternative utilizing flatbread, leftover chicken, and smoky BBQ sauce.",
  "instructions": "Preheat oven to 400F (200C). Place flatbread on a baking sheet. Spread BBQ sauce evenly across the base. Top with shredded chicken, thinly sliced red onion, and mozzarella cheese. Bake for 8-10 minutes until the cheese is bubbling and edges are crisp. Garnish with cilantro.",
  "image_key": "picture-of-bbq-flatbread.png",
  "recipie_metadata": {"prep_time": 5, "cook_time": 10, "servings": 1, "difficulty": "easy"},
  "recipe_ingredients": [
    {"ingredient_name": "naan or flatbread", "quantity": 1.0, "note": "large", "sort_order": 0},
    {"ingredient_name": "BBQ sauce", "quantity": 3.0, "unit": "tbsp", "sort_order": 1},
    {"ingredient_name": "chicken", "quantity": 0.5, "unit": "cup", "note": "cooked, shredded", "sort_order": 2},
    {"ingredient_name": "red onion", "quantity": 0.25, "unit": "cup", "note": "thinly sliced", "sort_order": 3},
    {"ingredient_name": "mozzarella cheese", "quantity": 0.5, "unit": "cup", "note": "shredded", "sort_order": 4},
    {"ingredient_name": "cilantro", "quantity": 1.0, "unit": "tbsp", "note": "fresh, chopped", "sort_order": 5}
  ],
  "tag_ids": ["$QUICK", "$CHICKEN", "$MEXICAN"]
}
EOF
)" "picture-of-bbq-flatbread.jpg"

echo ""
echo "Done. 11 tags and 12 recipes uploaded."
