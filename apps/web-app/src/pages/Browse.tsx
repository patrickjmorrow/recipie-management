import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getBrowseSections } from '../api/client'
import type { BrowseSection } from '../api/types'
import RecipeCard, { formatBadge } from '../components/RecipeCard'

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

      {!loading && !error && sections.map(section => {
        if (section.recipes.length === 0) return null
        // First tile is the magazine "feature" (2×2); the CSS handles the spans.
        return (
          <section key={section.key} className="pa-section">
            <div className="pa-section-head">
              <h2 className="pa-section-title">{section.title}</h2>
              {section.subtitle && <span className="pa-section-sub">{section.subtitle}</span>}
            </div>
            <div className="pa-mosaic">
              {section.recipes.map(recipe => (
                <div key={recipe.id} className="pa-mosaic-tile">
                  <RecipeCard
                    recipe={recipe}
                    variant="overlay"
                    badge={formatBadge(recipe, section.badge)}
                    onClick={() => open(recipe.id)}
                  />
                </div>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
