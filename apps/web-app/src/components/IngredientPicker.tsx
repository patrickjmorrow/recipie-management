import { useEffect, useRef, useState } from 'react'
import { getIngredients } from '../api/client'
import type { IngredientResponse } from '../api/types'

export interface PickedIngredient {
  id: string
  name: string
}

// Type-ahead over existing ingredients that accumulates a list of selected
// chips. Used for Advanced search (include/exclude) and the fridge picker.
// Mirrors the type-ahead pattern in RecipeEdit's IngredientNameInput.
export default function IngredientPicker({
  selected,
  onChange,
  placeholder = 'Add an ingredient…',
}: {
  selected: PickedIngredient[]
  onChange: (next: PickedIngredient[]) => void
  placeholder?: string
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<IngredientResponse[]>([])
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!open) return
    const q = query.trim()
    if (!q) { setResults([]); return }
    if (timer.current) clearTimeout(timer.current)
    let cancelled = false
    timer.current = setTimeout(() => {
      getIngredients(q, 8)
        .then(r => { if (!cancelled) setResults(r) })
        .catch(() => { if (!cancelled) setResults([]) })
    }, 300)
    return () => { cancelled = true; if (timer.current) clearTimeout(timer.current) }
  }, [open, query])

  function add(ing: IngredientResponse) {
    if (!selected.some(s => s.id === ing.id)) {
      onChange([...selected, { id: ing.id, name: ing.name }])
    }
    setQuery('')
    setResults([])
  }

  function remove(id: string) {
    onChange(selected.filter(s => s.id !== id))
  }

  const available = results.filter(r => !selected.some(s => s.id === r.id))

  return (
    <div className="pa-ing-picker">
      {selected.length > 0 && (
        <div className="pa-ing-chips">
          {selected.map(s => (
            <span key={s.id} className="pa-chip active">
              {s.name}
              <button type="button" className="pa-chip-x" onClick={() => remove(s.id)} aria-label={`Remove ${s.name}`}>×</button>
            </span>
          ))}
        </div>
      )}
      <div style={{ position: 'relative' }}>
        <input
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {open && query.trim() && available.length > 0 && (
          <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 30, marginTop: 2, background: 'var(--paper)', border: '1px solid var(--line)', borderRadius: 8, boxShadow: 'var(--shadow-hi)', maxHeight: 200, overflowY: 'auto' }}>
            {available.map(ing => (
              <button
                key={ing.id}
                type="button"
                onMouseDown={e => { e.preventDefault(); add(ing) }}
                style={{ display: 'block', width: '100%', textAlign: 'left', padding: '6px 8px', border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--ink)', fontSize: 14 }}
              >
                {ing.name}
                {ing.food?.name && <span style={{ color: 'var(--ink2)', fontSize: 12 }}> · {ing.food.name}</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
