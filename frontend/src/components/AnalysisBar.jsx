import ScaleBadge from './ScaleBadge'

export default function AnalysisBar({ results }) {
  if (!results) return null

  if (results.shots) {
    const { shot_count, scale_distribution, dominant_movement } = results
    return (
      <div className="analysis-bar">
        <div className="analysis-metric">
          <span className="metric-label">Planos</span>
          <span className="metric-value" style={{ color: 'var(--violet-hi)' }}>
            {shot_count ?? results.shots.length}
          </span>
        </div>
        <div className="analysis-divider" />
        <div className="analysis-metric">
          <span className="metric-label">Movimiento</span>
          <span className="metric-value">{dominant_movement ?? '—'}</span>
        </div>
        <div className="analysis-divider" />
        <div className="analysis-metric">
          <span className="metric-label">Escala</span>
          <div className="scale-dist">
            {scale_distribution
              ? Object.entries(scale_distribution).map(([k, v]) => (
                  <span key={k} className="scale-chip">
                    <ScaleBadge scale={k} />
                    <span className="scale-pct">{v}%</span>
                  </span>
                ))
              : <span className="metric-value">—</span>
            }
          </div>
        </div>
        <div className="analysis-divider" />
        <div className="analysis-metric">
          <span className="metric-label">Duración total</span>
          <span className="metric-value">
            {results.shots.length > 0
              ? `${results.shots[results.shots.length - 1].end_time.toFixed(1)}s`
              : '—'}
          </span>
        </div>
      </div>
    )
  }

  const { coherence, reference, scale_distribution, atmosphere } = results
  return (
    <div className="analysis-bar">
      <div className="analysis-metric">
        <span className="metric-label">Coherence</span>
        <span className="metric-value" style={{ color: 'var(--violet-hi)' }}>
          {coherence?.score != null ? coherence.score.toFixed(1) : '—'}
        </span>
      </div>
      <div className="analysis-divider" />
      <div className="analysis-metric">
        <span className="metric-label">Reference</span>
        <span className="metric-value">{reference ?? '—'}</span>
      </div>
      <div className="analysis-divider" />
      <div className="analysis-metric">
        <span className="metric-label">Scale</span>
        <div className="scale-dist">
          {scale_distribution
            ? Object.entries(scale_distribution).map(([k, v]) => (
                <span key={k} className="scale-chip">
                  <ScaleBadge scale={k} />
                  <span className="scale-pct">{v}%</span>
                </span>
              ))
            : <span className="metric-value">—</span>
          }
        </div>
      </div>
      <div className="analysis-divider" />
      <div className="analysis-metric">
        <span className="metric-label">Atmosphere</span>
        <span className="metric-value atmosphere">{atmosphere ?? '—'}</span>
      </div>
    </div>
  )
}
