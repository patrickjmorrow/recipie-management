import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getBrowseSections } from '../api/client'
import type { BrowseSection } from '../api/types'
import RecipeCard from '../components/RecipeCard'

export default function Browse() {
  const navigate = useNavigate()
  const [sections, setSections] = useState<BrowseSection[]>([])
  const [loading, setLoading] = useState(true)
  const [shuffling, setShuffling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback((shuffle = false) => {
    if (shuffle) setShuffling(true)
    else setLoading(true)
    setError(null)
    getBrowseSections()
      .then(res => setSections(res.sections))
      .catch(() => setError('Failed to load recipes.'))
      .finally(() => { setLoading(false); setShuffling(false) })
  }, [])

  useEffect(() => { load() }, [load])

  const open = (id: string) => navigate(`/recipes/${id}`)

  // The first recipe of the first section becomes a full-width featured hero.
  const featured = sections[0]?.recipes[0] ?? null

  return (
    <div className="pa-browse">
      <div className="pa-browse-header">
        <h1 className="pa-browse-title">What's Cooking?</h1>
        <button
          className="pa-chip"
          onClick={() => load(true)}
          disabled={shuffling || loading}
        >
          {shuffling ? 'Shuffling…' : 'Shuffle ↻'}
        </button>
      </div>

      {loading && <div className="pa-loading">Loading…</div>}
      {error && <div className="pa-error">{error}</div>}

      {!loading && !error && sections.length === 0 && (
        <div className="pa-loading">No recipes yet — add one to get cooking!</div>
      )}

      {!loading && !error && featured && (
        <div className="pa-browse-hero" onClick={() => open(featured.id)}>
          <RecipeCard recipe={featured} variant="overlay" />
        </div>
      )}

      {!loading && !error && sections.map((section, si) => {
        // Drop the hero recipe from the first section so it isn't shown twice.
        const recipes = si === 0 ? section.recipes.slice(1) : section.recipes
        if (recipes.length === 0) return null
        return (
          <section key={section.key} className="pa-section">
            <div className="pa-section-head">
              <h2 className="pa-section-title">{section.title}</h2>
              {section.subtitle && <span className="pa-section-sub">{section.subtitle}</span>}
            </div>
            <div className="pa-rail">
              {recipes.map(recipe => (
                <div key={recipe.id} className="pa-rail-item">
                  <RecipeCard recipe={recipe} variant="card" onClick={() => open(recipe.id)} />
                </div>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
