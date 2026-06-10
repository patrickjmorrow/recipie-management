interface Props {
  ratio?: number
  label?: string
  style?: React.CSSProperties
  className?: string
}

export default function PhotoPlaceholder({ ratio, label, style, className }: Props) {
  const base: React.CSSProperties = {
    background: 'repeating-linear-gradient(135deg, #DBE6DC 0 11px, #CDDECF 11px 22px)',
    border: '1px solid var(--line)',
    borderRadius: 'var(--r)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    width: '100%',
    ...(ratio ? { aspectRatio: String(ratio) } : { height: '100%' }),
    ...style,
  }
  return (
    <div style={base} className={className}>
      {label && (
        <span style={{ color: 'var(--accent)', fontSize: 13, fontWeight: 600, opacity: .7 }}>
          {label}
        </span>
      )}
    </div>
  )
}
