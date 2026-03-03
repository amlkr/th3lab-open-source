import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'

const API_BASE = ''

function CoherenceRing({ score }) {
  const r   = 22
  const c   = 2 * Math.PI * r
  const pct = Math.min(100, Math.max(0, score ?? 0))
  const dash = (pct / 100) * c
  const color = pct >= 70 ? '#8b5cf6' : pct >= 40 ? '#a8b5c0' : '#c4a882'

  return (
    <div className="coherence-ring-wrap">
      <svg width="56" height="56" viewBox="0 0 56 56">
        <circle cx="28" cy="28" r={r} fill="none" stroke="var(--border)" strokeWidth="3" />
        <circle
          cx="28" cy="28" r={r}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeDasharray={`${dash} ${c}`}
          strokeLinecap="round"
          transform="rotate(-90 28 28)"
        />
      </svg>
      <span className="coherence-ring-value">{pct.toFixed(0)}</span>
    </div>
  )
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function ReportsPage() {
  const { user }  = useAuth()
  const [jobs, setJobs]       = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const userParam = user?.id ? `&user_id=${user.id}` : ''
        const res  = await fetch(`${API_BASE}/api/jobs/?status=completed&limit=50${userParam}`)
        const data = await res.json()
        const list = data.jobs ?? []

        const details = await Promise.all(
          list.map(j =>
            fetch(`${API_BASE}/api/jobs/${j.job_id}`)
              .then(r => r.json())
              .catch(() => null)
          )
        )
        setJobs(details.filter(Boolean))
      } catch {
        // silently fail
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user?.id])

  const sel = jobs.find(j => j.job_id === selected)

  return (
    <div className="reports-page">
      <div className="page-header">
        <h1 className="page-title">Reportes</h1>
        {jobs.length > 0 && (
          <span className="page-count">{jobs.length} análisis</span>
        )}
      </div>

      {loading ? (
        <div className="page-loading">
          <span className="page-loading-dot">◈</span>
          <span>cargando...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="page-empty">
          <div className="empty-icon">◻</div>
          <p>Sin reportes todavía</p>
          <span>Completá un análisis de imágenes o video para ver el reporte acá</span>
        </div>
      ) : (
        <div className="reports-layout">
          {/* Left: report list */}
          <div className="reports-list">
            {jobs.map(job => {
              const coherence = job.result?.coherence?.score ?? null
              const imageCount = job.result?.image_count
                ?? job.result?.semantic_analysis?.length
                ?? job.result?.shots?.length
                ?? 0

              return (
                <div
                  key={job.job_id}
                  className={`report-card${selected === job.job_id ? ' active' : ''}`}
                  onClick={() => setSelected(job.job_id === selected ? null : job.job_id)}
                >
                  <div className="report-card-top">
                    {coherence !== null ? (
                      <CoherenceRing score={coherence} />
                    ) : (
                      <div className="report-card-type-icon">
                        {job.job_type === 'video' ? '▶' : '◈'}
                      </div>
                    )}
                    <div className="report-card-info">
                      <div className="report-card-title">
                        {job.input_data?.filename
                          ?? (job.input_data?.filenames?.length
                              ? `${job.input_data.filenames.length} imágenes`
                              : `Job ${job.job_id?.slice(0, 8)}`)
                        }
                      </div>
                      <div className="report-card-meta">
                        <span className="report-type-badge">{job.job_type}</span>
                        <span>{formatDate(job.created_at)}</span>
                        {imageCount > 0 && <span>{imageCount} items</span>}
                      </div>
                    </div>
                  </div>

                  {coherence !== null && (
                    <div className="report-metrics-row">
                      <div className="report-metric">
                        <span className="report-metric-label">Coherencia</span>
                        <span className="report-metric-value">{coherence.toFixed(1)}</span>
                      </div>
                      {job.result?.outlier_count != null && (
                        <div className="report-metric">
                          <span className="report-metric-label">Outliers</span>
                          <span className="report-metric-value">{job.result.outlier_count}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {job.job_type === 'video' && job.result?.dominant_movement && (
                    <div className="report-metrics-row">
                      <div className="report-metric">
                        <span className="report-metric-label">Movimiento</span>
                        <span className="report-metric-value">{job.result.dominant_movement}</span>
                      </div>
                      <div className="report-metric">
                        <span className="report-metric-label">Planos</span>
                        <span className="report-metric-value">{job.result.shots?.length ?? 0}</span>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Right: detail panel */}
          {sel && (
            <div className="report-detail-panel">
              <div className="report-detail-header">
                <span className="report-detail-title">Detalle del análisis</span>
                <button className="report-detail-close" onClick={() => setSelected(null)}>×</button>
              </div>

              {sel.result?.report && (
                <div className="report-narrative">
                  <div className="report-narrative-label">Reporte narrativo</div>
                  <div className="report-narrative-text">{sel.result.report}</div>
                </div>
              )}

              {sel.result?.semantic_analysis?.length > 0 && (
                <div className="report-semantic-list">
                  <div className="report-narrative-label">Análisis semántico</div>
                  {sel.result.semantic_analysis.map((item, i) => (
                    <div key={i} className="report-semantic-item">
                      <div className="report-semantic-index">#{i + 1}</div>
                      <div className="report-semantic-data">
                        {item.shot_scale && <span className="report-tag">{item.shot_scale}</span>}
                        {item.atmosphere && <span className="report-tag">{item.atmosphere}</span>}
                        {item.light_quality && <span className="report-tag">{item.light_quality}</span>}
                        {item.composition_notes && (
                          <div className="report-semantic-note">{item.composition_notes}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {sel.result?.scale_distribution && (
                <div className="report-scales">
                  <div className="report-narrative-label">Distribución de escalas</div>
                  <div className="report-scale-bars">
                    {Object.entries(sel.result.scale_distribution).map(([k, v]) => (
                      <div key={k} className="report-scale-row">
                        <span className="report-scale-label">{k}</span>
                        <div className="report-scale-bar-track">
                          <div className="report-scale-bar-fill" style={{ width: `${v}%` }} />
                        </div>
                        <span className="report-scale-pct">{v}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
