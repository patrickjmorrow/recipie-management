import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useNavigate, useParams } from 'react-router-dom'
import { getRecipe } from '../api/client'
import type { RecipeIngredientResponse, RecipeMetadata, RecipeResponse } from '../api/types'
import PhotoPlaceholder from '../components/PhotoPlaceholder'
import { useAuth } from '../contexts/AuthContext'

function ClockIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
      <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="2" />
      <path d="M10 5v5l2.5 2.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function CircleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
      <circle cx="10" cy="10" r="8.5" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

function DiamondIcon() {
  return (
    <svg width="28.28" height="28.28" viewBox="0 0 20 20" fill="none" aria-hidden>
      <rect x="10" y="2" width="10" height="10" transform="rotate(45 9 2)" stroke="currentColor" strokeWidth="1.41" />
    </svg>
  )
}

function parseSteps(instructions: string | null): string[] {
  if (!instructions) return []
  return instructions.split(/\n---\n/).map(s => s.trim()).filter(Boolean)
}

function IngredientLine({ ri }: { ri: RecipeIngredientResponse }) {
  const amt = [ri.quantity != null ? String(ri.quantity) : null, ri.unit].filter(Boolean).join(' ')
  return (
    <li className="pa-ing-row">
      <span className="pa-ing-amt">{amt || '—'}</span>
      <span className="pa-ing-name">
        {ri.ingredient.name}
        {ri.note && <span className="pa-ing-note"> · {ri.note}</span>}
      </span>
    </li>
  )
}

function MetaPills({ meta }: { meta: RecipeMetadata | null }) {
  if (!meta) return null

  const items: [React.ReactNode, string, string][] = []
  if (meta.prep_time != null) items.push([<ClockIcon />, 'PREP', `${meta.prep_time}m`])
  if (meta.cook_time != null) items.push([<ClockIcon />, 'COOK', `${meta.cook_time}m`])
  if (meta.servings != null) items.push([<CircleIcon />, 'SERVES', `${meta.servings}`])
  if (meta.difficulty) items.push([<DiamondIcon />, 'LEVEL', meta.difficulty])

  if (items.length === 0) return null

  return (
    <div className="pa-detail-meta">
      {items.map(([icon, label, value]) => (
        <div key={label} className="pa-meta-item">
          <span className="pa-meta-icon">{icon}</span>
          <span className="pa-meta-item-text">
            <span className="pa-meta-label">{label}</span>
            <span className="pa-meta-value">{value}</span>
          </span>
        </div>
      ))}
    </div>
  )
}

export default function RecipeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [recipe, setRecipe] = useState<RecipeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    getRecipe(id)
      .then(setRecipe)
      .catch(() => setError('Recipe not found.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="pa-loading">Loading…</div>
  if (error || !recipe) return <div className="pa-error">{error ?? 'Not found'}</div>

  const isAuthor = user?.id === recipe.author_id

  return (
    <div className="pa-detail">
      <div className="pa-detail-hero">
        <PhotoPlaceholder style={{ height: '100%', borderRadius: 0, border: 'none' }} />
        <div className="pa-hero-overlay">
          <div className="pa-hero-top">
            <button className="pa-hero-btn pa-hero-btn-back" onClick={() => navigate(-1)}>← Back</button>
            <button className="pa-hero-btn pa-hero-btn-cook" onClick={() => navigate(`/recipes/${id}/cook`)}>
              ▷ Cook mode
            </button>
          </div>
          <div className="pa-hero-bottom">
            {recipe.tags.length > 0 && (
              <div className="pa-hero-tags">
                {recipe.tags.map(t => (
                  <span key={t.id} className="pa-hero-tag">{t.name.toUpperCase()}</span>
                ))}
              </div>
            )}
            <h1 className="pa-hero-title">{recipe.title}</h1>
            {isAuthor && user?.display_name && (
              <span className="pa-hero-author">by {user.display_name}</span>
            )}
          </div>
        </div>
      </div>

      <div className="pa-detail-content">
        {recipe.description && (
              <p className="pa-detail-desc">{recipe.description}</p>
        )}
        <MetaPills meta={recipe.recipie_metadata} />

        {isAuthor && (
          <div className="pa-detail-actions">
            <button className="pa-btn-outline" onClick={() => navigate(`/recipes/${id}/edit`)}>
              Edit Recipe
            </button>
          </div>
        )}

        <div className="pa-detail-cols">
          <aside className="pa-detail-sidebar">
            {recipe.recipe_ingredients.length > 0 && (
              <div className="pa-sidebar-section">
                <h3 className="pa-section-heading">Ingredients</h3>
                {recipe.recipie_metadata?.servings != null && (
                  <span className="pa-ing-serves">SERVES {recipe.recipie_metadata.servings}</span>
                )}
                <ul className="pa-ingredient-list">
                  {recipe.recipe_ingredients
                    .slice()
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map(ri => <IngredientLine key={ri.id} ri={ri} />)}
                </ul>
              </div>
            )}
          </aside>

          <main className="pa-detail-main">
            {recipe.instructions && (
              <>
                <h3 className="pa-section-heading">Method</h3>
                <div className="pa-detail-instructions">
                  <ol>
                    {parseSteps(recipe.instructions).map((step, i) => (
                      <li key={i}><ReactMarkdown>{step}</ReactMarkdown></li>
                    ))}
                  </ol>
                </div>
              </>
            )}
            <button className="pa-bigbtn" onClick={() => navigate(`/recipes/${id}/cook`)}>
              ▷ Start cook mode
            </button>
          </main>
        </div>
      </div>
    </div>
  )
}
