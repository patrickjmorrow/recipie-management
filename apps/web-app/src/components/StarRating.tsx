interface StarIconProps {
  filled: number // 0–1
  size: number
  id: string
}

function StarIcon({ filled, size, id }: StarIconProps) {
  const clipId = `star-clip-${id}`
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden>
      <defs>
        <clipPath id={clipId}>
          <rect x="0" y="0" width={filled * 20} height="20" />
        </clipPath>
      </defs>
      {/* grey background star */}
      <path
        d="M10 1l2.39 4.84 5.35.78-3.87 3.77.91 5.32L10 13.27l-4.78 2.44.91-5.32L2.26 6.62l5.35-.78z"
        fill="var(--line)"
      />
      {/* gold filled star clipped to partial fill */}
      <path
        d="M10 1l2.39 4.84 5.35.78-3.87 3.77.91 5.32L10 13.27l-4.78 2.44.91-5.32L2.26 6.62l5.35-.78z"
        fill="var(--accent2)"
        clipPath={`url(#${clipId})`}
      />
    </svg>
  )
}

interface Props {
  value: number | null
  count?: number
  size?: number
}

export default function StarRating({ value, count, size = 16 }: Props) {
  return (
    <span className="pa-stars">
      {[1, 2, 3, 4, 5].map(n => (
        <StarIcon
          key={n}
          id={`${n}-${size}-${value}`}
          filled={Math.min(Math.max((value ?? 0) - (n - 1), 0), 1)}
          size={size}
        />
      ))}
      {count !== undefined && <span className="pa-stars-count">({count})</span>}
    </span>
  )
}
