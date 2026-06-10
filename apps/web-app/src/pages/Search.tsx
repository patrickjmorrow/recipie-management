import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRecipes, getTags } from '../api/client'
import type { RecipeSummary, TagResponse } from '../api/types'
import RecipeCard from '../components/RecipeCard'

export default function Search() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [tags, setTags] = useState<TagResponse[]>([])
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([])
  const [difficulty, setDifficulty] = useState('')
  const [prepTimeMax, setPrepTimeMax] = useState('')
  const [cookTimeMax, setCookTimeMax] = useState('')
  const [results, setResults] = useState<RecipeSummary[]>([])
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    getTags().then(setTags).catch(() => {})
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(fetchResults, 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [query, selectedTagIds, difficulty, prepTimeMax, cookTimeMax])

  async function fetchResults() {
    setLoading(true)
    const params: Record<string, string | string[]> = {}
    if (query) params['search'] = query
    if (selectedTagIds.length) params['tag_ids'] = selectedTagIds
    if (difficulty) params['difficulty'] = difficulty
    if (prepTimeMax) params['prep_time_max'] = prepTimeMax
    if (cookTimeMax) params['cook_time_max'] = cookTimeMax
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
      <div className="pa-search-layout">
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
            <input
              type="number"
              min={0}
              placeholder="—"
              value={prepTimeMax}
              onChange={e => setPrepTimeMax(e.target.value)}
            />
          </div>
          <div className="pa-facet-field">
            <label>Max cook time (min)</label>
            <input
              type="number"
              min={0}
              placeholder="—"
              value={cookTimeMax}
              onChange={e => setCookTimeMax(e.target.value)}
            />
          </div>
        </aside>
        <div className="pa-results">
          {loading && <div className="pa-results-empty">Searching…</div>}
          {!loading && results.length === 0 && (
            <div className="pa-results-empty">No recipes found.</div>
          )}
          {!loading && results.map(recipe => (
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
