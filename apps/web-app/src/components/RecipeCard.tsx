import { useEffect, useState } from 'react'
import { getRecipeImageUrl } from '../api/client'
import type { RecipeSummary } from '../api/types'
import PhotoPlaceholder from './PhotoPlaceholder'
import StarRating from './StarRating'

function metaText(recipe: RecipeSummary): string[] {
  const m = recipe.recipie_metadata
  if (!m) return []
  const parts: string[] = []
  if (m.prep_time != null && m.cook_time != null) parts.push(`${m.prep_time + m.cook_time} min`)
  else if (m.prep_time != null) parts.push(`${m.prep_time} min prep`)
  else if (m.cook_time != null) parts.push(`${m.cook_time} min cook`)
  if (m.servings != null) parts.push(`serves ${m.servings}`)
  if (m.difficulty) parts.push(m.difficulty)
  return parts
}

interface Props {
  recipe: RecipeSummary
  variant: 'overlay' | 'card'
  onClick?: () => void
}

export default function RecipeCard({ recipe, variant, onClick }: Props) {
  const pills = metaText(recipe)
  const [imgUrl, setImgUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!recipe.image_key) { setImgUrl(null); return }
    getRecipeImageUrl(recipe.id, recipe.image_key).then(setImgUrl).catch(() => {})
  }, [recipe.id, recipe.image_key])

  if (variant === 'overlay') {
    return (
      <div style={{ height: '100%', position: 'relative' }} onClick={onClick}>
        {imgUrl
          ? <img src={imgUrl} alt={recipe.title} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
          : <PhotoPlaceholder style={{ height: '100%', borderRadius: 0, border: 'none' }} />
        }
        <div className="pa-mtile-overlay">
          <div className="pa-mtile-title">{recipe.title}</div>
          {pills.length > 0 && (
            <span className="pa-mtile-meta-text">{pills.join(' · ')}</span>
          )}
          {recipe.avg_rating !== null && (
            <span className="pa-mtile-rating">
              <StarRating value={recipe.avg_rating} size={11} />
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <button className="pa-card-btn" onClick={onClick}>
      {imgUrl
        ? <img src={imgUrl} alt={recipe.title} style={{ width: '100%', aspectRatio: '16/9', objectFit: 'cover', display: 'block' }} />
        : <PhotoPlaceholder ratio={16 / 9} style={{ borderRadius: 0, border: 'none' }} />
      }
      <div className="pa-card-body">
        <div className="pa-card-title">{recipe.title}</div>
        {recipe.description && (
          <div className="pa-card-desc">{recipe.description}</div>
        )}
        {recipe.tags.length > 0 && (
          <div className="pa-card-tags">
            {recipe.tags.map(t => <span key={t.id} className="sk-chip">{t.name}</span>)}
          </div>
        )}
        {(recipe.avg_rating !== null || recipe.review_count > 0) && (
          <div className="pa-card-rating">
            <StarRating value={recipe.avg_rating} count={recipe.review_count} size={13} />
          </div>
        )}
        {pills.length > 0 && (
          <span className="pa-card-meta-text">{pills.join(' · ')}</span>
        )}
      </div>
    </button>
  )
}
