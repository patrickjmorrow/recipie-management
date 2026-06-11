import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createRecipe, createTag, deleteRecipe, deleteRecipeImage, getRecipe, getRecipeImageUrl, getTags, updateRecipe, uploadRecipeImage } from '../api/client'
import type { RecipeIngredientCreate, RecipeMetadata, TagResponse } from '../api/types'
import PhotoPlaceholder from '../components/PhotoPlaceholder'
import RichTextEditor from '../components/RichTextEditor'

interface IngRow {
  key: number
  ingredient_name: string
  quantity: string
  unit: string
  note: string
}

let nextKey = 0
function freshRow(): IngRow {
  return { key: nextKey++, ingredient_name: '', quantity: '', unit: '', note: '' }
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

  function updateIng(key: number, field: keyof Omit<IngRow, 'key'>, value: string) {
    setIngredients(prev => prev.map(r => r.key === key ? { ...r, [field]: value } : r))
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
                {ingredients.map(row => (
                  <div key={row.key} className="pa-ing-row">
                    <input placeholder="Qty" value={row.quantity} onChange={e => updateIng(row.key, 'quantity', e.target.value)} />
                    <input placeholder="Unit" value={row.unit} onChange={e => updateIng(row.key, 'unit', e.target.value)} />
                    <input placeholder="Ingredient *" value={row.ingredient_name} onChange={e => updateIng(row.key, 'ingredient_name', e.target.value)} />
                    <input placeholder="Note" value={row.note} onChange={e => updateIng(row.key, 'note', e.target.value)} />
                    <button type="button" className="pa-ing-remove" onClick={() => removeIng(row.key)}>×</button>
                  </div>
                ))}
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
