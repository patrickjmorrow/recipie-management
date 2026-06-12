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

/** Total prep+cook time in minutes, or null if neither is set. */
function totalTime(recipe: RecipeSummary): number | null {
  const m = recipe.recipie_metadata
  if (!m) return null
  if (m.prep_time == null && m.cook_time == null) return null
  return (m.prep_time ?? 0) + (m.cook_time ?? 0)
}

/**
 * Format a section's contextual stat for a tile, or null when the underlying data
 * is missing so the tile simply omits the badge.
 */
export function formatBadge(recipe: RecipeSummary, badgeType: string | null): string | null {
  switch (badgeType) {
    case 'protein':
      return recipe.protein_g_per_serving != null
        ? `${Math.round(recipe.protein_g_per_serving * 10) / 10}g protein`
        : null
    case 'carbs':
      return recipe.carbs_g_per_serving != null
        ? `${Math.round(recipe.carbs_g_per_serving)}g carbs`
        : null
    case 'calories':
      return recipe.energy_kcal_per_serving != null
        ? `${Math.round(recipe.energy_kcal_per_serving)} cal`
        : null
    case 'time': {
      const t = totalTime(recipe)
      return t != null ? `${t} min` : null
    }
    default:
      return null
  }
}

interface Props {
  recipe: RecipeSummary
  variant: 'overlay' | 'card'
  onClick?: () => void
  /** Optional contextual stat (overlay variant only), e.g. from `formatBadge`. */
  badge?: string | null
}

export default function RecipeCard({ recipe, variant, onClick, badge }: Props) {
  const pills = metaText(recipe)
  const [imgUrl, setImgUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!recipe.image_key) { setImgUrl(null); return }
    getRecipeImageUrl(recipe.id, recipe.image_key).then(setImgUrl).catch(() => {})
  }, [recipe.id, recipe.image_key])

  if (variant === 'overlay') {
    // Show at most three tags so the overlay stays picture-forward.
    const tags = recipe.tags.slice(0, 3)
    return (
      <div style={{ height: '100%', position: 'relative' }} onClick={onClick}>
        {imgUrl
          ? <img src={imgUrl} alt={recipe.title} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
          : <PhotoPlaceholder style={{ height: '100%', borderRadius: 0, border: 'none' }} />
        }
        {badge && <span className="pa-mtile-badge">{badge}</span>}
        <div className="pa-mtile-overlay">
          <div className="pa-mtile-title">{recipe.title}</div>
          {tags.length > 0 && (
            <div className="pa-mtile-tags">
              {tags.map(t => <span key={t.id} className="pa-mtile-chip">{t.name}</span>)}
            </div>
          )}
          {/* Badge carries the contextual stat; fall back to the rating when there's no badge. */}
          {!badge && recipe.avg_rating !== null && (
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
