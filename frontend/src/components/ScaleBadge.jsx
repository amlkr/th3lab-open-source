const SCALE_BG = {
  ECS: '#4c1d95',
  CS:  '#5b21b6',
  MS:  '#6d28d9',
  FS:  '#7c3aed',
  LS:  '#8b5cf6',
}

export default function ScaleBadge({ scale }) {
  if (!scale) return null
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: 'var(--font-mono)',
        fontSize: '9px',
        fontWeight: 500,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        padding: '2px 5px',
        borderRadius: '3px',
        background: SCALE_BG[scale] ?? '#3730a3',
        color: '#e0d4ff',
        flexShrink: 0,
      }}
    >
      {scale}
    </span>
  )
}
