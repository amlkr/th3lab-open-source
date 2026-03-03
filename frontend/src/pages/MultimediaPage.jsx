import { useState, useEffect } from 'react'
import ScaleBadge from '../components/ScaleBadge'
import { useAuth } from '../context/AuthContext'

const API_BASE = ''

function formatDuration(sec) {
  if (!sec) return '0s'
  if (sec < 60) return `${sec.toFixed(1)}s`
  return `${Math.floor(sec / 60)}m ${(sec % 60).toFixed(0)}s`
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function MultimediaPage() {
  const { user }  = useAuth()
  const [jobs, setJobs]       = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const userParam = user?.id ? `&user_id=${user.id}` : ''
        const res  = await fetch(`${API_BASE}/api/jobs/?job_type=video&limit=50${userParam}`)
        const data = await res.json()
        const list = data.jobs ?? []

        // Fetch full details for completed jobs
        const details = await Promise.all(
          list.map(j =>
            fetch(`${API_BASE}/api/jobs/${j.job_id}`)
              .then(r => r.json())
              .catch(() => j)
          )
        )
        setJobs(details)
      } catch {
        // silently fail
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user?.id])

  const toggle = (id) => setExpanded(prev => prev === id ? null : id)

  return (
    <div className="multimedia-page">
      <div className="page-header">
        <h1 className="page-title">Multimedia</h1>
        {jobs.length > 0 && (
          <span className="page-count">{jobs.length} videos</span>
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
          <p>Sin videos todavía</p>
          <span>Analizá un video en un proyecto para verlo acá</span>
        </div>
      ) : (
        <div className="multimedia-list">
          {jobs.map(job => {
            const shots = job.result?.shots ?? []
            const isOpen = expanded === job.job_id
            const scales = job.result?.scale_distribution ?? {}

            return (
              <div key={job.job_id} className={`multimedia-card${isOpen ? ' open' : ''}`}>
                {/* Card header */}
                <div className="multimedia-card-header" onClick={() => toggle(job.job_id)}>
                  <div className="multimedia-card-left">
                    <span className="multimedia-card-icon">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="5" width="20" height="14" rx="2" />
                        <polygon points="10 9 15 12 10 15 10 9" fill="currentColor" stroke="none" />
                      </svg>
                    </span>
                    <div>
                      <div className="multimedia-card-name">
                        {job.input_data?.filename ?? `Video ${job.job_id?.slice(0, 8)}`}
                      </div>
                      <div className="multimedia-card-meta">
                        {formatDate(job.created_at)} · {shots.length} planos
                        {job.result?.total_duration && ` · ${formatDuration(job.result.total_duration)}`}
                      </div>
                    </div>
                  </div>

                  <div className="multimedia-card-right">
                    {/* Scale pills */}
                    <div className="scale-dist">
                      {Object.entries(scales).map(([k, v]) => (
                        <span key={k} className="scale-dist-pill">
                          <ScaleBadge scale={k} />
                          <span className="scale-dist-pct">{v}%</span>
                        </span>
                      ))}
                    </div>
                    <span className={`status-pill status-${job.status}`}>{job.status}</span>
                    <span className="multimedia-chevron">{isOpen ? '▲' : '▼'}</span>
                  </div>
                </div>

                {/* Shot grid (expanded) */}
                {isOpen && shots.length > 0 && (
                  <div className="multimedia-shots">
                    {shots.map(s => (
                      <div key={s.shot_number} className="multimedia-shot">
                        {s.thumbnail_url ? (
                          <img
                            src={`${API_BASE}${s.thumbnail_url}`}
                            alt={`Shot ${s.shot_number}`}
                            className="multimedia-shot-thumb"
                            loading="lazy"
                          />
                        ) : (
                          <div className="multimedia-shot-thumb multimedia-shot-placeholder">◻</div>
                        )}
                        <div className="multimedia-shot-info">
                          {s.shot_scale && <ScaleBadge scale={s.shot_scale} />}
                          <span className="multimedia-shot-time">{s.start_time?.toFixed(1)}s</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
