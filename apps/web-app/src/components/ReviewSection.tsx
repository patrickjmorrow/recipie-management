import { useEffect, useState } from 'react'
import { createReview, deleteReview, getReviews, updateReview } from '../api/client'
import type { ReviewResponse } from '../api/types'
import { useAuth } from '../contexts/AuthContext'
import StarRating from './StarRating'

interface StarPickerProps {
  value: number
  onChange: (v: number) => void
}

function StarPicker({ value, onChange }: StarPickerProps) {
  const [hovered, setHovered] = useState(0)
  const display = hovered || value
  return (
    <span className="pa-star-picker">
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          onMouseEnter={() => setHovered(n)}
          onMouseLeave={() => setHovered(0)}
          aria-label={`${n} star${n !== 1 ? 's' : ''}`}
        >
          <svg width="22" height="22" viewBox="0 0 20 20" aria-hidden>
            <path
              d="M10 1l2.39 4.84 5.35.78-3.87 3.77.91 5.32L10 13.27l-4.78 2.44.91-5.32L2.26 6.62l5.35-.78z"
              fill={n <= display ? 'var(--accent2)' : 'var(--line)'}
            />
          </svg>
        </button>
      ))}
    </span>
  )
}

interface Props {
  recipeId: string
  authorId: string | null
}

export default function ReviewSection({ recipeId, authorId }: Props) {
  const { user } = useAuth()
  const [reviews, setReviews] = useState<ReviewResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [draftRating, setDraftRating] = useState(0)
  const [draftBody, setDraftBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editRating, setEditRating] = useState(0)
  const [editBody, setEditBody] = useState('')

  useEffect(() => {
    getReviews(recipeId)
      .then(setReviews)
      .catch(() => setError('Could not load reviews.'))
      .finally(() => setLoading(false))
  }, [recipeId])

  const canReview = !!user && user.id !== authorId
  const myReview = reviews.find(r => r.reviewer_id === user?.id) ?? null
  const showForm = canReview && !myReview && editingId === null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (draftRating === 0) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const created = await createReview(recipeId, {
        rating: draftRating,
        body: draftBody.trim() || undefined,
      })
      setReviews(prev => [created, ...prev])
      setDraftRating(0)
      setDraftBody('')
    } catch (err: unknown) {
      const status = (err as { status?: number }).status
      if (status === 409) setSubmitError("You've already reviewed this recipe.")
      else if (status === 403) setSubmitError("You can't review your own recipe.")
      else setSubmitError('Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  function handleEditStart(review: ReviewResponse) {
    setEditingId(review.id)
    setEditRating(review.rating)
    setEditBody(review.body ?? '')
  }

  async function handleEditSave(reviewId: string) {
    if (editRating === 0) return
    try {
      const updated = await updateReview(recipeId, reviewId, {
        rating: editRating,
        body: editBody.trim() || undefined,
      })
      setReviews(prev => prev.map(r => (r.id === reviewId ? updated : r)))
      setEditingId(null)
    } catch {
      // keep edit form open on error
    }
  }

  async function handleDelete(reviewId: string) {
    try {
      await deleteReview(recipeId, reviewId)
      setReviews(prev => prev.filter(r => r.id !== reviewId))
    } catch {
      // ignore
    }
  }

  return (
    <section className="pa-reviews">
      <h3 className="pa-section-heading">Reviews</h3>

      {loading && <div className="pa-loading">Loading…</div>}
      {error && <div className="pa-error">{error}</div>}

      {showForm && (
        <form className="pa-review-form" onSubmit={handleSubmit}>
          <StarPicker value={draftRating} onChange={setDraftRating} />
          <textarea
            className="pa-review-textarea"
            placeholder="Share your thoughts (optional)"
            value={draftBody}
            onChange={e => setDraftBody(e.target.value)}
            rows={3}
          />
          {submitError && <div className="pa-review-error">{submitError}</div>}
          <div>
            <button
              className="pa-save-btn"
              type="submit"
              disabled={draftRating === 0 || submitting}
            >
              {submitting ? 'Submitting…' : 'Post Review'}
            </button>
          </div>
        </form>
      )}

      {!loading && reviews.length === 0 && (
        <p className="pa-reviews-empty">No reviews yet. Be the first!</p>
      )}

      {reviews.map(review => (
        <div key={review.id} className="pa-review-card">
          {editingId === review.id ? (
            <>
              <StarPicker value={editRating} onChange={setEditRating} />
              <textarea
                className="pa-review-textarea"
                value={editBody}
                onChange={e => setEditBody(e.target.value)}
                rows={3}
              />
              <div className="pa-review-actions">
                <button
                  className="pa-save-btn"
                  type="button"
                  onClick={() => handleEditSave(review.id)}
                  disabled={editRating === 0}
                >
                  Save
                </button>
                <button
                  className="pa-review-edit-btn"
                  type="button"
                  onClick={() => setEditingId(null)}
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="pa-review-meta">
                <StarRating value={review.rating} size={14} />
                <span className="pa-review-reviewer">{review.reviewer_display_name}</span>
                <span className="pa-review-date">
                  {new Date(review.created_at).toLocaleDateString()}
                </span>
              </div>
              {review.body && <p className="pa-review-body">{review.body}</p>}
              {myReview?.id === review.id && (
                <div className="pa-review-actions">
                  <button
                    className="pa-review-edit-btn"
                    type="button"
                    onClick={() => handleEditStart(review)}
                  >
                    Edit
                  </button>
                  <button
                    className="pa-review-delete-btn"
                    type="button"
                    onClick={() => handleDelete(review.id)}
                  >
                    Delete
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      ))}
    </section>
  )
}
