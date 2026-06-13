import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useNavigate, useParams } from 'react-router-dom'
import { getRecipe } from '../api/client'
import type { RecipeIngredientResponse, RecipeResponse } from '../api/types'

const TIMER_RE = /(\d+)\s*(?:min|minutes)/i

function parseSteps(instructions: string | null): string[] {
  if (!instructions) return ['No instructions provided.']
  const steps = instructions.split(/\n---\n/)
  return steps.map(s => s.trim()).filter(Boolean)
}

function formatMmSs(secs: number) {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function IngredientLabel({ ing }: { ing: RecipeIngredientResponse }) {
  return (
    <span className="pa-cook-ing-label">
      <span className="pa-cook-ing-amount">{[ing.quantity, ing.unit].filter(Boolean).join(' ')}</span>
      {' '}{ing.ingredient.name}
      {ing.note && <span className="pa-cook-ing-note"> ({ing.note})</span>}
    </span>
  )
}

export default function CookMode() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [recipe, setRecipe] = useState<RecipeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState(0)
  const [checked, setChecked] = useState<Set<string>>(new Set())

  // timer
  const [secs, setSecs] = useState(0)
  const [running, setRunning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!id) return
    getRecipe(id)
      .then(setRecipe)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  // reset timer when step changes
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    setSecs(0)
    setRunning(false)
  }, [step])

  useEffect(() => {
    if (!running) {
      if (intervalRef.current) clearInterval(intervalRef.current)
      return
    }
    intervalRef.current = setInterval(() => {
      setSecs(s => {
        if (s <= 1) {
          setRunning(false)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [running])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!recipe) return
      const steps = parseSteps(recipe.instructions)
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') setStep(s => Math.min(s + 1, steps.length - 1))
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') setStep(s => Math.max(s - 1, 0))
      if (e.key === 'Escape') navigate(`/recipes/${id}`)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [recipe, id, navigate])

  if (loading) return <div className="pa-loading">Loading…</div>
  if (!recipe) return <div className="pa-error">Recipe not found.</div>

  const steps = parseSteps(recipe.instructions)
  const total = steps.length
  const current = steps[step]
  const timerMatch = current.match(TIMER_RE)
  const timerMins = timerMatch ? parseInt(timerMatch[1], 10) : null

  const ingredients = [...(recipe.recipe_ingredients ?? [])].sort(
    (a, b) => a.sort_order - b.sort_order
  )

  const toggleChecked = (ingId: string) => {
    setChecked(prev => {
      const next = new Set(prev)
      if (next.has(ingId)) next.delete(ingId)
      else next.add(ingId)
      return next
    })
  }

  const startTimer = () => {
    if (timerMins === null) return
    setSecs(timerMins * 60)
    setRunning(true)
  }

  return (
    <div className="pa-cook">
      <div className="pa-cook-top">
        <span className="pa-cook-recipe-title">{recipe.title}</span>
        <div style={{ flex: 1 }} />
        <span className="pa-cook-step-counter">STEP {step + 1} / {total}</span>
        <button className="pa-cook-close" onClick={() => navigate(`/recipes/${id}`)}>✕</button>
      </div>
      <div className="pa-cook-progress">
        {steps.map((_, i) => (
          <div
            key={i}
            className={'pa-prog-seg' + (i <= step ? ' done' : '')}
            onClick={() => setStep(i)}
          />
        ))}
      </div>

      <div className="pa-cook-main">
        {ingredients.length > 0 && (
          <aside className="pa-cook-ingredients">
            <span className="pa-cook-ing-title">Ingredients</span>
            <span className="pa-cook-ing-hint">Tap to check off</span>
            <div className="pa-cook-ing-list">
              {ingredients.map(ing => {
                const done = checked.has(ing.id)
                return (
                  <button
                    key={ing.id}
                    className={'pa-cook-ing-item' + (done ? ' done' : '')}
                    onClick={() => toggleChecked(ing.id)}
                  >
                    <span className={'pa-cook-ing-check' + (done ? ' done' : '')} aria-hidden>
                      {done ? '✓' : ''}
                    </span>
                    <IngredientLabel ing={ing} />
                  </button>
                )
              })}
            </div>
          </aside>
        )}

        <div className="pa-cook-body">
          <div className="pa-cook-step-num">{step + 1}</div>
          <div className="pa-cook-step-text">
            <ReactMarkdown>{current}</ReactMarkdown>
          </div>
          {timerMins !== null && (
            <div className="pa-timer" style={{ marginTop: 26 }}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent)', flexShrink: 0 }}>
                <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
              </svg>
              {running || secs > 0 ? (
                <>
                  <span className="pa-timer-display">{formatMmSs(secs)}</span>
                  <button className="pa-cook-nav-btn" onClick={() => setRunning(r => !r)}>
                    {running ? 'Pause' : 'Resume'}
                  </button>
                  <button className="pa-cook-nav-btn" onClick={() => { setRunning(false); setSecs(0) }}>
                    Reset
                  </button>
                </>
              ) : (
                <button className="pa-cook-nav-btn primary" onClick={startTimer}>
                  Start {timerMins}m timer
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="pa-cook-nav">
        <button
          className="pa-cook-nav-btn"
          onClick={() => setStep(s => Math.max(s - 1, 0))}
          disabled={step === 0}
        >
          ← Prev
        </button>
        <span className="pa-cook-nav-hint">screen stays awake while cooking</span>
        <button
          className="pa-cook-nav-btn primary"
          onClick={() => {
            if (step < total - 1) setStep(s => s + 1)
            else navigate(`/recipes/${id}`)
          }}
        >
          {step < total - 1 ? 'Next step →' : '✓ Done'}
        </button>
      </div>
    </div>
  )
}
