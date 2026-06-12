import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getRecipes, getFridgeRecipes, getTags } from '../api/client'
import type { FridgeMatch, RecipeSummary, TagResponse } from '../api/types'
import RecipeCard from '../components/RecipeCard'
import IngredientPicker, { type PickedIngredient } from '../components/IngredientPicker'

type Mode = 'easy' | 'advanced' | 'fridge'
const MODES: { key: Mode; label: string }[] = [
  { key: 'easy', label: 'Easy' },
  { key: 'advanced', label: 'Advanced' },
  { key: 'fridge', label: "What's in my fridge?" },
]

export default function Search() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialMode = (searchParams.get('mode') as Mode) || 'easy'
  const [mode, setMode] = useState<Mode>(
    MODES.some(m => m.key === initialMode) ? initialMode : 'easy',
  )

  const [tags, setTags] = useState<TagResponse[]>([])

  // Easy + Advanced shared
  const [query, setQuery] = useState('')
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([])
  const [difficulty, setDifficulty] = useState('')
  const [prepTimeMax, setPrepTimeMax] = useState('')
  const [cookTimeMax, setCookTimeMax] = useState('')
  const [includeIng, setIncludeIng] = useState<PickedIngredient[]>([])
  const [excludeIng, setExcludeIng] = useState<PickedIngredient[]>([])
  const [proteinMin, setProteinMin] = useState('')
  const [proteinMax, setProteinMax] = useState('')
  const [carbsMin, setCarbsMin] = useState('')
  const [carbsMax, setCarbsMax] = useState('')
  const [energyMin, setEnergyMin] = useState('')
  const [energyMax, setEnergyMax] = useState('')

  // Fridge
  const [fridgeIng, setFridgeIng] = useState<PickedIngredient[]>([])
  const [maxMissing, setMaxMissing] = useState('2')

  // Results
  const [results, setResults] = useState<RecipeSummary[]>([])
  const [fridgeResults, setFridgeResults] = useState<FridgeMatch[]>([])
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    getTags().then(setTags).catch(() => {})
  }, [])

  useEffect(() => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('mode', mode)
      return next
    }, { replace: true })
  }, [mode, setSearchParams])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(fetchResults, 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    mode, query, selectedTagIds, difficulty, prepTimeMax, cookTimeMax,
    includeIng, excludeIng, proteinMin, proteinMax, carbsMin, carbsMax,
    energyMin, energyMax, fridgeIng, maxMissing,
  ])

  async function fetchResults() {
    if (mode === 'fridge') {
      if (fridgeIng.length === 0) {
        setFridgeResults([])
        return
      }
      setLoading(true)
      try {
        const data = await getFridgeRecipes({
          have_ingredient_ids: fridgeIng.map(i => i.id),
          max_missing: maxMissing,
        })
        setFridgeResults(data)
      } catch {
        setFridgeResults([])
      } finally {
        setLoading(false)
      }
      return
    }

    setLoading(true)
    const params: Record<string, string | string[]> = {}
    if (query) params['search'] = query
    if (mode === 'advanced') {
      if (selectedTagIds.length) params['tag_ids'] = selectedTagIds
      if (difficulty) params['difficulty'] = difficulty
      if (prepTimeMax) params['prep_time_max'] = prepTimeMax
      if (cookTimeMax) params['cook_time_max'] = cookTimeMax
      if (includeIng.length) params['contains_ingredient_ids'] = includeIng.map(i => i.id)
      if (excludeIng.length) params['excludes_ingredient_ids'] = excludeIng.map(i => i.id)
      if (proteinMin) params['protein_min'] = proteinMin
      if (proteinMax) params['protein_max'] = proteinMax
      if (carbsMin) params['carbs_min'] = carbsMin
      if (carbsMax) params['carbs_max'] = carbsMax
      if (energyMin) params['energy_min'] = energyMin
      if (energyMax) params['energy_max'] = energyMax
    }
    try {
      const data = await getRecipes(params)
      setResults(data)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  function toggleTag(id: string) {
    setSelectedTagIds(prev =>
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    )
  }

  return (
    <div className="pa-search-page">
      <div className="pa-search-tabs">
        {MODES.map(m => (
          <button
            key={m.key}
            className={'pa-chip' + (mode === m.key ? ' active' : '')}
            onClick={() => setMode(m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode !== 'fridge' && (
        <div className="pa-search-bar">
          <span className="pa-search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search recipes…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
        </div>
      )}

      <div className="pa-search-layout">
        {mode === 'advanced' && (
          <aside className="pa-facets">
            <p className="pa-facet-heading">Tags</p>
            <div className="pa-facet-tags">
              {tags.map(tag => (
                <button
                  key={tag.id}
                  className={'pa-chip' + (selectedTagIds.includes(tag.id) ? ' active' : '')}
                  onClick={() => toggleTag(tag.id)}
                >
                  {tag.name}
                </button>
              ))}
            </div>
            <div className="pa-facet-field">
              <label>Include ingredients</label>
              <IngredientPicker selected={includeIng} onChange={setIncludeIng} placeholder="Must contain…" />
            </div>
            <div className="pa-facet-field">
              <label>Exclude ingredients</label>
              <IngredientPicker selected={excludeIng} onChange={setExcludeIng} placeholder="Must not contain…" />
            </div>
            <div className="pa-facet-field">
              <label>Difficulty</label>
              <select value={difficulty} onChange={e => setDifficulty(e.target.value)}>
                <option value="">Any</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            <div className="pa-facet-field">
              <label>Max prep time (min)</label>
              <input type="number" min={0} placeholder="—" value={prepTimeMax} onChange={e => setPrepTimeMax(e.target.value)} />
            </div>
            <div className="pa-facet-field">
              <label>Max cook time (min)</label>
              <input type="number" min={0} placeholder="—" value={cookTimeMax} onChange={e => setCookTimeMax(e.target.value)} />
            </div>
            <div className="pa-facet-field">
              <label>Protein per serving (g)</label>
              <div className="pa-macro-range">
                <input type="number" min={0} placeholder="min" value={proteinMin} onChange={e => setProteinMin(e.target.value)} />
                <input type="number" min={0} placeholder="max" value={proteinMax} onChange={e => setProteinMax(e.target.value)} />
              </div>
            </div>
            <div className="pa-facet-field">
              <label>Carbs per serving (g)</label>
              <div className="pa-macro-range">
                <input type="number" min={0} placeholder="min" value={carbsMin} onChange={e => setCarbsMin(e.target.value)} />
                <input type="number" min={0} placeholder="max" value={carbsMax} onChange={e => setCarbsMax(e.target.value)} />
              </div>
            </div>
            <div className="pa-facet-field">
              <label>Calories per serving (kcal)</label>
              <div className="pa-macro-range">
                <input type="number" min={0} placeholder="min" value={energyMin} onChange={e => setEnergyMin(e.target.value)} />
                <input type="number" min={0} placeholder="max" value={energyMax} onChange={e => setEnergyMax(e.target.value)} />
              </div>
            </div>
          </aside>
        )}

        {mode === 'fridge' && (
          <aside className="pa-facets">
            <p className="pa-facet-heading">Ingredients you have</p>
            <p className="pa-facet-hint">
              Pick what's on hand — we'll find recipes you can make or almost make.
              Pantry staples like salt &amp; pepper are assumed.
            </p>
            <IngredientPicker selected={fridgeIng} onChange={setFridgeIng} placeholder="e.g. butter, tortillas…" />
            <div className="pa-facet-field">
              <label>How much shopping?</label>
              <select value={maxMissing} onChange={e => setMaxMissing(e.target.value)}>
                <option value="0">I can make it now</option>
                <option value="1">Missing up to 1</option>
                <option value="2">Missing up to 2</option>
                <option value="3">Missing up to 3</option>
                <option value="5">Missing up to 5</option>
              </select>
            </div>
          </aside>
        )}

        <div className="pa-results">
          {loading && <div className="pa-results-empty">Searching…</div>}

          {!loading && mode === 'fridge' && fridgeIng.length === 0 && (
            <div className="pa-results-empty">Add ingredients you have to get started.</div>
          )}
          {!loading && mode === 'fridge' && fridgeIng.length > 0 && fridgeResults.length === 0 && (
            <div className="pa-results-empty">No recipes match what you have. Try adding more.</div>
          )}
          {!loading && mode === 'fridge' && fridgeResults.map(recipe => (
            <div key={recipe.id} className="pa-fridge-item">
              {recipe.missing_count === 0 ? (
                <span className="pa-fridge-badge ready">✓ Ready to make</span>
              ) : (
                <span className="pa-fridge-badge">
                  Missing {recipe.missing_count}: {recipe.missing_ingredient_names.slice(0, 3).join(', ')}
                  {recipe.missing_ingredient_names.length > 3 ? '…' : ''}
                </span>
              )}
              <RecipeCard recipe={recipe} variant="card" onClick={() => navigate(`/recipes/${recipe.id}`)} />
            </div>
          ))}

          {!loading && mode !== 'fridge' && results.length === 0 && (
            <div className="pa-results-empty">No recipes found.</div>
          )}
          {!loading && mode !== 'fridge' && results.map(recipe => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              variant="card"
              onClick={() => navigate(`/recipes/${recipe.id}`)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
