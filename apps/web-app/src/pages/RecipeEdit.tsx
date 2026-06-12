import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createRecipe, createTag, deleteRecipe, deleteRecipeImage, getIngredients, getRecipe, getRecipeImageUrl, getTags, previewMacros, searchFoods, updateRecipe, uploadRecipeImage } from '../api/client'
import type { FoodSearchResult, IngredientResponse, MacrosLineResult, MacrosPreview, RecipeIngredientCreate, RecipeMetadata, TagResponse } from '../api/types'
import PhotoPlaceholder from '../components/PhotoPlaceholder'
import RichTextEditor from '../components/RichTextEditor'

interface IngRow {
  key: number
  ingredient_name: string
  quantity: string
  unit: string
  note: string
  food_id: number | null
  food_name: string | null
  food_match: string | null
  // True only when the user explicitly chose a food via the picker — gates whether
  // we send food_id on save (so merely adopting an existing link never re-confirms it).
  food_confirmed: boolean
}

let nextKey = 0
function freshRow(): IngRow {
  return { key: nextKey++, ingredient_name: '', quantity: '', unit: '', note: '', food_id: null, food_name: null, food_match: null, food_confirmed: false }
}

export default function RecipeEdit() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [instructions, setInstructions] = useState('')
  const [prepTime, setPrepTime] = useState('')
  const [cookTime, setCookTime] = useState('')
  const [servings, setServings] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [ingredients, setIngredients] = useState<IngRow[]>([freshRow()])
  const [selectedTags, setSelectedTags] = useState<TagResponse[]>([])
  const [allTags, setAllTags] = useState<TagResponse[]>([])
  const [tagInput, setTagInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null)
  const [existingImageKey, setExistingImageKey] = useState<string | null>(null)
  const [existingImageUrl, setExistingImageUrl] = useState<string | null>(null)
  const [removeExistingImage, setRemoveExistingImage] = useState(false)
  const [macros, setMacros] = useState<MacrosPreview | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getTags().then(setAllTags).catch(() => {})
    if (!isNew && id) {
      getRecipe(id)
        .then(r => {
          setTitle(r.title)
          setDescription(r.description ?? '')
          setInstructions(r.instructions ?? '')
          const m = r.recipie_metadata
          if (m) {
            setPrepTime(m.prep_time != null ? String(m.prep_time) : '')
            setCookTime(m.cook_time != null ? String(m.cook_time) : '')
            setServings(m.servings != null ? String(m.servings) : '')
            setDifficulty(m.difficulty ?? '')
          }
          setIngredients(
            r.recipe_ingredients.length
              ? r.recipe_ingredients
                  .slice()
                  .sort((a, b) => a.sort_order - b.sort_order)
                  .map(ri => ({
                    key: nextKey++,
                    ingredient_name: ri.ingredient.name,
                    quantity: ri.quantity != null ? String(ri.quantity) : '',
                    unit: ri.unit ?? '',
                    note: ri.note ?? '',
                    food_id: ri.ingredient.food_id,
                    food_name: ri.ingredient.food?.name ?? null,
                    food_match: ri.ingredient.food_match,
                    food_confirmed: false,
                  }))
              : [freshRow()]
          )
          setSelectedTags(r.tags)
          setExistingImageKey(r.image_key)
          if (r.image_key) {
            getRecipeImageUrl(id, r.image_key).then(setExistingImageUrl).catch(() => {})
          }
        })
        .catch(() => setLoadError('Recipe not found.'))
    }
  }, [id, isNew])

  useEffect(() => {
    return () => { if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl) }
  }, [imagePreviewUrl])

  // Live per-serving nutrition preview, debounced as ingredients/servings change.
  const macrosKey = JSON.stringify({
    servings,
    lines: ingredients
      .filter(r => r.ingredient_name.trim())
      .map(r => [r.ingredient_name.trim(), r.quantity, r.unit, r.food_id]),
  })
  useEffect(() => {
    const lines = ingredients
      .filter(r => r.ingredient_name.trim())
      .map(r => ({
        ingredient_name: r.ingredient_name.trim(),
        quantity: r.quantity ? Number(r.quantity) : undefined,
        unit: r.unit || undefined,
        food_id: r.food_id ?? undefined,
      }))
    if (!lines.length) {
      setMacros(null)
      return
    }
    let cancelled = false
    const timer = setTimeout(() => {
      previewMacros({ servings: servings ? Number(servings) : undefined, recipe_ingredients: lines })
        .then(m => { if (!cancelled) setMacros(m) })
        .catch(() => { if (!cancelled) setMacros(null) })
    }, 500)
    return () => { cancelled = true; clearTimeout(timer) }
    // macrosKey captures the relevant inputs; ingredients/servings read inside.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [macrosKey])

  async function addTag() {
    const name = tagInput.trim()
    if (!name) return
    const existing = allTags.find(t => t.name.toLowerCase() === name.toLowerCase())
    if (existing) {
      if (!selectedTags.find(t => t.id === existing.id)) setSelectedTags(prev => [...prev, existing])
      setTagInput('')
      return
    }
    try {
      const tag = await createTag(name)
      setAllTags(prev => [...prev, tag])
      setSelectedTags(prev => [...prev, tag])
      setTagInput('')
    } catch {}
  }

  function removeTag(id: string) {
    setSelectedTags(prev => prev.filter(t => t.id !== id))
  }

  function updateIng(key: number, field: 'ingredient_name' | 'quantity' | 'unit' | 'note', value: string) {
    setIngredients(prev => prev.map(r => r.key === key ? { ...r, [field]: value } : r))
  }

  // Explicit user choice via the food picker → marks the link save-worthy (confirmed).
  function setIngFood(key: number, food: FoodSearchResult | null) {
    setIngredients(prev => prev.map(r => r.key === key
      ? { ...r, food_id: food ? food.id : null, food_name: food ? food.name : null, food_match: food ? 'confirmed' : 'rejected', food_confirmed: true }
      : r))
  }

  // Picked an existing ingredient from search: fill the name and adopt its saved
  // food link for display/preview, but do NOT confirm it (food_confirmed stays false).
  function adoptIngredient(key: number, ing: IngredientResponse) {
    setIngredients(prev => prev.map(r => r.key === key
      ? { ...r, ingredient_name: ing.name, food_id: ing.food_id, food_name: ing.food?.name ?? null, food_match: ing.food_match, food_confirmed: false }
      : r))
  }

  function removeIng(key: number) {
    setIngredients(prev => prev.filter(r => r.key !== key))
  }

  function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl)
    setImageFile(file)
    setImagePreviewUrl(URL.createObjectURL(file))
    e.target.value = ''
  }

  function handleRemoveImage() {
    if (imageFile) {
      if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl)
      setImageFile(null)
      setImagePreviewUrl(null)
    } else {
      setRemoveExistingImage(true)
      setExistingImageUrl(null)
    }
  }

  async function handleDeleteRecipe() {
    try {
      await deleteRecipe(id!)
      navigate('/recipes')
    } catch {}
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    const metadata: RecipeMetadata = {}
    if (prepTime) metadata.prep_time = Number(prepTime)
    if (cookTime) metadata.cook_time = Number(cookTime)
    if (servings) metadata.servings = Number(servings)
    if (difficulty) metadata.difficulty = difficulty as RecipeMetadata['difficulty']

    const recipe_ingredients: RecipeIngredientCreate[] = ingredients
      .filter(r => r.ingredient_name.trim())
      .map((r, i) => ({
        ingredient_name: r.ingredient_name.trim(),
        quantity: r.quantity ? Number(r.quantity) : undefined,
        unit: r.unit || undefined,
        note: r.note || undefined,
        sort_order: i,
        // Only persist the food link when the user explicitly confirmed it via the picker.
        food_id: r.food_confirmed ? (r.food_id ?? undefined) : undefined,
      }))

    const body = {
      title,
      description: description || undefined,
      instructions: instructions || undefined,
      recipie_metadata: Object.keys(metadata).length ? metadata : undefined,
      recipe_ingredients,
      tag_ids: selectedTags.map(t => t.id),
    }

    try {
      if (isNew) {
        const created = await createRecipe(body)
        if (imageFile) await uploadRecipeImage(created.id, imageFile)
        navigate(`/recipes/${created.id}`)
      } else {
        await updateRecipe(id!, body)
        if (removeExistingImage && existingImageKey) await deleteRecipeImage(id!)
        if (imageFile) await uploadRecipeImage(id!, imageFile)
        navigate(`/recipes/${id}`)
      }
    } catch {
      setSaving(false)
    }
  }

  if (loadError) return <div className="pa-error">{loadError}</div>

  const previewIngredients = ingredients.filter(r => r.ingredient_name.trim()).slice(0, 3)
  // Per-line resolution detail from the latest preview, keyed by ingredient name.
  const lineResults = new Map<string, MacrosLineResult>(
    (macros?.lines ?? []).map(l => [l.ingredient_name.trim().toLowerCase(), l]),
  )

  return (
    <div className="pa-edit-page">
      <div className="pa-edit-header">
        <button className="pa-btn-outline" onClick={() => navigate(-1)}>← Back</button>
        <h1 className="pa-edit-title">{isNew ? 'New Recipe' : 'Edit Recipe'}</h1>
      </div>
      <form onSubmit={handleSave}>
        <div className="pa-edit-layout">
          <div className="pa-edit-form">
            <div className="pa-form-field">
              <label>Photo</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {(imagePreviewUrl || existingImageUrl) ? (
                  <img
                    src={imagePreviewUrl ?? existingImageUrl!}
                    alt="Recipe photo preview"
                    style={{ width: '100%', aspectRatio: '16/9', objectFit: 'cover', borderRadius: 8, border: '1px solid var(--line)', display: 'block' }}
                  />
                ) : (
                  <PhotoPlaceholder ratio={16 / 9} style={{ borderRadius: 8 }} label="No photo" />
                )}
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="button" className="pa-btn-outline" onClick={() => fileInputRef.current?.click()}>
                    Choose photo
                  </button>
                  {(imagePreviewUrl || existingImageUrl) && (
                    <button type="button" className="pa-btn-outline" onClick={handleRemoveImage}>
                      Remove photo
                    </button>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  style={{ display: 'none' }}
                  onChange={handleImageChange}
                />
              </div>
            </div>
            <div className="pa-form-field">
              <label>Title *</label>
              <input value={title} onChange={e => setTitle(e.target.value)} required placeholder="Recipe name" />
            </div>
            <div className="pa-form-field">
              <label>Description</label>
              <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="A brief description…" rows={2} />
            </div>
            <div className="pa-form-row-4">
              <div className="pa-form-field">
                <label>Prep time (min)</label>
                <input type="number" min={0} value={prepTime} onChange={e => setPrepTime(e.target.value)} placeholder="—" />
              </div>
              <div className="pa-form-field">
                <label>Cook time (min)</label>
                <input type="number" min={0} value={cookTime} onChange={e => setCookTime(e.target.value)} placeholder="—" />
              </div>
              <div className="pa-form-field">
                <label>Servings</label>
                <input type="number" min={1} value={servings} onChange={e => setServings(e.target.value)} placeholder="—" />
              </div>
              <div className="pa-form-field">
                <label>Difficulty</label>
                <select value={difficulty} onChange={e => setDifficulty(e.target.value)}>
                  <option value="">—</option>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
            </div>
            <div className="pa-form-field">
              <label>Ingredients</label>
              <div className="pa-ing-list">
                {ingredients.map(row => {
                  const line = lineResults.get(row.ingredient_name.trim().toLowerCase())
                  return (
                  <div key={row.key} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div className="pa-ing-row">
                      <input placeholder="Qty" value={row.quantity} onChange={e => updateIng(row.key, 'quantity', e.target.value)} />
                      <input placeholder="Unit" value={row.unit} onChange={e => updateIng(row.key, 'unit', e.target.value)} />
                      <IngredientNameInput
                        value={row.ingredient_name}
                        onChange={v => updateIng(row.key, 'ingredient_name', v)}
                        onAdopt={ing => adoptIngredient(row.key, ing)}
                      />
                      <input placeholder="Note" value={row.note} onChange={e => updateIng(row.key, 'note', e.target.value)} />
                      <button type="button" className="pa-ing-remove" onClick={() => removeIng(row.key)}>×</button>
                    </div>
                    {row.ingredient_name.trim() && (
                      <IngredientFoodControl row={row} onPick={f => setIngFood(row.key, f)} />
                    )}
                    {row.ingredient_name.trim() && line && !line.resolved && (
                      <UnresolvedHint line={line} unit={row.unit} />
                    )}
                  </div>
                  )
                })}
              </div>
              <button type="button" className="pa-add" style={{ marginTop: 8 }} onClick={() => setIngredients(prev => [...prev, freshRow()])}>
                + Add ingredient
              </button>
            </div>
            <div className="pa-form-field">
              <label>Tags</label>
              <div className="pa-tag-input-row">
                <input
                  placeholder="Tag name…"
                  value={tagInput}
                  onChange={e => setTagInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag() } }}
                  list="all-tags"
                />
                <datalist id="all-tags">
                  {allTags.map(t => <option key={t.id} value={t.name} />)}
                </datalist>
                <button type="button" className="pa-tag-add-btn" onClick={addTag}>Add</button>
              </div>
              {selectedTags.length > 0 && (
                <div className="pa-edit-tags">
                  {selectedTags.map(t => (
                    <span key={t.id} className="pa-edit-tag">
                      {t.name}
                      <button type="button" onClick={() => removeTag(t.id)}>×</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="pa-form-field">
              <label>Instructions</label>
              <RichTextEditor
                value={instructions}
                onChange={setInstructions}
                placeholder="Write your instructions… Use '+ Add Step' to separate Cook Mode steps."
              />
            </div>
            <div className="pa-form-field">
              <div className="pa-form-btns">
              <button type="submit" className="pa-save-btn" disabled={saving || !title.trim()}>
                {saving ? 'Saving…' : isNew ? 'Create Recipe' : 'Save Changes'}
              </button>
              {!isNew && (
                <button type="button" className="pa-delete-btn" onClick={() => setShowDeleteConfirm(true)}>
                  Delete Recipe
                </button>
              )}
              </div>
            </div>
          </div>
          <aside className="pa-edit-preview">
            <p className="pa-preview-title">{title || 'Recipe title'}</p>
            <div className="pa-preview-meta">
              {prepTime && <span className="pa-card-meta-pill">{prepTime} min prep</span>}
              {cookTime && <span className="pa-card-meta-pill">{cookTime} min cook</span>}
              {servings && <span className="pa-card-meta-pill">serves {servings}</span>}
              {difficulty && <span className="pa-card-meta-pill">{difficulty}</span>}
            </div>
            {description && <p className="pa-preview-desc">{description}</p>}
            {macros && (
              <div style={{ marginTop: 14 }}>
                <p className="pa-preview-ing-heading">Nutrition (per serving)</p>
                <div className="pa-preview-meta">
                  <span className="pa-card-meta-pill">{Math.round(macros.energy_kcal)} kcal</span>
                  <span className="pa-card-meta-pill">{macros.protein_g} g protein</span>
                  <span className="pa-card-meta-pill">{macros.carbs_g} g carbs</span>
                  <span className="pa-card-meta-pill">{macros.fat_g} g fat</span>
                </div>
                {macros.unresolved.length > 0 && (
                  <p style={{ fontSize: 12, color: 'var(--ink2)', marginTop: 6 }}>
                    Not counted (no nutrition match): {macros.unresolved.join(', ')}
                  </p>
                )}
              </div>
            )}
            {previewIngredients.length > 0 && (
              <>
                <p className="pa-preview-ing-heading">Ingredients</p>
                <div className="pa-preview-ing-list">
                  {previewIngredients.map((r, i) => (
                    <span key={i}>
                      {[r.quantity, r.unit, r.ingredient_name].filter(Boolean).join(' ')}
                    </span>
                  ))}
                  {ingredients.filter(r => r.ingredient_name.trim()).length > 3 && (
                    <span style={{ color: 'var(--ink2)' }}>+{ingredients.filter(r => r.ingredient_name.trim()).length - 3} more…</span>
                  )}
                </div>
              </>
            )}
          </aside>
        </div>
      </form>
      {showDeleteConfirm && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(24,32,27,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }}>
          <div style={{ background: 'var(--paper)', borderRadius: 'var(--r)', boxShadow: 'var(--shadow-hi)', padding: '32px', maxWidth: 400, width: '90%' }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 10 }}>Delete recipe?</h2>
            <p style={{ fontSize: 15, color: 'var(--ink2)', marginBottom: 28, lineHeight: 1.5 }}>
              <strong style={{ color: 'var(--ink)' }}>{title}</strong> will be permanently deleted. This cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" className="pa-btn-outline" onClick={() => setShowDeleteConfirm(false)}>Cancel</button>
              <button type="button" className="pa-delete-btn" onClick={handleDeleteRecipe}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Inline hint shown when a line can't be resolved to nutrition, explaining why
// and (for unit mismatches) which measures the linked food actually supports.
function UnresolvedHint({ line, unit }: { line: MacrosLineResult; unit: string }) {
  let msg: React.ReactNode
  if (line.reason === 'no_food') {
    msg = 'No nutrition match — pick a food below.'
  } else if (line.reason === 'no_quantity') {
    msg = 'Add a quantity to include this in nutrition.'
  } else if (line.reason === 'no_unit') {
    msg = 'Add a unit to include this in nutrition.'
  } else if (line.reason === 'unit_unmatched') {
    const supported = line.supported_units.length ? line.supported_units.join(', ') + ', ' : ''
    msg = (
      <>
        “{unit}” isn't a known measure for <strong>{line.food_name}</strong>. Try: {supported}or a mass unit (g, oz, lb, kg).
      </>
    )
  } else {
    msg = 'Not included in nutrition.'
  }
  return (
    <div style={{ fontSize: 12, color: 'var(--warn, #a15c00)', paddingLeft: 2 }}>⚠ {msg}</div>
  )
}

// Ingredient name field with type-ahead over existing ingredients. Selecting an
// existing one adopts its saved nutrition link; "Create new" keeps the typed name.
function IngredientNameInput({ value, onChange, onAdopt }: {
  value: string
  onChange: (v: string) => void
  onAdopt: (ing: IngredientResponse) => void
}) {
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<IngredientResponse[]>([])

  useEffect(() => {
    if (!open) return
    const q = value.trim()
    if (!q) { setResults([]); return }
    let cancelled = false
    const timer = setTimeout(() => {
      getIngredients(q, 8)
        .then(r => { if (!cancelled) setResults(r) })
        .catch(() => { if (!cancelled) setResults([]) })
    }, 300)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [open, value])

  const exactExists = results.some(r => r.name.toLowerCase() === value.trim().toLowerCase())

  return (
    <div style={{ position: 'relative' }}>
      <input
        placeholder="Ingredient *"
        value={value}
        onChange={e => { onChange(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        style={{ width: '100%' }}
      />
      {open && value.trim() && (results.length > 0 || !exactExists) && (
        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 30, marginTop: 2, background: 'var(--paper)', border: '1px solid var(--line)', borderRadius: 8, boxShadow: 'var(--shadow-hi)', maxHeight: 200, overflowY: 'auto' }}>
          {results.map(ing => (
            <button
              key={ing.id}
              type="button"
              onMouseDown={e => { e.preventDefault(); onAdopt(ing); setOpen(false) }}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '6px 8px', border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--ink)', fontSize: 14 }}
            >
              {ing.name}
              {ing.food?.name && <span style={{ color: 'var(--ink2)', fontSize: 12 }}> · {ing.food.name}</span>}
            </button>
          ))}
          {!exactExists && (
            <button
              type="button"
              onMouseDown={e => { e.preventDefault(); setOpen(false) }}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '6px 8px', border: 'none', borderTop: results.length ? '1px solid var(--line)' : 'none', background: 'transparent', cursor: 'pointer', color: 'var(--ink2)', fontSize: 13 }}
            >
              Create new: “{value.trim()}”
            </button>
          )}
        </div>
      )}
    </div>
  )
}

const FOOD_BADGE = '13px'

// Per-ingredient USDA food matcher: shows the current match and lets the user
// search-and-pick a different food (or mark "no match"). Links are global —
// changing one updates the ingredient everywhere it's used.
function IngredientFoodControl({ row, onPick }: { row: IngRow; onPick: (food: FoodSearchResult | null) => void }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(row.ingredient_name)
  const [results, setResults] = useState<FoodSearchResult[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    const q = query.trim()
    if (!q) { setResults([]); return }
    let cancelled = false
    setLoading(true)
    const timer = setTimeout(() => {
      searchFoods(q, 10)
        .then(r => { if (!cancelled) setResults(r) })
        .catch(() => { if (!cancelled) setResults([]) })
        .finally(() => { if (!cancelled) setLoading(false) })
    }, 350)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [open, query])

  const badge =
    row.food_id != null
      ? { text: row.food_match === 'confirmed' ? 'confirmed' : 'auto', color: row.food_match === 'confirmed' ? 'var(--accent, #2d7d46)' : 'var(--ink2)' }
      : row.food_match === 'rejected'
        ? { text: 'no match', color: 'var(--ink2)' }
        : { text: 'auto-match', color: 'var(--ink2)' }

  return (
    <div style={{ fontSize: FOOD_BADGE, color: 'var(--ink2)', paddingLeft: 2 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span>
          Nutrition:{' '}
          <span style={{ color: 'var(--ink)' }}>{row.food_name ?? (row.food_match === 'rejected' ? 'none' : 'matched by name')}</span>{' '}
          <span style={{ color: badge.color }}>({badge.text})</span>
        </span>
        <button type="button" className="pa-btn-outline" style={{ padding: '1px 8px', fontSize: 12 }} onClick={() => { setQuery(row.ingredient_name); setOpen(o => !o) }}>
          {open ? 'Close' : 'Change'}
        </button>
      </div>
      {open && (
        <div style={{ marginTop: 6, padding: 8, border: '1px solid var(--line)', borderRadius: 8, background: 'var(--paper)' }}>
          <input
            autoFocus
            placeholder="Search USDA foods…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            style={{ width: '100%', marginBottom: 6 }}
          />
          <div style={{ maxHeight: 180, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
            {loading && <span style={{ color: 'var(--ink2)' }}>Searching…</span>}
            {!loading && results.length === 0 && query.trim() && <span style={{ color: 'var(--ink2)' }}>No foods found.</span>}
            {results.map(f => (
              <button
                key={f.id}
                type="button"
                onClick={() => { onPick(f); setOpen(false) }}
                style={{ textAlign: 'left', padding: '4px 6px', borderRadius: 6, border: 'none', background: f.id === row.food_id ? 'var(--line)' : 'transparent', cursor: 'pointer', color: 'var(--ink)' }}
              >
                {f.name}{f.category ? <span style={{ color: 'var(--ink2)' }}> · {f.category}</span> : null}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
            <button type="button" className="pa-btn-outline" style={{ padding: '1px 8px', fontSize: 12 }} onClick={() => { onPick(null); setOpen(false) }}>
              No good match
            </button>
          </div>
          <p style={{ fontSize: 11, color: 'var(--ink2)', marginTop: 6, marginBottom: 0 }}>
            Changing the food updates this ingredient everywhere it's used.
          </p>
        </div>
      )}
    </div>
  )
}
