#!/usr/bin/env bash
# Deletes all recipes and tags via the API. Ingredients are left intact.
# Requires the dev auth endpoint (ENVIRONMENT=local).
# Usage: BASE_URL=http://localhost:8000 SEED_EMAIL=you@example.com ./scripts/clear_db.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SEED_EMAIL="${SEED_EMAIL:-seed@example.com}"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: apt install jq / brew install jq" >&2
  exit 1
fi

# ─── Authenticate ──────────────────────────────────────────────────────────
echo "Authenticating as $SEED_EMAIL..."
TOKEN=$(curl -sf -X POST "$BASE_URL/api/v1/auth/dev" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$SEED_EMAIL\", \"display_name\": \"Seed Script\"}" \
  | jq -r '.access_token')

# ─── Recipes ───────────────────────────────────────────────────────────────
# Recipes are deleted first so tags can be hard-deleted (no active references).
# The list endpoint caps at 200; loop until the page comes back empty.
echo ""
echo "Deleting recipes..."
total_recipes=0
while true; do
  ids=$(curl -sf "$BASE_URL/api/v1/recipes/?limit=200" | jq -r '.[].id')
  [[ -z "$ids" ]] && break
  while IFS= read -r id; do
    curl -sf -X DELETE "$BASE_URL/api/v1/recipes/$id"
    echo "  deleted recipe $id"
    total_recipes=$((total_recipes + 1))
  done <<< "$ids"
done
echo "  $total_recipes recipe(s) deleted."

# ─── Tags ──────────────────────────────────────────────────────────────────
# include_deprecated=true catches any tags that were previously soft-deleted.
echo ""
echo "Deleting tags..."
total_tags=0
ids=$(curl -sf "$BASE_URL/api/v1/tags/?include_deprecated=true" | jq -r '.[].id')
if [[ -n "$ids" ]]; then
  while IFS= read -r id; do
    curl -sf -X DELETE "$BASE_URL/api/v1/tags/$id" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    echo "  deleted tag $id"
    total_tags=$((total_tags + 1))
  done <<< "$ids"
fi
echo "  $total_tags tag(s) deleted."

echo ""
echo "Done. Ingredients were not touched."
