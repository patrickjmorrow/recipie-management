import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRecipes, getTags } from '../api/client'
import type { RecipeSummary, TagResponse } from '../api/types'
import RecipeCard from '../components/RecipeCard'

const PRESET_TAGS = ['Dinner', 'Quick', 'Vegetarian', 'Sweet']

export default function Browse() {
  const navigate = useNavigate()
  const [recipes, setRecipes] = useState<RecipeSummary[]>([])
  const [tags, setTags] = useState<TagResponse[]>([])
  const [activeTagId, setActiveTagId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getTags().then(setTags).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const params: Record<string, string | string[]> = { limit: '50' }
    if (activeTagId) params['tag_ids'] = [activeTagId]
    getRecipes(params)
      .then(setRecipes)
      .catch(() => setError('Failed to load recipes.'))
      .finally(() => setLoading(false))
  }, [activeTagId])

  const filterTags = tags.filter(t => PRESET_TAGS.includes(t.name))

  function tileClass(index: number): string {
    if (index === 0) return 'pa-mtile span-big'
    if (index === 1 || index === 2) return 'pa-mtile span-wide'
    return 'pa-mtile'
  }

  return (
    <div className="pa-browse">
      <div className="pa-browse-header">
        <h1 className="pa-browse-title">What's Cooking?</h1>
        <div className="pa-filter-chips">
          <button
            className={'pa-chip' + (activeTagId === null ? ' active' : '')}
            onClick={() => setActiveTagId(null)}
          >
            All
          </button>
          {filterTags.map(tag => (
            <button
              key={tag.id}
              className={'pa-chip' + (activeTagId === tag.id ? ' active' : '')}
              onClick={() => setActiveTagId(activeTagId === tag.id ? null : tag.id)}
            >
              {tag.name}
            </button>
          ))}
        </div>
      </div>
      {loading && <div className="pa-loading">Loading…</div>}
      {error && <div className="pa-error">{error}</div>}
      {!loading && !error && (
        <div className="pa-mosaic">
          {recipes.map((recipe, i) => (
            <div key={recipe.id} className={tileClass(i)}>
              <RecipeCard
                recipe={recipe}
                variant="overlay"
                onClick={() => navigate(`/recipes/${recipe.id}`)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
